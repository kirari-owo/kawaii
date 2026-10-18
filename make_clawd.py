"""Clawd peeks up from the bottom of the screen and says hi. Renders an MP4 with synthesized SFX."""
import math, os, subprocess, sys, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont

OUT = sys.argv[1] if len(sys.argv) > 1 else "clawd_hi.mp4"
W = H = 1080
SS = 2                      # supersampling
FPS = 30
DUR = 6.6
SR = 44100
TMP = os.path.join(os.path.dirname(os.path.abspath(OUT)), "_frames")
os.makedirs(TMP, exist_ok=True)

BG = (244, 239, 230)
DOT = (226, 218, 205)
ORANGE = (217, 119, 87)
ORANGE_D = (191, 98, 70)
EYE = (30, 24, 20)
STRIP = (31, 30, 29)
STRIP_HI = (60, 57, 54)
TXT = (232, 226, 216)
U = 44                      # one "pixel" of Clawd, in output px
EDGE_Y = 800                # top of the bottom strip
CX = 540

FONT_B = "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf"
FONT_M = "/usr/share/fonts/truetype/dejavu/DejaVuSansMono-Bold.ttf"
f_bubble = ImageFont.truetype(FONT_B, 92 * SS)
f_term = ImageFont.truetype(FONT_M, 40 * SS)

def clamp(x, a=0.0, b=1.0): return max(a, min(b, x))
def seg(t, a, b): return clamp((t - a) / (b - a))
def ease_out(x): return 1 - (1 - x) ** 3
def ease_in(x): return x ** 3
def ease_io(x): return 3 * x * x - 2 * x * x * x
def back_out(x, s=1.9): x -= 1; return x * x * ((s + 1) * x + s) + 1
def lerp(a, b, x): return a + (b - a) * x

# ---------------------------------------------------------------- timeline
TYPE_TEXT = "> hello, world!"
TYPE_T0, TYPE_DT = 3.45, 0.075

def state(t):
    """visible = how many units of Clawd are above the edge (8 = feet on edge)."""
    sx = sy = 1.0
    vis = 0.0
    if t < 0.7: vis = -0.5
    elif t < 1.2: vis = lerp(-0.5, 3.0, ease_out(seg(t, 0.7, 1.2)))
    elif t < 2.4: vis = 3.0 + 0.12 * math.sin((t - 1.2) * 6)
    elif t < 2.55:
        vis = lerp(3.0, 2.4, ease_out(seg(t, 2.4, 2.55))); sy = lerp(1, 0.9, seg(t, 2.4, 2.55)); sx = 2 - sy
    elif t < 2.85:
        x = seg(t, 2.55, 2.85); vis = lerp(2.4, 9.6, ease_out(x)); sy = lerp(1.15, 1.0, x); sx = 2 - sy
    elif t < 3.05: vis = lerp(9.6, 8.0, ease_in(seg(t, 2.85, 3.05)))
    elif t < 5.6:
        vis = 8.0
        x = seg(t, 3.05, 3.35)
        sy = 1 - 0.16 * math.exp(-x * 4) * math.cos(x * 9); sx = 2 - sy
        sy += 0.015 * math.sin((t - 3.05) * 2 * math.pi * 2.5) if t > 3.4 else 0
    elif t < 5.75:
        x = seg(t, 5.6, 5.75); vis = 8.0; sy = lerp(1, 0.88, ease_out(x)); sx = 2 - sy
    elif t < 6.2:
        x = seg(t, 5.75, 6.2)
        vis = 8.0 + 1.3 * math.sin(x * math.pi) - 9.0 * ease_in(x)
        sy = 1.06; sx = 0.95
    else: vis = -2
    # eyes: look around while peeking
    ex = 0
    if 1.45 < t < 1.85: ex = -1
    elif 1.85 < t < 2.25: ex = 1
    blink = 1.0
    for bt in (1.3, 4.75):
        d = abs(t - bt)
        if d < 0.08: blink = 0.15 + 0.85 * d / 0.08
    if 5.75 < t < 6.2: blink = 0.15     # squeeze eyes shut when diving
    # arm wave
    arm = None
    if 3.2 < t < 5.55:
        up = ease_out(seg(t, 3.2, 3.4)) * (1 - ease_io(seg(t, 5.35, 5.55)))
        wav = math.sin((t - 3.4) * 2 * math.pi * 2.5) if t > 3.4 else 0
        arm = up * (55 + 20 * wav)     # degrees above horizontal
    bub = 0.0
    if t > 3.25:
        bub = back_out(seg(t, 3.25, 3.55)) * (1 - ease_in(seg(t, 5.4, 5.6)))
    return vis, sx, sy, ex, blink, arm, bub

