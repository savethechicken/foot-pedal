# SPDX-License-Identifier: MIT  (c) 2026 savethechicken - see LICENSE-CODE
"""
Pedal Config Dual - changes which keys the dual-PC foot pedal sends.

For the Pico 2 W pedal running the Arduino firmware (FootPedalDual.ino):
each pedal sends one key (or combo) to the USB computer and one to the
Bluetooth computer. The original CircuitPython pedal uses Pedal Config instead.

How it works, in one picture:
    [this app]  --- USB serial port --->  [Pico]
       sends {"cmd": "set", "keys": ...}     saves keys in its memory
       receives {"event": "press", ...}      lights up the pedal on screen

Needs: Python 3.9+ and pyserial  (py -m pip install pyserial)
Run:   py pedal_config_dual.py
"""

import json
import time
import tkinter as tk
from tkinter import ttk, messagebox

import serial                         # pyserial: talks to serial (COM) ports
from serial.tools import list_ports   # lists the COM ports on this computer

APP_TITLE = "Pedal Config Dual"
PEDAL_VIDS = (0x2E8A,)                # USB vendor ID used by Raspberry Pi boards

# Modifier keys: (label shown in the app, key name sent to the Pico)
MODIFIERS = [("Ctrl", "CONTROL"), ("Shift", "SHIFT"), ("Alt", "ALT"), ("Win", "GUI")]
MODIFIER_NAMES = {name for _, name in MODIFIERS}

NONE_LABEL = "(none)"

# Main keys you can pick: (label shown in the app, key name sent to the Pico).
# The names are the same ones both pedal firmwares understand.
KEY_CHOICES = (
    [(f"F{n}", f"F{n}") for n in range(13, 25)]             # F13-F24: never clash with typing
    + [("Numpad /", "KEYPAD_FORWARD_SLASH"), ("Numpad *", "KEYPAD_ASTERISK"),
       ("Numpad -", "KEYPAD_MINUS"), ("Numpad +", "KEYPAD_PLUS"),
       ("Numpad Enter", "KEYPAD_ENTER"), ("Numpad .", "KEYPAD_PERIOD")]
    + [(f"Numpad {d}", f"KEYPAD_{w}") for d, w in
       [("0", "ZERO"), ("1", "ONE"), ("2", "TWO"), ("3", "THREE"), ("4", "FOUR"),
        ("5", "FIVE"), ("6", "SIX"), ("7", "SEVEN"), ("8", "EIGHT"), ("9", "NINE")]]
    + [(f"F{n}", f"F{n}") for n in range(1, 13)]
    + [(chr(c), chr(c)) for c in range(ord("A"), ord("Z") + 1)]
    + [(d, w) for d, w in
       [("1", "ONE"), ("2", "TWO"), ("3", "THREE"), ("4", "FOUR"), ("5", "FIVE"),
        ("6", "SIX"), ("7", "SEVEN"), ("8", "EIGHT"), ("9", "NINE"), ("0", "ZERO")]]
    + [("Space", "SPACEBAR"), ("Enter", "ENTER"), ("Esc", "ESCAPE"), ("Tab", "TAB"),
       ("Backspace", "BACKSPACE"), ("Delete", "DELETE"), ("Insert", "INSERT"),
       ("Home", "HOME"), ("End", "END"), ("Page Up", "PAGE_UP"), ("Page Down", "PAGE_DOWN"),
       ("Up arrow", "UP_ARROW"), ("Down arrow", "DOWN_ARROW"),
       ("Left arrow", "LEFT_ARROW"), ("Right arrow", "RIGHT_ARROW"),
       ("Print Screen", "PRINT_SCREEN"), ("Pause", "PAUSE"), ("Scroll Lock", "SCROLL_LOCK")]
)
LABEL_TO_NAME = dict(KEY_CHOICES)
NAME_TO_LABEL = {name: label for label, name in KEY_CHOICES}

