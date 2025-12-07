#!/usr/bin/env python3
"""
Proof-of-concept controller for MeRGBW / LT-06 lamps (e.g., "Sunset lights").

Usage:
  python poc.py on
  python poc.py off
  python poc.py rgb 255 0 0
  python poc.py brightness 128

Environment:
  MERGBW_ADDRESS  - BLE MAC address (default: FF:FF:11:38:3D:36)
"""
import argparse
import asyncio
import os
import sys

from bleak import BleakClient

DEFAULT_ADDR = os.environ.get("MERGBW_ADDRESS", "FF:FF:11:38:3D:36")
WRITE_UUID = "0000fff3-0000-1000-8000-00805f9b34fb"


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
        default=DEFAULT_ADDR,
        help=f"BLE MAC address (env MERGBW_ADDRESS) [default: {DEFAULT_ADDR}]",
    )
    parser.add_argument("command", choices=["on", "off", "rgb", "brightness"])
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
            raise ValueError("brightness requires a level (0-255)")
        lvl = max(0, min(255, int(params[0])))
        return build_frame(0x05, bytes([lvl]))
    raise ValueError(f"Unhandled command {cmd}")


async def main():
    args = parse_args()
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
