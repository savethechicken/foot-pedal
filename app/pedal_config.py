"""
Pedal Config - a desktop app for changing which keys the foot pedal sends.

How it works, in one picture:
    [this app]  --- USB "data" serial port --->  [Pico running code.py]
       sends {"cmd": "set", "keys": [...]}         saves keys in its memory
       receives {"event": "press", "pedal": 0}     lights up pedal on screen

Needs: Python 3.9+ and pyserial  (pip install pyserial)
Run:   python pedal_config.py
"""

import json
import time
import tkinter as tk
from tkinter import ttk, messagebox

import serial                         # pyserial: talks to serial (COM) ports
from serial.tools import list_ports   # lists the COM ports on this computer

APP_TITLE = "Pedal Config"
CIRCUITPYTHON_VID = 0x239A            # USB vendor ID used by CircuitPython boards

# Modifier keys: (label shown in the app, Keycode name sent to the Pico)
MODIFIERS = [("Ctrl", "CONTROL"), ("Shift", "SHIFT"), ("Alt", "ALT"), ("Win", "GUI")]
MODIFIER_NAMES = {name for _, name in MODIFIERS}

# Main keys you can pick. These are adafruit_hid Keycode names.
MAIN_KEYS = (
    [f"F{n}" for n in range(13, 25)]          # F13-F24: great for pedals, no conflicts
    + [f"F{n}" for n in range(1, 13)]
    + [chr(c) for c in range(ord("A"), ord("Z") + 1)]
    + ["ONE", "TWO", "THREE", "FOUR", "FIVE", "SIX", "SEVEN", "EIGHT", "NINE", "ZERO"]
    + ["SPACEBAR", "ENTER", "ESCAPE", "TAB", "BACKSPACE", "DELETE", "INSERT",
       "HOME", "END", "PAGE_UP", "PAGE_DOWN",
       "UP_ARROW", "DOWN_ARROW", "LEFT_ARROW", "RIGHT_ARROW",
       "PRINT_SCREEN", "PAUSE", "SCROLL_LOCK"]
)


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
    labels = dict((name, label) for label, name in MODIFIERS)
    return " + ".join(labels.get(name, name) for name in combo)


# ---------------------------------------------------------------------------
# Talking to the pedal
# ---------------------------------------------------------------------------

class PedalLink:
    """Wraps one open serial port and speaks the pedal's JSON-lines language."""

    def __init__(self, port_name):
        # timeout=0 means read() returns right away with whatever has arrived
        # write_timeout stops the app from freezing on a port that never accepts data
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
    """Try each serial port and return a PedalLink to the one that's a pedal."""
    ports = list(list_ports.comports())
    # Check CircuitPython ports first - like checking the most likely drawer first
    ports.sort(key=lambda p: p.vid != CIRCUITPYTHON_VID)
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
            pass              # (pyserial's write timeout is a SerialException too)
        link.close()
    return None, None


# ---------------------------------------------------------------------------
# The window
# ---------------------------------------------------------------------------

class PedalRow:
    """The controls for one pedal: a light, modifier checkboxes and a key list."""

    def __init__(self, parent, name, column):
        self.frame = ttk.LabelFrame(parent, text=f" {name} ", padding=12)
        self.frame.grid(row=0, column=column, padx=8, sticky="n")

        # A little circle that turns green while the pedal is held down
        self.light = tk.Canvas(self.frame, width=26, height=26, highlightthickness=0)
        self.dot = self.light.create_oval(3, 3, 23, 23, fill="#555", outline="")
        self.light.pack(pady=(0, 8))

        self.mod_vars = {}
        for label, name_ in MODIFIERS:
            var = tk.BooleanVar()
            ttk.Checkbutton(self.frame, text=label, variable=var).pack(anchor="w")
            self.mod_vars[name_] = var

        ttk.Label(self.frame, text="Key").pack(anchor="w", pady=(8, 0))
        self.key_var = tk.StringVar()
        ttk.Combobox(self.frame, textvariable=self.key_var, values=MAIN_KEYS,
                     state="readonly", width=14).pack()

    def set_combo(self, combo):
        modifiers, main = split_combo(combo)
        for name, var in self.mod_vars.items():
            var.set(name in modifiers)
        self.key_var.set(main)

    def get_combo(self):
        modifiers = {name for name, var in self.mod_vars.items() if var.get()}
        return build_combo(modifiers, self.key_var.get())

    def set_lit(self, on):
        self.light.itemconfigure(self.dot, fill="#2ecc71" if on else "#555")


