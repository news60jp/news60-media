"""台本JSONから60秒ニュース動画(縦1080x1920)を作る。
使い方: python3 make_video.py script.json out.mp4
script.json の形:
{
  "title": "米中間選挙",            # 画面上の短いタイトル
  "category": "海外・政治",
  "date": "2026.11.3",             # 冒頭チップ(任意)
  "sources": "AP通信、NPR、NHK",
  "min_seconds": 61,               # TikTok収益化のため61秒以上に伸ばす
  "scenes": [
    {"heading": "何が起きた?",      # 画面の見出し
     "points": ["民主党が上下両院を制す", "共和党から7議席"],   # 画面のチップ(最大3)
     "number": {"value": "7議席", "label": "上院で移動"},         # 任意: 大きな数字
     "lines": [                                                  # ナレーション(字幕は{}で強調)
        {"cap": "アメリカの{中間選挙}で\n大きな結果が出ました", "say": "アメリカの中間選挙で、大きな結果が出ました。"}
     ]}
  ]
}
"""
import os, re, sys, json, subprocess, wave
import numpy as np
from PIL import Image, ImageDraw, ImageFont, ImageFilter, ImageEnhance
from images import fetch as fetch_image

W, H, FPS, SR = 1080, 1920, 30, 48000
VOICE, RATE = "ja-JP-NanamiNeural", "+22%"
FD = "/usr/share/fonts/opentype/noto/"
def F(w, s): return ImageFont.truetype(FD + f"NotoSansCJK-{w}.ttc", s, index=0)
INK, MUTED = (240, 243, 252), (150, 160, 195)
RED, BLUE, GOLD = (226, 72, 72), (64, 128, 236), (255, 206, 72)
THEMES = {  # 背景(上,下), カード色, 強調色
  "navy":   ((12, 18, 40), (22, 32, 72), (30, 42, 86), (255, 206, 72)),
  "wine":   ((44, 10, 24), (92, 22, 46), (110, 36, 62), (255, 196, 120)),
  "forest": ((8, 32, 28), (16, 64, 52), (24, 84, 70), (170, 240, 120)),
  "slate":  ((22, 22, 26), (46, 46, 54), (62, 62, 74), (255, 120, 80)),
  "ocean":  ((6, 30, 48), (10, 64, 96), (16, 84, 120), (120, 230, 255)),
  "plum":   ((30, 12, 44), (60, 24, 92), (78, 34, 116), (255, 170, 230)),
  "sand":   ((48, 36, 14), (92, 70, 28), (112, 86, 40), (255, 230, 120)),
}
CAT_THEME = {"海外": "navy", "政治": "navy", "国内": "wine", "社会": "wine", "経済": "forest", "科学": "ocean",
             "テクノロジー": "ocean", "災害": "slate", "事件": "slate", "スポーツ": "plum", "文化": "sand", "エンタメ": "sand"}
BG1, BG2, CARD, GOLD = THEMES["navy"][:4]
GAP, TAIL = 0.18, 0.45

