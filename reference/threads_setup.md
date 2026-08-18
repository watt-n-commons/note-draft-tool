# Threads連携セットアップ手順

note記事を公開したときに、Watt & Commons名義のThreadsアカウントへ手動で告知投稿するための
セットアップ手順。2026年8月時点でWeb検索した情報に基づく（Metaの仕様は変わることがあるので、
実際に画面が違う場合はその時点のMeta for Developersの案内に従うこと）。

手順4・6・7は2026-08-10に実際にセットアップして初めて分かった落とし穴を反映済み
（下記「詰まった点」参照）。

## 前提として分かっていること

- Threadsアカウントは**Facebookではなく、Instagramアカウント経由**で作成する。
- **実名確認は不要**。表示名はニックネーム・活動名でよい。
- この用途（自分の1アカウントに投稿するだけ）では、**Meta側の「App Review」
  「Tech Provider Verification」「Business Verification」は不要**。
  投稿先のアカウントを自分のアプリの「テスター」として登録すれば、審査なしで
  `threads_content_publish` 権限を使える。App Reviewが必要になるのは、
  不特定多数のユーザーに使わせる公開アプリを作る場合だけ。
- Meta Developerアカウント自体の作成時に、Account Centerでの**電話番号確認**
  （実名の身分証明ではない）を求められることがある。

## 手順

### 1. Instagramアカウントを作成する

1. 新しいメールアドレス（このプロジェクト用）でInstagramアカウントを作成する
2. アカウントの種類を「プロフェッショナルアカウント」（ビジネスまたはクリエイター）に切り替える
   （Threads APIでの投稿にはプロフェッショナルアカウントが必要）
3. 表示名・ユーザー名を「Watt & Commons」などプロジェクト名に設定する（実名不要）

### 2. Threadsを有効化する

1. Instagramアプリから「Threads」を開き、同じユーザー名でThreadsプロフィールを作成する

### 3. Meta for Developersでアプリを作成する

1. https://developers.facebook.com/ にアクセスし、（普段使っている）自分のFacebookアカウントでログインする
   （これはアプリの管理者としてのログインであり、Threads側の表示名とは別物）
2. 「アプリを作成」→ ユースケースで「Threads API へのアクセス」相当のものを選択
3. アプリ名・連絡先メールアドレスを入力
4. Account Centerでの電話番号確認を求められたら完了させる

### 4. Threads API のuse caseを追加し、リダイレクトURIを設定する

1. アプリのダッシュボードで「Threads API」のuse caseを追加
2. 「アプリID」「app secret」を控える
   - **注意**: アプリ全体の基本設定（Settings → Basic）にある「App ID」
     「App Secret」とは**別に**、Threads APIのuse case配下に専用の
     「Threads App ID」「Threads app secret」が表示される。OAuth認可
     （`threads.net/oauth/authorize`）にはこちらの**Threads専用の値**を
     使う。基本設定側のIDを使うと `error_code=4476002`
     （アプリIDが送信されませんでした）になる。
3. OAuthのリダイレクトURI（Valid OAuth Redirect URIs）を設定する
   - `https://localhost/` のようなダミーURLは**使えない**
     （「無効なドメインが含まれます」で保存できない）。実在する
     HTTPSドメインを指定する必要がある。このプロジェクトでは既存の
     GitHub Pages（`https://watt-n-commons.github.io/note-draft-tool/`）を
     流用した。ページ自体がcodeを処理する必要はなく、リダイレクト後の
     アドレスバーから `code=` を読み取れればよい。
   - リダイレクトURIに使うドメインは、先に基本設定（Settings → Basic）の
     「アプリドメイン（App Domains）」にも追加して保存しておかないと、
     Threads API設定側の保存時に無関係な項目（Delete Callback URL等）にまで
     「無効なドメインが含まれます」エラーが出て保存できない。

### 5. 投稿用アカウントをテスターとして追加する

1. アプリの「Threadsテスター」設定で、手順1で作ったThreadsアカウントのユーザー名を追加
2. Threads側（そのアカウントでログインした状態）で招待を承認する
   （設定 → アカウント → アプリとウェブサイト、あたりから招待が確認できる）

### 6. `.env` に値を設定する

