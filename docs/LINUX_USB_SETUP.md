# Linux USB Setup for GC2

This guide explains how to configure USB permissions on Linux to allow GC2 Connect Desktop to communicate with your Foresight GC2 launch monitor without requiring root privileges.

## The Problem

On Linux, USB devices are typically only accessible by root. To use the GC2 without running the application as root (which is not recommended for security reasons), you need to add a udev rule that grants your user access to the device.

## GC2 USB Identifiers

The Foresight GC2 uses the following USB identifiers:
- **Vendor ID (VID)**: `2c79` (decimal: 11385)
- **Product ID (PID)**: `0110` (decimal: 272)

## Quick Setup

Run these commands to set up USB access:

```bash
# Create the udev rule file
sudo tee /etc/udev/rules.d/99-gc2.rules << 'EOF'
# Foresight GC2 Launch Monitor
# Allows non-root users to access the GC2 USB device
SUBSYSTEM=="usb", ATTR{idVendor}=="2c79", ATTR{idProduct}=="0110", MODE="0666", GROUP="plugdev"
EOF

# Reload udev rules
sudo udevadm control --reload-rules
sudo udevadm trigger

# Add yourself to the plugdev group (if not already)
sudo usermod -a -G plugdev $USER
```

After running these commands, you need to:
1. Unplug and replug your GC2
2. Log out and log back in (for group membership to take effect)

## Detailed Explanation

### The udev Rule

The udev rule file `/etc/udev/rules.d/99-gc2.rules` contains:

```
SUBSYSTEM=="usb", ATTR{idVendor}=="2c79", ATTR{idProduct}=="0110", MODE="0666", GROUP="plugdev"
```

This rule:
- `SUBSYSTEM=="usb"` - Applies only to USB devices
- `ATTR{idVendor}=="2c79"` - Matches the GC2's vendor ID
- `ATTR{idProduct}=="0110"` - Matches the GC2's product ID
- `MODE="0666"` - Makes the device readable and writable by all users
- `GROUP="plugdev"` - Assigns the device to the plugdev group

### Using a More Restrictive Mode

If you prefer stricter permissions, you can use `MODE="0660"` instead, which only allows access to users in the `plugdev` group:

```bash
sudo tee /etc/udev/rules.d/99-gc2.rules << 'EOF'
SUBSYSTEM=="usb", ATTR{idVendor}=="2c79", ATTR{idProduct}=="0110", MODE="0660", GROUP="plugdev"
EOF
```

Make sure your user is in the `plugdev` group:

```bash
# Add user to plugdev group
sudo usermod -a -G plugdev $USER

# Verify group membership (requires re-login to take effect)
groups
```

## Verifying the Setup

### Check if the GC2 is Detected

```bash
# List USB devices (requires usbutils package)
lsusb | grep -i "2c79"

# If found, you should see something like:
# Bus 001 Device 003: ID 2c79:0110 Foresight Sports Foresight Launch Monitor
```

### Check Device Permissions

```bash
# Find the device path
ls -la /dev/bus/usb/*/$(lsusb | grep "2c79:0110" | awk '{print $4}' | tr -d ':')

# Should show permissions like:
# crw-rw-rw- 1 root plugdev 189, 2 Jan  3 10:00 /dev/bus/usb/001/003
```

### Test with Python

```python
import usb.core

# Try to find the GC2
device = usb.core.find(idVendor=0x2c79, idProduct=0x0110)
if device:
    print("GC2 found!")
    print(f"  Manufacturer: {device.manufacturer}")
    print(f"  Product: {device.product}")
else:
    print("GC2 not found")
```

Run this with:
```bash
uv run python -c "
import usb.core
device = usb.core.find(idVendor=0x2c79, idProduct=0x0110)
print('GC2 found!' if device else 'GC2 not found')
"
```

## Troubleshooting

### "GC2 Not Found" Error

1. **Check physical connection**: Make sure the GC2 is powered on and connected via USB

2. **Verify USB detection**:
   ```bash
   lsusb | grep -i foresight
   # or
   lsusb | grep "2c79"
   ```

3. **Check udev rules are loaded**:
   ```bash
   # Force reload
   sudo udevadm control --reload-rules
   sudo udevadm trigger

   # Check for rule syntax errors
   sudo udevadm test /devices/pci*/*/usb*/*-*
   ```

4. **Replug the device**: Unplug and replug the GC2 after changing rules

### "Permission Denied" Error

1. **Check group membership**:
   ```bash
   groups | grep plugdev
   ```
   If plugdev is not listed, add yourself and re-login:
   ```bash
   sudo usermod -a -G plugdev $USER
   # Then log out and log back in
   ```

2. **Check device permissions**:
   ```bash
   ls -la /dev/bus/usb/*/*
   ```

3. **Try the more permissive mode**:
   Update the rule to use `MODE="0666"` instead of `MODE="0660"`

### libusb Errors

If you see libusb-related errors:

1. **Install libusb**:
   ```bash
   # Ubuntu/Debian
   sudo apt install libusb-1.0-0-dev

   # Fedora/RHEL
   sudo dnf install libusb1-devel

   # Arch
   sudo pacman -S libusb
   ```

2. **Check libusb is working**:
   ```bash
   # This should list USB devices
   python3 -c "import usb.core; print(list(usb.core.find(find_all=True)))"
   ```

### SELinux Issues (Fedora/RHEL)

If you're on a system with SELinux enabled, you may need additional configuration:

```bash
# Check if SELinux is blocking access
sudo ausearch -m avc -ts recent | grep usb

# If blocked, you may need to create a policy module
# This is distribution-specific - consult your distro's documentation
```

## Alternative: Running as Root (Not Recommended)

As a last resort, you can run the application as root:

```bash
sudo uv run python -m gc2_connect.main
```

This is **not recommended** for regular use because:
- It grants unnecessary privileges to the application
- It may cause permission issues with settings files
- It's a security risk

## Uninstalling

To remove the udev rule:

```bash
sudo rm /etc/udev/rules.d/99-gc2.rules
sudo udevadm control --reload-rules
sudo udevadm trigger
```

## Additional Resources

- [udev - ArchWiki](https://wiki.archlinux.org/title/Udev)
- [Writing udev rules](http://www.reactivated.net/writing_udev_rules.html)
- [PyUSB Tutorial](https://github.com/pyusb/pyusb/blob/master/docs/tutorial.rst)
