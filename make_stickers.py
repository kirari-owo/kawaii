"""A set of Clawd pixel-art sticker emotes. Writes stickers/*.png (512x512, transparent) and stickers/sheet.png."""
import os
from PIL import Image, ImageDraw, ImageFont, ImageFilter

OUT = "stickers"
A = 64                    # art canvas, in art pixels
SCALE = 8                 # art pixel -> output px (512x512)
FONT = ImageFont.truetype("/usr/share/fonts/opentype/unifont/unifont.otf", 16)
TXT_SCALE = 4

ORANGE = (217, 119, 87, 255)
ORANGE_D = (191, 98, 70, 255)
ORANGE_L = (232, 146, 115, 255)
EYE = (30, 24, 20, 255)
WHITE = (255, 253, 250, 255)
BLUSH = (240, 150, 150, 255)
PINK = (238, 120, 150, 255)
RED = (214, 60, 60, 255)
BLUE = (110, 170, 230, 255)
BLUE_L = (170, 210, 245, 255)
GOLD = (240, 196, 80, 255)
GREEN = (90, 170, 90, 255)
GREEN_D = (60, 130, 70, 255)
NAVY = (60, 70, 130, 255)
GREY = (150, 150, 160, 255)
SHADOW = (0, 0, 0, 40)


class Art:
    def __init__(self):
        self.img = Image.new("RGBA", (A, A), (0, 0, 0, 0))
        self.px = self.img.load()
        self.dy = 0

    def P(self, x, y, c):
        y += self.dy
        if 0 <= x < A and 0 <= y < A: self.px[x, y] = c

    def R(self, x0, y0, x1, y1, c):
        for y in range(y0, y1):
            for x in range(x0, x1): self.P(x, y, c)

    def pts(self, pts, c):
        for x, y in pts: self.P(x, y, c)

    # Clawd: body x 12..52, y 12..36, legs to 44; arms at y 24..28
    def body(self, left_arm=True, right_arm=True, legs=True):
        self.R(12, 12, 52, 36, ORANGE)
        self.R(12, 12, 52, 13, ORANGE_L)
        self.R(12, 35, 52, 36, ORANGE_D)
        if legs:
            for lx in (16, 24, 36, 44): self.R(lx, 36, lx + 4, 44, ORANGE)
        if left_arm: self.R(8, 24, 12, 28, ORANGE)
        if right_arm: self.R(52, 24, 56, 28, ORANGE)

    def eyes(self, dx=0):
        for ex in (20, 40): self.R(ex + dx, 16, ex + dx + 4, 24, EYE)

    def blush(self, big=False):
        for bx in (14, 46):
            self.R(bx, 25, bx + 4, 27 + big, BLUSH)

    def heart(self, x, y, c=PINK):
        self.pts([(x + a, y + b) for a, b in ((0, 0), (1, 0), (3, 0), (4, 0), (-1, 1), (0, 1), (1, 1), (2, 1), (3, 1),
                  (4, 1), (5, 1), (0, 2), (1, 2), (2, 2), (3, 2), (4, 2), (1, 3), (2, 3), (3, 3), (2, 4))], c)

    def sparkle(self, x, y, c=GOLD):
        self.pts([(x, y), (x - 1, y), (x + 1, y), (x, y - 1), (x, y + 1)], c)

    def glyph(self, ch, x, y, c, size=16):
        f = FONT if size == 16 else ImageFont.truetype(FONT.path, size)
        m = Image.new("L", (size + 4, size + 4), 0)
        ImageDraw.Draw(m).text((0, 0), ch, font=f, fill=255)
        for gy in range(m.height):
            for gx in range(m.width):
                if m.getpixel((gx, gy)) > 128: self.P(x + gx, y + gy, c)

    def shadow(self):
        d, self.dy = self.dy, 0
        self.R(14, 45, 50, 47, SHADOW)
        self.dy = d


# ---------------------------------------------------------------- stickers
def hello(a):
    a.body(right_arm=False)
    a.R(52, 24, 60, 28, ORANGE); a.R(56, 12, 60, 24, ORANGE)       # raised arm
    for x, y in ((62, 10), (63, 9), (62, 14), (63, 14), (61, 6), (62, 5), (54, 8), (53, 7)): a.P(x, y, GOLD)
    a.eyes(); a.blush()
    return "你好呀"

