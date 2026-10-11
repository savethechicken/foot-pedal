// FootPedalDual.ino - Foot pedal firmware for the Raspberry Pi Pico 2 W
// SPDX-License-Identifier: MIT  (c) 2026 savethechicken
//
// One Pico, two computers:
//   USB cable  -> Stream PC  (e.g. Discord Mute / Push to Mute)
//   Bluetooth  -> Gaming PC  (e.g. game push-to-talk)
//
// Each pedal has a key (or combo) for the USB PC and one for the Bluetooth PC.
// Holding a pedal holds the keys on both; letting go releases them on both.
//
// NEW in version 2: settings live in the Pico's flash memory and can be
// changed with the Pedal Config app over USB - no re-uploading needed.
//
// Build settings (Arduino IDE, Tools menu):
//   Board:               Raspberry Pi Pico 2W
//   IP/Bluetooth Stack:  IPv4 + Bluetooth
//   USB Stack:           Pico SDK
// Library needed (Tools -> Manage Libraries): ArduinoJson by Benoit Blanchon (v7)

#include <Keyboard.h>       // USB keyboard
#include <KeyboardBLE.h>    // Bluetooth Low Energy keyboard
#include <EEPROM.h>         // a small block of flash that acts like Python's NVM
#include <ArduinoJson.h>    // reads/writes the JSON messages the app sends
#include <PicoBluetoothBLEHID.h>  // Bluetooth connection status
#include <BluetoothLock.h>   // safe access to the Bluetooth system
#include <btstack.h>        // low-level Bluetooth, used only for "forget pairings"

// =====================================================================
// HARDWARE + DEFAULTS
// The DEFAULT_ tables are only used the very first time (or after a reset).
// After that, keys come from flash and are changed with the app.
// =====================================================================

const int   PEDAL_COUNT = 3;
const int   PEDAL_PINS[PEDAL_COUNT]  = {18, 17, 16};          // left to right
const char *PEDAL_NAMES[PEDAL_COUNT] = {"Left", "Middle", "Right"};
const int   MAX_KEYS = 6;               // keys per combo (e.g. Ctrl+Shift+Alt+Win+key)

const char *DEFAULT_BT_NAME = "Foot Pedal";
const char *DEFAULT_USB[PEDAL_COUNT][MAX_KEYS] = {
  {"F13"}, {"F14"}, {"F14"}
};
const char *DEFAULT_BT[PEDAL_COUNT][MAX_KEYS] = {
  {}, {"KEYPAD_FORWARD_SLASH"}, {"KEYPAD_ASTERISK"}
};

const int FIRMWARE_VERSION = 2;

// =====================================================================
// KEY NAMES
// The app talks in names like "F13" or "CONTROL" (the same names the
// CircuitPython version uses). This table turns a name into a HID key
// number - the code every USB/Bluetooth keyboard sends for that key.
// =====================================================================

struct KeyName { const char *name; uint8_t hid; };

