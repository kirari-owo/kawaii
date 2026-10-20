"""Clawd x 呆头鸟 — v3: Clawd hops across every lyric; the meaning lives in the backgrounds.

  python3 make_hop.py song.mp3 out.mp4
  python3 make_hop.py song.mp3 preview sheet.png t1 t2 ...
Needs lyrics.txt next to this file (kept out of the repo) and beats.json.
"""
import math, os, subprocess, sys
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw

import make_ktv as K
from make_ktv import (W, H, FPS, END, BEAT, E, L, LYR, ct, clamp, seg, ease_out, ease_in, ease_io, back_out, lerp, mix,
                      F, glyph, put, anim, clawd, heart_px, sparkle, bg_solid, bg_grad, window, cursor, lattice, glow_disc,
                      ecg, willow, seal_img, check_img, butterfly, lantern, CHATTER, CODE, pulse, breathe, ms_blink, LAND,
                      DARK, PAPER, INK, OR, OR_D, BLUE, BLUE_D, YEL, YEL_D, RED, RED_D, PINK, GREEN, WHITE, GRAY, beat_phase)

CS = 140                    # lyric char size
GAP = 1.09
HU = 14                     # Clawd size while hopping on words
FLOOR = 1030

ROW_Y = [720, 560, 640, 420, 700, 700, 760, 560, 720, 780, 720, 760, 600, 700, 640, 640]
# (k0, k1, face colour, extrude colour) per line
STYLE = [
    [(0, 2, YEL, YEL_D), (2, 4, (226, 220, 246), (110, 100, 150)), (4, 6, WHITE, (150, 110, 120)), (6, 9, (240, 200, 170), (120, 80, 60))],
    [(0, 1, BLUE, BLUE_D), (1, 3, INK, OR), (3, 5, OR, OR_D), (5, 10, BLUE, BLUE_D)],
    [(0, 2, OR, OR_D), (2, 4, GREEN, (40, 110, 60)), (4, 8, INK, OR), (8, 10, YEL, YEL_D)],
    [(0, 1, WHITE, (90, 90, 90)), (1, 5, (180, 214, 240), (60, 90, 130)), (5, 7, WHITE, (90, 90, 90)), (7, 10, RED, RED_D)],
    [(0, 3, (214, 210, 204), (110, 106, 100)), (3, 7, WHITE, (40, 90, 50)), (7, 10, YEL, YEL_D)],
    [(0, 3, WHITE, BLUE_D), (3, 5, (255, 120, 120), (140, 30, 30)), (5, 7, YEL, YEL_D), (7, 10, WHITE, BLUE_D)],
    [(0, 1, WHITE, (150, 80, 100)), (1, 3, (255, 214, 222), (200, 80, 100)), (3, 7, WHITE, (150, 80, 100)), (8, 10, WHITE, (150, 80, 100))],
    [(0, 3, WHITE, (90, 90, 90)), (3, 5, (170, 166, 160), (80, 80, 80)), (5, 9, RED, RED_D)],
    [(0, 3, BLUE, BLUE_D), (3, 5, GREEN, (40, 100, 60)), (5, 9, OR, OR_D)],
    [(0, 3, WHITE, (190, 80, 110)), (3, 5, INK, (190, 80, 110)), (5, 9, PINK, (170, 70, 100))],
    [(0, 2, BLUE, BLUE_D), (2, 5, INK, OR), (5, 9, WHITE, BLUE_D)],
    [(0, 3, (170, 166, 176), (70, 70, 80)), (3, 5, OR, OR_D), (5, 9, YEL, YEL_D)],
    [(0, 3, (206, 70, 100), (120, 40, 60)), (3, 5, INK, OR), (5, 9, BLUE, BLUE_D)],
    [(0, 3, (255, 214, 140), (150, 80, 40)), (3, 5, WHITE, (70, 70, 110)), (5, 9, YEL, YEL_D)],
    [(0, 2, BLUE, (20, 30, 90)), (2, 5, (236, 236, 255), (70, 80, 140)), (5, 9, WHITE, (70, 80, 140))],
    [(0, 3, (150, 144, 138), (90, 86, 80)), (3, 5, INK, OR), (5, 7, INK, OR), (7, 9, OR, OR_D)],
]
def style_of(i, k):
    for k0, k1, c, e in STYLE[i]:
        if k0 <= k < k1: return c, e
    return WHITE, (90, 90, 90)

