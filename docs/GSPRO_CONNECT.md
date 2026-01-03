# GSPro Open Connect API - Implementation Guide

This document captures everything we learned about building a high-quality connector for GSPro golf simulator using the Open Connect API v1.

## Overview

GSPro (Golf Simulator Pro) accepts shot data from launch monitors via TCP socket connection. The Open Connect API v1 is a simple JSON-based protocol that allows custom launch monitor integration.

## Connection Details

| Property | Value |
|----------|-------|
| Protocol | TCP Socket |
| Default Port | 921 |
| Message Format | JSON (no newline delimiter) |
| Response Format | JSON |

## Critical Implementation Details

### 1. Socket Configuration

The socket setup is critical for reliable communication:

```python
import socket

# Use create_connection for cleaner handling
sock = socket.create_connection((host, port), timeout=5.0)

# CRITICAL: Set TCP_NODELAY to disable Nagle's algorithm
# This ensures messages are sent immediately, not buffered
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)

# Set timeout for recv operations
sock.settimeout(5.0)
```

**Key Points:**
- Use `socket.create_connection()` instead of `socket.socket()` + `connect()` for cleaner handling
- **Always set `TCP_NODELAY`** - without this, messages may be buffered and delayed
- Set timeouts after connection, not before

### 2. Message Format

Messages are JSON objects sent directly over TCP. **No newline delimiter needed.**

```python
import json

message = {
    "DeviceID": "My Launch Monitor",
    "Units": "Yards",
    "ShotNumber": 1,
    "APIversion": "1",
    "BallData": { ... },
    "ClubData": { ... },
    "ShotDataOptions": { ... }
}

# Send as JSON bytes - NO newline at the end
json_data = json.dumps(message)
sock.sendall(json_data.encode('utf-8'))
```

### 3. Response Handling

GSPro's response behavior varies by message type:

| Message Type | Response Behavior |
|--------------|-------------------|
| Shot Data | Responds with status code |
| Heartbeat | **No response** |
| Status Update | **No response** |

**Critical: Don't wait for responses to heartbeats/status messages!**

```python
def send_message(self, message, expect_response=True):
    # Clear any buffered data first
    self._clear_buffer()

    # Send message
    sock.sendall(json.dumps(message).encode('utf-8'))

    if not expect_response:
        return None  # Don't block waiting for response

    # Only wait for response on shot data
    response_data = sock.recv(4096)
    return json.loads(response_data)
```

### 4. Buffer Management

GSPro may buffer responses and send them later, causing JSON parsing errors:

```
{"Code":200,"Message":"OK"}{"Code":200,"Message":"OK"}
```

**Solution: Clear buffer before sending and parse only first JSON object**

```python
import json

def _clear_buffer(self):
    """Clear any stale data in the receive buffer."""
    self._socket.setblocking(False)
    try:
        while True:
            stale = self._socket.recv(4096)
            if not stale:
                break
    except BlockingIOError:
        pass  # Buffer is empty
    finally:
        self._socket.setblocking(True)

def _parse_response(self, data: bytes):
    """Parse only the first JSON object from response."""
    response_str = data.decode('utf-8')
    decoder = json.JSONDecoder()
    response_json, _ = decoder.raw_decode(response_str)
    return response_json
```

### 5. Graceful Shutdown

GSPro doesn't handle abrupt disconnections well. Always disconnect properly:

```python
def disconnect(self):
    if self._socket:
        try:
            self._socket.close()
        except Exception:
            pass
        self._socket = None
```

Register shutdown handlers for your application:
- NiceGUI: `app.on_shutdown(cleanup_function)`
- Signal handlers: SIGINT (Ctrl+C), SIGTERM
- atexit handler as fallback

## Message Structures

### Shot Data Message

```json
{
    "DeviceID": "GC2 Connect",
    "Units": "Yards",
    "ShotNumber": 1,
    "APIversion": "1",
    "BallData": {
        "Speed": 145.5,
        "SpinAxis": -7.35,
        "TotalSpin": 2650,
        "BackSpin": 2480,
        "SideSpin": -320,
        "HLA": 1.5,
        "VLA": 11.8,
        "CarryDistance": 0
    },
    "ClubData": {
        "Speed": 105.2,
        "AngleOfAttack": -4.2,
        "FaceToTarget": 1.5,
        "Lie": 0.5,
        "Loft": 15.2,
        "Path": 3.1,
        "SpeedAtImpact": 105.2,
        "VerticalFaceImpact": 0,
        "HorizontalFaceImpact": 0,
        "ClosureRate": 0
    },
    "ShotDataOptions": {
        "ContainsBallData": true,
        "ContainsClubData": true,
        "LaunchMonitorIsReady": true,
        "LaunchMonitorBallDetected": true,
        "IsHeartBeat": false
    }
}
```