def yay(a):
    a.dy = -3
    a.body(left_arm=False, right_arm=False)
    a.R(4, 24, 12, 28, ORANGE); a.R(4, 12, 8, 24, ORANGE); a.R(52, 24, 60, 28, ORANGE); a.R(56, 12, 60, 24, ORANGE)
    for ex in (20, 40):                                            # ^ ^ eyes
        a.pts([(ex, 21), (ex + 1, 20), (ex + 1, 19), (ex + 2, 18), (ex + 3, 18), (ex + 4, 19), (ex + 4, 20), (ex + 5, 21),
               (ex, 22), (ex + 5, 22), (ex + 2, 17), (ex + 3, 17)], EYE)
    a.blush()
    a.R(30, 27, 34, 29, EYE); a.R(31, 29, 33, 30, RED)            # open mouth
    for (x, y), c in zip([(4, 6), (16, 3), (30, 2), (46, 4), (60, 6), (3, 18), (61, 18), (24, 6), (38, 7)],
                         [GOLD, PINK, BLUE, GREEN, GOLD, PINK, BLUE, GOLD, PINK]):
        a.R(x, y, x + 2, y + 2, c)
    a.dy = 0
    a.shadow()
    return "好耶！"

def cry(a):
    a.body(left_arm=False, right_arm=False)
    a.R(8, 27, 12, 31, ORANGE); a.R(52, 27, 56, 31, ORANGE)        # drooped arms
    for ex in (20, 40):                                            # T T eyes
        a.R(ex - 2, 17, ex + 6, 19, EYE); a.R(ex + 1, 19, ex + 3, 23, EYE)
        for y in range(23, 46): a.R(ex + 1, y, ex + 3, y + 1, BLUE if y % 3 else BLUE_L)
    a.R(14, 45, 26, 47, BLUE); a.R(38, 45, 50, 47, BLUE)          # puddles
    a.pts([(30, 29), (31, 28), (32, 28), (33, 28), (34, 29)], EYE)  # wobbly mouth
    return "呜呜呜"

