"""Clawd in a maid outfit, as pixel art. Writes clawd_maid.png (upscaled, nearest-neighbour)."""
import sys
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else "clawd_maid.png"
W, H, SCALE = 72, 64, 16

BG = (244, 239, 230)
DOT = (232, 222, 208)
ORANGE = (217, 119, 87)
ORANGE_D = (191, 98, 70)
ORANGE_L = (232, 146, 115)
EYE = (30, 24, 20)
WHITE = (255, 253, 250)
FRILL = (226, 220, 214)
DRESS = (40, 38, 52)
DRESS_L = (64, 61, 80)
RIBBON = (196, 58, 74)
RIBBON_D = (150, 40, 56)
BLUSH = (240, 150, 150)
SILVER = (200, 204, 212)
SILVER_D = (150, 155, 166)
TEA = (150, 90, 50)
PINK = (238, 140, 160)
SHADOW = (225, 215, 200)

img = Image.new("RGB", (W, H), BG)
px = img.load()

def P(x, y, c):
    if 0 <= x < W and 0 <= y < H: px[x, y] = c
def R(x0, y0, x1, y1, c):           # inclusive-exclusive rectangle
    for y in range(y0, y1):
        for x in range(x0, x1): P(x, y, c)

# background polka dots
for y in range(2, H, 8):
    for x in range(2 + (y // 8 % 2) * 4, W, 8): P(x, y, DOT)

# floor shadow
R(14, 56, 58, 58, SHADOW); R(17, 58, 55, 59, SHADOW)

# ---- Clawd body (grid: unit = 4px, body x 14..54, top y 16)
BX0, BX1, BY0 = 14, 54, 16
R(BX0, BY0, BX1, BY0 + 24, ORANGE)
R(BX0, BY0, BX1, BY0 + 1, ORANGE_L)            # top highlight
# legs (under the skirt; visible part)
for lx in (18, 26, 38, 46):
    R(lx, 44, lx + 4, 54, ORANGE)
    R(lx, 51, lx + 4, 52, WHITE)                # sock band
    R(lx - 1, 52, lx + 5, 55, EYE)              # mary-jane shoes
    P(lx, 52, DRESS_L); P(lx + 1, 52, DRESS_L)

# ---- maid headdress (white frilly band with black trim)
R(16, 12, 52, 16, WHITE)
for x in range(16, 52):
    if x % 3 != 1: P(x, 11, WHITE)              # scalloped top
    if x % 3 == 0: P(x, 10, WHITE)
R(16, 15, 52, 16, DRESS)                         # black band
for x in range(17, 52, 3): P(x, 13, FRILL)      # lace dots
# little ribbon tails at the sides
R(13, 13, 16, 15, DRESS); P(12, 15, DRESS); P(13, 15, DRESS); P(12, 16, DRESS)
R(52, 13, 55, 15, DRESS); P(55, 15, DRESS); P(54, 15, DRESS); P(55, 16, DRESS)

# ---- face
for ex in (22, 42):
    R(ex, 20, ex + 4, 28, EYE)
    P(ex + 1, 21, WHITE); P(ex + 2, 21, WHITE); P(ex + 1, 22, WHITE)   # sparkle
    P(ex + 2, 26, (70, 60, 70))
# blush
for bx in (17, 47):
    R(bx, 27, bx + 4, 29, BLUSH)
    P(bx + 1, 27, (248, 180, 176))
# tiny "ω" mouth
for x, y in ((32, 27), (33, 28), (34, 27), (35, 28), (36, 27)): P(x, y, EYE)

# ---- dress: black bodice + flared skirt
R(BX0, 31, BX1, 44, DRESS)
R(BX0, 31, BX1, 32, DRESS_L)
for i, y in enumerate(range(38, 44)):          # skirt flare
    flare = (i + 1) // 2 + 1
    R(BX0 - flare, y, BX0, y + 1, DRESS); R(BX1, y, BX1 + flare, y + 1, DRESS)
# petticoat frill under the skirt
for x in range(BX0 - 4, BX1 + 4):
    P(x, 44, WHITE)
    if x % 2 == 0: P(x, 45, WHITE)
    else: P(x, 45, FRILL)
# skirt pleats
for x in (18, 25, 43, 50):
    R(x, 39, x + 1, 44, DRESS_L)

# white collar + red bow
R(24, 30, 44, 32, WHITE)
P(23, 30, WHITE); P(44, 30, WHITE); R(26, 32, 30, 33, WHITE); R(38, 32, 42, 33, WHITE)
R(30, 30, 38, 33, RIBBON)                        # bow wings
P(30, 30, RIBBON_D); P(37, 30, RIBBON_D); P(30, 32, RIBBON_D); P(37, 32, RIBBON_D)
R(33, 30, 35, 33, RIBBON_D)                      # knot
R(32, 33, 33, 36, RIBBON); R(35, 33, 36, 36, RIBBON)   # tails

# apron with frilled edge
R(24, 34, 44, 44, WHITE)
for y in range(34, 44):
    P(23 if y % 2 else 22, y, WHITE if y % 2 else FRILL)
    P(44 if y % 2 else 45, y, WHITE if y % 2 else FRILL)
for x in range(23, 45):
    P(x, 44, WHITE); P(x, 45, WHITE if x % 2 else FRILL)
R(26, 38, 42, 39, FRILL)                         # apron seam
# heart pocket
for x, y in ((31, 40), (32, 40), (35, 40), (36, 40), (30, 41), (31, 41), (32, 41), (33, 41),
             (34, 41), (35, 41), (36, 41), (37, 41), (31, 42), (32, 42), (33, 42), (34, 42),
             (35, 42), (36, 42), (32, 43), (33, 43), (34, 43), (35, 43)):
    P(x, y, PINK)

# ---- arms with puff sleeves + white cuffs
# left arm: hand on hip-ish, sticking out
R(10, 28, 14, 32, ORANGE)
R(12, 31, 15, 34, DRESS); P(14, 30, DRESS)       # puff sleeve
R(9, 28, 11, 32, WHITE)                          # cuff
R(7, 29, 9, 31, ORANGE)                          # hand
# right arm: holding up a tea tray
R(54, 24, 58, 28, ORANGE)
R(53, 27, 56, 31, DRESS); P(56, 27, DRESS)       # puff sleeve
R(57, 22, 61, 26, ORANGE)
R(57, 21, 61, 22, WHITE)                         # cuff
# tray
R(52, 19, 68, 20, SILVER); R(53, 20, 67, 21, SILVER_D)
# teacup
R(57, 14, 63, 19, WHITE); R(58, 14, 62, 15, TEA)
R(57, 18, 63, 19, FRILL)
P(63, 15, WHITE); P(64, 16, WHITE); P(63, 17, WHITE)   # handle
R(58, 16, 62, 17, PINK)                          # cup stripe
# steam
for x, y in ((59, 12), (60, 11), (59, 10), (61, 9), (62, 8), (61, 7)): P(x, y, (210, 205, 200))

# ---- floating hearts & sparkles
def heart(x, y, c):
    for dx, dy in ((0, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (2, 1), (3, 1), (0, 2), (1, 2), (2, 2), (1, 3)):
        P(x + dx, y + dy, c)
heart(5, 8, PINK); heart(64, 34, PINK); heart(8, 42, (240, 170, 185))
for sx, sy in ((30, 4), (4, 22), (66, 46)):
    P(sx, sy, ORANGE); P(sx - 1, sy, ORANGE_L); P(sx + 1, sy, ORANGE_L); P(sx, sy - 1, ORANGE_L); P(sx, sy + 1, ORANGE_L)

img.resize((W * SCALE, H * SCALE), Image.NEAREST).save(OUT)
print("wrote", OUT)
