# GSPro Open Connect API — TCP Protocol (v1)

Wire-level specification of the connector ↔ GSPro integration for **GSPro v1.x**. GSPro is a Windows golf-simulator package; it exposes a TCP "Open Connect API" so third-party launch monitors can feed shot data into a round.

This document is implementation-language-agnostic. It describes the protocol from the client (launch-monitor connector) perspective.

> Source: this document was derived from two pieces of evidence:
> 1. `docs/GsProApi.cs` — the OpenSkyPlus2 / GSPro4OSP reference connector source, which is the closest thing to an official wire spec.
> 2. The working `src/gc2_connect/gspro/client.py` integration in this repository.
>
> Earlier revisions of this document mixed in details from a different launch-monitor's connector (different inbound discriminator, different sign conventions, no `IsHeartBeat`, split ball/club messages). Those details did **not** apply to GSPro v1.x and have been removed. If you find newer/different behavior in production GSPro, prefer reality over this document.

## 1. Transport

| Property | Value |
|---|---|
| Protocol | Plain TCP (no TLS) |
| Default host/port | `127.0.0.1:921` (localhost) |
| Role | GSPro listens, the connector dials |
| Framing | JSON objects, `\n`-terminated |

**Socket setup (client-side):**

- **`TCP_NODELAY`**: enable. GSPro relies on prompt delivery of small JSON messages; Nagle batching introduces visible lag.
- **`SO_KEEPALIVE`**: enable, ~30 s idle. GSPro does not send application-level heartbeats *to* the client, so OS-level keepalive is the only reliable way to detect a half-open connection (e.g. GSPro process killed without a FIN).
  - macOS: `setsockopt(IPPROTO_TCP, TCP_KEEPALIVE, 30)`.
  - Linux: `TCP_KEEPIDLE=30`, `TCP_KEEPINTVL=10`, `TCP_KEEPCNT=3` (~60 s to detect a dead peer).
- **Read pattern**: a long-running reader task that consumes whatever GSPro sends. Do not synchronously `recv` after each send expecting an ack — see §6.

## 2. Message framing

JSON objects are carried over the TCP stream.

### Outbound (client → GSPro)

Every outbound message is one JSON object followed by a single newline byte (`\n`, `0x0A`):

```text
{"DeviceID":"GC2 Connect","APIversion":"1",...}\n
```

The newline is required. The reference implementation (`docs/GsProApi.cs`) appends `+ "\n"` to every write (shot data, heartbeat, status update, command). Without it, two messages sent in quick succession can land in the same TCP segment and the second is dropped by GSPro's line-oriented reader. Pretty-printed JSON is fine as long as exactly one `\n` follows the closing `}`.

### Inbound (GSPro → client)

GSPro is **mostly** line-oriented but not strictly so:

- Most messages are one JSON object terminated by `\n` or `\r\n`. The reference implementation splits inbound bytes on `'\n'` and `'\r'`.
- During the initial handshake, GSPro may send the bare string `GSPro ready` (no JSON envelope). Treat this as equivalent to a `Code:202` match-start signal (see §4.2).
- Defensive parsing: accumulate inbound bytes, try `JSON.parse` on each line; if a line fails to parse and contains `GSPro ready`, treat it as the bare handshake; otherwise log and skip. A balanced-brace `raw_decode` parser is a stronger fallback if GSPro ever batches.

The reference client reads up to 4096 bytes at a time and processes whatever lines are complete, retaining any trailing partial line for the next read.

## 3. Reconnection policy

GSPro can disappear mid-session (process restart, computer sleep, user close). Recommended client behavior:

- Initial backoff: 5 seconds.
- Backoff doubles on each failed attempt, capped at 60 seconds.
- **Retry indefinitely.** The reference (`GsProApi.cs` `ConnectLoopAsync`) treats `MaxRetries < 0` as unbounded and that is the default. The user cancels manually via "Disconnect".
- On reconnect, the client resets its `ShotNumber` to 0. GSPro tracks shots independently and accepts the reset.

The reconnect task runs concurrently with everything else; it must not block I/O paths.

## 4. Inbound messages (GSPro → client)

After the initial handshake, all post-handshake inbound messages are JSON objects discriminated by a top-level integer `Code` field:

```jsonc
{ "Code": <int>, "Message": "<string>", "Player": { /* optional */ } }
```

Known codes:

### 4.1 `Code: 200` — Generic OK

Acknowledgement of a shot data message. Informational; payload typically `{"Code":200,"Message":"OK"}` or similar. Acks are **not** flow control — if you miss one, just keep sending. GSPro does not retry or NACK.

