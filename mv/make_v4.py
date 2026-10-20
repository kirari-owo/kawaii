"""Clawd x 呆头鸟 — v4: free word layouts, small camera moves, a different transition per line.

  python3 make_v4.py song.mp3 out.mp4
  python3 make_v4.py song.mp3 preview sheet.png t1 t2 ...
Needs lyrics.txt (local, not in the repo) and beats.json.
"""
import math, os, subprocess, sys
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw

import make_ktv as K
import make_hop as HP
from make_ktv import (W, H, FPS, END, BEAT, E, L, LYR, ct, clamp, seg, ease_out, ease_in, ease_io, back_out, lerp, mix,
                      F, glyph, put, anim, clawd, heart_px, sparkle, bg_solid, bg_grad, lattice, ecg, seal_img, check_img,
                      pulse, breathe, ms_blink, beat_phase, DARK, PAPER, INK, OR, OR_D, BLUE, BLUE_D, YEL, YEL_D, RED, RED_D,
                      PINK, GREEN, WHITE, GRAY)
from make_hop import style_of, clawd_rot

LAND = 0.08
HU = 14
S0 = 140
FLOOR = 1010
FLING_T = 0.0

# ------------------------------------------------------------------ word layouts (world coords: centre x, centre y, size)
def _row(pts, s=S0): return [(x, y, s) for x, y in pts]
BASE = {
    0: _row([(700 + k * 124, 500 + k * 58) for k in range(9)]),
    1: [(260, 230, 170), (1290, 560, 120, -6), (1430, 560, 120, 4), (1100, 780, 160, -8), (1270, 780, 160, 6),
        (420, 560, 130), (570, 500, 130), (720, 560, 130), (870, 500, 130), (1020, 560, 130)],
    2: _row([(230 + k * 150, 900 - k * 40) for k in range(10)]),
    3: [(400, 420, 200), (620, 360, 120), (760, 360, 120), (620, 500, 120), (760, 500, 120),
        (980, 690, 150), (1140, 690, 150), (1350, 560, 150), (1520, 800, 150), (1700, 600, 150)],
    4: [(300, 930, 90), (390, 930, 90), (480, 930, 90), (620, 760, 140), (770, 740, 140), (920, 760, 140), (1070, 740, 140),
        (1300, 520, 140), (1500, 580, 140), (1700, 520, 140)],
    5: _row([(300, 560), (440, 600), (580, 640), (790, 700), (940, 700), (1180, 560), (1330, 560), (700, 240), (1220, 240), (960, 430)]),
    6: _row([(300, 830), (450, 770), (600, 770), (760, 830), (900, 830), (1060, 770), (1200, 770), (1370, 690), (1540, 820), (1700, 820)]),
    7: _row([(300, 480), (450, 540), (600, 470), (980, 380), (1140, 470), (1300, 560), (1450, 650), (1600, 740), (1750, 830)]),
    8: _row([(250 + k * 185, 0) for k in range(9)]),
    9: [(820, 400, 150), (960, 380, 150), (1100, 400, 150), (560, 700, 110, -10), (690, 730, 110, 6), (1020, 820, 170, -6),
        (1190, 760, 120, 8), (1340, 830, 170, -4), (1500, 760, 120, 10)],
    10: [(220, 280, 140), (370, 280, 140), (560, 700, 160, -4), (730, 680, 160, 3), (900, 700, 160, -2), (1130, 560, 170, -8),
         (1310, 540, 170, 6), (1180, 860, 150, 4), (1350, 880, 150, -6)],
    11: [(200, 860, 110), (330, 860, 110), (460, 860, 110), (760, 560, 220, -4), (990, 560, 220, 3), (1180, 840, 130),
         (1330, 790, 140), (1490, 740, 150), (1660, 690, 170)],
    12: [(320, 380, 140), (470, 520, 140), (620, 660, 140), (900, 640, 170), (1070, 640, 170), (0, 0, 130), (0, 0, 130), (0, 0, 130), (0, 0, 130)],
    13: [(492, 440, 130), (804, 460, 130), (1116, 440, 130), (330, 720, 170, -6), (520, 760, 170, 5), (900, 640, 150, -10),
         (1100, 860, 190, 8), (1330, 600, 150, 12), (1560, 820, 200, -6)],
    14: [(260, 860, 130), (410, 860, 130), (640, 760, 150), (800, 660, 170), (980, 560, 190), (1120, 480, 140, -6),
         (1260, 440, 140, 4), (1200, 660, 140, -4), (1340, 620, 140, 6)],
    15: [(300, 460, 110), (440, 460, 110), (580, 460, 110), (860, 640, 180), (1060, 640, 180), (1260, 820, 140), (1400, 820, 140),
         (1570, 730, 180), (1760, 730, 180)],
}
BALL = (760, 905)                     # where Clawd trips in 心乱了

