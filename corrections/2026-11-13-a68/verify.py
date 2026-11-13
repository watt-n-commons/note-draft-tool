#!/usr/bin/env python3
"""公開中のart-a68を、訂正前（before.md）・訂正後（corrected.md）と段落単位で比べる。"""
import html, json, os, re, urllib.request
HERE = os.path.dirname(os.path.abspath(__file__))

def norm(s):
    return re.sub(r"\s+", "", html.unescape(re.sub(r"<[^>]+>", "", s)))

def md_paras(path):
    body = open(os.path.join(HERE, path), encoding="utf-8").read().split("---\n", 2)[2]
    out = []
    for l in body.split("\n"):
        l = l.strip()
        if not l or l == "---":
            continue
        l = re.sub(r"^(#+\s+|- |> )", "", l)
        l = re.sub(r"\*\*", "", l)
        l = re.sub(r"\[([^\]]*)\]\([^)]*\)", r"\1", l)
        out.append(norm(l))
    return out

req = urllib.request.Request("https://note.com/api/v3/notes/n54eb2cd5ca38", headers={"User-Agent": "Mozilla/5.0"})
b = json.load(urllib.request.urlopen(req))["data"]["body"]
pub = [norm(x[1]) for x in re.findall(r"<(p|h2|h3|li|blockquote)[^>]*>(.*?)</\1>", b, re.S) if norm(x[1])]
before, after = md_paras("before.md"), md_paras("corrected.md")
text = "".join(pub)
print(f"公開版の段落数: {len(pub)}（訂正前 {len(before)}／訂正後 {len(after)}）")
print(f"p.17: {text.count('p.17')}件（訂正後は注記内の「誤：p.17–18」の1件）／p.16–17: {text.count('p.16–17')}件（訂正後は3件）／訂正した: {text.count('訂正した')}件（訂正後は1件）")
print("判定:", "訂正後と一致（反映済み）" if pub == after else "訂正前と一致（未反映）" if pub == before else "どちらとも不一致")
