"""Clawd x 呆头鸟 (礼越) — kinetic-typography fan animation, 16:9, 0:00-1:12.

Lyrics are typeset from text the user supplied. The song audio is not in the repo; pass its path:
  python3 make_ktv.py song.mp3 out.mp4
  python3 make_ktv.py song.mp3 preview sheet.png t1 t2 ...
"""
import json, math, os, subprocess, sys
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter, ImageFont

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
from make_story import clamp, seg, ease_out, ease_in, ease_io, back_out, lerp, mix, G, EPAL

W, H, FPS = 1920, 1080, 30
END = 72.6
HERE = os.path.dirname(os.path.abspath(__file__))
BEATS = np.array(json.load(open(os.path.join(HERE, "beats.json")))["beats"])
BEAT = 0.4412
E = BEAT / 2                       # one sung character ≈ an eighth note
# lyrics (one line per row) are supplied locally in lyrics.txt and kept out of the repo
LYR = [l.strip() for l in open(os.path.join(HERE, "lyrics.txt"), encoding="utf-8") if l.strip()]
L = [15.27, 18.78, 22.32, 25.65, 29.46, 33.18, 36.66, 40.35, 43.95, 47.43, 51.06, 54.15, 58.14, 61.62, 65.13, 68.28]
def ct(i, k): return L[i] + k * E          # when char k of line i is sung

# palette
DARK, PAPER, INK = (26, 25, 24), (234, 231, 226), (30, 26, 24)
OR, OR_D = (217, 119, 87), (140, 64, 44)
BLUE, BLUE_D = (47, 91, 234), (24, 48, 140)
YEL, YEL_D = (244, 196, 78), (176, 124, 30)
RED, RED_D = (214, 52, 60), (120, 24, 30)
PINK, GREEN, WHITE, CREAM = (238, 128, 150), (92, 176, 112), (255, 255, 255), (250, 246, 238)
GRAY = (150, 144, 138)

FB = "/usr/share/fonts/opentype/noto/NotoSansCJK-Bold.ttc"
FR = "/usr/share/fonts/opentype/noto/NotoSansCJK-Regular.ttc"
FM = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
FS = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
@lru_cache(None)
def F(size, kind="b"):
    if kind == "m": return ImageFont.truetype(FM, size)
    if kind == "s": return ImageFont.truetype(FS, size)
    return ImageFont.truetype(FB if kind == "b" else FR, size, index=2)

# ------------------------------------------------------------------ easing / beat helpers
def beat_phase(t):
    i = int(np.searchsorted(BEATS, t, side="right") - 1)
    if i < 0: return (t / BEAT) % 1, -1
    b0 = BEATS[i]; b1 = BEATS[i + 1] if i + 1 < len(BEATS) else b0 + BEAT
    return clamp((t - b0) / (b1 - b0)), i
def pulse(t, k=7.0): return math.exp(-beat_phase(t)[0] * k)
def breathe(t, amp=5): return amp * math.sin(2 * math.pi * t / (BEAT * 8))   # slow: once per two bars

# ------------------------------------------------------------------ text sprites
@lru_cache(None)
def glyph(text, size, color, ext=0, extc=None, stroke=0, strokec=None, kind="b", glow=0):
    f = F(size, kind)
    l, t0, r, b = f.getbbox(text, stroke_width=stroke)
    pad = int(size * 0.12) + ext + glow * 2 + stroke
    w, h = r - l + 2 * pad, b - t0 + 2 * pad
    im = Image.new("RGBA", (w, h), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    ox, oy = pad - l, pad - t0
    for k in range(ext, 0, -1):
        d.text((ox + k * 0.75, oy + k), text, font=f, fill=extc, stroke_width=stroke, stroke_fill=extc)
    d.text((ox, oy), text, font=f, fill=color, stroke_width=stroke, stroke_fill=strokec or color)
    if glow:
        g = im.filter(ImageFilter.GaussianBlur(glow)); out = Image.new("RGBA", im.size, (0, 0, 0, 0))
        out.alpha_composite(g); out.alpha_composite(g); out.alpha_composite(im); im = out
    return im

def put(img, im, cx, cy, scale=1.0, alpha=1.0, rot=0.0):
    if alpha <= 0.01 or scale <= 0.02: return
    if abs(scale - 1) > 1e-3:
        im = im.resize((max(1, int(im.width * scale)), max(1, int(im.height * scale))), Image.BICUBIC)
    if abs(rot) > 0.1: im = im.rotate(rot, expand=True, resample=Image.BICUBIC)
    if alpha < 0.999:
        im = im.copy(); im.putalpha(im.getchannel("A").point(lambda v: int(v * alpha)))
    img.paste(im, (int(cx - im.width / 2), int(cy - im.height / 2)), im)

def anim(t, t0, kind="pop"):
    """-> (scale, alpha, dx, dy, rot) for a sprite that appears at t0."""
    if t < t0: return 0, 0, 0, 0, 0
    x = seg(t, t0, t0 + (0.12 if kind == "stamp" else 0.2))
    if kind == "stamp": return lerp(1.9, 1.0, ease_out(x)), clamp(x * 3), 0, 0, 0
    if kind == "drop": return 1, clamp(x * 3), 0, -(1 - back_out(x, 2.2)) * 160, 0
    if kind == "rise": return 1, clamp(x * 3), 0, (1 - ease_out(x)) * 120, 0
    if kind == "slideL": return 1, clamp(x * 3), -(1 - ease_out(x)) * 300, 0, 0
    if kind == "slideR": return 1, clamp(x * 3), (1 - ease_out(x)) * 300, 0, 0
    if kind == "fade": return 1, ease_out(x), 0, 0, 0
    return 0.35 + 0.65 * back_out(x), clamp(x * 3), 0, 0, 0

def chars(img, t, i, k0, k1, x, y, size, color, ext=0, extc=None, kind="pop", gap=1.02, vertical=False,
          jitter=0.0, stroke=0, strokec=None, glow=0, delay=0.0, rots=None, offsets=None, alpha=1.0):
    """Typeset chars k0..k1-1 of lyric line i, each popping in when it is sung. Returns end x."""
    s = LYR[i][k0:k1]
    for j, ch in enumerate(s):
        k = k0 + j
        sc, a, dx, dy, r = anim(t, ct(i, k) + delay, kind)
        if a <= 0: continue
        px = x + (0 if vertical else j * size * gap); py = y + (j * size * gap if vertical else 0)
        if offsets: px += offsets[j][0]; py += offsets[j][1]
        if jitter: px += jitter * math.sin(t * 47 + k * 3.1); py += jitter * math.cos(t * 53 + k * 1.7)
        if kind == "stamp" and sc > 1.05:          # motion ghost
            put(img, glyph(ch, size, color, ext, extc, stroke, strokec, glow=glow), px + size / 2, py + size / 2, sc * 1.25, a * 0.25)
        put(img, glyph(ch, size, color, ext, extc, stroke, strokec, glow=glow), px + size / 2 + dx, py + size / 2 + dy,
            sc, a * alpha, (rots[j] if rots else 0) + r)
    return x + len(s) * size * gap

def tag(img, t, t0, text, x, y, size, bg=BLUE, fg=WHITE):
    """Blue speech-tag label like a chat chip."""
    sc, a, *_ = anim(t, t0, "pop")
    if a <= 0: return
    g = glyph(text, size, fg)
    w, h = g.width + 30, g.height + 6
    im = Image.new("RGBA", (w + 14, h + 24), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 6, w, h + 6], radius=18, fill=tuple(int(c * 0.6) for c in bg))
    d.rounded_rectangle([0, 0, w, h], radius=18, fill=bg)
    d.polygon([(18, h - 2), (44, h - 2), (14, h + 20)], fill=bg)
    im.paste(g, (15, 3), g)
    put(img, im, x + w / 2, y + h / 2, sc, a)

