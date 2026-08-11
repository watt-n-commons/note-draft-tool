# Obsidian Vault

コンサル業務(consulting)とDC/エネルギー事業(venture)を統合した個人ナレッジベース。PARA方式ベース。
詳細仕様はセットアップ時に渡された「Obsidian Vault 構築仕様」を参照。ここでは運用者向けの要点のみ再掲する。

## フォルダ構成

- `00_inbox/` — 未整理の一時置き場。週次レビューで振り分ける。
- `01_projects/consulting/<client>/` — 稼働中のコンサル案件(クライアント別)
- `01_projects/venture/<project>/` — 稼働中の事業(プロジェクト別)
- `02_areas/` — 継続的に管理する領域(consulting-ops / venture-ops)
- `03_resources/` — 参照資料。`insights/` は案件から抽象化した学びの置き場
- `04_archives/consulting/` — 取引終了クライアントの移動先
- `_templates/` — Templater用テンプレート

## 機密情報の運用ルール(最重要)

- **総務省案件はVaultに一切含めない**。進捗管理は別手段(カレンダー等)で行う。
- `01_projects/consulting/` 配下の案件ノートに**書かない**: 具体的な数値・分析結果、クライアント内部資料の中身、契約金額・機密条項、固有名詞を含む詳細
- 案件ノートに**書いてよい**もの: ステータス・進捗、次のアクション、一般化した手法・アプローチ
- 再利用価値のある学びは、クライアント名等を削除して抽象化した上で `03_resources/insights/` に別ノートとして起こす(案件ノートから直接リンクしない)

## プラグイン(Community Plugins から手動インストール)

いずれもObsidianの「設定 → コミュニティプラグイン → 閲覧」から検索してインストール・有効化する(PC/モバイル共通で操作可能)。

| プラグイン | 用途 |
|---|---|
| Dataview | ダッシュボード(`Home.md`)のクエリ実行 |
| Templater | `_templates/` のテンプレート展開 |
| QuickAdd | テンプレート起動のショートカット化 |
| Calendar / Periodic Notes | デイリーノート運用 |
| Obsidian Git (PC/Chromebookのみ) | git自動コミット・同期。モバイルでは不安定なため使わない |

モバイルの同期は `Obsidian Git` ではなく、GitHub API経由で動作する `Hybrid Git Sync` または `Git Sync` 系プラグインを別途検討する。Obsidian Syncとの併用は不可。

### Templaterの設定

- 「テンプレートフォルダの場所」を `_templates` に設定
- 各テンプレートは `domain`/`client` などのfrontmatterをTemplater変数で自動入力する(`_templates/project.md` 参照)

## Git同期

- プライベートGitHubリポジトリでVaultを管理する
- PC/Chromebook: Obsidian Git、Auto Commit and Sync を有効化
- スマホ: API経由プラグインでこのリポジトリに接続

## 案件の追加・終了

- 新規案件: `_templates/project.md` から作成し、該当ドメインのフォルダに配置
- 取引終了クライアント: `01_projects/consulting/<client>/` フォルダごと `04_archives/consulting/` へ移動
