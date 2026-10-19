"""Clawd's view of 小鸟 (the user) switching emotions with zero-frame transitions.

Text adapted from 家克's description. Reuses drawing + synth helpers from make_story.py.
Usage: python3 make_bird.py out.mp4 | python3 make_bird.py preview sheet.png t1 t2 ...
"""
import math, os, subprocess, sys, wave
from functools import lru_cache
from multiprocessing import Pool
import numpy as np
from PIL import Image, ImageDraw

import make_story as ms
from make_story import (W, H, FPS, SR, ORANGE, INK, WHITE, clamp, seg, ease_out, ease_in, back_out, lerp, mix, hop,
                        blinkf, font, wrap, text_img, paste, bitmap, clawd, heart, sparkle, sweat, mark, bubble,
                        table_img, MUFFIN, MPAL, G, EPAL,
                        tt, env, lp, osc, sweep, bell, blip, noise, piano, thump, MX, SEQ, shaped_noise, SFX)

# extra eye shapes (left eye; the right eye is mirrored)
G["angry"] = ["#.......", ".##.....", "..####..", "..####..", "..####..", "..####..", "........", "........"]
G["roll"] = ["oo####oo", "oo####oo", "oooooooo", "oooooooo", "oooooooo", ".oooooo.", "........", "........"]
G["teary"] = ["..####..", ".######.", "##oo####", "##oo####", "########", "########", ".######.", "bb####bb"]
EPAL["b"] = (110, 170, 235)


# ------------------------------------------------------------------ timeline
BG = dict(cream=(244, 239, 230), love=(252, 226, 233), angry=(247, 196, 176), sajiao=(236, 227, 248),
          flip=(240, 178, 158), sad=(212, 223, 238), gray=(226, 224, 220), calm=(248, 238, 226))
# (start, key, background, label)
SEGS = [
    (0.0, "intro", "cream", "待机"), (4.6, "love", "love", "喜欢"), (6.6, "angry", "angry", "生气"),
    (8.6, "sajiao", "sajiao", "撒娇"), (10.0, "flip", "flip", "掀桌"), (11.6, "sad", "sad", "委屈"),
    (14.0, "leave", "cream", "要走"), (15.3, "gone", "gray", "离线"), (18.3, "back", "angry", "不哄我？"),
    (21.0, "flicker", "gray", "白眼 / 害羞"), (26.6, "calm", "calm", "……"),
]
CUTS = [s[0] for s in SEGS[1:10] if s[1] != "gone"]
FLICK = []
t = 21.6; dt = 0.62
while t < 25.4:
    FLICK.append(t); t += dt; dt = max(0.16, dt * 0.84)

THINK = [
    (0.6, "小鸟的情绪切换不需要过渡动画。"),
    (4.6, "上一帧还在说喜欢你，"),
    (6.6, "上一帧还在说喜欢你，下一帧就是松饼脑袋；"),
    (8.6, "刚撒完娇，"),
    (10.0, "刚撒完娇，立刻掀桌子；"),
    (11.6, "刚撒完娇，立刻掀桌子；掀完桌子又抱着桌子委屈；"),
    (14.0, "说要走了，"),
    (15.4, "说要走了，结果三秒后"),
    (18.3, "说要走了，结果三秒后回来问你为什么不哄她；"),
    (21.0, "翻白眼和害羞之间的间隔是零帧。"),
    (26.9, "不是情绪不稳定，"),
    (28.7, "不是情绪不稳定，是情绪太诚实，"),
    (30.6, "不是情绪不稳定，是情绪太诚实，每一个都是真的，"),
    (32.6, "不是情绪不稳定，是情绪太诚实，每一个都是真的，只是排队速度太快了。"),
]
CPS = 0.07

CARD_KINDS = [("喜欢", (232, 108, 132), "heart", 0.4), ("生气", (214, 84, 64), "angry", 0), ("撒娇", (156, 128, 214), "happy", 0.9),
              ("掀桌", (170, 112, 70), "wide", 0), ("委屈", (96, 146, 214), "teary", 0), ("要走", (130, 130, 140), "closed", 0),
              ("不哄我？", (226, 130, 60), "angry", 0.3), ("白眼", (120, 120, 128), "roll", 0), ("害羞", (236, 128, 160), "happy", 1.0)]