def pos(i, k, t):
    """-> centre x, centre y, size, rotation (deg) of char k of line i at time t (world coords)."""
    b = BASE[i][k]; x, y, s = b[:3]; rot = b[3] if len(b) > 3 else 0.0
    if i == 1:
        if 3 <= k < 5 and t > ct(1, k): rot += 6 * math.sin(t * 22 + k)            # giggling
        if k >= 5:                                                                  # pushed out by the laugh
            q = ease_out(seg(t, ct(1, k), ct(1, k) + 0.45))
            x, y = lerp(1450, x, q), lerp(520, y, q) - 70 * math.sin(math.pi * q)
    elif i == 3:
        if k >= 7: rot = [-12, 10, -8][k - 7]
    elif i == 4 and k >= 7:                 # 摇摇摇 hang from willow strands
        ax, ln = x, [480, 540, 480][k - 7]
        a = 0.28 * math.sin(2 * math.pi * t / (BEAT * 2) + k)
        x, y, rot = ax + math.sin(a) * ln, math.cos(a) * ln + 40, -math.degrees(a)
    elif i == 7:
        if k < 3: rot = [-14, 9, -6][k]
        else:                               # flung out of the tangled ball
            q = ease_out(seg(t, ct(7, k), ct(7, k) + 0.3))
            x, y = lerp(BALL[0], x, q), lerp(BALL[1] - 60, y, q) - 120 * math.sin(math.pi * q); rot = (1 - q) * 360
    elif i == 8:                            # hanging on strands, swaying in the wind
        ln = 380 + (k % 3) * 110
        a = (0.10 + (0.12 if k >= 5 else 0)) * math.sin(2 * math.pi * t / (BEAT * 4) + k * 0.5) + 0.05 * math.sin(t * 1.4)
        x, y, rot = x + math.sin(a) * ln, math.cos(a) * ln + 70, -math.degrees(a)
    elif i == 9 and k < 3:
        y -= 14 * pulse(t, 6)
    elif i == 12 and k >= 5:                # 环绕环绕 orbit around 蝴蝶
        a = (k - 5) * math.pi / 2 + (t - L[12]) * 1.1
        x, y = 985 + math.cos(a) * 470, 640 + math.sin(a) * 250
    elif i == 13 and k >= 5:
        x += 4 * math.sin(t * 40 + k)
    return x, y, s, rot

def char_top(i, k, t):
    x, y, s, _ = pos(i, k, t); return x, y - 0.42 * s

# ------------------------------------------------------------------ cameras  (zoom, focus x, focus y)
def cam(i, t):
    if i < 0: return 1.0, W / 2, H / 2
    a, b = L[i], (L[i + 1] if i + 1 < 16 else END)
    q = seg(t, a, b)
    if i == 0:
        n = ease_io(seg(t, 8.38, 10.8))                  # night: drift in on the dozing Clawd
        nz, nx, ny = lerp(1.0, 1.4, n), lerp(W / 2, 520, n), lerp(H / 2, 380, n)
        r = ease_io(seg(t, L[0] - 0.5, L[0] + 0.9))
        return lerp(nz, 1.1, r), lerp(nx, lerp(840, 1160, q), r), lerp(ny, lerp(500, 640, q), r)
    if i == 1: return 1.05, lerp(900, 1000, q), 580
    if i == 2: return lerp(1.0, 1.12, ease_io(q)), lerp(960, 1300, ease_io(q)), lerp(540, 520, q)
    if i == 3:
        sh = 10 * math.sin(t * 70) * seg(t, ct(3, 7), ct(3, 7) + 0.1) if t > ct(3, 7) else 0
        return 1.05, 960 + sh, 560 + sh * 0.6
    if i == 4: return 1.08, lerp(700, 1100, ease_io(q)), 600
    if i == 5:
        z = 1.0 + 0.22 * ease_out(seg(t, FALL_T, FALL_T + 0.15)) * (1 - ease_io(seg(t, ct(5, 7) - 0.1, ct(5, 7) + 0.3)))
        fx = lerp(960, FALL_X + 40, (z - 1) / 0.22); fy = lerp(540, 820, (z - 1) / 0.22)
        return z, fx, fy
    if i == 6:
        z = 1.05 + 0.08 * ease_out(seg(t, HIT_T, HIT_T + 0.1)) * (1 - seg(t, HIT_T + 0.6, HIT_T + 1.0))
        sh = 12 * math.exp(-(t - HIT_T) * 8) * math.sin(t * 90) if t > HIT_T else 0
        return z, lerp(960, 1300, q) + sh, 640 + sh * 0.5
    if i == 7: return 1.06, lerp(700, 1180, ease_io(q)), 620
    if i == 8: return 1.04, 960 + 40 * math.sin(t * 1.3), 520
    if i == 9: return 1.02 + 0.02 * pulse(t, 6), 960, 560
    if i == 10: return lerp(1.14, 1.0, ease_io(seg(t, L[10], L[10] + 1.6))), lerp(960, 960, q), lerp(380, 540, ease_io(seg(t, L[10], L[10] + 1.6)))
    if i == 11: return lerp(1.0, 1.1, ease_io(q)), lerp(960, 1150, q), lerp(540, 660, q)
    if i == 12: return lerp(1.14, 1.0, ease_io(q)), 960, 560
    if i == 13: return 1.06, lerp(800, 1150, ease_io(q)), 600
    if i == 14: return 1.08, lerp(800, 1250, ease_io(q)), lerp(680, 440, ease_io(q))
    if i == 15: return lerp(1.1, 1.0, ease_io(q)), lerp(1100, 960, q), lerp(600, 540, q)
    return 1.0, W / 2, H / 2

def clamp_cam(z, fx, fy):
    hw, hh = W / (2 * z), H / (2 * z)
    return z, clamp(fx, hw, W - hw), clamp(fy, hh, H - hh)

# ------------------------------------------------------------------ transitions into line i
TRANS = {1: "slide_up", 2: "iris_sun", 3: "flash", 4: "wipe_ecg", 5: "wipe_green", 6: "rise_pink", 7: "cut",
         8: "wind", 9: "heart", 10: "box", 11: "crt", 12: "diag", 13: "dark", 14: "slide_down", 15: "white"}
TR_A, TR_B = 0.3, 0.18                # transition spans [L[i]-TR_A, L[i]+TR_B]
TRA = {1: 0.45, 14: 0.75}
def tr_a(i): return TRA.get(i, TR_A)
def tr_q(i, t): return seg(t, L[i] - tr_a(i), L[i] + TR_B)

def offset(i, t):
    """Screen offset of scene i (for sliding transitions)."""
    oy = 0.0
    if 1 <= i < 16 and TRANS.get(i, "").startswith("slide"):
        q = ease_io(tr_q(i, t)); oy += (H if TRANS[i] == "slide_up" else -H) * (1 - q)
    if i + 1 < 16 and TRANS.get(i + 1, "").startswith("slide"):
        q = ease_io(tr_q(i + 1, t)); oy += (-H if TRANS[i + 1] == "slide_up" else H) * q
    return 0.0, oy