# ---------------------------------------------------------------- drawing
def S(v): return int(round(v * SS))

def draw_clawd(d, vis, sx, sy, ex, blink, arm):
    feet = EDGE_Y + (8 - vis) * U        # y of bottom of legs
    def P(u, v):                          # unit coords (u: 0..12, v: 0..8 from top) -> px
        return CX + (u - 6) * U * sx, feet - (8 - v) * U * sy
    def R(u0, v0, u1, v1, c):
        x0, y0 = P(u0, v0); x1, y1 = P(u1, v1)
        d.rectangle([S(x0), S(y0), S(x1) - 1, S(y1) - 1], fill=c)
    # legs
    for lu in (2, 4, 7, 9):
        R(lu, 6, lu + 1, 8, ORANGE)
    # body
    R(1, 0, 11, 6, ORANGE)
    R(1, 5.6, 11, 6, ORANGE_D)
    # left arm (static)
    R(0, 3, 1, 4, ORANGE)
    # right arm
    if arm is None or arm < 3:
        R(11, 3, 12, 4, ORANGE)
    else:
        px, py = P(11.2, 3.5)
        a = math.radians(arm)
        L, Th = 3.4 * U * sx, U * sy
        ux, uy = math.cos(a), -math.sin(a)
        nx, ny = -uy, ux
        sx0, sy0 = px - ux * 0.4 * U, py - uy * 0.4 * U
        pts = [(sx0 + nx * Th / 2, sy0 + ny * Th / 2), (sx0 + ux * L + nx * Th / 2, sy0 + uy * L + ny * Th / 2),
               (sx0 + ux * L - nx * Th / 2, sy0 + uy * L - ny * Th / 2), (sx0 - nx * Th / 2, sy0 - ny * Th / 2)]
        d.polygon([(S(x), S(y)) for x, y in pts], fill=ORANGE)
        R(10.6, 3, 11.05, 4, ORANGE)
    # eyes
    eh = 2 * blink
    for eu in (3, 8):
        R(eu + ex, 1 + (2 - eh) / 2, eu + ex + 1, 1 + (2 - eh) / 2 + eh, EYE)

def draw_bubble(img, s):
    if s <= 0.01: return
    bw, bh = 300, 170
    ax, ay = CX + 300, EDGE_Y - 8 * U - 70          # anchor = tail tip
    layer = Image.new("RGBA", (S(bw + 40), S(bh + 70)), (0, 0, 0, 0))
    ld = ImageDraw.Draw(layer)
    ld.rounded_rectangle([S(20), S(10), S(20 + bw), S(10 + bh)], radius=S(46), fill=(255, 255, 255), outline=EYE, width=S(7))
    ld.polygon([(S(60), S(10 + bh - 8)), (S(110), S(10 + bh - 8)), (S(50), S(10 + bh + 52))], fill=(255, 255, 255))
    ld.line([(S(60), S(10 + bh - 3)), (S(50), S(10 + bh + 52)), (S(110), S(10 + bh - 3))], fill=EYE, width=S(7), joint="curve")
    ld.text((S(20 + bw / 2), S(10 + bh / 2)), "Hi!", font=f_bubble, fill=ORANGE_D, anchor="mm")
    nw, nh = max(1, int(layer.width * s)), max(1, int(layer.height * s))
    layer = layer.resize((nw, nh), Image.LANCZOS)
    tipx, tipy = S(50) * s, S(10 + bh + 52) * s
    img.alpha_composite(layer, (int(S(ax - 120) - tipx + S(120) * 0 ), int(S(ay) - tipy)))

