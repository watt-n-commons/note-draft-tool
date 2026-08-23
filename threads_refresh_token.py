#!/usr/bin/env python3
"""Threadsの長期アクセストークンを定期更新する（cronからの実行を想定）。

長期トークンは発行から60日で失効し、失効すると自動更新できず
threads_auth_init.py によるブラウザ経由の再認可が必要になる。
そのため、発行から REFRESH_AFTER_DAYS 日経過したら早めに更新する。
cronで毎日実行しても、閾値未満なら何もせず終了する（冪等）。

使い方（通常はcron専用。手動で強制更新したい場合のみ --force）:
    python3 threads_refresh_token.py
    python3 threads_refresh_token.py --force
"""

import argparse
import sys
import time

from threads_client import ThreadsAPIError, load_env, refresh_long_lived_token, save_env

REFRESH_AFTER_DAYS = 45  # 60日失効に対して余裕を持たせる


def log(message):
    # cron側で `>> threads_refresh.log 2>&1` によりstdoutをログファイルへ
    # リダイレクトしているため、ここでは標準出力にだけ書く
    # （ファイルへも直接書くと、cron実行時に二重に記録されてしまう）
    line = f"{time.strftime('%Y-%m-%d %H:%M:%S')} {message}"
    print(line)


def main():
    parser = argparse.ArgumentParser(description="Threadsトークンの定期更新")
    parser.add_argument("--force", action="store_true", help="経過日数に関わらず更新する")
    args = parser.parse_args()

    env = load_env()
    token = env.get("THREADS_ACCESS_TOKEN")
    issued_at = env.get("THREADS_TOKEN_ISSUED_AT")
    if not token or not issued_at:
        log("ERROR: THREADS_ACCESS_TOKEN / THREADS_TOKEN_ISSUED_AT が.envにありません。"
            "threads_auth_init.py を先に実行してください。")
        sys.exit(1)

    age_days = (time.time() - int(issued_at)) / 86400
    if not args.force and age_days < REFRESH_AFTER_DAYS:
        log(f"SKIP: トークンは発行から{age_days:.1f}日（閾値{REFRESH_AFTER_DAYS}日未満）")
        return

    try:
        result = refresh_long_lived_token(token)
    except ThreadsAPIError as e:
        log(f"ERROR: 更新に失敗しました: {e}")
        sys.exit(1)

    save_env({
        "THREADS_ACCESS_TOKEN": result["access_token"],
        "THREADS_TOKEN_ISSUED_AT": str(int(time.time())),
    })
    expires_in_days = int(result.get("expires_in", 0)) // 86400
    log(f"OK: トークンを更新しました（発行から{age_days:.1f}日経過、新しい有効期限は約{expires_in_days}日）")


if __name__ == "__main__":
    main()
