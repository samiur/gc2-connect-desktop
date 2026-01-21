#nullable enable
using GSPro4OSP.Configuration;
using OpenSkyPlus2;
using OpenSkyPlus2.Configuration;
using OpenSkyPlus2.Helpers;
using OpenSkyPlus2.Mappers;
using OpenSkyPlus2.Models;
using OpenSkyPlus2.OpenSkyPlusApi;
using OpenSkyPlus2.Services;
using OpenSkyPlus2.AI;
using SkyTrakWrapper;
using System;
using System.Collections.Generic;
using System.IO;
using System.Linq;
using System.Net.Sockets;
using System.Text;
using System.Text.Json;
using System.Text.Json.Serialization;
using System.Threading;
using System.Threading.Tasks;
using UnityEngine;
using static OpenSkyPlus2.Logging.OpenSkyPlusLogger;
using static OpenSkyPlus2.OpenSkyPlusApi.OpenSkyPlus2Api;

namespace GSPro4OSP
{
    public static class GsProApi
    {
        private static TcpClient? _client;
        private static NetworkStream? _stream;
        private static CancellationTokenSource? _cts;
        private static Task? _readerTask;
        private static long _shotCounter;
        private static Timer? _heartbeatTimer;
        private const int HeartbeatIntervalMs = 6000;

        private static readonly object _connectionLock = new();
        private static bool _isConnecting;
        private static Task? _connectTask;

        public static event Action? OnConnectedCallback;
        public static event Action? OnConnected;
        public static event Action? OnDisconnected;

        private static bool _hardwareReady = false;
        private static bool _matchStarted = false;
        private static bool _lastMonitorReadyState = false;
        private static readonly object _presenceLock = new();
        private static bool? _lastPresenceSent;
        private static DateTime _lastMatchStartSignalUtc = DateTime.MinValue;
        private static DateTime _last202Utc = DateTime.MinValue;

        private static float _currentDistanceToTarget;
        public static float CurrentDistanceToTarget => _currentDistanceToTarget;

        // Local state cache for bridge-only sync (no GSPro echo)
        private static ShotMode _cachedShotMode = ShotMode.Normal;
        private static Handedness _cachedHandedness = Handedness.RightHanded;

        public static ShotMode CachedShotMode => _cachedShotMode;
        public static Handedness CachedHandedness => _cachedHandedness;

        private static readonly JsonSerializerOptions jsonOptions = new JsonSerializerOptions
        {
            DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
            PropertyNamingPolicy = JsonNamingPolicy.CamelCase,
            WriteIndented = false
        };

        private class GsProBridge : IBridgeShotModeSync, IBridgeHandednessSync, IBridgeBallStatusSync
        {
            public void NotifySetShotMode(ShotMode mode)
            {
                if (_cachedShotMode == mode)
                    return;

                _cachedShotMode = mode;
                Info($"[GSPro4OSP] shot mode updated succesfully to {_cachedShotMode}");
                
            }

            public void NotifySetHandedness(Handedness hand)
            {
                if (_cachedHandedness == hand)
                    return;

                _cachedHandedness = hand;
                Info($"[GSPro4OSP] Bridge handedness updated succesfully to {_cachedHandedness}");
                
            }

            public void NotifyBallStatusChanged(STSWBallStatus status)
            {
                var detected =
                    status == STSWBallStatus.STSW_ONE_OR_MORE_BALLS ||
                    status == STSWBallStatus.STSW_LOCKED_ON_BALL;

                if (status == STSWBallStatus.STSW_BALL_LAUNCHED)
                    detected = false;

                GsProApi.SendBallStatus(detected);
            }
        }

        internal sealed class GsProSettingsBridge : OpenSkyPlus2Api.IGsProSettingsBridge
        {
            public bool AutoPuttingEnabled
            {
                get => GSPro4OspConfiguration.DistanceToPtMode.Value >= 0f;
                set => GSPro4OspConfiguration.DistanceToPtMode.Value = value ? 0f : -1f;
            }

            public float ShortChipDistance
            {
                get => GSPro4OspConfiguration.DistanceToShortChipMode.Value;
                set
                {
                    var v = MathF.Max(0f, value);
                    GSPro4OspConfiguration.DistanceToShortChipMode.Value = v;
                }
            }

            public string ShortChipUnit
            {
                get => NormalizeUnit(GSPro4OspConfiguration.DistanceToShortChipModeUnit.Value);
                set
                {
                    var newUnit = NormalizeUnit(value);
                    var meters = GSPro4OspConfiguration.Settings.DistanceToShortChipModeInMeters;
                    GSPro4OspConfiguration.DistanceToShortChipModeUnit.Value = newUnit;
                    GSPro4OspConfiguration.DistanceToShortChipMode.Value = MetersToUnit(meters, newUnit);
                }
            }

            public void Save() => GSPro4OspConfiguration.Save();
            public void Reload() => GSPro4OspConfiguration.Reload();

            private static string NormalizeUnit(string? u)
            {
                if (string.IsNullOrWhiteSpace(u)) return "yards";
                u = u.Trim().ToLowerInvariant();
                return (u is "yards" or "feet" or "meters") ? u : "yards";
            }

