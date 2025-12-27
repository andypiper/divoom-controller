#!/usr/bin/env python3
# /// script
# requires-python = ">=3.13"
# dependencies = [
#     "click>=8.1.0",
#     "rich>=13.0.0",
#     "pillow>=10.0.0",
# ]
# ///

"""
Divoom Timebox Evo Controller

A modern Python library and CLI for controlling Divoom Timebox Evo devices via Bluetooth.

Copyright (c) 2025 Andy Piper
SPDX-License-Identifier: MIT

Based on the divo project by spezifisch and contributors.
Protocol documentation from RomRider's node-divoom-timebox-evo.
"""

import math
import re
import socket
import struct
import subprocess
import sys
import sysconfig
from binascii import hexlify, unhexlify
from collections import OrderedDict
from datetime import datetime
from enum import IntEnum
from pathlib import Path
from typing import Optional

import click
from PIL import Image, ImageDraw, ImageFont
from rich.console import Console
from rich.panel import Panel
from rich.progress import track
from rich.table import Table

# ============================================================================
# Constants and Enumerations
# ============================================================================


class Command(IntEnum):
    """Divoom Timebox Evo command codes."""

    SET_TIME = 0x18
    SET_SYSTEM_COLOR = 0x24
    SEND_APP_NEWEST_TIME = 0x26  # Disable auto mode switching
    SET_24_HOUR = 0x2D
    LIGHT_CURRENT_LEVEL = 0x31
    CHANNEL = 0x45
    GET_SETTINGS = 0x46
    SET_BOX_COLOR = 0x44
    SET_BOX_MODE = 0x45
    GET_BOX_MODE = 0x46
    SET_MUL_BOX_COLOR = 0x49
    TEMPERATURE_WEATHER = 0x5F
    SET_SYSTEM_BRIGHTNESS = 0x74
    SET_GAME = 0xA0
    SET_SLEEP_COLOR = 0xAD
    SET_USER_GIF = 0xB1


class BoxMode(IntEnum):
    """Display modes for the device."""

    CLOCK = 0  # ENV mode
    LIGHT = 1
    CLOUD = 2  # HOT mode
    EFFECTS = 3  # SPECIAL mode
    VISUALIZER = 4  # MUSIC mode
    CUSTOM = 5  # USER_DEFINE mode
    SCOREBOARD = 6  # WATCH mode


class ClockStyle(IntEnum):
    """Available clock display styles."""

    FULLSCREEN = 0
    RAINBOW = 1
    BORDERED = 2
    ANALOG_SQUARE = 3
    FULLSCREEN_NEGATIVE = 4
    ANALOG_ROUND = 5
    WIDESCREEN = 6


class LightingEffect(IntEnum):
    """Available lighting effects."""

    PULSE = 0
    CYCLE = 1
    BREATHING = 2
    STROBE = 3
    SOLID = 4


class WeatherType(IntEnum):
    """Weather condition codes."""

    CLEAR = 1
    CLOUDY = 3
    THUNDERSTORM = 5
    RAIN = 6
    SNOW = 8
    FOG = 9


# Protocol constants
START_BYTE = 0x01
END_BYTE = 0x02


# ============================================================================
# Protocol Implementation
# ============================================================================


