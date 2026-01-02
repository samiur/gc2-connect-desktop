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

The GC2 exposes multiple USB endpoints:

| Endpoint | Address | Type | Direction | Description |
|----------|---------|------|-----------|-------------|
| BULK OUT | 0x07 | Bulk | Host → Device | Commands (if any) |
| BULK IN | 0x88 | Bulk | Device → Host | Data transfer |
| INTERRUPT IN | 0x82 | Interrupt | Device → Host | **Primary shot data** |

**Note:** Shot data is received on the INTERRUPT IN endpoint (0x82), not the BULK endpoint.

### Data Format
- Encoding: ASCII text
- Packet size: 64 bytes (data split across multiple packets)
- Line separator: Newline (`\n`)
- Field format: `KEY=VALUE`

## Shot Data Fields

### Ball Data (Always Present)

| Field | Type | Unit | Description | Range |
|-------|------|------|-------------|-------|
| `SHOT_ID` | int | - | Unique shot identifier | 1+ |
| `TIME_SEC` | int | s | Shot timestamp (usually 0) | 0+ |
| `MSEC_SINCE_CONTACT` | int | ms | Time since ball contact | 0-1000+ |
| `SPEED_MPH` | float | mph | Ball speed off clubface | 0-250 |
| `ELEVATION_DEG` | float | degrees | Vertical launch angle | -10 to 60 |
| `AZIMUTH_DEG` | float | degrees | Horizontal launch angle (+ = right) | -45 to 45 |
| `SPIN_RPM` | float | rpm | Total spin rate | 0-15000 |
| `BACK_RPM` | float | rpm | Backspin component | 0-15000 |
| `SIDE_RPM` | float | rpm | Sidespin component (+ = fade) | -5000 to 5000 |

**Note:** The GC2 sends multiple updates per shot:
- **Early reading** (~200ms): Initial ball detection, may have incomplete data
- **Final reading** (1000ms): Complete data including spin components (`BACK_RPM`, `SIDE_RPM`)

Always wait for the spin component fields before processing a shot.

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
| `FAXIS_DEG` | float | degrees | Face axis at impact | -15 to 15 |
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

## USB Message Structure

The GC2 sends data in 64-byte USB packets over the INTERRUPT IN endpoint (0x82). Each shot generates multiple message types.

### Message Types

| Prefix | Name | Description |
|--------|------|-------------|
| `0H` | Shot Header | Shot metrics (speed, spin, launch angle, etc.) |
| `0M` | Ball Movement | Real-time ball tracking/position updates |

### 0H Messages (Shot Data)

Contains the actual shot metrics. Fields are split across multiple 64-byte packets:

```
0H
SHOT_ID=1
TIME_SEC=0
MSEC_SINCE_CONTACT=1000
SPEED_MPH=145.20
AZIMUTH_DEG=1.50
ELEVATION_DEG=11.80
SPIN_RPM=2650
BACK_RPM=2480
SIDE_RPM=-320
```

### 0M Messages (Ball Tracking)

Real-time ball position updates during flight through the camera's field of view. These messages are sent while the ball is being tracked and typically contain position/detection data rather than final shot metrics.

**Recommendation:** Skip 0M messages when parsing shot data. Only accumulate fields from 0H messages.

### Data Accumulation Strategy

Shot data is split across multiple USB packets. The recommended approach (based on gc2_to_TGC implementation):

1. **Filter by message type**: Only process `0H` messages, skip `0M` messages
2. **Accumulate fields**: Parse key=value pairs into a dictionary, accumulating across packets
3. **Wait for complete data**: Don't process until `BACK_RPM` or `SIDE_RPM` is received
4. **Detect new shots**: When `SHOT_ID` changes, clear the accumulator and start fresh
5. **Handle timeouts**: If spin components never arrive (~500ms), process with available data

Example packet sequence for one shot:
```
Packet 1: 0H\nSHOT_ID=1\nTIME_SEC=0\nMSEC_SINCE_CONTACT=200\nSPEED_MPH=145.
Packet 2: 20\nAZIMUTH_DEG=1.50\nELEVATION_DEG=11.80\nSPIN_RPM=2650\n
Packet 3: 0H\nSHOT_ID=1\nTIME_SEC=0\nMSEC_SINCE_CONTACT=1000\nSPEED_MPH=145.
Packet 4: 20\nAZIMUTH_DEG=1.50\nELEVATION_DEG=11.80\nSPIN_RPM=2650\nBACK_
Packet 5: RPM=2480\nSIDE_RPM=-320\n
```

Note: The same shot may be sent multiple times with different `MSEC_SINCE_CONTACT` values as measurements are refined.

## Timing Considerations

- Shot data is sent immediately after each shot
- Data arrives in multiple 64-byte fragments; accumulate until complete
- The GC2 sends early readings (~200ms) and final readings (~1000ms)
- No heartbeat or polling required - GC2 pushes data on shot detection
- Typical latency: < 50ms from ball impact to first data packet

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
- gc2_to_TGC application (reverse engineered for protocol details)