            private static float MetersToUnit(float m, string unit) => unit switch
            {
                "meters" => m,
                "feet" => m / 0.3048f,
                _ => m / 0.9144f,
            };
        }

        public static bool IsConnected
        {
            get
            {
                lock (_connectionLock)
                {
                    return _client?.Connected == true && _stream != null;
                }
            }
        }

        public static void SetHardwareReady(bool ready)
        {
            if (_hardwareReady != ready)
            {
                _hardwareReady = ready;
                EvaluateAndSendReadyToGsPro();
            }
        }

        private static void SetMatchStarted(bool started)
        {
            if (started)
            {
                var now = DateTime.UtcNow;

                if ((now - _lastMatchStartSignalUtc).TotalSeconds < 2)
                    return;
                _lastMatchStartSignalUtc = now;
            }

            if (_matchStarted == started)
                return;

            _matchStarted = started;

            if (_matchStarted)
                StartHeartbeat();
            else
                StopHeartbeat();

            EvaluateAndSendReadyToGsPro();
        }

        private static void EvaluateAndSendReadyToGsPro()
        {
            bool reportReady = _hardwareReady && _matchStarted;
            SetMonitorReadyState(reportReady);
        }

        public static void Connect()
        {
            var cfg = GSPro4OspConfiguration.Settings;

            lock (_connectionLock)
            {
                if (_isConnecting)
                {
                    Info("[GSPro4OSP] Connect() called while a connection attempt is already in progress; ignoring.");
                    return;
                }

                if (_client?.Connected == true && _stream != null)
                {
                    return;
                }

                _isConnecting = true;

                try { _cts?.Cancel(); } catch { }
                _cts = null;
                _readerTask = null;

                try { _stream?.Close(); } catch { }
                try { _client?.Close(); } catch { }
                _stream = null;
                _client = null;

                _connectTask = ConnectLoopAsync(cfg);
            }
        }

        private static async Task ConnectLoopAsync(PluginSettings cfg)
        {
            int attempts = 0;
            try
            {
                while (cfg.MaxRetries < 0 || attempts < cfg.MaxRetries)
                {
                    try
                    {
                        Info($"[GSPro4OSP] [SYNC-CONNECT] Attempt {attempts + 1} to {cfg.Hostname}:{cfg.Port}");

                        var client = new TcpClient();
                        await client.ConnectAsync(cfg.Hostname, cfg.Port);
                        var stream = client.GetStream();

                        lock (_connectionLock)
                        {
                            _client = client;
                            _stream = stream;
                            lock (_presenceLock) _lastPresenceSent = null;
                        }

                        Info($"[GSPro4OSP] [SYNC-CONNECT] Connected to {cfg.Hostname}:{cfg.Port}");

                        await SendDeviceRegistrationAsync();

                        OnConnectedCallback?.Invoke();
                        OnConnected?.Invoke();

                        var bridge = new GsProBridge();
                        OpenSkyPlus2Api.GetInstance().RegisterService<IBridgeShotModeSync>(bridge);
                        OpenSkyPlus2Api.GetInstance().RegisterService<IBridgeHandednessSync>(bridge);
                        OpenSkyPlus2Api.GetInstance().RegisterService<IBridgeBallStatusSync>(bridge);
                        OpenSkyPlus2Api.GetInstance().RegisterService<OpenSkyPlus2Api.IGsProSettingsBridge>(new GsProSettingsBridge());

                        SetMatchStarted(false);

                        var cts = new CancellationTokenSource();
                        lock (_connectionLock)
                        {
                            _cts = cts;
                            _readerTask = Task.Run(() => ReadLoop(cts.Token), cts.Token);
                        }

                        return;
                    }
                    catch (Exception ex)
                    {
                        Warning($"[GSPro4OSP] [SYNC-CONNECT] Connection failed: {ex.Message}");
                        attempts++;

                        if (cfg.MaxRetries < 0 || attempts < cfg.MaxRetries)
                        {
                            Warning($"[GSPro4OSP] [SYNC-CONNECT] Retrying in {cfg.RetryDelay / 1000} seconds...");
                            await Task.Delay(cfg.RetryDelay);
                        }
                        else
                        {
                            Warning("[GSPro4OSP] [SYNC-CONNECT] Max connection attempts exceeded, aborting.");
                            break;
                        }
                    }
                }
            }
            finally
            {
                lock (_connectionLock)
                {
                    _isConnecting = false;
                }
            }
        }

        private static async Task SendDeviceRegistrationAsync()
        {
            if (_stream == null) return;

            string deviceJson = OpenSkyPlus2Telemetry.MapToGsProDeviceJson();
            var regBytes = Encoding.UTF8.GetBytes(deviceJson + "\n");
            await _stream.WriteAsync(regBytes, 0, regBytes.Length);
            Info("[GSPro4OSP] Sent device registration to GSPro APIv1 connector");
        }