def sparkles(d, t):
    if not (2.8 < t < 3.5): return
    x = seg(t, 2.8, 3.5)
    for i, ang in enumerate((200, 235, 305, 340, 270)):
        a = math.radians(ang)
        r = 230 + 160 * ease_out(x)
        px = CX + math.cos(a) * r; py = EDGE_Y - 4 * U + math.sin(a) * r * 0.9
        sz = 18 * (1 - x) * (1.2 if i % 2 else 0.8)
        if sz < 1: continue
        c = ORANGE if i % 2 else (240, 180, 70)
        d.rectangle([S(px - sz / 3), S(py - sz), S(px + sz / 3), S(py + sz)], fill=c)
        d.rectangle([S(px - sz), S(py - sz / 3), S(px + sz), S(py + sz / 3)], fill=c)

def make_bg():
    bg = Image.new("RGBA", (S(W), S(H)), BG + (255,))
    d = ImageDraw.Draw(bg)
    for y in range(30, EDGE_Y, 54):
        for x in range(30, W, 54):
            d.ellipse([S(x - 3), S(y - 3), S(x + 3), S(y + 3)], fill=DOT)
    return bg

def draw_strip(d, t):
    d.rectangle([0, S(EDGE_Y), S(W), S(H)], fill=STRIP)
    d.rectangle([0, S(EDGE_Y), S(W), S(EDGE_Y + 8)], fill=STRIP_HI)
    n = 2 if t < TYPE_T0 else min(len(TYPE_TEXT), 2 + int((t - TYPE_T0) / TYPE_DT))
    s = TYPE_TEXT[:n]
    x0, y0 = 90, EDGE_Y + 120
    d.text((S(x0), S(y0)), s[:1], font=f_term, fill=ORANGE, anchor="lm")
    d.text((S(x0) + f_term.getlength("> "), S(y0)), s[2:], font=f_term, fill=TXT, anchor="lm")
    if int(t * 2.5) % 2 == 0 or (TYPE_T0 < t < TYPE_T0 + TYPE_DT * len(TYPE_TEXT)):
        cx = S(x0) + f_term.getlength(s)
        d.rectangle([cx + S(4), S(y0 - 24), cx + S(26), S(y0 + 24)], fill=TXT)

def render():
    bg = make_bg()
    n = int(DUR * FPS)
    for i in range(n):
        t = i / FPS
        img = bg.copy()
        d = ImageDraw.Draw(img)
        vis, sx, sy, ex, blink, arm, bub = state(t)
        sparkles(d, t)
        if vis > -1.5:
            draw_clawd(d, vis, sx, sy, ex, blink, arm)
        draw_strip(d, t)
        draw_bubble(img, bub)
        img.convert("RGB").resize((W, H), Image.LANCZOS).save(f"{TMP}/f{i:04d}.png")

# ---------------------------------------------------------------- audio
N = int(DUR * SR)
audio = np.zeros(N)
rng = np.random.default_rng(7)

def add(sig, t0, gain=1.0):
    i = int(t0 * SR); j = min(N, i + len(sig))
    audio[i:j] += sig[: j - i] * gain

def tt(d): return np.arange(int(d * SR)) / SR
def sweep(f0, f1, d, shape=1.0):
    t = tt(d); f = f0 + (f1 - f0) * (t / d) ** shape
    return np.sin(2 * np.pi * np.cumsum(f) / SR)
def env(n, a=0.005, r=None):
    t = np.arange(n) / SR; e = np.minimum(1, t / a)
    if r: e *= np.exp(-t / r)
    fade = min(n, int(0.01 * SR)); e[-fade:] *= np.linspace(1, 0, fade)
    return e
def lowpass(x, k):
    k = max(1, int(k)); return np.convolve(x, np.ones(k) / k, mode="same")

def bloop(f0, f1, d):
    s = sweep(f0, f1, d, 0.6); return s * env(len(s), 0.01, d / 2.5)
