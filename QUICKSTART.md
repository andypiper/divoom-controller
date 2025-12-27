# Quick Start Guide

Get started with your Divoom Timebox Evo in 5 minutes!

## Step 1: Find Your Device

```bash
bluetoothctl
> scan on
# Wait and look for "Divoom" or "Timebox"
# Note the MAC address: XX:XX:XX:XX:XX:XX
> exit
```

## Step 2: Install uv (if needed)

```bash
curl -LsSf https://astral.sh/uv/install.sh | sh
```

Or use your package manager:
```bash
# Fedora
sudo dnf install uv

# Debian/Ubuntu
sudo apt install uv
```

## Step 3: Run Your First Command

```bash
# Download the script
wget https://raw.githubusercontent.com/andypiper/divoom-controller/main/divoom-timebox-evo.py
chmod +x divoom-timebox-evo.py

# Set brightness to 50%
uv run ./divoom-timebox-evo.py --mac XX:XX:XX:XX:XX:XX brightness 50

# Show current time
uv run ./divoom-timebox-evo.py --mac XX:XX:XX:XX:XX:XX time

# Display a colorful clock
uv run ./divoom-timebox-evo.py --mac XX:XX:XX:XX:XX:XX clock --style rainbow
```

## Step 4: Save Your MAC Address

Create an alias to avoid typing it every time:

```bash
# Add to ~/.bashrc or ~/.zshrc
alias divoom='uv run /path/to/divoom-timebox-evo.py --mac XX:XX:XX:XX:XX:XX'

# Then use it:
divoom brightness 75
divoom clock --style fullscreen --weather
divoom light 255 0 128 --effect breathing
```

## Common Commands

```bash
# Brightness
divoom brightness 75

# Sync time
divoom time

# Solid red light
divoom light 255 0 0

# Pulsing blue light
divoom light 0 0 255 --effect pulse

# Clock with weather
divoom clock --weather --temperature

# Audio visualizer
divoom visualizer 3

# Scoreboard (Blue 3, Red 2)
divoom scoreboard 3 2

# Weather display
divoom weather 22 --weather clear

# Show device info
divoom info
```

## Next Steps

- Read the full [README.md](README-NEW.md) for all features
- Check out [examples/](examples/) for Python library usage
- Customize clock colors: `divoom clock --red 255 --green 100 --blue 0`
- Try different visualizer modes: `divoom visualizer <0-11>`
- Display your own images: `divoom image path/to/image.png`

## Troubleshooting

**"Failed to connect"**
- Make sure device is powered on
- Check Bluetooth is running: `systemctl status bluetooth`
- Try pairing first in `bluetoothctl`

**"Python was not compiled with Bluetooth support"**
- Install: `sudo apt install libbluetooth-dev python3-dev` (Debian/Ubuntu)
- Or: `sudo dnf install bluez-libs-devel python3-devel` (Fedora)
- Reinstall Python or use system Python

**"Command not found: uv"**
- Use `pip` method instead (see README.md)
- Or install uv: `curl -LsSf https://astral.sh/uv/install.sh | sh`

## Help

```bash
# Show all commands
divoom --help

# Help for specific command
divoom light --help
divoom clock --help
```

---

Happy pixel pushing! 🎨
