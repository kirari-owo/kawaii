"""Clawd MV for 呆头鸟 (礼越), 0:00-1:12. Clawd acts the song alone.

The song audio is NOT in the repo; pass its path:
  python3 make_mv.py song.mp3 out.mp4
  python3 make_mv.py song.mp3 preview sheet.png t1 t2 ...
Beat grid: 136 BPM (from librosa), lyric line starts from the song's LRC timing.
"""
import json, math, os, subprocess, sys
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), ".."))
import make_story as ms
from make_story import (W, H, FPS, ORANGE, INK, WHITE, clamp, seg, ease_out, ease_in, ease_io, back_out, lerp, mix,
                        font, text_img, paste, bitmap, clawd, heart, sparkle, sweat, mark, G)

G["none"] = ["........"] * 8
END = 72.6
HERE = os.path.dirname(os.path.abspath(__file__))
BEATS = np.array(json.load(open(os.path.join(HERE, "beats.json")))["beats"])
BEAT = 0.4412
# lyric line start times (from LRC)
L = [15.27, 18.78, 22.32, 25.65, 29.46, 33.18, 36.66, 40.35, 43.95, 47.43, 51.06, 54.15, 58.14, 61.62, 65.13, 68.28]

def beat_phase(t):
    """0..1 position inside the current beat, and the index of that beat."""
    i = int(np.searchsorted(BEATS, t, side="right") - 1)
    if i < 0: return (t / BEAT) % 1, -1
    b0 = BEATS[i]; b1 = BEATS[i + 1] if i + 1 < len(BEATS) else b0 + BEAT
    return clamp((t - b0) / (b1 - b0)), i
def bounce(t, amp=14):
    p, _ = beat_phase(t); return amp * math.sin(math.pi * p) ** 2
def pulse(t, k=8.0):
    p, _ = beat_phase(t); return math.exp(-p * k)

GROUND, RIVER = 1390, 1520
FEET = GROUND + 4
CU = 48                                   # Clawd's pixel size
KS = CU / 40

# ------------------------------------------------------------------ scenery
DAY = dict(top=(150, 205, 238), bot=(232, 244, 240), hill1=(176, 214, 176), hill2=(140, 190, 150), grass=(122, 176, 108),
           grass_d=(98, 150, 90), water=(120, 180, 214), water_l=(176, 220, 238), sun=(255, 246, 214))
DUSK = dict(top=(248, 160, 140), bot=(255, 224, 186), hill1=(214, 170, 160), hill2=(178, 140, 140), grass=(150, 156, 100),
            grass_d=(120, 126, 84), water=(214, 150, 150), water_l=(255, 210, 180), sun=(255, 214, 140))

@lru_cache(None)
def scenery(name):
    P = DAY if name == "day" else DUSK
    im = Image.new("RGB", (W, H)); d = ImageDraw.Draw(im)
    for y in range(0, RIVER):
        d.line([(0, y), (W, y)], fill=mix(P["top"], P["bot"], y / RIVER))
    sy = 520 if name == "day" else 1050
    sx = 250 if name == "day" else 700
    d.ellipse([sx - 90, sy - 90, sx + 90, sy + 90], fill=P["sun"])
    for layer, (base, amp, col, ph) in enumerate([(1080, 70, P["hill1"], 0.3), (1180, 50, P["hill2"], 1.9)]):
        pts = [(x, base - amp * (0.6 * math.sin(x / 210 + ph) + 0.4 * math.sin(x / 97 + 2 * ph))) for x in range(0, W + 20, 20)]
        d.polygon(pts + [(W, RIVER), (0, RIVER)], fill=col)
    d.rectangle([0, GROUND, W, RIVER], fill=P["grass"])
    for x in range(0, W, 26):
        h = 14 + (x * 37) % 17
        d.polygon([(x, GROUND + 4), (x + 8, GROUND - h), (x + 14, GROUND + 4)], fill=P["grass"])
    d.rectangle([0, RIVER - 18, W, RIVER], fill=P["grass_d"])
    d.rectangle([0, RIVER, W, H], fill=P["water"])
    return im