def xf(i, t):
    z, fx, fy = clamp_cam(*cam(i, t)); ox, oy = offset(i, t)
    return lambda x, y: ((x - fx) * z + W / 2 + ox, (y - fy) * z + H / 2 + oy), z

# ------------------------------------------------------------------ special moments
FALL_K = 4
FALL_T = ct(5, 5) + 0.05
FALL_X = BASE[5][FALL_K][0]
STAMP_T = ct(6, 7)
HIT_T = ct(6, 9) + LAND + 0.22
LIFT_T, SETTLE_T, POP_T = HIT_T + 0.5, HIT_T + 0.85, HIT_T + 0.78
TRIP_T = ct(7, 3) + 0.05
SQUEEZE_T = ct(13, 5)
FLING_T = ct(13, 8) + 0.35
LATTICE = (380, 430, 400)
SLEEP = (500, LATTICE[1] - LATTICE[2] / 2 - 4)

# ------------------------------------------------------------------ Clawd's path: (time, node, jump style)
STATION = {1: (330, 990, 1.0), 9: (960, 1010, 1.0), 10: (1620, 1000, 1.0), 11: (460, 600, 2.0), 13: (960, 1010, 1.0),
           14: (1598, 236, 0.8), 15: (720, 1010, 1.0)}
def build_nodes():
    n = [(8.3, ("w", 0, SLEEP, 1.0), None)]
    for i in range(16):
        if i == 6: n.append((L[6] - 0.3, ("w", 5, (FALL_X + 70, FLOOR), 1.0), "none"))
        if i in STATION:
            x, y, sc = STATION[i]
            n.append((L[i] + (0.4 if i == 1 else 0.3 if i == 14 else 0.15), ("w", i, (x, y), sc), "fall" if i in (1, 14) else "hop"))
            if i == 13: n.append((FLING_T + 0.45, ("s", 1480, -420), "fling"))
            if i != 15: continue
        for k in range(len(LYR[i])):
            if i == 3 and 1 <= k <= 4: continue
            if i == 5 and k > FALL_K: continue
            if i == 6 and k == 7: continue
            if i == 7 and k >= 3: continue
            if i == 15 and k < 5: continue
            if i == 0 and k % 2 == 1: continue
            style = "hop"
            if i == 0: style = "fall" if k == 0 else "tumble"
            n.append((ct(i, k) + LAND, ("c", i, k), style))
        if i == 7: n.append((TRIP_T, ("w", 7, BALL, 1.0), "trip"))
        if i == 0:
            n.append((ct(0, 8) + LAND + 0.75, ("s", 1560, H + 260), "fall"))      # rolls off 翘, drops out of frame
            n.append((L[1] + 0.05, ("s", 330, -260), "none"))                      # ...and comes in from the top
    return n
NODES = build_nodes()

def node_screen(node, t):
    if node[0] == "s": return node[1], node[2], 1.0
    if node[0] == "c":
        _, i, k = node; f, z = xf(i, t); x, y = char_top(i, k, t); sx, sy = f(x, y); return sx, sy, z
    _, i, (x, y), sc = node; f, z = xf(i, t); sx, sy = f(x, y); return sx, sy, z * sc

def clawd_path(t):
    cur = 0
    for k in range(1, len(NODES)):
        if t >= NODES[k][0]: cur = k
    x, y, z = node_screen(NODES[cur][1], t)
    st = dict(x=x, y=y, z=z, sx=1.0, sy=1.0, rot=0.0, air=None, cur=cur)
    if cur + 1 < len(NODES):
        nt, nn, style = NODES[cur + 1]
        nx, ny, nz = node_screen(nn, t)
        gap = nt - NODES[cur][0]; dist = math.hypot(nx - x, ny - y)
        if style == "fall": dur = min(0.5, gap * 0.9) if nn[0] == "s" else min(0.35, gap * 0.9) if nn[1] == 1 else min(0.6, gap * 0.9)
        elif style == "tumble": dur = gap * 0.72
        elif style == "fling": dur = 0.45
        elif style == "trip": dur = 0.3
        elif style == "none": dur = 0.0
        else: dur = min(max(0.2, dist / 2400), gap * 0.85)
        if dur > 0 and t > nt - dur:
            q = (t - (nt - dur)) / dur
            h = {"hop": 46 + 0.12 * abs(nx - x) + 0.4 * abs(ny - y), "tumble": 40, "fall": 0, "trip": 40, "fling": 160}[style] * z
            st.update(x=lerp(x, nx, q), y=lerp(y, ny, q) - h * 4 * q * (1 - q), z=lerp(z, nz, q), air=(style, q),
                      sx=0.94, sy=1.08)
            if style == "tumble": st["rot"] = -360 * ease_io(q)
            if style == "fling": st["rot"] = -720 * q
            if style == "fall": st["rot"] = -90 - 270 * q if (nn[0] == "c" and nn[1] == 0) else -720 * q
            if style == "trip": st["rot"] = -100 * q
    if st["air"] is None and cur > 0 and NODES[cur][2] not in ("none", None) and NODES[cur][1][0] != "s":
        q = seg(t, NODES[cur][0], NODES[cur][0] + 0.14)
        if q < 1: st["sy"] = 1 - 0.22 * math.sin(math.pi * q); st["sx"] = 2 - st["sy"]
    return st

def line_at(t):
    return int(np.searchsorted(L, t, side="right") - 1)