### 4.2 `Code: 202` — GSPro ready / match started

```json
{"Code": 202, "Message": "GSPro ready"}
```

Sent when GSPro is ready to receive shot data (player teed off, returned from menu, or session start). May also arrive as the **bare string** `GSPro ready` (no JSON envelope) during initial handshake — treat it identically.

**Required action:** arm the launch monitor (enable ball detection), start heartbeats (§6.2).

### 4.3 `Code: 201` — Player information

```json
{
  "Code": 201,
  "Message": "Player info",
  "Player": {
    "Handed": "RH",
    "Club": "I7",
    "DistanceToTarget": 145.2,
    "Surface": "Fairway"
  }
}
```

Sent when the active player, their selected club, or distance-to-target changes. After delivering this message GSPro is effectively re-armed (similar in effect to `202`).

`Player` field semantics:

- `Handed` — `"RH"` (right-handed), `"LH"` (left-handed). Other values fall back to right-handed.
- `Club` — two-letter club code (see §4.3.1).
- `DistanceToTarget` — number, meters. Used by client to decide putting/short-chip mode.
- `Surface` — optional string (e.g. `"Fairway"`, `"Tee"`, `"Rough"`, `"Green"`).

The reference debounces a burst of 201s within ~2 s to avoid thrashing on rapid updates.

#### 4.3.1 Club code dictionary

| Code | Description |
|---|---|
| `DR` | Driver |
| `W2`–`W7` | 2- through 7-wood |
| `H2`–`H7` | 2- through 7-hybrid |
| `I1`–`I9` | 1- through 9-iron |
| `PW` | Pitching wedge |
| `AW` | Approach (gap) wedge |
| `GW` | Gap wedge |
| `SW` | Sand wedge |
| `LW` | Lob wedge |
| `PT` | Putter |

Unknown codes should be passed through to the UI as "unmapped" rather than rejected — new clubs may appear in future GSPro versions.

### 4.4 `Code: 203` — Round/match ended

```json
{"Code": 203, "Message": "GSPro round ended"}
```

The current round/match is over. Stop heartbeats; the launch monitor can stay connected for the next round.

### 4.5 `Code: 5xx` — Error

GSPro signalled an error processing a prior message. Log and continue; do not assume the connection is broken.

### 4.6 Other codes

Treat any unrecognized `Code` value as informational and log it. The protocol may grow.

## 5. Outbound messages (client → GSPro)

There is exactly **one outbound JSON schema** (`GsProRequest`). All variations — shot, heartbeat, status — share the same envelope; what differs is the `ShotDataOptions` flags and whether `BallData` / `ClubData` carry real measurements.

### 5.1 Full schema

```jsonc
{
  "DeviceID":   "GC2 Connect",
  "APIversion": "1",
  "Units":      "Yards",
  "ShotNumber": 14,
  "BallData": {
    "Speed":         145.5,
    "SpinAxis":       -3.5,
    "TotalSpin":    2800.0,
    "BackSpin":     2790.0,
    "SideSpin":     -170.0,
    "HLA":             1.2,
    "VLA":            12.5,
    "CarryDistance":   0.0
  },
  "ClubData": {
    "Speed":                102.0,
    "AngleOfAttack":         -1.5,
    "FaceToTarget":           0.8,
    "Lie":                    0.0,
    "Loft":                  13.2,
    "Path":                   1.1,
    "SpeedAtImpact":        102.0,
    "VerticalFaceImpact":     2.0,
    "HorizontalFaceImpact":  -1.0,
    "ClosureRate":            0.0,
    "DynamicLoft":           13.2,
    "SmashFactor":            1.43
  },
  "ShotDataOptions": {
    "ContainsBallData":          true,
    "ContainsClubData":          true,
    "LaunchMonitorIsReady":      true,
    "LaunchMonitorBallDetected": true,
    "IsHeartBeat":               false
  }
}
```

### 5.2 Top-level fields

| Field | Type | Notes |
|---|---|---|
| `DeviceID` | string | Free-form identifier shown in GSPro logs. Choose something stable per integration. |
| `APIversion` | string | `"1"`. Only one version exists. |
| `Units` | string | `"Yards"`. GSPro normalizes regardless of choice, but `"Yards"` is conventional. |
| `ShotNumber` | integer | Monotonic per TCP session. Incremented once per real shot. On reconnect, reset to 0. |
| `BallData` | object | Optional. Present iff `ContainsBallData=true` *or* you want to send placeholder values. Reference includes an empty object even when not used. |
| `ClubData` | object | Optional. Same convention as `BallData`. |
| `ShotDataOptions` | object | Required. See §5.5. |

