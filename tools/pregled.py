#!/usr/bin/env python3
"""Видео преглед на „Моя анимация“ без рестартиране: прави темата в /tmp и я рисува кадър по кадър
със същата математика като скрипта на Plymouth (50 опреснявания в секунда).
usage: python3 tools/pregled.py АНИМАЦИЯ.gif изход.mp4 [indicator] [#RRGGBB] [секунди]"""
import glob
import math
import os
import random
import subprocess
import sys
import tempfile

sys.path.insert(0, os.path.join(os.path.dirname(os.path.realpath(__file__)), ".."))
import jezgro as J
from PIL import Image, ImageDraw

src, out = sys.argv[1], sys.argv[2]
ind = sys.argv[3] if len(sys.argv) > 3 else "trikolor"
bg = tuple(int(sys.argv[4].lstrip("#")[i:i + 2], 16) for i in (0, 2, 4)) if len(sys.argv) > 4 else None
sec = float(sys.argv[5]) if len(sys.argv) > 5 else 6
if bg is None:
    bg = Image.open(src).convert("RGB").getpixel((2, 2))
W, H, FPS = 1280, 720, 50
D = tempfile.mkdtemp(prefix="bm-pregled-")
J.make_custom(J.Custom(title="Преглед", src=src, bg=bg, scale=0.4, fps=20, indicator=ind), workdir=D, log=lambda x: None)
frames = [Image.open(f).convert("RGBA") for f in sorted(glob.glob(D + "/frame-*.png"), key=J._num)]
k = min(W, H) * 0.4 / frames[0].height
frames = [f.resize((int(f.width * k), int(f.height * k)), Image.LANCZOS) for f in frames]
fw0, fh0 = frames[0].size
bottom = H * 0.45 + fh0 / 2
md = min(W, H)
cols = [(255, 255, 255), (0, 150, 110), (214, 38, 18)]
isk0 = Image.open(D + "/iskra.png") if os.path.exists(D + "/iskra.png") else None


def put(im, img, x, y, op):
    if op <= 0.01:
        return
    i2 = img.copy()
    i2.putalpha(i2.getchannel("A").point(lambda v: int(v * min(1, op))))
    im.paste(i2, (int(x), int(y)), i2)


enc = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                        "-c:v", "libx264", "-pix_fmt", "yuv420p", "-crf", "18", out], stdin=subprocess.PIPE)
for tick in range(1, int(FPS * sec)):
    im = Image.new("RGB", (W, H), bg)
    fr = frames[(tick // 2) % len(frames)]
    im.paste(fr, (int(W / 2 - fw0 / 2), int(H * 0.45 - fh0 / 2)), fr)
    d = ImageDraw.Draw(im, "RGBA")
    if ind == "trikolor":
        barw, bh, NC = md * 0.30, max(4, md * 0.008), 24
        cw, barx, bary, iks = barw / NC, W / 2 - barw / 2, bottom + H * 0.05, md * 0.05
        isk = isk0.resize((int(iks), int(iks)), Image.LANCZOS)
        t = (tick / 100) % 1
        wave = t * 1.4 - 0.2
        for c in range(NC):
            col = cols[0] if c < NC / 3 else cols[1] if c < NC * 2 / 3 else cols[2]
            g = max(0, 1 - abs((c + 0.5) / NC - wave) / 0.22) ** 2
            op = min(1, 0.32 + 0.12 * (0.5 + 0.5 * math.sin(tick * 0.37 + c * 1.7)) + 0.68 * g)
            d.rectangle((barx + c * cw + 1, bary, barx + c * cw + cw - 1, bary + bh), fill=(*col, int(255 * op)))
        if 0 < wave < 1:
            put(im, isk, barx + wave * barw - iks / 2, bary + bh / 2 - iks / 2, 0.55 + 0.45 * (0.5 + 0.5 * math.sin(tick * 1.1)))
    elif ind == "zname":
        barw, bh = md * 0.26, max(3, md * 0.006)
        gap, barx, bary, iks = bh * 0.7, W / 2 - barw / 2, bottom + H * 0.05, md * 0.03
        isk, big = isk0.resize((int(iks), int(iks)), Image.LANCZOS), isk0.resize((int(iks * 2.2), int(iks * 2.2)), Image.LANCZOS)
        t = (tick / 150) % 1
        fade = 1 - (t - 0.8) / 0.2 if t > 0.8 else 1
        for j in range(3):
            y = bary + j * (bh + gap)
            d.rectangle((barx, y, barx + barw, y + bh), fill=(*cols[j], 36))
            f = min(1, max(0, (t - j * 0.1) / 0.45))
            f = f * f * (3 - 2 * f)
            if f * barw >= 2:
                d.rectangle((barx, y, barx + f * barw, y + bh), fill=(*cols[j], int(242 * fade)))
                if f < 1:
                    put(im, isk, barx + f * barw - iks / 2, y + bh / 2 - iks / 2, 0.5 + 0.5 * (0.5 + 0.5 * math.sin(tick * 0.9 + j * 2)))
        if 0.62 < t < 0.8:
            put(im, big, barx + barw - iks * 1.1, bary + bh + gap + bh / 2 - iks * 1.1, math.sin((t - 0.62) / 0.18 * math.pi))
    elif ind == "begashta":
        barw, bary = md * 0.28, bottom + H * 0.05
        barx = W / 2 - barw / 2
        d.rectangle((barx, bary + 1, barx + barw, bary + 3), fill=(255, 255, 255, 56))
        p = (tick / 90) % 1
        a, b = max(0, p * 1.4 - 0.4), min(1, p * 1.4)
        if (b - a) * barw >= 2:
            d.rectangle((barx + a * barw, bary, barx + b * barw, bary + 4), fill=(255, 255, 255, 230))
    enc.stdin.write(im.tobytes())
enc.stdin.close()
enc.wait()
print(out)
