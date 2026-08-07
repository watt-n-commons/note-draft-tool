#!/usr/bin/env python3
"""noteの下書きをdrafts/内のMarkdownから作成するスクリプト。公開処理は実装しない。"""

import argparse
import json
import re
import subprocess
import sys
import tempfile
import uuid
from pathlib import Path

ENV_PATH = Path(__file__).parent / ".env"

# reference/draft_request.txt（実際のブラウザ操作のキャプチャ）と
# NoteClient2 (https://github.com/Mr-SuperInsane/NoteClient2) のソースで確認済みの値。
CREATE_NOTE_ENDPOINT = "https://note.com/api/v1/text_notes"
DRAFT_SAVE_ENDPOINT = "https://note.com/api/v1/text_notes/draft_save"


class CookieAuthError(Exception):
    pass


class UnexpectedResponseError(Exception):
    def __init__(self, response_text):
        self.response_text = response_text
        super().__init__("note APIから想定外のレスポンス構造が返されました")


def load_env(path=ENV_PATH):
    env = {}
    if not path.exists():
        return env
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        env[key.strip()] = value.strip().strip('"').strip("'")
    return env


def load_cookie_header():
    env = load_env()
    cookie = env.get("NOTE_COOKIE")
    if not cookie:
        sys.exit(
            "NOTE_COOKIE が .env に設定されていません。"
            "ブラウザの開発者ツールでnoteにログイン中のCookieヘッダーをコピーし、"
            ".env に NOTE_COOKIE=<値> の形式で保存してください。"
        )
    return cookie


def parse_frontmatter(text):
    match = re.match(r"^---\s*\n(.*?)\n---\s*\n(.*)$", text, re.DOTALL)
    if not match:
        sys.exit("frontmatter（--- で囲まれたメタデータ）が見つかりません。")

    raw_meta, body = match.groups()
    meta = {}
    for line in raw_meta.splitlines():
        line = line.strip()
        if not line or ":" not in line:
            continue
        key, value = line.split(":", 1)
        key = key.strip()
        value = value.strip()
        if value.startswith("[") and value.endswith("]"):
            items = value[1:-1].split(",")
            meta[key] = [item.strip() for item in items if item.strip()]
        else:
            meta[key] = value

    if "title" not in meta:
        sys.exit("frontmatterに title がありません。")

    return meta, body.strip()


def _inline(text):
    text = re.sub(r"\[(.+?)\]\((.+?)\)", r'<a href="\2">\1</a>', text)
    text = re.sub(r"\*\*(.+?)\*\*", r"<strong>\1</strong>", text)
    text = re.sub(r"~~(.+?)~~", r"<s>\1</s>", text)
    text = re.sub(r"(?<!\*)\*(?!\*)(.+?)(?<!\*)\*(?!\*)", r"<em>\1</em>", text)
    return text


def markdown_to_note_html(md_text):
    """noteのブロックエディタ形式に変換する。

    各ブロックに一意の name/id (uuid4) が必要で、見出しはh2/h3の2段階のみ、
    リストは <ul><li><p name id>...</p></li></ul> という入れ子構造になる。
    reference/draft_request.txt のキャプチャとNoteClient2のmarkdown_parser.pyで確認済み。
    """
    html_parts = []
    list_buffer = []  # [(kind, text), ...]  kind: "ul" or "ol"

    def flush_list():
        if not list_buffer:
            return
        kind = list_buffer[0][0]
        list_uid = str(uuid.uuid4())
        html_parts.append(f'<{kind} name="{list_uid}" id="{list_uid}">')
        for _, text in list_buffer:
            item_uid = str(uuid.uuid4())
            html_parts.append(f'<li><p name="{item_uid}" id="{item_uid}">{_inline(text)}</p></li>')
        html_parts.append(f"</{kind}>")
        list_buffer.clear()

    for raw_line in md_text.splitlines():
        line = raw_line.strip()

        if not line:
            flush_list()
            continue

        ordered_match = re.match(r"^\d+\.\s+(.*)$", line)
        unordered_match = re.match(r"^-\s+(.*)$", line)
        if ordered_match:
            list_buffer.append(("ol", ordered_match.group(1)))
            continue
        if unordered_match:
            list_buffer.append(("ul", unordered_match.group(1)))
            continue

        flush_list()

        heading_match = re.match(r"^(#{1,3})\s+(.*)$", line)
        quote_match = re.match(r"^>\s+(.*)$", line)
        uid = str(uuid.uuid4())

        if heading_match:
            level = "h3" if len(heading_match.group(1)) == 3 else "h2"
            html_parts.append(f'<{level} name="{uid}" id="{uid}">{_inline(heading_match.group(2))}</{level}>')
        elif quote_match:
            html_parts.append(f'<blockquote name="{uid}" id="{uid}">{_inline(quote_match.group(1))}</blockquote>')
        elif line in ("---", "***"):
            html_parts.append(f'<hr name="{uid}" id="{uid}">')
        else:
            html_parts.append(f'<p name="{uid}" id="{uid}">{_inline(line)}</p>')

    flush_list()
    return "".join(html_parts)


def build_draft_payload(title, html_body):
    # tags(hashtags)は draft_save では送信不可（NoteClient2のソースで確認済み。
    # hashtagsは公開時のPUTでのみ登場し、draft_saveのペイロードには含まれない）。
    plain_text = re.sub(r"<[^>]+>", "", html_body)
    return {
        "body": html_body,
        "body_length": len(plain_text),
        "name": title,
        "index": False,
        "is_lead_form": False,
    }


