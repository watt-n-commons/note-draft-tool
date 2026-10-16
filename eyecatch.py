#!/usr/bin/env python3
"""note記事のアイキャッチ（1280x720）を、Canvaを使わずローカルで生成する。

標準レイアウト（2026-09-16確定のCanvaレシピと同じ配置）:
  - 左半分（0〜640）：イラスト
  - 右半分（640〜1280）：ネイビー単色パネル #0b2545 に、小見出し＋タイトル（白・太字・中央揃え）
  - ロゴバッジ：白い角丸カード 180x190（既定は左上）に、ロゴ原本の輪とW＋「Watt & Commons」

イラストの種類（--illustration）:
  sheets   重ね合わせた2枚の地図（等高線）と、チェックマーク（見直し・検証）
  hands    電力網の一点へ、複数の手が伸びる図（--hands で本数。2〜4）
  image    外部のイラスト画像（PNG/JPEG）を左半分いっぱいに敷く（Canvaなどで作った絵を渡す用）

使い方（タイトルは --line を行ごとに指定。空文字 "" は行間のスペース）:
    python3 eyecatch.py out.png --subtitle "コラム" --illustration sheets \\
        --line "公開済みの記事を、" --line "見直してみた" --line "" \\
        --line "数字の読み違いと、" --line "言葉の精度"

    python3 eyecatch.py out.png --subtitle "海外比較×ソブリン性　第1回" --illustration hands --hands 3 \\
        --line "「進んでいる」" --line "「遅れている」" --line "では比べない" --line "" \\
        --line "各国が握ろうと" --line "しているもの"

必要なもの: Pillow（`pip3 install Pillow`）。このツール以外は標準ライブラリのみで動く。
ロゴ原本: 既定は Google Drive の Vault `04_Brand/watt and commons logo`（1280x720のPNG）。
          場所が違う場合は --logo または環境変数 EYECATCH_LOGO で指定する。

注意:
  - タイトル行の先頭・末尾にダッシュ（——）を置かない（行分けで避ける）。
  - 日本語フォントは macOS の Hiragino Sans GB（W6）。他OSでは --font で指定する。
  - 生成物は、必ず目視で確認する（行分け・イラストの重なり・文字の欠け）。
"""
import argparse
import math
import os
import random
import sys

try:
    from PIL import Image, ImageDraw, ImageFilter, ImageFont
except ImportError:
    sys.exit("Pillow が必要です: pip3 install Pillow")

S = 2                      # スーパーサンプリング倍率（最後に1280x720へ縮小）
CW, CH = 1280, 720
W, H = CW * S, CH * S

NAVY = (11, 37, 69)        # 右パネル #0b2545
EM = (52, 211, 153)        # エメラルド
EM_D = (16, 150, 110)
LIGHT = (127, 192, 201)    # 小見出し #7fc0c9
CREAM = (232, 222, 196)
DEEP = (8, 70, 82)
WHITE = (255, 255, 255)
BRAND = (0, 82, 100)       # ワードマーク #005264

DEFAULT_FONT = "/System/Library/Fonts/Hiragino Sans GB.ttc"
DEFAULT_FONT_INDEX = 2     # W6（太字）
WORDMARK_FONT = "/System/Library/Fonts/Supplemental/Arial Bold.ttf"
DEFAULT_LOGO = os.path.expanduser(
    "~/Library/CloudStorage/GoogleDrive-yusuke.kitashiba@gmail.com/"
    "マイドライブ/Watt&Commons/04_Brand/watt and commons logo")
LOGO_CROP = (522, 224, 758, 460)   # ロゴ原本（1280x720）の、輪＋W＋緑の角の範囲


class Ctx:
    def __init__(self, font_path, font_index, logo_path):
        self.font_path, self.font_index, self.logo_path = font_path, font_index, logo_path

    def font(self, size):
        return ImageFont.truetype(self.font_path, int(size * S), index=self.font_index)


# ───────────────────────── 背景 ─────────────────────────
def base_image(ctx, tone="teal"):
    """左半分の背景。tone: teal（明るめのティール。地図・チェックの図）／dark（暗め。電力網の図）"""
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)
    for y in range(H):                       # 上から下へ、わずかなグラデーション
        t = y / H
        c = (int(10 + 6 * t), int(99 - 14 * t), int(112 - 14 * t)) if tone == "teal" \
            else (int(9 + 4 * t), int(62 - 10 * t), int(84 - 14 * t))
        d.line([(0, y), (640 * S, y)], fill=c)
    return img