def blip(f, d=0.05):
    t = tt(d); s = np.sign(np.sin(2 * np.pi * f * t)) * 0.4 + np.sin(2 * np.pi * f * t) * 0.6
    return lowpass(s, 4) * env(len(s), 0.002, d / 3)
def boing(d=0.55):
    t = tt(d); f = 180 + 520 * (1 - np.exp(-t * 9)) + 60 * np.sin(2 * np.pi * 14 * t) * np.exp(-t * 5)
    s = np.sin(2 * np.pi * np.cumsum(f) / SR) + 0.3 * np.sin(4 * np.pi * np.cumsum(f) / SR)
    return s * env(len(s), 0.004, 0.22)
def thump():
    t = tt(0.18); s = np.sin(2 * np.pi * np.cumsum(140 * np.exp(-t * 18) + 55) / SR)
    return s * env(len(s), 0.002, 0.05)
def pop():
    t = tt(0.09); s = sweep(1500, 500, 0.09) * 0.8 + lowpass(rng.standard_normal(len(t)), 3) * 0.25
    return s * env(len(s), 0.001, 0.02)
def bell(f, d=0.9):
    t = tt(d); s = sum(a * np.sin(2 * np.pi * f * m * t) for m, a in ((1, 1), (2, 0.35), (3.01, 0.15), (4.2, 0.06)))
    return s * env(len(s), 0.003, 0.25)
def whoosh(d=0.22):
    n = int(d * SR); s = lowpass(rng.standard_normal(n), 30) * np.sin(np.linspace(0, np.pi, n)) ** 2
    return s / (np.abs(s).max() + 1e-9)
def tick():
    s = lowpass(rng.standard_normal(int(0.025 * SR)), 2) * 0.5 + blip(2400, 0.025) * 0.5
    return s * env(len(s), 0.0005, 0.006)

add(bloop(260, 620, 0.32), 0.72, 0.55)                 # peek up
add(blip(880), 1.47, 0.35); add(blip(1180), 1.87, 0.35)  # eye darts
add(blip(1500, 0.03), 1.29, 0.15)                       # blink
add(bloop(400, 300, 0.12), 2.40, 0.3)                   # crouch
add(boing(), 2.55, 0.55)                                 # jump!
add(thump(), 3.04, 0.9)                                  # land
add(pop(), 3.27, 0.6)                                    # bubble
for k, f in enumerate((1046.5, 1318.5, 1568.0, 2093.0)): # hi! chime
    add(bell(f), 3.30 + k * 0.075, 0.28)
for k in range(5):                                       # wave swishes
    add(whoosh(), 3.42 + k * 0.4, 0.12)
for k in range(len(TYPE_TEXT) - 2):                       # typing
    add(tick(), TYPE_T0 + (k + 1) * TYPE_DT, 0.35 + 0.1 * rng.random())
add(blip(1500, 0.03), 4.74, 0.15)                       # blink
add(bloop(500, 380, 0.1), 5.6, 0.3)                     # crouch
add(bloop(700, 150, 0.4) , 5.8, 0.5)                    # dive down
add(pop(), 6.18, 0.35)

# tiny room reverb
rev = np.zeros_like(audio)
for dl, g in ((0.031, 0.25), (0.047, 0.18), (0.071, 0.12), (0.103, 0.08)):
    k = int(dl * SR); rev[k:] += audio[:-k] * g
audio = audio + lowpass(rev, 6)
audio = audio / np.abs(audio).max() * 0.85
L = audio; Rch = np.roll(audio, 12)
pcm = (np.stack([L, Rch], 1) * 32767).astype(np.int16)
wav_path = os.path.join(TMP, "sfx.wav")
with wave.open(wav_path, "wb") as w:
    w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(pcm.tobytes())

render()
subprocess.run(["ffmpeg", "-y", "-loglevel", "error", "-framerate", str(FPS), "-i", f"{TMP}/f%04d.png", "-i", wav_path,
                "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", "-c:a", "aac", "-b:a", "192k",
                "-shortest", "-movflags", "+faststart", OUT], check=True)
print("wrote", OUT)
