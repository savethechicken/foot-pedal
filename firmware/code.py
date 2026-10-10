# SPDX-License-Identifier: MIT  (c) 2026 savethechicken - see LICENSE-CODE
# code.py - Foot pedal firmware with app-configurable keys
#
# What's new compared to the earlier code.py:
#   - The keys for each pedal are no longer hard-coded. They are saved in
#     the Pico's built-in memory (NVM), which survives unplugging.
#   - The Pedal Config app can read and change those keys over the USB
#     "data" serial port that boot.py turns on.
#   - Each pedal can send a single key (F13) or a combo (Ctrl+Shift+F13).

import json
import board
import keypad
import microcontroller
import usb_cdc
import usb_hid
from adafruit_hid.keyboard import Keyboard
from adafruit_hid.keycode import Keycode

# ---------------------------------------------------------------------------
# BUILD SETTINGS - the only part you should need to edit by hand.
# List the pedals LEFT to RIGHT as they sit on the floor in front of you.
# ---------------------------------------------------------------------------

# Three pedal (Pico is in the far-left pedal)
PEDAL_PINS = (board.GP18, board.GP17, board.GP16)
PEDAL_NAMES = ("Left", "Middle", "Right")
DEFAULT_KEYS = [["F13"], ["F14"], ["F15"]]

# Single pedal: comment out the three lines above and use these instead
# PEDAL_PINS = (board.GP16,)
# PEDAL_NAMES = ("Pedal",)
# DEFAULT_KEYS = [["F13"]]

FIRMWARE_VERSION = 1

# ---------------------------------------------------------------------------
# Saving and loading keys in NVM (non-volatile memory)
#
# NVM is a small block of flash (4 KB on the Pico) that keeps its contents
# when the power is off - like a tiny notebook the Pico carries around.
# Layout we use:
#   byte 0      = MAGIC  (a marker that says "we saved something here")
#   bytes 1-2   = how many bytes of JSON follow
#   bytes 3...  = the JSON text, e.g. [["F13"],["CONTROL","F14"],["F15"]]
# ---------------------------------------------------------------------------

MAGIC = 0xA7
nvm = microcontroller.nvm


def keys_are_valid(keys):
    """True if keys is a list with one non-empty list of real Keycode names per pedal."""
    if not isinstance(keys, list) or len(keys) != len(PEDAL_PINS):
        return False
    for combo in keys:
        if not isinstance(combo, list) or not combo or len(combo) > 6:
            return False
        for name in combo:
            # hasattr asks "does Keycode have something called this?"
            if not isinstance(name, str) or not hasattr(Keycode, name):
                return False
    return True


def load_keys():
    """Read saved keys from NVM, or fall back to DEFAULT_KEYS."""
    if nvm is None or nvm[0] != MAGIC:
        return DEFAULT_KEYS
    length = nvm[1] << 8 | nvm[2]       # rebuild the 2-byte length
    try:
        keys = json.loads(bytes(nvm[3:3 + length]).decode())
    except (ValueError, UnicodeError):
        return DEFAULT_KEYS
    return keys if keys_are_valid(keys) else DEFAULT_KEYS


def save_keys(keys):
    """Write keys to NVM. Returns True if it worked."""
    data = json.dumps(keys).encode()
    if nvm is None or len(data) + 3 > len(nvm):
        return False
    nvm[3:3 + len(data)] = data          # write the JSON first...
    nvm[1] = len(data) >> 8
    nvm[2] = len(data) & 0xFF
    nvm[0] = MAGIC                       # ...and the "valid" marker last
    return True


def to_keycodes(keys):
    """Turn names like ["CONTROL", "F13"] into the numbers adafruit_hid needs."""
    return [tuple(getattr(Keycode, name) for name in combo) for combo in keys]


# ---------------------------------------------------------------------------
# Talking to the app
#
# Every message is one line of JSON ending in a newline, like a text
# message. The app sends a command; the Pico sends back an answer.
#   {"cmd": "hello"}               -> who are you?
#   {"cmd": "get"}                 -> what keys are set?
#   {"cmd": "set", "keys": [...]}  -> use and save these keys
# The Pico also sends {"event": "press"/"release", "pedal": n} when a
# pedal is used, so the app can light up that pedal on screen.
# ---------------------------------------------------------------------------

def handle_command(message, state):
    """Act on one command from the app and return the reply (a dict)."""
    cmd = message.get("cmd")

    if cmd == "hello":
        return {"ok": True, "device": "foot-pedal",
                "version": FIRMWARE_VERSION, "pedals": list(PEDAL_NAMES)}

    if cmd == "get":
        return {"ok": True, "keys": state["keys"]}

    if cmd == "set":
        keys = message.get("keys")
        if not keys_are_valid(keys):
            return {"ok": False, "error": "invalid keys"}
        if not save_keys(keys):
            return {"ok": False, "error": "could not save"}
        state["keys"] = keys
        state["codes"] = to_keycodes(keys)
        state["reset_keyboard"] = True   # let go of anything held down
        return {"ok": True, "keys": keys}

    return {"ok": False, "error": "unknown command"}


def send(serial, message):
    if serial is not None and serial.connected:
        serial.write((json.dumps(message) + "\n").encode())


def read_messages(serial, buffer):
    """Collect bytes from the app; return (complete messages, leftover bytes)."""
    messages = []
    if serial is None or not serial.in_waiting:
        return messages, buffer
    buffer += serial.read(serial.in_waiting)
    while b"\n" in buffer:
        line, buffer = buffer.split(b"\n", 1)
        line = line.strip()
        if not line:
            continue
        try:
            messages.append(json.loads(line.decode()))
        except (ValueError, UnicodeError):
            messages.append({"cmd": "bad"})   # gets an "unknown command" reply
    if len(buffer) > 1024:               # junk with no newline - throw it away
        buffer = b""
    return messages, buffer


# ---------------------------------------------------------------------------
# Main loop
# ---------------------------------------------------------------------------

def main():
    keyboard = Keyboard(usb_hid.devices)
    pedals = keypad.Keys(PEDAL_PINS, value_when_pressed=False, pull=True)

    serial = usb_cdc.data                # None if boot.py didn't enable it
    if serial is not None:
        serial.timeout = 0               # never wait for data; just check

    keys = load_keys()
    state = {"keys": keys, "codes": to_keycodes(keys), "reset_keyboard": False}
    buffer = b""

    while True:
        # 1. Pedal presses -> keyboard keys
        event = pedals.events.get()
        if event:
            combo = state["codes"][event.key_number]
            if event.pressed:
                keyboard.press(*combo)   # * unpacks the tuple: press(CTRL, F13)
            else:
                keyboard.release(*combo)
            send(serial, {"event": "press" if event.pressed else "release",
                          "pedal": event.key_number})

        # 2. Messages from the app
        messages, buffer = read_messages(serial, buffer)
        for message in messages:
            send(serial, handle_command(message, state))

        # 3. After new keys are saved, make sure nothing is stuck down
        if state["reset_keyboard"]:
            keyboard.release_all()
            state["reset_keyboard"] = False


if __name__ == "__main__":
    main()