# ───────────────────── イラスト：重ね合わせた2枚の地図 ─────────────────────
def _contour(cx, cy, r0, phase, seed, n=240):
    rnd = random.Random(seed)
    a1, a2 = rnd.uniform(.08, .14), rnd.uniform(.04, .08)
    pts = []
    for i in range(n + 1):
        th = 2 * math.pi * i / n
        r = r0 * (1 + a1 * math.sin(3 * th + phase) + a2 * math.sin(5 * th + phase * 1.7))
        pts.append((cx + r * math.cos(th) * 1.15, cy + r * math.sin(th) * 0.9))
    return pts


def _sheet(w, h, line, fill, seed, shift):
    L = Image.new("RGBA", (w * S, h * S), (0, 0, 0, 0))
    g = ImageDraw.Draw(L)
    g.rounded_rectangle([0, 0, w * S - 1, h * S - 1], radius=22 * S, fill=fill + (235,),
                        outline=line + (255,), width=3 * S)
    for gx in range(40, w, 40):
        g.line([(gx * S, 18 * S), (gx * S, (h - 18) * S)], fill=line + (70,), width=S)
    for gy in range(40, h, 40):
        g.line([(18 * S, gy * S), ((w - 18) * S, gy * S)], fill=line + (70,), width=S)
    for k, r in enumerate((135, 108, 82, 56, 30)):
        pts = _contour((w / 2 + shift[0]) * S, (h / 2 + shift[1]) * S, r * S, seed * 0.7 + k * 0.35, seed + k)
        g.line(pts, fill=line + (255,), width=3 * S, joint="curve")
    return L


def draw_sheets(img, ctx, **_):
    A = _sheet(300, 380, CREAM, DEEP, 3, (0, 0)).rotate(7, expand=True, resample=Image.BICUBIC)
    B = _sheet(300, 380, LIGHT, (14, 84, 96), 3, (14, -10)).rotate(-6, expand=True, resample=Image.BICUBIC)
    rgba = img.convert("RGBA")

    def shadow(L):
        a = L.split()[3].point(lambda v: int(v * 0.35))
        return Image.merge("RGBA", (Image.new("L", L.size, 0),) * 3 + (a,)).filter(ImageFilter.GaussianBlur(10 * S))

    def paste(layer, cx, cy):
        rgba.alpha_composite(layer, (int(cx * S - layer.width / 2), int(cy * S - layer.height / 2)))

    paste(shadow(A), 270, 465); paste(A, 262, 455)
    paste(shadow(B), 400, 442); paste(B, 392, 432)
    img = rgba.convert("RGB")
    d = ImageDraw.Draw(img)
    for cy in (300, 380, 460):                 # チェックマーク（丸バッジ）
        r = 19
        d.ellipse([(568 - r) * S, (cy - r) * S, (568 + r) * S, (cy + r) * S], fill=DEEP, outline=CREAM, width=3 * S)
        d.line([((568 - r * .45) * S, (cy + r * .02) * S), ((568 - r * .1) * S, (cy + r * .38) * S),
                ((568 + r * .5) * S, (cy - r * .34) * S)], fill=CREAM, width=int(4 * S), joint="curve")
        for j, wd in enumerate((70, 46)):      # 数字の列を表す短い横棒（文字ではなく図形）
            d.rounded_rectangle([450 * S, (cy - 12 + j * 16) * S, (450 + wd) * S, (cy - 12 + j * 16 + 7) * S],
                                radius=3 * S, fill=CREAM if j == 0 else LIGHT)
    return img


# ───────────────────── イラスト：電力網の一点へ、手が伸びる ─────────────────────
def _grid(img, cx, cy, seed):
    d = ImageDraw.Draw(img)
    rnd = random.Random(seed)
    nodes = []
    for ring, (r, n) in enumerate(((120, 6), (230, 9), (330, 12))):
        for i in range(n):
            a = 2 * math.pi * i / n + rnd.uniform(-.2, .2) + ring * .4
            rr = r * rnd.uniform(.9, 1.1)
            nodes.append((cx + rr * math.cos(a), cy + rr * math.sin(a) * .95))
    pts = [(cx, cy)] + nodes
    for p in pts:
        for q in sorted(pts, key=lambda q: (q[0] - p[0]) ** 2 + (q[1] - p[1]) ** 2)[1:3]:
            d.line([(p[0] * S, p[1] * S), (q[0] * S, q[1] * S)], fill=EM_D, width=2 * S)
    for p in nodes:
        d.ellipse([(p[0] - 6) * S, (p[1] - 6) * S, (p[0] + 6) * S, (p[1] + 6) * S],
                  fill=(14, 84, 96), outline=EM, width=2 * S)