# What each output is called on screen
OUTPUTS = ["usb", "bt"]
OUTPUT_TITLES = {"usb": "USB computer", "bt": "Bluetooth computer"}


# ---------------------------------------------------------------------------
# Helpers that don't touch the screen (easy to test on their own)
# ---------------------------------------------------------------------------

def split_combo(combo):
    """["CONTROL", "SHIFT", "F13"] -> ({"CONTROL", "SHIFT"}, "F13")"""
    modifiers = {name for name in combo if name in MODIFIER_NAMES}
    main = next((name for name in combo if name not in MODIFIER_NAMES), "")
    return modifiers, main


def build_combo(modifiers, main):
    """The reverse of split_combo. Modifiers go first, in a fixed order."""
    combo = [name for _, name in MODIFIERS if name in modifiers]
    if main:
        combo.append(main)
    return combo


def describe(combo):
    """["CONTROL", "F13"] -> "Ctrl + F13" (for messages to the user)."""
    if not combo:
        return "nothing"
    labels = dict((name, label) for label, name in MODIFIERS)
    labels.update(NAME_TO_LABEL)
    return " + ".join(labels.get(name, name) for name in combo)


# ---------------------------------------------------------------------------
# Talking to the pedal
# ---------------------------------------------------------------------------

class PedalLink:
    """Wraps one open serial port and speaks the pedal's JSON-lines language."""

    def __init__(self, port_name):
        # timeout=0: read() returns right away with whatever has arrived
        # write_timeout: never freeze on a port that won't accept data
        self.port = serial.Serial(port_name, 115200, timeout=0, write_timeout=1)
        self.port_name = port_name
        self.buffer = b""
        self.events = []          # pedal press/release events seen while waiting

    def close(self):
        self.port.close()

    def send(self, message):
        self.port.write((json.dumps(message) + "\n").encode())

    def read_lines(self):
        """Return any complete JSON messages that have arrived."""
        self.buffer += self.port.read(self.port.in_waiting or 1)
        messages = []
        while b"\n" in self.buffer:
            line, self.buffer = self.buffer.split(b"\n", 1)
            try:
                messages.append(json.loads(line.decode().strip()))
            except (ValueError, UnicodeError):
                pass              # not a message for us - ignore it
        return messages

    def request(self, message, wait=1.5):
        """Send a command and wait for its reply (an answer with "ok" in it)."""
        self.send(message)
        deadline = time.time() + wait
        while time.time() < deadline:
            for reply in self.read_lines():
                if "event" in reply:
                    self.events.append(reply)   # save it for the screen
                elif "ok" in reply:
                    return reply
            time.sleep(0.02)
        raise TimeoutError("The pedal didn't answer.")


def find_pedal():
    """Try each serial port and return (PedalLink, hello reply) for the pedal."""
    ports = list(list_ports.comports())
    # Check Pico ports first - like checking the most likely drawer first
    ports.sort(key=lambda p: p.vid not in PEDAL_VIDS)
    for info in ports:
        try:
            link = PedalLink(info.device)
        except (serial.SerialException, OSError):
            continue              # port busy or not openable - skip it
        try:
            reply = link.request({"cmd": "hello"}, wait=0.8)
            if reply.get("device") == "foot-pedal":
                return link, reply
        except (TimeoutError, serial.SerialException, OSError):
            pass                  # (pyserial's write timeout is a SerialException too)
        link.close()
    return None, None


# ---------------------------------------------------------------------------
# The window
# ---------------------------------------------------------------------------

