"""
Persistent save data for the zombie game.
Stored as JSON — portable to web or other platforms.

Web porting note:
  In a browser / JS environment, swap open() + json for:
    save  -> localStorage.setItem("zombie_save", JSON.stringify(data))
    load  -> JSON.parse(localStorage.getItem("zombie_save") || "{}")
"""

import json
import os
import copy

SAVE_FILE = "save_data.json"

_DEFAULTS = {
    "skin_coins":    0,
    "skin_unlocked": False,
    "using_skin":    False,
    "settings":      {},
    "kill_stats":    {"zombie": 0, "fast": 0, "tank": 0, "police": 0, "boss": 0},
    "high_scores":   {},
}


def load():
    """Return a dict of all persistent values, filling missing keys with defaults."""
    if not os.path.exists(SAVE_FILE):
        return copy.deepcopy(_DEFAULTS)
    try:
        with open(SAVE_FILE, "r") as f:
            data = json.load(f)
        out = copy.deepcopy(_DEFAULTS)
        for k in _DEFAULTS:
            if k in data:
                out[k] = data[k]
        return out
    except Exception:
        return copy.deepcopy(_DEFAULTS)


def save(skin_coins, skin_unlocked, using_skin, settings, kill_stats, high_scores):
    """Write all persistent values to disk."""
    data = {
        "skin_coins":    int(skin_coins),
        "skin_unlocked": bool(skin_unlocked),
        "using_skin":    bool(using_skin),
        "settings":      dict(settings),
        "kill_stats":    dict(kill_stats),
        "high_scores":   dict(high_scores),
    }
    try:
        with open(SAVE_FILE, "w") as f:
            json.dump(data, f, indent=2)
    except Exception:
        pass
