# Divoom Timebox Evo Examples

This directory contains example scripts demonstrating how to use the Divoom Timebox Evo controller.

## Examples

### simple.py

Basic usage example showing:
- Connecting to device
- Setting brightness
- Syncing time
- Displaying clock

```bash
python examples/simple.py
```

### demo.py

Comprehensive demonstration of all features:
- Brightness control
- Clock styles
- Lighting effects
- Audio visualizers
- Scoreboard
- Weather display

```bash
python examples/demo.py
```

## Before Running

1. **Update MAC address**: Edit the examples to set your device's MAC address
2. **Install dependencies**: Ensure the main script dependencies are installed
3. **Bluetooth setup**: Make sure your device is paired and Bluetooth is enabled

## Finding Your Device MAC Address

```bash
bluetoothctl
> scan on
# Look for "Divoom" in the device list
# Note the MAC address (XX:XX:XX:XX:XX:XX)
> exit
```

## Troubleshooting

If you encounter connection issues:

1. **Check device is on**: The Timebox Evo should be powered and in pairing mode
2. **Verify Bluetooth**: `systemctl status bluetooth` should show "active"
3. **Check Python Bluetooth support**: The error message will indicate if missing
4. **Try pairing first**: Use `bluetoothctl` to pair the device before running scripts

## Creating Your Own Scripts

```python
#!/usr/bin/env python3
from divoom_timebox_evo import DivoomTimeboxEvo

MAC = "XX:XX:XX:XX:XX:XX"  # Your device MAC

with DivoomTimeboxEvo(MAC) as device:
    # Your code here
    device.set_brightness(50)
    device.set_time()
```

See the main README.md for complete API documentation.