// HID numbers 0xE0-0xE3 are the modifier keys (Ctrl, Shift, Alt, Win)
const KeyName KEY_TABLE[] = {
  {"CONTROL", 0xE0}, {"SHIFT", 0xE1}, {"ALT", 0xE2}, {"GUI", 0xE3},
  {"A", 4}, {"B", 5}, {"C", 6}, {"D", 7}, {"E", 8}, {"F", 9}, {"G", 10}, {"H", 11},
  {"I", 12}, {"J", 13}, {"K", 14}, {"L", 15}, {"M", 16}, {"N", 17}, {"O", 18}, {"P", 19},
  {"Q", 20}, {"R", 21}, {"S", 22}, {"T", 23}, {"U", 24}, {"V", 25}, {"W", 26}, {"X", 27},
  {"Y", 28}, {"Z", 29},
  {"ONE", 30}, {"TWO", 31}, {"THREE", 32}, {"FOUR", 33}, {"FIVE", 34},
  {"SIX", 35}, {"SEVEN", 36}, {"EIGHT", 37}, {"NINE", 38}, {"ZERO", 39},
  {"ENTER", 40}, {"ESCAPE", 41}, {"BACKSPACE", 42}, {"TAB", 43}, {"SPACEBAR", 44},
  {"F1", 58}, {"F2", 59}, {"F3", 60}, {"F4", 61}, {"F5", 62}, {"F6", 63},
  {"F7", 64}, {"F8", 65}, {"F9", 66}, {"F10", 67}, {"F11", 68}, {"F12", 69},
  {"PRINT_SCREEN", 70}, {"SCROLL_LOCK", 71}, {"PAUSE", 72}, {"INSERT", 73},
  {"HOME", 74}, {"PAGE_UP", 75}, {"DELETE", 76}, {"END", 77}, {"PAGE_DOWN", 78},
  {"RIGHT_ARROW", 79}, {"LEFT_ARROW", 80}, {"DOWN_ARROW", 81}, {"UP_ARROW", 82},
  {"KEYPAD_FORWARD_SLASH", 84}, {"KEYPAD_ASTERISK", 85}, {"KEYPAD_MINUS", 86},
  {"KEYPAD_PLUS", 87}, {"KEYPAD_ENTER", 88},
  {"KEYPAD_ONE", 89}, {"KEYPAD_TWO", 90}, {"KEYPAD_THREE", 91}, {"KEYPAD_FOUR", 92},
  {"KEYPAD_FIVE", 93}, {"KEYPAD_SIX", 94}, {"KEYPAD_SEVEN", 95}, {"KEYPAD_EIGHT", 96},
  {"KEYPAD_NINE", 97}, {"KEYPAD_ZERO", 98}, {"KEYPAD_PERIOD", 99},
  {"F13", 104}, {"F14", 105}, {"F15", 106}, {"F16", 107}, {"F17", 108}, {"F18", 109},
  {"F19", 110}, {"F20", 111}, {"F21", 112}, {"F22", 113}, {"F23", 114}, {"F24", 115},
};
const int KEY_TABLE_SIZE = sizeof(KEY_TABLE) / sizeof(KEY_TABLE[0]);

// Name -> HID number (0 = not found)
uint8_t hidFromName(const char *name) {
  if (name == nullptr) return 0;
  for (int i = 0; i < KEY_TABLE_SIZE; i++) {
    if (strcmp(KEY_TABLE[i].name, name) == 0) return KEY_TABLE[i].hid;
  }
  return 0;
}

// HID number -> name (for sending settings back to the app)
const char *nameFromHid(uint8_t hid) {
  for (int i = 0; i < KEY_TABLE_SIZE; i++) {
    if (KEY_TABLE[i].hid == hid) return KEY_TABLE[i].name;
  }
  return "?";
}

// The Arduino keyboard library wants modifiers as 0x80-0x83 and every
// other key as (HID number + 136). This converts our HID number to that.
uint8_t arduinoCode(uint8_t hid) {
  if (hid >= 0xE0 && hid <= 0xE3) return 0x80 + (hid - 0xE0);
  return hid + 136;
}

// =====================================================================
// SETTINGS IN FLASH
// =====================================================================

const uint32_t SETTINGS_MAGIC = 0x50454432;   // "PED2" - marks valid saved settings

struct Settings {
  uint32_t magic;
  char     btName[30];
  uint8_t  usb[PEDAL_COUNT][MAX_KEYS];        // HID numbers, 0 = empty slot
  uint8_t  bt[PEDAL_COUNT][MAX_KEYS];
};

Settings settings;

void loadDefaults() {
  memset(&settings, 0, sizeof(settings));     // fill with zeros = "no keys"
  settings.magic = SETTINGS_MAGIC;
  strncpy(settings.btName, DEFAULT_BT_NAME, sizeof(settings.btName) - 1);
  for (int p = 0; p < PEDAL_COUNT; p++) {
    for (int k = 0; k < MAX_KEYS; k++) {
      settings.usb[p][k] = hidFromName(DEFAULT_USB[p][k]);
      settings.bt[p][k]  = hidFromName(DEFAULT_BT[p][k]);
    }
  }
}

void saveSettings() {
  EEPROM.put(0, settings);
  EEPROM.commit();                            // actually write to flash
}

void loadSettings() {
  EEPROM.begin(512);
  EEPROM.get(0, settings);
  if (settings.magic != SETTINGS_MAGIC || settings.btName[0] == 0) {
    loadDefaults();                           // first run, or damaged data
    saveSettings();
  }
  settings.btName[sizeof(settings.btName) - 1] = 0;   // always properly ended
}

