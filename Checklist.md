# CHECKLIST — SCP Containment Breach (Zombie Game)

---

## Features Added

### Game Modes
- **Scaperoom** — Collect keys, reach the door, avoid the Doctor. Keys increase each wave.
- **Survival** — Kill all zombies (including boss) to advance. Double zombie limits, 10% faster zombies, no Doctor.
- **Boss Rush** — Endless boss waves. One new boss spawns every 5 waves. Each boss scales in speed, HP, spawn count, and cooldown every wave until capped at wave 9. No regular zombies, no Doctor, no keys.

### Difficulty
- Four levels: **Easy**, **Normal**, **Hard**, **Nightmare** — affect enemy speed and coin rewards
- Difficulty speed multiplier applies to all enemies including the Doctor, Police Zombie projectiles, and Boss Rush bosses

### Enemy Types
- **Zombie** — 2 HP, 1 damage on hit
- **Fast Zombie** — 1 HP, 1 damage on hit
- **Tank Zombie** — 4 HP, 2 damage on hit
- **Police Zombie** — 3 HP, 1 damage on hit; shoots animated directional projectiles (1 damage); max 5 projectiles active, 5s cooldown; scales with difficulty
- **Boss Zombie** (Survival/Scaperoom) — Spawns every 5 levels; scales +5 HP and +0.15 speed per appearance; max 5 minion spawns, 10s cooldown floor; 100 coins on kill; animated idle/move/die/shoot sprites; 3 damage on contact, 2 damage per projectile; boss health bar at top of screen
- **Boss Rush Boss** — More powerful variant used in Boss Rush mode; starts at 15 HP and scales to 60 HP over 9 waves; speed caps at 1.3×SCALE; max 4 minion spawns, 12s cooldown floor; affected by difficulty

### Weapons
- **Regular shot** `[SPACE]` — 2 damage, 2s cooldown
- **Super shot** `[N]` — 3 damage, piercing, 15s cooldown (20s with Ricochet, halved versions: 7.5s / 10s); deals 5 damage to bosses
- **Shotgun** `[B]` — 3-shot spread (or 6-shot with upgrade), 20s cooldown
- **Bomb** `[V]` — travels in facing direction, large area explosion on impact; unlock via shop
- **Time Burst** `[C]` — slows all enemies (including bosses) to 25% speed for 3 seconds; 30s cooldown; unlock via shop

### Special Abilities
- **Ricochet** (Super Shot upgrade) — Super shots bounce off left/right walls **twice**, returning across the map with piercing still active; increases super shot base cooldown to 20s as a trade-off
- **Time Burst** — Activatable panic button; blue screen tint while active, HUD shows countdown/cooldown
- **Shield** — Absorbs incoming damage before lives; 3 HP max; replenishes 1 HP every 3 waves automatically; shown in HUD

### Projectile Animations
- All player projectiles are 4-frame animated (directional right/left variants)
- Police Zombie projectiles are 4-frame animated (directional)
- Boss projectiles are 30-frame animated (directional)

### Explosion System
- Small explosion: 8 frames — triggered by regular/explosive shots
- Large bomb explosion: 13 frames — triggered by bomb impact; larger blast radius
- Skull, spark, and ring VFX on enemy kills and key pickups

### Shop & Economy (8 pages, opens every 5 waves)
| Page | Upgrade | Cost |
|------|---------|------|
| 0 | Buy life (+1 HP) | 150 coins |
| 0 | Max lives +5 (cap 15) | 800 coins |
| 1 | Halve regular shot cooldown | 600 coins |
| 1 | Halve super shot cooldown | 1000 coins |
| 2 | Halve shotgun cooldown | 800 coins |
| 2 | 6-shot shotgun | 750 coins |
| 3 | Explosive shots | 600 coins |
| 4 | Bomb `[V]` unlock | 1000 coins |
| 5 | Ricochet (super shot bounces x2) | 1200 coins |
| 6 | Time Burst `[C]` unlock | 1000 coins |
| 7 | Shield (3 HP damage buffer) | 1000 coins |