class DivoomProtocol:
    """Handles Divoom Timebox Evo protocol encoding and decoding."""

    @staticmethod
    def calculate_checksum(data: bytes) -> bytes:
        """Calculate LSB-first checksum for protocol data."""
        checksum = sum(data) & 0xFFFF
        lsb = checksum & 0xFF
        msb = (checksum >> 8) & 0xFF
        return bytes([lsb, msb])

    @staticmethod
    def encode_length(payload: bytes) -> bytes:
        """Encode payload length in LSB-first format."""
        length = len(payload) + 2  # +2 for checksum bytes
        return struct.pack("<H", length)

    @staticmethod
    def build_packet(command: int, payload: bytes = b"") -> bytes:
        """
        Build a complete packet with header, payload, checksum, and footer.

        Packet format: 01 LLLL CC PAYLOAD CRCR 02
        - 01: Start byte
        - LLLL: Length (payload + 2 for checksum) in LSB-first
        - CC: Command byte
        - PAYLOAD: Command-specific data
        - CRCR: Checksum in LSB-first
        - 02: End byte
        """
        # Build the data to be checksummed (length + command + payload)
        command_byte = bytes([command & 0xFF])
        length_bytes = DivoomProtocol.encode_length(command_byte + payload)
        checksum_data = length_bytes + command_byte + payload

        # Calculate checksum
        checksum = DivoomProtocol.calculate_checksum(checksum_data)

        # Assemble complete packet
        packet = (
            bytes([START_BYTE])
            + length_bytes
            + command_byte
            + payload
            + checksum
            + bytes([END_BYTE])
        )

        return packet

    @staticmethod
    def encode_image(pixel_data: list[int]) -> bytes:
        """
        Encode image pixel data using palette-based compression.

        Args:
            pixel_data: List of RGB colors as integers (0xRRGGBB format)

        Returns:
            Encoded image data ready to send
        """
        # Build color palette
        color_palette = OrderedDict()
        color_indices = []

        for color in pixel_data:
            if color not in color_palette:
                color_palette[color] = len(color_palette)
            color_indices.append(color_palette[color])

        # Calculate bits needed per pixel
        num_colors = len(color_palette)
        bits_per_pixel = max(1, int(math.ceil(math.log2(num_colors))))

        # Encode palette
        palette_size = num_colors % 256
        encoded = f"{palette_size:02x}"

        # Add colors to encoding
        for color in color_palette:
            encoded += f"{color:06x}"

        # Encode pixel indices with bit packing
        bit_string = ""
        for idx in color_indices:
            # Reverse bits for protocol
            bits = f"{idx:08b}"[-1::-1][:bits_per_pixel]
            bit_string += bits

        # Pack bits into bytes
        for i in range(-1, len(bit_string) - 1, 8):
            if i == -1:
                byte_bits = bit_string[i + 8 :: -1]
            else:
                byte_bits = bit_string[i + 8 : i : -1]
            encoded += f"{int(byte_bits, 2):02x}"

        # Add image header
        header = "000a0a04aa2d00000000"
        full_encoded = header + encoded

        return unhexlify(full_encoded)


# ============================================================================
# Device Discovery
# ============================================================================


def discover_bluetooth_devices(timeout: int = 10) -> list[dict[str, str]]:
    """
    Scan for Bluetooth devices.

    Args:
        timeout: Scan duration in seconds

    Returns:
        List of discovered devices with 'name' and 'address' keys
    """
    devices = []
    try:
        # Try using bluetoothctl for device discovery
        result = subprocess.run(
            ["bluetoothctl", "--timeout", str(timeout), "scan", "on"],
            capture_output=True,
            text=True,
            timeout=timeout + 5,
        )

        # Parse output for device information
        # Format: [NEW] Device XX:XX:XX:XX:XX:XX Device Name
        pattern = r"\[(?:NEW|CHG)\]\s+Device\s+([0-9A-F:]{17})\s+(.+)"
        for line in result.stdout.split("\n"):
            match = re.search(pattern, line, re.IGNORECASE)
            if match:
                address = match.group(1)
                name = match.group(2).strip()
                # Avoid duplicates
                if not any(d["address"] == address for d in devices):
                    devices.append({"address": address, "name": name})

    except (subprocess.TimeoutExpired, FileNotFoundError):
        # Fallback: try hcitool if bluetoothctl not available
        try:
            result = subprocess.run(
                ["hcitool", "scan"], capture_output=True, text=True, timeout=timeout
            )
            # Format: XX:XX:XX:XX:XX:XX  Device Name
            pattern = r"([0-9A-F:]{17})\s+(.+)"
            for line in result.stdout.split("\n")[1:]:  # Skip header
                match = re.search(pattern, line, re.IGNORECASE)
                if match:
                    devices.append(
                        {"address": match.group(1), "name": match.group(2).strip()}
                    )
        except (subprocess.TimeoutExpired, FileNotFoundError):
            pass

    return devices