def tts(text, path):
    env = dict(os.environ, SSL_CERT_FILE="/root/.ccr/ca-bundle.crt")
    for _ in range(3):
        subprocess.run(["edge-tts", "--proxy", os.environ.get("HTTPS_PROXY", ""), "--voice", VOICE, f"--rate={RATE}",
                        "--text", text, "--write-media", path], env=env, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if os.path.exists(path) and os.path.getsize(path) > 1000: break
    w = path[:-4] + ".wav"
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", path, "-ar", str(SR), "-ac", "1", w], check=True)
    with wave.open(w) as f:
        a = np.frombuffer(f.readframes(f.getnframes()), dtype=np.int16).astype(np.float32)
    nz = np.where(np.abs(a) > 300)[0]
    return a[max(0, nz[0] - 480): nz[-1] + 2400]

def ease(x): x = max(0, min(1, x)); return 1 - (1 - x) ** 3
def ramp(t, a, d=0.45): return ease((t - a) / d)
def lerp(a, b, k): return tuple(int(a[i] + (b[i] - a[i]) * k) for i in range(3))

_bgcache = {}
def photo_bg(path, theme):
    im = Image.open(path).convert("RGB")
    k = max(W / im.width, H / im.height); im = im.resize((int(im.width * k) + 1, int(im.height * k) + 1), Image.LANCZOS)
    im = im.crop(((im.width - W) // 2, (im.height - H) // 2, (im.width - W) // 2 + W, (im.height - H) // 2 + H))
    im = ImageEnhance.Brightness(im).enhance(0.42); im = ImageEnhance.Color(im).enhance(0.8)
    b1 = THEMES[theme][0]; tint = Image.new("RGB", (W, H), b1); im = Image.blend(im, tint, 0.25)
    # 文字が乗る帯(上部と字幕部)を少し暗く
    ov = Image.new("L", (W, H), 0); dd = ImageDraw.Draw(ov)
    dd.rectangle([0, 0, W, 1000], fill=90); dd.rectangle([0, 1150, W, 1500], fill=120)
    ov = ov.filter(ImageFilter.GaussianBlur(80)); im = Image.composite(Image.new("RGB", (W, H), (0, 0, 0)), im, ov.point(lambda v: int(v * 0.9)))
    return im

def make_bg(theme, seed, photo=None):
    key = (theme, seed, photo)
    if key in _bgcache: return _bgcache[key]
    if photo:
        try:
            im = photo_bg(photo, theme); _bgcache[key] = im; return im
        except Exception: pass
    b1, b2, card, acc = THEMES[theme]
    g = np.linspace(0, 1, H)[:, None, None]
    im = Image.fromarray((np.array(b1) * (1 - g) + np.array(b2) * g).repeat(W, axis=1).astype(np.uint8))
    d = ImageDraw.Draw(im, "RGBA"); rng = np.random.default_rng(seed)
    for _ in range(3):  # 大きな薄い円で画面ごとに表情を変える
        r = int(rng.integers(260, 520)); x = int(rng.integers(-100, W + 100)); y = int(rng.integers(-100, H + 100))
        d.ellipse([x - r, y - r, x + r, y + r], fill=acc + (14,))
    for i in range(0, H, 96): d.line([(0, i), (W, i)], fill=(255, 255, 255, 6))
    _bgcache[key] = im; return im
F_TOP, F_CAP, F_H, F_M, F_S, F_XS, F_NUM = F("Bold", 38), F("Black", 66), F("Black", 84), F("Bold", 54), F("Medium", 40), F("Medium", 32), F("Black", 220)

def text_c(d, xy, s, font, fill, anchor="mm"):
    d.text(xy, s, font=font, fill=fill, anchor=anchor)

def wrap(d, s, font, maxw):
    out, cur = [], ""
    for ch in s:
        if d.textlength(cur + ch, font=font) > maxw and cur: out.append(cur); cur = ch
        else: cur += ch
    if cur: out.append(cur)
    return out

def rich_lines(d, cx, cy, cap, font, lh, alpha):
    lines = cap.split("\n"); y0 = cy - (len(lines) - 1) * lh / 2
    for j, ln in enumerate(lines):
        segs = [(p[1:-1], GOLD) if p.startswith("{") else (p, INK) for p in re.split(r"(\{[^}]*\})", ln) if p]
        x = cx - sum(d.textlength(s, font=font) for s, _ in segs) / 2
        for s, c in segs:
            d.text((x, y0 + j * lh), s, font=font, fill=lerp(BG1, c, alpha), anchor="lm", stroke_width=6, stroke_fill=(8, 10, 24))
            x += d.textlength(s, font=font)

def chip(d, box, label, col, font=F_M, txt=INK):
    d.rounded_rectangle(box, radius=26, fill=col); text_c(d, ((box[0] + box[2]) / 2, (box[1] + box[3]) / 2 - 4), label, font, txt)

def draw_outro(d, t):
    k = ramp(t, 0); y = 520
    text_c(d, (W/2, y - 160), "役に立ったら", F_M, lerp(BG1, MUTED, k))
    # フォローボタン
    kb = ramp(t, 0.3)
    d.rounded_rectangle([W/2 - 300, y, W/2 + 300, y + 150], radius=40, fill=lerp(BG1, RED, kb))
    text_c(d, (W/2 + 20, y + 72), "フォロー", F("Black", 72), lerp(BG1, INK, kb))
    text_c(d, (W/2 - 200, y + 72), "+", F("Black", 90), lerp(BG1, INK, kb))
    # いいね(ハート)
    kh = ramp(t, 0.8); hy = y + 330; r = 70 + 10 * (1 if int(t * 2) % 2 == 0 else 0)
    c = lerp(BG1, (255, 90, 120), kh)
    d.ellipse([W/2 - r - 40, hy - r, W/2 - 40 + r, hy + r], fill=c); d.ellipse([W/2 + 40 - r, hy - r, W/2 + 40 + r, hy + r], fill=c)
    d.polygon([(W/2 - r - 40 + 10, hy + r * 0.45), (W/2 + r + 40 - 10, hy + r * 0.45), (W/2, hy + r * 1.9)], fill=c)
    text_c(d, (W/2, hy + 260), "いいね", F("Black", 72), lerp(BG1, INK, kh))
    kc = ramp(t, 1.6)
    text_c(d, (W/2, hy + 380), "明日も1分でニュースをお届け", F_S, lerp(BG1, GOLD, kc))

def draw_scene(d, sc, t, first, title, date):
    if sc.get("outro"): return draw_outro(d, t)
    k = ramp(t, 0)
    if first:
        if date: chip(d, (W/2 - 230, 210, W/2 + 230, 300), date, lerp(BG1, RED, k), F_M)
        text_c(d, (W/2, 420), title, F("Black", 110 if len(title) <= 6 else 84), lerp(BG1, INK, k))
        y = 560
    else:
        y = 300
    for ln in wrap(d, sc["heading"], F_H, 900)[:2]:
        text_c(d, (W/2, y), ln, F_H, lerp(BG1, INK, k)); y += 100
    y += 20
    num = sc.get("number")
    if num:
        kn = ramp(t, 0.5, 1.0)
        text_c(d, (W/2, y + 120), num["value"], F_NUM if len(num["value"]) <= 4 else F("Black", 150), lerp(BG1, GOLD, kn))
        text_c(d, (W/2, y + 290), num.get("label", ""), F_S, lerp(BG1, MUTED, kn)); y += 380
    for i, p in enumerate(sc.get("points", [])[:3]):
        kp = ramp(t, 0.4 + i * 0.35)
        if kp <= 0: continue
        lines = wrap(d, p, F_M, 820)[:2]; hgt = 60 + 64 * len(lines)
        d.rounded_rectangle([90, y + (1 - kp) * 30, W - 90, y + hgt + (1 - kp) * 30], radius=28, fill=lerp(BG1, CARD, kp))
        for j, ln in enumerate(lines):
            text_c(d, (W/2, y + 30 + 32 + j * 64 + (1 - kp) * 30), ln, F_M, lerp(BG1, INK, kp))
        y += hgt + 24

OUTRO = {"heading": "", "outro": True, "lines": [
    {"cap": "{フォロー}と{いいね}で\n応援お願いします", "say": "この動画が役に立ったら、フォローといいねで応援お願いします。明日も1分でニュースをお届けします。"}]}

def build(script, out):
    global RATE
    if not any(sc.get("outro") for sc in script["scenes"]): script["scenes"].append(dict(OUTRO))
    minsec = script.get("min_seconds", 61)
    for attempt in range(3):
        total = _build(script, out, os.path.join(os.path.dirname(os.path.abspath(out)), "_work"))
        if total >= minsec or attempt == 2: return total
        # 足りない分だけ読み上げを遅くして、無音ではなく声で埋める
        cur = int(RATE.replace("%", "").replace("+", "")); need = minsec / total
        RATE = f"+{max(0, int((100 + cur) / need) - 100)}%"
        import shutil; shutil.rmtree(os.path.join(os.path.dirname(os.path.abspath(out)), "_work"), ignore_errors=True)

def _build(script, out, tmp):
    os.makedirs(tmp, exist_ok=True)
    scenes, timeline, clips, t = [], [], [], 0.35
    for si, sc in enumerate(script["scenes"]):
        st = t
        for li, ln in enumerate(sc["lines"]):
            a = tts(ln["say"], os.path.join(tmp, f"s{si}_{li}.mp3")); clips.append(a)
            d = len(a) / SR; timeline.append((si, t, t + d, ln["cap"])); t += d + GAP
        t += TAIL - GAP; scenes.append([si, st, t])
    scenes[-1][2] = t = t + 0.3  # 声が終わったらすぐ終了
    for s in scenes: s[1] = round(s[1] * FPS) / FPS; s[2] = round(s[2] * FPS) / FPS
    scenes[0][1] = 0.0; TOTAL = scenes[-1][2]
    # ストーリーズ予告版用: つかみ(シーン1)が終わる秒数を書き出す
    json.dump({"hook_end": round(scenes[0][2], 2), "total": round(TOTAL, 2)},
              open(os.path.splitext(out)[0] + ".timing.json", "w"))
    # 音声ミックス
    n = int(TOTAL * SR) + SR; voice = np.zeros(n, dtype=np.float32)
    for (si, st, en, _), a in zip(timeline, clips): k = int(st * SR); voice[k:k + len(a)] += a
    tt = np.arange(n) / SR; bed = np.zeros(n, dtype=np.float32)
    for f0 in (110, 164.8, 220, 277.2): bed += np.sin(2 * np.pi * f0 * tt) * (0.5 + 0.5 * np.sin(2 * np.pi * 0.07 * tt + f0))
    bed *= 260
    for s in scenes[1:]:
        k = int(s[1] * SR); L = int(0.45 * SR)
        if k + L < n: bed[k:k + L] += np.convolve(np.random.default_rng(k).normal(0, 1, L), np.ones(30) / 30, "same") * np.sin(np.linspace(0, np.pi, L)) ** 2 * 2600
    fade = np.ones(n); fl = SR; fade[-fl:] = np.linspace(1, 0, fl); fade[:fl] = np.linspace(0, 1, fl)
    mix = voice + bed * fade; mix = np.clip(mix / max(1, np.abs(mix).max()) * 30000, -32767, 32767).astype(np.int16)
    with wave.open(os.path.join(tmp, "mix.wav"), "wb") as f:
        f.setnchannels(1); f.setsampwidth(2); f.setframerate(SR); f.writeframes(mix.tobytes())
    # 映像
    title, date, cat = script["title"], script.get("date", ""), script.get("category", "ニュース")
    base = script.get("theme") or next((v for k, v in CAT_THEME.items() if k in cat), "navy")
    order = [base] + [k for k in THEMES if k != base]
    files = []
    for si, st, en in scenes:
        sc = script["scenes"][si]; nfr = int(round((en - st) * FPS)); out_s = os.path.join(tmp, f"scene{si}.mp4")
        theme = sc.get("theme") or order[si % len(order)]
        global BG1, BG2, CARD, GOLD
        BG1, BG2, CARD, GOLD = THEMES[theme]
        photo, credit = (None, None)
        qs = sc.get("image_query") or []
        for q in ([qs] if isinstance(qs, str) else qs):
            photo, credit = fetch_image(q)
            if photo: break
        bg = make_bg(theme, si, photo)
        p = subprocess.Popen(["ffmpeg", "-y", "-v", "error", "-f", "rawvideo", "-pix_fmt", "rgb24", "-s", f"{W}x{H}", "-r", str(FPS), "-i", "-",
                              "-c:v", "libx264", "-preset", "veryfast", "-crf", "20", "-pix_fmt", "yuv420p", out_s + ".tmp.mp4"], stdin=subprocess.PIPE)
        for i in range(nfr):
            T = st + i / FPS; im = bg.copy(); d = ImageDraw.Draw(im)
            d.rounded_rectangle([40, 80, 330, 150], radius=18, fill=GOLD); text_c(d, (185, 113), "60秒ニュース", F_TOP, BG1)
            text_c(d, (W - 50, 115), cat, F_TOP, MUTED, anchor="rm")
            draw_scene(d, sc, T - st, si == 0, title, date)
            if si == len(scenes) - 1 and T > timeline[-1][2] + 0.3:
                ko = ramp(T, timeline[-1][2] + 0.3)
                text_c(d, (W/2, 1560), "出典: " + script.get("sources", ""), F_XS, lerp(BG1, MUTED, ko))
                text_c(d, (W/2, 1610), "フォローして次もチェック", F_S, lerp(BG1, GOLD, ko))
            cur = [c for c in timeline if c[1] - 0.05 <= T < c[2] + GAP]
            if cur:
                c = cur[-1]; a = ramp(T, c[1] - 0.05, 0.18); nl = c[3].count("\n") + 1
                cy0 = 1190
                d.rounded_rectangle([50, cy0, W - 50, cy0 + 60 + nl * 92], radius=30, fill=lerp(BG1, (6, 9, 22), a))
                rich_lines(d, W/2, cy0 + 30 + nl * 46, c[3], F_CAP, 92, a)
            z = 1.0 + 0.04 * ((T - st) / max(1, en - st))
            if z > 1.001:
                cw, ch = int(W / z), int(H / z); im = im.crop(((W - cw) // 2, (H - ch) // 2, (W - cw) // 2 + cw, (H - ch) // 2 + ch)).resize((W, H), Image.BILINEAR)
                d = ImageDraw.Draw(im)
            if credit: text_c(d, (W - 40, H - 40), credit, F("Medium", 24), (200, 205, 225), anchor="rm")
            d.rectangle([0, H - 14, W * T / TOTAL, H], fill=GOLD)
            p.stdin.write(im.tobytes())
        p.stdin.close()
        if p.wait() != 0: raise SystemExit("render failed")
        os.replace(out_s + ".tmp.mp4", out_s); files.append(out_s)
    with open(os.path.join(tmp, "list.txt"), "w") as f:
        for x in files: f.write(f"file '{x}'\n")
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-f", "concat", "-safe", "0", "-i", os.path.join(tmp, "list.txt"), "-c", "copy", os.path.join(tmp, "v.mp4")], check=True)
    subprocess.run(["ffmpeg", "-y", "-v", "error", "-i", os.path.join(tmp, "v.mp4"), "-i", os.path.join(tmp, "mix.wav"), "-map", "0:v", "-map", "1:a",
                    "-c:v", "copy", "-c:a", "aac", "-b:a", "192k", "-shortest", out], check=True)
    return TOTAL

if __name__ == "__main__":
    s = json.load(open(sys.argv[1], encoding="utf-8"))
    print("length", round(build(s, sys.argv[2]), 1), "sec")