def slot(i, k):
    n = len(LYR[i]); x0 = (W - n * CS * GAP) / 2
    return x0 + k * CS * GAP + CS / 2, ROW_Y[i]         # char centre x, row top y
def top_of(i, k): x, y = slot(i, k); return x, y + 0.1 * CS

# ------------------------------------------------------------------ special moments
FALL_T = ct(5, 5) + 0.05             # she turns her head -> spotlight, Clawd falls
FALL_X = slot(5, 4)[0]
STAMP_T = ct(6, 7)                   # 呆 appears in the sky
HIT_T = ct(6, 9) + LAND + 0.22       # ...and lands on Clawd standing on 鸟
LIFT_T, SETTLE_T, POP_T = HIT_T + 0.5, HIT_T + 0.85, HIT_T + 0.78

SKIP = {3: set(range(1, 5)), 5: set(range(5, 10)), 6: {7}}
def build_path():
    pts = [(14.95, 560, 880, 34)]
    for i in range(16):
        if i == 6: pts.append((L[6] - 0.3, FALL_X + 60, FLOOR, HU))
        for k in range(len(LYR[i])):
            if k in SKIP.get(i, ()): continue
            x, y = top_of(i, k); pts.append((ct(i, k) + LAND, x, y, HU))
    return pts
PATH = build_path()

def hop_path(t, pts):
    cur = 0
    for k in range(1, len(pts)):
        if t >= pts[k][0]: cur = k
    _, x, f, u = pts[cur]; sx = sy = 1.0; air = False
    if cur + 1 < len(pts):
        nt, nx, nf, nu = pts[cur + 1]
        dist = math.hypot(nx - x, nf - f)
        dur = min(max(0.2, dist / 2400), (nt - pts[cur][0]) * 0.85)
        t0 = nt - dur
        if t > t0:
            q = (t - t0) / dur
            h = 46 + 0.12 * abs(nx - x) + 0.4 * abs(nf - f)
            x, u = lerp(x, nx, q), lerp(u, nu, q)
            f = lerp(f, nf, q) - h * 4 * q * (1 - q); sy, sx = 1.08, 0.94; air = True
    if cur > 0 and not air:
        q = seg(t, pts[cur][0], pts[cur][0] + 0.14)
        if q < 1: sy = 1 - 0.22 * math.sin(math.pi * q); sx = 2 - sy
    return x, f, u, sx, sy, cur, air

def landed_dip(t, i, k):
    if k in SKIP.get(i, ()): return 0
    q = seg(t, ct(i, k) + LAND, ct(i, k) + LAND + 0.16)
    return 12 * math.sin(math.pi * q) if 0 < q < 1 else 0

# ------------------------------------------------------------------ backgrounds (the lyric's meaning)
def bg0(img, d, t):
    k = seg(t, L[0], L[1])
    img.paste(bg_grad(mix((40, 48, 92), (110, 150, 210), k), mix((180, 110, 110), (252, 206, 150), k)), (0, 0)); d = ImageDraw.Draw(img)
    put(img, glow_disc(), 1460, lerp(800, 340, ease_out(seg(t, L[0], L[0] + 2.6))), 0.8)
    lattice(d, 1460, 340, 440, 440, 1, (92, 60, 48))

def fan(d, cx, cy, r, a0, a1, col, rib):
    pts = [(cx, cy)] + [(cx + math.cos(math.radians(a)) * r, cy + math.sin(math.radians(a)) * r) for a in np.linspace(a0, a1, 24)]
    d.polygon(pts, fill=col)
    for a in np.linspace(a0, a1, 11):
        d.line([(cx, cy), (cx + math.cos(math.radians(a)) * r, cy + math.sin(math.radians(a)) * r)], fill=rib, width=4)
    d.ellipse([cx - 0.35 * r, cy - 0.35 * r, cx + 0.35 * r, cy + 0.35 * r], fill=PAPER)

