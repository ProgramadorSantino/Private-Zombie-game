import random
import time
import sys
import pygame
import save_data

pygame.init()
pygame.mixer.init()

try:
    pygame.mixer.music.load("SoundEffects/PauseMenuMusic.wav")
    pygame.mixer.music.set_volume(0.4)
except Exception:
    pass

# ---------------------------------
# Constants
# ---------------------------------

MAP_W = 26
MAP_H = 17

ZOMBIE_MAX      = 20
FAST_ZOMBIE_MAX = 10
TANK_ZOMBIE_MAX = 7

LEVEL_REWARD = 50
COLOR_TEXT   = "white"

# --- Shop Constants ---
SKIN_COST            = 1000
LEVELS_FOR_SHOP      = 5
REGULAR_HALVED_COST  = 600
SUPER_HALVED_COST    = 1000
SHOP_PAGES           = 8
SKIN_SHOP_PAGES      = 5
SHOTGUN_HALVED_COST  = 800
SHOTGUN_SIX_COST     = 750
EXPLOSIVE_COST       = 600
LIFE_COST            = 150
MAX_LIFE_COST        = 800
BOMB_COST            = 1000
SUPER_RICOCHET_COST  = 1200
TIME_BURST_COST      = 1000
SHIELD_COST          = 1000
TIME_BURST_DURATION  = 3.0   # seconds active
TIME_BURST_COOLDOWN  = 30.0  # seconds between uses

SETTINGS_NUM_PAGES = 6

SETTINGS_PAGES_DATA = [
    ("Weapon Sounds", [
        ("Shoot",   "snd_shoot"),
        ("Shotgun", "snd_shotgun"),
    ]),
    ("Explosion Sounds", [
        ("Explosion", "snd_explosion"),
        ("Bomb",      "snd_bomb"),
    ]),
    ("Event Sounds", [
        ("Player Hit", "snd_player_hit"),
        ("Key Pickup", "snd_key_pickup"),
        ("Level Up",   "snd_level_up"),
        ("Buy",        "snd_buy"),
        ("Game Over",  "snd_game_over"),
    ]),
    ("Visual Effects", [
        ("Explosions",      "vfx_explosion"),
        ("Bomb Explosions", "vfx_bomb_explosion"),
        ("Skull FX",        "vfx_skull"),
        ("Spark FX",        "vfx_spark"),
        ("Rings FX",        "vfx_rings"),
    ]),
    ("Music", [
        ("Menu Music", "music_enabled"),
    ]),
]

settings = {
    "snd_shoot": True, "snd_shotgun": True, "snd_explosion": True,
    "snd_bomb": True, "snd_player_hit": True, "snd_key_pickup": True,
    "snd_level_up": True, "snd_buy": True, "snd_game_over": True,
    "vfx_explosion": True, "vfx_bomb_explosion": True,
    "vfx_skull": True, "vfx_spark": True, "vfx_rings": True,
    "music_enabled": True,
}
settings_open = False
settings_page = 0
stats_open    = False

# ---------------------------------
# Map Generation
# ---------------------------------

def generate_map(w, h):
    mapa = [([0] * w)]
    for _ in range(h - 2):
        mapa.append([0] + [1] * (w - 2) + [0])
    mapa.append([0] * w)
    return mapa

game_map = generate_map(MAP_W, MAP_H)

# ---------------------------------
# Tile / Window sizing
# ---------------------------------

SCALE = 1.2

# Load border once without convert_alpha (display not created yet) just for size
_raw_border = pygame.image.load("images/border.png")
TILE_W = _raw_border.get_width()  * SCALE   # 60.0
TILE_H = _raw_border.get_height() * SCALE   # 60.0
SPAWN_SAFE_RADIUS = 5 * TILE_W              # 300px — min distance from player to spawn tile

WIDTH  = int(MAP_W * TILE_W)           # 1560
HEIGHT = int(len(game_map) * TILE_H)   # 1020

# ---------------------------------
# Display
# ---------------------------------

screen = pygame.display.set_mode((WIDTH, HEIGHT))
pygame.display.set_caption("SCP Containment Breach")
clock = pygame.time.Clock()
FPS   = 60

# ---------------------------------
# Sound system
# ---------------------------------

_sounds = {}

def _load_sounds():
    _vol_map = {
        "snd_player_hit":  0.8,
    }
    for name in ("snd_shoot", "snd_shotgun", "snd_explosion", "snd_bomb",
                 "snd_player_hit", "snd_key_pickup", "snd_level_up",
                 "snd_buy", "snd_game_over"):
        try:
            snd = pygame.mixer.Sound("SoundEffects/" + name + ".ogg")
            snd.set_volume(_vol_map.get(name, 0.6))
            _sounds[name] = snd
        except Exception:
            pass

_load_sounds()

def play_sound(name):
    try:
        if name in _sounds and settings.get(name, True):
            _sounds[name].play()
    except Exception:
        pass

def _trigger_game_over():
    _update_high_score()
    _save_progress()
    game.state = "game_over"
    play_sound("snd_game_over")

def _apply_hit(damage):
    """Apply damage to shield first, then lives. Returns True if game over."""
    if game.shield_hp > 0:
        absorbed       = min(damage, game.shield_hp)
        game.shield_hp -= absorbed
        damage         -= absorbed
    if damage > 0:
        game.lives -= damage
        if game.lives <= 0:
            _trigger_game_over()
            return True
    return False

# ---------------------------------
# Image loading (convert_alpha safe after display creation)
# ---------------------------------

_image_cache = {}

def load_image(name):
    if name not in _image_cache:
        _image_cache[name] = pygame.image.load("images/" + name + ".png").convert_alpha()
    return _image_cache[name]

def load_boss_image(name):
    if name not in _image_cache:
        _image_cache[name] = pygame.image.load("BossImages/" + name + ".png").convert_alpha()
    return _image_cache[name]

# ---------------------------------
# Actor class  (replaces pgzero Actor)
# ---------------------------------

class Actor:
    """
    Stores position as floats (_fx, _fy = center) so sub-pixel movement
    accumulates correctly.  Collision rect is computed on demand from ints.
    """
    def __init__(self, image_name, center=None, topleft=None):
        self._surf        = load_image(image_name)
        self._image_name  = image_name
        w, h              = self._surf.get_size()
        if center is not None:
            self._fx = float(center[0])
            self._fy = float(center[1])
        elif topleft is not None:
            self._fx = float(topleft[0]) + w / 2.0
            self._fy = float(topleft[1]) + h / 2.0
        else:
            self._fx = 0.0
            self._fy = 0.0

    # --- image property ---
    @property
    def image(self):
        return self._image_name

    @image.setter
    def image(self, name):
        self._surf       = load_image(name)
        self._image_name = name
        # center (_fx, _fy) is preserved automatically

    # --- position properties ---
    @property
    def x(self):
        return self._fx

    @x.setter
    def x(self, val):
        self._fx = float(val)

    @property
    def y(self):
        return self._fy

    @y.setter
    def y(self, val):
        self._fy = float(val)

    @property
    def left(self):
        return self._fx - self._surf.get_width() / 2.0

    @left.setter
    def left(self, val):
        self._fx = float(val) + self._surf.get_width() / 2.0

    @property
    def right(self):
        return self._fx + self._surf.get_width() / 2.0

    @right.setter
    def right(self, val):
        self._fx = float(val) - self._surf.get_width() / 2.0

    @property
    def top(self):
        return self._fy - self._surf.get_height() / 2.0

    @top.setter
    def top(self, val):
        self._fy = float(val) + self._surf.get_height() / 2.0

    @property
    def bottom(self):
        return self._fy + self._surf.get_height() / 2.0

    @bottom.setter
    def bottom(self, val):
        self._fy = float(val) - self._surf.get_height() / 2.0

    @property
    def center(self):
        return (self._fx, self._fy)

    @center.setter
    def center(self, val):
        self._fx = float(val[0])
        self._fy = float(val[1])

    @property
    def topleft(self):
        w, h = self._surf.get_size()
        return (self._fx - w / 2.0, self._fy - h / 2.0)

    @topleft.setter
    def topleft(self, val):
        w, h     = self._surf.get_size()
        self._fx = float(val[0]) + w / 2.0
        self._fy = float(val[1]) + h / 2.0

    @property
    def width(self):
        return self._surf.get_width()

    @property
    def height(self):
        return self._surf.get_height()

    # --- collision ---
    def _get_rect(self):
        w, h = self._surf.get_size()
        return pygame.Rect(int(self._fx - w / 2.0),
                           int(self._fy - h / 2.0), w, h)

    def colliderect(self, other):
        r = self._get_rect()
        if isinstance(other, Actor):
            return r.colliderect(other._get_rect())
        return r.colliderect(other)

    def collidepoint(self, x, y=None):
        r = self._get_rect()
        if y is None:
            return r.collidepoint(x)
        return r.collidepoint(x, y)

    def draw(self):
        # pgzero-compatible: render original (unscaled) surface at topleft
        screen.blit(self._surf, (int(self.left), int(self.top)))


# ---------------------------------
# Color helper
# ---------------------------------

def resolve_color(color):
    if isinstance(color, str):
        try:
            c = pygame.Color(color)
            return (c.r, c.g, c.b)
        except ValueError:
            return (255, 255, 255)
    if isinstance(color, (list, tuple)) and len(color) >= 3:
        return tuple(color[:3])
    return color

# ---------------------------------
# Font / text system
# ---------------------------------

_font_cache = {}

def get_font(size):
    if size not in _font_cache:
        _font_cache[size] = pygame.font.SysFont(None, size)
    return _font_cache[size]


