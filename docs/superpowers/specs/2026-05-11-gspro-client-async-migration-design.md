# GSPro Client Modernization — Design

**Status:** Design, pending implementation
**Date:** 2026-05-11
**Author:** Samiur + assistant

## Context

The GSPro TCP client (`src/gc2_connect/gspro/client.py`) was authored around `socket.socket` with sync I/O wrapped in `asyncio.run_in_executor`. It works in production today, but three operational gaps have surfaced when compared against the OpenSkyPlus2 reference (`docs/GsProApi.cs`, the closest thing to an official wire spec):

1. **No newline framing on outbound writes.** The reference appends `\n` to every JSON write. Our client used to (commit `76ff60d`) but a later refactor dropped it. Today this is benign because each `sendall` typically lands as one TCP packet, but it's not defensive against any future buffering, batched writes, or proxy.
2. **No `SO_KEEPALIVE`.** If GSPro is hard-killed without a FIN, the reader loop sits silent forever and the existing reconnect path never triggers.
3. **Reconnect window is short.** Current `ReconnectionManager` defaults give up after 5 attempts (1s → 16s, ~31s total). The user wants reconnect to keep trying indefinitely (matching the reference, where `MaxRetries < 0` means infinite).

The reader loop also has a code-smell wart: it flips the socket between blocking and non-blocking on every iteration and busy-polls with `await asyncio.sleep(0.1)` on `BlockingIOError`. Cleanly fixed by migrating to `asyncio.open_connection`.

A doc — `docs/GSPRO_TCP_PROTOCOL.md` — was dropped into the repo from a different launch-monitor's connector and contained wire-format claims (Message-string discriminator, no `IsHeartBeat`, sign-flipped spin) that contradict the actual GSPro v1.x protocol. The doc has been rewritten to describe the real wire, and is **not** the source of this design. The genuine source is `docs/GsProApi.cs` plus the working Python implementation.

## Goals

1. Adopt `\n` newline framing on every outbound JSON write.
2. Enable `SO_KEEPALIVE` with platform-appropriate timing on connect.
3. Migrate the client to `asyncio.open_connection` (StreamReader/StreamWriter), eliminating the sync-socket + `run_in_executor` pattern.
4. Make `ReconnectionManager` support infinite retries and use it for GSPro with a 5s→60s capped exponential backoff.
5. Keep the wire format and message semantics exactly as they are today (Code-based responses, `IsHeartBeat` flag, current sign conventions, `CarryDistance`, combined ball+club shot message).
6. Preserve the existing reconnect-via-`GSProConnectionManager` flow; UI cancels via the existing Disconnect action.

## Non-goals

- Changing GC2 / USB-side code or its reconnect policy.
- Changing the GSPro wire format (signs, fields, message split, etc.).
- Adding new UI affordances. The existing Reconnecting state + Disconnect button handle cancellation.
- Migrating to `pydantic` for the GSPro models. The current dataclass models stay.

## Design

### 1. Wire-format changes (small, isolated)

In `GSProClient._send_message`:

- Append `b"\n"` to every encoded payload: `payload = json.dumps(...).encode("utf-8") + b"\n"`.
- Same change applies to `_send_shutdown_heartbeat` and any other outbound write.

No other wire-format changes.

### 2. `GSProClient` async migration

`GSProClient` replaces sync sockets with `asyncio.StreamReader` / `StreamWriter`.

**Connection.** `async def connect(self) -> bool`:

```
reader, writer = await asyncio.wait_for(
    asyncio.open_connection(self.host, self.port),
    timeout=5.0,
)
sock = writer.get_extra_info("socket")
self._configure_socket(sock)         # TCP_NODELAY, SO_KEEPALIVE — see §3
self._reader, self._writer = reader, writer
self._connected = True
await self._send_initial_heartbeat()  # registration
self._start_reader_loop()
return True
```

On failure (`asyncio.TimeoutError`, `OSError`): `self._connected = False`, log, return `False`. Caller (the `GSProConnectionManager` + `ReconnectionManager`) handles retry.

**Send path.** All sends become `async`:

- `async def send_shot(self, shot: GC2ShotData) -> None` — increments `_shot_number`, builds the message, calls `_send_message`. **Returns `None`.** Shot acks arrive asynchronously through the reader loop and fire response callbacks; `send_shot` no longer waits inline.
- `async def send_heartbeat(self) -> None` — unchanged semantics.
- `async def send_status(self, status: GC2BallStatus) -> None` — unchanged semantics.

`_send_message` becomes async:

```
async def _send_message(self, message: GSProShotMessage) -> None:
    if not self._connected or self._writer is None:
        return
    payload = json.dumps(message.to_dict()).encode("utf-8") + b"\n"
    try:
        self._writer.write(payload)
        await self._writer.drain()
    except (ConnectionError, OSError) as e:
        logger.error(f"GSPro write failed: {e}")
        self._on_connection_lost(e)
```

`expect_response` parameter is removed. The pre-send "clear stale buffer" block is removed (no other path reads the socket — the dedicated reader task owns it).

