Advice from GSPro Discord on disconnecting:

Unfortunately, there is not a packet to tell GSPro that you're disconnecting that I am aware of. This is a GSPro thing. They do not have an advertised way of a clean disconnect.

What you can do to "cleanly" shutdown the connection to GSPro:

Send a final heartbeat packet with `LaunchMonitorIsReady = false`

Flush.

Short delay (250 ms should be fine)

Then do something like this (which is what OpenSkyPlus2 does):

```public static void Disconnect()
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
}```

I am not sure what language you are writing in, but this is for Unity (C#). Like I said, they do not have a clean shutdown, which is something I have requested. Seems they go off of a timeout model, rather than any kind of clean disconnect. So, you telling them the LM is not ready starts that process.