def draw_text(text, fontsize=20, color="white", center=None, topleft=None,
              shadow=None, ocolor=None):
    font = get_font(fontsize)
    col  = resolve_color(color)

    def _pos(surf, dx=0, dy=0):
        if center is not None:
            return (int(center[0]) - surf.get_width() // 2 + dx,
                    int(center[1]) - surf.get_height() // 2 + dy)
        return (int(topleft[0]) + dx, int(topleft[1]) + dy)

    if ocolor is not None:
        oc     = resolve_color(ocolor)
        o_surf = font.render(text, True, oc)
        for dx, dy in ((-1,-1),(-1,0),(-1,1),(0,-1),(0,1),(1,-1),(1,0),(1,1)):
            screen.blit(o_surf, _pos(o_surf, dx, dy))

    if shadow is not None:
        sx, sy  = shadow
        sh_surf = font.render(text, True, (0, 0, 0))
        screen.blit(sh_surf, _pos(sh_surf, sx, sy))

    main_surf = font.render(text, True, col)
    screen.blit(main_surf, _pos(main_surf))


# ---------------------------------
# Drawing primitives
# ---------------------------------

def draw_filled_rect(rect, color):
    if isinstance(color, (list, tuple)) and len(color) == 4:
        s = pygame.Surface((rect.width, rect.height), pygame.SRCALPHA)
        s.fill(color)
        screen.blit(s, (rect.left, rect.top))
    else:
        pygame.draw.rect(screen, color, rect)


def draw_rect_outline(rect, color):
    pygame.draw.rect(screen, resolve_color(color), rect, 1)


# ---------------------------------
# Pre-scaled resources
# ---------------------------------

_tile_border_scaled = pygame.transform.scale(load_image("border"),
                                              (int(TILE_W), int(TILE_H)))
_tile_floor_scaled  = pygame.transform.scale(load_image("floor"),
                                              (int(TILE_W), int(TILE_H)))

_explosion_frames = []
for _i in range(1, 9):
    _img    = load_image("explosion" + str(_i))
    _ow, _oh = _img.get_size()
    _explosion_frames.append((
        pygame.transform.scale(_img, (int(_ow * SCALE), int(_oh * SCALE))),
        _ow // 2, _oh // 2
    ))

_bomb_explosion_frames = []
for _i in range(1, 14):
    _img    = load_image("superexplosion" + str(_i))
    _ow, _oh = _img.get_size()
    _bomb_explosion_frames.append((
        pygame.transform.scale(_img, (int(_ow * SCALE), int(_oh * SCALE))),
        _ow // 2, _oh // 2
    ))

def _cache_bullet_frames(base_name):
    frames = []
    for _i in range(1, 5):
        _img = load_image(base_name + str(_i))
        _ow, _oh = _img.get_size()
        frames.append(pygame.transform.scale(_img, (int(_ow * SCALE), int(_oh * SCALE))))
    return frames

_proj_regular_right_frames = _cache_bullet_frames("meteorsmall")
_proj_regular_left_frames  = _cache_bullet_frames("meteorsmallleft")
_proj_super_right_frames   = _cache_bullet_frames("meteor")
_proj_super_left_frames    = _cache_bullet_frames("meteorleft")
_cop_bullet_right_frames   = _cache_bullet_frames("coppbullet")
_cop_bullet_left_frames    = _cache_bullet_frames("coppbulletleft")

_skull_frames = []
for _i in range(1, 30):
    _img     = load_image("skull" + str(_i))
    _ow, _oh = _img.get_size()
    _skull_frames.append((
        pygame.transform.scale(_img, (int(_ow * SCALE), int(_oh * SCALE))),
        _ow // 2, _oh // 2
    ))

_spark_frames = []
for _i in range(1, 14):
    _img     = load_image("spark" + str(_i))
    _ow, _oh = _img.get_size()
    _spark_frames.append((
        pygame.transform.scale(_img, (int(_ow * SCALE), int(_oh * SCALE))),
        _ow // 2, _oh // 2
    ))

_rings_frames = []
for _i in range(1, 16):
    _img     = load_image("rings" + str(_i))
    _ow, _oh = _img.get_size()
    _rings_frames.append((
        pygame.transform.scale(_img, (int(_ow * SCALE), int(_oh * SCALE))),
        _ow // 2, _oh // 2
    ))

def _cache_boss_frames(base_name, count):
    frames = []
    for _i in range(1, count + 1):
        _img    = load_boss_image(base_name + str(_i))
        _ow, _oh = _img.get_size()
        frames.append(pygame.transform.scale(_img, (int(_ow * SCALE), int(_oh * SCALE))))
    return frames

_boss_move_right_frames = _cache_boss_frames("boss_move",     13)
_boss_move_left_frames  = _cache_boss_frames("boss_moveleft", 13)
_boss_idle_right_frames = _cache_boss_frames("boss_idle",     12)
_boss_idle_left_frames  = _cache_boss_frames("boss_idleleft", 12)
_boss_die_right_frames  = _cache_boss_frames("boss_die",      32)
_boss_die_left_frames   = _cache_boss_frames("boss_dieleft",  32)
_boss_proj_right_frames = _cache_boss_frames("boss_proj",     30)
_boss_proj_left_frames  = _cache_boss_frames("boss_projleft", 30)
_boss_hit_frames        = _cache_boss_frames("boss_hit",       6)

# ---------------------------------
# Speed / difficulty constants
# ---------------------------------

PROJECTILE_SPEED        = 8  * SCALE
SUPER_PROJECTILE_SPEED  = 12 * SCALE
ZOMBIE_SPEED_LIMIT      = 0.7  * SCALE
FAST_ZOMBIE_SPEED_LIMIT = 1.4  * SCALE
TANK_ZOMBIE_SPEED_LIMIT = 0.6  * SCALE

DIFFICULTY_SETTINGS = {
    "easy":      {"speed_mult": 0.8,  "coin_mult": 0.75},
    "normal":    {"speed_mult": 1.0,  "coin_mult": 1.0},
    "hard":      {"speed_mult": 1.25, "coin_mult": 2.0},
    "nightmare": {"speed_mult": 1.4,  "coin_mult": 2.5},
}

# ---------------------------------
# Module-level actors and shop rects
# ---------------------------------

zombie_skin_icon = Actor("classdzombie")
life_heart_icon  = Actor("heart")
shield_icon      = Actor("ShieldImage.png")
_bomb_draw_actor = Actor("bombpixelart")   # visual only, never moved

shop_reg_rect            = pygame.Rect(0, 0, 260, 50)
shop_sup_rect            = pygame.Rect(0, 0, 260, 50)
shop_shotgun_halved_rect = pygame.Rect(0, 0, 260, 50)
shop_shotgun_six_rect    = pygame.Rect(0, 0, 260, 50)
shop_explosive_rect      = pygame.Rect(0, 0, 260, 50)
shop_maxlife_rect        = pygame.Rect(0, 0, 260, 50)
shop_bomb_rect           = pygame.Rect(0, 0, 260, 50)
shop_ricochet_rect       = pygame.Rect(0, 0, 260, 50)
shop_time_burst_rect     = pygame.Rect(0, 0, 260, 50)
shop_shield_rect         = pygame.Rect(0, 0, 260, 50)

# ---------------------------------
# Game State
# ---------------------------------

class GameState(object):
    def __init__(self):
        self.score              = 0
        self.money              = 0
        self.lives              = 3
        self.zombie_speed       = 0.3 * SCALE
        self.fast_zombie_speed  = 0.6 * SCALE
        self.min_zombies        = 0
        self.min_fast_zombies   = 0
        self.min_tank_zombies   = 0
        self.tank_zombie_speed   = 0.2 * SCALE
        self.min_police_zombies  = 0
        self.police_zombie_speed = 0.35 * SCALE
        self.police_proj_speed   = 0.8  * SCALE
        self.doctor_speed        = 1.2 * SCALE
        self.super_ready        = True
        self.regular_ready      = True
        self.last_super         = 0
        self.last_regular       = 0
        self.REGULAR_COOLDOWN   = 2.0
        self.SUPER_COOLDOWN     = 15.0
        self.paused             = False
        self.shop_open          = False
        self.skin_unlocked      = False
        self.lives_max          = 10
        self.difficulty         = "normal"
        self.state              = "mode_select"
        self.coin_multiplier    = 1.0
        self.mode               = "scaperoom"
        self.shop_page          = 0
        self.skin_shop_open     = False
        self.skin_shop_page     = 0
        self.regular_halved     = False
        self.super_halved       = False
        self.shotgun_ready      = True
        self.last_shotgun       = 0
        self.SHOTGUN_COOLDOWN   = 20
        self.shotgun_halved     = False
        self.shotgun_six        = False
        self.explosive_shots    = False
        self.bomb_unlocked      = False
        self.bomb_ready         = True
        self.last_bomb          = 0
        self.BOMB_COOLDOWN          = 50.0
        self.boss_level             = 0
        self.super_ricochet         = False
        self.time_burst_unlocked    = False
        self.time_burst_active      = False
        self.time_burst_timer       = 0.0
        self.time_burst_ready       = True
        self.last_time_burst        = 0
        self.shield_unlocked        = False
        self.shield_hp              = 0
        self.shield_max             = 3

game = GameState()

skin_coins  = 0   # persists across game resets; earns at half the rate of money
kill_stats  = {"zombie": 0, "fast": 0, "tank": 0, "police": 0, "boss": 0}
high_scores = {}  # key: "mode_difficulty", value: max wave (score)

def _earn(amount):
    global skin_coins
    game.money  += amount
    skin_coins  += amount // 2

def _kill(enemy_type, coins):
    """Award coins for a kill and increment the persistent kill counter."""
    global kill_stats
    _earn(coins)
    kill_stats[enemy_type] = kill_stats.get(enemy_type, 0) + 1

def _update_high_score():
    """Record the current run's score if it's a new best for this mode+difficulty."""
    key = game.mode + "_" + game.difficulty
    if game.score > high_scores.get(key, 0):
        high_scores[key] = game.score

def _save_progress():
    save_data.save(skin_coins, game.skin_unlocked, using_skin, settings,
                   kill_stats, high_scores)

def _go_to_menu():
    """Save progress and return to the mode-select / main menu screen."""
    global stats_open, settings_open
    _update_high_score()
    _save_progress()
    stats_open    = False
    settings_open = False
    _was_unlocked = game.skin_unlocked
    game.__init__()
    game.skin_unlocked  = _was_unlocked
    zombies[:]          = []
    fast_zombies[:]     = []
    tank_zombies[:]     = []
    police_zombies[:]   = []
    boss_zombies[:]     = []
    projectiles[:]      = []
    boss_projectiles[:] = []
    boss_hit_effects[:] = []
    key_items[:]        = []
    classd.topleft      = (TILE_W, TILE_H * (MAP_H - 3))
    doctor.topleft      = (TILE_W * 4, TILE_H * 3)

# ---------------------------------
# Projectile class
# ---------------------------------

class Projectile(object):
    def __init__(self, x, y, direction, super_shot, vy=0):
        self.direction        = direction
        self.vy               = vy
        self.super_shot       = super_shot
        self.bullet_frame     = 0
        self.bullet_frame_timer = 0.0
        if super_shot:
            self.actor     = Actor("meteor1", center=(x, y))
            self.speed     = SUPER_PROJECTILE_SPEED
            self.damage    = 3
            self.piercing  = True
            self.explosive = False
            self.ricochets = 2 if game.super_ricochet else 0
        else:
            self.actor     = Actor("meteorsmall1", center=(x, y))
            self.speed     = PROJECTILE_SPEED
            self.damage    = 2
            self.piercing  = False
            self.explosive = game.explosive_shots
            self.ricochets = 0
        self.bomb = False

    def move(self):
        if self.direction == "right":
            self.actor.x += self.speed
        else:
            self.actor.x -= self.speed
        self.actor.y += self.vy
        if self.ricochets > 0:
            if self.actor.right >= WIDTH:
                self.actor.right = WIDTH - 1
                self.direction   = "left"
                self.ricochets  -= 1
            elif self.actor.left <= 0:
                self.actor.left = 1
                self.direction  = "right"
                self.ricochets -= 1
        self.bullet_frame_timer += 0.15
        if self.bullet_frame_timer >= 1.0:
            self.bullet_frame_timer -= 1.0
            self.bullet_frame = (self.bullet_frame + 1) % 4

    def draw(self):
        if self.bomb:
            draw_bomb_projectile(self.actor)
        else:
            if self.super_shot:
                frames = _proj_super_right_frames if self.direction == "right" else _proj_super_left_frames
            else:
                frames = _proj_regular_right_frames if self.direction == "right" else _proj_regular_left_frames
            surf = frames[self.bullet_frame]
            cx   = int(self.actor.x)
            cy   = int(self.actor.y)
            screen.blit(surf, (cx - surf.get_width() // 2, cy - surf.get_height() // 2))

    def is_offscreen(self):
        return (self.actor.right < 0 or self.actor.left > WIDTH or
                self.actor.bottom < 0 or self.actor.top > HEIGHT)

# ---------------------------------
# Player
# ---------------------------------

PLAYER_DEFAULT       = "classd"
PLAYER_FLIPPED       = "classdflipped"
PLAYER_ZOMBIE        = "classdzombie"
PLAYER_ZOMBIE_FLIPPED = "classdzombieflipped"

using_skin = False

# --- Restore persistent data from disk (overwrites defaults above) ---
_sd = save_data.load()
skin_coins         = _sd["skin_coins"]
game.skin_unlocked = _sd["skin_unlocked"]
using_skin         = _sd["using_skin"]
settings.update(_sd["settings"])
kill_stats.update(_sd["kill_stats"])
high_scores.update(_sd["high_scores"])
del _sd

classd = Actor(PLAYER_DEFAULT)
classd.topleft = (TILE_W, TILE_H * (MAP_H - 3))

facing = "right"

def update_player_sprite():
    if using_skin:
        classd.image = PLAYER_ZOMBIE if facing == "right" else PLAYER_ZOMBIE_FLIPPED
    else:
        classd.image = PLAYER_DEFAULT if facing == "right" else PLAYER_FLIPPED

update_player_sprite()  # apply loaded skin state immediately

# ---------------------------------
# Door and Doctor
# ---------------------------------

door   = Actor("door",          topleft=(TILE_W * 12, TILE_H))
doctor = Actor("plague_doctor", topleft=(TILE_W * 4,  TILE_H * 3))
DOCTOR_SPEED = 1.2 * SCALE

# ---------------------------------
# Entity classes
# ---------------------------------

class Zombie(object):
    def __init__(self, x, y, speed):
        self.actor  = Actor("zombie", topleft=(x, y))
        self.health = 2
        self.speed  = speed

    def move(self, target):
        if self.actor.x < target.x:
            self.actor.x    += self.speed
            self.actor.image = "zombie"
        elif self.actor.x > target.x:
            self.actor.x    -= self.speed
            self.actor.image = "zombieflipped"
        if self.actor.y < target.y:
            self.actor.y += self.speed
        elif self.actor.y > target.y:
            self.actor.y -= self.speed

    def draw(self):
        draw_scaled(self.actor)


class FastZombie(object):
    def __init__(self, x, y, speed):
        self.actor  = Actor("zombiefast", topleft=(x, y))
        self.health = 1
        self.speed  = speed

    def move(self, target):
        if self.actor.x < target.x:
            self.actor.x    += self.speed
            self.actor.image = "zombiefast"
        elif self.actor.x > target.x:
            self.actor.x    -= self.speed
            self.actor.image = "zombiefastflipped"
        if self.actor.y < target.y:
            self.actor.y += self.speed
        elif self.actor.y > target.y:
            self.actor.y -= self.speed

    def draw(self):
        draw_scaled(self.actor)


class TankZombie(object):
    def __init__(self, x, y, speed):
        self.actor  = Actor("zombiebrute", topleft=(x, y))
        self.health = 4
        self.speed  = speed

    def move(self, target):
        if self.actor.x < target.x:
            self.actor.x    += self.speed
            self.actor.image = "zombiebrute"
        elif self.actor.x > target.x:
            self.actor.x    -= self.speed
            self.actor.image = "zombiebruteflipped"
        if self.actor.y < target.y:
            self.actor.y += self.speed
        elif self.actor.y > target.y:
            self.actor.y -= self.speed

    def draw(self):
        draw_scaled(self.actor)


class PoliceZombieProjectile(object):
    def __init__(self, x, y, dx, dy, speed):
        self.actor            = Actor("coppbullet1", center=(x, y))
        self.dx               = dx
        self.dy               = dy
        self.speed            = speed
        self.facing           = "right" if dx >= 0 else "left"
        self.bullet_frame     = 0
        self.bullet_frame_timer = 0.0

    def move(self):
        self.actor.x += self.dx * self.speed
        self.actor.y += self.dy * self.speed
        self.bullet_frame_timer += 0.15
        if self.bullet_frame_timer >= 1.0:
            self.bullet_frame_timer -= 1.0
            self.bullet_frame = (self.bullet_frame + 1) % 4

    def draw(self):
        frames = _cop_bullet_right_frames if self.facing == "right" else _cop_bullet_left_frames
        surf   = frames[self.bullet_frame]
        cx     = int(self.actor.x)
        cy     = int(self.actor.y)
        screen.blit(surf, (cx - surf.get_width() // 2, cy - surf.get_height() // 2))

    def is_offscreen(self):
        return (self.actor.right < 0 or self.actor.left > WIDTH or
                self.actor.bottom < 0 or self.actor.top > HEIGHT)


class BossProjectile(object):
    def __init__(self, x, y, dx, dy):
        self.x          = float(x)
        self.y          = float(y)
        self.dx         = dx
        self.dy         = dy
        self.speed      = 4 * SCALE
        self.facing     = "right" if dx >= 0 else "left"
        self.proj_frame = 0
        self.proj_timer = 0.0

    def move(self, dt):
        self.x += self.dx * self.speed
        self.y += self.dy * self.speed
        self.proj_timer += dt
        if self.proj_timer >= 0.04:
            self.proj_timer -= 0.04
            self.proj_frame = (self.proj_frame + 1) % 30

    def draw(self):
        frames = _boss_proj_right_frames if self.facing == "right" else _boss_proj_left_frames
        surf   = frames[self.proj_frame]
        screen.blit(surf, (int(self.x) - surf.get_width() // 2, int(self.y) - surf.get_height() // 2))

    def is_offscreen(self):
        return (self.x < 0 or self.x > WIDTH or self.y < 0 or self.y > HEIGHT)

    def _get_rect(self):
        frames = _boss_proj_right_frames if self.facing == "right" else _boss_proj_left_frames
        surf   = frames[self.proj_frame]
        w, h   = surf.get_size()
        return pygame.Rect(int(self.x) - w // 2, int(self.y) - h // 2, w, h)

    def colliderect(self, other):
        r = self._get_rect()
        if isinstance(other, Actor):
            return r.colliderect(other._get_rect())
        return r.colliderect(other)


class PoliceZombie(object):
    SHOOT_COOLDOWN = 5.0

    def __init__(self, x, y, speed, proj_speed):
        self.actor       = Actor("policezombie", topleft=(x, y))
        self.health      = 3
        self.speed       = speed
        self.proj_speed  = proj_speed
        self.projectiles = []
        self.last_shot   = 0

    def move(self, target):
        if self.actor.x < target.x:
            self.actor.x    += self.speed
            self.actor.image = "policezombie"
        elif self.actor.x > target.x:
            self.actor.x    -= self.speed
            self.actor.image = "policezombieflipped"
        if self.actor.y < target.y:
            self.actor.y += self.speed
        elif self.actor.y > target.y:
            self.actor.y -= self.speed

    def try_shoot(self, target):
        now = time.time()
        if len(self.projectiles) < 5 and now - self.last_shot >= self.SHOOT_COOLDOWN:
            dx   = target.x - self.actor.x
            dy   = target.y - self.actor.y
            dist = (dx ** 2 + dy ** 2) ** 0.5
            if dist > 0:
                dx /= dist
                dy /= dist
            self.projectiles.append(
                PoliceZombieProjectile(self.actor.x, self.actor.y, dx, dy, self.proj_speed))
            self.last_shot = now

    def update_projectiles(self):
        for p in self.projectiles[:]:
            p.move()
            if p.is_offscreen():
                self.projectiles.remove(p)

    def draw(self):
        draw_scaled(self.actor)
        for p in self.projectiles:
            p.draw()


class BossZombie(object):
    SHOOT_COOLDOWN = 4.0
    SPAWN_COOLDOWN = 15.0

    def __init__(self, x, y, speed=None, health=None, spawn_count=2, spawn_cooldown=20.0):
        _w = _boss_idle_right_frames[0].get_width()
        _h = _boss_idle_right_frames[0].get_height()
        self.x             = float(x) + _w // 2
        self.y             = float(y) + _h // 2
        self.health        = health if health is not None else 10
        self.max_health    = self.health
        self.speed         = speed  if speed  is not None else 0.9 * SCALE
        self.facing        = "right"
        self.anim_name     = "idle"
        self.anim_frame    = 0
        self.anim_timer    = 0.0
        self.dying         = False
        self.die_frame     = 0
        self.die_timer     = 0.0
        self.shoot_timer   = 0.0
        self.spawn_timer   = 0.0
        self.spawn_count   = spawn_count
        self.spawn_cooldown = spawn_cooldown

    def _get_rect(self):
        if self.dying:
            frames = _boss_die_right_frames if self.facing == "right" else _boss_die_left_frames
            idx    = min(self.die_frame, len(frames) - 1)
        elif self.anim_name == "move":
            frames = _boss_move_right_frames if self.facing == "right" else _boss_move_left_frames
            idx    = self.anim_frame
        else:
            frames = _boss_idle_right_frames if self.facing == "right" else _boss_idle_left_frames
            idx    = self.anim_frame
        surf = frames[idx]
        w, h = surf.get_size()
        return pygame.Rect(int(self.x) - w // 2, int(self.y) - h // 2, w, h)

    def colliderect(self, other):
        r = self._get_rect()
        if isinstance(other, Actor):
            return r.colliderect(other._get_rect())
        return r.colliderect(other)

    def move(self, target):
        if self.dying:
            return
        if target.x > self.x:
            self.x     += self.speed
            self.facing = "right"
        elif target.x < self.x:
            self.x     -= self.speed
            self.facing = "left"
        if target.y > self.y:
            self.y += self.speed
        elif target.y < self.y:
            self.y -= self.speed
        self.anim_name = "move"

    def update(self, dt):
        if self.dying:
            self.die_timer += dt
            if self.die_timer >= 0.06:
                self.die_timer -= 0.06
                self.die_frame += 1
            return

        frame_count      = 13 if self.anim_name == "move" else 12
        self.anim_timer += dt
        if self.anim_timer >= 0.07:
            self.anim_timer -= 0.07
            self.anim_frame  = (self.anim_frame + 1) % frame_count

        self.shoot_timer += dt
        if self.shoot_timer >= self.SHOOT_COOLDOWN:
            self.shoot_timer = 0.0
            self.anim_name   = "idle"
            self.anim_frame  = 0
            dx   = classd.x - self.x
            dy   = classd.y - self.y
            dist = (dx ** 2 + dy ** 2) ** 0.5
            if dist > 0:
                dx /= dist
                dy /= dist
            boss_projectiles.append(BossProjectile(self.x, self.y, dx, dy))

        self.spawn_timer += dt
        if self.spawn_timer >= self.spawn_cooldown:
            self.spawn_timer = 0.0
            for _ in range(self.spawn_count):
                while True:
                    tx = random.randint(1, MAP_W - 2)
                    ty = random.randint(1, MAP_H - 4)
                    if _safe_spawn_tile(tx, ty):
                        ztype = random.choice(["zombie", "fast", "tank"])
                        if ztype == "zombie":
                            zombies.append(Zombie(tx * TILE_W, ty * TILE_H, game.zombie_speed))
                        elif ztype == "fast":
                            fast_zombies.append(FastZombie(tx * TILE_W, ty * TILE_H, game.fast_zombie_speed))
                        else:
                            tank_zombies.append(TankZombie(tx * TILE_W, ty * TILE_H, game.tank_zombie_speed))
                        break

    def draw(self):
        if self.dying:
            frames = _boss_die_right_frames if self.facing == "right" else _boss_die_left_frames
            idx    = min(self.die_frame, len(frames) - 1)
        elif self.anim_name == "move":
            frames = _boss_move_right_frames if self.facing == "right" else _boss_move_left_frames
            idx    = self.anim_frame
        else:
            frames = _boss_idle_right_frames if self.facing == "right" else _boss_idle_left_frames
            idx    = self.anim_frame
        surf = frames[idx]
        screen.blit(surf, (int(self.x) - surf.get_width() // 2, int(self.y) - surf.get_height() // 2))

# ---------------------------------
# Entity lists
# ---------------------------------

zombies        = []
fast_zombies   = []
tank_zombies   = []
police_zombies = []
boss_zombies   = []
projectiles    = []
boss_projectiles = []
key_items      = []
explosions      = []      # [x, y, frame_index, timer]
bomb_explosions = []      # [x, y, frame_index, timer]
skull_effects   = []      # [x, y, frame_index, timer]
spark_effects   = []      # [x, y, frame_index, timer]
rings_effects   = []      # [x, y, frame_index, timer]
boss_hit_effects = []     # [x, y, frame_index, timer]

# ---------------------------------
# VFX spawn helpers (respect settings)
# ---------------------------------

def spawn_skull(x, y):
    if settings["vfx_skull"]:
        skull_effects.append([x, y, 0, 0.0])

def spawn_spark(x, y):
    if settings["vfx_spark"]:
        spark_effects.append([x, y, 0, 0.0])

def spawn_rings(x, y):
    if settings["vfx_rings"]:
        rings_effects.append([x, y, 0, 0.0])

# ---------------------------------
# Utility: spawn a key
# ---------------------------------

def spawn_key():
    while True:
        x = random.randint(1, MAP_W - 2)
        y = random.randint(1, MAP_H - 4)
        if game_map[y][x] == 1:
            return Actor("key", topleft=(x * TILE_W, y * TILE_H))

key_items.append(spawn_key())

# ---------------------------------
# Drawing helpers
# ---------------------------------

def draw_scaled(actor):
    orig_w = actor._surf.get_width()
    orig_h = actor._surf.get_height()
    surf   = pygame.transform.scale(actor._surf,
                                    (int(orig_w * SCALE), int(orig_h * SCALE)))
    screen.blit(surf, (int(actor.left), int(actor.top)))


_BOMB_PROJ_W = int(15 * SCALE * 3)
_BOMB_PROJ_H = int(13 * SCALE * 3)

def draw_bomb_projectile(actor):
    surf = pygame.transform.scale(_bomb_draw_actor._surf, (_BOMB_PROJ_W, _BOMB_PROJ_H))
    cx   = int(actor.x)
    cy   = int(actor.y)
    screen.blit(surf, (cx - _BOMB_PROJ_W // 2, cy - _BOMB_PROJ_H // 2))


def draw_map():
    for y in range(len(game_map)):
        for x in range(len(game_map[0])):
            tile = game_map[y][x]
            pos  = (x * int(TILE_W), y * int(TILE_H))
            if tile == 0:
                screen.blit(_tile_border_scaled, pos)
            elif tile == 1:
                screen.blit(_tile_floor_scaled, pos)

# ---------------------------------
# Shop drawing
# ---------------------------------

def draw_shop():
    rect = pygame.Rect(WIDTH // 2 - 190, HEIGHT // 2 - 165, 380, 340)
    draw_filled_rect(rect, (0, 0, 0, 200))
    draw_rect_outline(rect, COLOR_TEXT)

    draw_text("SCP Vending Terminal",
              center=(WIDTH // 2, HEIGHT // 2 - 133),
              fontsize=35, color="yellow", shadow=(1, 1))
    draw_text("Page " + str(game.shop_page + 1) + "/" + str(SHOP_PAGES),
              center=(WIDTH // 2, HEIGHT // 2 - 150),
              fontsize=16, color="grey")
    draw_text("[O] Back   [P] Next",
              center=(WIDTH // 2, HEIGHT // 2 + 120),
              fontsize=18, color="grey")
    draw_text("Press X to Continue",
              center=(WIDTH // 2, HEIGHT // 2 + 143),
              fontsize=22, color="white", ocolor="black")
    draw_text("Coins: " + str(game.money),
              center=(WIDTH // 2, HEIGHT // 2 - 103),
              fontsize=30, color="yellow", shadow=(1, 1))

    # ---- PAGE 0: Lives ----
    if game.shop_page == 0:
        life_heart_icon.center = (WIDTH // 2, HEIGHT // 2 - 20)
        draw_scaled(life_heart_icon)

        color_l = "green" if game.money >= LIFE_COST and game.lives < game.lives_max else "red"
        draw_text("Buy Life  -" + str(LIFE_COST) + " coins",
                  center=(WIDTH // 2, HEIGHT // 2 + 20), fontsize=22, color=color_l)
        draw_text("(Click heart to buy)",
                  center=(WIDTH // 2, HEIGHT // 2 + 40), fontsize=18, color="white")

        shop_maxlife_rect.topleft = (WIDTH // 2 - 130, HEIGHT // 2 + 65)
        shop_maxlife_rect.size    = (260, 50)
        if game.lives_max >= 15:
            draw_filled_rect(shop_maxlife_rect, (0, 80, 80))
            draw_rect_outline(shop_maxlife_rect, "cyan")
            draw_text("Max Lives +5 (owned)",
                      center=shop_maxlife_rect.center, fontsize=20, color="cyan")
        else:
            col = (0, 50, 50) if game.money >= MAX_LIFE_COST else (60, 0, 0)
            draw_filled_rect(shop_maxlife_rect, col)
            draw_rect_outline(shop_maxlife_rect, "white")
            color_ml = "cyan" if game.money >= MAX_LIFE_COST else "red"
            draw_text("Max Lives +5  -" + str(MAX_LIFE_COST) + " coins",
                      center=shop_maxlife_rect.center, fontsize=20, color=color_ml)

    # ---- PAGE 1: Cooldown upgrades ----
    elif game.shop_page == 1:
        shop_reg_rect.topleft = (WIDTH // 2 - 130, HEIGHT // 2 - 80)
        shop_reg_rect.size    = (260, 50)
        if game.regular_halved:
            draw_filled_rect(shop_reg_rect, (0, 80, 0))
            draw_rect_outline(shop_reg_rect, "green")
            draw_text("Shot CD: HALVED (owned)",
                      center=shop_reg_rect.center, fontsize=20, color="green")
        else:
            col = (0, 60, 0) if game.money >= REGULAR_HALVED_COST else (60, 0, 0)
            draw_filled_rect(shop_reg_rect, col)
            draw_rect_outline(shop_reg_rect, "white")
            color_r = "green" if game.money >= REGULAR_HALVED_COST else "red"
            draw_text("Halve Shot CD  -" + str(REGULAR_HALVED_COST) + " coins",
                      center=shop_reg_rect.center, fontsize=20, color=color_r)

        shop_sup_rect.topleft = (WIDTH // 2 - 130, HEIGHT // 2 - 15)
        shop_sup_rect.size    = (260, 50)
        if game.super_halved:
            draw_filled_rect(shop_sup_rect, (0, 80, 80))
            draw_rect_outline(shop_sup_rect, "cyan")
            draw_text("Super CD: HALVED (owned)",
                      center=shop_sup_rect.center, fontsize=20, color="cyan")
        else:
            col = (0, 40, 60) if game.money >= SUPER_HALVED_COST else (60, 0, 0)
            draw_filled_rect(shop_sup_rect, col)
            draw_rect_outline(shop_sup_rect, "white")
            color_s = "cyan" if game.money >= SUPER_HALVED_COST else "red"
            draw_text("Halve Super CD  -" + str(SUPER_HALVED_COST) + " coins",
                      center=shop_sup_rect.center, fontsize=20, color=color_s)

    # ---- PAGE 2: Shotgun upgrades ----
    elif game.shop_page == 2:
        shop_shotgun_halved_rect.topleft = (WIDTH // 2 - 130, HEIGHT // 2 - 50)
        shop_shotgun_halved_rect.size    = (260, 50)
        if game.shotgun_halved:
            draw_filled_rect(shop_shotgun_halved_rect, (0, 80, 40))
            draw_rect_outline(shop_shotgun_halved_rect, "orange")
            draw_text("Shotgun CD: HALVED (owned)",
                      center=shop_shotgun_halved_rect.center, fontsize=20, color="orange")
        else:
            col = (0, 50, 20) if game.money >= SHOTGUN_HALVED_COST else (60, 0, 0)
            draw_filled_rect(shop_shotgun_halved_rect, col)
            draw_rect_outline(shop_shotgun_halved_rect, "white")
            color_sh = "orange" if game.money >= SHOTGUN_HALVED_COST else "red"
            draw_text("Halve Shotgun CD  -" + str(SHOTGUN_HALVED_COST) + " coins",
                      center=shop_shotgun_halved_rect.center, fontsize=20, color=color_sh)

        shop_shotgun_six_rect.topleft = (WIDTH // 2 - 130, HEIGHT // 2 + 20)
        shop_shotgun_six_rect.size    = (260, 50)
        if game.shotgun_six:
            draw_filled_rect(shop_shotgun_six_rect, (80, 60, 0))
            draw_rect_outline(shop_shotgun_six_rect, "yellow")
            draw_text("6-Shot Shotgun (owned)",
                      center=shop_shotgun_six_rect.center, fontsize=20, color="yellow")
        else:
            col = (50, 40, 0) if game.money >= SHOTGUN_SIX_COST else (60, 0, 0)
            draw_filled_rect(shop_shotgun_six_rect, col)
            draw_rect_outline(shop_shotgun_six_rect, "white")
            color_s6 = "yellow" if game.money >= SHOTGUN_SIX_COST else "red"
            draw_text("6-Shot Shotgun  -" + str(SHOTGUN_SIX_COST) + " coins",
                      center=shop_shotgun_six_rect.center, fontsize=20, color=color_s6)

    # ---- PAGE 3: Explosive shots ----
    elif game.shop_page == 3:
        shop_explosive_rect.topleft = (WIDTH // 2 - 130, HEIGHT // 2 - 15)
        shop_explosive_rect.size    = (260, 50)
        if game.explosive_shots:
            draw_filled_rect(shop_explosive_rect, (80, 40, 0))
            draw_rect_outline(shop_explosive_rect, "orange")
            draw_text("Explosive Shots (owned)",
                      center=shop_explosive_rect.center, fontsize=20, color="orange")
        else:
            col = (50, 25, 0) if game.money >= EXPLOSIVE_COST else (60, 0, 0)
            draw_filled_rect(shop_explosive_rect, col)
            draw_rect_outline(shop_explosive_rect, "white")
            color_ex = "orange" if game.money >= EXPLOSIVE_COST else "red"
            draw_text("Explosive Shots  -" + str(EXPLOSIVE_COST) + " coins",
                      center=shop_explosive_rect.center, fontsize=20, color=color_ex)

    # ---- PAGE 4: Bomb ----
    elif game.shop_page == 4:
        shop_bomb_rect.topleft = (WIDTH // 2 - 130, HEIGHT // 2 - 15)
        shop_bomb_rect.size    = (260, 50)
        if game.bomb_unlocked:
            draw_filled_rect(shop_bomb_rect, (80, 0, 0))
            draw_rect_outline(shop_bomb_rect, "red")
            draw_text("Bomb [V] (owned)",
                      center=shop_bomb_rect.center, fontsize=20, color="red")
        else:
            col = (50, 0, 0) if game.money >= BOMB_COST else (60, 0, 0)
            draw_filled_rect(shop_bomb_rect, col)
            draw_rect_outline(shop_bomb_rect, "white")
            color_b = "red" if game.money >= BOMB_COST else (120, 120, 120)
            draw_text("Bomb [V]  -" + str(BOMB_COST) + " coins",
                      center=shop_bomb_rect.center, fontsize=20, color=color_b)

    # ---- PAGE 5: Ricochet (Super Shot upgrade) ----
    elif game.shop_page == 5:
        draw_text("Super Shot Upgrade",
                  center=(WIDTH // 2, HEIGHT // 2 - 65),
                  fontsize=22, color="cyan")
        draw_text("Shot bounces off walls once,",
                  center=(WIDTH // 2, HEIGHT // 2 - 42),
                  fontsize=17, color="grey")
        draw_text("still piercing on return trip.",
                  center=(WIDTH // 2, HEIGHT // 2 - 24),
                  fontsize=17, color="grey")
        shop_ricochet_rect.topleft = (WIDTH // 2 - 130, HEIGHT // 2 + 5)
        shop_ricochet_rect.size    = (260, 50)
        if game.super_ricochet:
            draw_filled_rect(shop_ricochet_rect, (0, 60, 80))
            draw_rect_outline(shop_ricochet_rect, "cyan")
            draw_text("Ricochet [N] (owned)",
                      center=shop_ricochet_rect.center, fontsize=20, color="cyan")
        else:
            col = (0, 40, 60) if game.money >= SUPER_RICOCHET_COST else (60, 0, 0)
            draw_filled_rect(shop_ricochet_rect, col)
            draw_rect_outline(shop_ricochet_rect, "white")
            color_rc = "cyan" if game.money >= SUPER_RICOCHET_COST else "red"
            draw_text("Ricochet  -" + str(SUPER_RICOCHET_COST) + " coins",
                      center=shop_ricochet_rect.center, fontsize=20, color=color_rc)

    # ---- PAGE 6: Time Burst ----
    elif game.shop_page == 6:
        draw_text("New Ability: Time Burst [C]",
                  center=(WIDTH // 2, HEIGHT // 2 - 65),
                  fontsize=22, color=(100, 200, 255))
        draw_text("Slows all enemies to 25% speed",
                  center=(WIDTH // 2, HEIGHT // 2 - 42),
                  fontsize=17, color="grey")
        draw_text("for 3 seconds.  30s cooldown.",
                  center=(WIDTH // 2, HEIGHT // 2 - 24),
                  fontsize=17, color="grey")
        shop_time_burst_rect.topleft = (WIDTH // 2 - 130, HEIGHT // 2 + 5)
        shop_time_burst_rect.size    = (260, 50)
        if game.time_burst_unlocked:
            draw_filled_rect(shop_time_burst_rect, (0, 40, 80))
            draw_rect_outline(shop_time_burst_rect, (100, 200, 255))
            draw_text("Time Burst [C] (owned)",
                      center=shop_time_burst_rect.center, fontsize=20, color=(100, 200, 255))
        else:
            col = (0, 25, 60) if game.money >= TIME_BURST_COST else (60, 0, 0)
            draw_filled_rect(shop_time_burst_rect, col)
            draw_rect_outline(shop_time_burst_rect, "white")
            color_tb = (100, 200, 255) if game.money >= TIME_BURST_COST else "red"
            draw_text("Time Burst  -" + str(TIME_BURST_COST) + " coins",
                      center=shop_time_burst_rect.center, fontsize=20, color=color_tb)

    # ---- PAGE 7: Shield ----
    elif game.shop_page == 7:
        shield_icon.center = (WIDTH // 2, HEIGHT // 2 - 20)
        draw_scaled(shield_icon)

        if game.shield_unlocked:
            draw_text("Shield (owned)  " + str(game.shield_hp) + "/" + str(game.shield_max) + " HP",
                      center=(WIDTH // 2, HEIGHT // 2 + 30),
                      fontsize=22, color="cyan")
            draw_text("Replenishes 1 HP every 3 waves",
                      center=(WIDTH // 2, HEIGHT // 2 + 52),
                      fontsize=17, color="grey")
        else:
            color_sh = "cyan" if game.money >= SHIELD_COST else "red"
            draw_text("Shield  -" + str(SHIELD_COST) + " coins",
                      center=(WIDTH // 2, HEIGHT // 2 + 30),
                      fontsize=22, color=color_sh)
            draw_text("Absorbs 3 damage  |  +1 HP every 3 waves",
                      center=(WIDTH // 2, HEIGHT // 2 + 52),
                      fontsize=17, color="grey")
            draw_text("(Click to buy)",
                      center=(WIDTH // 2, HEIGHT // 2 + 72),
                      fontsize=18, color="white")


# ---------------------------------
# Cosmetic shop drawing
# ---------------------------------

def draw_skin_shop():
    rect = pygame.Rect(WIDTH // 2 - 180, HEIGHT // 2 - 140, 360, 280)
    draw_filled_rect(rect, (0, 0, 0, 200))
    draw_rect_outline(rect, "purple")

    draw_text("Cosmetic Shop",
              center=(WIDTH // 2, HEIGHT // 2 - 110),
              fontsize=35, color="purple", shadow=(1, 1))
    draw_text("Page " + str(game.skin_shop_page + 1) + "/" + str(SKIN_SHOP_PAGES),
              center=(WIDTH // 2, HEIGHT // 2 - 125),
              fontsize=16, color="grey")
    draw_text("[O] Back   [P] Next",
              center=(WIDTH // 2, HEIGHT // 2 + 90),
              fontsize=18, color="grey")
    draw_text("Press X to Close",
              center=(WIDTH // 2, HEIGHT // 2 + 110),
              fontsize=22, color="white", ocolor="black")
    draw_text("Skin Coins: " + str(skin_coins),
              center=(WIDTH // 2, HEIGHT // 2 - 80),
              fontsize=30, color="yellow", shadow=(1, 1))

    if game.skin_shop_page == 0:
        zombie_skin_icon.center = (WIDTH // 2, HEIGHT // 2 - 20)
        draw_scaled(zombie_skin_icon)

        if game.skin_unlocked:
            status = "Active" if using_skin else "Inactive"
            draw_text("Zombie Skin [" + status + "]",
                      center=(WIDTH // 2, HEIGHT // 2 + 30),
                      fontsize=22, color="green")
            draw_text("(Click to toggle)",
                      center=(WIDTH // 2, HEIGHT // 2 + 52),
                      fontsize=18, color="white")
        else:
            color_s = "green" if skin_coins >= SKIN_COST else "red"
            draw_text("Zombie Skin  -" + str(SKIN_COST) + " skin coins",
                      center=(WIDTH // 2, HEIGHT // 2 + 30),
                      fontsize=22, color=color_s)
            draw_text("(Click to buy)",
                      center=(WIDTH // 2, HEIGHT // 2 + 52),
                      fontsize=18, color="white")
    else:
        draw_text("[ Coming Soon ]",
                  center=(WIDTH // 2, HEIGHT // 2),
                  fontsize=30, color="grey")


# ---------------------------------
# Screen drawing
# ---------------------------------

def draw_mode_select():
    screen.fill((10, 10, 10))
    draw_text("SCP CONTAINMENT BREACH",
              center=(WIDTH // 2, HEIGHT // 4),
              fontsize=54, color="red", shadow=(2, 2))
    draw_text("Select Mode:",
              center=(WIDTH // 2, HEIGHT // 2 - 60),
              fontsize=42, color="white")
    draw_text("[S] SCAPEROOM -- Collect keys, reach the door, survive the Doctor",
              center=(WIDTH // 2, HEIGHT // 2 - 20), fontsize=30, color="cyan")
    draw_text("[V] SURVIVAL -- Kill all zombies to advance, no Doctor,",
              center=(WIDTH // 2, HEIGHT // 2 + 15), fontsize=30, color="orange")
    draw_text("               double zombie limits, 10% faster zombies",
              center=(WIDTH // 2, HEIGHT // 2 + 40), fontsize=30, color="orange")
    draw_text("[B] BOSS RUSH -- Survive endless boss waves, one new boss",
              center=(WIDTH // 2, HEIGHT // 2 + 80), fontsize=30, color="red")
    draw_text("               every 10 waves, each boss scales each wave",
              center=(WIDTH // 2, HEIGHT // 2 + 105), fontsize=30, color="red")


def draw_menu():
    screen.fill((10, 10, 10))
    draw_text("SCP CONTAINMENT BREACH",
              center=(WIDTH // 2, HEIGHT // 4),
              fontsize=54, color="red", shadow=(2, 2))
    draw_text("Select Difficulty:",
              center=(WIDTH // 2, HEIGHT // 2 - 60),
              fontsize=42, color="white")
    draw_text("[E] EASY   - Slower enemies, Less coins",
              center=(WIDTH // 2, HEIGHT // 2), fontsize=30, color="cyan")
    draw_text("[N] NORMAL - Standard values",
              center=(WIDTH // 2, HEIGHT // 2 + 35), fontsize=30, color="green")
    draw_text("[H] HARD   - Faster enemies, double coins",
              center=(WIDTH // 2, HEIGHT // 2 + 70), fontsize=30, color="red")
    draw_text("[M] NIGHTMARE - 1.4x speed, double spawns, 2.5x coins",
              center=(WIDTH // 2, HEIGHT // 2 + 105), fontsize=30, color="purple")


def draw():
    if game.state == "mode_select":
        draw_mode_select()
        return

    if game.state == "menu":
        draw_menu()
        return

    screen.fill((30, 30, 30))
    draw_map()
    if game.mode == "scaperoom":
        draw_scaled(door)
    draw_scaled(classd)

    if game.mode == "scaperoom":
        draw_scaled(doctor)

    for k in key_items:
        k.draw()

    for z in zombies:
        z.draw()
    for z in fast_zombies:
        z.draw()
    for z in tank_zombies:
        z.draw()
    for z in police_zombies:
        z.draw()
    for boss in boss_zombies:
        boss.draw()
    for bp in boss_projectiles:
        bp.draw()
    for p in projectiles:
        p.draw()

    for e in explosions:
        frame, ox, oy = _explosion_frames[e[2]]
        screen.blit(frame, (int(e[0]) - ox, int(e[1]) - oy))

    for e in bomb_explosions:
        frame, ox, oy = _bomb_explosion_frames[e[2]]
        screen.blit(frame, (int(e[0]) - ox, int(e[1]) - oy))

    for e in skull_effects:
        frame, ox, oy = _skull_frames[e[2]]
        screen.blit(frame, (int(e[0]) - ox, int(e[1]) - oy))

    for e in spark_effects:
        frame, ox, oy = _spark_frames[e[2]]
        screen.blit(frame, (int(e[0]) - ox, int(e[1]) - oy))

    for e in rings_effects:
        frame, ox, oy = _rings_frames[e[2]]
        screen.blit(frame, (int(e[0]) - ox, int(e[1]) - oy))

    for e in boss_hit_effects:
        surf = _boss_hit_frames[e[2]]
        screen.blit(surf, (int(e[0]) - surf.get_width() // 2, int(e[1]) - surf.get_height() // 2))

    if game.time_burst_active:
        draw_filled_rect(pygame.Rect(0, 0, WIDTH, HEIGHT), (0, 60, 180, 40))

    if game.skin_shop_open:
        draw_skin_shop()
        return

    if game.shop_open:
        draw_shop()
        return

    if game.paused:
        draw_text("PAUSE", center=(WIDTH // 2, HEIGHT // 2),
                  fontsize=100, color="blue", shadow=(2, 2))
        draw_text("[S] Cosmetic Shop",
                  center=(WIDTH // 2, HEIGHT // 2 + 70),
                  fontsize=24, color="purple")
        draw_text("[T] Settings",
                  center=(WIDTH // 2, HEIGHT // 2 + 100),
                  fontsize=24, color="cyan")
        draw_text("[K] Statistics",
                  center=(WIDTH // 2, HEIGHT // 2 + 130),
                  fontsize=24, color="yellow")
        draw_text("[M] Main Menu",
                  center=(WIDTH // 2, HEIGHT // 2 + 160),
                  fontsize=24, color="orange")

    if stats_open:
        draw_stats()
        return

    if settings_open:
        draw_settings()
        return

    if game.state == "game_over":
        draw_filled_rect(pygame.Rect(0, 0, WIDTH, HEIGHT), (0, 0, 0, 180))
        draw_text("YOU DIED",
                  center=(WIDTH // 2, HEIGHT // 2 - 20),
                  fontsize=80, color="red")
        draw_text("Press R to Restart",
                  center=(WIDTH // 2, HEIGHT // 2 + 40),
                  fontsize=30, color="white")

    draw_ui()

# ---------------------------------
# UI
# ---------------------------------

def draw_ui():
    draw_text("Level: " + str(game.score + 1), topleft=(10, 10),
              fontsize=30, color=COLOR_TEXT)
    draw_text("Lives: " + str(game.lives), topleft=(10, 40),
              fontsize=30, color=COLOR_TEXT)
    draw_text("Money: " + str(game.money), topleft=(10, 70),
              fontsize=30, color="yellow")

    if game.bomb_unlocked:
        if game.bomb_ready:
            bomb_text  = "Bomb [V]: READY"
            bomb_color = "red"
        else:
            bomb_rem   = max(0.0, game.BOMB_COOLDOWN - (time.time() - game.last_bomb))
            bomb_text  = "Bomb [V]: {:.1f}s".format(bomb_rem)
            bomb_color = "darkred"

    if game.shotgun_ready:
        sho_text  = "Shotgun [B]: READY"
        sho_color = "orange"
    else:
        sho_rem   = max(0.0, game.SHOTGUN_COOLDOWN - (time.time() - game.last_shotgun))
        sho_text  = "Shotgun [B]: {:.1f}s".format(sho_rem)
        sho_color = "purple"

    if game.regular_ready:
        reg_text  = "Shot [SPACE]: READY"
        reg_color = "green"
    else:
        reg_rem   = max(0.0, game.REGULAR_COOLDOWN - (time.time() - game.last_regular))
        reg_text  = "Shot [SPACE]: {:.1f}s".format(reg_rem)
        reg_color = "red"

    if game.super_ready:
        sup_text  = "Super [N]: READY"
        sup_color = "cyan"
    else:
        sup_rem   = max(0.0, game.SUPER_COOLDOWN - (time.time() - game.last_super))
        sup_text  = "Super [N]: {:.1f}s".format(sup_rem)
        sup_color = "orange"

    if game.shield_unlocked:
        shield_color = "cyan" if game.shield_hp > 0 else (100, 100, 100)
        draw_text("Shield: " + str(game.shield_hp) + "/" + str(game.shield_max),
                  topleft=(10, 95), fontsize=24, color=shield_color)
    if game.bomb_unlocked:
        draw_text(bomb_text, topleft=(10, 120), fontsize=24, color=bomb_color)
    draw_text(sho_text, topleft=(10, 145), fontsize=24, color=sho_color)
    draw_text(sup_text, topleft=(10, 170), fontsize=24, color=sup_color)
    draw_text(reg_text, topleft=(10, 195), fontsize=24, color=reg_color)
    if game.time_burst_unlocked:
        if game.time_burst_active:
            tb_rem   = max(0.0, TIME_BURST_DURATION - game.time_burst_timer)
            tb_text  = "Time Burst [C]: {:.1f}s".format(tb_rem)
            tb_color = (100, 200, 255)
        elif game.time_burst_ready:
            tb_text  = "Time Burst [C]: READY"
            tb_color = (100, 200, 255)
        else:
            tb_rem   = max(0.0, TIME_BURST_COOLDOWN - (time.time() - game.last_time_burst))
            tb_text  = "Time Burst [C]: {:.1f}s".format(tb_rem)
            tb_color = (60, 120, 180)
        draw_text(tb_text, topleft=(10, 220), fontsize=24, color=tb_color)

    alive_bosses = [b for b in boss_zombies if not b.dying]
    if alive_bosses:
        bar_w    = 300
        bar_h    = 20
        bar_gap  = 4
        label    = "BOSS" if len(alive_bosses) == 1 else "BOSS  x{}".format(len(alive_bosses))
        draw_text(label, center=(WIDTH // 2, 12), fontsize=20, color="red", shadow=(1, 1))
        for i, boss in enumerate(alive_bosses):
            bx     = WIDTH // 2 - bar_w // 2
            by     = 26 + i * (bar_h + bar_gap)
            fill_w = int(bar_w * max(0, min(boss.health, boss.max_health)) / boss.max_health)
            bar_surf = pygame.Surface((bar_w, bar_h))
            bar_surf.fill((60, 0, 0))
            if fill_w > 0:
                pygame.draw.rect(bar_surf, (210, 0, 0), (0, 0, fill_w, bar_h))
            pygame.draw.rect(bar_surf, (255, 80, 80), (0, 0, bar_w, bar_h), 2)
            screen.blit(bar_surf, (bx, by))

# ---------------------------------
# Settings overlay
# ---------------------------------

_SETTINGS_PNL_W = 500
_SETTINGS_PNL_H = 360
_SETTINGS_ROW_H = 44
_SETTINGS_BTN_W = 70
_SETTINGS_BTN_H = 30

def draw_settings():
    pw = _SETTINGS_PNL_W
    ph = _SETTINGS_PNL_H
    px = WIDTH  // 2 - pw // 2
    py = HEIGHT // 2 - ph // 2

    draw_filled_rect(pygame.Rect(px, py, pw, ph), (0, 0, 0, 220))
    draw_rect_outline(pygame.Rect(px, py, pw, ph), "cyan")

    draw_text("Settings", center=(WIDTH // 2, py + 22),
              fontsize=34, color="cyan", shadow=(1, 1))
    draw_text("Page " + str(settings_page + 1) + "/" + str(SETTINGS_NUM_PAGES),
              center=(WIDTH // 2, py + 45), fontsize=15, color="grey")
    draw_text("[O] Back   [P] Next",
              center=(WIDTH // 2, py + ph - 38), fontsize=17, color="grey")
    draw_text("Press X to Close",
              center=(WIDTH // 2, py + ph - 18), fontsize=18, color="white", ocolor="black")

    if settings_page < len(SETTINGS_PAGES_DATA):
        title, items = SETTINGS_PAGES_DATA[settings_page]
        draw_text(title, center=(WIDTH // 2, py + 70), fontsize=22, color="white")

        start_y = py + 105
        label_x = px + 20
        btn_x   = px + pw - _SETTINGS_BTN_W - 20

        for i, (label, key) in enumerate(items):
            row_y   = start_y + i * _SETTINGS_ROW_H
            enabled = settings.get(key, True)
            draw_text(label, topleft=(label_x, row_y + 6), fontsize=21, color="white")
            btn = pygame.Rect(btn_x, row_y + 2, _SETTINGS_BTN_W, _SETTINGS_BTN_H)
            if enabled:
                draw_filled_rect(btn, (0, 110, 0))
                draw_rect_outline(btn, "green")
                draw_text("ON",  center=btn.center, fontsize=20, color="green")
            else:
                draw_filled_rect(btn, (110, 0, 0))
                draw_rect_outline(btn, "red")
                draw_text("OFF", center=btn.center, fontsize=20, color="red")
    else:
        draw_text("[ Coming Soon ]", center=(WIDTH // 2, HEIGHT // 2),
                  fontsize=30, color="grey")

# ---------------------------------
# Stats overlay
# ---------------------------------

_MODE_NAMES = {"scaperoom": "Scaperoom", "survival": "Survival", "bossrush": "Boss Rush"}
_DIFF_NAMES = {"easy": "Easy", "normal": "Normal", "hard": "Hard", "nightmare": "Nightmare"}

def draw_stats():
    pw = 460
    ph = 450
    px = WIDTH  // 2 - pw // 2
    py = HEIGHT // 2 - ph // 2

    draw_filled_rect(pygame.Rect(px, py, pw, ph), (0, 0, 0, 220))
    draw_rect_outline(pygame.Rect(px, py, pw, ph), "yellow")

    draw_text("Statistics",
              center=(WIDTH // 2, py + 24),
              fontsize=34, color="yellow", shadow=(1, 1))
    draw_text("Press K or X to Close",
              center=(WIDTH // 2, py + ph - 20),
              fontsize=18, color="white", ocolor="black")

    # --- Kill counts ---
    draw_text("Kill Counts",
              center=(WIDTH // 2, py + 66),
              fontsize=20, color="grey")

    kills = [
        ("Zombies",         kill_stats.get("zombie",  0), "green"),
        ("Fast Zombies",    kill_stats.get("fast",    0), "cyan"),
        ("Tank Zombies",    kill_stats.get("tank",    0), "orange"),
        ("Police Zombies",  kill_stats.get("police",  0), (100, 160, 255)),
        ("Boss Zombies",    kill_stats.get("boss",    0), "red"),
    ]
    lx = px + 30
    rx = px + pw - 30
    for i, (label, count, color) in enumerate(kills):
        y = py + 92 + i * 30
        draw_text(label + ":", topleft=(lx, y), fontsize=20, color="white")
        draw_text(str(count),  topleft=(rx - len(str(count)) * 12, y),
                  fontsize=20, color=color)

    # --- High scores ---
    draw_text("Best Wave per Mode",
              center=(WIDTH // 2, py + 252),
              fontsize=20, color="grey")

    entries = []
    for mode in ("scaperoom", "survival", "bossrush"):
        for diff in ("easy", "normal", "hard", "nightmare"):
            key   = mode + "_" + diff
            score = high_scores.get(key, 0)
            if score > 0:
                entries.append((_MODE_NAMES[mode], _DIFF_NAMES[diff], score))
    entries.sort(key=lambda e: -e[2])  # best first

    if not entries:
        draw_text("No runs completed yet.",
                  center=(WIDTH // 2, py + 290),
                  fontsize=20, color="grey")
    else:
        for i, (mname, dname, score) in enumerate(entries[:7]):
            y = py + 278 + i * 26
            draw_text(mname + "  " + dname + ":",
                      topleft=(lx, y), fontsize=18, color="white")
            draw_text("Wave " + str(score + 1),
                      topleft=(rx - 90, y), fontsize=18, color="yellow")


# ---------------------------------
# Spawning
# ---------------------------------

def _safe_spawn_tile(x, y):
    """Return True if tile (x,y) is a floor tile far enough from the player."""
    if game_map[y][x] != 1:
        return False
    px = x * TILE_W - classd.x
    py = y * TILE_H - classd.y
    return (px * px + py * py) >= SPAWN_SAFE_RADIUS * SPAWN_SAFE_RADIUS

def spawn_zombies(count):
    for _ in range(count):
        while True:
            x = random.randint(1, MAP_W - 2)
            y = random.randint(1, MAP_H - 4)
            if _safe_spawn_tile(x, y):
                zombies.append(Zombie(x * TILE_W, y * TILE_H, game.zombie_speed))
                break

def spawn_fast_zombies(count):
    for _ in range(count):
        while True:
            x = random.randint(1, MAP_W - 2)
            y = random.randint(1, MAP_H - 4)
            if _safe_spawn_tile(x, y):
                fast_zombies.append(FastZombie(x * TILE_W, y * TILE_H,
                                               game.fast_zombie_speed))
                break

def spawn_tank_zombies(count):
    for _ in range(count):
        while True:
            x = random.randint(1, MAP_W - 2)
            y = random.randint(1, MAP_H - 4)
            if _safe_spawn_tile(x, y):
                tank_zombies.append(TankZombie(x * TILE_W, y * TILE_H,
                                               game.tank_zombie_speed))
                break

def spawn_police_zombies(count):
    for _ in range(count):
        while True:
            x = random.randint(1, MAP_W - 2)
            y = random.randint(1, MAP_H - 4)
            if _safe_spawn_tile(x, y):
                police_zombies.append(PoliceZombie(x * TILE_W, y * TILE_H,
                                                   game.police_zombie_speed,
                                                   game.police_proj_speed))
                break

def spawn_boss_zombie():
    spd            = 0.8 * SCALE + game.boss_level * 0.15
    hp             = 10 + game.boss_level * 5
    spawn_count    = min(2 + game.boss_level, 5)
    spawn_cooldown = max(20.0 - game.boss_level * 2.0, 10.0)
    while True:
        x = random.randint(1, MAP_W - 2)
        y = random.randint(1, MAP_H - 4)
        if _safe_spawn_tile(x, y):
            boss_zombies.append(BossZombie(x * TILE_W, y * TILE_H,
                                           speed=spd, health=hp,
                                           spawn_count=spawn_count,
                                           spawn_cooldown=spawn_cooldown))
            break

def _rush_boss_stats(rush_level):
    """Compute BossRush boss stats for a given rush level (0 = freshest, 9 = fully capped)."""
    rl   = max(0, min(rush_level, 9))
    diff = DIFFICULTY_SETTINGS.get(game.difficulty, {"speed_mult": 1.0})
    spd  = min((0.8 + rl * (0.5 / 9.0)) * SCALE * diff["speed_mult"], 1.3 * SCALE)
    hp   = 15 + rl * 5                     # 15 HP at rl=0, 60 HP at rl=9
    sc   = min(2 + rl // 4, 4)             # 2 → 3 → 4, caps at rl=8
    scd  = max(20.0 - rl * (8.0 / 9.0), 12.0)  # 20s → 12s
    return spd, hp, sc, scd

def spawn_rush_boss(rush_level):
    spd, hp, sc, scd = _rush_boss_stats(rush_level)
    while True:
        x = random.randint(1, MAP_W - 2)
        y = random.randint(1, MAP_H - 4)
        if _safe_spawn_tile(x, y):
            boss_zombies.append(BossZombie(x * TILE_W, y * TILE_H,
                                           speed=spd, health=hp,
                                           spawn_count=sc,
                                           spawn_cooldown=scd))
            break

# ---------------------------------
# Level progression
# ---------------------------------

def next_level():
    game.score += 1
    _earn(int(LEVEL_REWARD * game.coin_multiplier))
    play_sound("snd_level_up")

    if game.shield_unlocked and game.shield_hp < game.shield_max and game.score % 3 == 0:
        game.shield_hp += 1

    if game.score % LEVELS_FOR_SHOP == 0:
        game.shop_open = True
        game.paused    = True
        return

    actual_level_progression()


def actual_level_progression():
    if game.mode == "bossrush":
        boss_zombies[:]      = []
        boss_projectiles[:]  = []
        key_items[:]         = []
        num_bosses = (game.score // 5) + 1
        for k in range(num_bosses):
            rush_level = game.score - k * 5
            if rush_level >= 0:
                spawn_rush_boss(rush_level)
        game.lives += 1
        return

    zombie_cap = ZOMBIE_MAX      * 2 if game.mode == "survival" else ZOMBIE_MAX
    fast_cap   = FAST_ZOMBIE_MAX * 2 if game.mode == "survival" else FAST_ZOMBIE_MAX
    tank_cap   = TANK_ZOMBIE_MAX * 2 if game.mode == "survival" else TANK_ZOMBIE_MAX

    speed_mult       = 1.1 if game.mode == "survival" else 1.0
    speed_limit      = ZOMBIE_SPEED_LIMIT      * SCALE * speed_mult
    fast_speed_limit = FAST_ZOMBIE_SPEED_LIMIT * SCALE * speed_mult
    tank_speed_limit = TANK_ZOMBIE_SPEED_LIMIT *         speed_mult

    normal_every = 2 if game.difficulty == "easy" else 1
    fast_every   = 4 if game.difficulty == "easy" else 2
    zombie_inc   = 2 if game.mode == "survival" else 1
    fast_inc     = 2 if game.mode == "survival" else 1

    if game.difficulty == "nightmare":
        zombie_inc *= 2
        fast_inc   *= 2

    game.zombie_speed = min(game.zombie_speed + 0.15 * SCALE, speed_limit)

    if game.score % normal_every == 0:
        game.min_zombies = min(game.min_zombies + zombie_inc, zombie_cap)

    if game.score % fast_every == 0:
        game.min_fast_zombies = min(game.min_fast_zombies + fast_inc, fast_cap)
        game.fast_zombie_speed = min(game.fast_zombie_speed + 0.35 * SCALE,
                                     fast_speed_limit)

    tank_every = 6 if game.difficulty == "easy" else 3
    if game.score % tank_every == 0:
        game.min_tank_zombies = min(game.min_tank_zombies + 1, tank_cap)
        game.tank_zombie_speed = min(game.tank_zombie_speed + 0.06 * SCALE,
                                     tank_speed_limit)

    if game.score % 4 == 0:
        game.min_police_zombies = min(game.min_police_zombies + 1, 5)

    zombies[:]         = []
    fast_zombies[:]    = []
    tank_zombies[:]    = []
    police_zombies[:]  = []
    boss_projectiles[:] = []

    spawn_zombies(game.min_zombies)

    if game.min_fast_zombies > 0:
        spawn_fast_zombies(game.min_fast_zombies)

    if game.min_tank_zombies > 0:
        spawn_tank_zombies(game.min_tank_zombies)

    if game.min_police_zombies > 0:
        spawn_police_zombies(game.min_police_zombies)

    if game.score % 5 == 0:
        boss_zombies[:] = []
        spawn_boss_zombie()
        game.boss_level += 1

    game.lives += 1

    if game.mode == "survival":
        key_items[:] = []
    else:
        key_items[:] = [spawn_key() for _ in range(game.score + 1)]

# ---------------------------------
# Boss update helpers
# ---------------------------------

def update_boss_zombies(dt):
    mult = 0.25 if game.time_burst_active else 1.0
    for boss in boss_zombies[:]:
        if not boss.dying:
            saved = boss.speed; boss.speed *= mult
            boss.move(classd)
            boss.speed = saved
        boss.update(dt)
        if boss.dying and boss.die_frame >= 32:
            boss_zombies.remove(boss)


def update_boss_projectiles(dt):
    for bp in boss_projectiles[:]:
        bp.move(dt)
        if bp.is_offscreen():
            boss_projectiles.remove(bp)


def update_boss_hit_effects(dt):
    for e in boss_hit_effects[:]:
        e[3] += dt
        if e[3] >= 0.05:
            e[3] -= 0.05
            e[2] += 1
        if e[2] >= 6:
            boss_hit_effects.remove(e)

# ---------------------------------
# Update (main loop logic)
# ---------------------------------

def update(dt):
    if game.state != "playing" or game.paused:
        return

    now = time.time()
    if not game.super_ready   and now - game.last_super   >= game.SUPER_COOLDOWN:
        game.super_ready   = True
    if not game.regular_ready and now - game.last_regular >= game.REGULAR_COOLDOWN:
        game.regular_ready = True
    if not game.shotgun_ready and now - game.last_shotgun >= game.SHOTGUN_COOLDOWN:
        game.shotgun_ready = True
    if not game.bomb_ready    and now - game.last_bomb    >= game.BOMB_COOLDOWN:
        game.bomb_ready    = True
    if game.time_burst_active:
        game.time_burst_timer += dt
        if game.time_burst_timer >= TIME_BURST_DURATION:
            game.time_burst_active = False
            game.time_burst_timer  = 0.0
            game.time_burst_ready  = False
            game.last_time_burst   = now
    if not game.time_burst_ready and now - game.last_time_burst >= TIME_BURST_COOLDOWN:
        game.time_burst_ready = True

    move_doctor()
    update_zombies()
    update_projectiles()
    check_collisions()
    update_explosions(dt)
    update_bomb_explosions(dt)
    update_skull_effects(dt)
    update_spark_effects(dt)
    update_rings_effects(dt)
    update_boss_zombies(dt)
    update_boss_projectiles(dt)
    update_boss_hit_effects(dt)

    for key in key_items[:]:
        if classd.colliderect(key):
            spawn_rings(key.x, key.y)
            key_items.remove(key)
            play_sound("snd_key_pickup")

    if game.mode in ("survival", "bossrush"):
        active_bosses = [b for b in boss_zombies if not b.dying]
        if (len(zombies) == 0 and len(fast_zombies) == 0 and
                len(tank_zombies) == 0 and len(police_zombies) == 0 and
                len(active_bosses) == 0):
            next_level()
    elif game.mode == "scaperoom":
        if len(key_items) == 0 and classd.colliderect(door):
            next_level()

# ---------------------------------
# Movement helpers
# ---------------------------------

def move_doctor():
    if game.mode in ("survival", "bossrush"):
        return
    if doctor.x < classd.x:
        doctor.x    += game.doctor_speed
        doctor.image = "plague_doctor"
    elif doctor.x > classd.x:
        doctor.x    -= game.doctor_speed
        doctor.image = "plague_doctor_flipped"
    if doctor.y < classd.y:
        doctor.y += game.doctor_speed
    elif doctor.y > classd.y:
        doctor.y -= game.doctor_speed


def update_zombies():
    mult = 0.25 if game.time_burst_active else 1.0
    for z in zombies:
        saved = z.speed; z.speed *= mult
        z.move(classd)
        z.speed = saved
    for z in fast_zombies:
        saved = z.speed; z.speed *= mult
        z.move(classd)
        z.speed = saved
    for z in tank_zombies:
        saved = z.speed; z.speed *= mult
        z.move(classd)
        z.speed = saved
    for z in police_zombies:
        saved = z.speed; z.speed *= mult
        z.move(classd)
        z.speed = saved
        z.try_shoot(classd)
        z.update_projectiles()

# ---------------------------------
# Collisions
# ---------------------------------

def check_collisions():
    if game.mode == "scaperoom" and classd.colliderect(doctor):
        _trigger_game_over()
        return

    for z in zombies[:]:
        if classd.colliderect(z.actor):
            play_sound("snd_player_hit")
            if not _apply_hit(1):
                classd.topleft = (TILE_W, TILE_H * (MAP_H - 3))
                zombies.remove(z)
            break

    for z in fast_zombies[:]:
        if classd.colliderect(z.actor):
            play_sound("snd_player_hit")
            if not _apply_hit(1):
                classd.topleft = (TILE_W, TILE_H * (MAP_H - 3))
                fast_zombies.remove(z)
            break

    for z in tank_zombies[:]:
        if classd.colliderect(z.actor):
            play_sound("snd_player_hit")
            if not _apply_hit(2):
                classd.topleft = (TILE_W, TILE_H * (MAP_H - 3))
                tank_zombies.remove(z)
            break

    for z in police_zombies[:]:
        if classd.colliderect(z.actor):
            play_sound("snd_player_hit")
            if not _apply_hit(1):
                classd.topleft = (TILE_W, TILE_H * (MAP_H - 3))
                police_zombies.remove(z)
            break
        for p in z.projectiles[:]:
            if classd.colliderect(p.actor):
                z.projectiles.remove(p)
                play_sound("snd_player_hit")
                if not _apply_hit(1):
                    classd.topleft = (TILE_W, TILE_H * (MAP_H - 3))
                break

    for bp in boss_projectiles[:]:
        if bp.colliderect(classd):
            boss_projectiles.remove(bp)
            boss_hit_effects.append([bp.x, bp.y, 0, 0.0])
            play_sound("snd_player_hit")
            if not _apply_hit(2):
                classd.topleft = (TILE_W, TILE_H * (MAP_H - 3))
            break

    for boss in boss_zombies[:]:
        if not boss.dying and boss.colliderect(classd):
            play_sound("snd_player_hit")
            if not _apply_hit(3):
                classd.topleft = (TILE_W, TILE_H * (MAP_H - 3))
            break

# ---------------------------------
# Projectiles and shooting
# ---------------------------------

def update_projectiles():
    for p in projectiles[:]:
        p.move()
        if (game.mode == "scaperoom" and p.actor.colliderect(doctor)) or p.is_offscreen():
            if p.bomb:
                do_bomb_explosion(p.actor.x, p.actor.y)
            projectiles.remove(p)
            continue
        for z in zombies[:]:
            if p.actor.colliderect(z.actor):
                spawn_spark(p.actor.x, p.actor.y)
                z.health -= p.damage
                if z.health <= 0:
                    spawn_skull(z.actor.x, z.actor.y)
                    zombies.remove(z)
                    _kill("zombie", int(10 * game.coin_multiplier))
                if p.bomb:
                    do_bomb_explosion(p.actor.x, p.actor.y)
                elif p.explosive:
                    do_explosion(p.actor.x, p.actor.y)
                if not p.piercing and p in projectiles:
                    projectiles.remove(p)
                break
        for z in fast_zombies[:]:
            if p in projectiles and p.actor.colliderect(z.actor):
                spawn_spark(p.actor.x, p.actor.y)
                z.health -= p.damage
                if z.health <= 0:
                    spawn_skull(z.actor.x, z.actor.y)
                    fast_zombies.remove(z)
                    _kill("fast", int(20 * game.coin_multiplier))
                if p.bomb:
                    do_bomb_explosion(p.actor.x, p.actor.y)
                elif p.explosive:
                    do_explosion(p.actor.x, p.actor.y)
                if not p.piercing and p in projectiles:
                    projectiles.remove(p)
                break
        for z in tank_zombies[:]:
            if p in projectiles and p.actor.colliderect(z.actor):
                spawn_spark(p.actor.x, p.actor.y)
                z.health -= p.damage
                if z.health <= 0:
                    spawn_skull(z.actor.x, z.actor.y)
                    tank_zombies.remove(z)
                    _kill("tank", int(30 * game.coin_multiplier))
                if p.bomb:
                    do_bomb_explosion(p.actor.x, p.actor.y)
                elif p.explosive:
                    do_explosion(p.actor.x, p.actor.y)
                if not p.piercing and p in projectiles:
                    projectiles.remove(p)
                break
        for z in police_zombies[:]:
            if p in projectiles and p.actor.colliderect(z.actor):
                spawn_spark(p.actor.x, p.actor.y)
                z.health -= p.damage
                if z.health <= 0:
                    spawn_skull(z.actor.x, z.actor.y)
                    police_zombies.remove(z)
                    _kill("police", int(25 * game.coin_multiplier))
                if p.bomb:
                    do_bomb_explosion(p.actor.x, p.actor.y)
                elif p.explosive:
                    do_explosion(p.actor.x, p.actor.y)
                if not p.piercing and p in projectiles:
                    projectiles.remove(p)
                break
        for boss in boss_zombies[:]:
            if not boss.dying and p in projectiles and boss.colliderect(p.actor):
                spawn_spark(p.actor.x, p.actor.y)
                dmg = 5 if p.piercing else p.damage
                boss.health -= dmg
                if boss.health <= 0:
                    boss.dying      = True
                    boss.anim_frame = 0
                    _kill("boss", int(100 * game.coin_multiplier))
                if p.bomb:
                    do_bomb_explosion(p.actor.x, p.actor.y)
                if p in projectiles:
                    projectiles.remove(p)
                break


def shoot(super_shot):
    x = classd.right + 10 if facing == "right" else classd.left - 10
    y = classd.y
    projectiles.append(Projectile(x, y, facing, super_shot))
    play_sound("snd_shoot")


def do_explosion(px, py):
    if settings["vfx_explosion"]:
        explosions.append([px, py, 0, 0.0])
    play_sound("snd_explosion")
    radius = 2 * TILE_W
    for z in zombies[:]:
        if ((z.actor.x - px) ** 2 + (z.actor.y - py) ** 2) ** 0.5 <= radius:
            z.health -= 1
            if z.health <= 0:
                spawn_skull(z.actor.x, z.actor.y)
                zombies.remove(z)
                _kill("zombie", int(10 * game.coin_multiplier))
    for z in fast_zombies[:]:
        if ((z.actor.x - px) ** 2 + (z.actor.y - py) ** 2) ** 0.5 <= radius:
            z.health -= 1
            if z.health <= 0:
                spawn_skull(z.actor.x, z.actor.y)
                fast_zombies.remove(z)
                _kill("fast", int(20 * game.coin_multiplier))
    for z in tank_zombies[:]:
        if ((z.actor.x - px) ** 2 + (z.actor.y - py) ** 2) ** 0.5 <= radius:
            z.health -= 1
            if z.health <= 0:
                spawn_skull(z.actor.x, z.actor.y)
                tank_zombies.remove(z)
                _kill("tank", int(30 * game.coin_multiplier))
    for z in police_zombies[:]:
        if ((z.actor.x - px) ** 2 + (z.actor.y - py) ** 2) ** 0.5 <= radius:
            z.health -= 1
            if z.health <= 0:
                spawn_skull(z.actor.x, z.actor.y)
                police_zombies.remove(z)
                _kill("police", int(25 * game.coin_multiplier))


def update_explosions(dt):
    for e in explosions[:]:
        e[3] += dt
        if e[3] >= 0.05:
            e[3] -= 0.05
            e[2] += 1
        if e[2] >= 8:
            explosions.remove(e)


def do_bomb_explosion(px, py):
    if settings["vfx_bomb_explosion"]:
        bomb_explosions.append([px, py, 0, 0.0])
    play_sound("snd_bomb")
    radius = 2 * TILE_W * 4.5
    for z in zombies[:]:
        if ((z.actor.x - px) ** 2 + (z.actor.y - py) ** 2) ** 0.5 <= radius:
            z.health -= 2
            if z.health <= 0:
                spawn_skull(z.actor.x, z.actor.y)
                zombies.remove(z)
                _kill("zombie", int(10 * game.coin_multiplier))
    for z in fast_zombies[:]:
        if ((z.actor.x - px) ** 2 + (z.actor.y - py) ** 2) ** 0.5 <= radius:
            z.health -= 2
            if z.health <= 0:
                spawn_skull(z.actor.x, z.actor.y)
                fast_zombies.remove(z)
                _kill("fast", int(20 * game.coin_multiplier))
    for z in tank_zombies[:]:
        if ((z.actor.x - px) ** 2 + (z.actor.y - py) ** 2) ** 0.5 <= radius:
            z.health -= 2
            if z.health <= 0:
                spawn_skull(z.actor.x, z.actor.y)
                tank_zombies.remove(z)
                _kill("tank", int(30 * game.coin_multiplier))
    for z in police_zombies[:]:
        if ((z.actor.x - px) ** 2 + (z.actor.y - py) ** 2) ** 0.5 <= radius:
            z.health -= 2
            if z.health <= 0:
                spawn_skull(z.actor.x, z.actor.y)
                police_zombies.remove(z)
                _kill("police", int(25 * game.coin_multiplier))


def update_bomb_explosions(dt):
    for e in bomb_explosions[:]:
        e[3] += dt
        if e[3] >= 0.06:
            e[3] -= 0.06
            e[2] += 1
        if e[2] >= 13:
            bomb_explosions.remove(e)


def update_skull_effects(dt):
    for e in skull_effects[:]:
        e[3] += dt
        if e[3] >= 0.04:
            e[3] -= 0.04
            e[2] += 1
        if e[2] >= 29:
            skull_effects.remove(e)


def update_spark_effects(dt):
    for e in spark_effects[:]:
        e[3] += dt
        if e[3] >= 0.035:
            e[3] -= 0.035
            e[2] += 1
        if e[2] >= 13:
            spark_effects.remove(e)


def update_rings_effects(dt):
    for e in rings_effects[:]:
        e[3] += dt
        if e[3] >= 0.045:
            e[3] -= 0.045
            e[2] += 1
        if e[2] >= 15:
            rings_effects.remove(e)


def shoot_bomb():
    x = classd.right + 10 if facing == "right" else classd.left - 10
    y = classd.y
    p      = Projectile(x, y, facing, False)
    p.bomb = True
    projectiles.append(p)


def shoot_shotgun():
    play_sound("snd_shotgun")
    x = classd.right + 10 if facing == "right" else classd.left - 10
    y = classd.y
    if game.shotgun_six:
        vys = [0, -2 * SCALE, 2 * SCALE, -4 * SCALE, 4 * SCALE, -6 * SCALE]
    else:
        vys = [0, -3 * SCALE, 3 * SCALE]
    for vy in vys:
        projectiles.append(Projectile(x, y, facing, False, vy=vy))

# ---------------------------------
# Keyboard input
# ---------------------------------

def on_key_down(key):
    global facing, settings_open, settings_page, stats_open

    # Mode selection
    if game.state == "mode_select":
        if key == pygame.K_s:
            game.mode  = "scaperoom"
            game.state = "menu"
        elif key == pygame.K_v:
            game.mode  = "survival"
            game.state = "menu"
        elif key == pygame.K_b:
            game.mode  = "bossrush"
            game.state = "menu"
        return

    # Difficulty selection
    if game.state == "menu":
        chosen = None
        if key == pygame.K_e:
            chosen = "easy"
        elif key == pygame.K_n:
            chosen = "normal"
        elif key == pygame.K_h:
            chosen = "hard"
        elif key == pygame.K_m:
            chosen = "nightmare"

        if chosen:
            diff                 = DIFFICULTY_SETTINGS[chosen]
            game.difficulty      = chosen
            game.coin_multiplier    = diff["coin_mult"]
            game.zombie_speed       = 0.3  * SCALE * diff["speed_mult"]
            game.fast_zombie_speed  = 0.6  * SCALE * diff["speed_mult"]
            game.police_zombie_speed = 0.15 * SCALE * diff["speed_mult"]
            game.police_proj_speed   = 0.6  * SCALE * diff["speed_mult"]
            game.doctor_speed       = 1.2  * SCALE * diff["speed_mult"]
            if game.mode == "survival":
                game.zombie_speed      *= 1.1
                game.fast_zombie_speed *= 1.1
                key_items[:] = []
                spawn_zombies(2)
            elif game.mode == "bossrush":
                key_items[:] = []
                spawn_rush_boss(0)
            else:
                spawn_zombies(1)
            game.state = "playing"
        return

    # Restart
    if game.state == "game_over" and key == pygame.K_r:
        _save_progress()
        _was_unlocked    = game.skin_unlocked
        game.__init__()
        game.skin_unlocked  = _was_unlocked
        zombies[:]          = []
        fast_zombies[:]     = []
        tank_zombies[:]     = []
        police_zombies[:]   = []
        boss_zombies[:]     = []
        projectiles[:]      = []
        boss_projectiles[:] = []
        boss_hit_effects[:] = []
        game.boss_level     = 0
        key_items[:]        = [spawn_key()]
        classd.topleft      = (TILE_W, TILE_H * (MAP_H - 3))
        doctor.topleft      = (TILE_W * 4, TILE_H * 3)
        return

    # Shop navigation / exit
    if game.shop_open and key == pygame.K_x:
        game.shop_open = False
        game.paused    = False
        actual_level_progression()
        return
    if game.shop_open and key == pygame.K_o:
        game.shop_page = (game.shop_page - 1) % SHOP_PAGES
        return
    if game.shop_open and key == pygame.K_p:
        game.shop_page = (game.shop_page + 1) % SHOP_PAGES
        return

    # Skin shop navigation / exit
    if game.skin_shop_open and key == pygame.K_x:
        game.skin_shop_open = False
        game.paused         = False
        return
    if game.skin_shop_open and key == pygame.K_o:
        game.skin_shop_page = (game.skin_shop_page - 1) % SKIN_SHOP_PAGES
        return
    if game.skin_shop_open and key == pygame.K_p:
        game.skin_shop_page = (game.skin_shop_page + 1) % SKIN_SHOP_PAGES
        return

    # Stats close
    if stats_open and key in (pygame.K_x, pygame.K_k):
        stats_open = False
        return

    # Settings navigation / exit
    if settings_open and key == pygame.K_x:
        settings_open = False
        return
    if settings_open and key == pygame.K_o:
        settings_page = (settings_page - 1) % SETTINGS_NUM_PAGES
        return
    if settings_open and key == pygame.K_p:
        settings_page = (settings_page + 1) % SETTINGS_NUM_PAGES
        return

    # Open settings from pause
    if (game.paused and not game.shop_open and not game.skin_shop_open
            and not settings_open and not stats_open and key == pygame.K_t):
        settings_open = True
        return

    # Open cosmetic shop while paused
    if game.paused and not game.shop_open and not game.skin_shop_open and not settings_open and not stats_open and key == pygame.K_s:
        game.skin_shop_open = True
        return

    # Open stats while paused
    if (game.paused and not game.shop_open and not game.skin_shop_open
            and not settings_open and not stats_open and key == pygame.K_k):
        stats_open = True
        return

    # Return to main menu from pause
    if (game.paused and not game.shop_open and not game.skin_shop_open
            and not settings_open and not stats_open and key == pygame.K_m):
        _go_to_menu()
        return

    # Toggle pause
    if key == pygame.K_p and game.state == "playing" and not game.skin_shop_open and not settings_open:
        game.paused = not game.paused
        return

    # Block input if dead or paused
    if game.state != "playing" or game.paused:
        return

    # Movement
    if key in (pygame.K_LEFT, pygame.K_a):
        classd.x -= TILE_W
        facing    = "left"
        update_player_sprite()
    elif key in (pygame.K_RIGHT, pygame.K_d):
        classd.x += TILE_W
        facing    = "right"
        update_player_sprite()
    elif key in (pygame.K_UP, pygame.K_w):
        classd.y -= TILE_H
    elif key in (pygame.K_DOWN, pygame.K_s):
        classd.y += TILE_H

    # Clamp inside map
    if classd.left  < TILE_W:          classd.left  = TILE_W
    if classd.right > WIDTH - TILE_W:  classd.right = WIDTH - TILE_W
    if classd.top   < TILE_H:          classd.top   = TILE_H
    if classd.bottom > HEIGHT - TILE_H: classd.bottom = HEIGHT - TILE_H

    # Shooting
    if key == pygame.K_SPACE and game.regular_ready:
        shoot(False)
        game.regular_ready = False
        game.last_regular  = time.time()
    elif key == pygame.K_n and game.super_ready:
        shoot(True)
        game.super_ready = False
        game.last_super  = time.time()
    elif key == pygame.K_b and game.shotgun_ready:
        shoot_shotgun()
        game.shotgun_ready = False
        game.last_shotgun  = time.time()
    elif key == pygame.K_v and game.bomb_unlocked and game.bomb_ready:
        shoot_bomb()
        game.bomb_ready = False
        game.last_bomb  = time.time()
    elif (key == pygame.K_c and game.time_burst_unlocked
            and game.time_burst_ready and not game.time_burst_active):
        game.time_burst_active = True
        game.time_burst_timer  = 0.0

# ---------------------------------
# Mouse / shop input
# ---------------------------------

def on_mouse_down(pos):
    global using_skin, skin_coins

    p = pos  # already (x, y) tuple from pygame event

    if settings_open:
        if settings_page < len(SETTINGS_PAGES_DATA):
            _, items = SETTINGS_PAGES_DATA[settings_page]
            pw      = _SETTINGS_PNL_W
            ph      = _SETTINGS_PNL_H
            px      = WIDTH  // 2 - pw // 2
            py      = HEIGHT // 2 - ph // 2
            start_y = py + 105
            btn_x   = px + pw - _SETTINGS_BTN_W - 20
            for i, (_, key) in enumerate(items):
                row_y = start_y + i * _SETTINGS_ROW_H
                btn   = pygame.Rect(btn_x, row_y + 2, _SETTINGS_BTN_W, _SETTINGS_BTN_H)
                if btn.collidepoint(*p):
                    settings[key] = not settings.get(key, True)
                    _save_progress()
        return

    if not game.shop_open and not game.skin_shop_open:
        return

    # --- Skin shop clicks ---
    if game.skin_shop_open:
        if game.skin_shop_page == 0:
            zombie_skin_icon.center = (WIDTH // 2, HEIGHT // 2 - 20)
            if zombie_skin_icon.collidepoint(*p):
                if not game.skin_unlocked and skin_coins >= SKIN_COST:
                    skin_coins         -= SKIN_COST
                    game.skin_unlocked = True
                    using_skin         = True
                    update_player_sprite()
                    _save_progress()
                    play_sound("snd_buy")
                    print("Protocol unlocked: Class-D Reanimation.")
                elif game.skin_unlocked:
                    using_skin = not using_skin
                    update_player_sprite()
                    _save_progress()
                    print("Skin Protocol: {}.".format("Active" if using_skin else "Inactive"))
                else:
                    print("Insufficient Dinero for cosmetic upgrade.")
        return

    # --- Main shop clicks ---
    if game.shop_page == 0:
        life_heart_icon.center = (WIDTH // 2, HEIGHT // 2 - 20)
        if life_heart_icon.collidepoint(*p):
            if game.money >= LIFE_COST and game.lives < game.lives_max:
                game.money -= LIFE_COST
                game.lives += 1
                play_sound("snd_buy")
                print("Item secured. Current lives: " + str(game.lives))
            elif game.money < LIFE_COST:
                print("Insufficient Dinero for life support.")
            else:
                print("Maximum life capacity reached.")
        shop_maxlife_rect.topleft = (WIDTH // 2 - 130, HEIGHT // 2 + 65)
        if shop_maxlife_rect.collidepoint(*p):
            if game.lives_max < 15 and game.money >= MAX_LIFE_COST:
                game.money    -= MAX_LIFE_COST
                game.lives_max = 15
                play_sound("snd_buy")
                print("Max lives increased to 15.")
            elif game.lives_max >= 15:
                print("Already purchased.")
            else:
                print("Insufficient coins.")

    elif game.shop_page == 1:
        if shop_reg_rect.collidepoint(*p):
            if not game.regular_halved and game.money >= REGULAR_HALVED_COST:
                game.money             -= REGULAR_HALVED_COST
                game.REGULAR_COOLDOWN  /= 2
                game.regular_halved     = True
                play_sound("snd_buy")
                print("Shot cooldown halved.")
            elif game.regular_halved:
                print("Already purchased.")
            else:
                print("Insufficient coins.")
        if shop_sup_rect.collidepoint(*p):
            if not game.super_halved and game.money >= SUPER_HALVED_COST:
                game.money           -= SUPER_HALVED_COST
                game.SUPER_COOLDOWN  /= 2
                game.super_halved     = True
                play_sound("snd_buy")
                print("Super cooldown halved.")
            elif game.super_halved:
                print("Already purchased.")
            else:
                print("Insufficient coins.")

    elif game.shop_page == 2:
        if shop_shotgun_halved_rect.collidepoint(*p):
            if not game.shotgun_halved and game.money >= SHOTGUN_HALVED_COST:
                game.money              -= SHOTGUN_HALVED_COST
                game.SHOTGUN_COOLDOWN   /= 2
                game.shotgun_halved      = True
                play_sound("snd_buy")
                print("Shotgun cooldown halved.")
            elif game.shotgun_halved:
                print("Already purchased.")
            else:
                print("Insufficient coins.")
        if shop_shotgun_six_rect.collidepoint(*p):
            if not game.shotgun_six and game.money >= SHOTGUN_SIX_COST:
                game.money      -= SHOTGUN_SIX_COST
                game.shotgun_six = True
                play_sound("snd_buy")
                print("6-shot shotgun unlocked.")
            elif game.shotgun_six:
                print("Already purchased.")
            else:
                print("Insufficient coins.")

    elif game.shop_page == 3:
        if shop_explosive_rect.collidepoint(*p):
            if not game.explosive_shots and game.money >= EXPLOSIVE_COST:
                game.money           -= EXPLOSIVE_COST
                game.explosive_shots  = True
                play_sound("snd_buy")
                print("Explosive shots unlocked.")
            elif game.explosive_shots:
                print("Already purchased.")
            else:
                print("Insufficient coins.")

    elif game.shop_page == 4:
        if shop_bomb_rect.collidepoint(*p):
            if not game.bomb_unlocked and game.money >= BOMB_COST:
                game.money        -= BOMB_COST
                game.bomb_unlocked = True
                play_sound("snd_buy")
                print("Bomb unlocked.")
            elif game.bomb_unlocked:
                print("Already purchased.")
            else:
                print("Insufficient coins.")

    elif game.shop_page == 5:
        if shop_ricochet_rect.collidepoint(*p):
            if not game.super_ricochet and game.money >= SUPER_RICOCHET_COST:
                game.money           -= SUPER_RICOCHET_COST
                game.super_ricochet   = True
                game.SUPER_COOLDOWN   = 10.0 if game.super_halved else 20.0
                play_sound("snd_buy")
                print("Ricochet unlocked.")
            elif game.super_ricochet:
                print("Already purchased.")
            else:
                print("Insufficient coins.")

    elif game.shop_page == 6:
        if shop_time_burst_rect.collidepoint(*p):
            if not game.time_burst_unlocked and game.money >= TIME_BURST_COST:
                game.money               -= TIME_BURST_COST
                game.time_burst_unlocked  = True
                play_sound("snd_buy")
                print("Time Burst unlocked.")
            elif game.time_burst_unlocked:
                print("Already purchased.")
            else:
                print("Insufficient coins.")

    elif game.shop_page == 7:
        shield_icon.center = (WIDTH // 2, HEIGHT // 2 - 20)
        if shield_icon.collidepoint(*p):
            if not game.shield_unlocked and game.money >= SHIELD_COST:
                game.money           -= SHIELD_COST
                game.shield_unlocked  = True
                game.shield_hp        = game.shield_max
                play_sound("snd_buy")
                print("Shield activated.")
            elif game.shield_unlocked:
                print("Shield already active.")
            else:
                print("Insufficient coins.")

# ---------------------------------
# Main game loop
# ---------------------------------

def update_music():
    try:
        want = settings.get("music_enabled", True) and (
            game.state in ("mode_select", "menu") or
            (game.state == "playing" and (game.paused or game.shop_open or game.skin_shop_open))
        )
        if want:
            if not pygame.mixer.music.get_busy():
                pygame.mixer.music.play(-1)
        else:
            if pygame.mixer.music.get_busy():
                pygame.mixer.music.stop()
    except Exception:
        pass


while True:
    dt = clock.tick(FPS) / 1000.0

    for event in pygame.event.get():
        if event.type == pygame.QUIT:
            pygame.quit()
            sys.exit()
        elif event.type == pygame.KEYDOWN:
            on_key_down(event.key)
        elif event.type == pygame.MOUSEBUTTONDOWN:
            if event.button == 1:
                on_mouse_down(event.pos)

    update_music()
    update(dt)
    draw()
    pygame.display.flip()