**Reader loop.**

```
async def _reader_loop(self) -> None:
    buffer = b""
    while self._connected and self._reader is not None:
        try:
            chunk = await self._reader.read(4096)
        except (ConnectionError, OSError) as e:
            self._on_connection_lost(e)
            return
        if not chunk:                       # EOF — peer closed
            self._on_connection_lost(None)
            return
        buffer += chunk
        buffer = self._drain_buffer(buffer)
```

`_drain_buffer` extracts complete JSON objects from `buffer`:

1. Split on `\n` first (handles the common, line-terminated case).
2. For any line that fails to parse, attempt `JSONDecoder().raw_decode` over the accumulated buffer (handles the rare batched case, matches `GSPRO_TCP_PROTOCOL.md` §2).
3. Special case: a non-JSON line containing `"GSPro ready"` is synthesized into `{"Code": 202, "Message": "GSPro ready"}` (matches the GsProApi.cs handshake handling in its ReadLoop, lines 564–567).
4. Each successfully extracted object is passed to `_handle_response` (existing function — unchanged).
5. Returns any unparsed tail to be retained for the next read.

**Connection-lost path.** `_on_connection_lost(exc)`:

- Marks `self._connected = False`.
- Stops the heartbeat task (`_stop_heartbeat_timer`).
- Schedules `self._writer.close()` and discards `self._reader`.
- Notifies disconnect callbacks (`_notify_disconnect`). `GSProConnectionManager` listens for this and starts `ReconnectionManager.attempt_reconnect(self._client.connect)`.

**Disconnect.** `async def disconnect(self) -> None`:

1. Stop heartbeat task.
2. Stop reader task.
3. If still connected, send a shutdown heartbeat (`LaunchMonitorIsReady=False, IsHeartBeat=True`) and `await writer.drain()`.
4. `await asyncio.sleep(0.250)`.
5. `writer.close(); await writer.wait_closed()`.
6. Clear `_shot_number`, `_current_player`, `_connected = False`.

**Removed surface:** `connect_async`, `disconnect_async`, `send_shot_async`, `send_status_async`. The async methods *are* the API now.

**Heartbeat task.** No change in concept — `_heartbeat_loop` already does `await asyncio.sleep(...)` and calls `send_heartbeat`. With `send_heartbeat` now native async, the loop becomes:

```
async def _heartbeat_loop(self) -> None:
    while self._connected and self._match_started:
        await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
        if self._connected and self._match_started:
            await self.send_heartbeat()
```

`set_hardware_ready` and `_on_match_started` currently call `self.send_heartbeat()` directly. With `send_heartbeat` async, those sync call sites become:

```
asyncio.create_task(self.send_heartbeat())
```