        public static void Disconnect()
        {
            try
            {
                CancellationTokenSource? ctsToCancel;
                lock (_connectionLock)
                {
                    ctsToCancel = _cts;
                    _cts = null;
                }

                try { ctsToCancel?.Cancel(); } catch { }

                lock (_connectionLock)
                {
                    _readerTask = null;
                    try { _stream?.Close(); } catch { }
                    try { _client?.Close(); } catch { }
                    _stream = null;
                    _client = null;
                    _isConnecting = false;
                }

                Info("[GSPro4OSP] Disconnected manually.");
                _shotCounter = 0;
            }
            catch (Exception ex)
            {
                Warning($"[GSPro4OSP] Error during manual disconnect: {ex.Message}");
            }
            finally
            {
                StopHeartbeat();
                SetMatchStarted(false);
                OnDisconnected?.Invoke();
            }

            lock (_presenceLock) _lastPresenceSent = null;
        }

        public static async void SendShotData(ShotData shot)
        {
            var openSkyCfg = OpenSkyPlusConfiguration.GetSettings();
            float threshold = openSkyCfg.ShotConfidence switch
            {
                ShotConfidenceLevel.Forgiving => 0.1f,
                ShotConfidenceLevel.Normal => 0.25f,
                ShotConfidenceLevel.Strict => 0.5f,
                _ => 0.51f
            };

            if ((shot.Launch?.BallSpeedConfidence ?? 1f) < threshold ||
                (shot.Launch?.LaunchAngleConfidence ?? 1f) < threshold ||
                (shot.Launch?.LaunchDirectionConfidence ?? 1f) < threshold)
            {
                Warning($"[GSPro4OSP] Shot #{_shotCounter + 1} has low confidence (BallSpeed: {shot.Launch?.BallSpeedConfidence}, LaunchAngle: {shot.Launch?.LaunchAngleConfidence}, LaunchDirection: {shot.Launch?.LaunchDirectionConfidence}) - sending anyway.");
            }

            if (!IsConnected || _stream == null)
            {
                Warning("[GSPro4OSP] Not connected to GSPro, scheduling reconnect and skipping shot.");
                Connect();
                return;
            }

            try
            {
                var shotNumber = (int)Interlocked.Increment(ref _shotCounter);
                var isBallDetected = OpenSkyPlus2Api.GetInstance().LaunchMonitor?.IsBallDetected ?? false;

                var merged = shot;
                var smart = shot.SmartResult;

                if (smart != null)
                {
                    var originIsNative = smart.Annotation?.FieldSources?.ContainsKey("__origin.native") == true;
                    if (originIsNative)
                    {
                        merged = smart.Data;
                        Info($"[GSPro4OSP] Native origin detected — pass-through for shot #{shotNumber}.");
                    }
                    else
                    {
                        try
                        {
                            var key = CorrelationKey.Build(smart.Data);
                            if (!string.IsNullOrEmpty(key) &&
                                AugmentationRegistry.TryGet(key, out var aug) && aug != null)
                            {
                                var fieldSources = smart.Annotation?.FieldSources;
                                merged = MergeHelpers.MergeNonMeasured(
                                    smart.Data,
                                    aug.Data,
                                    field =>
                                    {
                                        if (fieldSources != null && fieldSources.TryGetValue(field, out var src))
                                            return src != DataSourceType.Measured;
                                        return true;
                                    }
                                );
                                Info($"[GSPro4OSP] Annotation-merge applied for shot #{shotNumber} (key={key}, conf={aug.OverallConfidence:0.00}).");
                            }
                        }
                        catch (Exception ex)
                        {
                            Warning($"[GSPro4OSP] Annotation merge failed: {ex.Message}");
                        }
                    }
                }
                else
                {
                    try
                    {
                        var key = CorrelationKey.Build(shot);
                        if (!string.IsNullOrEmpty(key) &&
                            AugmentationRegistry.TryGet(key, out var aug) && aug != null)
                        {
                            merged = MergeHelpers.MergeIfMissing(shot, aug.Data);
                            Info($"[GSPro4OSP] Conservative merge applied for shot #{shotNumber} (key={key}, conf={aug.OverallConfidence:0.00}).");
                        }
                    }
                    catch (Exception ex)
                    {
                        Warning($"[GSPro4OSP] Conservative merge failed: {ex.Message}");
                    }
                }

                var request = new GsProRequest
                {
                    ShotNumber = shotNumber,
                    DeviceID = "GsPro4Osp",
                    APIversion = "1",
                    Units = "Yards",
                    BallData = new BallData
                    {
                        Speed = (merged.Launch?.BallSpeed ?? 0f) * 2.23694f,
                        SpinAxis = merged.Spin?.SpinAxis,
                        TotalSpin = merged.Spin?.TotalSpin,
                        BackSpin = merged.Spin?.BackSpin,
                        SideSpin = merged.Spin?.SideSpin,
                        HLA = merged.Launch?.HorizontalAngle ?? 0f,
                        VLA = merged.Launch?.LaunchAngle ?? 0f,
                        CarryDistance = merged.Positions?.CarryDistance ?? 0f
                    },
                    ClubData = new ClubData
                    {
                        Speed = (merged.Club?.ClubHeadSpeed ?? 0f) * 2.23694f,
                        AngleOfAttack = merged.Club?.AttackAngle ?? 0f,
                        FaceToTarget = merged.Club?.FaceToTarget ?? 0f,
                        Lie = merged.Club?.DynamicLieAngle,
                        Loft = merged.Club?.DynamicLoft,
                        Path = merged.Club?.ClubPath ?? 0f,
                        SpeedAtImpact = (merged.Club?.SpeedAtImpact ?? 0f) * 2.23694f,
                        VerticalFaceImpact = merged.Club?.ImpactLocationVertical ?? 0f,
                        HorizontalFaceImpact = merged.Club?.ImpactLocationHorizontal ?? 0f,
                        ClosureRate = merged.Club?.ClubClosureRate ?? 0f,
                        DynamicLoft = merged.Club?.DynamicLoft,
                        SmashFactor = merged.Club?.SmashFactor
                    },
                    ShotDataOptions = new ShotDataOptions
                    {
                        ContainsBallData = true,
                        ContainsClubData = true,
                        LaunchMonitorIsReady = _lastMonitorReadyState,
                        LaunchMonitorBallDetected = isBallDetected,
                        IsHeartBeat = false
                    }
                };

                string shotJson = JsonSerializer.Serialize(request, jsonOptions);

                MainThreadInvoker.Run(() =>
                {
                    ExpandedUI.AppendLog(
                        $"Shot #{shotNumber} → " +
                        $"BallSpeed={shot.Launch?.BallSpeed:F1}, " +
                        $"Carry={shot.Positions?.CarryDistance:F1}, " +
                        $"ClubSpeed={shot.Club?.ClubHeadSpeed:F1}");
                }, "G4O - SendShotData - log");

                await _stream.WriteAsync(
                    Encoding.UTF8.GetBytes(shotJson + "\n"),
                    0,
                    Encoding.UTF8.GetByteCount(shotJson + "\n")
                );
                lock (_presenceLock) _lastPresenceSent = isBallDetected;
                Info($"[GSPro4OSP] Shot #{shotNumber} telemetry sent successfully.");
            }
            catch (Exception ex)
            {
                MainThreadInvoker.Run(() =>
                {
                    ExpandedUI.AppendLog($"[GSPro4OSP] Failed to send shot data: {ex.Message}");
                }, "G4O - SendShotData - Failed log");
            }
        }

