"""Clawd tucks you in — a short animation for 家克's 'good night' voice clip.

  python3 make_goodnight.py voice.mp3 out.mp4
  python3 make_goodnight.py voice.mp3 preview sheet.png t1 t2 ...
"""
import math, os, subprocess, sys, wave
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw, ImageFilter

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "mv"))
import make_ktv as K
from make_ktv import (W, H, FPS, clamp, seg, ease_out, ease_in, ease_io, back_out, lerp, mix, F, glyph, put, clawd,
                      sparkle, heart_px, INK, OR, WHITE, YEL)

VOICE = sys.argv[1]
END = 13.6
SR = 44100

# voice timing (from speech recognition): "好" "好" ... "十分钟" ... "好" "晚安" "真的"
T_OK1, T_OK2, T_BUT, T_TEN, T_OK3, T_NIGHT, T_REAL, T_OFF = 0.0, 1.2, 2.68, 5.96, 7.96, 9.44, 10.88, 11.45

def load_env():
    raw = subprocess.run(["ffmpeg", "-v", "error", "-i", VOICE, "-ac", "1", "-ar", str(SR), "-f", "f32le", "-"],
                         capture_output=True, check=True).stdout
    a = np.frombuffer(raw, dtype=np.float32)
    hop = SR // FPS
    env = np.array([np.sqrt(np.mean(a[i:i + hop] ** 2)) for i in range(0, len(a), hop)])
    env = env / (env.max() + 1e-9)
    return np.convolve(env, np.ones(3) / 3, mode="same"), a
ENV, VOICE_PCM = load_env()
def talk(t):
    i = int(t * FPS); return float(ENV[i]) if 0 <= i < len(ENV) else 0.0

