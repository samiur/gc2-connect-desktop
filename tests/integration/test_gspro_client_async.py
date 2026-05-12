# ABOUTME: Integration tests for GSProClient async I/O behavior against MockGSProServer.
# ABOUTME: Covers newline framing, keepalive, dropped-connection handling, and handshake.
"""Async integration tests for GSProClient."""

from __future__ import annotations

import asyncio
import socket

import pytest

from gc2_connect.gspro.client import GSProClient
from gc2_connect.models import GC2BallStatus, GC2ShotData
from tests.simulators.gspro.config import MockGSProServerConfig, ResponseType
from tests.simulators.gspro.server import MockGSProServer


class TestNewlineFraming:
    @pytest.mark.asyncio
    async def test_every_outbound_write_ends_in_newline(self) -> None:
        async with MockGSProServer(MockGSProServerConfig()) as server:
            client = GSProClient(host=server.host, port=server.port)
            connected = await client.connect()
            assert connected

            try:
                shot = GC2ShotData(
                    ball_speed=140.0,
                    launch_angle=12.0,
                    horizontal_launch_angle=1.0,
                    total_spin=2500.0,
                    back_spin=2400.0,
                    side_spin=-200.0,
                )
                await client.send_shot(shot)
                await client.send_heartbeat()
                await client.send_status(GC2BallStatus(flags=7, ball_count=1))

                await asyncio.sleep(0.1)
            finally:
                await client.disconnect()

            raw = b"".join(server.received_raw_bytes)
            assert raw.count(b"\n") >= 4  # initial registration heartbeat + 3 above
            for idx, b in enumerate(raw):
                if b == 0x0A:
                    assert raw[idx - 1 : idx] == b"}", (
                        f"Newline at offset {idx} not preceded by '}}': "
                        f"context={raw[max(0, idx - 20) : idx + 1]!r}"
                    )


class TestKeepalive:
    @pytest.mark.asyncio
    async def test_so_keepalive_enabled_after_connect(self) -> None:
        async with MockGSProServer(MockGSProServerConfig()) as server:
            client = GSProClient(host=server.host, port=server.port)
            await client.connect()
            try:
                assert client._writer is not None
                sock = client._writer.get_extra_info("socket")
                ka = sock.getsockopt(socket.SOL_SOCKET, socket.SO_KEEPALIVE)
                assert ka != 0  # Non-zero means keepalive is enabled
            finally:
                await client.disconnect()


class TestDroppedConnection:
    @pytest.mark.asyncio
    async def test_reader_loop_triggers_disconnect_callback_on_eof(self) -> None:
        disconnect_fired = asyncio.Event()

        async with MockGSProServer(MockGSProServerConfig()) as server:
            client = GSProClient(host=server.host, port=server.port)
            client.add_disconnect_callback(lambda: disconnect_fired.set())
            await client.connect()

            # Give the server handler time to register the connection
            await asyncio.sleep(0.1)
            await server.close_all_connections()

            await asyncio.wait_for(disconnect_fired.wait(), timeout=2.0)
            assert client.is_connected is False


class TestSendShotReturnsNone:
    @pytest.mark.asyncio
    async def test_send_shot_returns_none_and_ack_arrives_via_callback(self) -> None:
        async with MockGSProServer(
            MockGSProServerConfig(
                response_type=ResponseType.SUCCESS,
            )
        ) as server:
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
                    ball_speed=140.0,
                    launch_angle=12.0,
                    horizontal_launch_angle=1.0,
                    total_spin=2500.0,
                    back_spin=2400.0,
                    side_spin=-200.0,
                )
                result = await client.send_shot(shot)
                assert result is None

                await asyncio.wait_for(ack_received.wait(), timeout=2.0)
                assert any(r.Code == 200 for r in seen)
            finally:
                await client.disconnect()


class TestBareHandshake:
    @pytest.mark.asyncio
    async def test_bare_gspro_ready_string_fires_match_started(self) -> None:
        async with MockGSProServer(MockGSProServerConfig()) as server:
            client = GSProClient(host=server.host, port=server.port)
            match_started = asyncio.Event()
            client.add_match_started_callback(lambda: match_started.set())
            await client.connect()

            try:
                # Give the server handler time to register the connection
                await asyncio.sleep(0.1)
                await server.send_raw_to_clients(b"GSPro ready\n")
                await asyncio.wait_for(match_started.wait(), timeout=2.0)
                assert client.match_started is True
            finally:
                await client.disconnect()