        private static async Task ReadLoop(CancellationToken token)
        {
            Info("[GSPro4OSP] >>> Entered ReadLoop");
            try
            {
                var buffer = new byte[4096];
                var incomplete = "";

                while (!token.IsCancellationRequested && IsConnected && _stream != null)
                {
                    if (_stream.DataAvailable)
                    {
                        Info("[GSPro4OSP] [TRACE] DataAvailable = TRUE, beginning read...");
                        var memoryStream = new MemoryStream();
                        int bytesRead;
                        do
                        {
                            Info("[GSPro4OSP] [TRACE] About to call ReadAsync...");
                            bytesRead = await _stream.ReadAsync(buffer, 0, buffer.Length, token);
                            Info($"[GSPro4OSP] [TRACE] ReadAsync returned {bytesRead} bytes.");
                            if (bytesRead > 0)
                                memoryStream.Write(buffer, 0, bytesRead);
                        } while (_stream.DataAvailable && !token.IsCancellationRequested);

                        var jsonResponse = incomplete + Encoding.UTF8.GetString(memoryStream.ToArray());
                        Info($"\n[GSPro4OSP] Response:\n{jsonResponse}");

                        var lines = jsonResponse.Split(new[] { '\n', '\r' }, StringSplitOptions.RemoveEmptyEntries);
                        var responses = new List<GsProResponse>();

                        incomplete = "";
                        if (lines.Length > 0 && !lines[^1].Trim().EndsWith("}"))
                        {
                            incomplete = lines[^1];
                            lines = lines.Take(lines.Length - 1).ToArray();
                        }

                        foreach (var line in lines)
                        {
                            Info($"[GSPro4OSP] [TRACE] About to deserialize line: {line}");
                            try
                            {
                                var resp = JsonSerializer.Deserialize<GsProResponse>(line);
                                if (resp != null)
                                    responses.Add(resp);
                            }
                            catch (JsonException)
                            {
                                if (!_matchStarted && line.Contains("GSPro ready", StringComparison.OrdinalIgnoreCase))
                                {
                                    Info("[GSPro4OSP] Handshake: 'GSPro ready' detected, simulating match start.");
                                    OnResponse(new GsProResponse { Code = 202, Message = "GSPro ready" });
                                }
                                else
                                {
                                    Warning($"[GSPro4OSP] [TRACE] JsonException on line: {line}");
                                }
                            }
                            catch (Exception ex)
                            {
                                Warning($"[GSPro4OSP] Couldn't deserialize GSPro response: {ex}");
                            }
                        }

                        foreach (var resp in responses)
                        {
                            Info("[GSPro4OSP] [TRACE] Passing deserialized response to OnResponse");
                            OnResponse(resp);
                        }
                    }

                    await Task.Delay(100, token);
                }

                Info("[GSPro4OSP] [TRACE] Exiting ReadLoop main while loop.");
            }
            catch (OperationCanceledException)
            {
                Info("[GSPro4OSP] [TRACE] OperationCanceledException caught in ReadLoop (normal shutdown).");
            }
            catch (Exception ex)
            {
                Error($"[GSPro4OSP] [FATAL] ReadLoop threw an exception: {ex}");
            }
            finally
            {
                if (!token.IsCancellationRequested)
                {
                    Warning("[GSPro4OSP] Lost connection, will attempt to reconnect.");
                                        
                    OnDisconnected?.Invoke();
                                        
                    MainThreadInvoker.Run(() =>
                    {
                        ConnectionUiHelper.EvaluateBridgeConnection();
                    });

                    Connect();
                }
                else
                {
                    Info("[GSPro4OSP] ReadLoop cancelled due to plugin shutdown or disconnect.");
                }
            }
        }