def bg1(img, d, t):
    img.paste(bg_solid(PAPER, halftone=True), (0, 0)); d = ImageDraw.Draw(img)
    op = ease_out(seg(t, ct(1, 1), ct(1, 2) + 0.3))
    fan(d, 1500, 470, 420, -170 + 20 * (1 - op), -170 + 20 * (1 - op) + 150 * op, (248, 196, 206), (230, 150, 170))
    for s in range(6):
        p = ((t - L[1]) * 0.8 + s / 6) % 1
        y = 820 + s * 34 + 24 * math.sin(p * 6 + s); x = lerp(-300, W, p)
        d.arc([x, y, x + 320, y + 90], 200, 340, fill=(170, 186, 226), width=5)

def bg2(img, d, t):
    img.paste(bg_solid((250, 226, 160), dot_c=(240, 206, 130)), (0, 0)); d = ImageDraw.Draw(img)
    cx, cy = 1560, 260
    for k in range(14):
        a = k * math.pi / 7 + t * 0.25
        d.polygon([(cx, cy), (cx + math.cos(a - 0.08) * 1900, cy + math.sin(a - 0.08) * 1900), (cx + math.cos(a + 0.08) * 1900, cy + math.sin(a + 0.08) * 1900)], fill=(252, 236, 186))
    d.ellipse([cx - 110, cy - 110, cx + 110, cy + 110], fill=(255, 214, 110))
    window(d, 110, 120, 760, 400, "warmth.config")
    d.text((160, 230), "暖阳", font=F(56), fill=INK, anchor="lm")
    d.line([(330, 230), (700, 230)], fill=(200, 194, 186), width=10)
    kx = lerp(330, 600, ease_out(seg(t, ct(2, 0), ct(2, 2))))
    d.line([(330, 230), (kx, 230)], fill=OR, width=10); d.ellipse([kx - 18, 212, kx + 18, 248], fill=OR, outline=INK, width=3)
    d.text((600, 290), "刚好", font=F(36), fill=GREEN if t > ct(2, 2) else GRAY, anchor="mm")
    if t > ct(2, 3): d.text((160, 340), "✓ 已应用", font=F(34), fill=GREEN, anchor="lm")

def bg3(img, d, t):
    img.paste(bg_solid(DARK), (0, 0)); d = ImageDraw.Draw(img)
    ecg(d, 0, W, 860, t, ease_out(seg(t, ct(3, 5), ct(3, 7))))
    if ct(3, 1) <= t < ct(3, 5):                         # frost rim while frozen
        a = seg(t, ct(3, 1), ct(3, 2))
        for k in range(18):
            x = (k * 113) % W; y = 120 + (k * 71) % 160
            sparkle(d, x, y, 14 * a, (160, 200, 240))

def bg4(img, d, t):
    img.paste(bg_solid((108, 168, 112), dot_c=(98, 156, 102)), (0, 0)); d = ImageDraw.Draw(img)
    willow(d, t, 700, W, 1.0, leaf=(70, 124, 70), leaf2=(150, 206, 130))
    d.polygon([(0, 0), (700, 0), (560, H), (0, H)], fill=(222, 218, 212))
    if t > ct(4, 3):
        p = (t - ct(4, 3)) * 0.35
        for k in range(2):                                # footprints: someone walking past
            x = lerp(800, 1900, (p + k * 0.12) % 1); d.ellipse([x, 980 + 20 * (k % 2), x + 40, 1000 + 20 * (k % 2)], fill=(80, 130, 80))

def bg5(img, d, t):
    img.paste(bg_solid(BLUE, dot_c=(60, 104, 240)), (0, 0)); d = ImageDraw.Draw(img)
    if t >= FALL_T:                                      # she turns: two huge eyes + a spotlight on Clawd
        q = ease_out(seg(t, FALL_T, FALL_T + 0.25))
        bl = ms_blink(t, (ct(5, 9) + 0.5,), 0.1)
        for ex_ in (700, 1220):
            h = 300 * q * bl
            d.rounded_rectangle([ex_ - 70, 230 - h / 2, ex_ + 70, 230 + h / 2], radius=30, fill=(20, 26, 70))
            if h > 60: d.ellipse([ex_ - 34, 230 - h / 2 + 30, ex_ + 6, 230 - h / 2 + 70], fill=WHITE)
        sx = lerp(W + 200, FALL_X, ease_out(seg(t, FALL_T, FALL_T + 0.2)))
        d.polygon([(960, -40), (sx - 160, FLOOR + 40), (sx + 160, FLOOR + 40)], fill=(96, 136, 246))

