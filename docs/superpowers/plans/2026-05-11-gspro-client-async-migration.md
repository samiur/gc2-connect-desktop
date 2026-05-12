# GSPro Client Async Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Migrate `GSProClient` to native `asyncio` streams with newline framing, `SO_KEEPALIVE`, and infinite reconnect — without changing the GSPro wire format.

**Architecture:** Replace `socket.socket` + sync I/O + `run_in_executor` wrappers with `asyncio.open_connection` (StreamReader/StreamWriter). Reader loop becomes `await reader.read()` with a balanced-brace fallback. All `send_*` methods become `async`. `ReconnectionManager` gains `max_retries: int | None = None` to support infinite retries; the GSPro manager uses 5s→60s capped backoff and retries forever.

**Tech Stack:** Python 3.10+, `asyncio.StreamReader`/`StreamWriter`, `asyncio.open_connection`, `pytest-asyncio` (already configured `asyncio_mode = "auto"`), `unittest.mock.AsyncMock`, `MockGSProServer` from `tests/simulators/gspro/`.

**Source spec:** `docs/superpowers/specs/2026-05-11-gspro-client-async-migration-design.md`. **Wire protocol reference:** `docs/GSPRO_TCP_PROTOCOL.md`.

---

## Background: what is GSProClient

`src/gc2_connect/gspro/client.py` is the TCP client that talks to the GSPro golf simulator on port 921. It does three things:

1. **Outbound**: sends one of three message shapes — shot data (`§6.1` of `GSPRO_TCP_PROTOCOL.md`), periodic heartbeat (`§6.2`), event-driven status update (`§6.3`).
2. **Inbound**: a long-running reader task that consumes GSPro's responses (discriminated by integer `Code`: 201 player info, 202 match started, 203 round ended, 5xx error). The handshake may include a bare non-JSON `GSPro ready` string.
3. **Connection lifecycle**: connect (with a registration heartbeat), keep alive while a match is running, disconnect cleanly with a final `LaunchMonitorIsReady=false` heartbeat.

Today it's all sync sockets wrapped in `run_in_executor`. We're moving to native asyncio streams.

## File map

| Path | Role | Touched in tasks |
|---|---|---|
| `src/gc2_connect/utils/reconnect.py` | Generic exponential-backoff reconnect helper | Task 1 |
| `src/gc2_connect/gspro/client.py` | TCP client for GSPro | Task 2 |
| `src/gc2_connect/services/connection_manager.py` | Wraps `GSProClient`, persists shot number, owns the GSPro `ReconnectionManager` | Tasks 2, 3 |
| `src/gc2_connect/services/shot_router.py` | Routes shots to GSPro or other targets | Task 2 |
| `src/gc2_connect/ui/app.py` | NiceGUI UI; calls `send_status` from a status handler | Task 2 |
| `tests/conftest.py` | `gspro_client` fixture | Task 2 |
| `tests/unit/test_gspro_heartbeat.py` | Heartbeat / match-state unit tests | Task 2 |
| `tests/unit/test_reconnect_manager.py` *(may exist; if not, create)* | `ReconnectionManager` tests | Task 1 |
| `tests/integration/test_gspro_client_async.py` *(create)* | Async I/O behavior of `GSProClient` against `MockGSProServer` | Task 2 |
| `tests/integration/test_gspro_reconnect.py` *(create)* | Reconnect-policy integration tests | Task 3 |

---

## Task 1: `ReconnectionManager` supports infinite retries

**Why first:** independent of everything else. Smallest blast radius. The new `GSProConnectionManager` defaults in Task 3 depend on this.

