#!/usr/bin/env python3
"""
note記事の公開前チェッカー

使い方:
    python3 check_article.py article.md
    python3 check_article.py article.md --config check_config.json
    python3 check_article.py article.md --strict   # WARNも異常終了扱い

終了コード: 0=問題なし / 1=ERRORあり / 2=--strict時にWARNあり
外部パッケージ依存なし（標準ライブラリのみ）。
"""

import argparse
import json
import re
import sys
import unicodedata
from pathlib import Path

# ---------------------------------------------------------------------------
# デフォルト設定（check_config.json で上書き可能）
# ---------------------------------------------------------------------------

DEFAULT_CONFIG = {
    # 文字数レンジ（本文のみ。出典注記は除外してカウント）
    "length_min": 1800,
    "length_max": 2800,

    # 本文に出てはいけない固有企業名。
    # 出典注記セクション内での言及は許容する（データ出所の明記は必要なため）。
    "company_names_body_ng": [
        "東京電力", "TEPCO", "関西電力", "中部電力", "東北電力", "九州電力",
        "NTT", "エヌ・ティ・ティ", "ソフトバンク", "KDDI", "楽天",
        "さくらインターネット", "IIJ", "インターネットイニシアティブ",
        "Equinix", "エクイニクス", "Digital Realty", "デジタルリアルティ",
        "AirTrunk", "エアトランク", "CyrusOne", "サイラスワン",
        "Google", "グーグル", "Amazon", "アマゾン", "AWS",
        "Microsoft", "マイクロソフト", "Meta", "OpenAI", "Oracle",
    ],

    # 本業と重なりが大きく、書き方に注意が必要なテーマ語
    "conflict_of_interest_terms": [
        "ワット・ビット", "ワットビット", "watt-bit",
    ],

    # 未確定のまま公開してはいけないプレースホルダ
    "placeholders": [
        "TODO", "FIXME", "TBD", "未定", "要確認", "あとで",
        "[リンク]", "[URL]", "[マップはこちら]", "（未）", "XXX",
        "http://example.com", "https://example.com",
    ],

    # 出典注記セクションを検出する目印
    "citation_markers": ["出典", "注記", "データ出所", "※データ"],

    # 数値の断定を検出（近似値・試算に「である」と書いていないか）
    "estimate_hedge_terms": ["近似", "試算", "推計", "概算", "目安", "参考値"],

    # 見出しの最低文字数（キーメッセージ的な一文を推奨、体言止めを警告）
    "heading_min_length": 12,
}


class Finding:
    def __init__(self, level, rule, message, line=None):
        self.level = level  # "ERROR" / "WARN" / "INFO"
        self.rule = rule
        self.message = message
        self.line = line

    def __str__(self):
        loc = f" (L{self.line})" if self.line else ""
        return f"[{self.level}] {self.rule}{loc}: {self.message}"


# ---------------------------------------------------------------------------
# ユーティリティ
# ---------------------------------------------------------------------------

def strip_frontmatter(text):
    """先頭のYAML frontmatter（---で囲まれたブロック）を取り除く。

    frontmatterの閉じ`---`が、本文と出典の区切り線と誤認されるのを防ぐため、
    本文チェックの前段で必ず取り除く。
    """
    lines = text.split("\n")
    if not lines or lines[0].strip() != "---":
        return text
    for i in range(1, len(lines)):
        if lines[i].strip() == "---":
            return "\n".join(lines[i + 1:])
    return text  # 閉じの --- が無ければfrontmatterとはみなさない


def split_body_and_citations(text, markers):
    """本文と出典注記セクションを分離する。

    最後の水平線(---)以降、または出典見出し以降を注記とみなす。
    呼び出し側でfrontmatterを除去済みであることを前提とする。
    """
    lines = text.split("\n")

    # 出典っぽい見出し行を後ろから探す
    for i in range(len(lines) - 1, -1, -1):
        line = lines[i].strip()
        stripped = line.lstrip("#*　 ").rstrip("*")
        if any(stripped.startswith(m) for m in markers):
            return "\n".join(lines[:i]), "\n".join(lines[i:])

    # 見つからなければ最後の --- で分割
    for i in range(len(lines) - 1, -1, -1):
        if lines[i].strip() == "---":
            return "\n".join(lines[:i]), "\n".join(lines[i + 1:])

    return text, ""


def count_chars(text):
    """日本語記事の「字数」に近い数え方。

    空白・改行・markdown記号を除いた可視文字数。
    """
    text = re.sub(r"^#{1,6}\s*", "", text, flags=re.M)   # 見出し記号
    text = re.sub(r"[*_`>\[\]()]", "", text)              # 強調・リンク記号
    text = re.sub(r"^\s*[-–—]\s*", "", text, flags=re.M)  # 箇条書き
    text = re.sub(r"\s+", "", text)                       # 空白全般
    return len(text)


def line_of(text, index):
    return text[:index].count("\n") + 1


def find_terms(text, terms, rule, level, msg_fmt):
    """語のリストを本文から探して Finding を返す。"""
    findings = []
    for term in terms:
        for m in re.finditer(re.escape(term), text, flags=re.IGNORECASE):
            findings.append(
                Finding(level, rule, msg_fmt.format(term=term), line_of(text, m.start()))
            )
            break  # 同じ語は1件だけ報告
    return findings


# ---------------------------------------------------------------------------
# 各チェック
# ---------------------------------------------------------------------------