def find_divoom_devices(timeout: int = 10) -> list[dict[str, str]]:
    """
    Scan for Divoom devices specifically.

    Args:
        timeout: Scan duration in seconds

    Returns:
        List of Divoom devices found
    """
    all_devices = discover_bluetooth_devices(timeout)
    divoom_devices = [
        d
        for d in all_devices
        if "divoom" in d["name"].lower() or "timebox" in d["name"].lower()
    ]
    return divoom_devices


# ============================================================================
# Text Rendering
# ============================================================================


def render_text_to_pixels(
    text: str,
    width: int = 16,
    height: int = 16,
    color: tuple[int, int, int] = (255, 255, 255),
    background: tuple[int, int, int] = (0, 0, 0),
    font_size: int = 8,
) -> list[int]:
    """
    Render text to pixel data for display.

    Args:
        text: Text to render
        width: Image width in pixels
        height: Image height in pixels
        color: Text color (R, G, B)
        background: Background color (R, G, B)
        font_size: Font size (default 8 works well for 16x16)

    Returns:
        List of pixel colors as integers
    """
    # Create image
    img = Image.new("RGB", (width, height), background)
    draw = ImageDraw.Draw(img)

    # Try to use a built-in font, fall back to default
    try:
        # Try to load a basic font
        font = ImageFont.truetype("/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf", font_size)
    except (OSError, IOError):
        try:
            font = ImageFont.truetype("/System/Library/Fonts/Helvetica.ttc", font_size)
        except (OSError, IOError):
            # Use default font
            font = ImageFont.load_default()

    # Get text bounding box to center it
    bbox = draw.textbbox((0, 0), text, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Center text
    x = (width - text_width) // 2
    y = (height - text_height) // 2

    # Draw text
    draw.text((x, y), text, fill=color, font=font)

    # Convert to pixel data
    pixel_data = []
    for py in range(height):
        for px in range(width):
            r, g, b = img.getpixel((px, py))
            pixel_color = (r << 16) | (g << 8) | b
            pixel_data.append(pixel_color)

    return pixel_data


# ============================================================================
# Bluetooth Communication
# ============================================================================


class BluetoothConnectionError(Exception):
    """Raised when Bluetooth connection fails."""

    pass


class BluetoothConnection:
    """Manages Bluetooth RFCOMM connection to Divoom device."""

    def __init__(self, mac_address: str, timeout: float = 5.0):
        """
        Initialize Bluetooth connection.

        Args:
            mac_address: Device MAC address (format: XX:XX:XX:XX:XX:XX)
            timeout: Socket timeout in seconds
        """
        self.mac_address = mac_address
        self.timeout = timeout
        self.socket: Optional[socket.socket] = None

        # Check if Bluetooth is supported
        if not self._check_bluetooth_support():
            raise BluetoothConnectionError(
                "Python was not compiled with Bluetooth support. "
                "Please install bluetooth development headers and recompile Python."
            )

    def _check_bluetooth_support(self) -> bool:
        """Check if Python has Bluetooth socket support."""
        config_vars = sysconfig.get_config_vars()
        return bool(
            config_vars.get("HAVE_BLUETOOTH_H")
            or config_vars.get("HAVE_BLUETOOTH_BLUETOOTH_H")
        )

    def connect(self) -> None:
        """Establish Bluetooth connection to device."""
        try:
            # BTPROTO_RFCOMM = 3
            self.socket = socket.socket(
                socket.AF_BLUETOOTH, socket.SOCK_STREAM, socket.BTPROTO_RFCOMM
            )
            self.socket.settimeout(self.timeout)
            self.socket.connect((self.mac_address, 1))  # RFCOMM channel 1
        except OSError as e:
            raise BluetoothConnectionError(f"Failed to connect: {e}") from e

    def disconnect(self) -> None:
        """Close Bluetooth connection."""
        if self.socket:
            try:
                self.socket.close()
            except OSError:
                pass
            finally:
                self.socket = None

    def send(self, data: bytes) -> None:
        """Send data to device."""
        if not self.socket:
            raise BluetoothConnectionError("Not connected")

        try:
            self.socket.sendall(data)
        except OSError as e:
            raise BluetoothConnectionError(f"Send failed: {e}") from e

    def receive(self, size: int) -> bytes:
        """Receive data from device."""
        if not self.socket:
            raise BluetoothConnectionError("Not connected")

        try:
            return self.socket.recv(size)
        except socket.timeout:
            return b""
        except OSError as e:
            raise BluetoothConnectionError(f"Receive failed: {e}") from e

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# ============================================================================
# Main Controller
# ============================================================================


class DivoomTimeboxEvo:
    """
    Main controller for Divoom Timebox Evo device.

    This class provides high-level methods to control the device,
    including setting time, brightness, colors, modes, and displaying images.
    """

    def __init__(self, mac_address: str, timeout: float = 5.0):
        """
        Initialize controller.

        Args:
            mac_address: Device Bluetooth MAC address
            timeout: Connection timeout in seconds
        """
        self.mac_address = mac_address
        self.timeout = timeout
        self.connection: Optional[BluetoothConnection] = None

    def connect(self) -> None:
        """Connect to the device."""
        self.connection = BluetoothConnection(self.mac_address, self.timeout)
        self.connection.connect()

    def disconnect(self) -> None:
        """Disconnect from the device."""
        if self.connection:
            self.connection.disconnect()
            self.connection = None

    def _send_command(self, command: Command, payload: bytes = b"") -> None:
        """Send a command to the device."""
        if not self.connection:
            raise BluetoothConnectionError("Not connected")

        packet = DivoomProtocol.build_packet(command.value, payload)
        self.connection.send(packet)

    def set_brightness(self, brightness: int) -> None:
        """
        Set display brightness.

        Args:
            brightness: Brightness level (0-100)
        """
        if not 0 <= brightness <= 100:
            raise ValueError("Brightness must be between 0 and 100")

        payload = bytes([brightness])
        self._send_command(Command.SET_SYSTEM_BRIGHTNESS, payload)

    def set_time(self, dt: Optional[datetime] = None) -> None:
        """
        Set device time.

        Args:
            dt: datetime object (uses current time if None)
        """
        if dt is None:
            dt = datetime.now()

        year = dt.year
        payload = bytes(
            [
                year % 100,
                year // 100,
                dt.month,
                dt.day,
                dt.hour,
                dt.minute,
                dt.second,
                dt.isoweekday() % 7,  # 0=Sunday
            ]
        )
        self._send_command(Command.SET_TIME, payload)

    def set_color(self, red: int, green: int, blue: int) -> None:
        """
        Set system color.

        Args:
            red: Red value (0-255)
            green: Green value (0-255)
            blue: Blue value (0-255)
        """
        payload = bytes([red & 0xFF, green & 0xFF, blue & 0xFF])
        self._send_command(Command.SET_SYSTEM_COLOR, payload)

    def set_temperature_weather(
        self, temperature: int, weather: WeatherType = WeatherType.CLEAR
    ) -> None:
        """
        Set temperature and weather display.

        Args:
            temperature: Temperature in Celsius (-128 to 127)
            weather: Weather condition
        """
        if not -128 <= temperature <= 127:
            raise ValueError("Temperature must be between -128 and 127")

        # Convert to signed byte
        temp_byte = temperature if temperature >= 0 else (256 + temperature)
        payload = bytes([temp_byte, weather.value])
        self._send_command(Command.TEMPERATURE_WEATHER, payload)

    def switch_channel(
        self, channel: BoxMode, options: bytes = b""
    ) -> None:
        """
        Switch to a different display channel/mode.

        Args:
            channel: Channel to switch to
            options: Channel-specific options
        """
        payload = bytes([channel.value]) + options
        self._send_command(Command.CHANNEL, payload)

    def disable_auto_mode_switching(self) -> None:
        """
        Disable automatic mode switching.

        The device has a feature that auto-cycles through different modes.
        This command disables that behavior so it stays in the current mode.
        """
        # Send 0 (False) to prevent auto-switching
        self._send_command(Command.SEND_APP_NEWEST_TIME, bytes([0]))

    def set_clock(
        self,
        style: ClockStyle = ClockStyle.FULLSCREEN,
        red: int = 255,
        green: int = 255,
        blue: int = 255,
        show_weather: bool = False,
        show_temperature: bool = False,
        show_date: bool = False,
        stay_in_mode: bool = True,
    ) -> None:
        """
        Set clock display mode.

        Args:
            style: Clock style
            red: Clock color red component
            green: Clock color green component
            blue: Clock color blue component
            show_weather: Show weather icon
            show_temperature: Show temperature
            show_date: Show date
            stay_in_mode: Prevent auto-switching to other modes (default: True)
        """
        # Disable auto-mode switching first if requested
        if stay_in_mode:
            self.disable_auto_mode_switching()

        # Protocol: [BoxMode, SubMode, ClockStyle, ClockEnabled, Weather, Temp, Date, R, G, B]
        payload = bytes(
            [
                BoxMode.CLOCK.value,  # 0 - Clock/ENV mode
                1,  # Submode - seems to always be 1 for clock
                style.value,  # Clock style
                1,  # Clock display enabled
                int(show_weather),
                int(show_temperature),
                int(show_date),
                red & 0xFF,
                green & 0xFF,
                blue & 0xFF,
            ]
        )
        self._send_command(Command.SET_BOX_MODE, payload)

    def set_lighting(
        self,
        red: int = 255,
        green: int = 255,
        blue: int = 255,
        effect: LightingEffect = LightingEffect.SOLID,
        brightness: int = 100,
    ) -> None:
        """
        Set lighting mode.

        Args:
            red: Red value (0-255)
            green: Green value (0-255)
            blue: Blue value (0-255)
            effect: Lighting effect (not currently used)
            brightness: Brightness (0-100, not currently used)
        """
        # Protocol: [BoxMode.LIGHT, R, G, B, 0x14, 0, clock, weather, temp, date]
        # For solid light mode, we disable clock/weather/temp/date
        payload = bytes([
            BoxMode.LIGHT,
            red & 0xFF,
            green & 0xFF,
            blue & 0xFF,
            0x14,  # Fixed value
            0,
            0,  # No clock
            0,  # No weather
            0,  # No temperature
            0,  # No date
        ])
        self._send_command(Command.SET_BOX_MODE, payload)

    def set_visualizer(self, visualizer_id: int = 0) -> None:
        """
        Set audio visualization mode.

        Args:
            visualizer_id: Visualizer ID (0-11)
        """
        if not 0 <= visualizer_id <= 11:
            raise ValueError("Visualizer ID must be between 0 and 11")

        # Protocol: [BoxMode.VISUALIZER, viz_id, 0, 0, 0, 0, 0, 0, 0, 0]
        payload = bytes([BoxMode.VISUALIZER, visualizer_id & 0xFF] + [0] * 8)
        self._send_command(Command.SET_BOX_MODE, payload)

    def set_scoreboard(self, blue_score: int, red_score: int) -> None:
        """
        Set scoreboard mode.

        Args:
            blue_score: Blue team score (0-999)
            red_score: Red team score (0-999)
        """
        if not 0 <= blue_score <= 999 or not 0 <= red_score <= 999:
            raise ValueError("Scores must be between 0 and 999")

        rs_lo = red_score & 0xFF
        rs_hi = (red_score >> 8) & 0xFF
        bs_lo = blue_score & 0xFF
        bs_hi = (blue_score >> 8) & 0xFF

        # Protocol: [BoxMode.SCOREBOARD, 0, red_lo, red_hi, blue_lo, blue_hi, 0, 0, 0, 0]
        payload = bytes([BoxMode.SCOREBOARD, 0, rs_lo, rs_hi, bs_lo, bs_hi, 0, 0, 0, 0])
        self._send_command(Command.SET_BOX_MODE, payload)

    def display_image(self, image_path: str, size: int = 16) -> None:
        """
        Display an image on the device.

        Args:
            image_path: Path to image file
            size: Display size (16x16 for Timebox Evo)
        """
        # Load and resize image
        img = Image.open(image_path)
        img = img.convert("RGB")
        img = img.resize((size, size), Image.Resampling.NEAREST)

        # Convert to pixel data
        pixel_data = []
        for y in range(size):
            for x in range(size):
                r, g, b = img.getpixel((x, y))
                color = (r << 16) | (g << 8) | b
                pixel_data.append(color)

        # Encode and send
        encoded = DivoomProtocol.encode_image(pixel_data)
        self._send_command(Command.SET_BOX_COLOR, encoded)

    def display_text(
        self,
        text: str,
        color: tuple[int, int, int] = (255, 255, 255),
        background: tuple[int, int, int] = (0, 0, 0),
        font_size: int = 8,
    ) -> None:
        """
        Display text on the device.

        Args:
            text: Text to display
            color: Text color (R, G, B)
            background: Background color (R, G, B)
            font_size: Font size (8 works well for 16x16)
        """
        # Render text to pixels
        pixel_data = render_text_to_pixels(
            text, color=color, background=background, font_size=font_size
        )

        # Encode and send
        encoded = DivoomProtocol.encode_image(pixel_data)
        self._send_command(Command.SET_BOX_COLOR, encoded)

    def __enter__(self):
        """Context manager entry."""
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.disconnect()


# ============================================================================
# CLI Interface
# ============================================================================

console = Console()


def validate_mac_address(ctx, param, value):
    """Validate MAC address format."""
    if value is None:
        return None

    # Check format XX:XX:XX:XX:XX:XX
    parts = value.split(":")
    if len(parts) != 6:
        raise click.BadParameter("MAC address must have format XX:XX:XX:XX:XX:XX")

    for part in parts:
        if len(part) != 2:
            raise click.BadParameter("Each MAC address octet must be 2 characters")
        try:
            int(part, 16)
        except ValueError:
            raise click.BadParameter("MAC address must contain hex digits only")

    return value


@click.group()
@click.option(
    "--mac",
    "-m",
    required=False,  # Not required for scan command
    callback=validate_mac_address,
    help="Device MAC address (XX:XX:XX:XX:XX:XX)",
)
@click.option("--timeout", "-t", default=5.0, help="Connection timeout in seconds")
@click.pass_context
def cli(ctx, mac, timeout):
    """
    Divoom Timebox Evo Controller

    Control your Divoom Timebox Evo device via Bluetooth from the command line.
    """
    ctx.ensure_object(dict)
    ctx.obj["mac"] = mac
    ctx.obj["timeout"] = timeout


def require_mac(ctx):
    """Validate that MAC address is provided."""
    if not ctx.obj.get("mac"):
        console.print("[red]✗[/red] Error: --mac option is required for this command", style="bold red")
        console.print("[dim]Tip: Use 'scan' command to find your device's MAC address[/dim]")
        sys.exit(1)


@cli.command()
@click.argument("brightness", type=click.IntRange(0, 100))
@click.pass_context
def brightness(ctx, brightness):
    """Set display brightness (0-100)."""
    require_mac(ctx)
    try:
        with DivoomTimeboxEvo(ctx.obj["mac"], ctx.obj["timeout"]) as device:
            device.set_brightness(brightness)
        console.print(f"[green]✓[/green] Brightness set to {brightness}%")
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.pass_context
def time(ctx):
    """Set device time to current system time."""
    try:
        with DivoomTimeboxEvo(ctx.obj["mac"], ctx.obj["timeout"]) as device:
            device.set_time()
        console.print("[green]✓[/green] Time synchronized")
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.argument("red", type=click.IntRange(0, 255))
@click.argument("green", type=click.IntRange(0, 255))
@click.argument("blue", type=click.IntRange(0, 255))
@click.option(
    "--effect",
    type=click.Choice(
        ["pulse", "cycle", "breathing", "strobe", "solid"], case_sensitive=False
    ),
    default="solid",
    help="Lighting effect",
)
@click.option(
    "--brightness", "-b", type=click.IntRange(0, 100), default=100, help="Brightness"
)
@click.pass_context
def light(ctx, red, green, blue, effect, brightness):
    """Set lighting mode with RGB color."""
    effect_map = {
        "pulse": LightingEffect.PULSE,
        "cycle": LightingEffect.CYCLE,
        "breathing": LightingEffect.BREATHING,
        "strobe": LightingEffect.STROBE,
        "solid": LightingEffect.SOLID,
    }

    try:
        with DivoomTimeboxEvo(ctx.obj["mac"], ctx.obj["timeout"]) as device:
            device.set_lighting(red, green, blue, effect_map[effect], brightness)

        # Show color preview
        color_block = f"[rgb({red},{green},{blue})]███[/rgb({red},{green},{blue})]"
        console.print(
            f"[green]✓[/green] Lighting set to {color_block} "
            f"RGB({red},{green},{blue}) with {effect} effect"
        )
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.option(
    "--style",
    type=click.Choice(
        [
            "fullscreen",
            "rainbow",
            "bordered",
            "analog-square",
            "fullscreen-negative",
            "analog-round",
            "widescreen",
        ],
        case_sensitive=False,
    ),
    default="fullscreen",
    help="Clock style (fullscreen/widescreen are simplest)",
)
@click.option("--red", "-r", type=click.IntRange(0, 255), default=255, help="Red")
@click.option("--green", "-g", type=click.IntRange(0, 255), default=255, help="Green")
@click.option("--blue", "-b", type=click.IntRange(0, 255), default=255, help="Blue")
@click.option("--weather", is_flag=True, help="Show weather icon")
@click.option("--temperature", is_flag=True, help="Show temperature")
@click.option("--date", is_flag=True, help="Show date")
@click.option(
    "--minimal",
    is_flag=True,
    help="Minimal clock (HH:MM only, no extras, widescreen style)",
)
@click.pass_context
def clock(ctx, style, red, green, blue, weather, temperature, date, minimal):
    """
    Set clock display mode.

    For a simple HH:MM display, use: --minimal

    Examples:
      Simple time only: --minimal
      With weather:     --weather --temperature
      Analog clock:     --style analog-round
    """
    style_map = {
        "fullscreen": ClockStyle.FULLSCREEN,
        "rainbow": ClockStyle.RAINBOW,
        "bordered": ClockStyle.BORDERED,
        "analog-square": ClockStyle.ANALOG_SQUARE,
        "fullscreen-negative": ClockStyle.FULLSCREEN_NEGATIVE,
        "analog-round": ClockStyle.ANALOG_ROUND,
        "widescreen": ClockStyle.WIDESCREEN,
    }

    # Minimal mode overrides everything
    if minimal:
        style = "widescreen"
        weather = False
        temperature = False
        date = False
        red = 255
        green = 255
        blue = 255

    try:
        with DivoomTimeboxEvo(ctx.obj["mac"], ctx.obj["timeout"]) as device:
            device.set_clock(
                style_map[style], red, green, blue, weather, temperature, date
            )

        if minimal:
            console.print("[green]✓[/green] Clock set to minimal mode (HH:MM only)")
        else:
            extras = []
            if weather:
                extras.append("weather")
            if temperature:
                extras.append("temperature")
            if date:
                extras.append("date")
            extra_text = f" with {', '.join(extras)}" if extras else ""
            console.print(f"[green]✓[/green] Clock set to {style} style{extra_text}")
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.argument("visualizer_id", type=click.IntRange(0, 11))
@click.pass_context
def visualizer(ctx, visualizer_id):
    """Set audio visualizer mode (0-11)."""
    try:
        with DivoomTimeboxEvo(ctx.obj["mac"], ctx.obj["timeout"]) as device:
            device.set_visualizer(visualizer_id)
        console.print(f"[green]✓[/green] Visualizer set to mode {visualizer_id}")
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.argument("blue", type=click.IntRange(0, 999))
@click.argument("red", type=click.IntRange(0, 999))
@click.pass_context
def scoreboard(ctx, blue, red):
    """Set scoreboard mode with blue and red scores."""
    try:
        with DivoomTimeboxEvo(ctx.obj["mac"], ctx.obj["timeout"]) as device:
            device.set_scoreboard(blue, red)
        console.print(f"[green]✓[/green] Scoreboard: [blue]Blue {blue}[/blue] - [red]Red {red}[/red]")
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.argument("temperature", type=click.IntRange(-128, 127))
@click.option(
    "--weather",
    type=click.Choice(
        ["clear", "cloudy", "thunderstorm", "rain", "snow", "fog"],
        case_sensitive=False,
    ),
    default="clear",
    help="Weather condition",
)
@click.pass_context
def weather(ctx, temperature, weather):
    """Set temperature and weather display."""
    weather_map = {
        "clear": WeatherType.CLEAR,
        "cloudy": WeatherType.CLOUDY,
        "thunderstorm": WeatherType.THUNDERSTORM,
        "rain": WeatherType.RAIN,
        "snow": WeatherType.SNOW,
        "fog": WeatherType.FOG,
    }

    try:
        with DivoomTimeboxEvo(ctx.obj["mac"], ctx.obj["timeout"]) as device:
            device.set_temperature_weather(temperature, weather_map[weather])
        console.print(
            f"[green]✓[/green] Weather set to {temperature}°C, {weather}"
        )
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.argument("image_path", type=click.Path(exists=True))
@click.pass_context
def image(ctx, image_path):
    """Display an image (will be resized to 16x16)."""
    try:
        with DivoomTimeboxEvo(ctx.obj["mac"], ctx.obj["timeout"]) as device:
            with console.status("[bold green]Encoding and sending image..."):
                device.display_image(image_path)
        console.print(f"[green]✓[/green] Image displayed from {image_path}")
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}", style="bold red")
        sys.exit(1)