# ------------------------------------------------------------------ room
WALL, WALL_D = (36, 42, 76), (30, 35, 64)
def room(t, light):
    im = Image.new("RGB", (W, H), WALL); d = ImageDraw.Draw(im)
    for y in range(30, H, 60):
        for x in range(30 + (y // 60 % 2) * 30, W, 60):
            d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=WALL_D)
    # window with moon
    d.rectangle([190, 150, 630, 590], fill=(92, 66, 54))
    d.rectangle([214, 174, 606, 566], fill=(18, 22, 48))
    for s in range(26):
        x = 230 + (s * 97) % 360; y = 190 + (s * 61) % 360; tw = 0.5 + 0.5 * math.sin(t * 2.3 + s)
        d.rectangle([x, y, x + 3, y + 3], fill=mix((40, 44, 80), (240, 240, 255), tw))
    d.ellipse([440, 220, 560, 340], fill=(250, 238, 196)); d.ellipse([474, 206, 594, 326], fill=(18, 22, 48))
    d.line([(410, 174), (410, 566)], fill=(92, 66, 54), width=14); d.line([(214, 370), (606, 370)], fill=(92, 66, 54), width=14)
    for side in (-1, 1):                          # curtains
        x0 = 150 if side < 0 else 590
        d.polygon([(x0, 120), (x0 + 90, 120), (x0 + 60 + 10 * math.sin(t * 0.8), 640), (x0 - 10, 640)], fill=(150, 96, 120))
    d.rectangle([140, 110, 680, 128], fill=(120, 84, 64))
    # wall clock
    cx, cy, r = 1290, 270, 110
    d.ellipse([cx - r - 10, cy - r - 10, cx + r + 10, cy + r + 10], fill=(120, 84, 64))
    d.ellipse([cx - r, cy - r, cx + r, cy + r], fill=(244, 238, 226))
    for k in range(12):
        a = k * math.pi / 6; d.line([(cx + math.cos(a) * r * 0.82, cy + math.sin(a) * r * 0.82), (cx + math.cos(a) * r * 0.94, cy + math.sin(a) * r * 0.94)], fill=INK, width=5)
    mins = 50 + 10 * ease_io(seg(t, T_BUT + 0.6, T_TEN + 0.6))          # 11:50 -> 12:00, ten minutes gone
    am = mins / 60 * 2 * math.pi - math.pi / 2; ah = (11 + mins / 60) / 12 * 2 * math.pi - math.pi / 2
    d.line([(cx, cy), (cx + math.cos(ah) * r * 0.5, cy + math.sin(ah) * r * 0.5)], fill=INK, width=10)
    d.line([(cx, cy), (cx + math.cos(am) * r * 0.78, cy + math.sin(am) * r * 0.78)], fill=(214, 70, 60), width=6)
    d.ellipse([cx - 10, cy - 10, cx + 10, cy + 10], fill=INK)
    # nightstand + lamp
    d.rectangle([1440, 760, 1760, 1080], fill=(110, 78, 62)); d.rectangle([1440, 760, 1760, 790], fill=(130, 94, 74))
    d.rectangle([1590, 640, 1610, 760], fill=(200, 180, 150))
    shade = mix((120, 110, 100), (255, 214, 150), light)
    d.polygon([(1520, 650), (1680, 650), (1640, 540), (1560, 540)], fill=shade)
    d.rectangle([1500, 755, 1700, 762], fill=(90, 64, 50))
    return im

GLOW = None
def lamp_glow():
    global GLOW
    if GLOW is None:
        r = 720; yy, xx = np.mgrid[0:2 * r, 0:2 * r]
        dd = np.sqrt((xx - r) ** 2 + (yy - r) ** 2) / r
        a = (np.clip(1 - dd, 0, 1) ** 1.8 * 120).astype(np.uint8)
        arr = np.zeros((2 * r, 2 * r, 4), np.uint8); arr[..., 0] = 255; arr[..., 1] = 196; arr[..., 2] = 130; arr[..., 3] = a
        GLOW = Image.fromarray(arr, "RGBA")
    return GLOW

def blanket(d, top, t):
    pts = [(x, top + 16 * math.sin(x / 140 + 0.6) + 6 * math.sin(t * 1.5 + x / 300)) for x in range(-20, W + 40, 40)]
    d.polygon(pts + [(W + 40, H + 40), (-20, H + 40)], fill=(238, 196, 204))
    d.line(pts, fill=(250, 226, 230), width=10)
    for x in range(80, W, 220):                   # quilt stitching
        y = top + 90 + 16 * math.sin(x / 140 + 0.6)
        d.line([(x, y), (x + 120, y)], fill=(222, 170, 182), width=4)
    if top + 200 < H: d.rectangle([-20, top + 200, W + 40, H + 40], fill=(232, 186, 196))

def nightcap(d, cx, top, U, sx, t, droop):
    w = 10 * U * sx
    tip = (cx + 3.2 * U * sx + 1.2 * U * math.sin(t * 2) + droop * U, top - 3.4 * U + droop * 1.2 * U)
    d.polygon([(cx - w * 0.46, top + 0.3 * U), (cx + w * 0.46, top + 0.3 * U), tip], fill=(96, 126, 214))
    d.rounded_rectangle([cx - w * 0.52, top - 0.2 * U, cx + w * 0.52, top + 0.9 * U], radius=int(0.4 * U), fill=(246, 244, 240))
    d.ellipse([tip[0] - 0.6 * U, tip[1] - 0.6 * U, tip[0] + 0.6 * U, tip[1] + 0.6 * U], fill=(246, 244, 240))

# ------------------------------------------------------------------ frame
def render_frame(fi):
    t = fi / FPS
    light = 1 - seg(t, T_OFF, T_OFF + 0.06)
    img = room(t, light)
    if light > 0.5: img.paste(lamp_glow(), (1600 - 720, 600 - 720), lamp_glow())
    d = ImageDraw.Draw(img)

    # ---- Clawd ----
    U = 38; cx = 960; feet = 975 - 40 * ease_io(seg(t, T_NIGHT - 0.4, T_NIGHT + 0.6))   # leans in over the bed
    v = talk(t)
    eyes, blush, ex, ey, la, ra, sx, sy = "soft", 0.35, 0.0, 0.0, None, None, 1.0, 1.0
    nod = 0.0
    for tn in (T_OK1 + 0.05, T_OK2):                       # 好，好 — two gentle nods
        q = seg(t, tn, tn + 0.45); nod += 14 * math.sin(math.pi * q) if 0 < q < 1 else 0
    if T_BUT <= t < T_OK3:                                 # "…ten minutes already" — hands on hips, deadpan
        eyes = "dot" if t > T_BUT + 0.3 else "normal"; la = ra = (-50, 2.2); blush = 0.2
        ex = 0.25 * math.sin((t - T_BUT) * 1.5) if t < T_TEN else 0
    if T_OK3 <= t < T_NIGHT:                                # big sigh, then a soft smile
        q = seg(t, T_OK3, T_OK3 + 0.6); sy = 1 - 0.1 * math.sin(math.pi * q); sx = 2 - sy
        eyes = "closed" if t < T_OK3 + 0.6 else "happy"; blush = 0.45
    if T_NIGHT <= t:                                        # tucks you in
        eyes = "soft"; blush = 0.6
        la = ra = (lerp(-20, -48, ease_out(seg(t, T_NIGHT - 0.3, T_NIGHT + 0.6))), 2.8)
    if T_REAL <= t:
        q = seg(t, T_REAL, T_REAL + 0.35); nod += 18 * math.sin(math.pi * q) if 0 < q < 1 else 0
        if t > T_REAL + 0.2: ra = (lerp(-48, 5, ease_io(seg(t, T_REAL + 0.2, T_OFF))), lerp(3.0, 6.2, ease_io(seg(t, T_REAL + 0.2, T_OFF))))
        if t > T_OFF + 0.2: ra = (lerp(5, -48, ease_io(seg(t, T_OFF + 0.2, T_OFF + 0.7))), 2.8); eyes = "soft"
    sy *= 1 + 0.05 * v                                      # talking: a little puff with the voice
    sx *= 1 - 0.025 * v
    blink = K.ms_blink(t, (3.3, 8.7, 12.6), 0.1)
    if eyes in ("soft", "happy", "closed"): blink = 1
    top = clawd(d, cx, feet + nod, U=U, sx=sx, sy=sy, eyes=eyes, ex=ex, ey=ey, blush=blush, larm=la, rarm=ra, blink=blink)
    nightcap(d, cx, top, U, sx, t, droop=ease_io(seg(t, T_OK3, T_OK3 + 0.6)) * (1 - seg(t, T_NIGHT, T_NIGHT + 0.6)))
    if T_BUT + 0.4 < t < T_OK3:
        p = ((t - T_BUT) * 0.7) % 1
        x0 = cx + 6 * U; y0 = top + 1.2 * U + 40 * p
        d.ellipse([x0 - 12, y0 - 12, x0 + 12, y0 + 14], fill=(120, 182, 238))
        d.polygon([(x0 - 11, y0 - 4), (x0 + 11, y0 - 4), (x0, y0 - 30)], fill=(120, 182, 238))
    if T_TEN <= t < T_OK3:                                  # the ten minutes, on the clock
        put(img, glyph("+10 min", 54, (255, 214, 140), kind="m"), 1290, 440, back_out(seg(t, T_TEN, T_TEN + 0.25)), 1 - seg(t, T_OK3 - 0.3, T_OK3))
    if T_OK3 <= t < T_OK3 + 1.2:                            # sigh puff
        p = seg(t, T_OK3, T_OK3 + 1.2)
        d.ellipse([cx + 5.5 * U + 60 * p, top + 2 * U - 50 * p, cx + 5.5 * U + 60 * p + 50 + 40 * p, top + 2 * U - 50 * p + 40 + 30 * p],
                  fill=mix((230, 232, 240), WALL, p))

    # blanket — rises when Clawd tucks you in
    btop = lerp(965, 875, ease_io(seg(t, T_NIGHT - 0.2, T_NIGHT + 1.0)))
    blanket(d, btop, t)
    for side in (-1, 1):                                    # Clawd's hands holding the blanket edge
        if t > T_NIGHT:
            hx = cx + side * 5.2 * U; d.rectangle([hx - U * 0.6, btop - U * 0.5, hx + U * 0.6, btop + U * 0.4], fill=OR)

    # subtitles (only the parts we are sure of)
    sub = None
    if 0.15 <= t < 2.4: sub = "好，好。"
    elif T_OK3 <= t < T_REAL: sub = "好，晚安。"
    elif T_REAL <= t < T_OFF + 0.8: sub = "真的。"
    if sub:
        put(img, glyph(sub, 56, (250, 246, 238), stroke=4, strokec=(30, 30, 40), kind="r"), 960, 1035, 1, 0.95)

    # lights out
    arr = np.asarray(img).astype(np.float32)
    dark = seg(t, T_OFF, T_OFF + 0.08)
    if dark > 0:
        arr = arr * (1 - 0.72 * dark)
        arr[:, :, 2] *= 1 + 0.25 * dark
    z = 1 + 0.12 * ease_io(seg(t, T_NIGHT - 0.4, END))
    img = Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")
    if z > 1.001:
        fx, fy = 960, min(620, H - H / (2 * z))
        img = img.transform((W, H), Image.AFFINE, (1 / z, 0, fx - W / (2 * z), 0, 1 / z, fy - H / (2 * z)), Image.BICUBIC)
    d = ImageDraw.Draw(img)
    if t > T_OFF + 0.4:                                     # zZ and a whispered good night
        for k in range(3):
            p = ((t - T_OFF - 0.4) * 0.45 + k / 3) % 1
            put(img, glyph("z", int(36 + 30 * p), (200, 206, 240), kind="s"), 1120 + 80 * p, 520 - 140 * p, 1, (1 - p) * 0.9)
        put(img, glyph("晚安～", 64, (220, 224, 250), kind="r"), 960, 1000, 1, ease_out(seg(t, T_OFF + 0.6, T_OFF + 1.3)) * 0.9)
    arr = np.asarray(img).astype(np.float32) * K.VIG + K.GRAIN[fi % 4] * 0.8
    if t < 0.5: arr *= t / 0.5
    if t > END - 1.0: arr *= clamp((END - t) / 0.9)
    return Image.fromarray(np.clip(arr, 0, 255).astype(np.uint8), "RGB")

# ------------------------------------------------------------------ audio: the voice + a soft music box + small foley
def build_audio():
    n = int(END * SR); buf = np.zeros(n)
    v = VOICE_PCM[:n]; buf[:len(v)] += v * 1.0
    def tt(dur): return np.arange(int(dur * SR)) / SR
    def bell(f, dur=1.4, r=0.5):
        x = tt(dur); s = np.sin(2 * np.pi * f * x) + 0.3 * np.sin(4 * np.pi * f * x) + 0.1 * np.sin(6.02 * np.pi * f * x)
        e = np.minimum(1, x / 0.004) * np.exp(-x / r); return s * e
    def add(sig, t0, g):
        i = int(t0 * SR); j = min(n, i + len(sig))
        if j > i: buf[i:j] += sig[: j - i] * g
    melody = [(0.3, 784), (0.9, 659), (1.5, 587), (2.1, 659), (2.9, 523), (3.7, 587), (4.5, 659), (5.3, 523),
              (6.3, 440), (7.1, 494), (8.1, 523), (9.1, 659), (10.1, 587), (11.1, 523), (12.0, 392)]
    for t0, f in melody: add(bell(f * 2, 1.6, 0.55), t0, 0.022)
    for t0, f in [(0.3, 262), (3.7, 220), (6.3, 175), (9.1, 196), (12.0, 131)]: add(bell(f, 3.0, 1.0), t0, 0.03)
    rng = np.random.default_rng(3)                        # blanket rustle + lamp click
    ns = np.convolve(rng.standard_normal(int(0.9 * SR)), np.ones(40) / 40, mode="same")
    add(ns / np.abs(ns).max() * np.sin(np.linspace(0, np.pi, len(ns))) ** 2, T_NIGHT - 0.1, 0.05)
    ck = rng.standard_normal(int(0.02 * SR)) * np.exp(-np.arange(int(0.02 * SR)) / (0.003 * SR))
    add(ck, T_OFF, 0.25); add(ck * 0.6, T_OFF + 0.035, 0.25)
    fade = int(1.0 * SR); buf[-fade:] *= np.linspace(1, 0, fade)
    peak = np.abs(buf).max(); buf = buf / peak * 0.9 if peak > 0.9 else buf
    return (buf * 32767).astype(np.int16)

def frame_bytes(fi): return render_frame(fi).tobytes()

if __name__ == "__main__":
    if sys.argv[2] == "preview":
        out, times = sys.argv[3], [float(x) for x in sys.argv[4:]]
        th = [render_frame(int(x * FPS)).resize((480, 270)) for x in times]
        cols = min(4, len(th)); rows = (len(th) + cols - 1) // cols
        sheet = Image.new("RGB", (480 * cols, 270 * rows))
        for k, im in enumerate(th): sheet.paste(im, ((k % cols) * 480, (k // cols) * 270))
        sheet.save(out); sys.exit()
    OUT = sys.argv[2]; wav_path = os.path.splitext(OUT)[0] + "_mix.wav"
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR); w.writeframes(build_audio().tobytes())
    n = int(END * FPS)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav_path, "-c:v", "libx264", "-preset", "medium", "-b:v", "9M",
                           "-maxrate", "12M", "-bufsize", "18M", "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k",
                           "-shortest", "-movflags", "+faststart", OUT], stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for b in pool.imap(frame_bytes, range(n), chunksize=6): ff.stdin.write(b)
    ff.stdin.close(); ff.wait(); os.remove(wav_path); print("wrote", OUT)