```
NOTE_USERNAME=watt_n_commons
THREADS_APP_ID=（手順4で控えたアプリID）
THREADS_APP_SECRET=（手順4で控えたapp secret）
THREADS_REDIRECT_URI=（手順4で設定したリダイレクトURI）
```

### 7. 初回トークンを取得する

`threads_auth_init.py`（ブラウザでの認可 → `code=` 貼り付け）を用意しているが、
実際には以下の**ダッシュボードから直接トークンを発行する方法の方が簡単**で、
リダイレクトURIの問題を一切気にしなくてよい。

1. アプリのダッシュボードで「Threadsテスター」（テスター一覧）を開く
2. 承認済みの投稿用アカウントの行にある「トークンを生成」的なボタンを押す
3. 表示されたトークン（`THAA...` で始まる）をコピーする
4. これは通常の短期トークンとは異なり、`th_exchange_token`（長期トークン交換）
   には使えないが、**そのままAPI呼び出しに使え、`th_refresh_token`
   （`threads_refresh_token.py` と同じ更新エンドポイント）で約60日の
   有効期限に更新できる**。つまり実質的に長期トークンとして扱ってよい。
5. 一度 `th_refresh_token` を通した値と、`GET /me` で取得したユーザーIDを
   `.env` に保存する（`THREADS_ACCESS_TOKEN` / `THREADS_USER_ID` /
   `THREADS_TOKEN_ISSUED_AT`）

`threads_auth_init.py` によるOAuthフローは、ダッシュボードにテスター用の
トークン発行ボタンが見当たらない場合のフォールバックとして残してある。

### 8. 自動更新をcronに登録する

`THREADS_TOKEN_ISSUED_AT` から45日経過すると、`threads_refresh_token.py` が
自動でトークンを更新する。crontabへの登録はセットアップ時に一度だけ行う
（`crontab -e` で以下のような行を追加。実行間隔は毎日で十分）。

```
0 6 * * * cd /home/yusukekitashiba/note-draft-tool && /usr/bin/python3 threads_refresh_token.py >> threads_refresh.log 2>&1
```

**注意**: 60日を過ぎて一度でも失効すると自動更新はできなくなり、
`threads_auth_init.py` によるブラウザ経由の再認可（手順7のやり直し）が必要になる。
このマシン（ChromeOSのLinuxコンテナ）が長期間起動しない場合は、この前提が崩れる。

## 使い方（記事公開のたび）

1. `note_draft.py` で下書きを保存する（今まで通り）
2. note.comのエディタで**手動で「公開」を押す**
3. 公開されたことを確認してから、以下を実行する

```bash
python3 announce_threads.py drafts/2026-08-09_connect-and-manage.md \
    --comment "系統の混雑対策、英・愛・日を比較しました"
```

同じ記事（frontmatterの`note_id`が同じ）への二重投稿は自動でブロックされる。
再投稿したい場合のみ `--force` を付ける。

## 詰まった点まとめ（2026-08-10のセットアップで発生）

- OAuth認可URLの `client_id` に基本設定の「App ID」を使うと
  `error_code=4476002`（アプリIDが送信されませんでした）になる。
  → Threads API use case配下の「Threads App ID」を使う（手順4参照）。
- リダイレクトURIに `https://localhost/` は使えない。
  → 実在するHTTPSドメイン（このプロジェクトではGitHub Pages）を使う。
- リダイレクトURIのドメインを先にアプリドメイン（基本設定）へ追加しておかないと、
  Threads API設定の保存時に無関係な項目でエラーになり保存できない。
- そもそもOAuthのリダイレクトフローを使わなくても、「Threadsテスター」画面から
  直接トークンを発行できる。こちらの方が圧倒的に簡単（手順7参照）。

## 出典

- Meta for Developers / Threads API ドキュメント（開発者ダッシュボード上の案内）
- [postproxy.dev: Post to Threads via API](https://postproxy.dev/blog/how-to-post-to-threads-via-api/)
- [singhamandeep.com: Threads API App Review](https://singhamandeep.com/threads-api-app-review-permissions/)
- [picklog.cc: Threads API Token Refresh](https://picklog.cc/blog/threads-api-token-refresh)
- [solezore.co.jp: Threadsアカウント作成](https://solezore.co.jp/blog/threads-create-account/)
