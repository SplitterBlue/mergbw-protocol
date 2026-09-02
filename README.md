# MeRGBW / LT-06 BLE Protocol

BLE protocol for LT-06 based lamps, as built by the MeRGBW Android app
(`com.mergbw.android`).

- Service: `0000fff0-0000-1000-8000-00805f9b34fb`
- Write characteristic: `0000fff3-0000-1000-8000-00805f9b34fb`
- Notify characteristic: `0000fff4-0000-1000-8000-00805f9b34fb`

Write without response. Commands are 6–8 bytes, well under the default ATT MTU.

## Frame format

```
Byte0:       0x55 (head)
Byte1:       cmd
Byte2:       seq — always 0xFF
Byte3:       length = 5 + payload_len (total frame length, including head and checksum)
Bytes4..n-2: payload
Byte n-1:    checksum = (~sum(previous bytes)) & 0xFF   (one's complement)
```

Byte 2 is hardcoded to `0xFF` for every command the app builds. Byte 3 counts the whole
frame.

## Device types

The app dispatches on a device type byte, giving each type its own view-model with its own
command subset. "Sunset lights" is **type 5** (`夕阳灯`, "Sunset lamp"), which sends `0x03`
(RGB), `0x05` (brightness) and `0x06` (scene).

A command in the table below is wired up only for the types whose view-model calls it.
`0x10`/`0x11`/`0x12` (`SET_WHITE_LIGHT`, `SET_WHITE_BRIGHTNESS`, `SET_COLD_AND_WARM`) have
no type-5 call site; they belong to types 3, 6, 7 and 8. Type 5 reaches its warm output
through [amber mode](#amber-mode).

## Command table

From `com.mergbw.core.ble.CommandList`:

| Cmd | Name | Cmd | Name |
|-----|------|-----|------|
| `0x00` | SYNC_STATUS | `0x0B` | SET_LED_NUM |
| `0x01` | POWER | `0x0C` | SYNC_TIME |
| `0x02` | FIRMWARE_INFO | `0x0D` | CONFIG_MODE |
| `0x03` | SET_COLOR | `0x0E` | CHECK_BIND_STATE |
| `0x04` | SET_PART_COLOR | `0x0F` | SET_MODE_SPEED |
| `0x05` | SET_BRIGHTNESS | `0x10` | SET_WHITE_LIGHT |
| `0x06` | SET_MODE (scene) | `0x11` | SET_WHITE_BRIGHTNESS |
| `0x07` | SET_MUSIC_MODE | `0x12` | SET_COLD_AND_WARM |
| `0x08` | SET_MUSIC_SENS | `0xF1`–`0xF6` | config: key mode, remote, info, RGB order, limit, complete |
| `0x09` | SET_DIY_MODE | | |
| `0x0A` | SET_TIMER | | |

## Color — `0x03`

Payload is `[R, G, B]`, one byte each, in that order.

```
RED:   55 03 FF 08 FF 00 00 A1
GREEN: 55 03 FF 08 00 FF 00 A1
BLUE:  55 03 FF 08 00 00 FF A1
```

`0x03` reaches the RGB LEDs only. An RGB approximation of warm white such as `FF AA 5A`
renders as a dim purple-white. The lamp's amber output comes from a separate emitter.

## Brightness — `0x05`

Payload range is **5–100**. The app computes `wire = slider + 5` against a brightness
seekbar with `android:max = 95`.

Values above 100 wrap, and the result is non-monotonic:

| Wire byte | Output |
|-----------|--------|
| `0x05` (5) | barely on |
| `0x32` (50) | roughly half |
| `0x64` (100) | full — hardware ceiling |
| `0x87` (135) | dimmer than 100 |
| `0xFF` (255) | between 135 and 100 |

This fits wrapping modulo 100 (135 → ~35, 255 → ~55). **Clamp to 5–100.** A driver mapping
a 0–255 brightness scale onto this byte makes "brighter" produce a dimmer lamp.

`0x64` already reaches the hardware ceiling, so the exact top of the accepted range is not
observable.

```
DIM:  55 05 FF 06 05 9B
HALF: 55 05 FF 06 32 6E
FULL: 55 05 FF 06 64 3C
```

## Amber mode

Type-5 lamps have a physical amber emitter, reachable as a **scene** via `0x06`:

```
AMBER: 55 06 FF 06 86 19     (scene index 134, "Sunset")
```

It is a single warm emitter, distinct from the discrete RGB LEDs.

- Brightness works in scene mode using the ordinary `0x05` command. Wire `5` in amber mode
  takes the lamp to almost off.
- Any ordinary `0x03` color frame leaves scene mode.

Type 5's scene payload is a single index byte.

| Index | Name | |
|-------|------|---|
| 134 (`0x86`) | Sunset | amber |
| 139 (`0x8B`) | Sunrise | untested |
| 142 (`0x8E`) | Summer sun | untested |

## Power — `0x01`

```
ON:  55 01 FF 06 01 A3
OFF: 55 01 FF 06 00 A4
```

## Python PoC

`poc.py` is a minimal sender using Bleak:

```
pip install bleak
MERGBW_ADDRESS=AA:BB:CC:DD:EE:FF python poc.py on
python poc.py rgb 255 0 0
python poc.py brightness 100
python poc.py amber
python poc.py scene 139
```

It reads the BLE MAC from `MERGBW_ADDRESS` and writes to characteristic
`0000fff3-0000-1000-8000-00805f9b34fb`.

See `protocol/README.md` for a condensed reference.
