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
- **Zombie** — 2 HP, 2 damage on hit
- **Fast Zombie** — 1 HP, 1 damage on hit
- **Tank Zombie** — 4 HP, 2 damage on hit
- **Police Zombie** — 3 HP, 1 damage on hit; shoots animated directional projectiles at the player (5 max per cop, 3s cooldown); scales with difficulty
- **Boss Zombie** (Survival/Scaperoom) — Spawns every 5 levels; scales +5 HP and +0.15 speed per appearance; max 5 minion spawns, 10s cooldown; 100 coins on kill; animated idle/move/die/shoot sprites; 3 damage on contact, 2 damage per projectile; boss health bar at top of screen
- **Boss Rush Boss** — More powerful variant used in Boss Rush mode; starts at 15 HP and scales to 60 HP over 9 waves; speed caps at 1.3×SCALE; max 4 minion spawns, 12s cooldown; affected by difficulty

### Weapons
- **Regular shot** `[SPACE]` — 2 damage, 2s cooldown
- **Super shot** `[N]` — 3 damage, piercing, 15s cooldown; deals 5 damage to bosses and removes piercing
- **Shotgun** `[B]` — 3-shot spread (or 6-shot with upgrade), 20s cooldown
- **Bomb** `[V]` — travels in facing direction, large area explosion (13 frames) on impact; unlock via shop

### Projectile Animations
- All player projectiles are 4-frame animated (directional right/left variants)
- Police Zombie projectiles are 4-frame animated (directional)
- Boss projectiles are 30-frame animated (directional)

### Explosion System
- Small explosion: 8 frames — triggered by regular/explosive shots
- Large bomb explosion: 13 frames — triggered by bomb impact; larger blast radius
- Skull, spark, and ring VFX on enemy kills and key pickups

### Shop & Economy
- **Upgrade shop** opens every 5 levels (pauses game)
  - Buy life (+1 HP) — 150 coins
  - Max lives +5 (cap 15) — 800 coins
  - Halve regular shot cooldown — 600 coins
  - Halve super shot cooldown — 1000 coins
  - Halve shotgun cooldown — 800 coins
  - 6-shot shotgun — 750 coins
  - Explosive shots — 600 coins
  - Bomb unlock — 1000 coins
- **Cosmetic shop** `[S while paused]` — buy and toggle zombie skin
- Coin drops: Zombie 10, Fast Zombie 20, Tank Zombie 30, Police Zombie 25, Boss 100 (all multiplied by difficulty coin multiplier)

### Settings Panel `[T while paused]`
- Toggle individual sound effects (shoot, shotgun, explosion, bomb, player hit, key pickup, level up, buy, game over)
- Toggle visual effects (explosions, bomb explosions, skull, spark, rings)
- Toggle menu music on/off

### Music & Sound
- Background music plays on menus and while paused/in shop; stops during active gameplay
- Music toggleable in settings

### Safe Spawn System
- All enemies spawn at least 300px (5 tiles) away from the player
- Spawn loop rerolls until a valid distant tile is found — player is never instantly swarmed

### Boss Health Bar
- Red bar at top-center of screen, only visible when a live boss is present
- Uses `max_health` for correct ratio on scaled bosses
- Stacks vertically for multiple bosses (Boss Rush); shows "BOSS x2", "BOSS x3" etc.

### Controls
- Move: Arrow keys or WASD
- Shoot: `SPACE` (regular), `N` (super), `B` (shotgun), `V` (bomb)
- Pause: `P`
- Cosmetic shop: `S` (while paused)
- Settings: `T` (while paused)
- Shop navigation: `O` (back), `P` (next), `X` (close/continue)
- Restart after game over: `R`

---

## Requirements & Installation

### Python
Requires **Python 3.7+**
Download: https://www.python.org/downloads/

### Install dependencies
```
pip install pygame
pip install pgzero
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

## Project Notes

**Code size:** ~2100+ lines in a single file. All game logic, rendering, input, and entity classes live in `main.py`.

**Structure:** Divided into clearly labelled sections with `# ---` banners. Main sections: constants, map generation, sound system, image loading, Actor class, entity classes, entity lists, spawning, level progression, update loop, collision, drawing, UI, input.

**Image folders:**
- `images/` — all sprite and VFX assets
- `BossImages/` — boss-specific sprite sheets (move, idle, die, projectile, hit — right and left variants)
- `SoundEffects/` — all `.ogg` sound files and `.wav` music

**Extensibility:** Adding a new enemy type requires touching: class definition, entity list, spawn function, draw loop, update loop, collision checks (player + projectile), explosion splash, level progression, and restart cleanup. A base class would reduce this friction.

---

## Security

This is a local single-player game with no networking, no user-generated input processed as code, and no external API calls. There is no meaningful attack surface and no adaptable malicious use.
