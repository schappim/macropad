#!/usr/bin/env python3
"""Control the backlight on the Fafeicy 0x514C:0x8851 macropad.

Wire protocol matches the k884x family handled by
https://github.com/kriomant/ch57x-keyboard-tool — same packets, just sent
over the vendor-specific HID interface instead of raw libusb (which macOS
won't let us claim).

Usage:
  ./set_led.py off
  ./set_led.py backlight blue
  ./set_led.py backlight white
  ./set_led.py press red                # light up keys only when pressed
  ./set_led.py shock cyan               # "shock" effect on press
  ./set_led.py shock2 green             # alternate shock effect
  ./set_led.py backlight blue --layer 1 # set for layer 1 (0-2 supported)

Colors: red, orange, yellow, green, cyan, blue, purple (looks pink),
        plus 'white' (backlight only).

Install:
  python3 -m venv .venv && .venv/bin/pip install hid hidapi
  brew install hidapi
"""
import argparse
import sys
import hid

VID, PID = 0x514C, 0x8851

# (mode, color) tuples. Code byte = (color << 4) | mode.
MODE_CODES = {"off": 0, "backlight": 1, "shock": 2, "shock2": 3, "press": 4, "white": 5}
COLOR_CODES = {"red": 1, "orange": 2, "yellow": 3, "green": 4, "cyan": 5, "blue": 6, "purple": 7}


def encode(mode: str, color: str | None) -> int:
    if mode == "off":
        return 0
    if mode == "backlight" and color == "white":
        return (0 << 4) | MODE_CODES["white"]
    if mode not in MODE_CODES or mode == "white":
        raise SystemExit(f"unknown mode: {mode}")
    if color is None or color not in COLOR_CODES:
        raise SystemExit(f"mode '{mode}' requires a color from {sorted(COLOR_CODES)}")
    return (COLOR_CODES[color] << 4) | MODE_CODES[mode]


def find_vendor_path() -> bytes:
    for d in hid.enumerate(VID, PID):
        if d["usage_page"] == 0xFF00:
            return d["path"]
    raise SystemExit(
        f"vendor HID interface for {VID:#06x}:{PID:#06x} not found — is the macropad plugged in?"
    )


def send(dev: "hid.Device", msg: list[int]) -> None:
    # HID write: first byte is the report ID. The device has no report IDs
    # in its descriptor, so we send 0x00 and the remaining 64 bytes are the
    # report payload (zero-padded).
    dev.write(bytes([0x00]) + bytes(msg) + bytes(64 - len(msg)))


def set_led(mode: str, color: str | None, layer: int) -> None:
    if not 0 <= layer <= 2:
        raise SystemExit("layer must be 0, 1, or 2")
    code = encode(mode, color)
    dev = hid.Device(path=find_vendor_path())
    try:
        send(dev, [])  # init
        send(dev, [0x03, 0xFE, 0xB0, layer + 1, 0x08, 0x00, 0x00, 0x00, 0x00, 0x00, 0x01, 0x00, code])
        send(dev, [0x03, 0xFD, 0xFE, 0xFF])  # commit
    finally:
        dev.close()


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    p.add_argument("mode", choices=["off", "backlight", "shock", "shock2", "press"])
    p.add_argument("color", nargs="?", help="red, orange, yellow, green, cyan, blue, purple, or (backlight only) white")
    p.add_argument("--layer", type=int, default=0, help="layer 0-2 (default: 0)")
    args = p.parse_args()
    set_led(args.mode, args.color, args.layer)


if __name__ == "__main__":
    main()