def check_length(body, cfg):
    n = count_chars(body)
    lo, hi = cfg["length_min"], cfg["length_max"]
    if n < lo:
        return [Finding("WARN", "文字数", f"本文{n}字。目安{lo}〜{hi}字を下回っています")]
    if n > hi:
        return [Finding("WARN", "文字数", f"本文{n}字。目安{lo}〜{hi}字を超えています")]
    return [Finding("INFO", "文字数", f"本文{n}字（目安{lo}〜{hi}字の範囲内）")]


def check_companies(body, cfg):
    return find_terms(
        body, cfg["company_names_body_ng"], "固有企業名", "WARN",
        "本文に「{term}」が含まれています。業界潮流としての記述に書き換えるか、出典注記へ移してください",
    )


def check_conflict_of_interest(body, cfg):
    return find_terms(
        body, cfg["conflict_of_interest_terms"], "利益相反", "WARN",
        "本業と重なるテーマ語「{term}」が含まれています。公開情報のみに基づく記述か確認してください",
    )


def check_placeholders(text, cfg):
    """未確定のプレースホルダを検出する。

    [マップはこちら] のような角括弧プレースホルダは、直後に (URL) が
    続いていれば実際のMarkdownリンクなので誤検知としない。
    """
    findings = []
    for term in cfg["placeholders"]:
        if term.startswith("[") and term.endswith("]"):
            pattern = re.escape(term) + r"(?!\()"
        else:
            pattern = re.escape(term)
        for m in re.finditer(pattern, text, flags=re.IGNORECASE):
            findings.append(
                Finding("ERROR", "未確定", f"プレースホルダ「{term}」が残っています", line_of(text, m.start()))
            )
            break  # 同じ語は1件だけ報告
    return findings


def check_citations(citations, cfg):
    if not citations.strip():
        return [Finding("ERROR", "出典注記", "出典・注記セクションが見つかりません")]

    findings = []
    if not re.search(r"(20\d{2})[年/\-]", citations):
        findings.append(
            Finding("WARN", "出典注記", "基準日（〇〇年）の記載が見当たりません")
        )
    return findings


def check_estimates(body, cfg):
    """試算値に断定表現を使っていないか。"""
    findings = []
    hedges = cfg["estimate_hedge_terms"]

    # 「MW」を含む文を抜き出し、ヘッジ語なしで断定していないか見る
    sentences = re.split(r"[。\n]", body)
    for s in sentences:
        if "MW" not in s:
            continue
        if any(h in s for h in hedges):
            continue
        if re.search(r"(である|だ|ある)$", s.strip()):
            findings.append(
                Finding("WARN", "数値の断定", f"試算値の可能性がある数値を断定しています: 「{s.strip()[:40]}…」")
            )
    return findings


def check_headings(body, cfg):
    findings = []
    for m in re.finditer(r"^(#{2,6})\s*(.+)$", body, flags=re.M):
        heading = m.group(2).strip()
        if len(heading) < cfg["heading_min_length"]:
            findings.append(
                Finding("WARN", "見出し", f"「{heading}」が短く、キーメッセージになっていない可能性があります",
                        line_of(body, m.start()))
            )
    return findings


def check_broken_markdown(text):
    findings = []
    # 閉じていないリンク
    for m in re.finditer(r"\[[^\]]*\]\((?![^)]*\))", text):
        findings.append(Finding("ERROR", "書式", "閉じられていないリンク記法があります", line_of(text, m.start())))
    # 全角括弧のURL
    for m in re.finditer(r"（https?://", text):
        findings.append(Finding("WARN", "書式", "URLが全角括弧で囲まれています", line_of(text, m.start())))
    return findings


# ---------------------------------------------------------------------------
# メイン
# ---------------------------------------------------------------------------

def run_checks(text, cfg):
    text = strip_frontmatter(text)
    body, citations = split_body_and_citations(text, cfg["citation_markers"])

    findings = []
    findings += check_length(body, cfg)
    findings += check_companies(body, cfg)
    findings += check_conflict_of_interest(body, cfg)
    findings += check_placeholders(text, cfg)
    findings += check_citations(citations, cfg)
    findings += check_estimates(body, cfg)
    findings += check_headings(body, cfg)
    findings += check_broken_markdown(text)
    return findings


def main():
    ap = argparse.ArgumentParser(description="note記事の公開前チェック")
    ap.add_argument("path", help="チェック対象のmarkdownファイル")
    ap.add_argument("--config", help="設定JSONのパス")
    ap.add_argument("--strict", action="store_true", help="WARNも異常終了扱いにする")
    ap.add_argument("--quiet", action="store_true", help="INFOを表示しない")
    args = ap.parse_args()

    cfg = dict(DEFAULT_CONFIG)
    if args.config:
        cfg.update(json.loads(Path(args.config).read_text(encoding="utf-8")))

    text = Path(args.path).read_text(encoding="utf-8")
    findings = run_checks(text, cfg)

    errors = [f for f in findings if f.level == "ERROR"]
    warns = [f for f in findings if f.level == "WARN"]
    infos = [f for f in findings if f.level == "INFO"]

    print(f"=== {args.path} ===")
    for f in errors + warns + (infos if not args.quiet else []):
        print(f)

    print(f"\nERROR {len(errors)} / WARN {len(warns)}")

    if errors:
        return 1
    if args.strict and warns:
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