def bg6(img, d, t):
    pink = seg(t, ct(6, 1), ct(6, 4))
    img.paste(bg_solid(mix((236, 160, 170), (236, 110, 128), pink), dot_c=mix((226, 150, 160), (226, 100, 118), pink)), (0, 0)); d = ImageDraw.Draw(img)
    b = ease_out(seg(t, ct(6, 1), ct(6, 3)))
    for cx in (360, 1560):
        d.ellipse([cx - 260 * b, 300 - 120 * b, cx + 260 * b, 300 + 120 * b], fill=(246, 140, 156))

def bg7(img, d, t):
    img.paste(bg_solid(DARK), (0, 0)); d = ImageDraw.Draw(img)
    prog = ease_io(seg(t, ct(7, 3), L[8] - 0.2)); n = int(600 * prog)
    if n > 2:
        pts = [(960 + 860 * math.sin(k / 600 * 2 * math.pi * 5 * 0.62 + 0.4) + 80 * math.sin(k / 600 * 2 * math.pi * 5 * 3.1 + t),
                560 + 380 * math.sin(k / 600 * 2 * math.pi * 5) + 50 * math.cos(k / 600 * 2 * math.pi * 5 * 4.3 - t)) for k in range(n)]
        d.line(pts, fill=(236, 70, 80), width=6, joint="curve")

def bg8(img, d, t):
    img.paste(bg_solid((226, 236, 220), dot_c=(210, 224, 204)), (0, 0)); d = ImageDraw.Draw(img)
    willow(d, t, 0, W, 1.6, strands=[(x, 220 + (k * 97) % 300) for k, x in enumerate(range(0, 1960, 60))])
    for s in range(6):
        p = ((t - L[8]) * 1.1 + s / 6) % 1; y = 930 + s * 20
        d.line([(lerp(-300, W, p), y), (lerp(-300, W, p) + 240, y - 10)], fill=WHITE, width=6)

def bg9(img, d, t):
    img.paste(bg_solid((252, 214, 224), dot_c=(246, 196, 210), halftone=True), (0, 0)); d = ImageDraw.Draw(img)
    heart_px(d, 960, 420, 80 * (1 + 0.1 * pulse(t, 6)), (246, 150, 172))
    for k in range(10):
        a = k * math.pi / 5 + t * 0.6
        sparkle(d, 960 + math.cos(a) * 700, 480 + math.sin(a) * 330, 20 * (0.5 + 0.5 * pulse(t, 4)), YEL)

def bg10(img, d, t):
    img.paste(bg_solid((222, 220, 216)), (0, 0)); d = ImageDraw.Draw(img)
    d.polygon([(1240, 0), (W, 0), (W, H), (1080, H)], fill=BLUE)
    window(d, 560, 120, 1360, 520, "claude — confirm")
    d.text((960, 260), "这风光，刚好吗？", font=F(72), fill=INK, anchor="mm")
    for k, (lbl, bx) in enumerate((("Yes", 720), ("No", 1000))):
        pressed = k == 0 and ct(10, 5) - 0.05 < t < ct(10, 5) + 0.15
        d.rectangle([bx, 380, bx + 200, 450], fill=INK if pressed else (250, 250, 250), outline=INK, width=4)
        d.text((bx + 100, 415), lbl, font=F(36, "s"), fill=WHITE if pressed else INK, anchor="mm")
    p = ease_io(seg(t, ct(10, 2), ct(10, 5) - 0.05))
    cursor(d, lerp(1700, 830, p), lerp(900, 415, p), 1.5)