// =====================================================================
// PRESSING KEYS
// =====================================================================

// How many pedals are holding each key right now, per computer.
// A shared key (e.g. two pedals both sending F14) only releases when
// the LAST pedal using it lets go - like two people holding a door.
uint8_t usbHolders[256];
uint8_t btHolders[256];

void sendCombo(HID_Keyboard &kb, uint8_t holders[256], const uint8_t keys[MAX_KEYS], bool down) {
  for (int k = 0; k < MAX_KEYS; k++) {
    uint8_t hid = keys[k];
    if (hid == 0) continue;
    if (down) {
      if (holders[hid] == 0) kb.press(arduinoCode(hid));
      holders[hid]++;
    } else if (holders[hid] > 0) {
      holders[hid]--;
      if (holders[hid] == 0) kb.release(arduinoCode(hid));
    }
  }
}

void releaseEverything() {
  Keyboard.releaseAll();
  KeyboardBLE.releaseAll();
  memset(usbHolders, 0, sizeof(usbHolders));
  memset(btHolders, 0, sizeof(btHolders));
}

// =====================================================================
// TALKING TO THE APP (one line of JSON per message, over USB serial)
//   {"cmd":"hello"}                                  -> who are you?
//   {"cmd":"get"}                                    -> current settings
//   {"cmd":"set","keys":{"usb":[...],"bt":[...]}}    -> save new keys
//   {"cmd":"set_name","name":"..."}                  -> new Bluetooth name (restarts)
//   {"cmd":"forget_bt"}                              -> erase Bluetooth pairings (restarts)
// The pedal also sends {"event":"press","pedal":0} / "release".
// =====================================================================

String inputLine;
bool restartPending = false;

void sendJson(JsonDocument &doc) {
  if (!Serial) return;                        // no app listening
  serializeJson(doc, Serial);
  Serial.println();
}

void addKeysTo(JsonObject keys) {
  JsonArray usb = keys["usb"].to<JsonArray>();
  JsonArray bt  = keys["bt"].to<JsonArray>();
  for (int p = 0; p < PEDAL_COUNT; p++) {
    JsonArray u = usb.add<JsonArray>();
    JsonArray b = bt.add<JsonArray>();
    for (int k = 0; k < MAX_KEYS; k++) {
      if (settings.usb[p][k]) u.add(nameFromHid(settings.usb[p][k]));
      if (settings.bt[p][k])  b.add(nameFromHid(settings.bt[p][k]));
    }
  }
}

// Check one computer's list (e.g. keys["usb"]) and copy it into dest.
// Returns false if anything is wrong, so bad data is never saved.
bool readKeyList(JsonVariant list, uint8_t dest[PEDAL_COUNT][MAX_KEYS]) {
  if (!list.is<JsonArray>() || list.size() != PEDAL_COUNT) return false;
  for (int p = 0; p < PEDAL_COUNT; p++) {
    JsonVariant combo = list[p];
    if (!combo.is<JsonArray>() || combo.size() > MAX_KEYS) return false;
    for (int k = 0; k < MAX_KEYS; k++) dest[p][k] = 0;
    for (int k = 0; k < (int)combo.size(); k++) {
      uint8_t hid = hidFromName(combo[k].as<const char *>());
      if (hid == 0) return false;             // unknown key name
      dest[p][k] = hid;
    }
  }
  return true;
}

void forgetBluetoothPairings() {
  BluetoothLock lock;                         // required before using btstack directly
  for (int i = 0; i < le_device_db_max_count(); i++) {
    le_device_db_remove(i);
  }
}

