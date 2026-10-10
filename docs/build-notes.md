# Foot Pedal Project – Notes

*Started: October 3, 2026*

## Overview

A USB foot pedal design in two versions: a **single pedal** and a **three-pedal** unit. Most parts are 3D printable.

Inspired by an earlier print of the USB Foot Switch on MakerWorld:
https://makerworld.com/en/models/2042179-usb-foot-switch#profileId-2203328

This is **not really a remix**: a few ideas came from the original pedal, but it's a complete redesign.

> ⚠️ **Parts are not interchangeable with the original USB Foot Switch.** The base and top/cover have different dimensions from the original design, so they won't swap between the two.

More details to come.

---

## Materials List

| Item | One Pedal | Three Pedal | Notes |
|---|---|---|---|
| M3 heat-set inserts | 2 | 6 | |
| M3 × 4 screws | 2 | 6 | Used on all pedals. M3 × 5 or M3 × 6 also work, but they're tighter and harder to tighten down (see Assembly) |
| Cherry MX mechanical key switch | 1 | 3 | |
| Compression spring | 2 | 6 | **3/8" × 3/4" (about 9.5 mm × 19.1 mm)** from the Harbor Freight 200-piece assorted set. See the Spring section for alternatives |
| Raspberry Pi Pico 1 or 2 | 1 | 1 | |
| M2 self-tapping screws (Pico mount) | Up to 4 | Up to 4 | Pico holes are 2.1 mm; the base's screw holes are modeled at **1.8 mm** so the screws cut threads into the plastic |
| 22 AWG wire | ✓ | ✓ | |
| Wago 221 lever connector (2-port) | ✓ | 2 | Used for the ground wire connection (see Wiring) |
| Superglue | Optional | Optional | Secures the wire runs between the pedals |
| Hot/cold glue gun | Optional | Optional | Mounts or holds down the Pico if M2 screws aren't available. Also secures the wire runs between the pedals |

---

## Wiring: Three Pedal

The Pico and USB connection are in the **far-left pedal** when the unit sits on the floor in front of you. Wires run through channels in the base to the middle and right pedals.

### Signal Wires (one per pedal, direct to the Pico)

> **Wire color doesn't matter.** These are just the colors I used. Don't call out specific colors in the install directions.

| Pedal | My wire color (any color works) | Code pin |
|---|---|---|
| Left, Pico pedal (1) | Blue | **GP18** ✅ |
| Middle (2) | Yellow | **GP17** ✅ |
| Right (3) | White | **GP16** ✅ |

### Ground (daisy-chained through Wagos)

```
Pico GND ──► Wago #1 (left pedal) ──► Switch 1
                  │
                  ▼
             Wago #2 (middle pedal) ──► Switch 2
                  │
                  ▼
               Switch 3 (right pedal)
```

- Every switch shares one common ground, so a **single** Pico GND pin serves all three pedals.
- **How I did it:** I didn't want three grounds soldered to the Pico, so one ground wire runs from the Pico to the Wagos. Where two wires share a Wago port, I twisted them together first. The 22 AWG wire is much smaller than the Wago's maximum wire size, so the twisted pair holds securely.
- **This is just one option.** You could also solder all the grounds together, or use the Pico's other GND pins (it has several).
- No diodes are needed: each pedal has its own signal pin (direct wiring, not a keyboard matrix), so there's no ghosting.

---

## Assembly

### Heat-Set Inserts

> ⚠️ **Go slow.** The inserts can be hard to get straight because there's no clear straight-on angle to the hole. With patience, they can be placed straight in the hole.

### Mounting the Pico

- **Option 1:** M2 self-tapping screws into the 1.8 mm holes in the base.
- **Option 2 (what I did):** Use a hot or cold glue gun to mount or hold down the Pico. This works well if M2 screws aren't available.

### Securing the Wiring

- Superglue and/or a glue gun can secure the wire runs between the pedals.

### Installing the Pedal Screws (Three Pedal)