### 5.3 `BallData` fields

All values numeric. Coordinate conventions: HLA positive = right of target, VLA positive = up. Spin axis/side spin signs match GSPro's native convention (no negation needed) when sourced from the GC2's native field names.

| Field | Unit | Notes |
|---|---|---|
| `Speed` | mph | Ball speed at separation. Convert from m/s with `× 2.23694` if your device reports m/s. |
| `SpinAxis` | degrees | Positive = right-axis tilt (fade for RH). |
| `TotalSpin` | RPM | |
| `BackSpin` | RPM | |
| `SideSpin` | RPM | Positive = right (fade for RH). |
| `HLA` | degrees | Horizontal launch angle. |
| `VLA` | degrees | Vertical launch angle. |
| `CarryDistance` | yards | Optional; `0` if not estimated client-side. |

### 5.4 `ClubData` fields

All numeric. Fields you don't measure should be `0.0` — GSPro treats `0` as "missing" and back-fills from its own physics model.

| Field | Unit | Notes |
|---|---|---|
| `Speed` | mph | Club head speed. |
| `AngleOfAttack` | degrees | Positive = up. |
| `FaceToTarget` | degrees | Positive = open (right of target for RH). |
| `Lie` | degrees | Dynamic lie angle. |
| `Loft` | degrees | Dynamic loft at impact. |
| `Path` | degrees | Positive = in-to-out (right of target for RH). |
| `SpeedAtImpact` | mph | Usually equal to `Speed`. |
| `VerticalFaceImpact` | mm | Sole-to-crown impact position. |
| `HorizontalFaceImpact` | mm | Heel-to-toe impact position. |
| `ClosureRate` | deg/s | |
| `DynamicLoft` | degrees | Optional; often equals `Loft`. |
| `SmashFactor` | unitless | Optional. |

### 5.5 `ShotDataOptions` flags

| Flag | Type | Meaning |
|---|---|---|
| `ContainsBallData` | bool | `true` if `BallData` carries a real measurement. |
| `ContainsClubData` | bool | `true` if `ClubData` carries real measurements. |
| `LaunchMonitorIsReady` | bool | "I'm armed and ready to detect a shot." |
| `LaunchMonitorBallDetected` | bool | "There's a ball in front of me right now." |
| `IsHeartBeat` | bool | `true` for periodic heartbeat pings; `false` for shots and event-driven status updates. |

`LaunchMonitorIsReady` should typically reflect **both** hardware readiness (e.g. green light on the launch monitor) **and** GSPro match state (saw a `Code:202`). Reporting `IsReady=true` while no match is active confuses GSPro.

## 6. Message patterns

The reference connector emits three distinct outbound shapes.

### 6.1 Shot data (new swing)

Emitted once per swing, after the device has produced ball *and* club metrics (or ball-only if no HMT). **Increment `ShotNumber` before sending.**

```jsonc
{
  "DeviceID": "GC2 Connect",
  "APIversion": "1",
  "Units": "Yards",
  "ShotNumber": 14,
  "BallData": { /* §5.3 */ },
  "ClubData": { /* §5.4, zeros if unavailable */ },
  "ShotDataOptions": {
    "ContainsBallData": true,
    "ContainsClubData": true,
    "LaunchMonitorIsReady": true,
    "LaunchMonitorBallDetected": false,
    "IsHeartBeat": false
  }
}
```

A single combined ball+club message is the standard. The GC2 protocol delivers ball and club in two USB packets within ~1 s of each other; the connector buffers ball, waits briefly for club, then emits one combined GSPro message. (Earlier protocol descriptions claimed separate ball-only and club-only emits were required — that does not match the reference and is not necessary.)

Expected ack: `{"Code":200,"Message":"..."}`. Informational; do not block waiting for it.

### 6.2 Heartbeat (periodic)

Emitted every ~6 s while a match is active. Confirms the connector is still alive and reports current readiness.

```jsonc
{
  "DeviceID": "GC2 Connect",
  "APIversion": "1",
  "Units": "Yards",
  "ShotDataOptions": {
    "ContainsBallData": false,
    "ContainsClubData": false,
    "LaunchMonitorIsReady": true,
    "LaunchMonitorBallDetected": false,
    "IsHeartBeat": true
  }
}
```

- Do **not** increment `ShotNumber` for heartbeats.
- `ShotNumber` may be omitted entirely (the reference omits it).
- No `BallData` / `ClubData` needed.
- GSPro does not respond to heartbeats — do not wait for an ack.