**Files:**
- Modify: `src/gc2_connect/utils/reconnect.py:41-92, 126-189`
- Test: `tests/unit/test_reconnect_manager.py` (create if it doesn't exist; otherwise add to existing)

**Reference reading:**
- `src/gc2_connect/utils/reconnect.py` — full file is short (~200 lines).

- [ ] **Step 1: Check whether the test file exists**

Run:
```bash
ls tests/unit/test_reconnect_manager.py 2>/dev/null || echo "MISSING"
```

If `MISSING`, create the file with this header:
```python
# ABOUTME: Unit tests for ReconnectionManager exponential-backoff reconnect helper.
# ABOUTME: Covers retry-count semantics, infinite-retry mode, cancellation, and delay calculation.
"""Unit tests for ReconnectionManager."""

from __future__ import annotations

import asyncio
from collections.abc import Awaitable, Callable
from unittest.mock import AsyncMock, MagicMock

import pytest

from gc2_connect.utils.reconnect import ReconnectionManager, ReconnectionState
```

- [ ] **Step 2: Write the failing test for infinite retries**

Append to `tests/unit/test_reconnect_manager.py`:

```python
class TestInfiniteRetries:
    """Test that max_retries=None means infinite retries."""

    @pytest.mark.asyncio
    async def test_infinite_retries_keeps_attempting_past_default_cap(self) -> None:
        """When max_retries=None the loop should keep attempting beyond any normal cap."""
        mgr = ReconnectionManager(max_retries=None, base_delay=0.0, max_delay=0.0)
        attempts = 0

        def fail_then_succeed() -> bool:
            nonlocal attempts
            attempts += 1
            return attempts >= 50  # success on the 50th attempt

        result = await mgr.attempt_reconnect(fail_then_succeed)
        assert result is True
        assert attempts == 50
        assert mgr.state == ReconnectionState.CONNECTED

    @pytest.mark.asyncio
    async def test_infinite_retries_stops_on_cancel(self) -> None:
        """When max_retries=None the loop should stop when cancel() is called."""
        mgr = ReconnectionManager(max_retries=None, base_delay=0.0, max_delay=0.0)
        attempts = 0

        def fail_and_cancel_after_3() -> bool:
            nonlocal attempts
            attempts += 1
            if attempts >= 3:
                mgr.cancel()
            return False

        result = await mgr.attempt_reconnect(fail_and_cancel_after_3)
        assert result is False
        assert mgr.state == ReconnectionState.DISCONNECTED
        # Should have stopped soon after cancel
        assert 3 <= attempts <= 5

    @pytest.mark.asyncio
    async def test_finite_retries_still_exits_at_max(self) -> None:
        """Confirm we did not regress the bounded-retry path: max_retries=3 still exits."""
        mgr = ReconnectionManager(max_retries=3, base_delay=0.0, max_delay=0.0)

        def always_fail() -> bool:
            return False

        result = await mgr.attempt_reconnect(always_fail)
        assert result is False
        assert mgr.state == ReconnectionState.FAILED
        assert mgr.retry_count == 3
```

- [ ] **Step 3: Run the new tests to verify they fail**

Run:
```bash
uv run pytest tests/unit/test_reconnect_manager.py::TestInfiniteRetries -v
```

Expected: the two new infinite-retry tests fail. The most likely failure is a `TypeError` constructing `ReconnectionManager(max_retries=None, ...)` because the current signature is `max_retries: int = 5`. (The third test, `test_finite_retries_still_exits_at_max`, should already pass — it's a regression guard.)

- [ ] **Step 4: Update `ReconnectionManager.__init__` typing**

Modify `src/gc2_connect/utils/reconnect.py:41-56`:

```python
def __init__(
    self,
    max_retries: int | None = 5,
    base_delay: float = 1.0,
    max_delay: float = 16.0,
) -> None:
    """Initialize the reconnection manager.

    Args:
        max_retries: Maximum number of reconnection attempts. ``None`` means
            retry forever until ``cancel()`` is called.
        base_delay: Initial delay between retries in seconds
        max_delay: Maximum delay between retries in seconds
    """
    self.max_retries = max_retries
    self.base_delay = base_delay
    self.max_delay = max_delay

    self._state = ReconnectionState.DISCONNECTED
    self._retry_count = 0
    self._cancelled = False

    # Callbacks
    self._state_callbacks: list[Callable[[ReconnectionState], None]] = []
    self._attempt_callbacks: list[Callable[[int, float], None]] = []
```

- [ ] **Step 5: Update the `attempt_reconnect` loop condition**

Modify `src/gc2_connect/utils/reconnect.py:144-189` (the body of `attempt_reconnect`):

```python
self._cancelled = False
self._retry_count = 0
self._set_state(ReconnectionState.CONNECTING)

def _should_continue(attempt: int) -> bool:
    if self._cancelled:
        return False
    if self.max_retries is None:
        return True
    return attempt < self.max_retries

attempt = 0
while _should_continue(attempt):
    try:
        result = connect_fn()
        if asyncio.iscoroutine(result):
            success = await result
        else:
            success = result

        if success:
            self._set_state(ReconnectionState.CONNECTED)
            logger.info("Reconnection successful")
            return True

    except Exception as e:
        logger.warning(f"Connection attempt {attempt + 1} failed: {e}")

    attempt += 1
    self._retry_count = attempt

    if _should_continue(attempt):
        delay = self.get_delay_for_attempt(attempt - 1)
        self._set_state(ReconnectionState.RECONNECTING)
        self._notify_attempt(attempt, delay)
        max_str = "∞" if self.max_retries is None else str(self.max_retries)
        logger.info(
            f"Reconnection attempt {attempt}/{max_str}, waiting {delay:.1f}s..."
        )

        try:
            await asyncio.sleep(delay)
        except asyncio.CancelledError:
            self._cancelled = True
            break

if self._cancelled:
    self._set_state(ReconnectionState.DISCONNECTED)
    logger.info("Reconnection cancelled")
    return False

self._set_state(ReconnectionState.FAILED)
logger.error(f"Reconnection failed after {self.max_retries} attempts")
return False
```

The key changes vs the original:
- New `_should_continue(attempt)` helper handles both bounded and unbounded.
- The "Reconnection failed after N attempts" line is only reachable when `max_retries` is a positive int (because infinite mode exits only via cancel, which takes the earlier branch).

- [ ] **Step 6: Run the new tests to verify they pass**

Run:
```bash
uv run pytest tests/unit/test_reconnect_manager.py::TestInfiniteRetries -v
```

Expected: all three pass.

- [ ] **Step 7: Run the full reconnect test file to confirm no regression**

Run:
```bash
uv run pytest tests/unit/test_reconnect_manager.py -v
```

Expected: all tests in the file pass.

- [ ] **Step 8: Run mypy on the changed file**

Run:
```bash
uv run mypy src/gc2_connect/utils/reconnect.py
```

Expected: 0 errors.

- [ ] **Step 9: Commit**

```bash
git add src/gc2_connect/utils/reconnect.py tests/unit/test_reconnect_manager.py
git commit -m "$(cat <<'EOF'
feat: support infinite retries in ReconnectionManager

Allow max_retries=None to mean "retry until cancel". The bounded-retry
path is unchanged. Prepares ReconnectionManager for use by the GSPro
client where the user expects indefinite reconnection after GSPro
restarts or sleep/wake.
EOF
)"
```

---

## Task 2: Migrate `GSProClient` to async I/O + update tests + ripple to callers

**Why one task:** the public API of `GSProClient` changes (sync send methods become async, `*_async` wrappers go away). Callers in `connection_manager.py`, `shot_router.py`, `app.py`, plus tests in `conftest.py` and `test_gspro_heartbeat.py`, all depend on this surface and cannot stay green if updated piecemeal. We do it all in one task ending with a green test suite.

**Files:**
- Modify: `src/gc2_connect/gspro/client.py` (full rewrite of socket I/O — keep public surface for state-tracking properties like `match_started`, `hardware_ready`, `set_hardware_ready`, callback management; rewrite connect/disconnect/send/reader)
- Modify: `src/gc2_connect/services/connection_manager.py:478-545` (async `send_status`, drop `*_async` suffixes)
- Modify: `src/gc2_connect/services/shot_router.py:164` (one line: drop `_async` suffix)
- Modify: `src/gc2_connect/ui/app.py:993-994` (await `send_status`)
- Modify: `tests/conftest.py:299-315` (async fixture)
- Modify: `tests/unit/test_gspro_heartbeat.py` (AsyncMock for `send_heartbeat`; replace `_socket` patching with `_writer` patching; affected tests become `async def`)
- Create: `tests/integration/test_gspro_client_async.py`

**Reference reading before starting:**
- `docs/GSPRO_TCP_PROTOCOL.md` — sections 2 (framing), 4 (inbound), 5 (outbound), 6.4 (shutdown).
- `docs/GsProApi.cs` — `SendDeviceRegistrationAsync` (line 309), `SendShotData` (359), `ReadLoop` (516), `SendBallStatus` (660), `SendHeartbeat` (884), `Disconnect` (319). Specifically note the `+ "\n"` on every write.
- `tests/simulators/gspro/server.py` — `MockGSProServer` API.

### Step group A — Write the new async tests

- [ ] **Step 1: Read existing `MockGSProServer` API**

Run:
```bash
sed -n '1,80p' tests/simulators/gspro/server.py
sed -n '1,40p' tests/simulators/gspro/config.py
```

Note the methods you'll use: `async with MockGSProServer(config) as server`, `server.host`, `server.port`, `server.get_shots()`, `server.received_messages` (or similar — check what's exposed). If the mock server does not currently expose the raw received bytes, add an attribute `received_raw_bytes: list[bytes]` that the connection handler appends each chunk to. Make that addition in this step; commit it later with Task 2.

- [ ] **Step 2: Create `tests/integration/test_gspro_client_async.py` with the file header**

```python
# ABOUTME: Integration tests for GSProClient async I/O behavior against MockGSProServer.
# ABOUTME: Covers newline framing, keepalive, dropped-connection handling, and handshake.
"""Async integration tests for GSProClient."""

from __future__ import annotations

import asyncio
import json
import socket
from unittest.mock import MagicMock

import pytest

from gc2_connect.gspro.client import GSProClient
from gc2_connect.models import GC2BallStatus, GC2ShotData
from tests.simulators.gspro.config import MockGSProServerConfig, ResponseType
from tests.simulators.gspro.server import MockGSProServer
```

- [ ] **Step 3: Write failing test — outbound writes are newline-terminated**

Append to `tests/integration/test_gspro_client_async.py`:

```python
class TestNewlineFraming:
    @pytest.mark.asyncio
    async def test_every_outbound_write_ends_in_newline(self) -> None:
        async with MockGSProServer(MockGSProServerConfig()) as server:
            client = GSProClient(host=server.host, port=server.port)
            connected = await client.connect()
            assert connected

            try:
                # Send each of the three outbound message shapes
                shot = GC2ShotData(
                    ball_speed=140.0, launch_angle=12.0, horizontal_launch_angle=1.0,
                    total_spin=2500.0, back_spin=2400.0, side_spin=-200.0,
                )
                await client.send_shot(shot)
                await client.send_heartbeat()
                await client.send_status(GC2BallStatus(flags=7, ball_count=1))

                # Give the server a beat to receive
                await asyncio.sleep(0.1)
            finally:
                await client.disconnect()

            raw = b"".join(server.received_raw_bytes)
            # Every JSON object on the wire must be \n-terminated
            assert raw.count(b"\n") >= 4  # initial registration heartbeat + 3 above
            # No object should be concatenated with another (each \n preceded by '}')
            for idx, b in enumerate(raw):
                if b == 0x0A:  # '\n'
                    assert raw[idx - 1:idx] == b"}", \
                        f"Newline at offset {idx} not preceded by '}}': context={raw[max(0,idx-20):idx+1]!r}"
```

- [ ] **Step 4: Write failing test — `SO_KEEPALIVE` is enabled after connect**

Append:

```python
class TestKeepalive:
    @pytest.mark.asyncio
    async def test_so_keepalive_enabled_after_connect(self) -> None:
        async with MockGSProServer(MockGSProServerConfig()) as server:
            client = GSProClient(host=server.host, port=server.port)
            await client.connect()
            try:
                sock = client._writer.get_extra_info("socket")
                ka = sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE)
                assert ka == 1
            finally:
                await client.disconnect()
```

- [ ] **Step 5: Write failing test — reader loop handles dropped connection**

Append:

```python
class TestDroppedConnection:
    @pytest.mark.asyncio
    async def test_reader_loop_triggers_disconnect_callback_on_eof(self) -> None:
        disconnect_fired = asyncio.Event()

        async with MockGSProServer(MockGSProServerConfig()) as server:
            client = GSProClient(host=server.host, port=server.port)
            client.add_disconnect_callback(lambda: disconnect_fired.set())
            await client.connect()

            # Server abruptly closes all client connections.
            await server.close_all_connections()

            # Disconnect callback must fire within a reasonable window.
            await asyncio.wait_for(disconnect_fired.wait(), timeout=2.0)
            assert client.is_connected is False
```

> If `MockGSProServer` doesn't have `close_all_connections`, add it: a method that iterates active client writers and calls `writer.close(); await writer.wait_closed()` on each.

- [ ] **Step 6: Write failing test — `send_shot` returns None and ack arrives via callback**

Append:

```python
class TestSendShotReturnsNone:
    @pytest.mark.asyncio
    async def test_send_shot_returns_none_and_ack_arrives_via_callback(self) -> None:
        async with MockGSProServer(MockGSProServerConfig(
            response_type=ResponseType.SUCCESS,
        )) as server:
            client = GSProClient(host=server.host, port=server.port)
            await client.connect()

            ack_received = asyncio.Event()
            seen = []

            def on_response(resp) -> None:
                seen.append(resp)
                if resp.Code == 200:
                    ack_received.set()

            client.add_response_callback(on_response)

            try:
                shot = GC2ShotData(
                    ball_speed=140.0, launch_angle=12.0, horizontal_launch_angle=1.0,
                    total_spin=2500.0, back_spin=2400.0, side_spin=-200.0,
                )
                result = await client.send_shot(shot)
                assert result is None  # async send_shot no longer returns inline

                await asyncio.wait_for(ack_received.wait(), timeout=2.0)
                assert any(r.Code == 200 for r in seen)
            finally:
                await client.disconnect()
```

- [ ] **Step 7: Write failing test — bare `GSPro ready` handshake**

Append:

```python
class TestBareHandshake:
    @pytest.mark.asyncio
    async def test_bare_gspro_ready_string_fires_match_started(self) -> None:
        async with MockGSProServer(MockGSProServerConfig()) as server:
            client = GSProClient(host=server.host, port=server.port)
            match_started = asyncio.Event()
            client.add_match_started_callback(lambda: match_started.set())
            await client.connect()

            try:
                # MockGSProServer needs an API for "send raw bytes to current client".
                # Send the bare handshake (no JSON envelope, ends with newline).
                await server.send_raw_to_clients(b"GSPro ready\n")
                await asyncio.wait_for(match_started.wait(), timeout=2.0)
                assert client.match_started is True
            finally:
                await client.disconnect()
```

> If `send_raw_to_clients` does not exist on `MockGSProServer`, add it in this task.

- [ ] **Step 8: Run all new tests to confirm they fail**

Run:
```bash
uv run pytest tests/integration/test_gspro_client_async.py -v
```

Expected: every test fails. Failures will mostly be `AttributeError` on `await client.connect()` (today `connect` is sync) and `await client.send_shot()` (today returns `GSProResponse | None`).

### Step group B — Rewrite `GSProClient`

- [ ] **Step 9: Open `src/gc2_connect/gspro/client.py` and read the full file**

Run:
```bash
sed -n '1,200p' src/gc2_connect/gspro/client.py
sed -n '200,400p' src/gc2_connect/gspro/client.py
sed -n '400,584p' src/gc2_connect/gspro/client.py
```

Note the surface that must be **preserved exactly**:

- Module-level constants: `DEFAULT_HOST`, `DEFAULT_PORT`, `HEARTBEAT_INTERVAL_SECONDS = 6.0`.
- Properties: `is_connected`, `shot_number`, `current_player`, `match_started`, `hardware_ready`, `is_ready_to_report`.
- State-tracking methods: `set_hardware_ready(bool)`.
- Callback registration methods: `add_response_callback`, `remove_response_callback`, `add_disconnect_callback`, `remove_disconnect_callback`, `add_player_info_callback`, `remove_player_info_callback`, `add_match_started_callback`, `remove_match_started_callback`, `add_match_ended_callback`, `remove_match_ended_callback`.
- Internal handlers: `_on_match_started`, `_on_match_ended`, `_handle_response` (logic unchanged; only the trigger mechanism shifts to async).
- Private attribute `_shot_number` — `connection_manager.py:497` writes to it directly to restore shot count across reconnects. Keep it.

Surface that **changes**:

- `connect()` → `async def connect() -> bool`
- `disconnect()` → `async def disconnect() -> None`
- `send_shot(shot)` → `async def send_shot(shot: GC2ShotData) -> None`
- `send_heartbeat()` → `async def send_heartbeat() -> None`
- `send_status(status)` → `async def send_status(status: GC2BallStatus) -> None`
- Remove: `connect_async`, `disconnect_async`, `send_shot_async`, `send_status_async`
- Remove: `_socket` attribute. Add: `_reader: asyncio.StreamReader | None`, `_writer: asyncio.StreamWriter | None`.
- `_send_message(message)` → `async def _send_message(message)` — no `expect_response` param, no return value, always appends `\n`, no stale-buffer-clear.

- [ ] **Step 10: Rewrite `client.py` — top, imports, and class skeleton**

Replace the imports and the class definition's `__init__` and constants. Here's the full new top of the file (replaces lines 1-70 approximately):

```python
# ABOUTME: TCP client for GSPro Open Connect API v1.
# ABOUTME: Sends shot data to GSPro golf simulator and handles responses.
"""GSPro Open Connect API v1 client (async)."""

from __future__ import annotations

import asyncio
import json
import logging
import socket
import sys
from collections.abc import Callable
from typing import Any

from gc2_connect.models import (
    GC2BallStatus,
    GC2ShotData,
    GSProResponse,
    GSProShotMessage,
    GSProShotOptions,
)

logger = logging.getLogger(__name__)


def _notify_callbacks(callbacks: list[Callable[..., None]], *args: Any) -> None:
    """Invoke all callbacks with the given arguments, logging any errors."""
    for callback in callbacks:
        try:
            callback(*args)
        except Exception as e:
            logger.error(f"Callback error: {e}")


DEFAULT_HOST = "127.0.0.1"
DEFAULT_PORT = 921
HEARTBEAT_INTERVAL_SECONDS = 6.0
CONNECT_TIMEOUT_SECONDS = 5.0
SHUTDOWN_GRACE_SECONDS = 0.250
KEEPALIVE_IDLE_SECONDS = 30
KEEPALIVE_INTVL_SECONDS = 10
KEEPALIVE_CNT = 3


class GSProClient:
    """Async client for GSPro Open Connect API v1."""

    def __init__(self, host: str = DEFAULT_HOST, port: int = DEFAULT_PORT):
        self.host = host
        self.port = port
        self._reader: asyncio.StreamReader | None = None
        self._writer: asyncio.StreamWriter | None = None
        self._connected = False
        self._shot_number = 0
        self._current_player: dict[str, Any] | None = None

        # Callbacks
        self._response_callbacks: list[Callable[[GSProResponse], None]] = []
        self._disconnect_callbacks: list[Callable[[], None]] = []
        self._player_info_callbacks: list[Callable[[dict[str, Any]], None]] = []
        self._match_started_callbacks: list[Callable[[], None]] = []
        self._match_ended_callbacks: list[Callable[[], None]] = []

        # Background tasks
        self._reader_task: asyncio.Task[None] | None = None
        self._heartbeat_task: asyncio.Task[None] | None = None

        # Match state tracking for heartbeat logic
        self._match_started = False
        self._hardware_ready = False

        # Register internal handlers for match state changes
        self._match_started_callbacks.append(self._on_match_started)
        self._match_ended_callbacks.append(self._on_match_ended)
```

- [ ] **Step 11: Keep the existing read-only properties and callback registration methods**

These come straight after `__init__` and are **unchanged** from the current file (lines 71-168 of the existing client.py):

- `is_connected`, `shot_number`, `current_player`, `match_started`, `hardware_ready`, `is_ready_to_report` properties.
- `add_response_callback` / `remove_response_callback` / `_notify_response`.
- `add_disconnect_callback` / `remove_disconnect_callback` / `_notify_disconnect`.
- `add_player_info_callback` / `remove_player_info_callback`.
- `add_match_started_callback` / `remove_match_started_callback`.
- `add_match_ended_callback` / `remove_match_ended_callback`.

Copy them over verbatim.

- [ ] **Step 12: Rewrite `set_hardware_ready` to fire-and-forget a heartbeat task**

Replace the existing `set_hardware_ready`:

```python
def set_hardware_ready(self, ready: bool) -> None:
    """Update hardware ready state from GC2.

    Called when GC2 status changes (FLAGS in 0M message).
    """
    if self._hardware_ready == ready:
        return
    self._hardware_ready = ready
    if not self._match_started:
        return
    self._schedule_heartbeat()
```

Add a small helper later in the class:

```python
def _schedule_heartbeat(self) -> None:
    """Fire-and-forget a heartbeat from a sync context."""
    try:
        asyncio.create_task(self.send_heartbeat())
    except RuntimeError:
        # No running event loop (e.g. sync-only test contexts).
        logger.debug("No running loop; skipping heartbeat schedule")
```

- [ ] **Step 13: Rewrite the match-state handlers**

Replace `_on_match_started` and `_on_match_ended`:

```python
def _on_match_started(self) -> None:
    """Handle match started event (code 202)."""
    if self._match_started:
        return
    self._match_started = True
    self._start_heartbeat_timer()
    self._schedule_heartbeat()

def _on_match_ended(self) -> None:
    """Handle match ended event (code 203)."""
    if not self._match_started:
        return
    self._match_started = False
    self._stop_heartbeat_timer()
```

- [ ] **Step 14: Rewrite the heartbeat timer plumbing**

Replace `_start_heartbeat_timer`, `_stop_heartbeat_timer`, `_heartbeat_loop`:

```python
def _start_heartbeat_timer(self) -> None:
    """Start the periodic heartbeat task."""
    self._stop_heartbeat_timer()
    try:
        self._heartbeat_task = asyncio.create_task(self._heartbeat_loop())
        logger.info("GSPro heartbeat timer started")
    except RuntimeError as e:
        logger.debug(f"Could not start heartbeat timer (no event loop): {e}")

def _stop_heartbeat_timer(self) -> None:
    """Stop the periodic heartbeat task."""
    if self._heartbeat_task is not None:
        self._heartbeat_task.cancel()
        self._heartbeat_task = None
        logger.info("GSPro heartbeat timer stopped")

async def _heartbeat_loop(self) -> None:
    """Send heartbeats at regular intervals while match is active."""
    try:
        while self._connected and self._match_started:
            await asyncio.sleep(HEARTBEAT_INTERVAL_SECONDS)
            if self._connected and self._match_started:
                await self.send_heartbeat()
    except asyncio.CancelledError:
        pass
```

- [ ] **Step 15: Add socket configuration helper**

Add this method to the class:

```python
def _configure_socket(self, sock: socket.socket) -> None:
    """Apply TCP_NODELAY and SO_KEEPALIVE to the underlying socket."""
    sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
    sock.setsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE, 1)
    if sys.platform == "darwin" and hasattr(socket, "TCP_KEEPALIVE"):
        sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPALIVE, KEEPALIVE_IDLE_SECONDS)
    elif sys.platform.startswith("linux"):
        if hasattr(socket, "TCP_KEEPIDLE"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPIDLE, KEEPALIVE_IDLE_SECONDS)
        if hasattr(socket, "TCP_KEEPINTVL"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPINTVL, KEEPALIVE_INTVL_SECONDS)
        if hasattr(socket, "TCP_KEEPCNT"):
            sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_KEEPCNT, KEEPALIVE_CNT)
```

- [ ] **Step 16: Rewrite `connect` as async**

```python
async def connect(self) -> bool:
    """Connect to GSPro and send the initial registration heartbeat."""
    try:
        self._reader, self._writer = await asyncio.wait_for(
            asyncio.open_connection(self.host, self.port),
            timeout=CONNECT_TIMEOUT_SECONDS,
        )
    except (TimeoutError, asyncio.TimeoutError, OSError) as e:
        logger.error(f"Failed to connect to GSPro: {e}")
        self._reader = None
        self._writer = None
        self._connected = False
        return False

    sock = self._writer.get_extra_info("socket")
    if sock is not None:
        self._configure_socket(sock)

    self._connected = True
    logger.info(f"Connected to GSPro at {self.host}:{self.port}")

    # Initial registration heartbeat
    logger.info("Sending initial heartbeat to GSPro...")
    await self.send_heartbeat()
    logger.info("Initial heartbeat sent")

    # Start the inbound reader task
    self._reader_task = asyncio.create_task(self._reader_loop())

    return True
```

- [ ] **Step 17: Rewrite `disconnect` as async**

```python
async def disconnect(self) -> None:
    """Cleanly disconnect from GSPro."""
    if self._writer is None and not self._connected:
        return

    # Stop heartbeat first so it does not race with shutdown
    self._stop_heartbeat_timer()
    self._match_started = False

    # Stop the reader task
    if self._reader_task is not None:
        self._reader_task.cancel()
        self._reader_task = None

    # Final shutdown heartbeat (LaunchMonitorIsReady=false)
    if self._writer is not None and self._connected:
        try:
            await self._send_shutdown_heartbeat()
            await asyncio.sleep(SHUTDOWN_GRACE_SECONDS)
        except Exception as e:
            logger.debug(f"Error sending shutdown heartbeat: {e}")

    # Close the writer
    if self._writer is not None:
        try:
            self._writer.close()
            await self._writer.wait_closed()
        except Exception:
            pass

    self._reader = None
    self._writer = None
    self._connected = False
    self._shot_number = 0
    self._current_player = None
    logger.info("Disconnected from GSPro (clean shutdown)")
```

- [ ] **Step 18: Rewrite `_send_shutdown_heartbeat` as async**

```python
async def _send_shutdown_heartbeat(self) -> None:
    """Send final heartbeat indicating launch monitor is going offline."""
    if self._writer is None:
        return
    message = GSProShotMessage(
        ShotNumber=self._shot_number,
        ShotDataOptions=GSProShotOptions(
            ContainsBallData=False,
            ContainsClubData=False,
            LaunchMonitorIsReady=False,
            IsHeartBeat=True,
        ),
    )
    payload = json.dumps(message.to_dict()).encode("utf-8") + b"\n"
    self._writer.write(payload)
    await self._writer.drain()
    logger.debug("Sent shutdown heartbeat (LaunchMonitorIsReady=false)")
```

- [ ] **Step 19: Rewrite the three public send methods**

```python
async def send_shot(self, shot: GC2ShotData) -> None:
    """Send a shot to GSPro.

    Returns immediately after writing. The GSPro ack arrives asynchronously
    through the reader loop and is dispatched to response callbacks.
    """
    if not self._connected or self._writer is None:
        logger.error("Not connected to GSPro")
        return

    self._shot_number += 1
    message = GSProShotMessage.from_gc2_shot(shot, self._shot_number)
    await self._send_message(message)

async def send_heartbeat(self) -> None:
    """Send a periodic heartbeat. GSPro does not respond to heartbeats."""
    if not self._connected or self._writer is None:
        return
    message = GSProShotMessage(
        ShotNumber=self._shot_number,
        ShotDataOptions=GSProShotOptions(
            ContainsBallData=False,
            ContainsClubData=False,
            LaunchMonitorIsReady=self.is_ready_to_report,
            IsHeartBeat=True,
        ),
    )
    await self._send_message(message)

async def send_status(self, status: GC2BallStatus) -> None:
    """Send an event-driven status update. GSPro does not respond."""
    if not self._connected or self._writer is None:
        return
    message = GSProShotMessage(
        ShotNumber=self._shot_number,
        ShotDataOptions=GSProShotOptions(
            ContainsBallData=False,
            ContainsClubData=False,
            LaunchMonitorIsReady=status.is_ready,
            LaunchMonitorBallDetected=status.ball_detected,
            IsHeartBeat=False,
        ),
    )
    logger.debug(
        f"Sending status: ready={status.is_ready}, ball_detected={status.ball_detected}"
    )
    await self._send_message(message)
```

- [ ] **Step 20: Rewrite `_send_message` as async with newline framing**

```python
async def _send_message(self, message: GSProShotMessage) -> None:
    """Send a single JSON object, newline-terminated."""
    if self._writer is None:
        logger.error("Cannot send message: writer is None")
        return

    payload = json.dumps(message.to_dict()).encode("utf-8") + b"\n"
    try:
        self._writer.write(payload)
        await self._writer.drain()
        logger.debug(f"Sent {len(payload)} bytes: {payload[:200]!r}")
    except (ConnectionError, OSError) as e:
        logger.error(f"GSPro write failed: {e}")
        self._on_connection_lost()
```

- [ ] **Step 21: Add the reader loop and buffer-drain helper**

```python
async def _reader_loop(self) -> None:
    """Continuously read from GSPro and dispatch responses."""
    logger.debug("GSPro reader loop started")
    buffer = b""
    try:
        while self._connected and self._reader is not None:
            try:
                chunk = await self._reader.read(4096)
            except (ConnectionError, OSError) as e:
                logger.warning(f"GSPro reader socket error: {e}")
                self._on_connection_lost()
                return
            if not chunk:
                logger.warning("GSPro connection closed (EOF)")
                self._on_connection_lost()
                return
            buffer = self._drain_buffer(buffer + chunk)
    except asyncio.CancelledError:
        pass
    finally:
        logger.info("GSPro reader loop ended")

def _drain_buffer(self, buffer: bytes) -> bytes:
    """Extract every complete JSON object (or bare 'GSPro ready') from buffer.

    Returns the unparsed tail.
    """
    text = buffer.decode("utf-8", errors="replace")
    decoder = json.JSONDecoder()

    while text:
        # Skip leading whitespace, including \r and \n
        stripped = text.lstrip()
        if not stripped:
            return b""
        skipped = len(text) - len(stripped)
        text = stripped

        # Bare handshake line?
        if text.startswith("GSPro ready"):
            self._handle_response({"Code": 202, "Message": "GSPro ready"})
            # Drop up to and including the next newline (or whole line)
            newline = text.find("\n")
            if newline == -1:
                return b""  # rest will arrive later
            text = text[newline + 1:]
            continue

        # Try to parse one JSON object off the front
        try:
            obj, end = decoder.raw_decode(text)
        except json.JSONDecodeError:
            # Possibly an incomplete object — keep waiting for more bytes.
            return (skipped * b" " + text.encode("utf-8")) if skipped else text.encode("utf-8")

        self._handle_response(obj)
        text = text[end:]

    return b""
```

> The "skipped * b' '" trick on the JSONDecodeError branch preserves byte-level offsets for clean logging if needed; functionally `text.encode()` alone is fine. Either is acceptable.

- [ ] **Step 22: Add the connection-lost helper**

```python
def _on_connection_lost(self) -> None:
    """Mark disconnected and notify callbacks. Idempotent."""
    if not self._connected:
        return
    self._connected = False
    self._stop_heartbeat_timer()
    self._match_started = False
    # Best-effort writer close; do not await here (we might be in a sync context).
    if self._writer is not None:
        try:
            self._writer.close()
        except Exception:
            pass
    self._notify_disconnect()
```

- [ ] **Step 23: Keep `_handle_response` as-is**

The current `_handle_response` (lines 222-246 of the old file) does not need any change — it just inspects `Code` and fires callbacks. Copy it verbatim.

- [ ] **Step 24: Delete the obsolete methods**

The new `client.py` must **not** contain:

- `_start_reader_loop` (the old `try/except` task-starter).
- `_stop_reader_loop`.
- `connect_async`, `disconnect_async`, `send_shot_async`, `send_status_async`.
- The old sync `connect`, `disconnect`, `send_shot`, `send_heartbeat`, `send_status`, `_send_message`, `_send_shutdown_heartbeat`.
- The `_reader_running` flag.
- Any reference to `self._socket`.

Verify with:
```bash
grep -n "connect_async\|disconnect_async\|send_shot_async\|send_status_async\|_socket\|_reader_running" src/gc2_connect/gspro/client.py
```

Expected output: empty.

### Step group C — Update tests for the new API

- [ ] **Step 25: Update `tests/conftest.py::gspro_client` fixture**

Replace lines 299-315 of `tests/conftest.py`:

```python
@pytest.fixture
async def gspro_client(mock_gspro_server):
    """Fixture providing a GSProClient connected to the mock server."""
    from gc2_connect.gspro.client import GSProClient

    client = GSProClient(host=mock_gspro_server.host, port=mock_gspro_server.port)
    connected = await client.connect()
    assert connected, "Failed to connect to mock GSPro server"

    # Give the initial registration heartbeat a moment to land
    await asyncio.sleep(0.05)

    try:
        yield client
    finally:
        if client.is_connected:
            await client.disconnect()
```

If `asyncio` is not already imported at the top of `conftest.py`, add `import asyncio`.

- [ ] **Step 26: Update `tests/unit/test_gspro_heartbeat.py` connected-client fixture**

The fixture at lines 21-27 puts `MagicMock` on `_socket`. Replace with a `MagicMock` writer that supports `write` (sync) and `drain` (async):

```python
@pytest.fixture
def connected_client() -> Generator[GSProClient, None, None]:
    """Create a GSProClient that appears connected, with a mocked writer."""
    client = GSProClient()
    client._connected = True
    writer = MagicMock()
    writer.write = MagicMock()
    writer.drain = AsyncMock()
    client._writer = writer
    yield client
```

Add `from unittest.mock import AsyncMock` to the imports at the top of the file (alongside the existing `MagicMock, patch`).

- [ ] **Step 27: Update `TestSetHardwareReady` tests**

The test bodies at lines 74-94 patch `send_heartbeat` as a sync method and assert `assert_called_once()`. `send_heartbeat` is now async; with our `_schedule_heartbeat()` helper, `set_hardware_ready` now calls `asyncio.create_task(self.send_heartbeat())`. The right assertion is that `asyncio.create_task` was called with the right coroutine.

Replace lines 74-94 with:

```python
def test_set_hardware_ready_sends_status_during_match(
    self, connected_client: GSProClient
) -> None:
    """Test set_hardware_ready schedules a heartbeat when match is active."""
    connected_client._match_started = True

    with patch.object(connected_client, "_schedule_heartbeat") as mock_schedule:
        connected_client.set_hardware_ready(True)
        mock_schedule.assert_called_once()

def test_set_hardware_ready_no_status_when_no_match(
    self, connected_client: GSProClient
) -> None:
    """Test set_hardware_ready doesn't schedule a heartbeat when no match is active."""
    connected_client._match_started = False

    with patch.object(connected_client, "_schedule_heartbeat") as mock_schedule:
        connected_client.set_hardware_ready(True)
        mock_schedule.assert_not_called()

def test_set_hardware_ready_no_status_when_value_unchanged(
    self, connected_client: GSProClient
) -> None:
    """Test set_hardware_ready doesn't schedule a heartbeat when value doesn't change."""
    connected_client._match_started = True
    connected_client._hardware_ready = True

    with patch.object(connected_client, "_schedule_heartbeat") as mock_schedule:
        connected_client.set_hardware_ready(True)
        mock_schedule.assert_not_called()
```

- [ ] **Step 28: Update `TestOnMatchStarted` tests**

Replace lines 112-155 (`test_on_match_started_*` tests). The handler now also goes through `_schedule_heartbeat`:

```python
class TestOnMatchStarted:
    """Test _on_match_started internal handler."""

    def test_on_match_started_sets_flag(self, connected_client: GSProClient) -> None:
        assert connected_client._match_started is False
        with (
            patch.object(connected_client, "_start_heartbeat_timer"),
            patch.object(connected_client, "_schedule_heartbeat"),
        ):
            connected_client._on_match_started()
        assert connected_client._match_started is True

    def test_on_match_started_starts_heartbeat_timer(self, connected_client: GSProClient) -> None:
        with (
            patch.object(connected_client, "_start_heartbeat_timer") as mock_start_timer,
            patch.object(connected_client, "_schedule_heartbeat"),
        ):
            connected_client._on_match_started()
            mock_start_timer.assert_called_once()

    def test_on_match_started_sends_status(self, connected_client: GSProClient) -> None:
        with (
            patch.object(connected_client, "_start_heartbeat_timer"),
            patch.object(connected_client, "_schedule_heartbeat") as mock_schedule,
        ):
            connected_client._on_match_started()
            mock_schedule.assert_called_once()

    def test_on_match_started_idempotent(self, connected_client: GSProClient) -> None:
        connected_client._match_started = True
        with (
            patch.object(connected_client, "_start_heartbeat_timer") as mock_start_timer,
            patch.object(connected_client, "_schedule_heartbeat") as mock_schedule,
        ):
            connected_client._on_match_started()
            mock_start_timer.assert_not_called()
            mock_schedule.assert_not_called()
```

- [ ] **Step 29: Update `TestHeartbeatLoop` tests**

The loop now `await`s `send_heartbeat`. Replace `patch.object(connected_client, "send_heartbeat", side_effect=...)` with `AsyncMock(side_effect=...)`. Replace lines 238-301 with:

```python
class TestHeartbeatLoop:
    """Test the heartbeat loop behavior."""

    @pytest.mark.asyncio
    async def test_heartbeat_loop_sends_heartbeats(self, connected_client: GSProClient) -> None:
        connected_client._match_started = True
        heartbeat_count = 0

        async def mock_send_heartbeat() -> None:
            nonlocal heartbeat_count
            heartbeat_count += 1
            if heartbeat_count >= 2:
                connected_client._match_started = False

        with (
            patch.object(connected_client, "send_heartbeat", new=AsyncMock(side_effect=mock_send_heartbeat)),
            patch("asyncio.sleep", new=AsyncMock(return_value=None)) as mock_sleep,
        ):
            await connected_client._heartbeat_loop()
            assert heartbeat_count == 2
            assert mock_sleep.call_count >= 1
            mock_sleep.assert_called_with(HEARTBEAT_INTERVAL_SECONDS)

    @pytest.mark.asyncio
    async def test_heartbeat_loop_stops_on_disconnect(self, connected_client: GSProClient) -> None:
        connected_client._match_started = True
        iteration = 0

        async def mock_sleep(_seconds: float) -> None:
            nonlocal iteration
            iteration += 1
            if iteration >= 1:
                connected_client._connected = False

        with (
            patch.object(connected_client, "send_heartbeat", new=AsyncMock()),
            patch("asyncio.sleep", new=AsyncMock(side_effect=mock_sleep)),
        ):
            await connected_client._heartbeat_loop()
            assert iteration >= 1

    @pytest.mark.asyncio
    async def test_heartbeat_loop_stops_on_match_ended(self, connected_client: GSProClient) -> None:
        connected_client._match_started = True
        iteration = 0

        async def mock_sleep(_seconds: float) -> None:
            nonlocal iteration
            iteration += 1
            if iteration >= 1:
                connected_client._match_started = False

        with (
            patch.object(connected_client, "send_heartbeat", new=AsyncMock()),
            patch("asyncio.sleep", new=AsyncMock(side_effect=mock_sleep)),
        ):
            await connected_client._heartbeat_loop()
            assert iteration >= 1
```

- [ ] **Step 30: Update `TestSendHeartbeatWithReadyState` tests**

Lines 307-345 assert on `mock_socket.sendall` and check the decoded bytes. Replace with assertions on `writer.write`. These tests are now async:

```python
class TestSendHeartbeatWithReadyState:
    """Test that send_heartbeat uses is_ready_to_report."""

    @pytest.mark.asyncio
    async def test_send_heartbeat_uses_is_ready_to_report_true(
        self, connected_client: GSProClient
    ) -> None:
        connected_client._hardware_ready = True
        connected_client._match_started = True

        writer = connected_client._writer
        assert writer is not None

        await connected_client.send_heartbeat()

        writer.write.assert_called_once()
        sent_data = writer.write.call_args[0][0].decode("utf-8")
        assert sent_data.endswith("\n"), "outbound payload must end with \\n"
        assert '"LaunchMonitorIsReady": true' in sent_data

    @pytest.mark.asyncio
    async def test_send_heartbeat_uses_is_ready_to_report_false(
        self, connected_client: GSProClient
    ) -> None:
        connected_client._hardware_ready = True
        connected_client._match_started = False

        writer = connected_client._writer
        assert writer is not None

        await connected_client.send_heartbeat()

        writer.write.assert_called_once()
        sent_data = writer.write.call_args[0][0].decode("utf-8")
        assert sent_data.endswith("\n")
        assert '"LaunchMonitorIsReady": false' in sent_data
```

- [ ] **Step 31: Update `TestDisconnectStopsHeartbeat`**

Lines 351-369 — `disconnect` is now async. Make those tests async and use `AsyncMock` for `_send_shutdown_heartbeat`:

```python
class TestDisconnectStopsHeartbeat:
    """Test that disconnect stops the heartbeat timer."""

    @pytest.mark.asyncio
    async def test_disconnect_stops_heartbeat_timer(self, connected_client: GSProClient) -> None:
        mock_task = MagicMock()
        connected_client._heartbeat_task = mock_task
        with patch.object(connected_client, "_send_shutdown_heartbeat", new=AsyncMock()):
            await connected_client.disconnect()
        mock_task.cancel.assert_called_once()
        assert connected_client._heartbeat_task is None

    @pytest.mark.asyncio
    async def test_disconnect_clears_match_state(self, connected_client: GSProClient) -> None:
        connected_client._match_started = True
        with patch.object(connected_client, "_send_shutdown_heartbeat", new=AsyncMock()):
            await connected_client.disconnect()
        assert connected_client._match_started is False
```

- [ ] **Step 32: Confirm the remaining tests in `test_gspro_heartbeat.py` need no change**

`TestMatchStateTracking`, `TestHeartbeatTimerControl`, `TestOnMatchEnded`, `TestMatchStateCallbackWiring`, `TestHeartbeatIntervalConstant`, `TestInitializationWithCallbacks` all exercise sync property logic. They do not need updates. Run them as a sanity check:

```bash
uv run pytest tests/unit/test_gspro_heartbeat.py::TestMatchStateTracking tests/unit/test_gspro_heartbeat.py::TestHeartbeatTimerControl tests/unit/test_gspro_heartbeat.py::TestOnMatchEnded tests/unit/test_gspro_heartbeat.py::TestMatchStateCallbackWiring tests/unit/test_gspro_heartbeat.py::TestHeartbeatIntervalConstant tests/unit/test_gspro_heartbeat.py::TestInitializationWithCallbacks -v
```

Expected: all pass.

### Step group D — Update callers

- [ ] **Step 33: Update `services/connection_manager.py::GSProConnectionManager`**

Replace lines 478-545 with:

```python
async def connect(self, host: str, port: int) -> bool:
    """Connect to GSPro."""
    if self._client is not None:
        await self.disconnect()

    self._host = host
    self._port = port
    self._client = GSProClient(host=host, port=port)
    self._client.add_disconnect_callback(self._on_disconnect)

    # Restore shot number from our persistent storage
    self._client._shot_number = self._shot_number

    success = await self._client.connect()
    self._callback_registry.notify_gspro_connect(success)

    if success:
        logger.info(f"GSPro connected to {host}:{port} via connection manager")
    else:
        logger.warning(f"GSPro connection to {host}:{port} failed")
        self._client = None

    return success

async def disconnect(self) -> None:
    """Disconnect from GSPro."""
    if self._client is not None:
        # Save shot number before disconnect (client resets it)
        self._shot_number = self._client.shot_number
        await self._client.disconnect()
        self._client = None
    logger.info("GSPro disconnected via connection manager")

async def send_shot(self, shot: GC2ShotData) -> None:
    """Send shot to GSPro."""
    if self._client is None or not self._client.is_connected:
        logger.warning("Cannot send shot: GSPro not connected")
        return

    await self._client.send_shot(shot)
    self._shot_number = self._client.shot_number

async def send_status(self, status: GC2BallStatus) -> None:
    """Send ball status to GSPro."""
    if self._client is not None and self._client.is_connected:
        await self._client.send_status(status)
```

Notes:
- `disconnect` was sync; it's now async. The only caller that triggers it from a sync context is `_on_disconnect` (line 547) — see Step 34.
- `send_shot` no longer returns a response; if any caller used the return value (line 269 of the same file: `response = await self._gspro_mgr.send_shot(shot)`), update the caller too (it is fine to ignore the now-`None` return).

- [ ] **Step 34: Update `_on_disconnect` and any sync disconnect callers in `connection_manager.py`**

Search for any callers of `self.disconnect()` inside `GSProConnectionManager`:

```bash
grep -n "self\.disconnect()\|self\._client\.disconnect" src/gc2_connect/services/connection_manager.py
```

Any sync callers (e.g. `_on_disconnect`, or a shutdown handler) need to be async or to schedule the disconnect with `asyncio.create_task(self.disconnect())`. Pick whichever matches the surrounding context:

- If the caller is itself async, `await self.disconnect()`.
- If the caller is sync and inside a running event loop (callback from the client), `asyncio.create_task(self.disconnect())`.

Apply the appropriate fix in each call site within `connection_manager.py`.

- [ ] **Step 35: Update `services/shot_router.py:164`**

Change:
```python
await self._gspro_client.send_shot_async(shot)
```
to:
```python
await self._gspro_client.send_shot(shot)
```

- [ ] **Step 36: Update `ui/app.py:993-994`**

The current code:
```python
if self.send_status_to_gspro and self._gspro_mgr.is_connected:
    self._gspro_mgr.send_status(status)
```
becomes:
```python
if self.send_status_to_gspro and self._gspro_mgr.is_connected:
    await self._gspro_mgr.send_status(status)
```

Verify the enclosing function is `async def`. If it is not (it should be — it's inside the GC2 status handler chain which is async), promote it. Run:

```bash
sed -n '950,1000p' src/gc2_connect/ui/app.py
```

Confirm the enclosing function declaration is `async def`.

- [ ] **Step 37: Check for any other call sites you might have missed**

Run:
```bash
grep -rn "send_shot_async\|send_status_async\|connect_async\|disconnect_async" src/ tests/
```

Expected: empty. If anything turns up, update it (drop the `_async` suffix and add `await`).

### Step group E — Run the full suite

- [ ] **Step 38: Run the new integration tests**

Run:
```bash
uv run pytest tests/integration/test_gspro_client_async.py -v
```

Expected: all five tests pass (newline framing, keepalive, dropped connection, send_shot returns None + ack via callback, bare handshake).

- [ ] **Step 39: Run the heartbeat unit tests**

Run:
```bash
uv run pytest tests/unit/test_gspro_heartbeat.py -v
```

Expected: all pass.

- [ ] **Step 40: Run the full pytest suite**

Run:
```bash
uv run pytest
```

Expected: 0 failures. If a test fails, fix it before continuing — do not move on.

- [ ] **Step 41: Run mypy**

Run:
```bash
uv run mypy src/
```

Expected: 0 errors. Likely fix-ups: type narrowing on `self._writer` (use `assert self._writer is not None` at the top of methods that touch it after the `is_connected` check).

- [ ] **Step 42: Run ruff lint and format check**

Run:
```bash
uv run ruff check . && uv run ruff format --check .
```

Expected: clean. If formatting fails, run `uv run ruff format .` and re-check.

- [ ] **Step 43: Commit**

```bash
git add src/gc2_connect/gspro/client.py \
        src/gc2_connect/services/connection_manager.py \
        src/gc2_connect/services/shot_router.py \
        src/gc2_connect/ui/app.py \
        tests/conftest.py \
        tests/unit/test_gspro_heartbeat.py \
        tests/integration/test_gspro_client_async.py \
        tests/simulators/gspro/server.py
git commit -m "$(cat <<'EOF'
refactor: migrate GSPro client to asyncio.open_connection

Replace sync socket + run_in_executor wrappers with native asyncio
StreamReader/StreamWriter. All send_* methods become async; send_shot
returns None (the ack arrives through the reader loop's response
callbacks). Append \n to every outbound JSON write, matching the
GsProApi.cs reference. Enable SO_KEEPALIVE with platform-appropriate
idle/interval/count on connect.

Update callers in connection_manager, shot_router, and the UI app to
the new async API. Migrate tests/conftest.py gspro_client fixture
and tests/unit/test_gspro_heartbeat.py to AsyncMock + writer patches.
Add tests/integration/test_gspro_client_async.py covering newline
framing, keepalive, dropped-connection handling, send_shot return
shape, and the bare "GSPro ready" handshake.
EOF
)"
```

---

## Task 3: Wire infinite reconnect for GSPro + capped-backoff test

**Files:**
- Modify: `src/gc2_connect/services/connection_manager.py` (where the GSPro `ReconnectionManager` is instantiated)
- Modify: `tests/unit/test_reconnect_manager.py` (append capped-backoff test)

- [ ] **Step 1: Locate the GSPro `ReconnectionManager` instantiation**

Run:
```bash
grep -n "ReconnectionManager" src/gc2_connect/services/connection_manager.py src/gc2_connect/ui/app.py
```

Identify the line where the GSPro `ReconnectionManager` is constructed. (USB-side `ReconnectionManager` is also nearby — do **not** touch it.)

- [ ] **Step 2: Update the GSPro `ReconnectionManager` defaults**

Replace the GSPro construction with:

```python
ReconnectionManager(
    max_retries=None,   # retry forever; user cancels via Disconnect
    base_delay=5.0,
    max_delay=60.0,
)
```

- [ ] **Step 3: Write a unit test for the capped backoff sequence**

Append to `tests/unit/test_reconnect_manager.py`:

```python
class TestCappedBackoff:
    """Test the 5s -> 60s capped exponential backoff used for GSPro."""

    def test_gspro_backoff_sequence(self) -> None:
        mgr = ReconnectionManager(max_retries=None, base_delay=5.0, max_delay=60.0)
        delays = [mgr.get_delay_for_attempt(i) for i in range(7)]
        assert delays == [5.0, 10.0, 20.0, 40.0, 60.0, 60.0, 60.0]
```

- [ ] **Step 4: Run the new test**

Run:
```bash
uv run pytest tests/unit/test_reconnect_manager.py::TestCappedBackoff -v
```

Expected: pass. (No code change should be needed; this is a property assertion on the existing `get_delay_for_attempt` algorithm with new defaults.)

- [ ] **Step 5: Run full CI suite**

Run:
```bash
uv run pytest && uv run mypy src/ && uv run ruff check . && uv run ruff format --check .
```

Expected: all clean.

- [ ] **Step 6: Commit**

```bash
git add src/gc2_connect/services/connection_manager.py tests/unit/test_reconnect_manager.py
git commit -m "$(cat <<'EOF'
feat: GSPro reconnect retries forever with 5s-60s capped backoff

Default GSPro ReconnectionManager to max_retries=None and base/max
delay of 5s/60s. When GSPro restarts, sleeps, or otherwise vanishes,
the client now keeps trying indefinitely until the user explicitly
disconnects.
EOF
)"
```

---

## Task 4: Manual smoke test against the mock server

**Why:** verifies the async path works end-to-end and exercises a real reconnect cycle, which the automated tests only approximate.

**Files:** none modified.

- [ ] **Step 1: Start the mock GSPro server in a separate terminal**

```bash
uv run python tools/mock_gspro_server.py --host 0.0.0.0 --port 921
```

- [ ] **Step 2: Start the app**

```bash
uv run python -m gc2_connect.main
```

- [ ] **Step 3: Connect to GSPro from the UI**

Use the GSPro panel to connect to `127.0.0.1:921`. Confirm "Connected" state.

- [ ] **Step 4: Fire a test shot**

If mock GC2 mode is available, fire a test shot. Confirm in the mock server's terminal that the shot JSON arrived and ended with a newline (the mock server typically logs raw bytes).

- [ ] **Step 5: Kill the mock server mid-session**

In the mock-server terminal, `Ctrl+C` it.

- [ ] **Step 6: Confirm the client transitions to Reconnecting**

The UI should display a "Reconnecting…" indicator. Wait at least 90 seconds and confirm the client is still attempting reconnects — the previous 31-second bound is gone.

- [ ] **Step 7: Restart the mock server**

```bash
uv run python tools/mock_gspro_server.py --host 0.0.0.0 --port 921
```

- [ ] **Step 8: Confirm the client reconnects automatically**

Within ~60 seconds (one cap interval) the client should reconnect, the UI should return to "Connected", and shots should send again.

- [ ] **Step 9: Hit "Disconnect" mid-reconnect**

Kill the mock server again, wait until the UI shows Reconnecting, then click Disconnect. Confirm the loop stops and the UI returns to a clean disconnected state.

- [ ] **Step 10: Record results**

If everything passed, no code change. Note any anomalies in a follow-up.

---

## Spec coverage check

Walking back through `docs/superpowers/specs/2026-05-11-gspro-client-async-migration-design.md`:

| Spec item | Implemented in |
|---|---|
| Outbound `\n` framing | Task 2 (Steps 18, 20); test in Task 2 Step 3 |
| `SO_KEEPALIVE` with platform-specific tuning | Task 2 Step 15; test Step 4 |
| `asyncio.open_connection` migration | Task 2 Step 16 |
| `_send_message` async + drops `expect_response` + drops stale-buffer-clear | Task 2 Step 20 |
| `send_shot` returns `None` | Task 2 Step 19; test Step 6 |
| Reader loop via StreamReader with `_drain_buffer` fallback | Task 2 Step 21; test Step 5 |
| Bare `GSPro ready` handshake | Task 2 Step 21; test Step 7 |
| `disconnect` async with `writer.close()` + `wait_closed()` | Task 2 Step 17 |
| Remove `*_async` sync wrappers | Task 2 Steps 24, 33-37 |
| `_on_match_started`, `set_hardware_ready` schedule via `create_task` | Task 2 Steps 12, 13; tests in Steps 27, 28 |
| `ReconnectionManager.max_retries: int \| None = None` | Task 1 Steps 4, 5; tests Step 2 |
| GSPro reconnect defaults (None, 5s, 60s) | Task 3 Step 2; test Step 3 |
| Caller ripple in connection_manager / shot_router / app | Task 2 Steps 33-36 |
| `conftest.py` fixture async | Task 2 Step 25 |
| `test_gspro_heartbeat.py` AsyncMock updates | Task 2 Steps 26-31 |
| Manual smoke test | Task 4 |

Spec is fully covered.