@cli.command()
@click.pass_context
def info(ctx):
    """Show device and library information."""
    table = Table(title="Divoom Timebox Evo Controller", show_header=False)
    table.add_column("Property", style="cyan")
    table.add_column("Value", style="green")

    table.add_row("Device MAC", ctx.obj["mac"])
    table.add_row("Timeout", f"{ctx.obj['timeout']}s")
    table.add_row("Display Size", "16x16 pixels")
    table.add_row("Author", "Andy Piper")
    table.add_row("License", "MIT")
    table.add_row("Repository", "https://github.com/andypiper/divoom-controller")

    console.print(table)


@cli.command()
@click.option(
    "--timeout", "-t", default=10, help="Scan duration in seconds", type=int
)
def scan(timeout):
    """Scan for Divoom Bluetooth devices."""
    console.print(f"[bold]Scanning for Divoom devices...[/bold] ({timeout}s)")

    with console.status("[bold green]Scanning..."):
        devices = find_divoom_devices(timeout)

    if not devices:
        console.print("[yellow]No Divoom devices found.[/yellow]")
        console.print("\n[dim]Tip: Make sure your device is powered on and in pairing mode.[/dim]")
        return

    table = Table(title=f"Found {len(devices)} Divoom Device(s)")
    table.add_column("Name", style="cyan")
    table.add_column("MAC Address", style="green")

    for device in devices:
        table.add_row(device["name"], device["address"])

    console.print(table)
    console.print(
        f"\n[dim]Use --mac [green]{devices[0]['address']}[/green] to connect to the first device[/dim]"
    )