There's very little room between the pedals, so I used **M3 × 4** screws on all the pedals. **M3 × 5 or M3 × 6 also work,** but the longer screws are tighter and harder to tighten down. Screw each one in until it's **flush on the inside**.

1. **Middle pedal first:** Install the screws on **both sides**. With the outer pedals not yet installed, there's room to use a driver.
2. **Left and right pedals:** On each one, put in the **outside screw** first.
3. **Inside screws (between pedals):** Use a **small Allen wrench** to reach into the gap between the two pedals. Turn the screw as far as the gap allows on each pass, then reposition and repeat until it's flush.

---

## Spring

### ✅ Current: 3/8" × 3/4" Compression Spring

**Final choice: 3/8" × 3/4" (about 9.5 mm × 19.1 mm), 2 per pedal.** It's a little taller and gives a little more resistance than the springs below.

- **Source:** Harbor Freight 200-Piece Assorted Spring Set: https://www.harborfreight.com/200-piece-assorted-spring-set-67562.html
- **The set includes 10 of this size,** enough for a three-pedal build (6 springs). The leftover springs and other sizes can be used in other prints.

### Other Springs Tested (same Harbor Freight set)

| Compression spring | Metric (approx.) | Qty in set | Result |
|---|---|---|---|
| 7/32" × 11/16" | 5.6 mm × 17.5 mm | 12 | Worked well, better than 3/8" × 5/8" |
| 3/8" × 5/8" | 9.5 mm × 15.9 mm | 12 | Works |

*Sizes are diameter × length.*

### ❌ Abandoned: 3D-Printed Springs

> I've had minimal success with printable springs. It's hit and miss. Even the ones that printed without supports failed before I could use them in the print (3 out of 5 broke). I switched to store-bought springs.

#### Parametric Octagonal Spring (OctaSpring), for reference

