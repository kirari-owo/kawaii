"""Clawd in a bunny-girl outfit, as pixel art. Writes clawd_bunny.png (upscaled, nearest-neighbour)."""
import sys
from PIL import Image

OUT = sys.argv[1] if len(sys.argv) > 1 else "clawd_bunny.png"
W, H, SCALE = 72, 72, 16
OY = 10                     # shift the drawing down to center it in the square

BG = (246, 236, 240)
DOT = (236, 220, 228)
ORANGE = (217, 119, 87)
ORANGE_D = (191, 98, 70)
ORANGE_L = (232, 146, 115)
EYE = (30, 24, 20)
WHITE = (255, 253, 250)
FRILL = (226, 220, 214)
SUIT = (34, 30, 40)
SUIT_L = (72, 66, 86)
EAR_IN = (240, 160, 175)
RED = (204, 52, 68)
RED_D = (150, 36, 52)
BLUSH = (240, 150, 150)
PINK = (238, 140, 160)
CARROT = (240, 140, 50)
CARROT_D = (205, 105, 35)
LEAF = (110, 175, 90)
LEAF_D = (75, 135, 65)
GOLD = (236, 196, 90)
SHADOW = (228, 210, 218)

img = Image.new("RGB", (W, H), BG)
px = img.load()

def P(x, y, c):
    y += OY
    if 0 <= x < W and 0 <= y < H: px[x, y] = c
def R(x0, y0, x1, y1, c):           # inclusive-exclusive rectangle
    for y in range(y0, y1):
        for x in range(x0, x1): P(x, y, c)