class KeyPicker:
    """Modifier checkboxes + a key list, for one pedal and one computer."""

    def __init__(self, parent, title, allow_none):
        self.frame = ttk.Frame(parent)
        self.frame.pack(fill="x", pady=(6, 0))
        ttk.Label(self.frame, text=title, font=("Segoe UI", 9, "bold")).pack(anchor="w")

        mods = ttk.Frame(self.frame)
        mods.pack(anchor="w")
        self.mod_vars = {}
        for label, name in MODIFIERS:
            var = tk.BooleanVar()
            ttk.Checkbutton(mods, text=label, variable=var).pack(side="left")
            self.mod_vars[name] = var

        choices = ([NONE_LABEL] if allow_none else []) + [label for label, _ in KEY_CHOICES]
        self.key_var = tk.StringVar(value=NONE_LABEL if allow_none else "")
        ttk.Combobox(self.frame, textvariable=self.key_var, values=choices,
                     state="readonly", width=16).pack(anchor="w", pady=(2, 0))

    def set_combo(self, combo):
        modifiers, main = split_combo(combo)
        for name, var in self.mod_vars.items():
            var.set(name in modifiers)
        self.key_var.set(NAME_TO_LABEL.get(main, main) if main else NONE_LABEL)

    def get_combo(self):
        """Returns (combo, problem). problem is a message if something's wrong."""
        modifiers = {name for name, var in self.mod_vars.items() if var.get()}
        label = self.key_var.get()
        main = "" if label in ("", NONE_LABEL) else LABEL_TO_NAME.get(label, label)
        if modifiers and not main:
            return None, "has Ctrl/Shift/Alt/Win ticked but no key picked"
        return build_combo(modifiers, main), None


class PedalPanel:
    """One pedal: a light that shows presses, plus a KeyPicker per computer."""

    def __init__(self, parent, name, column):
        self.name = name
        self.frame = ttk.LabelFrame(parent, text=f" {name} ", padding=12)
        self.frame.grid(row=0, column=column, padx=8, sticky="n")

        self.light = tk.Canvas(self.frame, width=26, height=26, highlightthickness=0)
        self.dot = self.light.create_oval(3, 3, 23, 23, fill="#555", outline="")
        self.light.pack()

        # One picker per computer; either one can be "(none)"
        self.pickers = {}
        for out in OUTPUTS:
            self.pickers[out] = KeyPicker(self.frame, OUTPUT_TITLES[out], allow_none=True)

    def set_lit(self, on):
        self.light.itemconfigure(self.dot, fill="#2ecc71" if on else "#555")


