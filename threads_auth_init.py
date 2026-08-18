#!/usr/bin/env python3
"""Threads APIの初回アクセストークンを取得する（対話式・最初に一度だけ実行）。

前提（reference/threads_setup.md 参照）:
- 投稿用のInstagramアカウントを作成し、Threadsを有効化済み
- Meta for DevelopersでアプリのThreads API use caseを追加済み
- そのInstagramアカウントを、アプリの「Threadsテスター」として追加・承認済み
  （テスターであれば App Review なしで投稿権限を得られる）
- .env に THREADS_APP_ID / THREADS_APP_SECRET / THREADS_REDIRECT_URI を設定済み

使い方:
    python3 threads_auth_init.py

取得した長期トークンとユーザーIDは .env に書き戻される。
2回目以降のトークン更新は threads_refresh_token.py が担当するので、
このスクリプトは通常は最初の1回だけ実行すればよい。
"""

import sys
import time
import urllib.parse

from threads_client import (
    AUTH_HOST,
    ThreadsAPIError,
    exchange_code_for_short_lived_token,
    exchange_for_long_lived_token,
    load_env,
    save_env,
)

SCOPES = "threads_basic,threads_content_publish"


def main():
    env = load_env()
    app_id = env.get("THREADS_APP_ID")
    app_secret = env.get("THREADS_APP_SECRET")
    redirect_uri = env.get("THREADS_REDIRECT_URI")
    if not (app_id and app_secret and redirect_uri):
        sys.exit(
            "THREADS_APP_ID / THREADS_APP_SECRET / THREADS_REDIRECT_URI が.envに"
            "設定されていません。reference/threads_setup.md の手順に沿って設定してください。"
        )

    auth_url = f"{AUTH_HOST}/oauth/authorize?" + urllib.parse.urlencode({
        "client_id": app_id,
        "redirect_uri": redirect_uri,
        "scope": SCOPES,
        "response_type": "code",
    })

    print("1) 次のURLをブラウザで開き、投稿用アカウントでログインして許可してください:\n")
    print(f"   {auth_url}\n")
    print("2) 許可後にリダイレクトされたURLをコピーし、code= の値だけを貼り付けてください")
    print("   （末尾に # が付く場合はそれより前の部分だけを使ってください）\n")
    code = input("code: ").strip().split("#")[0]
    if not code:
        sys.exit("codeが空です。")

    try:
        short = exchange_code_for_short_lived_token(app_id, app_secret, redirect_uri, code)
        long_lived = exchange_for_long_lived_token(app_secret, short["access_token"])
    except ThreadsAPIError as e:
        sys.exit(str(e))

    save_env({
        "THREADS_ACCESS_TOKEN": long_lived["access_token"],
        "THREADS_USER_ID": str(short.get("user_id", env.get("THREADS_USER_ID", ""))),
        "THREADS_TOKEN_ISSUED_AT": str(int(time.time())),
    })

    expires_in_days = int(long_lived.get("expires_in", 0)) // 86400
    print(f"\n長期トークンを取得し、.envに保存しました（有効期限: 約{expires_in_days}日）。")
    print("以降の自動更新は threads_refresh_token.py がcron経由で行います。")


if __name__ == "__main__":
    main()