# ------------------------------------------------------------------ Clawd (with mirrored eyes)
G["gt"] = ["#.......", "###.....", "..###...", "....###.", "..###...", "###.....", "#.......", "........"]
G["none"] = ["........"] * 8
SHADES = ["########", "########", "########", "........", "........", "........", "........", "........"]

def clawd(d, cx, feet, U=40, sx=1.0, sy=1.0, eyes="normal", ex=0.0, ey=0.0, blink=1.0, blush=0.0,
          larm=None, rarm=None, color=OR, ahoge=0.0, bow=0.0, t=0.0):
    def P(u, v): return cx + (u - 6) * U * sx, feet - (8 - v) * U * sy
    def R(u0, v0, u1, v1, c):
        x0, y0 = P(u0, v0); x1, y1 = P(u1, v1)
        d.rectangle([round(min(x0, x1)), round(y0), round(max(x0, x1)) - 1, round(y1) - 1], fill=c)
    shade = tuple(int(c * 0.86) for c in color)
    for lu in (2, 4, 7, 9): R(lu, 6, lu + 1, 8, color)
    R(1, 0, 11, 6, color); R(1, 5.6, 11, 6, shade)
    for side, arm in ((-1, larm), (1, rarm)):
        if arm is None:
            R(0, 3, 1, 4, color) if side < 0 else R(11, 3, 12, 4, color); continue
        ang, ln = arm if isinstance(arm, tuple) else (arm, 3.0)
        px, py = P(6 + side * 5.2, 3.5)
        a = math.radians(ang); ux, uy = side * math.cos(a) * sx, -math.sin(a); nx, ny = -uy, ux
        L_, T = ln * U, U * sy
        x0, y0 = px - ux * 0.5 * U, py - uy * 0.5 * U
        d.polygon([(x0 + nx * T / 2, y0 + ny * T / 2), (x0 + ux * L_ + nx * T / 2, y0 + uy * L_ + ny * T / 2),
                   (x0 + ux * L_ - nx * T / 2, y0 + uy * L_ - ny * T / 2), (x0 - nx * T / 2, y0 - ny * T / 2)], fill=color)
    g, q = G[eyes], U / 4
    bh = max(blink, 0.2)
    for k, eu in enumerate((3.5, 8.5)):
        ecx, ecy = P(eu + ex, 2 + ey)
        rows = g if k == 0 else [r[::-1] for r in g]
        for r, row in enumerate(rows):
            for c, ch in enumerate(row):
                if ch == ".": continue
                x0 = ecx + (c - 4) * q * sx; y0 = ecy + (r - 4) * q * sy * bh
                d.rectangle([round(x0), round(y0), max(round(x0), round(x0 + q * sx) - 1), max(round(y0), round(y0 + q * sy * bh) - 1)], fill=EPAL[ch])
    if blush > 0.02:
        bc = mix(color, (240, 110, 125), clamp(blush))
        R(1.9, 3.3, 3.5, 3.85, bc); R(8.5, 3.3, 10.1, 3.85, bc)
    top = feet - 8 * U * sy
    if ahoge > 0.05:
        sw = 8 * math.sin(t * 9) * ahoge
        d.line([(cx, top), (cx - 0.15 * U * ahoge + sw * 0.3, top - 0.75 * U * ahoge), (cx + 0.35 * U * ahoge + sw, top - 1.3 * U * ahoge),
                (cx + 0.05 * U * ahoge + sw, top - 1.75 * U * ahoge)], fill=color, width=max(3, int(0.35 * U * ahoge)), joint="curve")
    if bow > 0.05:
        bx, by, s = cx + 3 * U * sx, top + 0.1 * U, U * 0.9 * bow
        d.polygon([(bx, by), (bx - s, by - 0.6 * s), (bx - s, by + 0.6 * s)], fill=PINK)
        d.polygon([(bx, by), (bx + s, by - 0.6 * s), (bx + s, by + 0.6 * s)], fill=PINK)
        d.ellipse([bx - 0.25 * s, by - 0.25 * s, bx + 0.25 * s, by + 0.25 * s], fill=(214, 80, 110))
    return top

def heart_px(d, x, y, px, color=(226, 72, 96)):
    rows = [".##.##.", "#######", "#######", ".#####.", "..###..", "...#..."]
    if px < 1: return
    for r, row in enumerate(rows):
        for c, ch in enumerate(row):
            if ch == "#": d.rectangle([x + (c - 3.5) * px, y + (r - 3) * px, x + (c - 2.5) * px - 1, y + (r - 2) * px - 1], fill=color)

def sparkle(d, x, y, sz, color=YEL):
    if sz < 1.5: return
    d.polygon([(x, y - sz), (x + sz * 0.25, y - sz * 0.25), (x + sz, y), (x + sz * 0.25, y + sz * 0.25),
               (x, y + sz), (x - sz * 0.25, y + sz * 0.25), (x - sz, y), (x - sz * 0.25, y - sz * 0.25)], fill=color)

# ------------------------------------------------------------------ backgrounds & UI
@lru_cache(None)
def bg_solid(c, dots=True, dot_c=None, halftone=False):
    im = Image.new("RGB", (W, H), c); d = ImageDraw.Draw(im)
    if dots:
        dc = dot_c or tuple(max(0, v - 14) if sum(c) > 380 else min(255, v + 14) for v in c)
        for y in range(24, H, 40):
            for x in range(24, W, 40):
                r = 2
                if halftone:
                    r = 1 + 7 * max(0, 1 - math.hypot(x - W, y - 0) / 900)
                d.ellipse([x - r, y - r, x + r, y + r], fill=dc)
    return im

@lru_cache(None)
def bg_grad(c0, c1):
    a = np.linspace(0, 1, H)[:, None, None]
    arr = (np.array(c0)[None, None, :] * (1 - a) + np.array(c1)[None, None, :] * a).astype(np.uint8)
    return Image.fromarray(np.repeat(arr, W, axis=1), "RGB")

def window(d, x0, y0, x1, y1, title="", dark=False, fill=None):
    body = fill or ((30, 30, 32) if dark else (248, 246, 242)); bar = (44, 44, 48) if dark else (226, 222, 216)
    d.rounded_rectangle([x0 + 10, y0 + 12, x1 + 10, y1 + 12], radius=16, fill=(0, 0, 0))
    d.rounded_rectangle([x0, y0, x1, y1], radius=16, fill=body, outline=(20, 20, 20), width=3)
    d.rounded_rectangle([x0, y0, x1, y0 + 46], radius=16, fill=bar); d.rectangle([x0, y0 + 30, x1, y0 + 46], fill=bar)
    d.line([(x0, y0 + 46), (x1, y0 + 46)], fill=(20, 20, 20), width=3)
    for k, c in enumerate(((236, 96, 88), (240, 190, 70), (98, 196, 98))):
        d.ellipse([x0 + 20 + k * 30, y0 + 14, x0 + 38 + k * 30, y0 + 32], fill=c)
    if title: d.text(((x0 + x1) / 2, y0 + 23), title, font=F(22, "m"), fill=(120, 116, 110) if not dark else (160, 156, 150), anchor="mm")