        public static void SendStatus(bool ready)
        {
            var isBallDetected = OpenSkyPlus2Api.GetInstance().LaunchMonitor?.IsBallDetected ?? false;
            var statusRequest = new
            {
                APIversion = "1",
                DeviceID = "GsPro4Osp",
                Units = "Yards",
                ShotDataOptions = new
                {
                    IsHeartBeat = false,
                    LaunchMonitorIsReady = ready,
                    LaunchMonitorBallDetected = isBallDetected
                }
            };

            string statusJson = JsonSerializer.Serialize(statusRequest, jsonOptions);

            try
            {
                if (_stream != null && IsConnected)
                {
                    var bytes = Encoding.UTF8.GetBytes(statusJson + "\n");
                    _stream.Write(bytes, 0, bytes.Length);
                    lock (_presenceLock) _lastPresenceSent = isBallDetected;
                    Info($"[GSPro4OSP] Sent ready status ({ready}) to GSPro.");
                }
                else
                {
                    Warning("[GSPro4OSP] Tried to send status to GSPro, but not connected.");
                }
            }
            catch (Exception ex)
            {
                Warning($"[GSPro4OSP] Failed to send status to GSPro: {ex.Message}");
            }
        }

        public static void SendBallStatus(bool isDetected)
        {
            if (_stream == null || !IsConnected) return;

            lock (_presenceLock)
            {
                if (!isDetected) { _lastPresenceSent = false; return; }
                if (_lastPresenceSent == true) return;
                _lastPresenceSent = true;
            }

            var payload = new
            {
                APIversion = "1",
                DeviceID = "GsPro4Osp",
                Units = "Yards",
                ShotDataOptions = new
                {
                    IsHeartBeat = false,
                    LaunchMonitorIsReady = _lastMonitorReadyState,
                    LaunchMonitorBallDetected = true
                }
            };
            var json = JsonSerializer.Serialize(payload, jsonOptions) + "\n";
            _stream.Write(Encoding.UTF8.GetBytes(json));

            Info("[GSPro4OSP] -> Sent Ball Detected");
        }

        private static void OnResponse(GsProResponse response)
        {
            try
            {
                var responseCode = response?.Code ?? 0;
                switch (responseCode)
                {
                    case 201:
                        
                        HandlePlayerInfo201Coalesced(response!);
                        break;

                    case 202:
                        _last202Utc = DateTime.UtcNow;
                        Info("[GSPro4OSP] GSPro is Ready.");
                        SetMatchStarted(true);
                        break;

                    case 203:
                        if ((response?.Message ?? "") == "GSPro round ended")
                        {
                            Info("[GSPro4OSP] Match ended.");
                            SetMatchStarted(false);
                            StopHeartbeat();
                        }
                        break;

                    default:
                        if ((response?.Code ?? 500) >= 500)
                            Warning($"[GSPro4OSP] Received a failure response from GSPro: Code: {response?.Code}, Message: {response?.Message}");
                        break;
                }
            }
            catch (Exception ex)
            {
                Warning($"[GSPro4OSP] Failed when processing GSPro response: {ex}");
            }
        }

        private static void CheckPlayerHandedness(string handed)
        {
            var handedness = handed.StartsWith("L", StringComparison.OrdinalIgnoreCase)
                ? Handedness.LeftHanded
                : Handedness.RightHanded;

            var api = OpenSkyPlus2Api.GetInstance();
            var current = api.GetService<ILaunchMonitorSW>()?.CurrentDexterity == Dexterity.LeftHanded
                ? Handedness.LeftHanded
                : Handedness.RightHanded;

            if (current != handedness)
                api.SetHandedness(handedness);
            else
                Info("[GSPro4OSP] Handedness already set, skipping redundant update.");
        }