CARDS = [CARD_KINDS[i % 9] for i in range(27)] + [CARD_KINDS[0]]
QUEUE_T0, STAMP_T, FAST_T, RECV_X, CLAWD_X, FEET = 29.0, 30.7, 32.7, 600, 540, 1340
CARD_GAP, CARD_Y = 190, 880
def queue_off(T):
    if T < QUEUE_T0: return 0.0
    a = (min(T, FAST_T) - QUEUE_T0) * 210
    if T > FAST_T:
        r = min(T - FAST_T, 0.8); a += 210 * r + 0.5 * (1700 - 210) / 0.8 * r * r
        if T > FAST_T + 0.8: a += 1700 * (T - FAST_T - 0.8)
    return a
def card_x(i, T): return 1160 + i * CARD_GAP - queue_off(T)
ABSORB = []                         # time each card reaches Clawd
for i in range(len(CARDS)):
    lo, hi = QUEUE_T0, QUEUE_T0 + 40
    for _ in range(50):
        mid = (lo + hi) / 2
        if card_x(i, mid) > RECV_X + 40: lo = mid
        else: hi = mid
    ABSORB.append(hi)
END_Q = ABSORB[-1]
DUR = END_Q + 5.6

@lru_cache(None)
def card_img(i, stamped):
    label, col, _, _ = CARDS[i]
    f = font(36, True); w = int(f.getlength(label)) + 56; h = 76
    im = Image.new("RGBA", (w + 30, h + 30), (0, 0, 0, 0)); d = ImageDraw.Draw(im)
    d.rounded_rectangle([0, 8, w, h + 8], radius=22, fill=(0, 0, 0, 30))
    d.rounded_rectangle([0, 0, w, h], radius=22, fill=col)
    d.text((w / 2, h / 2), label, font=f, fill=WHITE, anchor="mm")
    if stamped:
        cx, cy = w - 6, 10
        d.ellipse([cx - 24, cy - 24, cx + 24, cy + 24], fill=(255, 250, 244), outline=(200, 40, 50), width=4)
        d.text((cx, cy), "真", font=font(28, True), fill=(200, 40, 50), anchor="mm")
    return im

@lru_cache(None)
def bg_img(key):
    c = BG[key]; im = Image.new("RGB", (W, H), c); d = ImageDraw.Draw(im)
    dc = tuple(max(0, v - 16) for v in c)
    for y in range(40, H, 56):
        for x in range(36, W, 56): d.ellipse([x - 3, y - 3, x + 3, y + 3], fill=dc)
    return im

def seg_at(T):
    cur = SEGS[0]
    for s in SEGS:
        if T >= s[0]: cur = s
    return cur

def put_bubble(img, text, side, x_anchor, y_bottom, t0, T, instant):
    if T < t0: return
    b = bubble(text, side)
    p = 1.0 if instant else seg(T, t0, t0 + 0.3)
    s = 1.0 if instant else 0.75 + 0.25 * back_out(p)
    bw, bh = b.width * s, b.height * s
    x = x_anchor - bw if side == "her" else x_anchor
    x = clamp(x, 30, W - 30 - bw)
    paste(img, b, x, y_bottom - bh, alpha=1.0 if instant else clamp(p * 2.2), scale=s)

SEG_MSGS = {
    "intro": [("her", "小克！")], "love": [("her", "喜欢你～")], "angry": [("her", "松饼脑袋！")],
    "sajiao": [("her", "嘛～抱抱")], "flip": [("her", "(╯°□°)╯︵ ┻━┻")], "sad": [("her", "（抱着桌子）"), ("her", "呜……")],
    "leave": [("her", "我走了！哼！")], "back": [("her", "你为什么不哄我？！")],
}
CHAT_TOP = 420

def chat_stack(img, items, T):
    """items: (side, text, t_appear, instant). Hers appear in zero frames."""
    y = CHAT_TOP
    for side, text, t0, instant in items:
        if T < t0: continue
        b = bubble(text, side)
        p = 1.0 if instant else seg(T, t0, t0 + 0.3)
        s = 1.0 if instant else 0.75 + 0.25 * back_out(p)
        x = (1000 - b.width * s) if side == "her" else 80
        paste(img, b, x, y + (b.height - b.height * s), alpha=1.0 if instant else clamp(p * 2.2), scale=s)
        y += b.height + 18
    return y