def cursor(d, x, y, s=1.0):
    pts = [(0, 0), (0, 34), (9, 26), (16, 42), (23, 39), (16, 24), (28, 24)]
    d.polygon([(x + px * s, y + py * s) for px, py in pts], fill=(255, 255, 255), outline=(0, 0, 0))

def lattice(d, cx, cy, w, h, prog, color):
    """A Chinese window lattice (窗棂) that draws itself in as prog goes 0->1."""
    x0, y0, x1, y1 = cx - w / 2, cy - h / 2, cx + w / 2, cy + h / 2
    bars = [("r", x0, y0, x1, y1)]
    n = 4
    for k in range(1, n): bars.append(("v", x0 + w * k / n, y0, x0 + w * k / n, y1))
    for k in range(1, n): bars.append(("h", x0, y0 + h * k / n, x1, y0 + h * k / n))
    for k in range(n):
        for m in range(n):
            if (k + m) % 2 == 0:
                ax, ay = x0 + w * k / n, y0 + h * m / n; bars.append(("d", ax + w / n * 0.25, ay + h / n * 0.5, ax + w / n * 0.5, ay + h / n * 0.25))
    shown = int(len(bars) * prog + 0.999)
    for kind, a, b, c, e in bars[:shown]:
        if kind == "r": d.rectangle([a, b, c, e], outline=color, width=16)
        elif kind == "d":
            d.polygon([(a, b), (c, e), (2 * c - a, b), (c, 2 * b - e)], outline=color, width=8)
        else: d.line([(a, b), (c, e)], fill=color, width=10)

# ------------------------------------------------------------------ scenes
def sc_intro(img, d, t):
    img.paste(bg_solid(DARK), (0, 0)); d = ImageDraw.Draw(img)
    if t < 8.38:
        cmd = "claude"; n = int(seg(t, 0.8, 0.8 + 0.09 * len(cmd)) * len(cmd))
        d.text((160, 150), "$ " + cmd[:n], font=F(56, "m"), fill=(220, 214, 204), anchor="lm")
        if t > 2.2:
            a = ease_out(seg(t, 2.2, 2.5))
            x0, y0 = 160, 210 + (1 - a) * 20
            d.rounded_rectangle([x0, y0, 1760, y0 + 250], radius=14, outline=mix(DARK, OR, a), width=4)
            clawd(d, x0 + 150, y0 + 190, U=16, eyes="normal", blink=ms_blink(t, (3.4,)))
            d.text((x0 + 300, y0 + 70), "Claude Code", font=F(62, "s"), fill=mix(DARK, (240, 236, 228), a), anchor="lm")
            d.text((x0 + 300, y0 + 140), "春日模式 · 早安", font=F(40, "r"), fill=mix(DARK, GRAY, a), anchor="lm")
            d.text((x0 + 300, y0 + 200), "~/春天/河边", font=F(36, "r"), fill=mix(DARK, GRAY, a), anchor="lm")
        if t > 4.0:
            d.rounded_rectangle([160, 520, 1760, 660], radius=14, outline=(90, 86, 82), width=3)
            d.text((200, 590), ">", font=F(64, "m"), fill=OR, anchor="lm")
            msg = "出门走走吧"; n = int(seg(t, 4.4, 4.4 + 0.22 * len(msg)) * len(msg))
            d.text((270, 590), msg[:n], font=F(68), fill=(240, 236, 228), anchor="lm")
            if int(t * 2.5) % 2 == 0 or t < 6.0:
                cx = 270 + F(68).getlength(msg[:n]) + 8; d.rectangle([cx, 558, cx + 32, 622], fill=(240, 236, 228))
        if t > 6.6:
            sp = "·✢✳✶✻✽"[int(t * 10) % 6]
            d.text((180, 750), sp, font=F(48, "s"), fill=OR, anchor="lm")
            d.text((240, 750), "Thinking…", font=F(42, "m"), fill=GRAY, anchor="lm")
        if 6.55 < t < 6.75: d.rounded_rectangle([160, 520, 1760, 660], radius=14, outline=OR, width=6)
        return
    # 8.4 - 15.27: night before dawn, a window lattice draws itself on the beat; Clawd dozing
    k = (t - 8.38) / (15.27 - 8.38)
    img.paste(bg_grad(mix((14, 16, 34), (40, 48, 92), k * 0.6), mix((24, 26, 50), (180, 110, 110), ease_in(k))), (0, 0)); d = ImageDraw.Draw(img)
    for s in range(30):
        x = (s * 397) % W; y = (s * 211) % 600; tw = 0.5 + 0.5 * math.sin(t * 3 + s)
        d.rectangle([x, y, x + 3, y + 3], fill=mix((40, 44, 80), (230, 230, 255), tw * (1 - k)))
    _, bi = beat_phase(t); b0 = int(np.searchsorted(BEATS, 8.38))
    lattice(d, 1220, 520, 620, 620, clamp((bi - b0 + 1) / 14), (92, 60, 48))
    top = clawd(d, 560, 880 + breathe(t, 3), U=34, eyes="closed" if t < 14.6 else "wide", blink=1)
    if t < 14.6:
        for z in range(3):
            p = ((t - 8.4) * 0.5 + z / 3) % 1
            put(img, glyph("z", int(30 + 30 * p), (200, 200, 230), kind="s"), 560 + 160 + 90 * p, top - 30 - 120 * p, 1, 1 - p)
    else:
        put(img, glyph("!", 80, YEL, kind="s"), 560, top - 60, back_out(seg(t, 14.6, 14.8)), 1)

def ms_blink(t, times, w=0.08):
    for bt in times:
        if abs(t - bt) < w: return 0.15 + 0.85 * abs(t - bt) / w
    return 1.0

def sc0(img, d, t):   # 晨曦杳杳爬上窗棂翘
    k = seg(t, L[0], L[1])
    img.paste(bg_grad(mix((40, 48, 92), (110, 150, 210), k), mix((180, 110, 110), (252, 206, 150), k)), (0, 0)); d = ImageDraw.Draw(img)
    sy = lerp(1000, 520, ease_out(seg(t, L[0], L[0] + 2.6)))
    put(img, glow_disc(), 1220, sy)
    lattice(d, 1220, 520, 620, 620, 1, (92, 60, 48))
    chars(img, t, 0, 0, 2, 120, 120, 230, YEL, ext=14, extc=YEL_D, kind="rise", glow=0)
    chars(img, t, 0, 2, 4, 140, 400, 90, (240, 236, 250), kind="fade", alpha=0.8)
    for j in range(2):                                    # 爬上: climbing up
        kk = 4 + j; t0 = ct(0, kk)
        if t >= t0:
            y = lerp(900, 560 - j * 0, ease_out(seg(t, t0, t0 + 0.8)))
            put(img, glyph(LYR[0][kk], 120, WHITE, 8, (150, 120, 120)), 360 + j * 130, y, 1, clamp((t - t0) * 6))
    for j in range(3):                                    # 窗棂翘 sit in the panes
        kk = 6 + j; sc, a, *_ = anim(t, ct(0, kk), "pop")
        put(img, glyph(LYR[0][kk], 110, (92, 60, 48), 0), 1220 - 230 + j * 155, 290 + j * 155 - (40 if j == 2 else 0), sc, a, -12 if j == 2 else 0)
    clawd(d, 560, 880 + breathe(t, 3), U=34, eyes="happy" if t > L[0] + 1 else "wide", ex=0.4, ey=-0.3, blush=0.2)