class App:
    def __init__(self, root):
        self.root = root
        self.link = None
        self.rows = []

        root.title(APP_TITLE)
        root.resizable(False, False)

        top = ttk.Frame(root, padding=10)
        top.pack(fill="x")
        ttk.Button(top, text="Connect", command=self.connect).pack(side="left")
        self.save_button = ttk.Button(top, text="Save to Pedal",
                                      command=self.save, state="disabled")
        self.save_button.pack(side="left", padx=6)
        self.reload_button = ttk.Button(top, text="Reload",
                                        command=self.reload, state="disabled")
        self.reload_button.pack(side="left")

        self.pedal_area = ttk.Frame(root, padding=(10, 0, 10, 10))
        self.pedal_area.pack()

        self.status = tk.StringVar(value="Plug in the pedal, then click Connect.")
        ttk.Label(root, textvariable=self.status, relief="sunken",
                  padding=(8, 4)).pack(fill="x", side="bottom")

        root.protocol("WM_DELETE_WINDOW", self.quit)
        root.after(200, self.connect)          # try once at start-up
        root.after(50, self.poll)              # start listening for pedal events

    # ---- connecting -------------------------------------------------------
    def connect(self):
        self.disconnect()
        self.status.set("Looking for the pedal...")
        self.root.update_idletasks()           # repaint before the search
        link, hello = find_pedal()
        if link is None:
            self.status.set("No pedal found. Is it plugged in, with the new "
                            "boot.py and code.py?")
            return
        self.link = link
        self.build_rows(hello["pedals"])
        self.save_button.config(state="normal")
        self.reload_button.config(state="normal")
        self.reload()

    def disconnect(self):
        if self.link:
            try:
                self.link.close()
            except (serial.SerialException, OSError):
                pass
        self.link = None
        self.save_button.config(state="disabled")
        self.reload_button.config(state="disabled")

    def build_rows(self, names):
        for child in self.pedal_area.winfo_children():
            child.destroy()
        self.rows = [PedalRow(self.pedal_area, name, i) for i, name in enumerate(names)]

    # ---- reading and saving keys -------------------------------------------
    def reload(self):
        reply = self.talk({"cmd": "get"})
        if reply and reply.get("ok"):
            for row, combo in zip(self.rows, reply["keys"]):
                row.set_combo(combo)
            self.status.set(f"Connected on {self.link.port_name}. "
                            "Press a pedal to see it light up.")

    def save(self):
        keys = [row.get_combo() for row in self.rows]
        if any(not split_combo(combo)[1] for combo in keys):
            messagebox.showwarning(APP_TITLE, "Pick a key for every pedal.")
            return
        reply = self.talk({"cmd": "set", "keys": keys})
        if reply and reply.get("ok"):
            summary = ",  ".join(describe(c) for c in keys)
            self.status.set(f"Saved: {summary}")
        elif reply:
            messagebox.showerror(APP_TITLE, f"The pedal said: {reply.get('error')}")

    def talk(self, message):
        """Send one command, handling a pedal that was unplugged."""
        if not self.link:
            return None
        try:
            return self.link.request(message)
        except (TimeoutError, serial.SerialException, OSError):
            self.disconnect()
            self.status.set("Lost the pedal. Plug it back in and click Connect.")
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
                    if 0 <= pedal < len(self.rows):
                        self.rows[pedal].set_lit(event["event"] == "press")
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