def _request_headers(cookie_header):
    # reference/draft_request.txt でキャプチャした実ブラウザのヘッダーをそのまま再現する。
    # User-Agent等が無いとCloudFrontのBot対策に403でブロックされることを確認済み。
    return {
        "Cookie": cookie_header,
        "Content-Type": "application/json",
        "Accept": "*/*",
        "Accept-Language": "ja-JP,ja;q=0.9,en-US;q=0.8,en;q=0.7",
        "Origin": "https://editor.note.com",
        "Referer": "https://editor.note.com/",
        "Priority": "u=1, i",
        "Sec-CH-UA": '"Not;A=Brand";v="8", "Chromium";v="150", "Google Chrome";v="150"',
        "Sec-CH-UA-Mobile": "?0",
        "Sec-CH-UA-Platform": '"Chrome OS"',
        "Sec-Fetch-Dest": "empty",
        "Sec-Fetch-Mode": "cors",
        "Sec-Fetch-Site": "same-site",
        "User-Agent": (
            "Mozilla/5.0 (X11; CrOS x86_64 14541.0.0) AppleWebKit/537.36 "
            "(KHTML, like Gecko) Chrome/150.0.0.0 Safari/537.36"
        ),
        "X-Requested-With": "XMLHttpRequest",
    }


def _curl_post(url, headers, payload):
    """POSTリクエストをcurlコマンドで送る。

    同じヘッダー・Cookieでも requests ライブラリだとCloudFrontに403
    (Bot対策と思われる)で弾かれるが、curlコマンドだと通ることを実機で確認済み。
    そのため requests ではなくcurlをsubprocessで呼び出す実装にしている。
    """
    header_args = []
    for key, value in headers.items():
        header_args += ["-H", f"{key}: {value}"]

    with tempfile.NamedTemporaryFile() as body_file:
        try:
            result = subprocess.run(
                ["curl", "-s", "-o", body_file.name, "-w", "%{http_code}",
                 "-X", "POST", url, *header_args, "--data-binary", "@-"],
                input=json.dumps(payload).encode("utf-8"),
                capture_output=True,
            )
        except FileNotFoundError:
            sys.exit("curl コマンドが見つかりません。インストールしてください。")

        if result.returncode != 0:
            raise UnexpectedResponseError(result.stderr.decode("utf-8", errors="replace"))

        status_code = int(result.stdout.decode("ascii").strip())
        body_file.seek(0)
        body_text = body_file.read().decode("utf-8", errors="replace")

    return status_code, body_text


def create_note(cookie_header):
    """新規の下書きの器を作り、note_id・note_keyを取得する。"""
    status_code, body_text = _curl_post(
        CREATE_NOTE_ENDPOINT,
        _request_headers(cookie_header),
        {"template_key": None},
    )

    if status_code in (401, 403):
        raise CookieAuthError("ブラウザでnoteに再ログインしてCookieを更新してください。")

    try:
        data = json.loads(body_text)
    except ValueError:
        raise UnexpectedResponseError(body_text)

    note_data = (data or {}).get("data") or {}
    note_id = note_data.get("id")
    note_key = note_data.get("key")
    if not note_id or not note_key:
        raise UnexpectedResponseError(json.dumps(data, ensure_ascii=False, indent=2))

    return note_id, note_key


def save_draft(note_id, payload, cookie_header):
    url = f"{DRAFT_SAVE_ENDPOINT}?id={note_id}&is_temp_saved=true"
    status_code, body_text = _curl_post(url, _request_headers(cookie_header), payload)

    if status_code in (401, 403):
        raise CookieAuthError("ブラウザでnoteに再ログインしてCookieを更新してください。")

    if status_code not in (200, 201):
        raise UnexpectedResponseError(body_text)

    try:
        data = json.loads(body_text)
    except ValueError:
        raise UnexpectedResponseError(body_text)

    if (data or {}).get("data", {}).get("result") is not True:
        raise UnexpectedResponseError(body_text)


def main():
    parser = argparse.ArgumentParser(description="noteに下書きを保存する")
    parser.add_argument("filepath", help="drafts/内のMarkdownファイルパス")
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="APIを叩かず、変換後のペイロードを表示するだけ",
    )
    args = parser.parse_args()

    source_path = Path(args.filepath)
    if not source_path.exists():
        sys.exit(f"ファイルが見つかりません: {source_path}")

    text = source_path.read_text(encoding="utf-8")
    meta, body = parse_frontmatter(text)
    html_body = markdown_to_note_html(body)
    payload = build_draft_payload(title=meta["title"], html_body=html_body)

    if args.dry_run:
        print(json.dumps(payload, ensure_ascii=False, indent=2))
        if meta.get("tags"):
            print(
                f"# 注意: tags {meta['tags']} はfrontmatterから読み取りましたが、"
                "draft_save APIには送信されません（下書き保存にtagsフィールドは存在しないため）。",
                file=sys.stderr,
            )
        return

    cookie_header = load_cookie_header()

    try:
        note_id, note_key = create_note(cookie_header)
        save_draft(note_id, payload, cookie_header)
    except CookieAuthError as e:
        sys.exit(str(e))
    except UnexpectedResponseError as e:
        print("--- 想定外のレスポンス（生データ） ---")
        print(e.response_text)
        sys.exit(1)

    edit_url = f"https://editor.note.com/notes/{note_key}/edit"
    print(f"下書きを作成しました: {edit_url}")


if __name__ == "__main__":
    main()
