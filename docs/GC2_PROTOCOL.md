# GC2 USB Protocol Specification

## Overview

The Foresight GC2 launch monitor communicates via USB using a simple text-based protocol. This document describes the protocol format and data fields.

## Device Identification

| Property | Value |
|----------|-------|
| Vendor ID | 0x2C79 (11385) |
| Product ID | 0x0110 (272) |
| Manufacturer | Foresight Sports |
| Product | GC2 |

## USB Communication

### Interface Type
- USB Bulk Transfer
- Primary data direction: Device → Host (IN endpoint)

### Data Format
- Encoding: ASCII text
- Line separator: Newline (`\n`)
- Field format: `KEY=VALUE`

## Shot Data Fields

### Ball Data (Always Present)

| Field | Type | Unit | Description | Range |
|-------|------|------|-------------|-------|
| `SHOT_ID` | int | - | Unique shot identifier | 1+ |
| `SPEED_MPH` | float | mph | Ball speed off clubface | 0-250 |
| `ELEVATION_DEG` | float | degrees | Vertical launch angle | -10 to 60 |
| `AZIMUTH_DEG` | float | degrees | Horizontal launch angle (+ = right) | -45 to 45 |
| `SPIN_RPM` | float | rpm | Total spin rate | 0-15000 |
| `BACK_RPM` | float | rpm | Backspin component | 0-15000 |
| `SIDE_RPM` | float | rpm | Sidespin component (+ = fade) | -5000 to 5000 |

### Club Data (HMT Only)

These fields are only present when the GC2 is equipped with the HMT (Head Measurement Technology) add-on.

| Field | Type | Unit | Description | Range |
|-------|------|------|-------------|-------|
| `CLUBSPEED_MPH` | float | mph | Club head speed | 0-150 |
| `HPATH_DEG` | float | degrees | Swing path (+ = in-to-out) | -15 to 15 |
| `VPATH_DEG` | float | degrees | Angle of attack (+ = up) | -10 to 10 |
| `FACE_T_DEG` | float | degrees | Face to target (+ = open) | -15 to 15 |
| `LIE_DEG` | float | degrees | Lie angle at impact | -10 to 10 |
| `LOFT_DEG` | float | degrees | Dynamic loft at impact | 0-60 |
| `HIMPACT_MM` | float | mm | Horizontal impact location | -30 to 30 |
| `VIMPACT_MM` | float | mm | Vertical impact location | -30 to 30 |
| `CLOSING_RATE_DEGSEC` | float | deg/s | Face closure rate | 0-2000 |
| `HMT` | int | boolean | HMT data present flag | 0 or 1 |

## Example Data

### Ball Only (No HMT)

```
SHOT_ID=1
SPEED_MPH=145.2
ELEVATION_DEG=11.8
AZIMUTH_DEG=1.5
SPIN_RPM=2650
BACK_RPM=2480
SIDE_RPM=-320
```

### Full Data (With HMT)

```
SHOT_ID=1
SPEED_MPH=150.5
ELEVATION_DEG=12.3
AZIMUTH_DEG=2.1
SPIN_RPM=2800
BACK_RPM=2650
SIDE_RPM=-400
CLUBSPEED_MPH=105.2
HPATH_DEG=3.1
VPATH_DEG=-4.2
FACE_T_DEG=1.5
LIE_DEG=0.5
LOFT_DEG=15.2
HIMPACT_MM=2.5
VIMPACT_MM=-1.2
CLOSING_RATE_DEGSEC=500.0
HMT=1
```

## Calculated Fields

### Spin Axis

The spin axis can be calculated from back spin and side spin:

```python
import math

def calculate_spin_axis(back_spin: float, side_spin: float) -> float:
    """
    Calculate spin axis from spin components.
    
    Returns:
        Spin axis in degrees
        Positive = fade/slice spin axis (tilted right)
        Negative = draw/hook spin axis (tilted left)
    """
    if back_spin == 0:
        return 0.0
    return math.degrees(math.atan2(side_spin, back_spin))
```

## Data Validation

### Misread Detection

The GC2 occasionally produces misreads that should be rejected:

1. **Zero Spin**: `SPIN_RPM == 0` indicates a misread
2. **2222 Pattern**: `BACK_RPM == 2222` is a known error pattern
3. **Unrealistic Speed**: `SPEED_MPH < 10` or `SPEED_MPH > 250`

### Duplicate Detection

The GC2 may send the same shot multiple times. Track `SHOT_ID` to detect and ignore duplicates.

```python
def is_duplicate(shot_id: int, last_shot_id: int) -> bool:
    return shot_id == last_shot_id
```

## Parsing Implementation

### Python

```python
def parse_gc2_data(raw_data: str) -> dict:
    """Parse raw GC2 USB data into a dictionary."""
    result = {}
    
    for line in raw_data.strip().split('\n'):
        line = line.strip()
        if '=' not in line:
            continue
            
        key, value = line.split('=', 1)
        key = key.strip()
        value = value.strip()
        
        # Convert to appropriate type
        if key == 'SHOT_ID':
            result[key] = int(value)
        elif key == 'HMT':
            result[key] = value == '1'
        else:
            try:
                result[key] = float(value)
            except ValueError:
                result[key] = value
    
    return result
```

### TypeScript

```typescript
function parseGC2Data(rawData: string): Record<string, number | boolean> {
    const result: Record<string, number | boolean> = {};
    
    for (const line of rawData.trim().split('\n')) {
        const trimmed = line.trim();
        if (!trimmed.includes('=')) continue;
        
        const [key, value] = trimmed.split('=', 2);
        const k = key.trim();
        const v = value.trim();
        
        if (k === 'SHOT_ID') {
            result[k] = parseInt(v, 10);
        } else if (k === 'HMT') {
            result[k] = v === '1';
        } else {
            result[k] = parseFloat(v);
        }
    }
    
    return result;
}
```

## USB Implementation Notes

### Linux/macOS

- Use `libusb` (via `pyusb` in Python)
- May require `udev` rules on Linux for non-root access
- macOS typically allows USB access without special configuration

### Android

- Use `android.hardware.usb` APIs
- Requires USB Host mode support
- Permission dialog shown to user
- Can auto-launch app on device connection

### iPad

- Requires DriverKit (USBDriverKit)
- Only available on M1+ iPads
- Requires entitlements from Apple
- Runs as user-space driver extension

## Timing Considerations

- Shot data is sent immediately after each shot
- Data may arrive in fragments; buffer until complete message received
- No heartbeat or polling required - GC2 pushes data on shot detection
- Typical latency: < 50ms from ball impact to data availability

## Error Conditions

| Condition | Behavior |
|-----------|----------|
| USB Disconnected | No data; detect via USB events |
| GC2 Powered Off | USB device disappears |
| Camera Obscured | May produce misreads (zero spin) |
| Low Battery | GC2 may disconnect unexpectedly |

## References

- USB 2.0 Specification
- Foresight Sports GC2 User Manual
- GSPro Open Connect API v1 Documentation