- **Cosmetic shop** `[S while paused]` — buy and toggle zombie skin using Skin Coins
- Coin drops: Zombie 10, Fast Zombie 20, Tank Zombie 30, Police Zombie 25, Boss 100 (all × difficulty coin multiplier)

### Skin Coins
- Separate persistent currency — earned at **half** the rate of regular coins
- Never resets between games or runs — accumulates across all sessions
- Only visible inside the Cosmetic Shop
- Used exclusively for cosmetic purchases (not interchangeable with regular coins)

### Save System (`save_data.py`)
- Saves to `save_data.json` (excluded from repo — each player starts fresh)
- Persists across sessions: **skin_coins**, **skin_unlocked**, **using_skin**, **settings**, **kill_stats**, **high_scores**
- JSON format — portable to web (`localStorage`) or other platforms without structural changes
- Saves automatically on: skin purchase/toggle, settings change, game over, and returning to menu

### Statistics System
- **Kill counts** — tracks zombies, fast zombies, tank zombies, police zombies, and bosses killed (lifetime, never resets)
- **High scores** — best wave reached per mode+difficulty combination (lifetime)
- Accessible via `[K]` while paused; shows kill counts and best-wave table sorted by score

### Pause Menu
- `[P]` — toggle pause
- `[S]` — open Cosmetic Shop
- `[T]` — open Settings
- `[K]` — open Statistics overlay
- `[M]` — return to Main Menu (saves progress first)

### Settings Panel `[T while paused]`
- Toggle individual sound effects (shoot, shotgun, explosion, bomb, player hit, key pickup, level up, buy, game over)
- Toggle visual effects (explosions, bomb explosions, skull, spark, rings)
- Toggle menu music on/off
- Settings persist across sessions via save system

### Music & Sound
- Background music plays on menus and while paused/in shop; stops during active gameplay
- Music toggleable in settings

### Safe Spawn System
- All enemies spawn at least 300px (5 tiles) away from the player
- Spawn loop rerolls until a valid distant tile is found

### Boss Health Bar
- Red bar at top-center of screen, only visible when a live boss is present
- Uses `max_health` for correct ratio on scaled bosses
- Stacks vertically for multiple bosses (Boss Rush); shows "BOSS x2", "BOSS x3" etc.

### HUD
- Lives, money, wave number always visible
- **Shield HP** shown in cyan when shield is purchased (grey when broken)
- Per-weapon cooldown status (READY / countdown in seconds)
- **Time Burst** status shown when unlocked
- Boss health bar(s) at top of screen

### Controls
| Key | Action |
|-----|--------|
| Arrow keys / WASD | Move |
| `SPACE` | Regular shot |
| `N` | Super shot |
| `B` | Shotgun |
| `V` | Bomb (if unlocked) |
| `C` | Time Burst (if unlocked) |
| `P` | Pause / unpause |
| `S` | Open Cosmetic Shop (paused) |
| `T` | Open Settings (paused) |
| `K` | Open Statistics (paused) |
| `M` | Return to Main Menu (paused) |
| `O` / `P` | Previous / next page in shop, settings, stats |
| `X` | Close shop / settings / stats |
| `R` | Restart after game over |

---

## Requirements & Installation

### Python
Requires **Python 3.7+**
Download: https://www.python.org/downloads/

### Install dependencies
```
pip install pygame
```

### Built-in modules (no install needed)
- `random`, `time`, `sys`, `json`, `os`, `copy` — standard library

---

## Project Structure

| File | Purpose |
|------|---------|
| `main.py` | All game logic, rendering, input, entity classes (~2500+ lines) |
| `save_data.py` | Save/load persistent data to `save_data.json` |
| `images/` | All sprite and VFX assets |
| `BossImages/` | Boss sprite sheets (move, idle, die, projectile, hit — right/left variants) |
| `SoundEffects/` | `.ogg` sound effects and `.wav` music |

**Code structure:** Divided into clearly labelled sections. Main sections: constants, map generation, sound system, image loading, Actor class, entity classes, entity lists, spawning, level progression, update loop, collision, drawing, UI, input.

---

## Security

This is a local single-player game with no networking, no user-generated input processed as code, and no external API calls. There is no meaningful attack surface and no adaptable malicious use.
