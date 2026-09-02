# MeRGBW / LT-06 BLE Protocol

Extracted from the MeRGBW Android app (package `com.mergbw.android`) for LT-06 based lamps
(e.g., "Sunset lights"), and verified against physical hardware.

- Service: `0000fff0-0000-1000-8000-00805f9b34fb`
- Write characteristic: `0000fff3-0000-1000-8000-00805f9b34fb`
- Notify characteristic: `0000fff4-0000-1000-8000-00805f9b34fb`

Write without response. All normal commands are 6–8 bytes, well under the default ATT MTU.

## Frame format

```
Byte0:      0x55 (head)
Byte1:      cmd
Byte2:      seq (always 0xFF — a fixed constant in the app, not a segment or device mask)
Byte3:      length = 5 + payload_len (total frame length, including head and checksum)
Bytes4..n-2: payload
Byte n-1:   checksum = (~sum(previous bytes)) & 0xFF   (one's complement — not two's, not XOR)
```

Byte 2 is hardcoded to `-1` (`0xFF`) for every command the app builds; it is not a
selector. Byte 3 counts the whole frame, not just the payload.

## Device types

The app dispatches on a device type byte and gives each type its own view-model with a
different command subset. "Sunset lights" is **type 5** (`夕阳灯`, "Sunset lamp"), which
sends only `0x03` (RGB), `0x05` (brightness) and `0x06` (scene).

This matters: commands that exist in the app's command table are not necessarily wired up
for every type. In particular `0x10`/`0x11`/`0x12` (`SET_WHITE_LIGHT`,
`SET_WHITE_BRIGHTNESS`, `SET_COLD_AND_WARM`) have **no type-5 call site** and are used by
types 3, 6, 7 and 8 instead. Do not send them to a type-5 lamp expecting white control —
see [Amber mode](#amber-mode-the-important-one) for how type 5 actually reaches its warm
output.

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

## Colour — `0x03`

Payload is `[R, G, B]`, one byte each, in that order. Verified on hardware: `FF 00 00`
gives red, `00 FF 00` green, `00 00 FF` blue.

```
RED:   55 03 FF 08 FF 00 00 A1
GREEN: 55 03 FF 08 00 FF 00 A1
BLUE:  55 03 FF 08 00 00 FF A1
```

There is **no white channel reachable through `0x03`**. RGB values chosen to approximate
warm white (e.g. `FF AA 5A`) render as a dim purple-white on this hardware, not amber. The
lamp's amber output is a separate emitter — see below.

## Brightness — `0x05`

**Payload range is 5–100.** The app computes `wire = slider + 5`, and its brightness
seekbar has `android:max = 95`, giving a wire range of 5 through 100.

Values above 100 are **not clamped**. They wrap, and the result is non-monotonic.
Verified on hardware by direct A/B comparison:

| Wire byte | Observed output |
|-----------|-----------------|
| `0x05` (5) | barely on |
| `0x32` (50) | roughly half |
| `0x64` (100) | full — hardware ceiling |
| `0x87` (135) | **dimmer than 100** |
| `0xFF` (255) | brighter than 135, still well below 100 |

Consistent with wrapping modulo 100 (135 → ~35, 255 → ~55), though only these three
out-of-range points were tested. The practical rule is simple: **clamp to 5–100 and never
send more than 100.** A driver that maps a 0–255 brightness scale straight onto this byte
will make "brighter" produce a dimmer lamp.

`0x64` already reaches the hardware ceiling, so the exact top of the accepted range
(whether 100 or 105) is not observable and does not matter in practice.

```
DIM:  55 05 FF 06 05 9B
HALF: 55 05 FF 06 32 6E
FULL: 55 05 FF 06 64 3C
```

## Amber mode — the important one

Type-5 lamps have a physical amber emitter that RGB mixing cannot reproduce. It is
reachable only as a **scene**, via `0x06`:

```
AMBER: 55 06 FF 06 86 19     (scene index 134, "Sunset")
```

Verified on hardware: sending this from a known green state switches the lamp to amber.
Visually it is a single warm emitter, distinct from the discrete RGB LEDs.

- **Brightness works in scene mode** using the ordinary `0x05` command — verified: wire `5`
  in amber mode takes it to almost off.
- **To leave amber mode, send any ordinary `0x03` colour frame.** There is no separate
  "exit scene" command, and none is needed — verified.

Type 5's scene payload is a **single index byte**. Do not use the two-byte `00 <id>` form
documented for TG201A firmware.

Other type-5 scene indices from the app, **not yet tested on hardware**:

| Index | Name |
|-------|------|
| 134 (`0x86`) | Sunset — **verified amber** |
| 139 (`0x8B`) | Sunrise |
| 142 (`0x8E`) | Summer sun |

## Power — `0x01`

```
ON:  55 01 FF 06 01 A3
OFF: 55 01 FF 06 00 A4
```

## Python PoC

`poc.py` provides a minimal sender using Bleak:

```
pip install bleak
MERGBW_ADDRESS=AA:BB:CC:DD:EE:FF python poc.py on
python poc.py rgb 255 0 0
python poc.py brightness 100
python poc.py amber
python poc.py scene 139
```

Defaults:
- BLE MAC from `MERGBW_ADDRESS` env
- Writes to characteristic `0000fff3-0000-1000-8000-00805f9b34fb`

## Verification status

Findings are tagged by how they are known:

- **Verified** — observed on a physical "Sunset lights" unit on 2026-09-02, by sending
  individual frames over BLE with a human watching the lamp and reporting the result.
  Covers: RGB channel order, the 5–100 brightness range and its wrap behaviour above 100,
  scene 134 as amber, brightness within scene mode, and the colour-frame exit from a scene.
- **From APK** — decompiled from `com.mergbw.android` 1.6.3. Covers: the command table,
  device-type dispatch, the `slider + 5` brightness relation, and the scene index names.
- **Untested** — scene indices 139 and 142, and every command outside
  `0x01`/`0x03`/`0x05`/`0x06`.

See `protocol/README.md` for a condensed reference.
