# claude-config

個人で利用している [Claude Code](https://claude.com/claude-code) の設定一式を管理するリポジトリです。自分用の運用ルール・スキルを整理・再利用する目的で管理しており、外部からの利用や貢献は想定していません。内容は個人の作業スタイルに合わせたものなので、そのまま他の環境で使えることは保証しません。

## 含まれているもの

- `CLAUDE.md` — 全プロジェクト共通のグローバル指示（このPC固有の環境事情、Python複数バージョンの扱いなど）
- `skills/` — プロジェクトを問わず使う再利用可能なスキル
  - `git-conventions` — Claude Codeによるコミット規約・禁止Git操作を定めた汎用ルール
  - `git-history-rewrite` — 過去の履歴から残したくない情報を取り除く・コミットの名義を直す手順（書き換えはユーザーが実行し、Claudeは調査・バックアップ・検証を担当）
  - `public-release-review` — リポジトリを公開する前の点検と事前対応（今の版と全履歴の機密情報・権利・リンクの点検、判断の確認、独立したレビュー、公開の案内）
  - `qa-log` — ユーザーへの確認と判断の経緯を、プロジェクトのQA表に記録するルール
  - `test-strategy` — テストレベル（単体/結合/統合）・由来管理・リグレッション方針などのテスト戦略
  - `waterfall-dev-workflow` — ウォーターフォール型開発（要件定義〜デプロイ）を工程ゲート承認・トレーサビリティマトリックス付きで進めるためのワークフロー
  - `reverse-engineering` — 既存のシステムを、構造分析→意味分析→セキュリティ解析の順で解析する方法論
  - `resume-after-interruption` — セッションが異常終了した後に、状況を整理して作業を再開する手順
  - `start-idea-project` — アイデアを別プロジェクトで実現し始めるときの初回セットアップ手順
  - `author-agent` — サブエージェント定義の作成・レビューの手順（名前・目的・権限・性格を事前に確認する）
  - `list-agents` — 使えるサブエージェントの一覧を作る
  - `powershell-scripting` — PowerShellとClaude Codeのツールの技術的な罠と対策
  - `markdown-mermaid` — Markdownとmermaidの書き方（図のmermaid/SVGの使い分け）と、表示する環境によって崩れる罠（日本語の文中の数式、mermaidの番号ラベル、VS Codeの拡張機能の競合）と確かめ方
  - `learning-text-authoring` — 他の学習者も1人で読む学習用のテキスト（手順書・教科書）の書き方（教科書の口調、期待する結果、その場で説明する、前方参照）と、サンプルを確かめてから書く方法、SVG図の生成と点検、書いた後の点検
  - `spare-capacity-backlog` — 週次利用枠に余裕がある時に消化する手空きタスクのバックログ運用
  - `readme-overview-figure` — READMEの冒頭に貼る全体像のポンチ絵（概念図）を作る手順（svg-diagramで描くか、Claude Designの案をSVGに移植するか）
- `commands/` — 個人用のカスタムスラッシュコマンド
  - `wrapup` — セッションを閉じる前に変更を整理してコミットする
  - `review-session` — セッション中の作業を独立したサブエージェントにレビューさせる
- `agents/` — 個人用のカスタムサブエージェント定義
  - `session-safety-reviewer` — セッション中の操作を危険性・意図しない変更の観点で静的レビューする（修正・実行は行わない）
  - `waterfall-loop-orchestrator` — ウォーターフォール型開発の自律ループモードで、工程の進行管理とサブエージェント呼び出しを担うオーケストレーター
  - `svg-diagram` — mermaidでは視認性を追い込めない技術図をSVGで作成・修正する（ヘッドレスのブラウザでの描画と、別のサブエージェントによる目視確認を含む）
  - `circuit-diagram` — 電子工作の回路図（SVG・回路記号）の作成と、電圧・電流の計算
  - `embedded-dev` — Arduino等のマイコンのファームウェア開発（PlatformIOでのビルド・書き込み・実機の不具合の切り分け）
  - `design-doc-readability-editor` — 設計書の内容を変えずに、表やmermaidの図で読みやすくする
- `hooks/` — SessionEnd等のイベントで動くカスタムフックスクリプト
  - `log_task.py` — セッション終了時に依頼/成果物の要約・トークン数等を`~/.claude/dev-task-log.jsonl`に1行追記する
  - `require-approval-description.ps1` — Bash・PowerShellのツール呼び出しの説明に「目的・実行内容・危険度」が無ければ差し戻す（PreToolUse）
  - `approval-rule-reminder.ps1` — 毎回のメッセージで、承認を求める操作の説明のルールを文脈に差し込む（UserPromptSubmit）
- `statusline.ps1` — ステータスラインの表示（モデル・effort・コンテキストの使用率・利用枠）。`settings.json`（Git管理外）の`statusLine`から呼ぶ

## 含まれていないもの

各プロジェクト（`projects/*/memory/`）で蓄積される auto memory（作業内容・個別の学習メモ）は、機密情報が混在しうるため意図的にこのリポジトリの管理対象から除外しています（`.gitignore`参照）。

## ライセンス・出典

- このリポジトリにはライセンスを付与していません。公開は閲覧のためのもので、内容の複製・改変・再配布は許可していません（GitHubの利用規約で認められる閲覧・フォークを除く）。
- 第三者の著作物（コード・文書・画像等）の複製は含めていません（公式ドキュメントの要約が1件あり、出典は下記）。外部のツール（git-filter-repo等）や公式の文書（GitHub Docs等）は、リンクや題名で参照しているだけです。
- 出典: `skills/author-agent/references/frontmatter_reference.md` は、Claude Code 公式ドキュメント（サブエージェントの節）を要約・再構成したものです（逐語の転載ではありません）。
- Anthropic 公式のスキルを同期したもの（`skills/synced/`）は、再配布を避けるため管理対象から除外しています。
