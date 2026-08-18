#!/usr/bin/env python3
"""note記事を「公開した後」に、手動でThreadsへ告知投稿するスクリプト。

note_draft.py は下書きの作成・更新のみを行い、実際の公開はnote.comの
エディタ上で手動で行う仕様になっている。そのため、このスクリプトを
note_draft.py実行時に自動連動させることはしない
（下書きの段階でThreadsに公開リンクを告知してしまう事故を防ぐため）。

使い方（note.com側で「公開」ボタンを押した後に、自分で実行する）:
    python3 announce_threads.py drafts/2026-08-09_connect-and-manage.md \
        --comment "系統の混雑対策、英・愛・日を比較しました"

    # 投稿内容を確認するだけ（APIは叩かない）
    python3 announce_threads.py drafts/xxx.md --comment "..." --dry-run

    # 二重投稿チェックを無視して再投稿する
    python3 announce_threads.py drafts/xxx.md --comment "..." --force
"""

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))
from note_draft import parse_frontmatter  # noqa: E402
from threads_client import ThreadsAPIError, load_env, post_text  # noqa: E402

POSTED_LOG_PATH = Path(__file__).parent / "threads_posted.json"
MAX_TEXT_LENGTH = 500


def load_posted_log():
    if not POSTED_LOG_PATH.exists():
        return {}
    return json.loads(POSTED_LOG_PATH.read_text(encoding="utf-8"))


def save_posted_log(log):
    POSTED_LOG_PATH.write_text(
        json.dumps(log, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def build_article_url(username, note_key):
    return f"https://note.com/{username}/n/{note_key}"


def build_text(title, comment, url):
    text = f"{title}\n\n{comment}\n\n{url}"
    if len(text) > MAX_TEXT_LENGTH:
        sys.exit(
            f"投稿本文が{len(text)}文字でThreadsの上限({MAX_TEXT_LENGTH}文字)を超えています。"
            "--comment を短くしてください。"
        )
    return text


def main():
    parser = argparse.ArgumentParser(description="公開済みnote記事をThreadsへ告知投稿する")
    parser.add_argument("filepath", help="drafts/内のMarkdownファイルパス")
    parser.add_argument("--comment", required=True, help="記事タイトルに添える一言コメント")
    parser.add_argument("--dry-run", action="store_true", help="投稿内容を表示するだけ")
    parser.add_argument("--force", action="store_true", help="二重投稿チェックを無視する")
    args = parser.parse_args()

    source_path = Path(args.filepath)
    if not source_path.exists():
        sys.exit(f"ファイルが見つかりません: {source_path}")

    text = source_path.read_text(encoding="utf-8")
    meta, _ = parse_frontmatter(text)

    note_id = meta.get("note_id")
    note_key = meta.get("note_key")
    if not note_id or not note_key:
        sys.exit(
            "frontmatterに note_id / note_key がありません。"
            "先に note_draft.py で下書きを保存してください。"
        )

    env = load_env()
    username = env.get("NOTE_USERNAME")
    if not username:
        sys.exit("NOTE_USERNAME が .env に設定されていません。")

    posted_log = load_posted_log()
    if note_id in posted_log and not args.force:
        prev = posted_log[note_id]
        sys.exit(
            f"この記事は既にThreadsへ投稿済みです（{prev['posted_at']}, "
            f"threads_post_id={prev['threads_post_id']}）。再投稿するには --force を付けてください。"
        )

    article_url = build_article_url(username, note_key)
    post_body = build_text(meta["title"], args.comment, article_url)

    if args.dry_run:
        print(post_body)
        return

    access_token = env.get("THREADS_ACCESS_TOKEN")
    threads_user_id = env.get("THREADS_USER_ID")
    if not access_token or not threads_user_id:
        sys.exit(
            "THREADS_ACCESS_TOKEN / THREADS_USER_ID が .env にありません。"
            "threads_auth_init.py を先に実行してください。"
        )

    try:
        threads_post_id, threads_permalink = post_text(threads_user_id, access_token, post_body)
    except ThreadsAPIError as e:
        sys.exit(f"Threadsへの投稿に失敗しました: {e}")

    posted_log[note_id] = {
        "note_key": note_key,
        "title": meta["title"],
        "article_url": article_url,
        "threads_post_id": threads_post_id,
        "threads_permalink": threads_permalink,
        "posted_at": time.strftime("%Y-%m-%dT%H:%M:%S"),
    }
    save_posted_log(posted_log)

    print(f"Threadsに投稿しました: {threads_permalink}")


if __name__ == "__main__":
    main()