### 6.3 Status update (event-driven)

Emitted when launch-monitor readiness or ball-detection state changes (separate from the periodic heartbeat).

```jsonc
{
  "DeviceID": "GC2 Connect",
  "APIversion": "1",
  "Units": "Yards",
  "ShotDataOptions": {
    "ContainsBallData": false,
    "ContainsClubData": false,
    "LaunchMonitorIsReady": true,
    "LaunchMonitorBallDetected": true,
    "IsHeartBeat": false
  }
}
```

- Same skeleton as heartbeat but `IsHeartBeat=false`.
- GSPro does not respond. Do not wait.
- Use to inform GSPro the user has placed a ball, or the device has finished its post-shot cooldown.

### 6.4 Shutdown handshake

When the connector is disconnecting cleanly:

1. Stop the heartbeat timer.
2. Send one final status with `LaunchMonitorIsReady=false` and `IsHeartBeat=true`.
3. Wait ~250 ms for GSPro to process.
4. Close the socket.

This tells GSPro the launch monitor is going offline gracefully rather than disappearing.

## 7. Session lifecycle

Typical flow:

1. Connector dials `127.0.0.1:921`. Sets `TCP_NODELAY` and `SO_KEEPALIVE`.
2. Connector sends an initial heartbeat (`IsReady=false`, `IsHeartBeat=true`) to register.
3. Both sides idle until GSPro sends `GSPro ready` (bare or `Code:202`) or `Code:201` with player info.
4. Connector arms the launch monitor, starts the periodic heartbeat (§6.2), and may send a status update (§6.3) to confirm.
5. Player swings → launch monitor produces shot metrics → connector emits §6.1.
6. GSPro replies with a `Code:200` ack (informational), eventually followed by another `Code:201` for the next shot's player/club/distance context.
7. Steps 4–6 repeat for each shot until `Code:203` (round ended) or the user disconnects.

`ShotNumber` continues to climb for the duration of the TCP connection. On reconnect, the client resets `ShotNumber` to 0 — GSPro tracks shots independently and accepts the reset.

## 8. Error handling

| Condition | Handling |
|---|---|
| TCP connect fails | Apply backoff (§3) and retry. Surface state to UI. |
| TCP read returns 0 bytes | Peer closed. Disconnect locally and start reconnect. |
| Socket error during read or write | Same — disconnect and reconnect. |
| Read silence | Normal between events. SO_KEEPALIVE handles dead-peer detection. |
| Inbound JSON parse fails | If line contains `GSPro ready`, handle as `Code:202`. Otherwise log and skip the line. |
| Inbound message with unknown `Code` | Log and ignore. |
| Outbound write fails | Close socket, start reconnect. The shot/heartbeat is lost — GSPro does not retry. |
| GSPro sends `Code:5xx` | Log; connection is still healthy. |

Acks are **informational**, not flow control. Missing an ack is not a failure condition.

## 9. Implementing a new client — checklist

Minimum viable client:

1. Open TCP socket to `127.0.0.1:921` (configurable host/port). Set `TCP_NODELAY` and `SO_KEEPALIVE`.
2. Send initial heartbeat (`§6.2` shape with `IsReady=false`) to register.
3. Start a reader task: read line-by-line (or bytes with `raw_decode` fallback); dispatch by `Code`. Handle the bare `GSPro ready` handshake string.
4. On `Code:202` (or bare `GSPro ready`): arm the device, start the 6-second heartbeat timer, transition `IsReady` reporting to track real hardware state.
5. On `Code:201`: update internal player state (handedness, club, distance-to-target).
6. On `Code:203`: stop heartbeats; stay connected.
7. Maintain a `ShotNumber` integer. Increment **only** on emitting a shot data message (§6.1). Reset to 0 on reconnect.
8. On shot: emit §6.1 with one combined ball+club JSON, terminated by `\n`. Do not block on the ack.
9. On readiness/ball-detection state change: emit §6.3.
10. Implement the reconnect policy (§3) on any socket error.
11. On clean shutdown: emit final §6.4 status, sleep ~250 ms, close socket.

Things you can skip:

- `APIversion` switching — only `"1"` exists.
- Buffering acks — they have no functional effect.
- TLS / authentication — not part of the protocol.
- Sign flips on `SpinAxis` / `SideSpin` — GSPro's convention matches the GC2's native fields directly. If you see fade/draw inverted in GSPro, fix it in your device adapter, not in the GSPro outbound layer.