@lru_cache(None)
def glow_disc():
    r = 300; im = Image.new("RGBA", (2 * r, 2 * r), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([r - 140, r - 140, r + 140, r + 140], fill=(255, 226, 150, 255))
    return Image.alpha_composite(im.filter(ImageFilter.GaussianBlur(60)), im)

def sc1(img, d, t):   # 你掩面轻笑像那晚风绕
    img.paste(bg_solid(PAPER, halftone=True), (0, 0)); d = ImageDraw.Draw(img)
    tag(img, t, ct(1, 0), "你", 110, 110, 110)
    chars(img, t, 1, 1, 3, 300, 120, 150, INK, ext=10, extc=OR, kind="stamp")
    if t > ct(1, 2) + 0.25:                               # a pink veil covers 掩面
        x = seg(t, ct(1, 2) + 0.25, ct(1, 2) + 0.5)
        d.rounded_rectangle([290, 130, 290 + 330 * x, 290], radius=20, fill=(246, 170, 186))
    chars(img, t, 1, 3, 5, 660, 120, 150, OR, ext=10, extc=OR_D, kind="pop", jitter=4 if t > ct(1, 4) else 0)
    offs = [(0, 70 * math.sin(j * 1.2 + t * 3)) for j in range(5)]
    chars(img, t, 1, 5, 10, 300, 560, 120, BLUE, ext=8, extc=BLUE_D, kind="slideR", gap=1.25, offsets=offs)
    for s in range(5):                                    # wind streaks
        p = ((t - L[1]) * 0.9 + s / 5) % 1
        if t > ct(1, 5):
            y = 520 + s * 50 + 30 * math.sin(p * 6 + s); x = lerp(-200, W, p)
            d.arc([x, y, x + 260, y + 80], 200, 340, fill=(160, 180, 220), width=5)
    clawd(d, 1620, 1000 + breathe(t), U=26, eyes="happy", ex=-0.4, blush=0.5 * seg(t, L[1], L[1] + 1))

def sc2(img, d, t):   # 暖阳刚好照在你的眉梢
    img.paste(bg_solid((250, 226, 160), dot_c=(240, 206, 130)), (0, 0)); d = ImageDraw.Draw(img)
    cx, cy = 1500, 300
    for k in range(14):
        a = k * math.pi / 7 + t * 0.25
        d.polygon([(cx, cy), (cx + math.cos(a - 0.08) * 1600, cy + math.sin(a - 0.08) * 1600), (cx + math.cos(a + 0.08) * 1600, cy + math.sin(a + 0.08) * 1600)], fill=(252, 236, 186))
    window(d, 110, 160, 860, 520, "warmth.config")
    chars(img, t, 2, 0, 2, 160, 240, 80, INK, kind="fade")
    d.line([(380, 290), (800, 290)], fill=(200, 194, 186), width=10)
    kx = lerp(380, 690, ease_out(seg(t, ct(2, 0), ct(2, 2))))
    d.line([(380, 290), (kx, 290)], fill=OR, width=10); d.ellipse([kx - 20, 270, kx + 20, 310], fill=OR, outline=INK, width=3)
    d.line([(690, 260), (690, 320)], fill=GRAY, width=3)
    if t > ct(2, 2):
        chars(img, t, 2, 2, 4, 610, 350, 70, GREEN, kind="pop")
        a = seg(t, ct(2, 3) + 0.15, ct(2, 3) + 0.35)
        if a > 0: d.line([(170, 420), (200, 455), (260, 390)][:2 + int(a > 0.5)], fill=GREEN, width=12)
        d.text((280, 425), "已应用", font=F(34, "r"), fill=GRAY, anchor="lm")
    chars(img, t, 2, 4, 6, 1000, 600, 150, INK, ext=10, extc=OR)
    chars(img, t, 2, 6, 8, 1000, 780, 120, OR, ext=8, extc=OR_D)
    chars(img, t, 2, 8, 10, 1300, 760, 170, YEL, ext=12, extc=YEL_D, kind="stamp")
    if t > ct(2, 9):
        for k in range(3): sparkle(img_draw(img), 1300 + k * 160, 730 + 30 * math.sin(t * 6 + k), 26 * (0.6 + 0.4 * pulse(t)), WHITE)
    clawd(img_draw(img), 380, 1000 + breathe(t), U=24, eyes="happy", blush=0.4, ex=0.3)

def img_draw(img): return ImageDraw.Draw(img)

def ecg(d, x0, x1, y, t, chaos):
    pts = []
    for x in range(int(x0), int(x1), 6):
        u = (x - x0) / 260 - t * 1.6
        ph = u % 1
        v = 0
        if 0.45 < ph < 0.5: v = -90
        elif 0.5 < ph < 0.55: v = 70
        elif 0.55 < ph < 0.6: v = -20
        v += chaos * (60 * math.sin(x * 0.11 + t * 30) + 40 * math.sin(x * 0.037 - t * 17))
        pts.append((x, y + v))
    d.line(pts, fill=RED, width=6, joint="curve")

def sc3(img, d, t):   # 我愣在原地心跳乱了调
    img.paste(bg_solid(DARK), (0, 0)); d = ImageDraw.Draw(img)
    chars(img, t, 3, 0, 1, 120, 100, 170, WHITE, ext=10, extc=(80, 80, 80), kind="stamp")
    chars(img, t, 3, 1, 5, 340, 140, 120, (180, 214, 240), ext=8, extc=(60, 90, 130), kind="stamp")
    chaos = ease_out(seg(t, ct(3, 5), ct(3, 7)))
    ecg(d, 0, W, 760, t, chaos)
    glitch = ct(3, 7) <= t
    for j, kk in enumerate(range(5, 10)):
        sc, a, *_ = anim(t, ct(3, kk), "stamp")
        if a <= 0: continue
        x = 760 + j * 190; y = 900
        if glitch:
            jx = 10 * math.sin(t * 80 + j); put(img, glyph(LYR[3][kk], 150, (40, 220, 230)), x - 8 + jx, y, sc, a * 0.7)
            put(img, glyph(LYR[3][kk], 150, (240, 40, 90)), x + 8 - jx, y, sc, a * 0.7)
        put(img, glyph(LYR[3][kk], 150, WHITE if kk < 7 else RED), x + (6 * math.sin(t * 60 + j) if glitch else 0), y, sc, a)
    clawd(d, 1180, 560, U=30, eyes="dot", blush=0.3)
    if t > ct(3, 3): put(img, glyph("…", 90, GRAY, kind="s"), 1180, 270, 1, 1)

STRANDS = [(x, 300 + (k * 131) % 380) for k, x in enumerate(range(820, 1960, 46))]
def willow(d, t, x0, x1, amp=1.0, leaf=(118, 176, 96), leaf2=(160, 210, 120), strands=None):
    w = 0.35 * math.sin(t * 1.4) + 0.5 * amp * math.sin(2 * math.pi * t / (BEAT * 4))
    for i, (x, ln) in enumerate(strands or STRANDS):
        if not (x0 <= x <= x1): continue
        pts = [(x + (w * 70 + 8 * math.sin(t * 2 + i)) * (k / 16) ** 1.6, -20 + ln * k / 16) for k in range(17)]
        d.line(pts, fill=leaf, width=4)
        for k in range(2, 17, 2):
            xx, yy = pts[k]; d.ellipse([xx - 7, yy - 3, xx + 7, yy + 10], fill=leaf2 if (k + i) % 4 else leaf)
    return w

def sc4(img, d, t):   # 偷看你走过柳荫摇摇摇
    img.paste(bg_solid((108, 168, 112), dot_c=(98, 156, 102)), (0, 0)); d = ImageDraw.Draw(img)
    w = willow(d, t, 700, W, 1.0, leaf=(70, 124, 70), leaf2=(150, 206, 130))
    d.polygon([(0, 0), (760, 0), (620, H), (0, H)], fill=(222, 218, 212))
    top = clawd(d, 560, 1000 + breathe(t), U=24, eyes="normal", ex=0.45, blush=0.4)
    chars(img, t, 4, 0, 3, 90, 760, 60, GRAY, kind="fade")
    put(img, glyph("(小声)", 34, GRAY, kind="r"), 230, 860, 1, clamp((t - ct(4, 2)) * 4))
    chars(img, t, 4, 3, 7, 840, 680, 150, WHITE, ext=10, extc=(40, 90, 50), kind="slideL")
    for j in range(3):                                     # 摇摇摇 swing from strings
        kk = 7 + j; t0 = ct(4, kk)
        if t < t0: continue
        ax, ay = 1100 + j * 260, 0; ln = 360 + j * 40
        ang = 0.45 * math.sin(2 * math.pi * (t - t0) / (BEAT * 2) + j) * (1 + 0.5 * pulse(t))
        bx, by = ax + math.sin(ang) * ln, ay + math.cos(ang) * ln
        d.line([(ax, ay), (bx, by)], fill=(60, 110, 60), width=4)
        sc, a, *_ = anim(t, t0, "pop")
        put(img, glyph(LYR[4][kk], 140, YEL, 10, YEL_D), bx, by + 70, sc, a, -math.degrees(ang))

def sc5(img, d, t):   # 你故意停步转头瞧瞧瞧
    if t < ct(5, 7):
        img.paste(bg_solid(BLUE, dot_c=(60, 104, 240)), (0, 0)); d = ImageDraw.Draw(img)
        chars(img, t, 5, 0, 3, 140, 160, 150, WHITE, ext=10, extc=BLUE_D)
        sc, a, *_ = anim(t, ct(5, 3), "stamp")
        if a > 0:
            box = Image.new("RGBA", (440, 230), (0, 0, 0, 0)); bd = ImageDraw.Draw(box)
            bd.rounded_rectangle([6, 6, 434, 224], radius=20, outline=(255, 90, 90), width=12)
            box.paste(glyph("停步", 150, (255, 90, 90)), (30, 14), glyph("停步", 150, (255, 90, 90)))
            put(img, box, 1200, 260, sc, a, -6)
        for j, kk in enumerate((5, 6)):                    # 转头: flip
            t0 = ct(5, kk)
            if t < t0: continue
            fl = abs(math.cos(math.pi * seg(t, t0, t0 + 0.4))) if t < t0 + 0.4 else 1
            g = glyph(LYR[5][kk], 200, YEL, 12, YEL_D)
            g2 = g.resize((max(1, int(g.width * fl)), g.height))
            put(img, g2, 700 + j * 240, 700, 1, 1)
        clawd(d, 260, 1010 + breathe(t), U=22, eyes="wide", ex=0.4, blush=0.3)
        return
    # 瞧瞧瞧: we are inside Clawd's face, words in the eyes
    img.paste(bg_solid(OR, dots=False), (0, 0)); d = ImageDraw.Draw(img)
    for j, (ex_, kk) in enumerate(((560, 7), (1360, 8))):
        h = 520 * ms_blink(t, (ct(5, 9) + 0.6,), 0.1)
        d.rectangle([ex_ - 130, 300 + (520 - h) / 2, ex_ + 130, 300 + (520 + h) / 2], fill=INK)
        sc, a, *_ = anim(t, ct(5, kk), "stamp")
        put(img, glyph(LYR[5][kk], 150, WHITE), ex_, 560, sc, a)
    sc, a, *_ = anim(t, ct(5, 9), "stamp")
    put(img, glyph(LYR[5][9], 170, WHITE, 10, OR_D), 960, 940, sc, a)

def sc6(img, d, t):   # 我脸红局促像个呆头鸟
    if t < ct(6, 7):
        img.paste(bg_solid(mix(OR, (236, 110, 120), 0.35 * seg(t, ct(6, 1), ct(6, 5))), dots=False), (0, 0)); d = ImageDraw.Draw(img)
        sh = 1 + 0.03 * math.sin(t * 40) if t > ct(6, 3) else 1
        for ex_ in (560, 1360):
            d.rectangle([ex_ - 130 * sh, 300, ex_ + 130 * sh, 820], fill=INK)
        b = ease_out(seg(t, ct(6, 1), ct(6, 3)))
        for ex_ in (560, 1360):
            d.rectangle([ex_ - 190 * b, 880, ex_ + 190 * b, 960], fill=(240, 110, 130))
        chars(img, t, 6, 0, 1, 900, 120, 110, WHITE, kind="pop")
        chars(img, t, 6, 1, 3, 480, 540, 150, (255, 200, 210), kind="stamp", gap=5.3)
        chars(img, t, 6, 3, 5, 790, 980, 90, WHITE, kind="pop", jitter=6)
        chars(img, t, 6, 5, 7, 1500, 980, 70, WHITE, kind="fade")
        return
    img.paste(bg_solid(DARK), (0, 0)); d = ImageDraw.Draw(img)
    t0 = ct(6, 7); x = seg(t, t0, t0 + 0.14)
    sc = lerp(2.4, 1.0, ease_out(x)); shake = 14 * math.exp(-(t - t0) * 8) * math.sin(t * 90)
    seal = seal_img()
    if x > 0.02:
        put(img, seal, 760 + shake, 470, sc * 1.25, 0.25 * x)
        put(img, seal, 760 + shake, 470, sc, clamp(x * 3), -8)
    rng = np.random.default_rng(1)
    if t > t0 + 0.1:
        for k in range(26):
            a = rng.uniform(0, 6.28); r = 280 + 220 * ease_out(seg(t, t0 + 0.1, t0 + 0.6)) * rng.uniform(0.6, 1.2)
            s = 10 * (1 - seg(t, t0 + 0.1, t0 + 0.9))
            if s > 1: d.rectangle([760 + math.cos(a) * r - s, 470 + math.sin(a) * r - s, 760 + math.cos(a) * r + s, 470 + math.sin(a) * r + s], fill=RED)
    chars(img, t, 6, 8, 10, 1120, 360, 170, WHITE, ext=10, extc=(90, 90, 90), kind="stamp")
    top = clawd(d, 1460, 1010, U=22, eyes="dot", blush=1.0, ahoge=back_out(seg(t, t0 + 0.2, t0 + 0.45)), t=t)
    if t > t0 + 0.3:
        d.ellipse([1460 + 150, top + 20, 1460 + 180, top + 60], fill=(120, 182, 238))

@lru_cache(None)
def seal_img():
    im = Image.new("RGBA", (520, 520), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([20, 20, 500, 500], radius=40, outline=RED, width=26)
    d.rounded_rectangle([56, 56, 464, 464], radius=24, outline=RED, width=8)
    g = glyph("呆", 330, RED)
    im.paste(g, ((520 - g.width) // 2, (520 - g.height) // 2), g)
    return im

def sc7(img, d, t):   # 心乱了像那红线缠绕
    img.paste(bg_solid(DARK), (0, 0)); d = ImageDraw.Draw(img)
    rots = [-14, 9, -6]
    chars(img, t, 7, 0, 3, 120, 110, 140, WHITE, ext=8, extc=(80, 80, 80), kind="stamp", rots=rots, jitter=3)
    chars(img, t, 7, 3, 5, 640, 160, 70, GRAY, kind="fade")
    chars(img, t, 7, 5, 9, 420, 520, 190, RED, ext=12, extc=RED_D, kind="pop")
    prog = ease_io(seg(t, ct(7, 4), L[8] - 0.2))
    n = int(600 * prog)
    if n > 2:
        pts = []
        for k in range(n):
            u = k / 600 * 2 * math.pi * 5
            pts.append((900 + 620 * math.sin(u * 0.62 + 0.4) + 80 * math.sin(u * 3.1 + t),
                        620 + 260 * math.sin(u * 1.0) + 50 * math.cos(u * 4.3 - t)))
        d.line(pts, fill=(236, 70, 80), width=6, joint="curve")
    clawd(d, 1600, 1020, U=20, eyes="gt", blush=0.8, larm=(60 + 25 * math.sin(t * 18), 2.4), rarm=(60 + 25 * math.sin(t * 18 + 2), 2.4))

def sc8(img, d, t):   # 风儿吹柳丝轻摇轻摇
    img.paste(bg_solid((226, 236, 220), dot_c=(210, 224, 204)), (0, 0)); d = ImageDraw.Draw(img)
    wsw = willow(d, t, 0, W, 1.6, strands=[(x, 260 + (k * 97) % 300) for k, x in enumerate(range(0, 1960, 60))])
    for s in range(6):
        p = ((t - L[8]) * 1.1 + s / 6) % 1; y = 380 + s * 60
        d.line([(lerp(-300, W, p), y), (lerp(-300, W, p) + 220, y - 10)], fill=(255, 255, 255), width=6)
    chars(img, t, 8, 0, 3, 140, 380, 130, BLUE, ext=8, extc=BLUE_D, kind="slideR",
          offsets=[(30 * math.sin(t * 3 + j), 0) for j in range(3)])
    for j, kk in enumerate(range(3, 9)):                   # 柳丝 / 轻摇轻摇 hang like strands
        t0 = ct(8, kk)
        if t < t0: continue
        ax = 620 + j * 205; ln = 430 + (j % 2) * 130
        big = kk >= 5
        ang = (0.12 + (0.14 if big else 0)) * math.sin(2 * math.pi * t / (BEAT * 4) + j * 0.5) + wsw * 0.1
        bx, by = ax + math.sin(ang) * ln, math.cos(ang) * ln
        d.line([(ax, 0), (bx, by)], fill=(110, 170, 96), width=4)
        sc, a, *_ = anim(t, t0, "drop")
        col, ec = ((OR, OR_D) if big else (GREEN, (40, 100, 60)))
        put(img, glyph(LYR[8][kk], 150 if big else 120, col, 10, ec), bx, by + 80, 1, a, -math.degrees(ang))
    clawd(d, 380 + 30 * wsw, 1010, U=24, eyes="happy", blush=0.5, sx=1 + 0.03 * wsw)

def sc9(img, d, t):   # 心儿跳看你娇俏娇俏
    img.paste(bg_solid((252, 214, 224), dot_c=(246, 196, 210), halftone=True), (0, 0)); d = ImageDraw.Draw(img)
    hp = 1 + 0.12 * pulse(t, 6)
    heart_px(d, 520, 470, 64 * hp)
    chars(img, t, 9, 0, 3, 520 - 186, 330, 120, WHITE, kind="stamp", gap=1.03)
    cx, cy, r = 1340, 470, 300
    d.ellipse([cx - r - 26, cy - r - 26, cx + r + 26, cy + r + 26], fill=(230, 180, 70))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(248, 244, 240))
    d.chord([cx - r, cy - r, cx + r, cy + r], 200, 250, fill=(226, 232, 240))
    clawd(d, cx, cy + 150 + breathe(t, 4), U=30, eyes="happy", blush=0.8, bow=back_out(seg(t, ct(9, 3), ct(9, 3) + 0.3)))
    for k in range(8):
        a = k * math.pi / 4 + t * 0.8
        sparkle(d, cx + math.cos(a) * (r + 60), cy + math.sin(a) * (r + 60), 18 * (0.5 + 0.5 * pulse(t, 4)), YEL)
    chars(img, t, 9, 3, 5, 900, 120, 90, INK, kind="pop")
    chars(img, t, 9, 5, 7, 300, 840, 150, PINK, stroke=6, strokec=WHITE, ext=8, extc=(170, 70, 100), kind="stamp")
    chars(img, t, 9, 7, 9, 980, 840, 150, PINK, stroke=6, strokec=WHITE, ext=8, extc=(170, 70, 100), kind="stamp")

def sc10(img, d, t):   # 你说这风光刚好刚好
    img.paste(bg_solid((222, 220, 216)), (0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(1180, 0), (W, 0), (W, H), (1020, H)], fill=BLUE)
    tag(img, t, ct(10, 0), "你说", 110, 90, 90)
    window(d, 380, 260, 1220, 760, "claude — confirm")
    chars(img, t, 10, 2, 5, 460, 360, 120, INK, kind="pop")
    put(img, glyph("吗？", 120, INK), 960, 425, 1, clamp((t - ct(10, 4) - 0.1) * 6))
    for k, (lbl, bx) in enumerate((("Yes", 560), ("No", 860))):
        pressed = k == 0 and ct(10, 5) - 0.05 < t < ct(10, 5) + 0.15
        d.rectangle([bx, 600, bx + 220, 680], fill=INK if pressed else (250, 250, 250), outline=INK, width=4)
        d.text((bx + 110, 640), lbl, font=F(40, "s"), fill=WHITE if pressed else INK, anchor="mm")
    p = ease_io(seg(t, ct(10, 3), ct(10, 5) - 0.05))
    cursor(d, lerp(1500, 680, p), lerp(900, 640, p), 1.6)
    for j, (k0, x, y) in enumerate(((5, 1260, 230), (7, 1300, 640))):
        sc, a, *_ = anim(t, ct(10, k0), "stamp")
        if a > 0:
            d2 = ImageDraw.Draw(img)
            chars(img, t, 10, k0, k0 + 2, x + 120, y, 150, WHITE, ext=10, extc=BLUE_D, kind="stamp")
            put(img, check_img(), x + 40, y + 80, sc, a)
    clawd(d, 200, 1020 + breathe(t), U=18, eyes="happy" if t > ct(10, 5) else "normal", ex=0.4, blush=0.3)

@lru_cache(None)
def check_img():
    im = Image.new("RGBA", (130, 130), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.ellipse([0, 0, 129, 129], fill=GREEN); d.line([(32, 66), (56, 92), (100, 40)], fill=WHITE, width=16, joint="curve")
    return im

CODE = ["/* fate.css — written by Claude */", ".缘分 {", "  奇妙: 100%;", "  巧合: true;", "  心跳: always;", "}"]
def sc11(img, d, t):   # 我叹这缘分真是奇妙
    img.paste(bg_solid((24, 24, 28)), (0, 0)); d = ImageDraw.Draw(img)
    d.text((70, 60), "● LIVE PREVIEW", font=F(24, "m"), fill=(240, 90, 90), anchor="lm")
    cx, cy, r = 470, 560, 330
    for k in range(22):
        a = k * 2 * math.pi / 22 + t * 0.4
        d.ellipse([cx + math.cos(a) * (r + 40) - 9, cy + math.sin(a) * (r + 40) - 9, cx + math.cos(a) * (r + 40) + 9, cy + math.sin(a) * (r + 40) + 9],
                  fill=mix((120, 90, 40), (255, 210, 100), 0.5 + 0.5 * math.sin(t * 4 + k)))
    d.ellipse([cx - r - 18, cy - r - 18, cx + r + 18, cy + r + 18], fill=(214, 170, 70))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(246, 242, 236))
    d.chord([cx - r, cy - r, cx + r, cy + r], 200, 245, fill=(222, 230, 240))
    top = clawd(d, cx, cy + 170, U=32, eyes="soft", blush=0.5)
    if t > ct(11, 1):
        p = seg(t, ct(11, 1), ct(11, 1) + 1.0)
        if p < 1: d.ellipse([cx + 220 + 60 * p, top + 20 - 40 * p, cx + 260 + 90 * p, top + 60 - 40 * p], fill=(230, 230, 236))
    d.rounded_rectangle([960, 120, 1860, 700], radius=14, fill=(32, 32, 38), outline=(60, 60, 70), width=2)
    d.text((990, 150), "fate.css", font=F(24, "m"), fill=(170, 170, 180), anchor="lm")
    total = sum(len(s) for s in CODE); n = int(total * seg(t, L[11], L[11] + 2.6)); y = 220
    for li, line in enumerate(CODE):
        s = line[:max(0, n)]; n -= len(line)
        d.text((990, y), f"{li + 1:2d}", font=F(30, "m"), fill=(90, 90, 100), anchor="lm")
        col = (110, 120, 130) if li == 0 else (230, 160, 110) if li in (1, 5) else (150, 200, 240)
        d.text((1050, y), s, font=F(36, "r"), fill=col, anchor="lm"); y += 60
    chars(img, t, 11, 0, 3, 980, 760, 80, GRAY, kind="fade")
    chars(img, t, 11, 3, 5, 1240, 740, 150, OR, ext=12, extc=OR_D, kind="stamp")
    chars(img, t, 11, 5, 9, 1060, 900, 130, YEL, ext=8, extc=YEL_D, kind="pop", glow=0)
    if t > ct(11, 7):
        for k in range(5): sparkle(d, 1060 + k * 150, 880 + 30 * math.sin(t * 5 + k), 18 * pulse(t, 3) + 6, WHITE)

def butterfly(d, x, y, s, t, c=(120, 170, 240)):
    f = abs(math.sin(t * 14)) * 0.8 + 0.2
    d.ellipse([x - 26 * s * f, y - 22 * s, x, y + 2 * s], fill=c); d.ellipse([x, y - 22 * s, x + 26 * s * f, y + 2 * s], fill=c)
    d.ellipse([x - 18 * s * f, y, x, y + 18 * s], fill=mix(c, WHITE, 0.3)); d.ellipse([x, y, x + 18 * s * f, y + 18 * s], fill=mix(c, WHITE, 0.3))
    d.line([(x, y - 18 * s), (x, y + 16 * s)], fill=INK, width=max(2, int(4 * s)))

def sc12(img, d, t):   # 花儿落蝴蝶环绕环绕
    img.paste(bg_grad((252, 208, 196), (250, 232, 214)), (0, 0)); d = ImageDraw.Draw(img)
    rng = np.random.default_rng(12)
    for k in range(50):
        x0, sp, ph = rng.uniform(0, W), rng.uniform(80, 160), rng.uniform(0, 6.28)
        y = (rng.uniform(0, H) + (t - L[12]) * sp) % (H + 60) - 30; x = x0 + 40 * math.sin(t + ph)
        wv = 12 * abs(math.cos(t * 3 + ph)) + 4
        d.ellipse([x - wv, y - 9, x + wv, y + 9], fill=(250, 180, 196) if k % 3 else WHITE)
    chars(img, t, 12, 0, 3, 120, 120, 140, (200, 70, 100), ext=8, extc=(120, 40, 60), kind="drop")
    cx, cy = 960, 560
    chars(img, t, 12, 3, 5, cx - 170, cy - 85, 170, INK, ext=10, extc=OR, kind="pop")
    for j, kk in enumerate(range(5, 9)):                   # 环绕环绕 orbit
        t0 = ct(12, kk)
        if t < t0: continue
        a = j * math.pi / 2 + (t - L[12]) * 1.4
        sc, al, *_ = anim(t, t0, "pop")
        put(img, glyph(LYR[12][kk], 110, BLUE, 6, BLUE_D), cx + math.cos(a) * 480, cy + math.sin(a) * 250, sc, al)
    for k in range(3):
        a = -(t - L[12]) * 1.1 + k * 2.1
        butterfly(d, cx + math.cos(a) * 640, cy + math.sin(a) * 330, 1.2, t + k, [(120, 170, 240), (250, 190, 80), (240, 130, 170)][k])
    clawd(d, 1650, 1030 + breathe(t), U=18, eyes="star", blush=0.4, ex=-0.3, ey=-0.3)

def lantern(d, x, y, lit, sway):
    x += sway
    d.line([(x - sway, 0), (x, y - 60)], fill=(60, 50, 50), width=3)
    if lit > 0.05:
        for r, a in ((140, 0.15), (100, 0.25)):
            c = mix((20, 22, 46), (255, 160, 90), a * lit); d.ellipse([x - r, y - r, x + r, y + r], fill=c)
    body = mix((110, 30, 36), (240, 70, 60), lit)
    d.rectangle([x - 26, y - 70, x + 26, y - 58], fill=(200, 160, 60))
    d.ellipse([x - 60, y - 62, x + 60, y + 62], fill=body)
    for k in (-30, 0, 30): d.arc([x - 60 + abs(k) * 0.6, y - 62, x + 60 - abs(k) * 0.6, y + 62], 270, 90, fill=mix(body, (90, 20, 24), 0.4), width=2) if k else None
    d.rectangle([x - 26, y + 58, x + 26, y + 70], fill=(200, 160, 60))
    d.line([(x, y + 70), (x, y + 110)], fill=(220, 180, 70), width=6)

CHATTER = ["叮", "咚", "哗", "嘿", "哈", "热闹", "嗒", "喂", "啦", "呀", "咕", "嘻"]
def sc13(img, d, t):   # 灯儿亮街巷喧闹喧闹
    img.paste(bg_solid((20, 22, 46), dot_c=(32, 34, 64)), (0, 0)); d = ImageDraw.Draw(img)
    for k in range(6):
        x = 180 + k * 312; lit = ease_out(seg(t, ct(13, 0) + k * E * 0.5, ct(13, 0) + k * E * 0.5 + 0.2))
        lantern(d, x, 230 + 20 * (k % 2), lit, 8 * math.sin(t * 2 + k))
    chars(img, t, 13, 0, 3, 120, 430, 120, (255, 214, 140), ext=8, extc=(150, 80, 40), kind="pop", glow=0)
    chars(img, t, 13, 3, 5, 120, 600, 150, WHITE, ext=10, extc=(70, 70, 110), kind="stamp")
    rng = np.random.default_rng(13)
    t0 = ct(13, 5)
    for k in range(40):
        tk = t0 + k * E / 2
        if t < tk: break
        x, y = rng.uniform(640, 1840), rng.uniform(400, 1040); s = int(rng.uniform(34, 90))
        w = CHATTER[k % len(CHATTER)]; c = [(255, 214, 140), WHITE, PINK, (150, 200, 255)][k % 4]
        sc, a, *_ = anim(t, tk, "pop")
        put(img, glyph(w, s, c), x, y, sc, a * 0.85, rng.uniform(-15, 15))
    for j, (k0, x, y) in enumerate(((5, 760, 640), (7, 1240, 820))):
        chars(img, t, 13, k0, k0 + 2, x, y, 160, YEL, ext=12, extc=YEL_D, kind="stamp", jitter=4)
    clawd(d, 420, 1030, U=18, eyes="wide", ex=0.4 * math.sin(t * 3), ey=-0.2)

def sc14(img, d, t):   # 你说这夜色刚好刚好
    img.paste(bg_grad((16, 20, 52), (44, 52, 100)), (0, 0)); d = ImageDraw.Draw(img)
    for s in range(60):
        x = (s * 331) % W; y = (s * 197) % 760; tw = 0.5 + 0.5 * math.sin(t * 2.4 + s * 1.3)
        d.rectangle([x, y, x + 3, y + 3], fill=mix((40, 44, 90), (240, 240, 255), tw))
    d.ellipse([1500, 120, 1700, 320], fill=(252, 240, 200)); d.ellipse([1560, 100, 1760, 300], fill=(28, 32, 70))
    tag(img, t, ct(14, 0), "你说", 120, 120, 90)
    chars(img, t, 14, 2, 5, 120, 300, 170, (236, 236, 255), ext=8, extc=(70, 80, 140), kind="fade", glow=0)
    for j, (k0, x, y) in enumerate(((5, 860, 560), (7, 1220, 760))):
        sc, a, *_ = anim(t, ct(14, k0), "pop")
        if a > 0: put(img, check_img(), x - 50, y + 80, sc * 0.8, a)
        chars(img, t, 14, k0, k0 + 2, x + 40, y, 150, WHITE, ext=8, extc=(70, 80, 140), kind="pop")
    clawd(d, 420, 1010 + breathe(t, 3), U=26, eyes="soft", blush=0.5, ex=0.3, ey=-0.3)

def sc15(img, d, t):   # 我想这相遇真是太巧
    img.paste(bg_solid(PAPER, halftone=True), (0, 0)); d = ImageDraw.Draw(img)
    chars(img, t, 15, 0, 3, 120, 110, 100, GRAY, kind="fade")
    tm = ct(15, 4) + 0.25
    meet = ease_io(seg(t, ct(15, 3), tm))
    for side, kk in ((-1, 3), (1, 4)):
        if t < ct(15, kk) - 0.2: continue
        x = 960 + side * lerp(780, 130, meet); y = 470
        if int(t * 3) % 2 == 0 or t < tm: d.rectangle([x + (110 if side < 0 else -130), y - 90, x + (130 if side < 0 else -110), y + 90], fill=OR)
        put(img, glyph(LYR[15][kk], 190, INK, 12, OR), x, y, 1, clamp((t - ct(15, kk) + 0.2) * 5))
    if t > tm:
        p = seg(t, tm, tm + 0.4)
        heart_px(d, 960, 260, 24 * back_out(p) * (1 + 0.15 * pulse(t, 5)))
        for k in range(8):
            a = k * math.pi / 4; r = 120 + 260 * ease_out(p)
            sparkle(d, 960 + math.cos(a) * r, 470 + math.sin(a) * r * 0.7, 22 * (1 - p) + 2, YEL)
    chars(img, t, 15, 5, 7, 420, 760, 170, INK, ext=12, extc=OR, kind="stamp")
    chars(img, t, 15, 7, 9, 860, 720, 220, OR, ext=14, extc=OR_D, kind="stamp")
    clawd(d, 1600, 1010 + breathe(t, 4), U=26, eyes="happy", blush=0.9, rarm=50 + 20 * math.sin(t * 10) if t > ct(15, 8) else None)

SCENES = [sc0, sc1, sc2, sc3, sc4, sc5, sc6, sc7, sc8, sc9, sc10, sc11, sc12, sc13, sc14, sc15]

# ------------------------------------------------------------------ post: grain + vignette
_yy, _xx = np.mgrid[0:H, 0:W]
VIG = (1 - 0.28 * np.clip(((_xx - W / 2) / (W * 0.62)) ** 2 + ((_yy - H / 2) / (H * 0.62)) ** 2, 0, 1))[..., None].astype(np.float32)
GRAIN = [np.random.default_rng(s).normal(0, 6, (H, W, 1)).astype(np.float32) for s in range(4)]

def render_frame(fi):
    t = fi / FPS
    img = Image.new("RGB", (W, H), DARK); d = ImageDraw.Draw(img)
    if t < L[0]: sc_intro(img, d, t)
    else:
        i = int(np.searchsorted(L, t, side="right") - 1)
        SCENES[i](img, d, t)
    arr = np.asarray(img).astype(np.float32) * VIG + GRAIN[fi % 4]
    if t < 0.6: arr *= t / 0.6
    if t > END - 1.2: arr *= clamp((END - t) / 1.1)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")

def frame_bytes(fi): return render_frame(fi).tobytes()

if __name__ == "__main__":
    song = sys.argv[1]
    if sys.argv[2] == "preview":
        out, times = sys.argv[3], [float(x) for x in sys.argv[4:]]
        th = [render_frame(int(x * FPS)).resize((480, 270)) for x in times]
        cols = min(4, len(th)); rows = (len(th) + cols - 1) // cols
        sheet = Image.new("RGB", (480 * cols, 270 * rows))
        for k, im in enumerate(th): sheet.paste(im, ((k % cols) * 480, (k // cols) * 270))
        sheet.save(out); sys.exit()
    OUT = sys.argv[2]; n = int(END * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-t", str(END), "-i", song,
                           "-af", f"afade=t=in:st=0:d=0.4,afade=t=out:st={END - 1.4}:d=1.4",
                           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "19",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", OUT],
                          stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for b in pool.imap(frame_bytes, range(n), chunksize=6): ff.stdin.write(b)
    ff.stdin.close(); ff.wait(); print("wrote", OUT)
