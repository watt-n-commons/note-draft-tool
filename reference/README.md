# reference/

`draft_request.txt` は解析済みです（実際のCookie値はファイルから削除し、`.env` にのみ保存）。

判明したこと:
- `draft_request.txt` は **既存の下書き（id指定済み）** への自動保存リクエストだった。
  新規下書きを作るための「作成」APIはこのキャプチャには含まれていなかったため、
  GitHub上の [NoteClient2](https://github.com/Mr-SuperInsane/NoteClient2)（ユーザー許可済みの参考実装）
  のソースを読んで `POST /api/v1/text_notes` (`{"template_key": null}`) が
  新規の下書きの器を作り、レスポンスの `data.id` / `data.key` を返すことを確認した。
- ブロックエディタのHTMLは各ブロック（見出し・段落・リスト項目）に
  一意の `name`/`id`（UUID）が必要。見出しは `h2`（大見出し）/`h3`（小見出し）の2段階のみ。
  リストは `<ul name id><li><p name id>...</p></li></ul>` という入れ子構造。
- draft_save のペイロードに `tags`/`hashtags` に相当するフィールドは
  キャプチャにもNoteClient2にも見当たらなかった（hashtagsは公開時のPUTでのみ登場）。
  そのため現状は **frontmatterのtagsは解析するがAPIには送っていない**（推測で送信しない）。
  タグ付けの実際のAPIを知りたい場合は、ブラウザで既存下書きにタグを追加する操作を行い、
  そのときのNetworkリクエストを新しくキャプチャして教えてください。
- draft_save の成功レスポンスは `{"data":{"result":true,"note_days_count":0,"updated_at":"..."}}`。
  実アカウントでの実行で確認済み（`note_draft.py` は `data.result is True` で成功判定）。
- create_note (`POST /api/v1/text_notes`, `{"template_key": null}`) の成功レスポンスは
  `{"data":{"id":<int>,"key":"<str>","name":null,"body":null,...}}`。これも実アカウントで確認済み。
- `note_gql_auth_token`（GraphQL用JWT）は draft_save のリクエストには**そもそも送られない**
  ことを2回目のキャプチャで確認済み（同一セッションで `_note_session_v5` は同値、
  tokenだけ欠落）。おそらくCookieのPathスコープがGraphQLエンドポイント限定で、
  draft_save/create系は `_note_session_v5` のセッションCookieのみで認証されている。
  401/403のデバッグ時はこちらを疑う。