for y in range(2 - 16, H, 8):
    for x in range(2 + (y // 8 % 2) * 4, W, 8): P(x, y, DOT)

R(14, 49, 58, 51, SHADOW); R(17, 51, 55, 52, SHADOW)

# ---- bunny ears on a headband (left one bent)
def ear(x0, top, bent):
    R(x0, top, x0 + 6, 17, SUIT)
    R(x0 + 2, top + 2, x0 + 4, 16, EAR_IN)
    R(x0 + 1, top - 1, x0 + 5, top, SUIT)        # rounded tip
    P(x0 + 1, top + 1, SUIT_L)
    if bent:                                      # fold the top over
        R(x0, top, x0 + 6, top + 5, BG)
        R(x0 + 1, top - 1, x0 + 5, top, BG)
        R(x0 - 5, top + 2, x0 + 3, top + 6, SUIT)
        R(x0 - 6, top + 3, x0 - 5, top + 5, SUIT)
        R(x0 - 3, top + 3, x0 + 1, top + 5, EAR_IN)
ear(21, 2, True)
ear(41, 1, False)
R(16, 15, 52, 17, SUIT)                           # headband
R(16, 15, 52, 16, SUIT_L)

# ---- Clawd body
BX0, BX1, BY0 = 14, 54, 17
R(BX0, BY0, BX1, BY0 + 23, ORANGE)
R(BX0, BY0, BX1, BY0 + 1, ORANGE_L)
R(16, 16, 52, 17, SUIT)                           # band sits on the head

# ---- face
for ex in (22, 42):
    R(ex, 20, ex + 4, 28, EYE)
    P(ex + 1, 21, WHITE); P(ex + 2, 21, WHITE); P(ex + 1, 22, WHITE)
    P(ex + 2, 26, (70, 60, 70))
P(46, 22, ORANGE); R(42, 22, 46, 26, EYE); R(42, 23, 46, 25, ORANGE)  # right eye winks: ">"
R(42, 20, 46, 28, ORANGE)
for x, y in ((42, 21), (43, 22), (44, 23), (45, 24), (44, 25), (43, 26), (42, 27)): P(x, y, EYE)
for x, y in ((43, 21), (44, 22), (45, 23), (46, 24), (45, 25), (44, 26), (43, 27)): P(x, y, EYE)
for bx in (17, 47):
    R(bx, 27, bx + 4, 29, BLUSH); P(bx + 1, 27, (248, 180, 176))
for x, y in ((32, 27), (33, 28), (34, 27), (35, 28), (36, 27)): P(x, y, EYE)

# ---- collar + red bow tie
R(26, 30, 42, 32, WHITE); P(25, 30, WHITE); P(42, 30, WHITE)
R(29, 30, 33, 33, RED); R(35, 30, 39, 33, RED)
P(29, 30, RED_D); P(38, 30, RED_D); P(29, 32, RED_D); P(38, 32, RED_D)
R(33, 30, 35, 33, RED_D)

# ---- leotard with a sweetheart neckline
neck = {31: 35, 32: 36, 33: 36, 34: 36, 35: 36, 36: 35}
for x in range(BX0, BX1):
    top = neck.get(x, 34)
    R(x, top, x + 1, 44, SUIT)
    P(x, top, SUIT_L)
# high-cut leg holes
for i in range(4):
    R(BX0, 40 + i, BX0 + 2 + i * 2, 41 + i, ORANGE)
    R(BX1 - 2 - i * 2, 40 + i, BX1, 41 + i, ORANGE)
# gold buttons
P(34, 41, GOLD)

# ---- fluffy tail peeking out on the right
for x, y in ((54, 39), (55, 39), (56, 39), (53, 40), (54, 40), (55, 40), (56, 40), (57, 40),
             (54, 41), (55, 41), (56, 41), (57, 41), (55, 42), (56, 42)):
    P(x, y, WHITE)
P(56, 41, FRILL); P(57, 41, FRILL); P(56, 42, FRILL)

# ---- short stubby legs
for lx in (18, 26, 38, 46):
    R(lx, 44, lx + 4, 49, ORANGE)
    R(lx, 48, lx + 4, 49, ORANGE_D)

# ---- arms + white cuffs
# left arm: hand on hip
R(10, 31, 14, 35, ORANGE)
R(8, 31, 10, 35, WHITE); P(9, 31, FRILL); P(9, 34, FRILL)
P(10, 35, GOLD)                                   # cufflink
R(6, 32, 8, 34, ORANGE)
# right arm: raised, holding a carrot
R(54, 26, 58, 30, ORANGE)
R(57, 22, 61, 27, ORANGE)
R(57, 21, 61, 23, WHITE); P(58, 23, GOLD)
# carrot (wide end up, tip tucked into the hand)
for y, (x0, x1) in zip(range(11, 22), [(57, 62), (57, 62), (57, 62), (57, 62), (58, 62), (58, 62),
                                         (58, 61), (58, 61), (59, 61), (59, 61), (59, 60)]):
    R(x0, y, x1, y + 1, CARROT)
    P(x1 - 1, y, CARROT_D)
for x, y in ((58, 13), (59, 13), (59, 16), (60, 16)): P(x, y, CARROT_D)
for x, y in ((59, 10), (60, 10), (58, 9), (59, 9), (61, 9), (57, 8), (58, 8), (61, 8), (62, 8), (59, 7), (62, 7)):
    P(x, y, LEAF)
P(60, 9, LEAF_D); P(58, 7, LEAF_D)
R(57, 21, 61, 23, WHITE); P(58, 23, GOLD)   # cuff over the carrot tip

# ---- hearts & sparkles
def heart(x, y, c):
    for dx, dy in ((0, 0), (2, 0), (-1, 1), (0, 1), (1, 1), (2, 1), (3, 1), (0, 2), (1, 2), (2, 2), (1, 3)):
        P(x + dx, y + dy, c)
heart(5, 12, PINK); heart(64, 32, PINK); heart(6, 42, (240, 170, 185))
for sx, sy in ((33, 5), (4, 24), (66, 47), (51, 6)):
    P(sx, sy, GOLD); P(sx - 1, sy, ORANGE_L); P(sx + 1, sy, ORANGE_L); P(sx, sy - 1, ORANGE_L); P(sx, sy + 1, ORANGE_L)

img.resize((W * SCALE, H * SCALE), Image.NEAREST).save(OUT)
print("wrote", OUT)
