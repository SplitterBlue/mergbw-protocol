#!/usr/bin/env python3
"""
Proof-of-concept controller for MeRGBW / LT-06 lamps (e.g., "Sunset lights").

Usage:
  python poc.py on
  python poc.py off
  python poc.py rgb 255 0 0
  python poc.py brightness 100
  python poc.py amber
  python poc.py scene 139

Environment:
  MERGBW_ADDRESS  - BLE MAC address of the target lamp (required, or pass --address)
"""

import argparse
import asyncio
import os
import sys

from bleak import BleakClient

WRITE_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"

# Brightness is a 5-100 field: the app sends slider+5 with a slider max of 95. Values above
# 100 wrap, non-monotonically -- 135 comes out dimmer than 100, and 255 lands between the
# two. Mapping a 0-255 scale onto this byte makes "brighter" produce a dimmer lamp.
# See README.md.
BRIGHTNESS_MIN = 5
BRIGHTNESS_MAX = 100

# Type-5 scene indices. 134 drives the lamp's physical amber emitter; an RGB approximation
# of warm white through 0x03 renders as a dim purple-white.
SCENE_AMBER = 134
SCENES = {134: "Sunset (amber)", 139: "Sunrise", 142: "Summer sun"}


def build_frame(cmd: int, payload: bytes | None = None) -> bytes:
    """Construct a 0x55-framed command."""
    payload = payload or b""
    total_len = 5 + len(payload)
    frame = bytearray([0x55, cmd & 0xFF, 0xFF, total_len & 0xFF])
    frame.extend(payload)
    checksum = (~(sum(frame) & 0xFF)) & 0xFF
    frame.append(checksum)
    return bytes(frame)


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Send MeRGBW/LT-06 BLE commands")
    parser.add_argument(
        "--address",
        default=os.environ.get("MERGBW_ADDRESS"),
        help="BLE MAC address of the lamp (env MERGBW_ADDRESS)",
    )
    parser.add_argument(
        "command", choices=["on", "off", "rgb", "brightness", "amber", "scene"]
    )
    parser.add_argument("params", nargs="*", help="Command parameters")
    return parser.parse_args()


def build_from_cli(cmd: str, params: list[str]) -> bytes:
    if cmd == "on":
        return build_frame(0x01, bytes([0x01]))
    if cmd == "off":
        return build_frame(0x01, bytes([0x00]))
    if cmd == "rgb":
        if len(params) != 3:
            raise ValueError("rgb requires R G B")
        r, g, b = [max(0, min(255, int(x))) for x in params]
        return build_frame(0x03, bytes([r, g, b]))
    if cmd == "brightness":
        if len(params) != 1:
            raise ValueError(
                f"brightness requires a level ({BRIGHTNESS_MIN}-{BRIGHTNESS_MAX})"
            )
        requested = int(params[0])
        if not BRIGHTNESS_MIN <= requested <= BRIGHTNESS_MAX:
            raise ValueError(
                f"brightness must be {BRIGHTNESS_MIN}-{BRIGHTNESS_MAX}; "
                f"the lamp wraps values above {BRIGHTNESS_MAX} and would come out dimmer than full"
            )
        return build_frame(0x05, bytes([requested]))
    if cmd == "amber":
        return build_frame(0x06, bytes([SCENE_AMBER]))
    if cmd == "scene":
        if len(params) != 1:
            known = ", ".join(f"{i} = {n}" for i, n in sorted(SCENES.items()))
            raise ValueError(f"scene requires an index (known: {known})")
        index = int(params[0])
        if not 0 <= index <= 255:
            raise ValueError("scene index must be 0-255")
        return build_frame(0x06, bytes([index]))
    raise ValueError(f"Unhandled command {cmd}")


async def main():
    args = parse_args()
    if not args.address:
        print(
            "Error: no BLE address. Set MERGBW_ADDRESS or pass --address.",
            file=sys.stderr,
        )
        sys.exit(1)
    try:
        frame = build_from_cli(args.command, args.params)
    except ValueError as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)

    print(f"Target: {args.address}")
    print(f"Sending: {frame.hex()}")

    try:
        async with BleakClient(args.address) as client:
            await client.write_gatt_char(WRITE_UUID, frame, response=False)
            print("✓ sent")
    except Exception as exc:  # noqa: BLE001
        print(f"✗ failed: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    asyncio.run(main())