# ------------------------------------------------------------------ backgrounds
def bg_night_dawn(img, d, t):
    if t < L[0]:
        k = seg(t, 8.38, L[0])
        img.paste(bg_grad(mix((14, 16, 34), (40, 48, 92), k * 0.6), mix((24, 26, 50), (180, 110, 110), ease_in(k))), (0, 0))
        d = ImageDraw.Draw(img)
        for s in range(30):
            x = (s * 397) % W; y = (s * 211) % 600; tw = 0.5 + 0.5 * math.sin(t * 3 + s)
            d.rectangle([x, y, x + 3, y + 3], fill=mix((40, 44, 80), (230, 230, 255), tw * (1 - k)))
        _, bi = beat_phase(t); b0 = int(np.searchsorted(K.BEATS, 8.38))
        lattice(d, LATTICE[0], LATTICE[1], LATTICE[2], LATTICE[2], clamp((bi - b0 + 1) / 14), (92, 60, 48))
        return
    k = seg(t, L[0], L[1])
    img.paste(bg_grad(mix((24, 34, 70), (110, 150, 210), k), mix((180, 110, 110), (252, 206, 150), k)), (0, 0)); d = ImageDraw.Draw(img)
    put(img, K.glow_disc(), LATTICE[0], lerp(900, LATTICE[1] + 20, ease_out(seg(t, L[0], L[0] + 2.6))), 0.8)
    lattice(d, LATTICE[0], LATTICE[1], LATTICE[2], LATTICE[2], 1, (92, 60, 48))

def bg3(img, d, t):
    img.paste(bg_solid(DARK), (0, 0)); d = ImageDraw.Draw(img)
    ecg(d, 0, W, 760, t, ease_out(seg(t, ct(3, 5), ct(3, 7))))
    if ct(3, 1) <= t:
        a = seg(t, ct(3, 1), ct(3, 2)) * (1 - seg(t, ct(3, 5), ct(3, 5) + 0.3))
        for k in range(14): sparkle(d, 540 + (k * 97) % 360, 270 + (k * 61) % 330, 12 * a, (160, 200, 240))

def bg5(img, d, t):
    img.paste(bg_solid(BLUE, dot_c=(60, 104, 240)), (0, 0)); d = ImageDraw.Draw(img)
    if t >= FALL_T:
        q = ease_out(seg(t, FALL_T, FALL_T + 0.25)); bl = ms_blink(t, (ct(5, 9) + 0.5,), 0.1)
        for ex_ in (700, 1220):
            h = 320 * q * bl
            d.rounded_rectangle([ex_ - 90, 240 - h / 2, ex_ + 90, 240 + h / 2], radius=34, fill=(20, 26, 70))
            if h > 80: d.ellipse([ex_ - 46, 240 - h / 2 + 30, ex_ + 4, 240 - h / 2 + 80], fill=WHITE)
        sx = lerp(W + 200, FALL_X + 40, ease_out(seg(t, FALL_T, FALL_T + 0.2)))
        d.polygon([(960, -40), (sx - 170, FLOOR + 60), (sx + 170, FLOOR + 60)], fill=(96, 136, 246))
        d.ellipse([sx - 200, FLOOR - 20, sx + 200, FLOOR + 50], fill=(120, 156, 250))

def bg7(img, d, t):
    img.paste(bg_solid(DARK), (0, 0)); d = ImageDraw.Draw(img)
    if t > TRIP_T:                                   # the thread runs from the ball out through the flung words
        pts = [BALL]
        for k in range(3, 9):
            if t < ct(7, k): break
            x, y, _, _ = pos(7, k, t); pts.append((x, y + 40))
        if len(pts) > 1: d.line(pts, fill=(236, 70, 80), width=6, joint="curve")

def bg8(img, d, t):
    img.paste(bg_solid((226, 236, 220), dot_c=(210, 224, 204)), (0, 0)); d = ImageDraw.Draw(img)
    K.willow(d, t, 0, W, 1.6, strands=[(x, 200 + (k * 97) % 260) for k, x in enumerate(range(30, 1960, 70))])
    for k in range(9):                                # the strands holding the words
        bx = BASE[8][k][0]; x, y, _, _ = pos(8, k, t)
        if t >= ct(8, k): d.line([(bx, 0), (x, y - 60)], fill=(110, 170, 96), width=4)
    for s in range(6):
        p = ((t - L[8]) * 1.1 + s / 6) % 1; y = 950 + s * 18
        d.line([(lerp(-300, W, p), y), (lerp(-300, W, p) + 240, y - 10)], fill=WHITE, width=6)

def bg14(img, d, t):
    img.paste(bg_grad((16, 20, 52), (44, 52, 100)), (0, 0)); d = ImageDraw.Draw(img)
    for s in range(80):
        x = (s * 331) % W; y = (s * 197) % H; tw = 0.5 + 0.5 * math.sin(t * 2.4 + s * 1.3)
        d.rectangle([x, y, x + 3, y + 3], fill=mix((40, 44, 90), (240, 240, 255), tw))
    d.ellipse([1560, 200, 1740, 380], fill=(252, 240, 200)); d.ellipse([1616, 182, 1796, 362], fill=(26, 30, 66))

def bg1(img, d, t):
    img.paste(bg_solid(PAPER, halftone=True), (0, 0)); d = ImageDraw.Draw(img)
    op = ease_out(seg(t, ct(1, 1), ct(1, 2) + 0.3))
    HP.fan(d, 1500, 470, 420, -170 + 20 * (1 - op), -170 + 20 * (1 - op) + 150 * op, (248, 196, 206), (230, 150, 170))
    for k in range(3, 10):                                # laugh ripples push the words out
        p = seg(t, ct(1, k), ct(1, k) + 0.6)
        if 0 < p < 1:
            r = 120 + 700 * ease_out(p); c = mix((236, 150, 170), PAPER, p)
            d.arc([1450 - r, 520 - r, 1450 + r, 520 + r], 150, 230, fill=c, width=max(2, int(8 * (1 - p))))
    p = seg(t, ct(1, 7), ct(1, 7) + 1.1)                  # evening breeze
    if 0 < p < 1:
        for s_ in range(4):
            x = lerp(W + 200, -500, p) + s_ * 90; y = 880 + s_ * 34
            d.arc([x, y, x + 520, y + 120], 200, 340, fill=(170, 186, 226), width=6)
            if s_ == 1:
                for pk in range(5):
                    px = x + 80 + pk * 90; py = y + 20 + 14 * math.sin(pk + t * 6)
                    d.ellipse([px - 10, py - 7, px + 10, py + 7], fill=(250, 190, 205))