def bg11(img, d, t):
    img.paste(bg_solid((24, 24, 28)), (0, 0)); d = ImageDraw.Draw(img)
    d.rounded_rectangle([960, 90, 1860, 600], radius=14, fill=(32, 32, 38), outline=(60, 60, 70), width=2)
    d.text((990, 120), "fate.css", font=F(24, "m"), fill=(170, 170, 180), anchor="lm")
    total = sum(len(s) for s in CODE); n = int(total * seg(t, L[11], L[11] + 2.6)); y = 190
    for li, line in enumerate(CODE):
        s = line[:max(0, n)]; n -= len(line)
        d.text((990, y), f"{li + 1:2d}", font=F(30, "m"), fill=(90, 90, 100), anchor="lm")
        col = (110, 120, 130) if li == 0 else (230, 160, 110) if li in (1, 5) else (150, 200, 240)
        d.text((1050, y), s, font=F(36, "r"), fill=col, anchor="lm"); y += 62
    d.text((70, 60), "● LIVE PREVIEW", font=F(24, "m"), fill=(240, 90, 90), anchor="lm")
    for k in range(22):
        a = k * 2 * math.pi / 22 + t * 0.4; cx, cy, r = 460, 380, 260
        d.ellipse([cx + math.cos(a) * r - 8, cy + math.sin(a) * r - 8, cx + math.cos(a) * r + 8, cy + math.sin(a) * r + 8],
                  fill=mix((120, 90, 40), (255, 210, 100), 0.5 + 0.5 * math.sin(t * 4 + k)))
    if t > ct(11, 7):
        for k in range(6): sparkle(d, 300 + k * 260, 680 + 30 * math.sin(t * 5 + k), 18 * pulse(t, 3) + 6, WHITE)

def bg12(img, d, t):
    img.paste(bg_grad((252, 208, 196), (250, 232, 214)), (0, 0)); d = ImageDraw.Draw(img)
    rng = np.random.default_rng(12)
    for k in range(50):
        x0, sp, ph = rng.uniform(0, W), rng.uniform(80, 160), rng.uniform(0, 6.28)
        y = (rng.uniform(0, H) + (t - L[12]) * sp) % (H + 60) - 30; x = x0 + 40 * math.sin(t + ph)
        wv = 12 * abs(math.cos(t * 3 + ph)) + 4
        d.ellipse([x - wv, y - 9, x + wv, y + 9], fill=(250, 180, 196) if k % 3 else WHITE)
    for k in range(3):
        a = -(t - L[12]) * 1.1 + k * 2.1
        butterfly(d, 960 + math.cos(a) * 780, 640 + math.sin(a) * 300, 1.3, t + k, [(120, 170, 240), (250, 190, 80), (240, 130, 170)][k])

def bg13(img, d, t):
    img.paste(bg_solid((20, 22, 46), dot_c=(32, 34, 64)), (0, 0)); d = ImageDraw.Draw(img)
    for k in range(6):
        lit = ease_out(seg(t, ct(13, 0) + k * E * 0.5, ct(13, 0) + k * E * 0.5 + 0.2))
        lantern(d, 180 + k * 312, 230 + 20 * (k % 2), lit, 8 * math.sin(t * 2 + k))
    rng = np.random.default_rng(13)
    for k in range(40):
        tk = ct(13, 5) + k * E / 2
        if t < tk: break
        x, y = rng.uniform(80, 1840), rng.choice([rng.uniform(420, 600), rng.uniform(900, 1040)]); s = int(rng.uniform(34, 80))
        sc, a, *_ = anim(t, tk, "pop")
        put(img, glyph(CHATTER[k % len(CHATTER)], s, [(255, 214, 140), WHITE, PINK, (150, 200, 255)][k % 4]), x, y, sc, a * 0.7, rng.uniform(-15, 15))

def bg14(img, d, t):
    img.paste(bg_grad((16, 20, 52), (44, 52, 100)), (0, 0)); d = ImageDraw.Draw(img)
    for s in range(70):
        x = (s * 331) % W; y = (s * 197) % H; tw = 0.5 + 0.5 * math.sin(t * 2.4 + s * 1.3)
        d.rectangle([x, y, x + 3, y + 3], fill=mix((40, 44, 90), (240, 240, 255), tw))
    d.ellipse([1500, 120, 1700, 320], fill=(252, 240, 200)); d.ellipse([1560, 100, 1760, 300], fill=(28, 32, 70))