RIPPLES = np.random.default_rng(4).uniform([0, RIVER + 30, 40, 0], [W, H - 20, 140, 6.28], (36, 4))
CLOUDS = [(160, 300, 1.0), (640, 220, 0.8), (930, 420, 1.2)]
def draw_sky_bits(d, t, dusk):
    P = DUSK if dusk > 0.5 else DAY
    cc = mix((255, 255, 255), (255, 236, 226), dusk)
    for x0, y, s in CLOUDS:
        x = (x0 + t * 12 * s) % (W + 300) - 150
        for dx, dy, r in ((0, 0, 50), (55, -18, 62), (115, 0, 48), (60, 18, 46)):
            d.ellipse([x + dx * s - r * s, y + dy * s - r * s, x + dx * s + r * s, y + dy * s + r * s], fill=cc)
    wl = mix(DAY["water_l"], DUSK["water_l"], dusk)
    for x0, y, ln, ph in RIPPLES:
        x = (x0 + t * 30) % (W + 200) - 100
        a = 0.5 + 0.5 * math.sin(t * 2 + ph)
        if a > 0.3: d.line([(x, y), (x + ln * a, y)], fill=wl, width=5)

# willow on the right
TRUNK_X = 870
STRANDS = [(x, 470 + 60 * math.sin(x / 70), 520 + (k * 131) % 360) for k, x in enumerate(range(560, 1120, 26))]
def wind(t):
    w = 0.25 * math.sin(t * 1.3)
    if L[10] <= t < L[11]:               # 风儿吹柳丝轻摇轻摇: big sways on the beat
        p, _ = beat_phase(t); w += 1.4 * math.sin(math.pi * p) * (1 if int((t - L[10]) / (BEAT * 2)) % 2 == 0 else -1)
    if 8 < t < 9.5: w += 0.6 * math.sin(math.pi * seg(t, 8, 9.5))
    return w

def draw_willow(d, t, dusk, front_only=False):
    trunk = mix((120, 88, 64), (110, 76, 64), dusk)
    leaf = mix((112, 170, 92), (150, 150, 86), dusk)
    leaf2 = mix((150, 200, 110), (186, 176, 100), dusk)
    if not front_only:
        w = wind(t)
        for i, (x, y0, ln) in enumerate(STRANDS):
            pts = []
            for k in range(0, 21):
                f = k / 20; yy = y0 + ln * f
                xx = x + (w * 60 + 10 * math.sin(t * 2.2 + i)) * f ** 1.6
                pts.append((xx, yy))
            d.line(pts, fill=leaf, width=4)
            for k in range(2, 21, 2):
                xx, yy = pts[k]; c = leaf2 if (k + i) % 4 else leaf
                d.ellipse([xx - 6, yy - 3, xx + 6, yy + 9], fill=c)
        for cx, cy, r in ((760, 470, 110), (900, 420, 140), (1040, 470, 120), (830, 360, 90), (980, 330, 100)):
            d.ellipse([cx - r, cy - r * 0.7, cx + r, cy + r * 0.7], fill=leaf)
    d.polygon([(TRUNK_X - 34, GROUND + 6), (TRUNK_X - 22, 900), (TRUNK_X - 40, 520), (TRUNK_X + 10, 520),
               (TRUNK_X + 18, 900), (TRUNK_X + 34, GROUND + 6)], fill=trunk)

PETALS = np.random.default_rng(8).uniform([0, 0, 0.6, 0, 20], [W, H, 1.4, 6.28, 60], (70, 5))
def draw_petals(d, t, n=46, storm=0.0):
    w = wind(t)
    for i in range(n):
        x0, y0, s, ph, sp = PETALS[i]
        y = (y0 + t * (60 + sp) * s) % (H + 100) - 50
        x = (x0 + t * (40 + 140 * storm) * s + w * 80 + 30 * math.sin(t * 1.5 + ph)) % (W + 100) - 50
        wdt = 10 * s * abs(math.cos(t * 3 + ph)) + 3; hgt = 8 * s
        d.ellipse([x - wdt, y - hgt, x + wdt, y + hgt], fill=(250, 190, 205) if i % 3 else (255, 220, 228))

# ------------------------------------------------------------------ red thread
RED = (210, 38, 52)
def thread_pts(t, cx, cy, tangle, sag, tug):
    ax, ay = W + 60, 1040                     # the other end, off screen
    hx, hy = cx + 230 * KS, cy + 10                # Clawd's hand side
    pts = []
    for k in range(41):
        f = k / 40
        x = lerp(ax, hx, f); y = lerp(ay, hy, f) + sag * math.sin(math.pi * f) * (1 - tug)
        y += 6 * math.sin(f * 18 + t * 3) * (1 - tug) * (1 - f)
        pts.append((x, y))
    if tangle > 0.01:
        n = int(160 * tangle) + 2
        for k in range(n):
            a = k / 160 * 2 * math.pi * 4.5
            r = 1 - 0.25 * math.sin(k * 0.37)
            x = cx + math.cos(a) * 250 * KS * r + 18 * math.sin(k * 1.7 + t * 2) * tangle
            y = cy - 40 + math.sin(a) * 170 * KS * r * (0.7 + 0.3 * math.cos(k * 0.21)) + 14 * math.cos(k * 2.3)
            pts.append((lerp(hx, x, min(1, tangle * 1.4)), lerp(hy, y, min(1, tangle * 1.4))))
    return pts

