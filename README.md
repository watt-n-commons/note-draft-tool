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

# 実際に下書きを保存（初回は新規作成、2回目以降は自動で上書き更新）
python note_draft.py drafts/2026-07-27_sample.md

# note_idがあっても新規の下書きとして作成したい場合
python note_draft.py drafts/2026-07-27_sample.md --new

# check_article.pyによる公開前チェックをスキップする場合
python note_draft.py drafts/2026-07-27_sample.md --skip-check
```

## 処理の流れ

1. 保存前に `check_article.py` の公開前チェックを実行する（ERRORがあれば中断。`--skip-check`で無効化可）
2. frontmatterに `note_id` が無ければ `POST /api/v1/text_notes` で新規下書きの器を作成し、`note_id`/`note_key` を取得してfrontmatterに書き戻す
3. `POST /api/v1/text_notes/draft_save?id={note_id}&is_temp_saved=true` で本文を保存
4. `https://editor.note.com/notes/{note_key}/edit` を下書きURLとして表示

**挙動:** 同じファイルを編集して再実行すると、frontmatterに書き込まれた `note_id` を使って既存の下書きを上書き更新する（新しい下書きは増えない）。別の下書きとして新規作成したい場合は `--new` を付ける。

## 現在の状況

- [x] frontmatter解析（title / tags / note_id / note_key）
- [x] Markdown → note.comブロックエディタ形式のHTML変換（見出しh2/h3・太字・斜体・取り消し線・リスト・リンク、各ブロックへのUUID付与）
- [x] `.env` からのCookie読み込み
- [x] `--dry-run` モード
- [x] Cookie失効（401/403）検知、想定外レスポンス時のログ出力
- [x] 下書き作成・保存APIの実装（実アカウントで動作確認済み）
- [x] 既存下書きの上書き更新（frontmatterの`note_id`を再利用）
- [x] `check_article.py` による保存前の自動チェック（ERRORで中断、`--skip-check`で無効化可）
- [ ] **tagsのAPI送信は未実装**（該当エンドポイントが未確認のため。詳細は `reference/README.md`）

`reference/README.md` に解析の詳細と既知のギャップを記載しています。

## Threads連携

note記事の公開後、Watt & Commonsの Threadsアカウントへ手動で告知投稿できる。
セットアップ手順は `reference/threads_setup.md` を参照。

```bash
# 初回のみ：アクセストークン取得（対話式）
python3 threads_auth_init.py

# note.com側で「公開」した後、手動で実行する
python3 announce_threads.py drafts/xxx.md --comment "一言コメント"
```

`note_draft.py` は下書き保存のみを行う仕様のため、Threadsへの投稿は
自動連動させていない（下書き段階でリンクを告知する事故を防ぐため）。
アクセストークンの60日ごとの更新は `threads_refresh_token.py` をcronに
登録して自動化する。

## 実装メモ：requestsではなくcurlを使っている理由

当初 `requests` ライブラリでPOSTしたところ、実際のブラウザと同一のCookie・ヘッダーでも
CloudFront（note.comのCDN）に `403 Request blocked` で弾かれた。原因はCookie失効ではなく、
`_request_headers()` が User-Agent 等のブラウザ由来ヘッダーを省略していたこと
（bot対策が汎用HTTPクライアントのデフォルトUser-Agent等を検知していたと見られる）。
`reference/draft_request.txt` でキャプチャした実ブラウザのヘッダーをフルセットで
再現することで解決した。実装は `subprocess` 経由でシステムの `curl` コマンドを呼び出す形。

## eyecatch.py（アイキャッチをローカルで生成する）

Canvaを使わずに、標準レイアウト（左：イラスト／右：ネイビーのパネル＋タイトル／左上：ロゴバッジ）の
1280x720のPNGを作る。ロゴは原本の画像をそのまま使い、日本語は太字で書き出される。

```bash
pip3 install Pillow

# 重ね合わせた2枚の地図（見直し・検証）
python3 eyecatch.py out.png --subtitle "コラム" --illustration sheets \
    --line "公開済みの記事を、" --line "見直してみた" --line "" \
    --line "数字の読み違いと、" --line "言葉の精度"

# 電力網の一点へ、手が伸びる図（--hands 2〜4）
python3 eyecatch.py out.png --subtitle "海外比較×ソブリン性　第1回" --illustration hands --hands 3 \
    --line "「進んでいる」" --line "「遅れている」" --line "では比べない" --line "" \
    --line "各国が握ろうと" --line "しているもの"

# 外部のイラスト（Canvaなどで作った絵）を左半分に敷く
python3 eyecatch.py out.png --subtitle "..." --illustration image --image illustration.png --line "..."
```

- タイトルは `--line` を行ごとに指定する（`""` は行間）。行の先頭・末尾にダッシュを置かない。
- ロゴ原本は、既定でDriveの `04_Brand/watt and commons logo`。場所が違えば `--logo` または環境変数 `EYECATCH_LOGO`。
- 日本語フォントは macOS の Hiragino Sans GB（W6）。他OSでは `--font` で指定する。
- 生成物は必ず目視で確認する（行分け・文字の欠け・イラストの重なり）。note への画像アップロードは手動。