CROWD = [(-1, 0.00, (226, 120, 98), 200), (1, 0.05, (120, 150, 210), 230), (-1, 0.12, (150, 196, 140), 180),
         (1, 0.18, (230, 190, 90), 210), (-1, 0.24, (190, 140, 200), 240), (1, 0.30, (236, 150, 170), 190),
         (-1, 0.36, (120, 200, 210), 220), (1, 0.42, (210, 130, 110), 200)]
def person(d, x, feet, h, col, t, k):
    w = h * 0.42; bob = 10 * abs(math.sin(t * 9 + k))
    top = feet - h - bob
    d.rounded_rectangle([x - w / 2, top + h * 0.32, x + w / 2, feet - bob], radius=int(w * 0.35), fill=col)
    d.ellipse([x - w * 0.38, top, x + w * 0.38, top + w * 0.76], fill=mix(col, WHITE, 0.25))
    d.rectangle([x - w * 0.18, top + w * 0.3, x - w * 0.1, top + w * 0.42], fill=INK)
    d.rectangle([x + w * 0.1, top + w * 0.3, x + w * 0.18, top + w * 0.42], fill=INK)
    d.line([(x - w / 2, top + h * 0.5), (x - w * 0.9, top + h * 0.3 - bob)], fill=col, width=int(w * 0.18))
    d.line([(x + w / 2, top + h * 0.5), (x + w * 0.9, top + h * 0.3 - bob)], fill=col, width=int(w * 0.18))