def draw_bow(d, x, y, s):
    if s < 0.05: return
    r = 52 * s
    d.ellipse([x - 2.2 * r, y - r, x - 0.2 * r, y + r], outline=RED, width=max(2, int(7 * s)))
    d.ellipse([x + 0.2 * r, y - r, x + 2.2 * r, y + r], outline=RED, width=max(2, int(7 * s)))
    d.ellipse([x - 0.4 * r, y - 0.4 * r, x + 0.4 * r, y + 0.4 * r], fill=RED)
    d.line([(x, y), (x - 0.9 * r, y + 1.9 * r)], fill=RED, width=max(2, int(7 * s)))
    d.line([(x, y), (x + 0.9 * r, y + 1.9 * r)], fill=RED, width=max(2, int(7 * s)))

def ahoge(d, cx, top, s, t):
    if s < 0.05: return
    sw = 8 * math.sin(t * 9)
    pts = [(cx, top), (cx - 6 * s + sw * 0.3, top - 30 * s), (cx + 14 * s + sw, top - 52 * s), (cx + 2 * s + sw, top - 70 * s)]
    d.line(pts, fill=ORANGE, width=max(3, int(14 * s)), joint="curve")

# ------------------------------------------------------------------ frame
def render_frame(fi):
    t = fi / FPS
    dusk = ease_io(seg(t, L[12], L[12] + 2.0))
    img = scenery("day")
    if dusk > 0: img = Image.blend(img, scenery("dusk"), dusk)
    else: img = img.copy()
    d = ImageDraw.Draw(img)
    draw_sky_bits(d, t, dusk)
    draw_willow(d, t, dusk)

    # ---------- Clawd blocking ----------
    cx, eyes, ex, ey, blush, larm, rarm, sx, sy, up = 380, "normal", 0.0, 0.0, 0.0, None, None, 1.0, 1.0, 0.0
    marks = []
    if t < 8.0:                               # stroll in, one hop per beat
        cx = lerp(-260, 380, seg(t, 0.4, 7.6)); up = bounce(t, 26); ex = 0.25
    elif t < L[0]:
        p, i = beat_phase(t)
        ex = [-0.35, -0.35, 0.35, 0.35][(i // 2) % 4] if t < 12 else 0
        ey = -0.35 if 12 < t < 14 else 0
        eyes = "happy" if 13.0 < t < L[0] else "normal"
        up = bounce(t, 8)
    elif t < L[1]:                            # spots someone off screen
        ex, ey = 0.4, 0; eyes = "wide"; marks.append(("!", back_out(seg(t, L[0], L[0] + 0.25)) * (1 - seg(t, L[1] - 0.4, L[1]))))
    elif t < L[2]:
        ex = 0.4; eyes = "normal"; blush = 0.7 * seg(t, L[1], L[1] + 0.8); up = bounce(t, 6)
    elif t < L[3]:                            # pretends to look away, whistles
        ex = -0.4; ey = -0.2; blush = 0.6; larm = rarm = (-35, 2.4); up = bounce(t, 6)
        marks.append(("♪", 1.0))
    elif t < L[4]:
        ex = 0.4; eyes = "happy" if int((t - L[3]) / BEAT) % 4 < 2 else "normal"; blush = 0.8; up = bounce(t, 14)
    elif t < L[5]:                            # inches closer
        cx = lerp(380, 540, seg(t, L[4], L[5] - 0.5)); up = bounce(t, 18); ex = 0.35; blush = 0.6
    elif t < L[6]:                            # loses nerve, backs off
        cx = lerp(540, 320, ease_out(seg(t, L[5], L[5] + 1.2))); eyes = "wide"; blush = 0.8; up = bounce(t, 8)
        marks.append(("sweat", 1.0))
    elif t < L[7]:
        cx = lerp(320, 440, seg(t, L[6], L[7] - 0.4)); ex = 0.35; blush = 0.6; up = bounce(t, 12)
    elif t < L[8]:                            # deep breath before the chorus
        cx = 440; x = seg(t, L[7], L[8] - 0.3)
        sx = 1 + 0.12 * ease_io(x) - 0.12 * ease_in(seg(t, L[8] - 0.3, L[8])); sy = sx
        eyes = "closed"; blush = 0.4
    elif t < L[9]:                            # 呆头鸟: flustered spin, steam, a 呆毛 pops up
        cx = 440; spin = seg(t, L[8], L[8] + 1.8)
        c = math.cos(spin * 2 * math.pi * 2); sx = max(0.08, abs(c))
        eyes = "dot" if c > 0 else "none"; blush = 1.0; up = bounce(t, 16)
        if spin >= 1: sx = 1
        marks.append(("steam", 1.0))
    elif t < L[11]:                           # tangled up in the red thread, wind blowing
        cx = 440 + (20 * wind(t) if t > L[10] else 0); eyes = "wide" if t < L[10] else "x"; blush = 0.9
        larm, rarm = (50 + 30 * math.sin(t * 20), 2.6), (50 + 30 * math.sin(t * 20 + 2), 2.6); up = bounce(t, 8)
    elif t < L[12]:                           # hides behind the (very thin) willow, peeking on the beat
        cx = lerp(440, TRUNK_X + 40, ease_out(seg(t, L[11], L[11] + 0.6)))
        _, i = beat_phase(t); peek = (i % 2 == 0)
        cx -= 70 if peek else 0; ex = -0.45; blush = 0.9; eyes = "normal"
    elif t < L[13]:                           # 风光刚好: steps out into the sunset
        cx = lerp(TRUNK_X - 30, 480, ease_io(seg(t, L[12], L[12] + 1.6))); eyes = "soft"; blush = 0.7; up = bounce(t, 10)
    elif t < L[14]:                           # 缘分奇妙: thread untangles, sparkles
        cx = 480; eyes = "happy"; blush = 0.6; up = bounce(t, 12); ex = 0.2
    elif t < L[15]:                           # tug ... and a tug back
        cx = 480; tg = seg(t, L[14], L[14] + 0.5); back = seg(t, L[14] + 1.6, L[14] + 1.9)
        cx -= 40 * tg * (1 - back); cx += 50 * back * (1 - seg(t, L[14] + 1.9, L[14] + 2.6))
        rarm = (10, 3.0); eyes = "normal" if back < 0.5 else "wide"; ex = 0.4; blush = 0.6
        if back > 0.5: marks.append(("!", back_out(seg(t, L[14] + 1.6, L[14] + 1.85)) * (1 - seg(t, L[15] - 0.4, L[15]))))
    else:                                     # 相遇太巧: bow, heart
        cx = 500; eyes = "happy"; blush = 0.9; up = bounce(t, 14); rarm = (25, 3.0)
        larm = 45 + 20 * math.sin(t * 14) if t > L[15] + 0.5 else None

    feet = FEET - up
    ctop = feet - 8 * CU * abs(sy)
    blink = ms.blinkf(t, (3.0, 10.4, 27.4, 38.2, 60.4, 70.6))

    # thread state
    tangle = 0.0; sag = 120; tug = 0.0; thread_on = t > L[9]
    if L[9] <= t < L[13]: tangle = ease_out(seg(t, L[9], L[9] + 2.4))
    if L[13] <= t < L[13] + 2.2: tangle = 1 - ease_io(seg(t, L[13], L[13] + 2.2))
    if t >= L[14]:
        tug = ease_out(seg(t, L[14], L[14] + 0.5)); sag = 120 * (1 - tug) + 40 * tug
    thread_reveal = ease_out(seg(t, L[9], L[9] + 0.8))

    if t >= L[11] and t < L[12]:              # behind the trunk
        clawd(d, cx=cx, feet=feet, U=CU, sx=sx, sy=sy, eyes=eyes, ex=ex, ey=ey, blush=blush, larm=larm, rarm=rarm,
              blink=blink if eyes == "normal" else 1)
        draw_willow(d, t, dusk, front_only=True)
        hp = 1 + 0.35 * pulse(t)
        heart(d, cx - 40, feet - 4 * CU, 9 * hp)
    else:
        clawd(d, cx=cx, feet=feet, U=CU, sx=sx, sy=sy, eyes=eyes, ex=ex, ey=ey, blush=blush, larm=larm, rarm=rarm,
              blink=blink if eyes == "normal" else 1)

    if thread_on:
        pts = thread_pts(t, cx, feet - 4 * CU, tangle, sag, tug)
        n = max(2, int(len(pts) * thread_reveal)) if t < L[9] + 0.8 else len(pts)
        if t < L[9] + 0.8: pts = pts[:n]
        d.line(pts, fill=RED, width=6, joint="curve")
        if t >= L[15]:
            draw_bow(d, lerp(W + 60, cx + 230 * KS, 0.5), lerp(1040, feet - 180, 0.5) + 40 * (1 - tug), back_out(seg(t, L[15], L[15] + 0.5)))

    # little extras
    for kind, s in marks:
        if kind == "!": mark(img, "!", cx + 20, ctop - 40, s)
        elif kind == "♪":
            for k in range(3):
                p = ((t - L[2]) * 0.8 + k / 3) % 1
                mark(img, "♪", cx - 160 - 60 * p, ctop - 20 - 160 * p, 0.6 * (1 - p) + 0.2, color=(90, 110, 170))
        elif kind == "sweat": sweat(d, cx + 230, ctop + 40, 1.0)
        elif kind == "steam":
            for k in range(4):
                p = ((t - L[8]) * 1.2 + k / 4) % 1
                r = 14 + 26 * p; x = cx + (k - 1.5) * 90 + 20 * math.sin(p * 6); y = ctop - 20 - 160 * p
                d.ellipse([x - r, y - r, x + r, y + r], fill=mix((255, 255, 255), (230, 236, 240), p))
    if L[8] <= t < L[13]: ahoge(d, cx, ctop, back_out(seg(t, L[8] + 0.2, L[8] + 0.5)), t)
    if L[13] <= t < L[14]:
        for k in range(6):
            a = k * 1.05 + t * 1.5; r = 300 + 30 * math.sin(t * 4 + k)
            sparkle(d, cx + math.cos(a) * r, ctop + 120 + math.sin(a) * r * 0.5, 14 * (0.6 + 0.4 * pulse(t, 5)), (255, 214, 120))
    if 12.0 < t < L[0] + 1.0:                 # a petal lands on Clawd's head
        x = seg(t, 12.0, 13.4); px = lerp(cx + 260, cx + 40, x); py = lerp(ctop - 300, ctop - 12, ease_out(x))
        if t > 13.4: px, py = cx + 40, ctop - 12
        d.ellipse([px - 12, py - 8, px + 12, py + 8], fill=(250, 190, 205))
    if t >= L[15]:
        p = seg(t, L[15] + 0.3, L[15] + 0.8)
        heart(d, cx, ctop - 80 - 8 * math.sin(t * 3), 11 * back_out(p) * (1 + 0.2 * pulse(t)))
    storm = 1.0 if L[10] <= t < L[11] else (0.6 if t >= L[12] else 0.0)
    draw_petals(d, t, 46 if t < L[8] else 60 if t < L[12] else 70, storm)

    # gentle vignette pulse on chorus downbeats
    if L[8] <= t < END and pulse(t, 10) > 0.6 and int((t - L[8]) / BEAT + 0.5) % 4 == 0:
        img = Image.blend(img, Image.new("RGB", (W, H), (255, 240, 236)), 0.06 * pulse(t, 10))
    if t < 0.7: img = Image.blend(img, Image.new("RGB", (W, H), ms.DIP), 1 - t / 0.7)
    if t > END - 1.2: img = Image.blend(img, Image.new("RGB", (W, H), ms.DIP), clamp((t - END + 1.2) / 1.1))
    return img

def frame_bytes(fi): return render_frame(fi).tobytes()

if __name__ == "__main__":
    song = sys.argv[1]
    if sys.argv[2] == "preview":
        out, times = sys.argv[3], [float(x) for x in sys.argv[4:]]
        th = [render_frame(int(x * FPS)).resize((270, 480)) for x in times]
        cols = min(6, len(th)); rows = (len(th) + cols - 1) // cols
        sheet = Image.new("RGB", (270 * cols, 480 * rows))
        for k, im in enumerate(th): sheet.paste(im, ((k % cols) * 270, (k // cols) * 480))
        sheet.save(out); sys.exit()
    OUT = sys.argv[2]
    n = int(END * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-t", str(END), "-i", song,
                           "-af", f"afade=t=in:st=0:d=0.4,afade=t=out:st={END - 1.4}:d=1.4",
                           "-map", "0:v", "-map", "1:a", "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "256k", "-shortest", "-movflags", "+faststart", OUT],
                          stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for b in pool.imap(frame_bytes, range(n), chunksize=8): ff.stdin.write(b)
    ff.stdin.close(); ff.wait(); print("wrote", OUT)
