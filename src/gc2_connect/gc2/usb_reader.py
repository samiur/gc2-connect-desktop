# ABOUTME: USB communication handler for the Foresight GC2 launch monitor.
# ABOUTME: Reads shot data via USB bulk transfer and provides mock reader for testing.
"""GC2 USB communication handler."""

from __future__ import annotations

import asyncio
import logging
from collections.abc import Callable
from typing import Any

try:
    import usb.backend.libusb1
    import usb.core
    import usb.util

    USB_AVAILABLE = True
except ImportError:
    USB_AVAILABLE = False

from gc2_connect.models import GC2BallStatus, GC2ShotData

logger = logging.getLogger(__name__)

# GC2 USB identifiers
GC2_VENDOR_ID = 0x2C79
GC2_PRODUCT_ID = 0x0110


class GC2USBReader:
    """Handles USB communication with the GC2 launch monitor."""

    def __init__(self) -> None:
        self.dev: Any = None
        self.endpoint_in: Any = None  # BULK IN for data
        self.endpoint_out: Any = None  # BULK OUT for commands
        self.endpoint_intr: Any = None  # INTERRUPT IN for notifications
        self.last_shot_id = 0
        self._running = False
        self._connected = False
        self._callbacks: list[Callable[[GC2ShotData], None]] = []
        self._status_callbacks: list[Callable[[GC2BallStatus], None]] = []
        self._last_status: GC2BallStatus | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_status(self) -> GC2BallStatus | None:
        """Get the most recent ball status."""
        return self._last_status

    def add_shot_callback(self, callback: Callable[[GC2ShotData], None]) -> None:
        """Add a callback to be called when a shot is received."""
        self._callbacks.append(callback)

    def remove_shot_callback(self, callback: Callable[[GC2ShotData], None]) -> None:
        """Remove a shot callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def add_status_callback(self, callback: Callable[[GC2BallStatus], None]) -> None:
        """Add a callback to be called when ball status changes."""
        self._status_callbacks.append(callback)

    def remove_status_callback(self, callback: Callable[[GC2BallStatus], None]) -> None:
        """Remove a status callback."""
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)

    def _notify_shot(self, shot: GC2ShotData) -> None:
        """Notify all callbacks of a new shot."""
        for callback in self._callbacks:
            try:
                callback(shot)
            except Exception as e:
                logger.error(f"Shot callback error: {e}")

    def _notify_status(self, status: GC2BallStatus) -> None:
        """Notify all callbacks of a status change."""
        for callback in self._status_callbacks:
            try:
                callback(status)
            except Exception as e:
                logger.error(f"Status callback error: {e}")

    def find_device(self) -> bool:
        """Find the GC2 USB device."""
        if not USB_AVAILABLE:
            logger.error("pyusb not installed")
            return False

        self.dev = usb.core.find(idVendor=GC2_VENDOR_ID, idProduct=GC2_PRODUCT_ID)

        if self.dev is None:
            logger.warning(f"GC2 not found (VID=0x{GC2_VENDOR_ID:04X}, PID=0x{GC2_PRODUCT_ID:04X})")
            return False

        logger.info(f"Found GC2: VID=0x{self.dev.idVendor:04X} PID=0x{self.dev.idProduct:04X}")
        return True

    def _log_device_info(self) -> None:
        """Log detailed USB device information for debugging."""
        if not self.dev:
            return

        logger.info("=== GC2 USB Device Info ===")
        try:
            manufacturer = usb.util.get_string(self.dev, self.dev.iManufacturer)
            product = usb.util.get_string(self.dev, self.dev.iProduct)
            serial = usb.util.get_string(self.dev, self.dev.iSerialNumber)
            logger.info(f"Manufacturer: {manufacturer}")
            logger.info(f"Product: {product}")
            logger.info(f"Serial: {serial}")
        except Exception as e:
            logger.debug(f"Could not get device strings: {e}")

        logger.info(f"Device class: {self.dev.bDeviceClass}")
        logger.info(f"Num configurations: {self.dev.bNumConfigurations}")

        for cfg in self.dev:
            logger.info(f"  Configuration {cfg.bConfigurationValue}:")
            for intf in cfg:
                logger.info(f"    Interface {intf.bInterfaceNumber}, Alt {intf.bAlternateSetting}:")
                logger.info(
                    f"      Class: {intf.bInterfaceClass}, Subclass: {intf.bInterfaceSubClass}"
                )
                logger.info(f"      Num endpoints: {intf.bNumEndpoints}")
                for ep in intf:
                    direction = (
                        "IN"
                        if usb.util.endpoint_direction(ep.bEndpointAddress) == usb.util.ENDPOINT_IN
                        else "OUT"
                    )
                    ep_type = {
                        usb.util.ENDPOINT_TYPE_CTRL: "CTRL",
                        usb.util.ENDPOINT_TYPE_ISO: "ISO",
                        usb.util.ENDPOINT_TYPE_BULK: "BULK",
                        usb.util.ENDPOINT_TYPE_INTR: "INTR",
                    }.get(usb.util.endpoint_type(ep.bmAttributes), "???")
                    logger.info(
                        f"        EP 0x{ep.bEndpointAddress:02X}: {direction} {ep_type}, max={ep.wMaxPacketSize}"
                    )
        logger.info("=== End Device Info ===")

    def connect(self) -> bool:
        """Connect to the GC2."""
        if not self.find_device():
            return False

        try:
            # Log device info for debugging
            self._log_device_info()

            # Detach kernel driver if necessary (Linux/Mac)
            for i in range(4):  # Try multiple interfaces
                try:
                    if self.dev.is_kernel_driver_active(i):
                        logger.info(f"Detaching kernel driver from interface {i}...")
                        self.dev.detach_kernel_driver(i)
                except (usb.core.USBError, NotImplementedError):
                    pass  # Not supported on all platforms

            # Set configuration
            self.dev.set_configuration()

            # Get the active configuration
            cfg = self.dev.get_active_configuration()
            logger.info(f"Active configuration: {cfg.bConfigurationValue}")

            # Find all endpoints
            self.endpoint_in = None
            self.endpoint_out = None
            self.endpoint_intr = None

            for intf in cfg:
                logger.info(f"Checking interface {intf.bInterfaceNumber}...")
                for ep in intf:
                    ep_type = usb.util.endpoint_type(ep.bmAttributes)
                    direction = usb.util.endpoint_direction(ep.bEndpointAddress)

                    if direction == usb.util.ENDPOINT_IN:
                        if ep_type == usb.util.ENDPOINT_TYPE_BULK:
                            logger.info(f"Found BULK IN endpoint: 0x{ep.bEndpointAddress:02X}")
                            self.endpoint_in = ep
                        elif ep_type == usb.util.ENDPOINT_TYPE_INTR:
                            logger.info(f"Found INTERRUPT IN endpoint: 0x{ep.bEndpointAddress:02X}")
                            self.endpoint_intr = ep
                    elif (
                        direction == usb.util.ENDPOINT_OUT
                        and ep_type == usb.util.ENDPOINT_TYPE_BULK
                    ):
                        logger.info(f"Found BULK OUT endpoint: 0x{ep.bEndpointAddress:02X}")
                        self.endpoint_out = ep

            if self.endpoint_in is None and self.endpoint_intr is None:
                logger.error("Could not find any IN endpoint")
                return False

            logger.info("Connected to GC2!")
            if self.endpoint_in:
                logger.info(f"  BULK IN: 0x{self.endpoint_in.bEndpointAddress:02X}")
            if self.endpoint_out:
                logger.info(f"  BULK OUT: 0x{self.endpoint_out.bEndpointAddress:02X}")
            if self.endpoint_intr:
                logger.info(f"  INTERRUPT IN: 0x{self.endpoint_intr.bEndpointAddress:02X}")

            self._connected = True
            return True

        except usb.core.USBError as e:
            logger.error(f"USB connection error: {e}")
            return False

    def disconnect(self) -> None:
        """Disconnect from the GC2."""
        self._running = False
        self._connected = False

        if self.dev:
            try:
                usb.util.dispose_resources(self.dev)
            except Exception:
                pass
            self.dev = None
            self.endpoint_in = None
            self.endpoint_out = None
            self.endpoint_intr = None

        logger.info("Disconnected from GC2")

    def parse_data(self, raw_text: str) -> GC2ShotData | None:
        """Parse raw GC2 text data into a ShotData object."""
        data_dict = {}

        for line in raw_text.strip().split("\n"):
            line = line.strip()
            if "=" not in line:
                continue

            key, value = line.split("=", 1)
            data_dict[key.strip()] = value.strip()

        if not data_dict:
            return None

        shot = GC2ShotData.from_gc2_dict(data_dict)

        if not shot.is_valid():
            logger.warning(f"Invalid shot data rejected: {data_dict}")
            return None

        return shot

    def _is_complete_shot(self, msg: str) -> bool:
        """Check if a shot message has all required fields."""
        has_shot_id = "SHOT_ID=" in msg
        has_speed = "SPEED_MPH=" in msg
        has_total_spin = "SPIN_RPM=" in msg
        has_back_spin = "BACK_RPM=" in msg
        has_side_spin = "SIDE_RPM=" in msg

        # Need basic fields plus spin components for complete data
        return has_shot_id and has_speed and has_total_spin and (has_back_spin or has_side_spin)

    def _has_minimum_data(self, msg: str) -> bool:
        """Check if message has minimum required fields for a valid shot."""
        has_shot_id = "SHOT_ID=" in msg
        has_speed = "SPEED_MPH=" in msg
        has_total_spin = "SPIN_RPM=" in msg
        return has_shot_id and has_speed and has_total_spin

    def _extract_shot_message(self, buffer: str) -> tuple[str | None, str]:
        """
        Extract a complete 0H shot message from the buffer.

        The GC2 sends two types of messages:
        - 0M: Ball tracking/position updates (ignore these)
        - 0H: Actual shot data with metrics

        Messages are split across 64-byte USB packets.
        Shot messages contain: SHOT_ID, SPEED_MPH, ELEVATION_DEG, AZIMUTH_DEG,
        SPIN_RPM, BACK_RPM, SIDE_RPM (and possibly more fields).

        We wait for SIDE_RPM or BACK_RPM to ensure we have complete spin data.

        Returns:
            (shot_message, remaining_buffer) - shot_message is None if no complete shot found
        """
        # Find the start of a 0H message
        h_start = buffer.find("0H\n")
        if h_start == -1:
            # No shot message started yet - clear any 0M messages
            # Keep only from the last 0M or 0H marker
            last_m = buffer.rfind("0M\n")
            if last_m != -1:
                # Discard everything before the current 0M message
                return None, buffer[last_m:]
            return None, buffer

        # We have a 0H message starting
        remaining = buffer[h_start:]

        # Find where the shot data ends (next 0M or 0H marker)
        next_m = remaining.find("0M\n", 3)
        next_h = remaining.find("0H\n", 3)

        # If there's a next message marker, extract everything before it
        if next_m != -1 and (next_h == -1 or next_m < next_h):
            # 0M comes first - shot message ends before it
            shot_msg = remaining[:next_m]
            new_buffer = remaining[next_m:]
            # Only return if the EXTRACTED message has complete data
            if self._is_complete_shot(shot_msg):
                return shot_msg, new_buffer
            # If not complete but has minimum data, still accept it
            # (device may not send back/side spin)
            if self._has_minimum_data(shot_msg):
                logger.debug(f"Shot message missing spin components: {shot_msg!r}")
                return shot_msg, new_buffer
            return None, new_buffer
        elif next_h != -1:
            # Another 0H comes - check if it's same shot or different
            shot_msg = remaining[:next_h]
            new_buffer = remaining[next_h:]

            # Check the EXTRACTED shot_msg, not the full buffer
            if self._is_complete_shot(shot_msg):
                return shot_msg, new_buffer

            # Check if the next 0H is the same shot (continuation)
            # by comparing SHOT_ID
            current_id = None
            next_id = None
            for line in shot_msg.split("\n"):
                if line.strip().startswith("SHOT_ID="):
                    current_id = line.split("=")[1].strip()
                    break
            for line in new_buffer.split("\n")[:5]:
                if line.strip().startswith("SHOT_ID="):
                    next_id = line.split("=")[1].strip()
                    break

            if current_id and next_id and current_id == next_id:
                # Same shot ID - this is a duplicate/update, skip the first one
                # and wait for the more complete one
                return None, new_buffer

            # Different shot - accept current if it has minimum data
            if self._has_minimum_data(shot_msg):
                logger.debug(f"Shot message missing spin components: {shot_msg!r}")
                return shot_msg, new_buffer
            return None, new_buffer

        # No next marker yet - check if message appears complete
        if self._is_complete_shot(remaining):
            return remaining, ""

        # Message is incomplete - wait for more data
        return None, buffer[h_start:]

    def _parse_gc2_fields(
        self, text: str, accumulator: dict[str, str], line_buffer: str
    ) -> tuple[dict[str, str], str]:
        """
        Parse GC2 field data and accumulate into dictionary.

        This mimics the gc2_to_TGC approach where data is accumulated
        across multiple USB reads until a complete shot is received.

        Handles partial lines split across 64-byte USB packets by buffering
        incomplete lines until the next packet completes them.

        Args:
            text: Raw text from current USB packet
            accumulator: Dictionary to accumulate key=value pairs into
            line_buffer: Any incomplete line from previous packet

        Returns:
            (accumulator, remaining_buffer) - remaining_buffer contains any
            incomplete line at the end of the current packet
        """
        # Prepend any incomplete line from previous packet
        full_text = line_buffer + text

        # Split into lines - lines ending with \n are complete
        lines = full_text.split("\n")

        # The last element might be incomplete (no trailing \n)
        # Keep it in the buffer for the next packet
        remaining = lines[-1] if not full_text.endswith("\n") else ""
        complete_lines = lines[:-1] if not full_text.endswith("\n") else lines

        for line in complete_lines:
            line = line.strip()
            if "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip()
            if key and value:
                accumulator[key] = value

        return accumulator, remaining

    async def read_loop(self, timeout: int = 1000) -> None:
        """Async read loop - reads shots from USB and calls callbacks."""
        if not self.endpoint_in and not self.endpoint_intr:
            logger.error("Not connected - no endpoints!")
            return

        self._running = True
        shot_accumulator: dict[str, str] = {}  # Accumulate fields across packets
        line_buffer = ""  # Buffer for incomplete lines split across packets
        timeout_count = 0

        logger.info("Starting GC2 read loop...")

        # Determine which endpoints to read from
        endpoints_to_try = []
        if self.endpoint_intr:
            endpoints_to_try.append(("INTR", self.endpoint_intr))
        if self.endpoint_in:
            endpoints_to_try.append(("BULK", self.endpoint_in))

        for ep_name, ep in endpoints_to_try:
            logger.info(f"Will monitor {ep_name} endpoint: 0x{ep.bEndpointAddress:02X}")

        logger.info("Listening for shots...")

        while self._running:
            # Try reading from all endpoints
            for ep_name, ep in endpoints_to_try:
                # Drain all available packets from this endpoint before moving on
                # This prevents missing rapidly-arriving packets
                packets_read = 0
                while True:
                    try:
                        # Read from USB endpoint (run in thread pool to avoid blocking)
                        def read_endpoint(endpoint: Any = ep) -> Any:
                            return self.dev.read(
                                endpoint.bEndpointAddress,
                                endpoint.wMaxPacketSize,
                                timeout=50,  # Shorter timeout to drain buffer quickly
                            )

                        data = await asyncio.get_event_loop().run_in_executor(
                            None,
                            read_endpoint,
                        )

                        packets_read += 1
                        timeout_count = 0

                        # Convert to string
                        text = "".join(chr(x) for x in data if x != 0)

                        # Log ALL received data for debugging
                        # Shot-relevant packets at INFO, others at DEBUG
                        is_shot_data = (
                            "SHOT_ID" in text
                            or "SPIN_RPM" in text
                            or "BACK_RPM" in text
                            or "SIDE_RPM" in text
                        )
                        is_tracking = "0M" in text
                        ends_with_terminator = text.endswith("\n\t") or text.endswith("\t")

                        if is_shot_data:
                            logger.info(
                                f"USB RX [{ep_name}] ({len(data)} bytes) [term={ends_with_terminator}]: {text!r}"
                            )
                        elif is_tracking:
                            logger.debug(f"USB RX [{ep_name}] 0M tracking: {text!r}")
                        else:
                            # Log ALL other packets so we can see what's being received
                            logger.info(
                                f"USB RX [{ep_name}] ({len(data)} bytes) [term={ends_with_terminator}] OTHER: {text!r}"
                            )

                        # Debug: log line buffer state when processing shot data
                        if is_shot_data and line_buffer:
                            logger.debug(f"Line buffer before parse: {line_buffer!r}")

                        # Handle 0M (ball tracking) messages separately from shot data
                        if "0M" in text:
                            # Parse 0M message for ball status
                            status_accumulator: dict[str, str] = {}
                            status_accumulator, _ = self._parse_gc2_fields(
                                text, status_accumulator, ""
                            )

                            if status_accumulator:
                                new_status = GC2BallStatus.from_gc2_dict(status_accumulator)

                                # Only notify if status actually changed
                                status_changed = (
                                    self._last_status is None
                                    or self._last_status.flags != new_status.flags
                                    or self._last_status.ball_count != new_status.ball_count
                                )

                                if status_changed:
                                    ready_str = "READY" if new_status.is_ready else "NOT READY"
                                    ball_str = (
                                        f"{new_status.ball_count} ball(s)"
                                        if new_status.ball_detected
                                        else "no ball"
                                    )
                                    logger.info(
                                        f"GC2 Status: {ready_str}, {ball_str} "
                                        f"(FLAGS={new_status.flags}, pos={new_status.ball_position})"
                                    )
                                    self._last_status = new_status
                                    self._notify_status(new_status)

                            # Don't accumulate 0M fields into shot data
                            continue

                        # Check if this is a new shot ID - if so, clear stale data
                        if "0H" in text and "SHOT_ID" in text:
                            # Extract the new shot ID from the text
                            for line in text.split("\n"):
                                if "SHOT_ID=" in line:
                                    new_id = line.split("=")[1].strip()
                                    old_id = shot_accumulator.get("SHOT_ID")
                                    if old_id and old_id != new_id:
                                        logger.warning(
                                            f"Incomplete shot #{old_id} discarded "
                                            f"(had: {list(shot_accumulator.keys())})"
                                        )
                                        shot_accumulator.clear()
                                        line_buffer = ""
                                    break

                        shot_accumulator, line_buffer = self._parse_gc2_fields(
                            text, shot_accumulator, line_buffer
                        )

                        # Debug: show accumulator state after parsing shot data
                        if is_shot_data:
                            logger.debug(
                                f"Accumulator after parse: {list(shot_accumulator.keys())}"
                            )
                            if line_buffer:
                                logger.debug(f"Line buffer after parse: {line_buffer!r}")

                        # Check if message is complete (ends with \n\t)
                        # GC2 messages terminate with \n\t as the final delimiter
                        message_complete = text.endswith("\n\t") or text.endswith("\t")

                        if message_complete:
                            # Check if we have shot data to process
                            current_shot_id = shot_accumulator.get("SHOT_ID")
                            has_speed = "SPEED_MPH" in shot_accumulator
                            has_total_spin = "SPIN_RPM" in shot_accumulator

                            if current_shot_id and has_speed and has_total_spin:
                                shot_id_int = int(float(current_shot_id))

                                # Check if this is a new shot (different ID from last processed)
                                if shot_id_int != self.last_shot_id:
                                    logger.info(f"Complete shot data: {shot_accumulator}")

                                    shot = GC2ShotData.from_gc2_dict(shot_accumulator)
                                    if shot.is_valid():
                                        self.last_shot_id = shot_id_int
                                        spin_info = f"spin={shot.total_spin:.0f}"
                                        if shot.back_spin or shot.side_spin:
                                            spin_info += f" (back={shot.back_spin:.0f}, side={shot.side_spin:.0f}, axis={shot.spin_axis:.1f}°)"
                                        else:
                                            spin_info += " (no spin components from device)"
                                        logger.info(
                                            f"Shot #{shot.shot_id}: {shot.ball_speed:.1f} mph, "
                                            f"{spin_info}, launch={shot.launch_angle:.1f}°"
                                        )
                                        self._notify_shot(shot)

                                    else:
                                        logger.warning(
                                            f"Invalid shot data rejected: {shot_accumulator}"
                                        )

                                    # Clear accumulator for next shot
                                    shot_accumulator.clear()
                                    line_buffer = ""  # Also clear line buffer

                    except usb.core.USBTimeoutError:
                        # No more data on this endpoint - move to next endpoint
                        break
                    except usb.core.USBError as e:
                        if "timeout" not in str(e).lower():
                            logger.error(f"USB read error on {ep_name}: {e}")
                        break

            # Count timeouts for logging
            timeout_count += 1
            if timeout_count % 100 == 0 and shot_accumulator:
                logger.debug(
                    f"Waiting for GC2 data... (accumulated fields: {list(shot_accumulator.keys())})"
                )

            try:
                await asyncio.sleep(0.01)
            except asyncio.CancelledError:
                break

        self._running = False
        logger.info("GC2 read loop stopped")

    @staticmethod
    def list_devices() -> list[dict[str, str]]:
        """List all USB devices."""
        if not USB_AVAILABLE:
            return []

        devices = []
        for dev in usb.core.find(find_all=True):
            try:
                manufacturer = (
                    usb.util.get_string(dev, dev.iManufacturer) if dev.iManufacturer else ""
                )
                product = usb.util.get_string(dev, dev.iProduct) if dev.iProduct else ""
                serial = usb.util.get_string(dev, dev.iSerialNumber) if dev.iSerialNumber else ""
            except Exception:
                manufacturer = product = serial = ""

            devices.append(
                {
                    "vendor_id": f"0x{dev.idVendor:04X}",
                    "product_id": f"0x{dev.idProduct:04X}",
                    "manufacturer": manufacturer,
                    "product": product,
                    "serial": serial,
                }
            )

        return devices


class MockGC2Reader:
    """Mock GC2 reader for testing without hardware."""

    def __init__(self) -> None:
        self._connected = False
        self._running = False
        self._callbacks: list[Callable[[GC2ShotData], None]] = []
        self._status_callbacks: list[Callable[[GC2BallStatus], None]] = []
        self._shot_number = 0
        self._last_status: GC2BallStatus | None = None

    @property
    def is_connected(self) -> bool:
        return self._connected

    @property
    def is_running(self) -> bool:
        return self._running

    @property
    def last_status(self) -> GC2BallStatus | None:
        return self._last_status

    def add_shot_callback(self, callback: Callable[[GC2ShotData], None]) -> None:
        self._callbacks.append(callback)

    def remove_shot_callback(self, callback: Callable[[GC2ShotData], None]) -> None:
        if callback in self._callbacks:
            self._callbacks.remove(callback)

    def add_status_callback(self, callback: Callable[[GC2BallStatus], None]) -> None:
        self._status_callbacks.append(callback)

    def remove_status_callback(self, callback: Callable[[GC2BallStatus], None]) -> None:
        if callback in self._status_callbacks:
            self._status_callbacks.remove(callback)

    def connect(self) -> bool:
        self._connected = True
        logger.info("Mock GC2 connected")
        # Simulate initial status: ready with ball detected
        self._last_status = GC2BallStatus(flags=7, ball_count=1, ball_position=(200, 200, 10))
        for callback in self._status_callbacks:
            try:
                callback(self._last_status)
            except Exception as e:
                logger.error(f"Status callback error: {e}")
        return True

    def disconnect(self) -> None:
        self._connected = False
        self._running = False
        logger.info("Mock GC2 disconnected")

    async def read_loop(self, timeout: int = 10000) -> None:
        """Mock read loop - doesn't do anything, use send_test_shot() to simulate."""
        self._running = True
        while self._running:
            await asyncio.sleep(1)
        self._running = False

    def send_test_shot(self) -> None:
        """Send a simulated test shot."""
        import random

        self._shot_number += 1

        shot = GC2ShotData(
            shot_id=self._shot_number,
            ball_speed=140 + random.uniform(-20, 20),
            launch_angle=12 + random.uniform(-3, 3),
            horizontal_launch_angle=random.uniform(-5, 5),
            total_spin=2500 + random.uniform(-500, 500),
            back_spin=2300 + random.uniform(-400, 400),
            side_spin=random.uniform(-500, 500),
            club_speed=100 + random.uniform(-15, 15),
            swing_path=random.uniform(-5, 5),
            angle_of_attack=random.uniform(-6, 2),
            face_to_target=random.uniform(-3, 3),
        )

        logger.info(f"Test shot #{shot.shot_id}: {shot.ball_speed:.1f} mph")

        for callback in self._callbacks:
            try:
                callback(shot)
            except Exception as e:
                logger.error(f"Shot callback error: {e}")
