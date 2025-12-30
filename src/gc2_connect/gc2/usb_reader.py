"""GC2 USB communication handler."""

from __future__ import annotations

import asyncio
import logging
from typing import Callable, Optional

try:
    import usb.core
    import usb.util
    import usb.backend.libusb1
    USB_AVAILABLE = True
except ImportError:
    USB_AVAILABLE = False

from gc2_connect.models import GC2ShotData

logger = logging.getLogger(__name__)

# GC2 USB identifiers
GC2_VENDOR_ID = 0x2C79
GC2_PRODUCT_ID = 0x0110


class GC2USBReader:
    """Handles USB communication with the GC2 launch monitor."""
    
    def __init__(self):
        self.dev = None
        self.endpoint = None
        self.last_shot_id = 0
        self._running = False
        self._connected = False
        self._callbacks: list[Callable[[GC2ShotData], None]] = []
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def add_shot_callback(self, callback: Callable[[GC2ShotData], None]):
        """Add a callback to be called when a shot is received."""
        self._callbacks.append(callback)
    
    def remove_shot_callback(self, callback: Callable[[GC2ShotData], None]):
        """Remove a shot callback."""
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def _notify_shot(self, shot: GC2ShotData):
        """Notify all callbacks of a new shot."""
        for callback in self._callbacks:
            try:
                callback(shot)
            except Exception as e:
                logger.error(f"Shot callback error: {e}")
    
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
    
    def connect(self) -> bool:
        """Connect to the GC2."""
        if not self.find_device():
            return False
        
        try:
            # Detach kernel driver if necessary (Linux/Mac)
            try:
                if self.dev.is_kernel_driver_active(0):
                    logger.info("Detaching kernel driver...")
                    self.dev.detach_kernel_driver(0)
            except (usb.core.USBError, NotImplementedError):
                pass  # Not supported on all platforms
            
            # Set configuration
            self.dev.set_configuration()
            
            # Get the active configuration
            cfg = self.dev.get_active_configuration()
            intf = cfg[(0, 0)]
            
            # Find the IN endpoint
            self.endpoint = usb.util.find_descriptor(
                intf,
                custom_match=lambda e: usb.util.endpoint_direction(e.bEndpointAddress) == usb.util.ENDPOINT_IN
            )
            
            if self.endpoint is None:
                logger.error("Could not find IN endpoint")
                return False
            
            logger.info(f"Connected to GC2! Endpoint: 0x{self.endpoint.bEndpointAddress:02X}")
            self._connected = True
            return True
            
        except usb.core.USBError as e:
            logger.error(f"USB connection error: {e}")
            return False
    
    def disconnect(self):
        """Disconnect from the GC2."""
        self._running = False
        self._connected = False
        
        if self.dev:
            try:
                usb.util.dispose_resources(self.dev)
            except Exception:
                pass
            self.dev = None
            self.endpoint = None
        
        logger.info("Disconnected from GC2")
    
    def parse_data(self, raw_text: str) -> Optional[GC2ShotData]:
        """Parse raw GC2 text data into a ShotData object."""
        data_dict = {}
        
        for line in raw_text.strip().split('\n'):
            line = line.strip()
            if '=' not in line:
                continue
            
            key, value = line.split('=', 1)
            data_dict[key.strip()] = value.strip()
        
        if not data_dict:
            return None
        
        shot = GC2ShotData.from_gc2_dict(data_dict)
        
        if not shot.is_valid():
            logger.warning(f"Invalid shot data rejected: {data_dict}")
            return None
        
        return shot
    
    async def read_loop(self, timeout: int = 10000):
        """Async read loop - reads shots from USB and calls callbacks."""
        if not self.endpoint:
            logger.error("Not connected!")
            return
        
        self._running = True
        buffer = ""
        
        logger.info("Starting GC2 read loop...")
        
        while self._running:
            try:
                # Read from USB endpoint (run in thread pool to avoid blocking)
                data = await asyncio.get_event_loop().run_in_executor(
                    None,
                    lambda: self.dev.read(
                        self.endpoint.bEndpointAddress,
                        self.endpoint.wMaxPacketSize,
                        timeout=timeout
                    )
                )
                
                # Convert to string
                text = ''.join(chr(x) for x in data if x != 0)
                buffer += text
                
                # Check for complete message
                if '\n' in buffer:
                    lines = buffer.split('\n')
                    buffer = lines[-1]
                    
                    for line in lines[:-1]:
                        if line.strip():
                            shot = self.parse_data(line)
                            if shot and shot.shot_id != self.last_shot_id:
                                self.last_shot_id = shot.shot_id
                                logger.info(f"Shot #{shot.shot_id}: {shot.ball_speed:.1f} mph")
                                self._notify_shot(shot)
                
            except usb.core.USBTimeoutError:
                # Timeout is normal - no data available
                await asyncio.sleep(0.01)
            except usb.core.USBError as e:
                logger.error(f"USB read error: {e}")
                self._connected = False
                await asyncio.sleep(1)
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Unexpected error: {e}")
                await asyncio.sleep(1)
        
        self._running = False
        logger.info("GC2 read loop stopped")
    
    @staticmethod
    def list_devices() -> list[dict]:
        """List all USB devices."""
        if not USB_AVAILABLE:
            return []
        
        devices = []
        for dev in usb.core.find(find_all=True):
            try:
                manufacturer = usb.util.get_string(dev, dev.iManufacturer) if dev.iManufacturer else ""
                product = usb.util.get_string(dev, dev.iProduct) if dev.iProduct else ""
                serial = usb.util.get_string(dev, dev.iSerialNumber) if dev.iSerialNumber else ""
            except Exception:
                manufacturer = product = serial = ""
            
            devices.append({
                "vendor_id": f"0x{dev.idVendor:04X}",
                "product_id": f"0x{dev.idProduct:04X}",
                "manufacturer": manufacturer,
                "product": product,
                "serial": serial,
            })
        
        return devices


class MockGC2Reader:
    """Mock GC2 reader for testing without hardware."""
    
    def __init__(self):
        self._connected = False
        self._running = False
        self._callbacks: list[Callable[[GC2ShotData], None]] = []
        self._shot_number = 0
    
    @property
    def is_connected(self) -> bool:
        return self._connected
    
    @property
    def is_running(self) -> bool:
        return self._running
    
    def add_shot_callback(self, callback: Callable[[GC2ShotData], None]):
        self._callbacks.append(callback)
    
    def remove_shot_callback(self, callback: Callable[[GC2ShotData], None]):
        if callback in self._callbacks:
            self._callbacks.remove(callback)
    
    def connect(self) -> bool:
        self._connected = True
        logger.info("Mock GC2 connected")
        return True
    
    def disconnect(self):
        self._connected = False
        self._running = False
        logger.info("Mock GC2 disconnected")
    
    async def read_loop(self, timeout: int = 10000):
        """Mock read loop - doesn't do anything, use send_test_shot() to simulate."""
        self._running = True
        while self._running:
            await asyncio.sleep(1)
        self._running = False
    
    def send_test_shot(self):
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
