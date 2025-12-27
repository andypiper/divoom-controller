#!/usr/bin/env python3
"""
Demonstration script for Divoom Timebox Evo Controller.

This script shows various features of the device.
Update MAC_ADDRESS to match your device.
"""

import sys
import time
from pathlib import Path

# Add parent directory to path to import the main module
sys.path.insert(0, str(Path(__file__).parent.parent))

from divoom_timebox_evo import (
    DivoomTimeboxEvo,
    ClockStyle,
    LightingEffect,
    WeatherType,
)

# UPDATE THIS TO YOUR DEVICE MAC ADDRESS
MAC_ADDRESS = "11:75:58:6C:D6:D8"


def demo_brightness(device: DivoomTimeboxEvo):
    """Demonstrate brightness control."""
    print("\n=== Brightness Demo ===")
    for brightness in [100, 75, 50, 25, 50, 75, 100]:
        print(f"Setting brightness to {brightness}%")
        device.set_brightness(brightness)
        time.sleep(1)


def demo_clock(device: DivoomTimeboxEvo):
    """Demonstrate clock styles."""
    print("\n=== Clock Styles Demo ===")
    styles = [
        ("Fullscreen", ClockStyle.FULLSCREEN),
        ("Rainbow", ClockStyle.RAINBOW),
        ("Bordered", ClockStyle.BORDERED),
        ("Analog Square", ClockStyle.ANALOG_SQUARE),
        ("Analog Round", ClockStyle.ANALOG_ROUND),
    ]

    for name, style in styles:
        print(f"Showing {name} clock")
        device.set_clock(style=style, show_weather=True, show_temperature=True)
        time.sleep(3)


def demo_lighting(device: DivoomTimeboxEvo):
    """Demonstrate lighting effects."""
    print("\n=== Lighting Effects Demo ===")

    colors = [
        ("Red", 255, 0, 0),
        ("Green", 0, 255, 0),
        ("Blue", 0, 0, 255),
        ("Purple", 128, 0, 128),
        ("Cyan", 0, 255, 255),
        ("Yellow", 255, 255, 0),
    ]

    effects = [
        ("Solid", LightingEffect.SOLID),
        ("Pulse", LightingEffect.PULSE),
        ("Breathing", LightingEffect.BREATHING),
        ("Cycle", LightingEffect.CYCLE),
    ]

    for color_name, r, g, b in colors[:3]:  # Show first 3 colors
        for effect_name, effect in effects[:2]:  # Show first 2 effects
            print(f"Showing {color_name} with {effect_name} effect")
            device.set_lighting(r, g, b, effect, brightness=80)
            time.sleep(2)


def demo_visualizer(device: DivoomTimeboxEvo):
    """Demonstrate audio visualizer."""
    print("\n=== Audio Visualizer Demo ===")
    print("Cycling through visualizer modes (play some music!)")

    for viz_id in range(0, 4):  # Show first 4 visualizers
        print(f"Visualizer mode {viz_id}")
        device.set_visualizer(viz_id)
        time.sleep(4)


def demo_scoreboard(device: DivoomTimeboxEvo):
    """Demonstrate scoreboard."""
    print("\n=== Scoreboard Demo ===")

    scores = [
        (0, 0),
        (1, 0),
        (1, 1),
        (1, 2),
        (2, 2),
        (3, 2),
    ]

    for blue, red in scores:
        print(f"Score - Blue: {blue}, Red: {red}")
        device.set_scoreboard(blue, red)
        time.sleep(2)


def demo_weather(device: DivoomTimeboxEvo):
    """Demonstrate weather display."""
    print("\n=== Weather Demo ===")

    weather_conditions = [
        ("Clear", 22, WeatherType.CLEAR),
        ("Rainy", 18, WeatherType.RAIN),
        ("Snowy", -2, WeatherType.SNOW),
        ("Cloudy", 15, WeatherType.CLOUDY),
    ]

    for name, temp, weather in weather_conditions:
        print(f"Weather: {name}, {temp}°C")
        device.set_temperature_weather(temp, weather)
        time.sleep(3)


def main():
    """Run all demonstrations."""
    print("=" * 50)
    print("Divoom Timebox Evo - Feature Demonstration")
    print("=" * 50)
    print(f"Connecting to device at {MAC_ADDRESS}...")

    try:
        with DivoomTimeboxEvo(MAC_ADDRESS) as device:
            print("Connected successfully!")

            # Sync time
            print("\nSyncing device time...")
            device.set_time()

            # Run demonstrations
            demo_brightness(device)
            demo_clock(device)
            demo_lighting(device)
            demo_visualizer(device)
            demo_scoreboard(device)
            demo_weather(device)

            # Return to clock
            print("\n=== Returning to clock display ===")
            device.set_clock(
                style=ClockStyle.FULLSCREEN,
                show_weather=True,
                show_temperature=True,
            )

            print("\nDemo complete!")

    except Exception as e:
        print(f"\nError: {e}")
        print("\nTroubleshooting:")
        print("1. Check that the device is powered on")
        print("2. Verify the MAC address is correct")
        print("3. Ensure Bluetooth is enabled on your system")
        print("4. Try pairing the device first using bluetoothctl")
        sys.exit(1)


if __name__ == "__main__":
    main()