@cli.command()
@click.argument("text")
@click.option("--color", "-c", default="255,255,255", help="Text color (R,G,B)")
@click.option("--background", "-bg", default="0,0,0", help="Background color (R,G,B)")
@click.option("--font-size", "-s", default=8, type=int, help="Font size (default: 8)")
@click.pass_context
def text(ctx, text, color, background, font_size):
    """Display text on the device."""
    # Parse colors
    try:
        color_rgb = tuple(map(int, color.split(",")))
        bg_rgb = tuple(map(int, background.split(",")))

        if len(color_rgb) != 3 or len(bg_rgb) != 3:
            raise ValueError("Colors must have 3 values (R,G,B)")

        for val in color_rgb + bg_rgb:
            if not 0 <= val <= 255:
                raise ValueError("Color values must be 0-255")

    except ValueError as e:
        console.print(f"[red]✗[/red] Invalid color format: {e}", style="bold red")
        console.print("[dim]Use format: R,G,B (e.g., 255,0,0 for red)[/dim]")
        sys.exit(1)

    try:
        with DivoomTimeboxEvo(ctx.obj["mac"], ctx.obj["timeout"]) as device:
            with console.status("[bold green]Rendering and sending text..."):
                device.display_text(text, color=color_rgb, background=bg_rgb, font_size=font_size)
        console.print(f'[green]✓[/green] Text "{text}" displayed')
    except Exception as e:
        console.print(f"[red]✗[/red] Error: {e}", style="bold red")
        sys.exit(1)


if __name__ == "__main__":
    cli()
