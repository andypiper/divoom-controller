# Divoom Timebox Evo Controller

[![Python Version](https://img.shields.io/badge/python-3.13+-blue.svg)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Code Style](https://img.shields.io/badge/code%20style-black-000000.svg)](https://github.com/psf/black)

> Modern Python library and CLI for controlling Divoom Timebox Evo devices via Bluetooth

Control your Divoom Timebox Evo pixel display from Linux (Fedora, Debian) using a simple command-line interface or Python library.

## Table of Contents

- [Background](#background)
- [Install](#install)
- [Usage](#usage)
  - [CLI](#cli)
  - [Library](#library)
- [API](#api)
- [Examples](#examples)
- [Requirements](#requirements)
- [Maintainers](#maintainers)
- [Contributing](#contributing)
- [License](#license)

## Background

The Divoom Timebox Evo is a 16x16 pixel LED display with Bluetooth connectivity. This tool provides a modern Python interface to control the device, including:

- Setting brightness, time, and colors
- Switching display modes (clock, lighting, visualizer, scoreboard)
- Displaying custom images
- Setting weather and temperature information

The implementation is based on reverse-engineered protocol documentation and builds on the work of the [divo](https://github.com/spezifisch/divo) project and [RomRider's protocol documentation](https://github.com/RomRider/node-divoom-timebox-evo).

## Install

This is a standalone Python script using [PEP 723](https://peps.python.org/pep-0723/) inline script metadata. You can run it directly with modern Python package managers.

### Using uv (recommended)

```bash
# Install uv if you don't have it
curl -LsSf https://astral.sh/uv/install.sh | sh

# Run directly
uv run divoom-timebox-evo.py --help

# Or make it executable
chmod +x divoom-timebox-evo.py
uv run ./divoom-timebox-evo.py --help
```

### Using pipx

```bash
# Install pipx if you don't have it
pip install pipx

# Run the script
pipx run divoom-timebox-evo.py --help
```

### Traditional method

```bash
# Create virtual environment
python3.13 -m venv venv
source venv/bin/activate

# Install dependencies
pip install click rich pillow

# Run script
python divoom-timebox-evo.py --help
```

### System Requirements

**Linux Bluetooth Setup:**

```bash
# Debian/Ubuntu
sudo apt-get install bluetooth bluez libbluetooth-dev python3-dev

# Fedora
sudo dnf install bluez bluez-libs-devel python3-devel

# Ensure Bluetooth service is running
sudo systemctl start bluetooth
sudo systemctl enable bluetooth
```

**Find your device MAC address:**

```bash
bluetoothctl
> scan on
# Look for "Divoom" device
# Note the MAC address (format: XX:XX:XX:XX:XX:XX)
> exit
```

## Usage

### CLI

All commands require the `--mac` option with your device's Bluetooth MAC address.

```bash
# Set brightness
./divoom-timebox-evo.py --mac 11:75:58:6C:D6:D8 brightness 50

# Sync time
./divoom-timebox-evo.py --mac 11:75:58:6C:D6:D8 time

# Set solid color
./divoom-timebox-evo.py --mac 11:75:58:6C:D6:D8 light 255 0 0

# Set pulsing purple light
./divoom-timebox-evo.py --mac 11:75:58:6C:D6:D8 light 128 0 128 --effect pulse

# Show simple HH:MM clock (minimal, no distractions)
./divoom-timebox-evo.py --mac 11:75:58:6C:D6:D8 clock --minimal

# Show clock with weather and temperature
./divoom-timebox-evo.py --mac 11:75:58:6C:D6:D8 clock --weather --temperature

# Set audio visualizer
./divoom-timebox-evo.py --mac 11:75:58:6C:D6:D8 visualizer 3

# Display scoreboard
./divoom-timebox-evo.py --mac 11:75:58:6C:D6:D8 scoreboard 42 37

# Set weather and temperature
./divoom-timebox-evo.py --mac 11:75:58:6C:D6:D8 weather 22 --weather sunny

# Display image
./divoom-timebox-evo.py --mac 11:75:58:6C:D6:D8 image path/to/image.png

# Show info
./divoom-timebox-evo.py --mac 11:75:58:6C:D6:D8 info
```

**Available Commands:**

- `brightness <0-100>` - Set display brightness
- `time` - Sync device time with system time
- `light <R> <G> <B>` - Set lighting mode (RGB 0-255)
  - `--effect` - Choose effect: pulse, cycle, breathing, strobe, solid
  - `--brightness` - Light brightness (0-100)
- `clock` - Set clock display
  - `--minimal` - Simple HH:MM only display (recommended for minimal distraction)
  - `--style` - Clock style: fullscreen, rainbow, bordered, analog-square, analog-round, widescreen
  - `--weather` - Show weather icon
  - `--temperature` - Show temperature
  - `--date` - Show date
  - `--red/--green/--blue` - Clock color (0-255)
  - **Tip:** Use `--minimal` for a clean, simple time display without animations
- `visualizer <0-11>` - Set audio visualizer mode
- `scoreboard <blue> <red>` - Set scoreboard (scores 0-999)
- `weather <temp>` - Set temperature (-128 to 127°C)
  - `--weather` - Weather: clear, cloudy, thunderstorm, rain, snow, fog
- `image <path>` - Display image (auto-resized to 16x16)
- `info` - Show device information

### Library

Use as a Python library in your own projects:

```python
from divoom_timebox_evo import DivoomTimeboxEvo, ClockStyle, LightingEffect, WeatherType

# Connect to device
with DivoomTimeboxEvo("11:75:58:6C:D6:D8") as device:
    # Set brightness
    device.set_brightness(75)

    # Set time
    device.set_time()

    # Show clock with weather
    device.set_clock(
        style=ClockStyle.FULLSCREEN,
        red=255, green=255, blue=255,
        show_weather=True,
        show_temperature=True
    )

    # Set lighting
    device.set_lighting(
        red=255, green=0, blue=128,
        effect=LightingEffect.BREATHING,
        brightness=80
    )

    # Display image
    device.display_image("path/to/image.png")

    # Set weather
    device.set_temperature_weather(22, WeatherType.RAIN)

    # Set scoreboard
    device.set_scoreboard(blue_score=3, red_score=2)
```

## API

### DivoomTimeboxEvo Class

Main controller class for device interaction.

**Constructor:**
- `DivoomTimeboxEvo(mac_address: str, timeout: float = 5.0)`

**Methods:**
- `connect()` - Establish Bluetooth connection
- `disconnect()` - Close connection
- `set_brightness(brightness: int)` - Set display brightness (0-100)
- `set_time(dt: datetime | None)` - Set device time
- `set_color(red: int, green: int, blue: int)` - Set system color
- `set_clock(...)` - Set clock display mode
- `set_lighting(...)` - Set lighting mode
- `set_visualizer(visualizer_id: int)` - Set audio visualizer (0-11)
- `set_scoreboard(blue_score: int, red_score: int)` - Set scoreboard
- `set_temperature_weather(temperature: int, weather: WeatherType)` - Set weather display
- `display_image(image_path: str)` - Display image file

### Enumerations

- `ClockStyle` - Clock display styles
- `LightingEffect` - Lighting effects
- `WeatherType` - Weather conditions
- `BoxMode` - Display modes

## Examples

### Quick Start Script

```python
#!/usr/bin/env python3
"""Quick demo of Divoom Timebox Evo features."""

from divoom_timebox_evo import (
    DivoomTimeboxEvo,
    ClockStyle,
    LightingEffect,
    WeatherType
)
import time

MAC_ADDRESS = "11:75:58:6C:D6:D8"

with DivoomTimeboxEvo(MAC_ADDRESS) as device:
    # Set brightness to 50%
    device.set_brightness(50)
    print("Set brightness to 50%")
    time.sleep(2)

    # Show a colorful clock
    device.set_clock(
        style=ClockStyle.RAINBOW,
        show_weather=True,
        show_temperature=True
    )
    print("Showing rainbow clock")
    time.sleep(5)

    # Pulsing ambient light
    device.set_lighting(
        red=100, green=50, blue=150,
        effect=LightingEffect.BREATHING
    )
    print("Breathing purple light")
    time.sleep(5)

    # Audio visualizer
    device.set_visualizer(0)
    print("Audio visualizer active")
```

### Integration with Home Assistant

The library can be imported into Home Assistant custom components for integration with your smart home setup.

### Batch Operations

```python
"""Update multiple settings at once."""

from divoom_timebox_evo import DivoomTimeboxEvo, WeatherType
from datetime import datetime

MAC = "11:75:58:6C:D6:D8"

with DivoomTimeboxEvo(MAC) as device:
    device.set_time(datetime.now())
    device.set_brightness(60)
    device.set_temperature_weather(22, WeatherType.CLEAR)
    device.set_clock(show_weather=True, show_temperature=True)
```

## Requirements

- **Python:** 3.13 or higher
- **Operating System:** Linux (Fedora, Debian, Ubuntu, etc.)
- **Hardware:** Bluetooth adapter with RFCOMM support
- **Device:** Divoom Timebox Evo

**Python Dependencies:**
- click >= 8.1.0
- rich >= 13.0.0
- pillow >= 10.0.0

**System Dependencies:**
- bluez
- bluez-libs-devel (Fedora) or libbluetooth-dev (Debian/Ubuntu)
- python3-dev or python3-devel

## Maintainers

[@andypiper](https://github.com/andypiper)

- Website: https://andypiper.me
- Mastodon: [@andypiper@macaw.social](https://macaw.social/@andypiper)
- Codeberg: [@andypiper](https://codeberg.org/andypiper)

## Contributing

Contributions welcome! Please:

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Make your changes
4. Format code with Black (`black divoom-timebox-evo.py`)
5. Commit your changes (`git commit -m 'Add amazing feature'`)
6. Push to the branch (`git push origin feature/amazing-feature`)
7. Open a Pull Request

## Acknowledgments

This project builds on the excellent work of:

- [spezifisch](https://github.com/spezifisch) and contributors to the [divo](https://github.com/spezifisch/divo) project
- [RomRider](https://github.com/RomRider) for [protocol documentation](https://github.com/RomRider/node-divoom-timebox-evo/blob/master/PROTOCOL.md)
- [johsam](https://github.com/johsam) for the original encoder implementation

## License

[MIT](LICENSE) © 2025 Andy Piper

Original divo project: GPL-3.0 © spezifisch and contributors

---

**Note:** This is a complete rewrite and modernization of the original code with a new MIT license. Protocol implementations are based on publicly documented reverse-engineering efforts.
