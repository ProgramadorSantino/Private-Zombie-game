# CHECKLIST — SCP Containment Breach (Zombie Game)

---

## Features Added
- Two game modes: **Scaperoom** (collect keys, reach the door, avoid the Doctor) and **Survival** (kill all zombies to advance)
- Four difficulty levels: Easy, Normal, Hard, Nightmare — affect enemy speed and coin rewards
- Four enemy types: **Zombie** (2 HP), **Fast Zombie** (1 HP), **Tank Zombie** (4 HP, 2 lives damage on hit) **PoliceZombie** (3 HP shoots bullets at player)
- Four weapons: Regular shot (SPACE), Super shot (N), Shotgun (B), Bomb (V)
- Explosion system: small explosions for regular/explosive shots (8 frames), large super explosions for bombs (10 frames)
- Upgrade shop (opens every 5 levels): buy lives, max lives +5, halve cooldowns, 6-shot shotgun, explosive shots, bomb unlock
- Cosmetic shop (accessible while paused with S): zombie skin, toggle equip/unequip
- Coin economy: enemies drop coins, used to buy upgrades
- Level progression: zombies increase in count and speed each wave, tank zombies appear every 3 levels (6 on Easy)
- Animated explosion visuals drawn from sprite sheets, independent lists per explosion type
- Bomb projectile: travels in facing direction, triggers large area explosion on impact with zombie or wall

---

## Requirements & Installation

### Python
Requires **Python 3.7+**
Download: https://www.python.org/downloads/

### Install dependencies
Run these commands in your terminal:

```
pip install pgzero
pip install pygame
```

### Run the game
```
pgzrun main.py
```

### Built-in modules (no install needed)
- `random` — standard library
- `time` — standard library
- `sys` — standard library

---

## Human Errors
**How readable is the code?**
Moderate. Functions are clearly named and separated by comment banners, but the file is a single 1100+ line script with no separation into modules. A new reader would need to scan the whole file to understand the structure.

**How is the indentation?**
Inconsistent in places. Most code uses 4-space indentation correctly, but there are several spots with misaligned comments, stray blank lines, and one known leftover triple-assignment of `self.state` in `GameState.__init__` (set to `"playing"`, then `"menu"`, then `"mode_select"` — only the last one matters, the first two are dead code).

---

## Project Problems
**What does the code want to achieve? How effectively does it do it?**
A functional top-down zombie survival game with progression, upgrades, and two modes. It achieves this well for a solo project — all core systems work. The main limitation is that everything lives in one file, making it harder to extend as it grows.

**How large is the code?**
Approximately 1150 lines in a single file. Manageable now, but will become difficult to navigate if many more features are added.

**Can the code be adapted for other purposes?**
The map generation, entity/projectile system, and shop framework are generic enough to be reused for other top-down games. The upgrade shop pattern in particular is reusable.

**Are there better alternatives easily available?**
pgzero is a beginner-friendly framework but has limitations (no built-in sound management, no scene system, no sprite groups). For a larger project, plain pygame or a framework like Arcade would give more control. For this project's scope, pgzero is fine.

---

## Structural Problems
**How easy is it to add new features?**
Adding new enemies, weapons, or shop upgrades follows a clear pattern and is straightforward. The main friction is that every new enemy type requires touching 8+ places in the code (class definition, list, draw, update, collision, projectile hit, explosion splash, spawn function, level progression, restart cleanup). A base class or component system would reduce this.

**How easy is the code to read?**
Section banners (`# ---`) help a lot. However, `on_mouse_down` and `draw_shop` are long and repetitive — each new shop page adds another block of nearly identical code. `GameState.__init__` has three redundant `self.state =` assignments that should be cleaned up. The variable name `mim_fast_zombies` is a typo of `min_fast_zombies`.

---

## Security Problems
**How could bad actors exploit flaws in the code?**
This is a local single-player game with no networking, no file I/O beyond image loading, and no user-generated input processed as code. There is no meaningful attack surface.

**How could the code be used outside its original purpose?**
It cannot. It is a self-contained game script with no external APIs, no data collection, and no network calls. It is not adaptable for malicious use.

---