def _hand(scale, fill=(8, 30, 56), edge=EM, curl=30):
    """手首が中央(400,400)の正方キャンバス。指先は +x 方向。腕は左へ長く伸ばす。"""
    N = 800
    L = Image.new("RGBA", (N * S, N * S), (0, 0, 0, 0))
    g = ImageDraw.Draw(L)
    ox, oy = 400 * S, 400 * S

    def cap(p, q, w, col):
        g.line([p, q], fill=col, width=int(w * S))
        for c in (p, q):
            g.ellipse([c[0] - w * S / 2, c[1] - w * S / 2, c[0] + w * S / 2, c[1] + w * S / 2], fill=col)

    def seg(o, deg, ln):
        r = math.radians(deg)
        return (o[0] + ln * S * math.cos(r), o[1] + ln * S * math.sin(r))

    parts = [("poly", [(ox - 395 * S, oy - 44 * S), (ox + 110 * S, oy - 58 * S),
                       (ox + 130 * S, oy + 58 * S), (ox - 395 * S, oy + 44 * S)])]
    for i, off in enumerate((-46, -15, 15, 44)):
        bp = (ox + 122 * S, oy + off * S)
        ln = 58 + (8 if i in (1, 2) else 0)
        p1 = seg(bp, off * .15, ln)
        p2 = seg(p1, off * .15 + (curl if off < 0 else -curl), ln * .78)
        parts += [("cap", bp, p1, 30), ("cap", p1, p2, 26)]
    tb = (ox + 60 * S, oy - 46 * S)
    t1 = seg(tb, -58, 60)
    t2 = seg(t1, -20, 46)
    parts += [("cap", tb, t1, 30), ("cap", t1, t2, 26)]

    def paint(col, grow):
        for p in parts:
            if p[0] == "poly":
                g.polygon(p[1], fill=col)
                if grow:
                    g.line(p[1] + [p[1][0]], fill=col, width=int(grow * S), joint="curve")
            else:
                cap(p[1], p[2], p[3] + grow, col)

    paint(edge + (255,), 5)
    paint(fill + (255,), 0)
    if scale != 1.0:
        L = L.resize((int(L.width * scale), int(L.height * scale)), Image.LANCZOS)
    return L


HAND_LAYOUTS = {   # (手首が来る方向°, 中心からの距離, 拡大率)
    2: [(195, 235, .7), (335, 215, .7)],
    3: [(205, 215, .62), (318, 215, .62), (82, 215, .62)],
    4: [(180, 225, .55), (270, 205, .55), (0, 215, .55), (90, 205, .55)],
}


def draw_hands(img, ctx, hands=3, **_):
    cx, cy = 330, 430
    _grid(img, cx, cy, {2: 7, 3: 3, 4: 5}.get(hands, 3))
    rgba = img.convert("RGBA")
    d = ImageDraw.Draw(rgba)
    for r in (38, 26):
        d.ellipse([(cx - r) * S, (cy - r) * S, (cx + r) * S, (cy + r) * S], outline=EM + (255,), width=2 * S)
    for ang, dist, sc in HAND_LAYOUTS[hands]:
        L = _hand(sc)
        th = math.radians(ang)
        wx, wy = cx * S + dist * S * math.cos(th), cy * S + dist * S * math.sin(th)
        Lr = L.rotate(-(ang + 180), resample=Image.BICUBIC)
        rgba.alpha_composite(Lr, (int(wx - Lr.width / 2), int(wy - Lr.height / 2)))
    d = ImageDraw.Draw(rgba)
    d.ellipse([(cx - 13) * S, (cy - 13) * S, (cx + 13) * S, (cy + 13) * S], fill=EM + (255,))
    return rgba.convert("RGB")


# ───────────────────── イラスト：外部画像 ─────────────────────
def draw_image(img, ctx, image=None, **_):
    if not image:
        sys.exit("--illustration image には --image が必要です")
    src = Image.open(image).convert("RGB")
    tw, th = 640 * S, H
    k = max(tw / src.width, th / src.height)
    src = src.resize((int(src.width * k), int(src.height * k)), Image.LANCZOS)
    x, y = (src.width - tw) // 2, (src.height - th) // 2
    img.paste(src.crop((x, y, x + tw, y + th)), (0, 0))
    return img


