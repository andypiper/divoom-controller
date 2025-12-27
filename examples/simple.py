#!/usr/bin/env python3
"""
Simple example of using the Divoom Timebox Evo library.

This shows basic usage patterns.
"""

import sys
from pathlib import Path

# Add parent directory to path to import the main module
sys.path.insert(0, str(Path(__file__).parent.parent))

from divoom_timebox_evo import DivoomTimeboxEvo, ClockStyle

# Update this to your device MAC address
MAC_ADDRESS = "11:75:58:6C:D6:D8"

# Connect and perform basic operations
with DivoomTimeboxEvo(MAC_ADDRESS) as device:
    # Set brightness to 75%
    device.set_brightness(75)

    # Sync the time
    device.set_time()

    # Show a fullscreen clock
    device.set_clock(
        style=ClockStyle.FULLSCREEN,
        red=255,
        green=255,
        blue=255,
        show_weather=True,
        show_temperature=True,
    )

print("Device configured successfully!")
