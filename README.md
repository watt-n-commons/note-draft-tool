# note_draft.py

`drafts/` にあるMarkdown記事を note.com の下書きとして保存するスクリプト。
**公開処理は実装していません。下書き作成・更新のみです。**

## セットアップ

外部Pythonパッケージへの依存はありません（標準ライブラリ + システムの `curl` コマンドのみ）。

```bash
cp .env.example .env
```

`.env` にブラウザの開発者ツールから取得したCookieヘッダーを設定してください。

```
NOTE_COOKIE=（noteにログイン中のCookieヘッダーの値）
```

## 使い方

```bash
# ペイロード変換結果だけ確認（APIは叩かない）
python note_draft.py drafts/2026-07-27_sample.md --dry-run

# 実際に下書きを保存
python note_draft.py drafts/2026-07-27_sample.md
```

## 処理の流れ

1. `POST /api/v1/text_notes` で新規下書きの器を作成し、`note_id`/`note_key` を取得
2. `POST /api/v1/text_notes/draft_save?id={note_id}&is_temp_saved=true` で本文を保存
3. `https://editor.note.com/notes/{note_key}/edit` を下書きURLとして表示

**注意:** 実行するたびに新しい下書き記事が1つ作られます（既存下書きの更新ではありません）。
同じファイルを編集して再実行すると、別の下書きが増えます。

## 現在の状況

- [x] frontmatter解析（title / tags）
- [x] Markdown → note.comブロックエディタ形式のHTML変換（見出しh2/h3・太字・斜体・取り消し線・リスト・リンク、各ブロックへのUUID付与）
- [x] `.env` からのCookie読み込み
- [x] `--dry-run` モード
- [x] Cookie失効（401/403）検知、想定外レスポンス時のログ出力
- [x] 下書き作成・保存APIの実装（実アカウントで動作確認済み）
- [ ] **tagsのAPI送信は未実装**（該当エンドポイントが未確認のため。詳細は `reference/README.md`）

`reference/README.md` に解析の詳細と既知のギャップを記載しています。

## 実装メモ：requestsではなくcurlを使っている理由

当初 `requests` ライブラリでPOSTしたところ、実際のブラウザと同一のCookie・ヘッダーでも
CloudFront（note.comのCDN）に `403 Request blocked` で弾かれた。原因はCookie失効ではなく、
`_request_headers()` が User-Agent 等のブラウザ由来ヘッダーを省略していたこと
（bot対策が汎用HTTPクライアントのデフォルトUser-Agent等を検知していたと見られる）。
`reference/draft_request.txt` でキャプチャした実ブラウザのヘッダーをフルセットで
再現することで解決した。実装は `subprocess` 経由でシステムの `curl` コマンドを呼び出す形。