- **Source:** https://makerworld.com/en/models/2669388-parametric-octagonal-spring?from=search#profileId-2954420
- **Designer:** it_could_explode
- **Base file:** `GenericOctaSpring.f3d` (customized with MakerWorld's Parametric Model Maker)
- **Powered by MakerWorld Parametric Model Maker:** https://makerworld.com/makerlab/parametricModelMaker
- **Prints without supports**

##### Parameters Used

| Parameter | Value | Notes |
|---|---|---|
| Windings | 6.5 | Designer recommends ending in .125 to .875 (not a whole number) so the spring's end isn't printed in mid-air, which would need support |
| Length | 28 | mm |
| Strength | 2 | |
| Outer diameter (d out) | 10 | mm |
| Inner diameter (d in) | 4 | mm |

---

## Print Settings

> **No supports needed.** All printable parts print without supports.

### Filament

- **Recommended: PLA or PETG,** depending on what you have available.
- My unit is printed entirely in PLA. Test prints in PETG also worked great.

### Strength

| Setting | Value |
|---|---|
| Wall loops | 2 |
| Sparse infill density | 15% |

### Printers

- **Bambu Lab P1S:** Uses the speed settings below.
- **Snapmaker U1:** I'll print all parts on this too, with the **same speed settings below**. Its larger bed fits the **three-pedal base in one piece**, without splitting it.

### Speed Profile

- **Base profile:** 0.20mm Standard @BBL X1C (modified)

### Initial Layer Speed

| Setting | Value |
|---|---|
| Initial layer | 40 mm/s |
| Initial layer infill | 80 mm/s |

### Other Layers Speed

| Setting | Value |
|---|---|
| Outer wall | 150 mm/s |
| Inner wall | 200 mm/s |
| Small perimeters | 50% |
| Small perimeter threshold | 0 mm |
| Sparse infill | 200 mm/s |
| Internal solid infill | 200 mm/s |
| Vertical shell speed | 80% |
| Top surface | 150 mm/s |

### Overhangs

**Slow down for overhangs:** On

| Overhang amount | Speed |
|---|---|
| 10% | 0 mm/s (no slowdown) |
| 25% | 35 mm/s |
| 50% | 20 mm/s |
| 75% | 5 mm/s |
| 100% | 10 mm/s |

---

## Code: Single Pedal (`code.py`)

CircuitPython on a Raspberry Pi Pico. The pedal sends **F13** as a USB keyboard key.

```python
import board
import time
import usb_hid
from adafruit_hid.keycode import Keycode
from adafruit_hid.keyboard import Keyboard
from digitalio import DigitalInOut, Direction, Pull

keyboard = Keyboard(usb_hid.devices)   # makes the Pico act like a USB keyboard

btn1 = DigitalInOut(board.GP16)        # claims GP16 again (boot.py released it)
btn1.direction = Direction.INPUT
btn1.pull = Pull.UP

was_pressed = False                    # button state from the previous loop

while True:
    is_pressed = not btn1.value        # pressed = True, released = False

    if is_pressed and not was_pressed:     # button just went down
        keyboard.press(Keycode.F13)
    elif not is_pressed and was_pressed:   # button just came up
        keyboard.release(Keycode.F13)

    was_pressed = is_pressed
    time.sleep(0.01)
```

### How it works

- **Wiring:** Switch between **GP16** and **GND**. The internal pull-up holds the pin HIGH (`True`). Pressing the pedal connects it to ground (`False`), so `not btn1.value` flips it to read "pressed = True."
- **Edge detection:** `was_pressed` remembers the last loop's state. A key event is sent only when the state *changes*: press on the way down, release on the way up. Holding the pedal holds F13, the same as holding a key.
- **`time.sleep(0.01)`:** The loop checks the pedal about 100 times per second. This also works as simple debouncing.
- **`boot.py`:** The comment on GP16 refers to `boot.py` (below). It uses the pin at startup and then releases it.

### `boot.py` (Single Pedal)

Runs once at power-up, before `code.py`. It decides whether the Pico's **CIRCUITPY** USB drive shows up on the computer.

```python
import board
import storage
from digitalio import DigitalInOut, Direction, Pull

btn1 = DigitalInOut(board.GP16)
btn1.direction = Direction.INPUT
btn1.pull = Pull.UP

# If the button is NOT held at startup, hide the drive
if btn1.value:
    storage.disable_usb_drive()

btn1.deinit()  # hand GP16 over to code.py
```

#### How it works

- **Normal plug-in (pedal not pressed):** `btn1.value` is `True` (pull-up = HIGH), so `storage.disable_usb_drive()` hides the CIRCUITPY drive. The computer sees only a keyboard.
- **Hold the pedal while plugging in:** `btn1.value` is `False`, so the drive stays visible. Use this to edit or update the code.
- **`btn1.deinit()`:** This releases GP16 so `code.py` can claim it. Without it, `code.py` fails with a "pin in use" error.
- **Note:** `boot.py` changes take effect only after a full power cycle (unplug and replug) or a hard reset, not a normal code reload.

---

## Code: Three Pedal (`code.py`) ✅ TESTED

CircuitPython on a Raspberry Pi Pico. Each pedal sends its own key: **F13 / F14 / F15**.

> **Tested Oct 5, 2026:** It works with all three pedals. I tested it with `Keycode.A, B, C` (visible in Notepad) and with `Keycode.F21, F22, F14`. To change keys, edit only the `BUTTON_KEYS` line. Keycode names must be **UPPERCASE** (`Keycode.A`, not `Keycode.a`).

```python
import board
import keypad
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode
from digitalio import DigitalInOut, Direction, Pull

keyboard = Keyboard(usb_hid.devices)   # makes the Pico act like a USB keyboard

# Each button's pin and the key it sends, in matching order
BUTTON_PINS = (board.GP16, board.GP17, board.GP18)
BUTTON_KEYS = (Keycode.F13, Keycode.F14, Keycode.F15)

# Watch all the buttons: pressed = pin pulled low, use internal pull-ups
keys = keypad.Keys(BUTTON_PINS, value_when_pressed=False, pull=True)

while True:
    event = keys.events.get()          # next button event, or None if nothing happened
    if event:
        key = BUTTON_KEYS[event.key_number]
        if event.pressed:
            keyboard.press(key)
        else:
            keyboard.release(key)
```

### How it works

| Pedal | Pin | Key |
|---|---|---|
| Right | GP16 | F13 |
| Middle | GP17 | F14 |
| Left (Pico pedal) | GP18 | F15 |

- **Wiring:** Each switch goes between its pin and **GND**, the same as the single pedal.
- **`keypad.Keys`:** CircuitPython's built-in module scans all three pins in the background. It handles pull-ups, debouncing, and change detection, which replaces the `was_pressed` logic in the single-pedal version.
- **Events:** `keys.events.get()` returns a press or release event, or `None` if nothing changed. `event.key_number` is the pedal's position in `BUTTON_PINS` (0, 1, or 2). That number picks the matching key from `BUTTON_KEYS`.
- **Note:** `DigitalInOut, Direction, Pull` are imported but not used, because `keypad` handles the pins. They're harmless and could be removed.

### `boot.py` (Three Pedal)

Runs once at power-up, before `code.py`. It works the same as the single-pedal version, but uses the **far-left pedal (GP18)** as the "show drive" button.

```python
import board
import storage
from digitalio import DigitalInOut, Direction, Pull

btn3 = DigitalInOut(board.GP18)
btn3.direction = Direction.INPUT
btn3.pull = Pull.UP

#If the button is NOT held at startup, hide the drive
if btn3.value:
    storage.disable_usb_drive()

btn3.deinit()  # hand GP18 over to code.py
```

#### How it works

- **Normal plug-in (pedal not pressed):** The CIRCUITPY drive is hidden. The computer sees only a keyboard.
- **Hold the far-left pedal (GP18) while plugging in:** The drive shows up for editing.
- **`btn3.deinit()`:** This releases GP18 so `keypad.Keys` in `code.py` can claim it along with GP16 and GP17.

#### Rebooting without unplugging

Saving a file or pressing **Ctrl+D** only reloads `code.py`. It **skips `boot.py`**. For a full restart that runs `boot.py`, open the serial console (REPL), press **Ctrl+C** to stop `code.py`, then run:

```python
import microcontroller
microcontroller.reset()
```

To get the drive to show this way, hold the far-left pedal while pressing Enter on the `reset()` line. The serial console still works when the drive is hidden.

---

## Companion App: Pedal Config 🚧 In Progress (Oct 10, 2026)

A Python desktop app (tkinter + pyserial) that changes each pedal's key without editing `code.py`. The full code and setup steps are in the `pedal-config` project folder (`README.md`).

- **Connection:** USB serial. `boot.py` turns on a second serial port (`usb_cdc` data) just for the app, so it works with the CIRCUITPY drive hidden.
- **Storage:** Keys are saved in the Pico's NVM (`microcontroller.nvm`), so they survive unplugging and work on any computer, even without the app.
- **Keys:** Single keys or combos (Ctrl / Shift / Alt / Win + a key).
- **Builds:** Supports both the single and three-pedal builds. The app reads the pedal count from the Pico.
- **Live check:** Each pedal's dot in the app turns green while pressed.
- **Pedal order is now left to right:** defaults are Left = F13, Middle = F14, Right = F15 (the reverse of the earlier three-pedal `code.py`).
- **Status:** Tested on a simulated Pico. Not yet tested on the real pedal.

---

## To Do / Future Details

- [x] Test the three-pedal `code.py`
- [x] Decide on a `boot.py` for the three pedal (GP18, far-left pedal)
- [ ] Test the Pedal Config app on the real pedal
- [ ] Single pedal design details
- [ ] Three-pedal design details
- [x] Confirm whether superglue is needed (optional, for the wire runs)
- [x] Add Pico mounting screw size (M2 self-tapping, 1.8 mm holes in base)
- [x] Other print settings (strength: 2 walls, 15% infill)