This is fire-and-forget and matches the prior behavior (those callers didn't use the return value).

### 3. Keepalive and reconnection

**`_configure_socket(sock)`** in `GSProClient`:

```
sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
sock.setsockopt(socket.SOL_SOCKET,  socket.SO_KEEPALIVE, 1)
if sys.platform == "darwin":
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, 30)
elif sys.platform.startswith("linux"):
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE,  30)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, 10)
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT,    3)
```

`TCP_KEEPALIVE` is the macOS spelling; the Linux constants only exist on Linux. Guard with `hasattr(socket, "TCP_KEEPIDLE")` etc. to keep import-time safe across platforms.

**`ReconnectionManager` changes** (in `src/gc2_connect/utils/reconnect.py`):

- `max_retries: int | None = None` — `None` means infinite retries.
- The bounded-exit branch (`while attempt < self.max_retries ...`) becomes `while (self.max_retries is None or attempt < self.max_retries) and not self._cancelled`.
- The "after max attempts" log line and `FAILED` state only fire when `max_retries` is a positive int.
- `cancel()` semantics unchanged. The UI calls it via the existing Disconnect action.

**Defaults for GSPro** (in `services/connection_manager.py::GSProConnectionManager`):

```
self._reconnect_mgr = ReconnectionManager(
    max_retries=None,   # infinite
    base_delay=5.0,
    max_delay=60.0,
)
```

USB-side `ReconnectionManager` instantiation is **not** touched in this change.

### 4. API ripple

| Caller | Change |
|---|---|
| `services/connection_manager.py::GSProConnectionManager.send_status` | becomes `async def`; awaits `self._client.send_status(status)` |
| `services/connection_manager.py::GSProConnectionManager.send_shot` | already async; swap `send_shot_async` → `send_shot` |
| `services/shot_router.py:164` | swap `send_shot_async` → `send_shot` |
| `ui/app.py:~994` | `self._gspro_mgr.send_status(status)` → `await self._gspro_mgr.send_status(status)` (caller is already async) |
| `tests/conftest.py::gspro_client` | becomes `async def` with `@pytest.fixture` (pytest-asyncio is already configured `asyncio_mode = "auto"`); awaits `client.connect()` / `client.disconnect()` |
| `tests/unit/test_gspro_heartbeat.py` | tests that `patch.object(client, "send_heartbeat")` use `AsyncMock`; those tests become `async def` |

### 5. Tests

**Existing tests:** updated as above to track the API shape change.

**New tests (TDD — write before implementing the corresponding code):**

- `test_reconnect_manager_supports_infinite_retries` — `max_retries=None` does not exit on attempt count; only `cancel()` ends the loop.
- `test_gspro_client_appends_newline_to_writes` — `MockGSProServer` records raw bytes; assert each captured message ends with `\n`.
- `test_gspro_client_enables_keepalive` — after `await client.connect()`, the underlying socket has `SO_KEEPALIVE == 1`.
- `test_gspro_client_reader_loop_handles_dropped_connection` — mock server abruptly closes; client transitions to disconnected and fires disconnect callback.
- `test_send_shot_returns_none_and_acks_via_callback` — `send_shot` returns `None`; the `Code:200` ack arrives via the existing response callback.
- `test_gspro_client_reconnects_forever_with_capped_backoff` — instrument `ReconnectionManager.get_delay_for_attempt` returns `5, 10, 20, 40, 60, 60, …`.
- `test_gspro_client_handshakes_with_bare_gspro_ready` — mock server sends the bare string `"GSPro ready\n"` (not JSON); client treats as `Code:202`, fires match-started callback.

**Manual end-to-end smoke** (after code merges green):

1. Start `tools/mock_gspro_server.py`.
2. Run the app, connect, fire a few shots.
3. Kill the mock server mid-session.
4. Confirm the client transitions to Reconnecting and keeps trying past the previous 31s cap.
5. Restart the mock server; confirm reconnect succeeds and shots resume.

## Files changed

| Path | Change |
|---|---|
| `src/gc2_connect/gspro/client.py` | Async rewrite; newline framing; keepalive; reader loop via StreamReader; sync wrappers removed; `_send_message` no longer returns ack. |
| `src/gc2_connect/utils/reconnect.py` | `max_retries: int \| None = None`; loop condition + state transitions handle the infinite case. |
| `src/gc2_connect/services/connection_manager.py` | GSPro `ReconnectionManager` defaults: `max_retries=None, base_delay=5.0, max_delay=60.0`. `send_status` becomes async. Internal calls to `send_shot_async` swap to `send_shot`. |
| `src/gc2_connect/services/shot_router.py` | `send_shot_async` → `send_shot`. |
| `src/gc2_connect/ui/app.py` | One call site awaits `send_status`. |
| `tests/conftest.py` | `gspro_client` fixture becomes `async def @pytest.fixture` (pytest-asyncio auto mode is already configured). |
| `tests/unit/test_gspro_heartbeat.py` | `AsyncMock` for `send_heartbeat` patches; affected tests `async def`. |
| `docs/GSPRO_TCP_PROTOCOL.md` | Already rewritten in this change to reflect real GSPro v1.x wire. |

No new files.

## Execution order

1. **`ReconnectionManager` infinite retries.** Write `test_reconnect_manager_supports_infinite_retries`. Make it pass. Smallest blast radius; nothing depends on it yet.
2. **`GSProClient` async migration** — single atomic change. Write the new failing tests (`appends_newline`, `enables_keepalive`, `reader_loop_handles_dropped`, `send_shot_returns_none_and_acks_via_callback`, `handshakes_with_bare_gspro_ready`). Then rewrite `client.py`. Update `conftest.py` and `test_gspro_heartbeat.py` AsyncMock patches in the same change so the suite stays green.
3. **Ripple to callers.** Update `connection_manager.py` (including `send_status` async + reconnect defaults), `shot_router.py`, `app.py`. Add `test_gspro_client_reconnects_forever_with_capped_backoff`.
4. **Local CI gate.** `uv run pytest && uv run mypy src/ && uv run ruff check . && uv run ruff format --check .`
5. **Manual smoke test** with `tools/mock_gspro_server.py` (steps in §5 above).

## Risks and mitigations

| Risk | Mitigation |
|---|---|
| `MockGSProServer` expects sync-style framing | Verify the mock server's parser handles `\n`-terminated input (likely already does); add a test that feeds it `\n`-framed input explicitly. |
| Async-conversion regression on a hot path (shot ack timing) | The Code:200 ack already flows through `_handle_response` in the existing reader loop; this design just removes the redundant inline read in `_send_message`. The async path is what GsProApi.cs reference uses today. |
| Linux constants (`TCP_KEEPIDLE` etc.) missing on some Pythons | Guard each `setsockopt` with `hasattr(socket, "...")`. |
| `_on_match_started` / `set_hardware_ready` currently call `send_heartbeat` synchronously from sync contexts | Replace with `asyncio.create_task(self.send_heartbeat())`. Guarded by the existing "no running loop" handling pattern in `_start_heartbeat_timer`. |
| User pressing Disconnect mid-Reconnect needs to actually stop the loop | `ReconnectionManager.cancel()` already wired; verify the Disconnect action in the UI calls it on the GSPro manager. |

## Open questions

None at design time. All design decisions confirmed in brainstorming session 2026-05-11.