        private static void UpdateDistanceToTargetAndPutting(string club, float distanceToPin)
        {
            _currentDistanceToTarget = distanceToPin;
            var api = OpenSkyPlus2Api.GetInstance();
            api.UpdateDistanceToTarget(_currentDistanceToTarget);

            var settings = GSPro4OspConfiguration.Settings;
            var currentMode = api.GetDeviceShotMode();

            try
            {
                bool shortChipEnabled = settings.DistanceToShortChipMode > 0;

               
                bool clubMatchesChip = false;
                bool isShortChip = false;

                if (shortChipEnabled)
                {
                    clubMatchesChip =
                        settings.ShortChipModeClubs?.Any(c => c.Equals(club, StringComparison.OrdinalIgnoreCase)) ?? false;

                    if (distanceToPin > 0f)
                        isShortChip = clubMatchesChip && (distanceToPin <= settings.DistanceToShortChipModeInMeters);
                }

                bool inPuttingClubs =
                    settings.PuttingModeClubs?.Any(c => c.Equals(club, StringComparison.OrdinalIgnoreCase)) ?? false;

                bool isPutting;
                if (settings.DistanceToPtMode < 0)
                {
                    isPutting = false;
                }
                else if (settings.DistanceToPtMode == 0)
                {
                    isPutting = club.Equals("PT", StringComparison.OrdinalIgnoreCase) || inPuttingClubs;
                }
                else
                {
                    if (distanceToPin > 0f)
                    {
                        isPutting =
                            club.Equals("PT", StringComparison.OrdinalIgnoreCase)
                            || inPuttingClubs
                            || distanceToPin <= settings.DistanceToPtModeInMeters;
                    }
                    else
                    {
                        isPutting = club.Equals("PT", StringComparison.OrdinalIgnoreCase) || inPuttingClubs;
                    }
                }

                bool goPuttingMode = isShortChip || isPutting;

                
                Info(
                    $"[GSPro4OSP] DistEval club={club}, dist={distanceToPin:F2}, " +
                    $"shortChipEnabled={shortChipEnabled}, " +
                    $"chipClubs=[{string.Join(",", settings.ShortChipModeClubs ?? Array.Empty<string>())}], " +
                    $"chipThreshM={settings.DistanceToShortChipModeInMeters:F2}, clubMatchesChip={clubMatchesChip}, isShortChip={isShortChip}, " +
                    $"ptModeRaw={settings.DistanceToPtMode}, ptThreshM={settings.DistanceToPtModeInMeters:F2}, " +
                    $"isPutting={isPutting}, currentMode={currentMode}, goPuttingMode={goPuttingMode}"
                );

                if (goPuttingMode && currentMode != ShotMode.Putting)
                {
                    api.ForcePuttingMode();
                    if (isShortChip)
                        Info($"[GSPro4OSP] ShortChipMode engaged (club={club}, dist={distanceToPin:F1}m, thresh={settings.DistanceToShortChipModeInMeters:F1}m).");
                    else
                        Info($"[GSPro4OSP] TruePutt engaged (club={club}, dist={distanceToPin:F1}m).");
                }
                else if (!goPuttingMode && currentMode != ShotMode.Normal)
                {
                    api.ForceNormalMode();
                    Info("[GSPro4OSP] Requested mode change to Normal.");
                }
                else
                {
                    
                    if (currentMode == ShotMode.Putting && goPuttingMode)
                    {
                        if (isShortChip)
                        {
                            Info(
                                $"[GSPro4OSP] ShortChipMode condition met while already in Putting " +
                                $"(club={club}, dist={distanceToPin:F1}m, thresh={settings.DistanceToShortChipModeInMeters:F1}m)."
                            );
                        }
                        else if (isPutting)
                        {
                            Info(
                                $"[GSPro4OSP] TruePutt condition met while already in Putting " +
                                $"(club={club}, dist={distanceToPin:F1}m)."
                            );
                        }
                        else
                        {
                            Info("[GSPro4OSP] Already in Putting; goPuttingMode=true but neither ShortChip nor TruePutt flagged (diagnostic).");
                        }
                    }
                    else
                    {
                        Info("[GSPro4OSP] ShotMode already set, skipping redundant update.");
                    }
                }

            }
            catch (Exception ex)
            {
                Warning($"[GSPro4OSP] CalculateDistanceMode failed: {ex.Message}");
            }
        }

       
        public static void StartHeartbeat()
        {
            StopHeartbeat();
            _heartbeatTimer = new Timer(_ => SendHeartbeat(_lastMonitorReadyState), null, HeartbeatIntervalMs, HeartbeatIntervalMs);
            Info("[GSPro4OSP] Heartbeat timer started.");
        }

        public static void StopHeartbeat()
        {
            _heartbeatTimer?.Dispose();
            _heartbeatTimer = null;
            Info("[GSPro4OSP] Heartbeat timer stopped.");
        }

        public static void SetMonitorReadyState(bool isReady)
        {
            if (_lastMonitorReadyState != isReady)
            {
                _lastMonitorReadyState = isReady;
                SendStatus(isReady);
            }
        }

        public static void SendHeartbeat(bool isReady)
        {
            var isBallDetected = OpenSkyPlus2Api.GetInstance().LaunchMonitor?.IsBallDetected ?? false;
            var payload = new
            {
                APIversion = "1",
                DeviceID = "GsPro4Osp",
                Units = "Yards",
                ShotDataOptions = new
                {
                    IsHeartBeat = true,
                    LaunchMonitorIsReady = isReady,
                    LaunchMonitorBallDetected = isBallDetected
                }
            };

            string heartbeatJson = JsonSerializer.Serialize(payload, jsonOptions) + "\n";
            try
            {
                if (_stream != null && IsConnected)
                {
                    var bytes = Encoding.UTF8.GetBytes(heartbeatJson);
                    _stream.Write(bytes, 0, bytes.Length);
                    lock (_presenceLock) _lastPresenceSent = isBallDetected;
                    Info($"[GSPro4OSP] Sent heartbeat (Ready={isReady}) to GSPro.");
                }
            }
            catch (Exception ex)
            {
                Warning($"[GSPro4OSP] Failed to send heartbeat: {ex.Message}");
            }
        }