def angry(a):
    a.body()
    a.eyes()
    for i in range(5):                                             # cut the eye tops into a frown
        a.R(20, 16, 20 + 4 - i, 17 + i // 2, ORANGE) if False else None
    a.pts([(20, 16), (21, 16), (22, 16), (20, 17), (21, 17), (20, 18)], ORANGE)
    a.pts([(43, 16), (42, 16), (41, 16), (43, 17), (42, 17), (43, 18)], ORANGE)
    a.R(17, 13, 20, 14, EYE); a.pts([(20, 14), (21, 14), (22, 15), (23, 15)], EYE)    # brows
    a.R(44, 13, 47, 14, EYE); a.pts([(43, 14), (42, 14), (41, 15), (40, 15)], EYE)
    a.R(28, 29, 36, 30, EYE)                                       # flat mouth
    # anger mark
    for x, y in ((54, 3), (55, 3), (56, 4), (56, 5), (59, 3), (60, 3), (58, 4), (58, 5),
                 (54, 9), (55, 9), (56, 8), (56, 7), (59, 9), (60, 9), (58, 8), (58, 7)):
        a.P(x, y, RED)
    for x0, y0 in ((2, 10), (5, 6)):                               # steam puffs
        a.R(x0, y0, x0 + 3, y0 + 2, GREY)
    a.shadow()
    return "气鼓鼓"

def night(a):
    a.body()
    for ex in (20, 40):                                            # closed eyes: u
        a.pts([(ex, 19), (ex, 20), (ex + 1, 21), (ex + 2, 21), (ex + 3, 21), (ex + 4, 20), (ex + 4, 19)], EYE)
    a.blush()
    # nightcap
    a.R(12, 9, 52, 12, WHITE)
    a.R(16, 5, 48, 9, NAVY); a.R(24, 2, 44, 5, NAVY); a.R(36, 0, 46, 2, NAVY)
    a.R(46, 0, 50, 4, NAVY); a.R(50, 2, 54, 7, NAVY)
    a.R(53, 6, 57, 10, WHITE)                                      # pompom
    for x, y in ((22, 6), (32, 3), (30, 7), (40, 6)): a.P(x, y, GOLD)
    a.glyph("Z", 2, 12, BLUE, 16); a.glyph("z", 0, 2, BLUE, 12)
    a.shadow()
    return "晚安"

def huh(a):
    a.body()
    a.R(20, 18, 24, 22, EYE)                                       # small eye
    a.R(40, 16, 44, 24, EYE)
    a.R(30, 29, 33, 30, EYE)
    a.glyph("?", 50, -2, NAVY, 24); a.glyph("?", 2, 0, NAVY, 16); a.glyph("?", 56, 16, NAVY, 12)
    a.shadow()
    return "？？？"

def love(a):
    a.body(left_arm=False, right_arm=False)
    a.R(8, 24, 12, 28, ORANGE); a.R(52, 24, 56, 28, ORANGE)
    for ex in (19, 39):                                            # heart eyes
        a.pts([(ex + i, ex and 0) for i in ()], PINK)
        a.R(ex, 17, ex + 2, 19, PINK); a.R(ex + 3, 17, ex + 5, 19, PINK)
        a.R(ex - 1 + 1, 19, ex + 5, 21, PINK); a.R(ex + 1, 21, ex + 4, 22, PINK); a.P(ex + 2, 22, PINK)
        a.P(ex - 1, 18, PINK); a.P(ex + 5, 18, PINK); a.P(ex - 1, 19, PINK); a.P(ex + 5, 19, PINK)
    a.blush()
    # big heart held in front
    big = [(x, y) for y in range(9) for x in range(13)
           if (y == 0 and x in (2, 3, 4, 8, 9, 10)) or (y == 1 and x not in (0, 6, 12)) or (2 <= y <= 3)
           or (y >= 4 and y - 4 <= x <= 12 - (y - 4))]
    a.pts([(26 + x, 27 + y) for x, y in big], RED)
    a.pts([(28, 28), (29, 28), (28, 29)], (255, 200, 200, 255))
    for x, y in ((6, 6), (54, 4)): a.heart(x, y)
    a.heart(58, 14, (245, 170, 190, 255))
    a.shadow()
    return "爱你"

def roger(a):
    a.body(right_arm=False)
    a.R(52, 24, 60, 28, ORANGE); a.R(56, 10, 60, 24, ORANGE)      # salute
    a.R(48, 9, 60, 12, ORANGE)
    a.eyes(); a.blush()
    a.pts([(30, 28), (31, 29), (32, 29), (33, 29), (34, 28)], EYE)
    # green check mark
    for i in range(4): a.R(4 + i, 4 + i, 6 + i, 6 + i, GREEN)
    for i in range(8): a.R(8 + i, 6 - i + 1, 10 + i, 8 - i + 1, GREEN)
    a.sparkle(20, 4); a.sparkle(58, 4)
    a.shadow()
    return "收到！"

def shock(a):
    a.dy = -2
    a.body(left_arm=False, right_arm=False)
    a.R(6, 16, 12, 20, ORANGE); a.R(52, 16, 58, 20, ORANGE)        # arms flung out
    for ex in (19, 39):                                            # white eyes, tiny pupils
        a.R(ex, 15, ex + 6, 24, EYE); a.R(ex + 1, 16, ex + 5, 23, WHITE); a.R(ex + 2, 18, ex + 4, 20, EYE)
    a.R(30, 27, 34, 32, EYE)                                       # O mouth
    for x in range(16, 50, 4): a.R(x, 13, x + 1, 15, (120, 110, 180, 255))   # gloom lines
    a.dy = 0
    for x, y in ((3, 8), (4, 6), (5, 4), (60, 8), (59, 6), (58, 4), (2, 22), (61, 22)): a.P(x, y, EYE)
    a.shadow()
    return "震惊"

def shy(a):
    a.body(left_arm=False, right_arm=False)
    a.R(12, 22, 18, 26, ORANGE_D); a.R(46, 22, 52, 26, ORANGE_D)  # paws on cheeks
    for ex, flip in ((20, False), (40, True)):                     # > < eyes
        pts = [(0, 0), (1, 1), (2, 2), (3, 3), (2, 4), (1, 5), (0, 6), (1, 0), (2, 1), (3, 2), (4, 3), (3, 4), (2, 5), (1, 6)]
        a.pts([(ex + (4 - x if flip else x), 17 + y) for x, y in pts], EYE)
    a.R(14, 26, 22, 29, BLUSH); a.R(42, 26, 50, 29, BLUSH)
    for x in (15, 18, 21, 43, 46, 49): a.P(x, 27, (220, 110, 110, 255))
    a.pts([(31, 30), (32, 31), (33, 30)], EYE)
    a.heart(4, 8); a.heart(54, 6, (245, 170, 190, 255)); a.sparkle(30, 5, PINK)
    a.shadow()
    return "害羞"

def melon(a):
    a.body(right_arm=False)
    for ex in (20, 40):                                            # eyes glancing sideways
        a.R(ex, 16, ex + 4, 24, EYE); a.R(ex, 17, ex + 2, 19, WHITE)
    a.pts([(30, 29), (31, 29), (32, 30), (33, 30)], EYE)
    a.R(52, 24, 60, 28, ORANGE); a.R(56, 18, 60, 24, ORANGE)
    cx, top, rx, ry = 57, 6, 8.5, 11
    for y in range(top, top + 12):
        for x in range(cx - 9, cx + 10):
            r = ((x - cx) / rx) ** 2 + ((y - top) / ry) ** 2
            if r <= 1: a.P(x, y, GREEN_D if r > 0.72 else (WHITE if r > 0.55 else RED))
    for x, y in ((53, 8), (57, 9), (61, 8), (55, 11), (59, 11), (57, 13)): a.P(x, y, EYE)
    a.shadow()
    return "吃瓜中"

def flat(a):
    # Clawd lying on its back, legs in the air
    a.R(12, 22, 52, 40, ORANGE); a.R(12, 39, 52, 40, ORANGE_D); a.R(12, 22, 52, 23, ORANGE_L)
    for lx in (16, 24, 36, 44): a.R(lx, 16, lx + 4, 22, ORANGE)
    a.R(8, 34, 12, 38, ORANGE); a.R(52, 34, 56, 38, ORANGE)
    for ex in (20, 40): a.R(ex, 29, ex + 5, 31, EYE)               # - - eyes
    a.R(30, 34, 34, 35, EYE)
    a.blush()
    a.R(12, 40, 52, 42, SHADOW)
    for x, y in ((6, 8), (9, 5), (12, 2)): a.R(x, y, x + 2, y + 2, BLUE_L)   # sigh bubbles
    return "躺平了"


STICKERS = [("hello", hello), ("yay", yay), ("cry", cry), ("angry", angry), ("goodnight", night), ("huh", huh),
            ("love", love), ("roger", roger), ("shock", shock), ("shy", shy), ("melon", melon), ("flat", flat)]


def caption(text):
    w = int(FONT.getlength(text)) + 4
    t = Image.new("RGBA", (w, 20), (0, 0, 0, 0))
    ImageDraw.Draw(t).text((2, 2), text, font=FONT, fill=EYE)
    outline = t.getchannel("A").filter(ImageFilter.MaxFilter(3))
    bg = Image.new("RGBA", t.size, WHITE); bg.putalpha(outline)
    return Image.alpha_composite(bg, t)


def render(fn):
    a = Art()
    text = fn(a)
    art = a.img
    # white sticker border around the art
    mask = art.getchannel("A").point(lambda v: 255 if v > 60 else 0).filter(ImageFilter.MaxFilter(3))
    border = Image.new("RGBA", art.size, WHITE); border.putalpha(mask)
    art = Image.alpha_composite(border, art)
    big = Image.new("RGBA", (A * SCALE, A * SCALE), (0, 0, 0, 0))
    big.alpha_composite(art.resize(big.size, Image.NEAREST), (0, 0))
    cap = caption(text)
    cap = cap.resize((cap.width * TXT_SCALE, cap.height * TXT_SCALE), Image.NEAREST)
    big.alpha_composite(cap, ((big.width - cap.width) // 2, big.height - cap.height - 4))
    return big


os.makedirs(OUT, exist_ok=True)
tiles = []
for i, (name, fn) in enumerate(STICKERS, 1):
    im = render(fn)
    im.save(os.path.join(OUT, f"{i:02d}_{name}.png"))
    tiles.append(im)

cols, tile = 4, 256
sheet = Image.new("RGBA", (cols * tile, (len(tiles) + cols - 1) // cols * tile), (244, 239, 230, 255))
for i, im in enumerate(tiles):
    sheet.alpha_composite(im.resize((tile, tile), Image.NEAREST), (i % cols * tile, i // cols * tile))
sheet.convert("RGB").save(os.path.join(OUT, "sheet.png"))
print("wrote", len(tiles), "stickers")