def bg13(img, d, t):
    HP.bg13(img, d, t); d = ImageDraw.Draw(img)
    if t < SQUEEZE_T - 0.1: return
    cx = STATION[13][0]
    for k, (side, delay, col, h) in enumerate(CROWD):
        q = ease_out(seg(t, SQUEEZE_T - 0.1 + delay, FLING_T - 0.1 + delay * 0.5))
        gap = 110 + 70 * (k // 2)
        if t > FLING_T: gap -= 30 * ease_out(seg(t, FLING_T, FLING_T + 0.2))
        x = lerp(cx + side * (1300 + 100 * k), cx + side * gap, q)
        person(d, x, FLOOR + 6, h, col, t, k)

BGS = [bg_night_dawn, bg1, HP.bg2, bg3, HP.bg4, bg5, HP.bg6, bg7, bg8, HP.bg9, HP.bg10, HP.bg11, HP.bg12, bg13, bg14, HP.bg15]

# ------------------------------------------------------------------ one scene (world) -> screen
def draw_words(img, t, i):
    for k, ch in enumerate(LYR[i]):
        if i == 6 and k == 7:
            if t >= SETTLE_T:
                x, y, s, _ = pos(6, 7, t); put(img, seal_img(), x, y, s * 1.15 / 520, 1, -6)
            continue
        t0 = ct(i, k)
        if t < t0: continue
        x, y, s, rot = pos(i, k, t)
        kind = "drop" if i == 12 and k < 3 else "pop"
        sc, a, dx, dy, r = anim(t, t0, kind)
        if (i == 7 and k >= 3) or (i == 1 and k >= 5): sc, a = 1, clamp((t - t0) * 8)
        if i == 15 and k in (3, 4):                   # 相 / 遇 slide in from the sides
            q = ease_out(seg(t, t0, t0 + 0.3)); dx = (-1 if k == 3 else 1) * 700 * (1 - q); sc, a = 1, clamp(q * 3)
        landed = any(nd[1] == ("c", i, k) and nd[0] <= t < nd[0] + 0.16 for nd in NODES)
        if landed:
            nd = [nd for nd in NODES if nd[1] == ("c", i, k)][0]; dy += 12 * math.sin(math.pi * seg(t, nd[0], nd[0] + 0.16))
        c, e = style_of(i, k)
        g = glyph(ch, s, c, 9, e, 6 if (i == 9 and k >= 5) else 0, WHITE if (i == 9 and k >= 5) else None)
        if i == 3 and k >= 7:
            jx = 10 * math.sin(t * 80 + k)
            put(img, glyph(ch, s, (40, 220, 230)), x - 8 + jx, y, sc, a * 0.7, rot)
            put(img, glyph(ch, s, (240, 40, 90)), x + 8 - jx, y, sc, a * 0.7, rot)
        if i == 5 and k in (5, 6):                     # 转头: flip
            fl = abs(math.cos(math.pi * seg(t, t0, t0 + 0.4))) if t < t0 + 0.4 else 1
            g = g.resize((max(1, int(g.width * fl)), g.height))
        put(img, g, x + dx, y + dy, sc, a, rot + r)
        if i in (10, 14) and k in (5, 7):
            s2, a2, *_ = anim(t, t0, "stamp"); put(img, check_img(), x - s * 0.55, y - s * 0.55, s2 * 0.6, a2)

def render_scene(i, t):
    world = Image.new("RGB", (W, H), DARK); d = ImageDraw.Draw(world)
    BGS[i](world, d, t)
    if t >= L[0]: draw_words(world, t, i)
    z, fx, fy = clamp_cam(*cam(i, t))
    if abs(z - 1) < 1e-3 and abs(fx - W / 2) < 0.5 and abs(fy - H / 2) < 0.5: return world
    return world.transform((W, H), Image.AFFINE, (1 / z, 0, fx - W / (2 * z), 0, 1 / z, fy - H / (2 * z)), Image.BICUBIC)

def heart_mask(cx, cy, s):
    m = Image.new("L", (W, H), 0); d = ImageDraw.Draw(m)
    pts = []
    for a in np.linspace(0, 2 * math.pi, 80):
        x = 16 * math.sin(a) ** 3; y = -(13 * math.cos(a) - 5 * math.cos(2 * a) - 2 * math.cos(3 * a) - math.cos(4 * a))
        pts.append((cx + x * s, cy + y * s))
    d.polygon(pts, fill=255); return m

def compose(t):
    if t < 8.38:
        img = Image.new("RGB", (W, H), DARK); K.sc_intro(img, ImageDraw.Draw(img), t)
        return img
    i = max(0, line_at(t))
    nxt = i + 1 if i + 1 < 16 and t >= L[i + 1] - tr_a(i + 1) else None
    if nxt is None and i >= 1 and t < L[i] + TR_B: a_i, b_i = i - 1, i
    elif nxt is not None: a_i, b_i = i, nxt
    else: return render_scene(i, t)
    kind = TRANS[b_i]; q = tr_q(b_i, t)
    A, B = render_scene(a_i, t), render_scene(b_i, t)
    if kind.startswith("slide"):
        out = Image.new("RGB", (W, H), DARK)
        _, oa = offset(a_i, t); _, ob = offset(b_i, t)
        out.paste(A, (0, int(oa))); out.paste(B, (0, int(ob))); return out
    if kind == "cut": return B if q > 0.5 else A
    if kind in ("flash", "white", "dark"):
        c = (20, 20, 19) if kind == "dark" else (255, 252, 246)
        return Image.blend(A, Image.new("RGB", (W, H), c), q * 2) if q < 0.5 else Image.blend(Image.new("RGB", (W, H), c), B, (q - 0.5) * 2)
    m = Image.new("L", (W, H), 0); d = ImageDraw.Draw(m); qe = ease_io(q)
    edge = None
    if kind == "iris_sun":
        r = qe * 2400; d.ellipse([1560 - r, 260 - r, 1560 + r, 260 + r], fill=255)
    elif kind == "wipe_ecg":
        x = qe * (W + 40); d.rectangle([0, 0, x, H], fill=255); edge = ("v", x, RED)
    elif kind == "wipe_green":
        x = W - qe * (W + 40); d.rectangle([x, 0, W, H], fill=255); edge = ("v", x, (70, 140, 70))
    elif kind == "rise_pink":
        y = H - qe * (H + 80)
        d.polygon([(0, H)] + [(x, y + 30 * math.sin(x / 90 + t * 8)) for x in range(0, W + 40, 40)] + [(W, H)], fill=255)
    elif kind == "wind":
        x = W - qe * (W * 1.3)
        d.polygon([(x + 200 * math.sin(y / 120), y) for y in range(0, H + 40, 40)] + [(W, H), (W, 0)], fill=255)
    elif kind == "heart":
        m = heart_mask(960, 520, 0.1 + qe * 90)
    elif kind == "box":
        w, h = qe * W * 0.56, qe * H * 0.56; d.rounded_rectangle([960 - w, 540 - h, 960 + w, 540 + h], radius=20, fill=255)
        edge = ("box", (960 - w, 540 - h, 960 + w, 540 + h), INK)
    elif kind == "diag":
        x = qe * (W + H); d.polygon([(0, 0), (x, 0), (x - H, H), (0, H)], fill=255)
    elif kind == "crt":
        out = Image.new("RGB", (W, H), (8, 8, 8))
        src, k = (A, 1 - q * 2) if q < 0.5 else (B, (q - 0.5) * 2)
        hh = max(2, int(H * ease_io(k)))
        out.paste(src.resize((W, hh)), (0, (H - hh) // 2))
        if hh < 40: ImageDraw.Draw(out).rectangle([0, H / 2 - 3, W, H / 2 + 3], fill=(240, 240, 255))
        return out
    out = Image.composite(B, A, m)
    if edge:
        d2 = ImageDraw.Draw(out)
        if edge[0] == "v": d2.line([(edge[1], 0), (edge[1], H)], fill=edge[2], width=10)
        else: d2.rectangle(edge[1], outline=edge[2], width=8)
    return out

# ------------------------------------------------------------------ actors (screen space): Clawd, the seal, the tangle
MOOD = ["x", "x", "happy", "dot", "normal", "normal", "wide", "wide", "happy", "happy", "normal", "soft",
        "star", "wide", "soft", "happy"]

def draw_actors(img, t):
    d = ImageDraw.Draw(img)
    if t < 8.38: return
    i = max(0, line_at(t))
    st = clawd_path(t); x, y, z = st["x"], st["y"], st["z"]; U = HU * z
    eyes, blush, extra, rot = MOOD[i], 0.45, {}, st["rot"]
    air = st["air"]
    if air and air[0] == "hop": eyes = "happy" if eyes in ("normal", "happy", "x") else eyes
    if air and air[0] in ("tumble", "fall"): eyes = "x" if air[0] == "tumble" or NODES[st["cur"] + 1][1] == ("c", 0, 0) else "wide"
    if air and air[0] == "fling": eyes = "gt"
    if i == 3 and t >= ct(3, 5): eyes = "wide"
    if i == 4: extra["ex"] = 0.4 * math.sin(t * 3)
    if i == 6: blush = 0.45 + 0.55 * seg(t, ct(6, 1), ct(6, 3))
    if i == 9: extra["bow"] = 1.0
    # ---- dozing on the edge of the lattice, swaying, nearly falls, then really falls ----
    if t < ct(0, 0) + LAND - 0.6:
        amp = lerp(4, 14, seg(t, 8.4, 14.0)); rot = amp * math.sin(2 * math.pi * (t - 8.4) / 1.9); eyes = "closed"
        if 11.5 <= t < 12.4:                              # nearly tips over, jolts back
            a_ = ease_out(seg(t, 11.5, 11.85)) * (1 - ease_io(seg(t, 11.95, 12.35)))
            rot = lerp(rot, -38, a_)
            if 11.8 < t < 12.5: eyes = "dot"
        if t >= 14.25: rot = lerp(-12, -90, ease_in(seg(t, 14.25, ct(0, 0) + LAND - 0.6)))
        x += -rot * 0.9 * z
        if not (11.6 < t < 12.6) and t < 14.25:
            for zz in range(3):
                p = ((t - 8.4) * 0.5 + zz / 3) % 1
                put(img, glyph("z", int((22 + 22 * p) * z), (200, 200, 230), kind="s"), x + 60 + 60 * p, y - 120 - 80 * p, 1, 1 - p)
        if 11.8 < t < 12.3:
            put(img, glyph("!", int(56 * z), YEL, kind="s"), x, y - 8 * U - 30, back_out(seg(t, 11.8, 11.95)), 1)
            d.ellipse([x + 7 * U, y - 7 * U, x + 7 * U + 18, y - 7 * U + 22], fill=(120, 182, 238))
        clawd_rot(img, rot, x, y, U, eyes=eyes, blush=0.3); return
    on_station = air is None and NODES[st["cur"]][1][0] == "w" and NODES[st["cur"]][1][1] in STATION
    if on_station and i == 1:                            # dazed after the fall -> the laugh -> evening breeze, a soft blush
        if t < ct(1, 3):
            eyes = "x"
            for kk in range(3):
                a = t * 6 + kk * 2.09; sparkle(d, x + math.cos(a) * 9 * U, y - 9 * U + math.sin(a) * 2 * U, 12, YEL)
        elif t < ct(1, 7): eyes, extra["ex"] = "dot", 0.4
        else:
            eyes, blush = "happy", 0.45 + 0.45 * seg(t, ct(1, 7), ct(1, 8) + 0.4)
        if ct(1, 3) <= t < ct(1, 5): put(img, glyph("?", int(60 * z), (90, 110, 200), kind="s"), x + 20, y - 8 * U - 40, back_out(seg(t, ct(1, 3), ct(1, 3) + 0.15)), 1)
    if on_station and i == 9: st["sy"] = 1 + 0.07 * pulse(t, 6); st["sx"] = 2 - st["sy"]
    if on_station and i == 10: eyes, extra["ex"] = ("happy", 0) if t > ct(10, 5) else ("normal", -0.4)
    if on_station and i == 11:
        eyes = "soft"
        p = seg(t, ct(11, 1), ct(11, 1) + 1.0)
        if 0 < p < 1: d.ellipse([x + 5 * U + 40 * p, y - 7 * U - 40 * p, x + 5 * U + 40 + 60 * p, y - 7 * U + 40 - 40 * p], fill=(230, 230, 236))
    if on_station and i == 13:
        eyes, extra["ex"] = "wide", 0.4 * math.sin(t * 2.5)
        if t >= SQUEEZE_T:
            q = ease_in(seg(t, SQUEEZE_T + 0.1, FLING_T)); st["sx"] = lerp(1.0, 0.5, q); st["sy"] = lerp(1.0, 1.35, q)
            x += 6 * math.sin(t * 60) * q; eyes, blush, extra["ex"] = "gt", 0.9, 0
            for kk in range(1 + int(3 * q)):
                p = ((t - SQUEEZE_T) * 2.6 + kk / 3) % 1; x0 = x + (5 * U if kk % 2 == 0 else -5 * U); y0 = y - 9 * U + 60 * p
                d.ellipse([x0 - 9, y0 - 9, x0 + 9, y0 + 11], fill=(120, 182, 238))
    if on_station and i == 14: eyes, blush = "soft", 0.6
    if on_station and i == 15: eyes, blush = ("happy", 0.9) if t > ct(15, 4) + 0.1 else ("wide", 0.5)
    # ---- caught peeking: falls off 步 ----
    if i == 5 and t >= FALL_T and t < L[6] - 0.3 + 1e-6 or (i == 6 and t < L[6] - 0.3):
        f5, z5 = xf(5, t); bx, by = f5(*char_top(5, FALL_K, t)); flx, fly = f5(FALL_X + 70, FLOOR)
        U = HU * z5
        if t < FALL_T + 0.3:
            clawd(d, bx, by, U=U, eyes="wide", blush=0.9)
            put(img, glyph("!", int(70 * z5), YEL, kind="s"), bx, by - 8 * U - 30, back_out(seg(t, FALL_T, FALL_T + 0.12)), 1); return
        q = seg(t, FALL_T + 0.3, FALL_T + 0.75)
        fx, fy = lerp(bx, flx, q), lerp(by, fly, q * q); rr = -95 * ease_out(q)
        if q >= 1:
            b = seg(t, FALL_T + 0.75, FALL_T + 1.0); fy = fly - 30 * z5 * math.sin(math.pi * b) if b < 1 else fly; rr = -90
            if t > L[6] - 0.6: rr = lerp(-90, 0, ease_io(seg(t, L[6] - 0.6, L[6] - 0.3)))
        clawd_rot(img, rr, fx, fy, U, eyes="x" if q >= 1 and t < L[6] - 0.6 else "wide", blush=0.9,
                  larm=(70 + 30 * math.sin(t * 30), 2.4) if q < 1 else None, rarm=(70 + 30 * math.sin(t * 30 + 2), 2.4) if q < 1 else None)
        if q >= 1 and t < L[6] - 0.6:
            for kk in range(3):
                a = t * 6 + kk * 2.09; sparkle(d, fx + math.cos(a) * 9 * U, fy - 10 * U + math.sin(a) * 2 * U, 12, YEL)
        return
    # ---- tangled in red thread ----
    if i == 7 and t >= TRIP_T and not air:
        wob = 6 * math.sin(t * 12)
        clawd_rot(img, -20 + wob, x, y, U, eyes="x", blush=0.9)
        cy = y - 4 * U
        pts = []
        for kk in range(160):
            a = kk / 160 * 2 * math.pi * 5; r = (1 - 0.25 * math.sin(kk * 0.37)) * 7.5 * U
            pts.append((x + math.cos(a + t) * r, cy + math.sin(a * 1.1) * r * 0.7 + 3 * math.cos(kk * 2.3)))
        n = int(len(pts) * ease_out(seg(t, TRIP_T, TRIP_T + 0.4)))
        if n > 2: d.line(pts[:n], fill=(236, 70, 80), width=5, joint="curve")
        return
    # ---- the 呆 seal ----
    if i == 6 and t >= STAMP_T:
        f6, z6 = xf(6, t); bx, by = f6(*char_top(6, 9, t)); sx7, sy7 = f6(*pos(6, 7, t)[:2]); U = HU * z6
        if t < HIT_T:
            eyes = "wide" if t < STAMP_T + 0.2 else "gt"; blush = 1.0
            if t > STAMP_T + 0.2: extra["larm"] = extra["rarm"] = (70 + 30 * math.sin(t * 40), 2.4)
        elif t < POP_T: x, y, st["sx"], st["sy"], eyes = bx, by, 1.55, 0.16, "x"
        else:
            qq = seg(t, POP_T, POP_T + 0.25); x, y = bx, by
            st["sy"] = lerp(0.16, 1.0, back_out(qq, 2.4)); st["sx"] = lerp(1.55, 1.0, ease_out(qq)); eyes = "dot"
            extra["ahoge"] = back_out(seg(t, POP_T + 0.1, POP_T + 0.3)); extra["t"] = t
        top = clawd(d, x, y, U=U, sx=st["sx"], sy=st["sy"], eyes=eyes, blush=blush, **extra)
        if t < HIT_T:
            for kk in range(1 + int(3 * seg(t, STAMP_T, HIT_T))):
                p = ((t - STAMP_T) * 2.4 + kk / 3) % 1; x0 = x + (8 * U if kk % 2 == 0 else -8 * U); y0 = top + 20 + 80 * p
                d.ellipse([x0 - 9, y0 - 9, x0 + 9, y0 + 11], fill=(120, 182, 238))
            if t < STAMP_T + 0.25: put(img, glyph("!", int(70 * z6), YEL, kind="s"), x, top - 50, back_out(seg(t, STAMP_T, STAMP_T + 0.12)), 1)
        if t >= POP_T:
            put(img, glyph("呆", int(max(18, 54 * z6 * min(1, st["sy"] * 2.5))), RED), x + 2 * U, y - 3.2 * U * st["sy"], 1, 0.85, -8)
        sz = 300 / 520 * z6
        if t < HIT_T:
            hx = lerp(sx7, x, ease_io(seg(t, STAMP_T, HIT_T - 0.15)))
            hy = lerp(-200, 240, ease_out(seg(t, STAMP_T, STAMP_T + 0.3))) + 8 * math.sin(t * 9)
            if t > HIT_T - 0.18: hy = lerp(240, by - 150 * z6, ease_in(seg(t, HIT_T - 0.18, HIT_T)))
            w = 140 * z6 * seg(t, STAMP_T, HIT_T); d.ellipse([hx - w, by - 10, hx + w, by + 12], fill=(0, 0, 0))
            put(img, seal_img(), hx, hy, sz, 1, -6 * (1 - seg(t, HIT_T - 0.18, HIT_T)))
        elif t < LIFT_T:
            put(img, seal_img(), bx, by - 150 * z6, sz, 1)
        elif t < SETTLE_T:
            qq = ease_io(seg(t, LIFT_T, SETTLE_T)); s7 = pos(6, 7, t)[2]
            put(img, seal_img(), lerp(bx, sx7, qq), lerp(by - 150 * z6, sy7, qq) - 160 * math.sin(math.pi * qq),
                lerp(sz, s7 * 1.15 / 520 * z6, qq), 1, -6 * qq)
        if HIT_T <= t < HIT_T + 0.5:
            p = seg(t, HIT_T, HIT_T + 0.5)
            for side in (-1, 1):
                for kk in range(3):
                    r = (16 + 26 * kk) * (0.4 + p) * (1 - p) + 2
                    cx = bx + side * (170 + 50 * kk * p) * z6; cy = by - 10 - 14 * kk * p
                    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(250, 250, 250))
        return
    # ---- normal hopping ----
    if abs(rot) > 0.5:
        clawd_rot(img, rot, x, y, U, sx=st["sx"], sy=st["sy"], eyes=eyes, blush=blush, **extra)
        return
    top = clawd(d, x, y, U=U, sx=st["sx"], sy=st["sy"], eyes=eyes, blush=blush,
                rarm=(50 + 20 * math.sin(t * 10)) if (i == 15 and t > ct(15, 8) + 0.4) else None, **extra)
    if i == 15 and t > ct(15, 8) + 0.5:
        heart_px(d, x, top - 60 - 6 * math.sin(t * 3), 9 * z * back_out(seg(t, ct(15, 8) + 0.5, ct(15, 8) + 0.9)))

def render_frame(fi):
    t = fi / FPS
    img = compose(t)
    if t >= 8.38: draw_actors(img, t)
    arr = np.asarray(img).astype(np.float32) * K.VIG + K.GRAIN[fi % 4]
    if t < 0.6: arr *= t / 0.6
    if 8.2 < t < 8.56: arr *= 0.25 + 0.75 * abs(t - 8.38) / 0.18      # quick dip from the terminal into the night
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