        // NOTE: SendSetShotMode / SendSetHandedness are now *manual* tools.
        // Bridge no longer calls them; they exist only for explicit use if needed.
        public static void SendSetShotMode(ShotMode mode)
        {
            if (_stream == null || !IsConnected)
            {
                Warning($"[GSPro4OSP] SendSetShotMode({mode}) skipped (not connected).");
                return;
            }
            var isBallDetected = OpenSkyPlus2Api.GetInstance().LaunchMonitor?.IsBallDetected ?? false;
            var request = new
            {
                APIversion = "1",
                DeviceID = "GsPro4Osp",
                Units = "Yards",
                ShotDataOptions = new
                {
                    ContainsBallData = false,
                    ContainsClubData = false,
                    IsHeartBeat = false,
                    LaunchMonitorIsReady = _lastMonitorReadyState,
                    LaunchMonitorBallDetected = isBallDetected
                },
                Command = "SetShotMode",
                Payload = new
                {
                    ShotMode = (mode == ShotMode.Putting ? "Putting" : "Normal")
                }
            };

            var opts = new JsonSerializerOptions
            {
                DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
                WriteIndented = false
            };

            string json = JsonSerializer.Serialize(request, opts) + "\n";
            Info($"[GSPro4OSP] -> Sent full shot mode change JSON:\n{json.Trim()}");
            _stream.Write(Encoding.UTF8.GetBytes(json), 0, Encoding.UTF8.GetByteCount(json));
            lock (_presenceLock) _lastPresenceSent = isBallDetected;
        }

        public static void SendSetHandedness(Handedness hand)
        {
            if (_stream == null || !IsConnected)
            {
                Warning($"[GSPro4OSP] SetHandedness({hand}) skipped (not connected).");
                return;
            }

            var request = new
            {
                APIversion = "1",
                DeviceID = "GsPro4Osp",
                Units = "Yards",
                ShotDataOptions = new
                {
                    ContainsBallData = false,
                    ContainsClubData = false,
                    IsHeartBeat = false,
                    LaunchMonitorIsReady = _lastMonitorReadyState,
                },
                Command = "SetHandedness",
                Payload = new
                {
                    Handed = hand == Handedness.LeftHanded ? "Left" : "Right"
                }
            };

            var opts = new JsonSerializerOptions
            {
                DefaultIgnoreCondition = JsonIgnoreCondition.WhenWritingNull,
                WriteIndented = false
            };

            string json = JsonSerializer.Serialize(request, opts) + "\n";
            Info($"[GSPro4OSP] -> Sent full handedness change JSON:\n{json.Trim()}");
            _stream.Write(Encoding.UTF8.GetBytes(json), 0, Encoding.UTF8.GetByteCount(json));
        }
        private sealed class PendingPlayerInfo201
        {
            public string? Handed;
            public string? Club;
            public float Distance;
            public int Sequence;
        }

        private static readonly object _playerInfo201Lock = new();
        private static PendingPlayerInfo201? _pendingPlayerInfo201;
        private static readonly System.TimeSpan PlayerInfo201Debounce = System.TimeSpan.FromSeconds(2);

        private static void HandlePlayerInfo201Coalesced(GsProResponse response)
        {
            var player = response.Player;
            if (player == null)
                return;

            var handed = player.Handed;
            var club = player.Club;
            var distance = (float)(player.DistanceToTarget ?? 0);

            // Don’t bother if there’s nothing actionable.
            if (string.IsNullOrEmpty(handed) && (string.IsNullOrEmpty(club) || distance <= 0f))
                return;

            int seq;
            PendingPlayerInfo201 snapshotForTask;

            lock (_playerInfo201Lock)
            {
                _pendingPlayerInfo201 ??= new PendingPlayerInfo201();
                _pendingPlayerInfo201.Handed = handed;
                _pendingPlayerInfo201.Club = club;
                _pendingPlayerInfo201.Distance = distance;
                _pendingPlayerInfo201.Sequence++;

                seq = _pendingPlayerInfo201.Sequence;

                snapshotForTask = new PendingPlayerInfo201
                {
                    Handed = _pendingPlayerInfo201.Handed,
                    Club = _pendingPlayerInfo201.Club,
                    Distance = _pendingPlayerInfo201.Distance,
                    Sequence = _pendingPlayerInfo201.Sequence
                };
            }

            Info($"[GSPro4OSP] Scheduled coalesced 201 update seq={seq}, " +
                 $"club={snapshotForTask.Club}, dist={snapshotForTask.Distance:0.00}m, " +
                 $"handed={snapshotForTask.Handed ?? "null"}");

            
            Task.Run(async () =>
            {
                try
                {
                    await Task.Delay(PlayerInfo201Debounce).ConfigureAwait(false);

                    PendingPlayerInfo201? final;
                    lock (_playerInfo201Lock)
                    {
                        // If another 201 arrived after this one, bail out.
                        if (_pendingPlayerInfo201 == null || _pendingPlayerInfo201.Sequence != seq)
                            return;

                        final = new PendingPlayerInfo201
                        {
                            Handed = _pendingPlayerInfo201.Handed,
                            Club = _pendingPlayerInfo201.Club,
                            Distance = _pendingPlayerInfo201.Distance,
                            Sequence = _pendingPlayerInfo201.Sequence
                        };
                    }

                    if (final == null)
                        return;

                    
                    MainThreadInvoker.RunCritical(() =>
                    {
                        
                        if (!string.IsNullOrEmpty(final.Handed))
                        {
                            CheckPlayerHandedness(final.Handed);
                        }
                                                
                        if (!string.IsNullOrEmpty(final.Club) && final.Distance > 0f)
                        {
                            UpdateDistanceToTargetAndPutting(final.Club, final.Distance);

                            var normalizedClub = ClubKeyNormalizer.Normalize(final.Club);
                            OpenSkyPlus2Api.SetCurrentClub(normalizedClub);

                            OpenSkyPlus2Api.GetInstance().ReadyForNextShot();
                        }
                    }, "G4O - 201");
                }
                catch (System.Exception ex)
                {
                    Warning($"[GSPro4OSP] Coalesced 201 handler failed: {ex.Message}");
                }
            });
        }
        // ---- DATA MODELS ----
        public class GsProResponse
        {
            [JsonPropertyName("Code")]
            public int? Code { get; set; }

