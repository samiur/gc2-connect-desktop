# macOS USB Setup for GC2

This guide covers USB setup for the Foresight GC2 launch monitor on macOS.

## Prerequisites

### Install libusb

GC2 Connect requires libusb for USB communication. Install it with Homebrew:

```bash
brew install libusb
```

If you don't have Homebrew, install it first:
```bash
/bin/bash -c "$(curl -fsSL https://raw.githubusercontent.com/Homebrew/install/HEAD/install.sh)"
```

## USB Permissions

Unlike Linux, macOS handles USB device permissions differently and typically allows user-level access to USB devices without additional configuration.

### Standard Setup

For most users, simply connecting the GC2 should work:

1. Power on your GC2
2. Connect it to your Mac via USB
3. Run GC2 Connect Desktop

### Verifying Connection

You can verify the GC2 is detected in System Information:

1. Click the Apple menu ()
2. Hold Option and click "System Information..."
3. Navigate to Hardware > USB
4. Look for "Foresight Launch Monitor" or a device with Vendor ID 2c79

Or use the command line:

```bash
# List USB devices
system_profiler SPUSBDataType | grep -A 10 "GC2\|Foresight\|2c79"
```

## Troubleshooting

### "GC2 Not Found" Error

1. **Check physical connection**:
   - Ensure the GC2 is powered on (green or red LED visible)
   - Try a different USB port
   - Try a different USB cable
   - Avoid USB hubs if possible - connect directly to your Mac

2. **Check System Information**:
   - Open System Information (Apple menu > About This Mac > System Report)
   - Navigate to USB
   - Look for the GC2 device

3. **Verify libusb installation**:
   ```bash
   brew list libusb

   # If not installed:
   brew install libusb
   ```

4. **Test USB access with Python**:
   ```bash
   uv run python -c "
   import usb.core
   device = usb.core.find(idVendor=0x2c79, idProduct=0x0110)
   print('GC2 found!' if device else 'GC2 not found')
   "
   ```

### Security & Privacy Settings

macOS may block USB access for security reasons. If prompted:

1. Go to System Settings > Privacy & Security
2. Check for any blocked USB access notifications
3. Allow access for the terminal or GC2 Connect

### USB Power Issues

If the GC2 disconnects intermittently:

1. Connect directly to your Mac (not through a hub)
2. Use a high-quality USB cable
3. Check if the GC2 is getting sufficient power

Some USB-C to USB-A adapters may not provide adequate power. If using an adapter, try a powered USB hub instead.

### Multiple USB Controllers

On newer Macs with multiple USB controllers, the GC2 might appear on a different controller than expected. This should not cause issues, but if you encounter problems:

1. Try different USB ports
2. Restart your Mac with the GC2 connected

### Driver Conflicts

macOS does not require additional drivers for the GC2, but if you've installed third-party USB drivers (e.g., for other devices), they might interfere:

1. Check for installed kexts:
   ```bash
   kextstat | grep -v com.apple
   ```

2. If you see USB-related third-party kexts, they may be causing conflicts

## Apple Silicon (M1/M2/M3) Notes

GC2 Connect works on Apple Silicon Macs. The application runs natively through Python without Rosetta.

If you encounter issues:

1. Ensure you're using Python 3.10 or later built for arm64
2. Verify with:
   ```bash
   python3 -c "import platform; print(platform.machine())"
   # Should output: arm64
   ```

## USB-C Connections

Modern MacBooks only have USB-C ports, but the GC2 uses USB-A. You'll need an adapter:

### Recommended Adapters

- Apple USB-C to USB Adapter
- Any quality USB-C hub with USB-A ports
- USB-C to USB-A cable (if the GC2 cable is detachable)

### Tips

- Powered hubs are more reliable than passive adapters
- Avoid cheap adapters that may have power delivery issues
- If using a hub, connect the GC2 to the hub before powering on

## Testing the Connection

Once connected, verify everything works:

```bash
# Run the app
uv run python -m gc2_connect.main
```

In the app:
1. Click "Connect" in the GC2 panel
2. Status should change to "Connected"
3. The Ready indicator should match the GC2's LED state

## Additional Resources

- [Apple: About USB](https://support.apple.com/guide/mac-help/about-usb-ports-and-devices-mchlp1159/mac)
- [Homebrew Documentation](https://docs.brew.sh/)
- [PyUSB on macOS](https://github.com/pyusb/pyusb#macos)
