#!/usr/bin/env python3
"""note本番への反映確認（読み取りのみ）。

公開中の記事本文（公開API・ログイン不要）を取得し、各フォルダの
corrected.md（訂正後）/ before.md（訂正前）と文字単位で比較する。

    python3 corrections/2026-10-14-round4/verify.py            # 1記事（art-a36）
    python3 corrections/2026-10-14-round4/verify.py a36     # 1記事だけ
    python3 corrections/2026-10-14-round4/verify.py a25 a27 # 複数
    （フォルダ名の先頭: a36 = art-a36）

判定:
  訂正後と一致  → 反映済み
  訂正前と一致  → 未反映
  どちらでもない → 一部だけ反映／想定外（差分を表示）
あわせて、公開状態・URL（note_key）・ハッシュタグ・アイキャッチの有無も表示する。
"""
import difflib, glob, html, json, os, re, subprocess, sys

HERE = os.path.dirname(os.path.abspath(__file__))


def norm(s):
    s = re.sub(r"https?://[^\s)\"'<]+", "", s)
    s = re.sub(r"<[^>]+>", "", s)
    s = html.unescape(s)
    return re.sub(r"[#*\[\]()\s　_`>\-]", "", s)


def body_of(path):
    m = re.match(r"^---\n.*?\n---\n(.*)$", open(path, encoding="utf-8").read(), re.S)
    return norm(m.group(1) if m else "")


def fetch(key):
    out = subprocess.run(["curl", "-sL", f"https://note.com/api/v3/notes/{key}"], capture_output=True)
    return json.loads(out.stdout)["data"]


def show_diff(a, b, label_a, label_b, width=40):
    sm = difflib.SequenceMatcher(None, a, b, autojunk=False)
    n = 0
    for t, i1, i2, j1, j2 in sm.get_opcodes():
        if t == "equal":
            continue
        n += 1
        if n > 8:
            print("    …（以降省略）")
            break
        print(f"    {label_a}: …{a[max(0,i1-width):i2+width]}…")
        print(f"    {label_b}: …{b[max(0,j1-width):j2+width]}…")


only = sys.argv[1:]
for d in sorted(glob.glob(f"{HERE}/*_n*"), key=lambda p: os.path.basename(p)):
    num, key = os.path.basename(d).split("_", 1)
    if only and num not in only:
        continue
    note = fetch(key)
    pub = norm(note.get("body") or "")
    after = body_of(f"{d}/corrected.md")
    before = body_of(f"{d}/before.md")
    if pub == after:
        verdict = "訂正後と一致（反映済み）"
    elif pub == before:
        verdict = "訂正前と一致（未反映）"
    else:
        r = difflib.SequenceMatcher(None, pub, after, autojunk=False).ratio()
        verdict = f"どちらとも不一致（訂正後との類似度 {r:.3f}）"
    tags = [h["hashtag"]["name"] for h in note.get("hashtag_notes", [])]
    print(f"[{num}] {key}  {note.get('name')}")
    print(f"    判定: {verdict}")
    print(f"    status={note.get('status')} / スキ={note.get('like_count')} / eyecatch={'あり' if note.get('eyecatch') else 'なし'} / タグ{len(tags)}件 {tags}")
    if pub != after and pub != before:
        show_diff(pub, after, "公開中", "訂正後")