def bg15(img, d, t):
    img.paste(bg_solid(PAPER, halftone=True), (0, 0)); d = ImageDraw.Draw(img)
    tm = ct(15, 4) + 0.1
    if t > tm:
        p = seg(t, tm, tm + 0.5)
        heart_px(d, 960, 330, 50 * back_out(p) * (1 + 0.08 * pulse(t, 5)), (246, 180, 190))
        for k in range(10):
            a = k * math.pi / 5; r = 200 + 420 * ease_out(p)
            sparkle(d, 960 + math.cos(a) * r, 380 + math.sin(a) * r * 0.5, 26 * (1 - p) + 3, YEL)

BGS = [bg0, bg1, bg2, bg3, bg4, bg5, bg6, bg7, bg8, bg9, bg10, bg11, bg12, bg13, bg14, bg15]
MOOD = ["happy", "happy", "happy", "dot", "normal", "normal", "wide", "wide", "happy", "happy", "happy", "soft",
        "star", "wide", "soft", "happy"]

# ------------------------------------------------------------------ foreground: the lyric row
def draw_row(img, t, i):
    d = ImageDraw.Draw(img)
    for k, ch in enumerate(LYR[i]):
        if i == 6 and k == 7: continue                   # 呆 is the falling seal
        sc, a, dx, dy, r = anim(t, ct(i, k), "pop")
        if a <= 0: continue
        x, y = slot(i, k); y += landed_dip(t, i, k)
        c, e = style_of(i, k); rot = 0
        if i == 3 and k >= 7:                             # 乱了调: glitch
            jx = 10 * math.sin(t * 80 + k)
            put(img, glyph(ch, CS, (40, 220, 230)), x - 8 + jx, y + CS / 2, sc, a * 0.7)
            put(img, glyph(ch, CS, (240, 40, 90)), x + 8 - jx, y + CS / 2, sc, a * 0.7)
            x += 6 * math.sin(t * 60 + k)
        if i == 4 and k >= 7: rot = 14 * math.sin(2 * math.pi * t / (BEAT * 2) + k)     # 摇摇摇
        if i == 8: rot = 6 * math.sin(2 * math.pi * t / (BEAT * 4) + k * 0.5) * (2 if k >= 5 else 1)
        if i == 6 and 3 <= k < 5: x += 5 * math.sin(t * 47 + k)                           # 局促
        if i == 7 and k < 3: rot = [-14, 9, -6][k]
        if i == 13 and k >= 5: x += 4 * math.sin(t * 40 + k)
        stroke = 6 if i == 9 and k >= 5 else 0
        put(img, glyph(ch, CS, c, 9, e, stroke, WHITE if stroke else None), x, y + CS / 2, sc, a, rot + r)
        if i in (10, 14) and k in (5, 7):                 # ✓ above 刚好
            s2, a2, *_ = anim(t, ct(i, k), "stamp"); put(img, check_img(), x + CS * 0.5, y - 50, s2 * 0.7, a2)
    if i == 6 and t >= SETTLE_T:                          # the seal, shrunk into its slot
        x, y = slot(6, 7); put(img, seal_img(), x, y + CS / 2, CS * 1.15 / 520, 1, -6)

# ------------------------------------------------------------------ Clawd
def clawd_rot(img, rot, cx, feet, U, **kw):
    """Draw Clawd rotated about its body centre (for the fall)."""
    S = int(18 * U); lay = Image.new("RGBA", (S, S), (0, 0, 0, 0)); ld = ImageDraw.Draw(lay)
    clawd(ld, S / 2, S / 2 + 4 * U, U=U, **kw)
    lay = lay.rotate(rot, resample=Image.BICUBIC)
    img.paste(lay, (int(cx - S / 2), int(feet - 4 * U - S / 2)), lay)