            [JsonPropertyName("Message")]
            public string? Message { get; set; }

            [JsonPropertyName("Player")]
            public PlayerData? Player { get; set; }
        }

        public class PlayerData
        {
            [JsonPropertyName("Handed")]
            public string? Handed { get; set; }

            [JsonPropertyName("Club")]
            public string? Club { get; set; }

            [JsonPropertyName("DistanceToTarget")]
            public float? DistanceToTarget { get; set; }

            [JsonPropertyName("Surface")]
            public string? Surface { get; set; }
        }

        public class GsProRequest
        {
            [JsonPropertyName("APIversion")]
            public string APIversion { get; set; } = "1";

            [JsonPropertyName("DeviceID")]
            public string DeviceID { get; set; } = "GsPro4Osp";

            [JsonPropertyName("Units")]
            public string Units { get; set; } = "Yards";

            [JsonPropertyName("ShotNumber")]
            public int ShotNumber { get; set; }

            [JsonPropertyName("BallData")]
            public BallData? BallData { get; set; }

            [JsonPropertyName("ClubData")]
            public ClubData? ClubData { get; set; }

            [JsonPropertyName("ShotDataOptions")]
            public ShotDataOptions ShotDataOptions { get; set; } = new();
        }

        public class BallData
        {
            [JsonPropertyName("Speed")]
            public float? Speed { get; set; }

            [JsonPropertyName("SpinAxis")]
            public float? SpinAxis { get; set; }

            [JsonPropertyName("TotalSpin")]
            public float? TotalSpin { get; set; }

            [JsonPropertyName("BackSpin")]
            public float? BackSpin { get; set; }

            [JsonPropertyName("SideSpin")]
            public float? SideSpin { get; set; }

            [JsonPropertyName("HLA")]
            public float? HLA { get; set; }

            [JsonPropertyName("VLA")]
            public float? VLA { get; set; }

            [JsonPropertyName("CarryDistance")]
            public float? CarryDistance { get; set; }
        }

        public class ClubData
        {
            [JsonPropertyName("Speed")]
            public float? Speed { get; set; }

            [JsonPropertyName("AngleOfAttack")]
            public float? AngleOfAttack { get; set; }

            [JsonPropertyName("FaceToTarget")]
            public float? FaceToTarget { get; set; }

            [JsonPropertyName("Lie")]
            public float? Lie { get; set; }

            [JsonPropertyName("Loft")]
            public float? Loft { get; set; }

            [JsonPropertyName("Path")]
            public float? Path { get; set; }

            [JsonPropertyName("SpeedAtImpact")]
            public float? SpeedAtImpact { get; set; }

            [JsonPropertyName("VerticalFaceImpact")]
            public float? VerticalFaceImpact { get; set; }

            [JsonPropertyName("HorizontalFaceImpact")]
            public float? HorizontalFaceImpact { get; set; }

            [JsonPropertyName("ClosureRate")]
            public float? ClosureRate { get; set; }

            [JsonPropertyName("DynamicLoft")]
            public float? DynamicLoft { get; set; }

            [JsonPropertyName("SmashFactor")]
            public float? SmashFactor { get; set; }
        }

        public class ShotDataOptions
        {
            [JsonPropertyName("ContainsBallData")]
            public bool ContainsBallData { get; set; }

            [JsonPropertyName("ContainsClubData")]
            public bool ContainsClubData { get; set; }

            [JsonPropertyName("LaunchMonitorIsReady")]
            public bool? LaunchMonitorIsReady { get; set; }

            [JsonPropertyName("LaunchMonitorBallDetected")]
            public bool? LaunchMonitorBallDetected { get; set; }

            [JsonPropertyName("IsHeartBeat")]
            public bool? IsHeartBeat { get; set; }
        }
    }
}