class App:
    def __init__(self, root):
        self.root = root
        self.link = None
        self.hello = {}
        self.panels = []
        self.reconnect_tries = 0

        root.title(APP_TITLE)
        root.resizable(False, False)

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")
        ttk.Button(top, text="Connect", command=self.connect).pack(side="left")
        self.save_button = ttk.Button(top, text="Save to Pedal", command=self.save,
                                      state="disabled")
        self.save_button.pack(side="left", padx=6)
        self.reload_button = ttk.Button(top, text="Reload", command=self.reload,
                                        state="disabled")
        self.reload_button.pack(side="left")
        self.version_label = ttk.Label(top, text="", foreground="#888")
        self.version_label.pack(side="right")

        self.pedal_area = ttk.Frame(root, padding=(10, 0, 10, 4))
        self.pedal_area.pack()

        # Bluetooth controls - only shown for version 2 pedals
        self.bt_area = ttk.LabelFrame(root, text=" Bluetooth ", padding=10)
        self.bt_name_var = tk.StringVar()
        row = ttk.Frame(self.bt_area)
        row.pack(fill="x")
        self.bt_light = tk.Canvas(row, width=16, height=16, highlightthickness=0)
        self.bt_dot = self.bt_light.create_oval(2, 2, 14, 14, fill="#555", outline="")
        self.bt_light.pack(side="left")
        self.bt_status = ttk.Label(row, text="Unknown", width=14)
        self.bt_status.pack(side="left", padx=(4, 12))
        ttk.Label(row, text="Name:").pack(side="left")
        ttk.Entry(row, textvariable=self.bt_name_var, width=22).pack(side="left", padx=4)
        ttk.Button(row, text="Rename", command=self.rename).pack(side="left")
        ttk.Button(row, text="Forget Pairings", command=self.forget_pairings).pack(
            side="left", padx=(12, 0))
        ttk.Label(self.bt_area, foreground="#888",
                  text="Tip: many games ignore F13-F24. Numpad keys work well "
                       "for the Bluetooth computer.").pack(anchor="w", pady=(6, 0))

        self.bt_area.pack(fill="x", padx=18, pady=(0, 10))   # under the pedals

        self.status = tk.StringVar(value="Plug in the pedal, then click Connect.")
        ttk.Label(root, textvariable=self.status, relief="sunken",
                  padding=(8, 4)).pack(fill="x", side="bottom")

        root.protocol("WM_DELETE_WINDOW", self.quit)
        root.after(200, self.connect)          # try once at start-up
        root.after(50, self.poll)              # listen for pedal presses
        root.after(3000, self.check_bluetooth) # keep the Bluetooth light current

    # ---- connecting -------------------------------------------------------
    def connect(self):
        self.disconnect()
        self.status.set("Looking for the pedal...")
        self.root.update_idletasks()           # repaint before the search
        link, hello = find_pedal()
        if link is None:
            self.status.set("No pedal found. Is it plugged in? (Close Thonny or the "
                            "Arduino Serial Monitor if either is open.)")
            return False
        if "bt" not in hello.get("outputs", []):   # the original CircuitPython pedal
            link.close()
            self.status.set("This is the original (CircuitPython) pedal. "
                            "Use Pedal Config instead.")
            return False
        self.link = link
        self.hello = hello
        self.build_panels(hello["pedals"])
        self.save_button.config(state="normal")
        self.reload_button.config(state="normal")
        version = hello.get("version", 1)
        self.version_label.config(text=f"Pedal firmware v{version}")
        self.reload()
        return True

    def disconnect(self):
        if self.link:
            try:
                self.link.close()
            except (serial.SerialException, OSError):
                pass
        self.link = None
        self.save_button.config(state="disabled")
        self.reload_button.config(state="disabled")

    def build_panels(self, names):
        for child in self.pedal_area.winfo_children():
            child.destroy()
        self.panels = [PedalPanel(self.pedal_area, name, i)
                       for i, name in enumerate(names)]

    # ---- reading and saving keys -------------------------------------------
    def reload(self):
        reply = self.talk({"cmd": "get"})
        if not (reply and reply.get("ok")):
            return
        keys = reply["keys"]
        for out in OUTPUTS:
            for panel, combo in zip(self.panels, keys.get(out, [])):
                panel.pickers[out].set_combo(combo)
        self.bt_name_var.set(reply.get("bt_name", ""))
        self.show_bluetooth(reply.get("bt_connected"))
        self.status.set(f"Connected on {self.link.port_name}. "
                        "Press a pedal to see it light up.")

    def collect_keys(self):
        """Read every picker. Returns {output: [combo per pedal]} or None if invalid."""
        keys = {out: [] for out in OUTPUTS}
        for panel in self.panels:
            for out in OUTPUTS:
                combo, problem = panel.pickers[out].get_combo()
                if problem:
                    messagebox.showwarning(APP_TITLE, f"{panel.name} pedal "
                                           f"({OUTPUT_TITLES.get(out, out)}) {problem}.")
                    return None
                keys[out].append(combo)
        return keys

    def save(self):
        keys = self.collect_keys()
        if keys is None:
            return
        reply = self.talk({"cmd": "set", "keys": keys})
        if reply and reply.get("ok"):
            parts = []
            for i, panel in enumerate(self.panels):
                sends = [describe(keys[out][i]) for out in OUTPUTS]
                parts.append(f"{panel.name}: " + " | ".join(sends))
            self.status.set("Saved.  " + "   ".join(parts))
        elif reply:
            messagebox.showerror(APP_TITLE, f"The pedal said: {reply.get('error')}")

    # ---- Bluetooth (version 2 pedals) ---------------------------------------
    def show_bluetooth(self, connected):
        self.bt_light.itemconfigure(self.bt_dot, fill="#2ecc71" if connected else "#c0392b")
        self.bt_status.config(text="Connected" if connected else "Not connected")

    def check_bluetooth(self):
        """Every few seconds, ask the pedal whether the Bluetooth computer is connected."""
        if self.link:
            reply = self.talk({"cmd": "hello"}, quiet=True)
            if reply and reply.get("ok"):
                self.show_bluetooth(reply.get("bt_connected"))
        self.root.after(3000, self.check_bluetooth)

    def rename(self):
        name = self.bt_name_var.get().strip()
        if not 1 <= len(name) <= 29:
            messagebox.showwarning(APP_TITLE, "The name must be 1-29 characters.")
            return
        if not messagebox.askokcancel(APP_TITLE,
                f"Rename the pedal to \"{name}\"?\n\n"
                "The pedal will restart. Then, on the Bluetooth computer:\n"
                "  1. Remove the old pedal in Bluetooth settings\n"
                f"  2. Add device -> Bluetooth -> \"{name}\""):
            return
        reply = self.talk({"cmd": "set_name", "name": name})
        if reply and reply.get("ok"):
            self.wait_for_restart(f"Renamed to \"{name}\". Re-pair it on the Bluetooth computer.")
        elif reply:
            messagebox.showerror(APP_TITLE, f"The pedal said: {reply.get('error')}")

    def forget_pairings(self):
        if not messagebox.askokcancel(APP_TITLE,
                "Erase all Bluetooth pairings stored on the pedal?\n\n"
                "Use this if the Bluetooth computer shows the pedal as connected "
                "but no keys arrive.\n\nThe pedal will restart. Then, on the "
                "Bluetooth computer, remove the pedal and pair it again."):
            return
        reply = self.talk({"cmd": "forget_bt"})
        if reply and reply.get("ok"):
            self.wait_for_restart("Pairings erased. Remove and re-pair the pedal "
                                  "on the Bluetooth computer.")

    def wait_for_restart(self, done_message):
        """The pedal restarts after rename/forget: wait, then reconnect."""
        self.disconnect()
        self.done_message = done_message
        self.reconnect_tries = 0
        self.status.set("Pedal is restarting...")
        self.root.after(3000, self.try_reconnect)

    def try_reconnect(self):
        self.reconnect_tries += 1
        if self.connect():
            self.status.set(self.done_message)
        elif self.reconnect_tries < 10:
            self.status.set("Waiting for the pedal to come back...")
            self.root.after(1500, self.try_reconnect)
        else:
            self.status.set("The pedal didn't come back. Unplug it, plug it back in, "
                            "then click Connect.")

    # ---- talking safely -----------------------------------------------------
    def talk(self, message, quiet=False):
        """Send one command, handling a pedal that was unplugged."""
        if not self.link:
            return None
        try:
            return self.link.request(message)
        except (TimeoutError, serial.SerialException, OSError):
            self.disconnect()
            if not quiet:
                self.status.set("Lost the pedal. Plug it back in and click Connect.")
            else:
                self.status.set("Lost the pedal. Click Connect to try again.")
            return None

    # ---- live pedal lights --------------------------------------------------
    def poll(self):
        """Runs every 50 ms: check for press/release events from the pedal."""
        if self.link:
            try:
                events = self.link.events + [
                    m for m in self.link.read_lines() if "event" in m]
                self.link.events = []
                for event in events:
                    pedal = event.get("pedal", -1)
                    if 0 <= pedal < len(self.panels):
                        self.panels[pedal].set_lit(event["event"] == "press")
            except (serial.SerialException, OSError):
                self.disconnect()
                self.status.set("Lost the pedal. Plug it back in and click Connect.")
        self.root.after(50, self.poll)

    def quit(self):
        self.disconnect()
        self.root.destroy()


if __name__ == "__main__":
    window = tk.Tk()
    App(window)
    window.mainloop()