def draw_clawd(img, t, i):
    d = ImageDraw.Draw(img)
    if t < 14.95:                                         # waking up in the night scene
        top = clawd(d, 560, 880 + breathe(t, 3), U=34, eyes="closed" if t < 14.6 else "wide")
        if t < 14.6:
            for z in range(3):
                p = ((t - 8.4) * 0.5 + z / 3) % 1
                put(img, glyph("z", int(30 + 30 * p), (200, 200, 230), kind="s"), 720 + 90 * p, top - 30 - 120 * p, 1, 1 - p)
        else: put(img, glyph("!", 80, YEL, kind="s"), 560, top - 60, back_out(seg(t, 14.6, 14.8)), 1)
        return
    x, f, u, sx, sy, cur, air = hop_path(t, PATH)
    eyes = MOOD[i] if i >= 0 else "happy"; blush = 0.4; ex = ey = 0.0; extra = {}
    if air: eyes = "happy" if eyes in ("normal", "happy") else eyes
    if i == 3 and ct(3, 5) <= t: eyes = "wide"
    if i == 4: ex = 0.4 * math.sin(t * 3)                 # sneaky glances
    if i == 6: blush = 0.4 + 0.6 * seg(t, ct(6, 1), ct(6, 3))
    if i == 9: extra["bow"] = 1.0
    # --- 你故意停步转头: caught peeking -> falls off the word ---
    if i == 5 and t >= FALL_T:
        bx, by = top_of(5, 4)
        if t < FALL_T + 0.3:
            clawd(d, bx, by, U=HU, eyes="wide", blush=0.8)
            put(img, glyph("!", 70, YEL, kind="s"), bx, by - 8 * HU - 40, back_out(seg(t, FALL_T, FALL_T + 0.12)), 1)
            return
        q = seg(t, FALL_T + 0.3, FALL_T + 0.75)
        fx = bx + 60 * q; ff = lerp(by, FLOOR, q * q); rot = -95 * ease_out(q)
        if q >= 1:
            b = seg(t, FALL_T + 0.75, FALL_T + 1.0); ff = FLOOR - 30 * math.sin(math.pi * b) if b < 1 else FLOOR; rot = -90
        clawd_rot(img, rot, fx, ff, HU, eyes="x" if q >= 1 else "wide", blush=0.8,
                  larm=(70 + 30 * math.sin(t * 30), 2.4) if q < 1 else None, rarm=(70 + 30 * math.sin(t * 30 + 2), 2.4) if q < 1 else None)
        if q >= 1:
            for k in range(3):
                a = t * 6 + k * 2.09; sparkle(d, fx + math.cos(a) * 110, FLOOR - 150 + math.sin(a) * 22, 12, YEL)
        return
    # --- 呆 seal chases Clawd and squashes it on 鸟 ---
    if i == 6 and t >= STAMP_T:
        bx, by = top_of(6, 9)
        if t < HIT_T:
            eyes = "wide" if t < STAMP_T + 0.2 else "gt"; blush = 1.0
            extra["larm"] = extra["rarm"] = (70 + 30 * math.sin(t * 40), 2.4) if t > STAMP_T + 0.2 else None
        elif t < POP_T:
            x, f, sx, sy, eyes = bx, by, 1.55, 0.16, "x"
        else:
            qq = seg(t, POP_T, POP_T + 0.25); x, f = bx, by
            sy = lerp(0.16, 1.0, back_out(qq, 2.4)); sx = lerp(1.55, 1.0, ease_out(qq)); eyes = "dot"
            extra["ahoge"] = back_out(seg(t, POP_T + 0.1, POP_T + 0.3)); extra["t"] = t
    top = clawd(d, x, f, U=u, sx=sx, sy=sy, eyes=eyes, ex=ex, ey=ey, blush=blush, **extra)
    if i == 6 and t >= STAMP_T:
        bx, by = top_of(6, 9); sx0, _ = slot(6, 7)
        if t < HIT_T:
            for k in range(1 + int(3 * seg(t, STAMP_T, HIT_T))):
                p = ((t - STAMP_T) * 2.4 + k / 3) % 1; x0 = x + (110 if k % 2 == 0 else -110); y0 = top + 20 + 80 * p
                d.ellipse([x0 - 9, y0 - 9, x0 + 9, y0 + 11], fill=(120, 182, 238))
            if t < STAMP_T + 0.25: put(img, glyph("!", 70, YEL, kind="s"), x, top - 50, back_out(seg(t, STAMP_T, STAMP_T + 0.12)), 1)
        if t >= LIFT_T and t >= POP_T - 0.01:
            put(img, glyph("呆", int(max(18, 54 * min(1, sy * 2.5))), RED), x + 30, f - 3.2 * HU * sy, 1, 0.85, -8)
        # the seal itself
        sz = 300 / 520
        if t < HIT_T:
            hx = lerp(sx0, x, ease_io(seg(t, STAMP_T, HIT_T - 0.15)))
            hy = lerp(-200, 220, ease_out(seg(t, STAMP_T, STAMP_T + 0.3))) + 8 * math.sin(t * 9)
            if t > HIT_T - 0.18: hy = lerp(220, by - 150, ease_in(seg(t, HIT_T - 0.18, HIT_T)))
            d.ellipse([hx - 140 * seg(t, STAMP_T, HIT_T), by - 10, hx + 140 * seg(t, STAMP_T, HIT_T), by + 12], fill=(0, 0, 0))
            put(img, seal_img(), hx, hy, sz, 1, -6 * (1 - seg(t, HIT_T - 0.18, HIT_T)))
        elif t < LIFT_T:
            sh = 12 * math.exp(-(t - HIT_T) * 8) * math.sin(t * 95)
            put(img, seal_img(), bx + sh, by - 150, sz, 1)
        elif t < SETTLE_T:
            qq = ease_io(seg(t, LIFT_T, SETTLE_T)); _, ry = slot(6, 7)
            put(img, seal_img(), lerp(bx, sx0, qq), lerp(by - 150, ry + CS / 2, qq) - 160 * math.sin(math.pi * qq),
                lerp(sz, CS * 1.15 / 520, qq), 1, -6 * qq)
        if HIT_T <= t < HIT_T + 0.5:                      # impact
            p = seg(t, HIT_T, HIT_T + 0.5)
            for side in (-1, 1):
                for k in range(3):
                    r = (16 + 26 * k) * (0.4 + p) * (1 - p) + 2
                    cx = bx + side * (170 + 50 * k * p); cy = by - 10 - 14 * k * p
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(250, 250, 250))
    if i == 15 and t > ct(15, 8) + 0.5:                   # wave + heart at the very end
        heart_px(d, x, top - 60 - 6 * math.sin(t * 3), 9 * back_out(seg(t, ct(15, 8) + 0.5, ct(15, 8) + 0.9)))

