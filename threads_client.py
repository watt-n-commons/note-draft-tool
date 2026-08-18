"""Threads API (Meta) の共通クライアント。

.env の読み書きと、投稿・トークン更新のHTTP呼び出しだけを担当する。
初回トークン取得は threads_auth_init.py、定期更新は threads_refresh_token.py、
実際の投稿は announce_threads.py が呼び出す。
"""

import json
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

GRAPH_BASE = "https://graph.threads.net/v1.0"
TOKEN_HOST = "https://graph.threads.net"
AUTH_HOST = "https://threads.net"

ENV_PATH = Path(__file__).parent / ".env"


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


def save_env(updates, path=ENV_PATH):
    """.env の指定キーだけ更新する。存在しないキーは末尾に追記する。"""
    lines = path.read_text(encoding="utf-8").splitlines() if path.exists() else []
    seen = set()
    new_lines = []
    for line in lines:
        stripped = line.strip()
        if stripped and not stripped.startswith("#") and "=" in stripped:
            key = stripped.split("=", 1)[0].strip()
            if key in updates:
                new_lines.append(f"{key}={updates[key]}")
                seen.add(key)
                continue
        new_lines.append(line)
    for key, value in updates.items():
        if key not in seen:
            new_lines.append(f"{key}={value}")
    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


class ThreadsAPIError(Exception):
    pass


def _request(url, data=None, method="GET"):
    headers = {}
    body = None
    if data is not None:
        body = urllib.parse.urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as e:
        detail = e.read().decode("utf-8", errors="replace")
        raise ThreadsAPIError(f"Threads API error {e.code}: {detail}") from e


# --- 投稿 -------------------------------------------------------------

def create_text_container(user_id, access_token, text):
    url = f"{GRAPH_BASE}/{user_id}/threads"
    return _request(
        url,
        data={"media_type": "TEXT", "text": text, "access_token": access_token},
        method="POST",
    )


def publish_container(user_id, access_token, creation_id):
    url = f"{GRAPH_BASE}/{user_id}/threads_publish"
    return _request(
        url,
        data={"creation_id": creation_id, "access_token": access_token},
        method="POST",
    )


def get_permalink(media_id, access_token):
    params = urllib.parse.urlencode({"fields": "permalink", "access_token": access_token})
    result = _request(f"{GRAPH_BASE}/{media_id}?{params}", method="GET")
    return result.get("permalink")


def post_text(user_id, access_token, text):
    """テキスト投稿をコンテナ作成→公開の2段階で行い、(投稿ID, パーマリンク)を返す。"""
    created = create_text_container(user_id, access_token, text)
    creation_id = created["id"]
    published = publish_container(user_id, access_token, creation_id)
    post_id = published["id"]
    permalink = get_permalink(post_id, access_token)
    return post_id, permalink


# --- トークン -----------------------------------------------------------

def exchange_code_for_short_lived_token(app_id, app_secret, redirect_uri, code):
    return _request(
        f"{TOKEN_HOST}/oauth/access_token",
        data={
            "client_id": app_id,
            "client_secret": app_secret,
            "grant_type": "authorization_code",
            "redirect_uri": redirect_uri,
            "code": code,
        },
        method="POST",
    )


def exchange_for_long_lived_token(app_secret, short_lived_token):
    params = urllib.parse.urlencode({
        "grant_type": "th_exchange_token",
        "client_secret": app_secret,
        "access_token": short_lived_token,
    })
    return _request(f"{TOKEN_HOST}/access_token?{params}", method="GET")


def refresh_long_lived_token(access_token):
    params = urllib.parse.urlencode({
        "grant_type": "th_refresh_token",
        "access_token": access_token,
    })
    return _request(f"{TOKEN_HOST}/refresh_access_token?{params}", method="GET")
