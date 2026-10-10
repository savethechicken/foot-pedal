# boot.py - runs ONCE at power-up, before code.py
#
# Jobs:
#   1. Turn on a second USB serial port (the "data" port) that the
#      Pedal Config app uses to talk to the Pico.
#   2. Hide the CIRCUITPY drive unless the "show drive" pedal is held
#      while plugging in (same behavior as before).

import board
import storage
import usb_cdc
from digitalio import DigitalInOut, Direction, Pull

# ---- Build setting: pick the pedal to hold at plug-in to show the drive ----
SHOW_DRIVE_PIN = board.GP18      # three pedal: far-left pedal
# SHOW_DRIVE_PIN = board.GP16    # single pedal

# console=True keeps the normal REPL/serial console (Thonny, Mu).
# data=True adds a SECOND serial port just for the app, so app messages
# never mix with the console. Think of it as a second phone line.
usb_cdc.enable(console=True, data=True)

btn = DigitalInOut(SHOW_DRIVE_PIN)
btn.direction = Direction.INPUT
btn.pull = Pull.UP               # not pressed = True, pressed = False

# If the pedal is NOT held at startup, hide the drive
if btn.value:
    storage.disable_usb_drive()

btn.deinit()  # release the pin so code.py (keypad.Keys) can use it