def render_frame(fi):
    t = fi / FPS
    img = Image.new("RGB", (W, H), DARK); d = ImageDraw.Draw(img)
    if t < 8.38:
        K.sc_intro(img, d, t)
    else:
        i = int(np.searchsorted(L, t, side="right") - 1)
        if i < 0:
            # night before dawn (Clawd is drawn separately)
            k = (t - 8.38) / (15.27 - 8.38)
            img.paste(bg_grad(mix((14, 16, 34), (40, 48, 92), k * 0.6), mix((24, 26, 50), (180, 110, 110), ease_in(k))), (0, 0))
            d = ImageDraw.Draw(img)
            for s in range(30):
                x = (s * 397) % W; y = (s * 211) % 600; tw = 0.5 + 0.5 * math.sin(t * 3 + s)
                d.rectangle([x, y, x + 3, y + 3], fill=mix((40, 44, 80), (230, 230, 255), tw * (1 - k)))
            _, bi = beat_phase(t); b0 = int(np.searchsorted(K.BEATS, 8.38))
            lattice(d, 1460, 340, 440, 440, clamp((bi - b0 + 1) / 14), (92, 60, 48))
        else:
            BGS[i](img, d, t)
            draw_row(img, t, i)
        draw_clawd(img, t, i)
    arr = np.asarray(img).astype(np.float32) * K.VIG + K.GRAIN[fi % 4]
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
                           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-b:v", "9M", "-maxrate", "12M",
                           "-bufsize", "18M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", OUT],
                          stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for b in pool.imap(frame_bytes, range(n), chunksize=6): ff.stdin.write(b)
    ff.stdin.close(); ff.wait(); print("wrote", OUT)