void handleCommand(const String &line) {
  JsonDocument msg;
  JsonDocument reply;

  if (deserializeJson(msg, line)) {           // returns an error if it isn't valid JSON
    reply["ok"] = false;
    reply["error"] = "bad json";
    sendJson(reply);
    return;
  }

  String cmd = msg["cmd"] | "";

  if (cmd == "hello" || cmd == "get") {
    reply["ok"] = true;
    reply["device"] = "foot-pedal";
    reply["version"] = FIRMWARE_VERSION;
    reply["platform"] = "arduino-pico2w";
    JsonArray names = reply["pedals"].to<JsonArray>();
    for (int p = 0; p < PEDAL_COUNT; p++) names.add(PEDAL_NAMES[p]);
    JsonArray outs = reply["outputs"].to<JsonArray>();
    outs.add("usb");
    outs.add("bt");
    reply["bt_name"] = settings.btName;
    reply["bt_connected"] = PicoBluetoothBLEHID.connected();
    addKeysTo(reply["keys"].to<JsonObject>());
  }
  else if (cmd == "set") {
    uint8_t newUsb[PEDAL_COUNT][MAX_KEYS];
    uint8_t newBt[PEDAL_COUNT][MAX_KEYS];
    if (!readKeyList(msg["keys"]["usb"], newUsb) || !readKeyList(msg["keys"]["bt"], newBt)) {
      reply["ok"] = false;
      reply["error"] = "invalid keys";
    } else {
      releaseEverything();                    // let go of anything held with the old keys
      memcpy(settings.usb, newUsb, sizeof(newUsb));
      memcpy(settings.bt, newBt, sizeof(newBt));
      saveSettings();
      reply["ok"] = true;
      addKeysTo(reply["keys"].to<JsonObject>());
    }
  }
  else if (cmd == "set_name") {
    String name = msg["name"] | "";
    name.trim();
    if (name.length() < 1 || name.length() >= sizeof(settings.btName)) {
      reply["ok"] = false;
      reply["error"] = "name must be 1-29 characters";
    } else {
      strncpy(settings.btName, name.c_str(), sizeof(settings.btName) - 1);
      saveSettings();
      reply["ok"] = true;
      reply["restarting"] = true;             // the new name needs a restart
      restartPending = true;
    }
  }
  else if (cmd == "forget_bt") {
    forgetBluetoothPairings();
    reply["ok"] = true;
    reply["restarting"] = true;
    restartPending = true;
  }
  else {
    reply["ok"] = false;
    reply["error"] = "unknown command";
  }
  sendJson(reply);
}

void readSerial() {
  while (Serial.available()) {
    char c = Serial.read();
    if (c == '\n') {
      inputLine.trim();
      if (inputLine.length()) handleCommand(inputLine);
      inputLine = "";
    } else if (inputLine.length() < 1024) {
      inputLine += c;
    }
  }
}

// =====================================================================
// SETUP + MAIN LOOP
// =====================================================================

bool wasPressed[PEDAL_COUNT];
unsigned long changedAt[PEDAL_COUNT];
const unsigned long DEBOUNCE_MS = 15;

void setup() {
  Serial.begin(115200);
  pinMode(LED_BUILTIN, OUTPUT);
  for (int i = 0; i < PEDAL_COUNT; i++) {
    pinMode(PEDAL_PINS[i], INPUT_PULLUP);
    wasPressed[i] = false;
    changedAt[i] = 0;
  }

  loadSettings();

  Keyboard.begin();                           // USB keyboard -> stream PC
  KeyboardBLE.begin(settings.btName);         // Bluetooth keyboard -> gaming PC
}

void loop() {
  bool anyHeld = false;
  unsigned long now = millis();

  for (int i = 0; i < PEDAL_COUNT; i++) {
    bool pressed = (digitalRead(PEDAL_PINS[i]) == LOW);
    if (pressed) anyHeld = true;
    if (pressed == wasPressed[i]) continue;
    if (now - changedAt[i] < DEBOUNCE_MS) continue;   // bounce - ignore

    wasPressed[i] = pressed;
    changedAt[i] = now;

    sendCombo(Keyboard,    usbHolders, settings.usb[i], pressed);   // stream PC
    sendCombo(KeyboardBLE, btHolders,  settings.bt[i],  pressed);   // gaming PC

    JsonDocument ev;                          // tell the app, so it can light up
    ev["event"] = pressed ? "press" : "release";
    ev["pedal"] = i;
    sendJson(ev);
  }

  readSerial();

  if (restartPending) {
    delay(200);                               // give the reply time to reach the app
    rp2040.reboot();
  }

  digitalWrite(LED_BUILTIN, anyHeld ? HIGH : LOW);
  delay(2);
}