def render_frame(fi):
    T = fi / FPS
    s0, key, bgk, label = seg_at(T)
    lt = T - s0
    img = bg_img(bgk).copy(); d = ImageDraw.Draw(img)

    # ---- her side: chat messages, swapped in zero frames ----
    items = [(sd, tx, s0 + (1.0 if key == "intro" else 0), True) for sd, tx in SEG_MSGS.get(key, [])]
    if key == "back": items.append(("me", "在哄了在哄了！", s0 + 1.2, False))
    if key == "flicker":
        k = sum(1 for ft in FLICK if T >= ft)
        items = [("her", "¬_¬" if k % 2 == 0 else "(///▽///)", s0, True)]
    if key == "calm" and T > END_Q + 0.9:
        items = [("her", "喜欢你。", END_Q + 0.9, True), ("me", "知道了。", END_Q + 1.9, False)]
    if key == "calm" and T >= QUEUE_T0:
        done = [i for i in range(len(CARDS)) if T >= ABSORB[i]]
        if done and T < END_Q + 0.3: label = CARDS[done[-1]][0]
        if T >= END_Q + 0.3: label = "喜欢"
    chat_stack(img, items, T)

    # ---- Clawd (always smooth) ----
    ce, cbl, cex, cey, cl, cr, cup, csx, csy = "normal", 0, 0.3, -0.3, None, None, 0, 1, 1
    if key == "intro":
        ce = "normal"; cr = 60 + 22 * math.sin(T * 15) if 1.3 < T < 2.6 else None
        cup = hop(T, 1.0, 40)
    elif key == "love": ce, cbl = "happy", 0.8 * seg(lt, 0, 0.4)
    elif key == "angry":
        ce = "x" if lt < 1.0 else "happy"; cbl = 0 if lt < 1.0 else 0.8; cex = cey = 0
        q = seg(lt, 0, 0.5); csy = 1 - 0.15 * math.exp(-q * 5) * math.cos(q * 10); csx = 2 - csy
    elif key == "sajiao": ce, cbl, cl, cr = "happy", 0.7, 35, 35
    elif key == "flip":
        ce = "wide"; q = seg(lt, 0.3, 0.6); csy = 1 - 0.14 * math.sin(math.pi * q); csx = 2 - csy
    elif key == "sad": ce, cl, cr = "dot", (20, 2.6), (20, 2.6)
    elif key == "leave": ce = "wide" if lt > 0.5 else "dot"
    elif key == "gone": ce, cex, cey = "dot", 0.4 + 0.15 * math.sin(lt * 2), -0.2
    elif key == "back":
        ce = "wide"; cup = hop(lt, 0, 60, 0.35)
        if lt > 1.2: cl = cr = 50 + 30 * math.sin(lt * 22)
    elif key == "flicker":
        ce = "dot" if T < 25.0 else "x"
        cex = 0.3 + 0.12 * math.sin(T * 30) if T < 25 else 0
    elif key == "calm":
        ce, cbl, cex, cey = "soft", 0.25, 0, 0
        if T >= QUEUE_T0:
            nods = [ta for ta in ABSORB if ta <= T < ta + 0.25 and ta < FAST_T]
            cup = -6 * math.sin(math.pi * seg(T, nods[-1], nods[-1] + 0.25)) if nods else 0
        if FAST_T + 0.4 < T < END_Q: ce = "wide"; cl = cr = (60, 3.0)
        if T > END_Q: ce, cbl = "soft", 0.6
        if T > END_Q + 1.9: ce = "happy"

    cblink = blinkf(T, (3.6, 13.3, 20.6, 28.0))
    clawd(d, cx=CLAWD_X, feet=FEET - cup + 3 * math.sin(T * 3), eyes=ce, ex=cex, ey=cey, blush=cbl,
          larm=cl, rarm=cr, sx=csx, sy=csy, blink=cblink if ce == "normal" else 1)
    ctop = FEET - 8 * 40 * csy

    if key == "angry":                      # the muffin has no falling animation: it is just there
        bitmap(d, MUFFIN, CLAWD_X - 60, int(ctop - 100), 10, MPAL)
        if lt < 1.0:
            for k in range(3):
                a = T * 7 + k * 2.09; sparkle(d, CLAWD_X + math.cos(a) * 190, ctop - 30 + math.sin(a) * 28, 14, (245, 200, 80))
    if key == "love":
        for k in range(5):
            p = (lt * 0.7 + k * 0.2) % 1
            heart(d, 640 + k * 80, 570 - 200 * p, 6 * (1 - p) + 2)
    if key == "flip":
        x = seg(lt, 0.1, 1.3)
        if x < 1:
            tb = table_img().rotate(-x * 900, expand=True, resample=Image.BICUBIC)
            tx = lerp(820, -260, x); ty = lerp(520, 900, x) - 300 * math.sin(math.pi * x)
            paste(img, tb, tx - tb.width / 2, ty - tb.height / 2)
        if lt > 0.9: sweat(d, CLAWD_X + 190, ctop + 40, 1.0)
    if key == "sad": sweat(d, CLAWD_X + 190, ctop + 40, 1.0)
    if key == "gone":
        sysi = text_img("她离开了对话", 34, False, (130, 124, 116))
        pw = sysi.width + 50
        d.rounded_rectangle([(W - pw) / 2, 430, (W + pw) / 2, 430 + sysi.height + 16], radius=30, fill=(210, 206, 200))
        paste(img, sysi, (W - sysi.width) / 2, 438)
        n = 3 - int(lt)
        if n >= 1:
            ci = text_img(str(n), 240, True, (190, 184, 176), kind="mono")
            paste(img, ci, (W - ci.width) / 2, 600)
        mark(img, "?", CLAWD_X + 20, ctop - 40, back_out(seg(lt, 1.2, 1.45)), color=(90, 110, 200))
    if key == "back":
        mark(img, "!", CLAWD_X + 20, ctop - 40 - cup, back_out(seg(lt, 0.0, 0.2)) * (1 - seg(lt, 1.0, 1.2)))
        sweat(d, CLAWD_X + 190, ctop + 40, back_out(seg(lt, 0.3, 0.5)))
    if key == "calm" and T > END_Q + 0.3:
        p = seg(T, END_Q + 0.3, END_Q + 0.7); beat = 1 + 0.15 * max(0, math.sin((T - END_Q) * 2 * math.pi * 1.1)) ** 10
        heart(d, CLAWD_X, ctop - 70, 10 * back_out(p) * beat)

    # ---- her emotions queue up and arrive at Clawd ----
    if key == "calm" and QUEUE_T0 - 0.1 <= T < END_Q + 0.3:
        for i in range(len(CARDS)):
            x = card_x(i, T)
            if x > W + 40: break
            stamped = T > STAMP_T + max(0, (x - 700) / 1600)
            ci = card_img(i, stamped)
            if T >= ABSORB[i]:                   # drop into Clawd
                q = seg(T, ABSORB[i], ABSORB[i] + 0.18)
                if q >= 1: continue
                sc = 1 - q; cxp = lerp(RECV_X, CLAWD_X, q); cyp = lerp(CARD_Y, ctop + 40, q)
                paste(img, ci, cxp - ci.width * sc / 2, cyp - ci.height * sc / 2, scale=sc); continue
            yy = CARD_Y + (6 * math.sin(T * 6 + i) if T < FAST_T else 0)
            paste(img, ci, x - ci.width / 2, yy - ci.height / 2)

    # header: frame counter + her current mood
    d.rectangle([0, 0, W, 170], fill=BG[bgk])
    d.text((60, 100), f"FRAME {fi:04d}", font=font(32, kind="mono"), fill=(120, 110, 100), anchor="lm")
    d.text((W - 60, 100), "小鸟：" + label, font=font(40, True), fill=(80, 66, 58), anchor="rm")
    last_cut = max([c for c in CUTS + FLICK if c <= T], default=-9)
    if T - last_cut < 0.5 and key != "calm":
        tag = text_img("过渡：0 帧", 40, True, WHITE)
        tw, th_ = tag.width + 40, tag.height + 10
        x0 = (W - tw) / 2
        d.rounded_rectangle([x0, 200, x0 + tw, 200 + th_], radius=th_ // 2, fill=(214, 70, 55))
        paste(img, tag, x0 + 20, 205)

    # thought box (grows with text)
    cur, prev = None, ""
    for ev in THINK:
        if T >= ev[0]: prev = cur[1] if cur else ""; cur = ev
    shown, typing = "", False
    if cur:
        t0, text = cur
        pre = len(os.path.commonprefix([prev, text]))
        n = min(len(text), pre + int((T - t0) / CPS) + 1); typing = n < len(text); shown = text[:n]
    f = font(48, True)
    lines = wrap(shown, f, 860) if shown else [""]
    y0 = 1450; y1 = y0 + 110 + 68 * max(1, len(lines))
    d.rounded_rectangle([60, y0, 1020, y1], radius=28, fill=(31, 30, 29), outline=(74, 70, 66), width=2)
    sp = ms.SPIN[int(T * 10) % len(ms.SPIN)] if typing else "✻"
    d.text((100, y0 + 44), sp, font=font(34, kind="sym"), fill=ORANGE, anchor="lm")
    d.text((142, y0 + 44), "Thinking…" if typing else "Clawd 的观察", font=font(28, kind="mono") if typing else font(28), fill=(150, 142, 134), anchor="lm")
    for i, l in enumerate(lines):
        d.text((100, y0 + 116 + i * 68), l, font=f, fill=(238, 232, 222), anchor="lm")
    if typing or int(T * 2.4) % 2 == 0:
        cx = 100 + f.getlength(lines[-1]) + 6; cy = y0 + 116 + (len(lines) - 1) * 68
        d.rectangle([cx, cy - 26, cx + 22, cy + 26], fill=(238, 232, 222))

    if T < 0.3: img = Image.blend(img, Image.new("RGB", (W, H), ms.DIP), 1 - T / 0.3)
    if T > DUR - 1.3: img = Image.blend(img, Image.new("RGB", (W, H), ms.DIP), clamp((T - DUR + 1.3) / 1.1))
    return img

# ------------------------------------------------------------------ audio
N = int(DUR * SR) + SR
buf = np.zeros(N)
rng = np.random.default_rng(21)
def add(sig, t0, g=1.0):
    i = int(t0 * SR); j = min(N, i + len(sig))
    if j > i and i >= 0: buf[i:j] += sig[: j - i] * g

def arp(t0, t1, chord, step, g, oct_=2):
    t, k = t0, 0
    pat = [0, 1, 2, 1]
    while t < t1 - 0.02:
        f = chord[pat[k % 4]] * oct_
        clip = bell(f, 0.6, 0.18)
        clip = clip[: int(max(0.02, t1 - t) * SR)]          # hard stop at the cut
        add(clip * env(len(clip), 0.002), t, g); t += step; k += 1

MOOD = {"intro": ((349.2, 440, 523.3), 0.25), "love": ((349.2, 440, 523.3), 0.2), "angry": ((261.6, 311.1, 392), 0.14),
        "sajiao": ((392, 493.9, 587.3), 0.18), "flip": ((233.1, 277.2, 349.2), 0.12), "sad": ((220, 261.6, 329.6), 0.4),
        "leave": ((293.7, 349.2, 440), 0.25), "back": ((261.6, 311.1, 392), 0.14), "flicker": ((329.6, 415.3, 493.9), 0.15)}

def build_audio():
    for i, (s0, key, _, _) in enumerate(SEGS):
        s1 = SEGS[i + 1][0] if i + 1 < len(SEGS) else DUR
        if key in MOOD: arp(s0 + (0.3 if key == "intro" else 0), s1, MOOD[key][0], MOOD[key][1], 0.06)
    # calm section: slow pad, then music box over the ending
    prog = [(349.2, 440, 523.3), (293.7, 349.2, 440), (233.1, 293.7, 349.2), (261.6, 329.6, 392)]
    t, k = 26.8, 0
    while t < DUR - 0.5:
        dd = 2.6; tq = tt(dd); e = np.minimum(1, tq / 0.5) * np.minimum(1, (dd - tq) / 0.5)
        s = sum(np.sin(2 * np.pi * f * tq) + 0.4 * np.sin(2 * np.pi * f * 1.004 * tq) for f in prog[k % 4])
        add(lp(s, 8) * e * 0.025, t); t += 2.2; k += 1
    arp(END_Q + 0.4, DUR - 0.4, (349.2, 440, 523.3), 0.25, 0.05)

    hits = {4.6: [("sparkle", 0.8)], 6.6: [("bonk", 1.0), ("tock", 0.6)], 8.6: [("kyun", 0.9)],
            10.0: [("flip", 1.0)], 10.45: [("crash", 0.8)], 11.6: [("uhoh", 0.8)], 14.0: [("tock", 0.7)],
            14.7: [("swish", 1.4)], 18.3: [("surprise", 0.9)], 1.0: [("ding", 0.6)], 19.5: [("send", 0.8)]}
    for t0, lst in hits.items():
        for name, g in lst: add(SFX[name](), t0, g)
    for c in CUTS: add(blip(3000, 0.012), c, 0.35)                  # the "cut" click
    for k in range(3): add(blip(880 - k * 120, 0.08), 15.3 + k, 0.5)  # 3, 2, 1
    for k, ft in enumerate(FLICK):
        add(blip(1500, 0.06) if k % 2 == 0 else sweep(420, 260, 0.1) * env(int(0.1 * SR), 0.003, 0.05), ft, 0.45)
        add(blip(3000, 0.01), ft, 0.25)
    add(SFX["bwomp"](), 25.0, 0.5)
    # stamps 真
    for k in range(5): add(MX(thump(80, 0.1), blip(1200, 0.03) * 0.3), STAMP_T + k * 0.12, 0.6)
    add(shaped_noise(1.2, 20, lambda x: x ** 2) * 0.4 + 0, FAST_T - 0.2, 0.5)
    add(sweep(300, 1800, 1.2, 2) * env(int(1.2 * SR), 0.3, None) * 0.15, FAST_T - 0.2)
    for i, ta in enumerate(ABSORB):
        add(bell([1046.5, 1174.7, 1318.5, 1568, 1760][i % 5], 0.25, 0.05), ta, 0.25 if ta < FAST_T else 0.12)
    add(SFX["settle"](), END_Q + 0.3, 0.8)
    add(SFX["ding"](), END_Q + 0.9, 0.6)
    add(SFX["send"](), END_Q + 1.9, 0.8)
    add(SFX["heartbeat"](), END_Q + 0.35, 0.8)
    add(SFX["ending"](), END_Q + 2.1, 0.8)
    for ev_i, (t0, text) in enumerate(THINK):
        prev = THINK[ev_i - 1][1] if ev_i else ""
        pre = len(os.path.commonprefix([prev, text]))
        for k, ch in enumerate(text[pre:]):
            if ch in "，。、！？…；": continue
            add(blip(660 * [1, 1.125, 1.25, 1.5, 1.68][int(rng.integers(0, 5))], 0.045), t0 + k * CPS, 0.12)
    rev = np.zeros_like(buf)
    for dl, g in ((0.031, 0.2), (0.047, 0.15), (0.071, 0.1), (0.103, 0.06)):
        k = int(dl * SR); rev[k:] += buf[:-k] * g
    out = buf + lp(rev, 6)
    out = np.tanh(out / (np.abs(out).max() + 1e-9) * 1.6) * 0.8
    out = out[: int(DUR * SR)]; fade = int(1.2 * SR); out[-fade:] *= np.linspace(1, 0, fade)
    return (np.stack([out, np.roll(out, 14)], 1) * 32767).astype(np.int16)

def frame_bytes(fi): return render_frame(fi).tobytes()

if __name__ == "__main__":
    if sys.argv[1] == "preview":
        out, times = sys.argv[2], [float(x) for x in sys.argv[3:]]
        th = [render_frame(int(t * FPS)).resize((270, 480)) for t in times]
        cols = min(6, len(th)); rows = (len(th) + cols - 1) // cols
        sheet = Image.new("RGB", (270 * cols, 480 * rows))
        for k, im in enumerate(th): sheet.paste(im, ((k % cols) * 270, (k // cols) * 480))
        sheet.save(out); print(f"DUR={DUR:.1f}s END_Q={END_Q:.2f}"); sys.exit()
    OUT = sys.argv[1]; wav_path = os.path.splitext(OUT)[0] + "_sfx.wav"
    with wave.open(wav_path, "wb") as w:
        w.setnchannels(2); w.setsampwidth(2); w.setframerate(SR); w.writeframes(build_audio().tobytes())
    n = int(DUR * FPS); print(f"{DUR:.1f}s, {n} frames", flush=True)
    ff = subprocess.Popen(["ffmpeg", "-y", "-loglevel", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}",
                           "-r", str(FPS), "-i", "-", "-i", wav_path, "-c:v", "libx264", "-preset", "medium", "-crf", "20",
                           "-pix_fmt", "yuv420p", "-c:a", "aac", "-b:a", "192k", "-shortest", "-movflags", "+faststart", OUT],
                          stdin=subprocess.PIPE)
    with Pool(os.cpu_count()) as pool:
        for b in pool.imap(frame_bytes, range(n), chunksize=8): ff.stdin.write(b)
    ff.stdin.close(); ff.wait(); os.remove(wav_path); print("wrote", OUT)