### Heartbeat Message

```json
{
    "DeviceID": "GC2 Connect",
    "Units": "Yards",
    "ShotNumber": 0,
    "APIversion": "1",
    "BallData": { ... },
    "ClubData": { ... },
    "ShotDataOptions": {
        "ContainsBallData": false,
        "ContainsClubData": false,
        "LaunchMonitorIsReady": true,
        "LaunchMonitorBallDetected": true,
        "IsHeartBeat": true
    }
}
```

### Status Update Message

Used to indicate launch monitor readiness and ball detection:

```json
{
    "DeviceID": "GC2 Connect",
    "Units": "Yards",
    "ShotNumber": 0,
    "APIversion": "1",
    "BallData": { ... },
    "ClubData": { ... },
    "ShotDataOptions": {
        "ContainsBallData": false,
        "ContainsClubData": false,
        "LaunchMonitorIsReady": true,
        "LaunchMonitorBallDetected": false,
        "IsHeartBeat": false
    }
}
```

## Response Codes

| Code | Meaning |
|------|---------|
| 200 | Success |
| 201 | Success with player info |
| 5xx | Error |

### Response with Player Info

GSPro sends player information in responses:

```json
{
    "Code": 201,
    "Message": "Player info",
    "Player": {
        "Handed": "RH",
        "Club": "DR",
        "DistanceToTarget": 450
    }
}
```

## Units

All values should be sent in these units:

| Field | Unit | Notes |
|-------|------|-------|
| Ball Speed | mph | Send as mph directly |
| Club Speed | mph | Send as mph directly |
| Spin | rpm | Total, back, and side spin |
| Spin Axis | degrees | Calculated from back/side spin |
| Launch Angle (VLA) | degrees | Vertical launch angle |
| HLA | degrees | Horizontal launch angle |
| Path | degrees | Club path |
| Face | degrees | Face to target |
| Attack Angle | degrees | Angle of attack |

**Note:** The GSPro Open Connect debug window may display incorrect values (appears to apply a unit conversion), but the actual simulator uses values correctly.

## Common Pitfalls

### 1. Waiting for Heartbeat Responses

**Problem:** Connection hangs or times out
**Cause:** Waiting for response to heartbeat/status messages
**Solution:** Set `expect_response=False` for non-shot messages

### 2. Buffered/Concatenated Responses

**Problem:** "Invalid JSON" or "Extra data" errors
**Cause:** Multiple responses buffered together
**Solution:** Clear buffer before sending, parse only first JSON object

### 3. Nagle's Algorithm Delays

**Problem:** Messages appear delayed or batched
**Cause:** TCP Nagle's algorithm buffering small packets
**Solution:** Set `TCP_NODELAY` socket option

### 4. Abrupt Disconnection

**Problem:** GSPro shows "disconnected" state incorrectly
**Cause:** Socket closed without proper cleanup
**Solution:** Implement shutdown handlers, close socket gracefully

### 5. Unit Confusion

**Problem:** Values displayed incorrectly in GSPro
**Cause:** Wrong unit assumptions (m/s vs mph)
**Solution:** Send ball speed in mph (not m/s)

## Reference Implementations

These implementations were studied for protocol details:

- [MLM2PRO-GSPro-Connector](https://github.com/springbok/MLM2PRO-GSPro-Connector)
- [gspro-connect](https://github.com/joebockhorst/gspro-connect)
- gc2_to_TGC (reverse engineered Windows application)

## Testing

### Mock GSPro Server

For development without GSPro:

```python
# tools/mock_gspro_server.py
import socket
import json

def run_mock_server(host='0.0.0.0', port=921):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind((host, port))
        s.listen(1)

        while True:
            conn, addr = s.accept()
            with conn:
                data = conn.recv(4096)
                message = json.loads(data)

                # Send response only for shot data
                if message.get('ShotDataOptions', {}).get('ContainsBallData'):
                    response = {"Code": 200, "Message": "OK"}
                    conn.sendall(json.dumps(response).encode())
```

### Testing Checklist

- [ ] Connection establishes successfully
- [ ] Initial heartbeat sent on connect
- [ ] Shot data receives 200 response
- [ ] Heartbeats don't block waiting for response
- [ ] Status updates don't block waiting for response
- [ ] Buffered responses handled correctly
- [ ] Graceful shutdown disconnects properly
- [ ] Ball speed displays correctly in GSPro

## Summary

Building a reliable GSPro connector requires attention to:

1. **Socket configuration**: TCP_NODELAY, proper timeouts
2. **Response handling**: Don't wait for heartbeat/status responses
3. **Buffer management**: Clear stale data, parse first JSON only
4. **Shutdown handling**: Register cleanup handlers for graceful disconnect
5. **Units**: Send speeds in mph

Following these guidelines will produce a high-quality, reliable GSPro integration.