ILLUSTRATIONS = {"sheets": draw_sheets, "hands": draw_hands, "image": draw_image}


# ───────────────────── パネル・ロゴ ─────────────────────
def draw_panel(img, ctx, subtitle, lines, size):
    d = ImageDraw.Draw(img)
    d.rectangle([640 * S, 0, W, H], fill=NAVY)
    f = ctx.font(size)
    maxw = max((d.textlength(t, font=f) for t in lines if t), default=0) / S
    if maxw > 540:                                   # 長い行は縮小
        size = size * 540 / maxw
        f = ctx.font(size)
    lh, gap = size * 1.3, size * 0.28
    n_text = sum(1 for t in lines if t)
    n_gap = sum(1 for t in lines if not t)
    block = 22 * 1.3 + 24 + n_text * lh + n_gap * gap
    top = max(40, (CH - block) / 2)
    cx = 960

    def centered(text, font, y, fill, sw):
        w = d.textlength(text, font=font)
        d.text((cx * S - w / 2, y * S), text, font=font, fill=fill, stroke_width=sw, stroke_fill=fill)

    centered(subtitle, ctx.font(22), top, LIGHT, 1)
    y = top + 22 * 1.3 + 24
    for t in lines:
        if not t:
            y += gap
            continue
        centered(t, f, y, WHITE, 2)
        y += lh
    return img


def draw_badge(img, ctx, position):
    d = ImageDraw.Draw(img)
    left = 50
    top = 40 if position == "top-left" else 520
    d.rounded_rectangle([left * S, top * S, (left + 180) * S, (top + 190) * S], radius=16 * S, fill=WHITE)
    if not os.path.exists(ctx.logo_path):
        sys.exit(f"ロゴ原本が見つかりません: {ctx.logo_path}（--logo または EYECATCH_LOGO で指定）")
    logo = Image.open(ctx.logo_path).convert("RGB").crop(LOGO_CROP).resize((130 * S, 130 * S), Image.LANCZOS)
    img.paste(logo, ((left + 25) * S, (top + 8) * S))
    wm = ImageFont.truetype(WORDMARK_FONT, 15 * S)
    txt = "Watt & Commons"
    w = d.textlength(txt, font=wm)
    d.text(((left + 90) * S - w / 2, (top + 158) * S), txt, font=wm, fill=BRAND)
    return img


def check_title(lines):
    for t in lines:
        if t and (t[0] in "—―－-" or t[-1] in "—―－-"):
            print(f"警告: 行の先頭・末尾にダッシュがあります: {t!r}", file=sys.stderr)


def main():
    ap = argparse.ArgumentParser(description="アイキャッチ（1280x720）をローカルで生成する")
    ap.add_argument("out", help="出力PNGのパス")
    ap.add_argument("--subtitle", required=True, help="小見出し（シリーズ名と回、または「コラム」など）")
    ap.add_argument("--line", action="append", required=True, help="タイトルの1行（複数回指定。\"\"は行間）")
    ap.add_argument("--illustration", choices=sorted(ILLUSTRATIONS), default="sheets")
    ap.add_argument("--hands", type=int, choices=(2, 3, 4), default=3, help="hands の手の本数")
    ap.add_argument("--image", help="--illustration image のときの画像ファイル")
    ap.add_argument("--badge", choices=("top-left", "bottom-left"), default="top-left")
    ap.add_argument("--size", type=float, default=50, help="タイトルの文字サイズ（既定50）")
    ap.add_argument("--logo", default=os.environ.get("EYECATCH_LOGO", DEFAULT_LOGO))
    ap.add_argument("--font", default=DEFAULT_FONT)
    ap.add_argument("--font-index", type=int, default=DEFAULT_FONT_INDEX)
    a = ap.parse_args()

    check_title(a.line)
    ctx = Ctx(a.font, a.font_index, a.logo)
    img = base_image(ctx, "dark" if a.illustration == "hands" else "teal")
    img = ILLUSTRATIONS[a.illustration](img, ctx, hands=a.hands, image=a.image)
    img = draw_panel(img, ctx, a.subtitle, a.line, a.size)
    img = draw_badge(img, ctx, a.badge)
    out = img.resize((CW, CH), Image.LANCZOS)
    out.save(a.out)
    print(f"保存しました: {a.out} ({CW}x{CH})")


if __name__ == "__main__":
    main()
