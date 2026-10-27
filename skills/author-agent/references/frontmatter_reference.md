# frontmatterスキーマ詳細

サブエージェント定義ファイル（`.claude/agents/*.md` / `~/.claude/agents/*.md`）の先頭に置くYAML frontmatterの各項目。

出典: Claude Code 公式ドキュメント（サブエージェントの節）を要約・再構成したもの。逐語の転載ではない。

## 必須項目

| フィールド | 説明 |
|---|---|
| `name` | エージェントのID。小文字英数字とハイフンのみ。**コロンは使用不可**（`plugin:subagent`のようなプラグインスコープID用に予約されている） |
| `description` | オーケストレーター（メイン会話）がこのエージェントへ自動委任するかどうかを判断するために読む文言。書き方の詳細は`description_and_prompt_writing.md` |

`name`または`description`を欠くファイル、YAMLとして不正なファイルは**エラーにならず黙ってスキップされる**。存在するはずのagentが一覧に出ない場合はまずここを疑う。

## 省略可能項目

| フィールド | 値 | 意味・デフォルト |
|---|---|---|
| `model` | `sonnet` / `opus` / `haiku` / `fable` / フルモデルID / `inherit` | 省略時は`inherit`（呼び出し元セッションのモデルを継承） |
| `tools` | カンマ区切りのツール名リスト | allowlist。指定すると**このリストのみ**使用可能になる。省略時は全ツールを継承 |
| `disallowedTools` | カンマ区切りのツール名リスト | denylist。継承した全ツールからここに挙げたものを除外する。`tools`と併用しないのが基本（allowlistとdenylistを両方使うと意図が読みにくくなる） |
| `permissionMode` | `default` / `acceptEdits` / `auto` / `dontAsk` / `bypassPermissions` / `plan` | 省略時はセッションの設定に従う。`bypassPermissions`は承認プロンプトを一切出さずに実行するため、ユーザーの明示的合意がある場合のみ設定する |
| `skills` | カンマ区切りのSkill名リスト | 使用可能なSkillを限定したい場合に指定 |
| `mcpServers` | カンマ区切りのMCPサーバー名 | 特定のMCPサーバーのみ使わせたい場合。ツール単位で絞る場合は`tools`側に`mcp__server_name`または`mcp__server_name__tool_name`の形式で書く |
| `hooks` | PreToolUse/PostToolUse/Stop等のマッピング | エージェント固有のフックを定義する場合 |
| `memory` | `user` / `project` / `local` | このエージェントが参照するメモリのスコープ |
| `maxTurns` | 整数 | ターン数の上限 |
| `isolation` | `worktree` | gitワークツリーを隔離して作業させる場合 |
| `background` | 真偽値 | バックグラウンド実行を既定にする場合 |
| `effort` | 文字列 | セッションのreasoning effortを上書きする場合 |
| `color` | 文字列 | タスク一覧・UI上での表示色 |
| `initialPrompt` | 文字列 | メインエージェントとして起動された際に自動投入されるプロンプト |

## 保存場所と優先順位

1. `<project>/.claude/agents/`（プロジェクトレベル、最優先）— バージョン管理でチーム共有
2. `~/.claude/agents/`（ユーザーレベル）— このマシン全体・全プロジェクトで使う個人用
3. プラグインの`agents/`ディレクトリ（最も優先度低）

同名エージェントが複数スコープに存在する場合、ファイルシステム順で解決される（どちらが勝つか保証されないため、意図的に上書きしたい場合以外は同名を避ける）。

## プラグイン提供エージェントの制約

プラグインの`agents/`ディレクトリで配布するエージェントは、`hooks`・`mcpServers`・`permissionMode`をサポートしない。これらの制御が必要なエージェントはプロジェクトまたはユーザーレベルで定義する。

## その他の制約

- サブエージェントの入れ子は既定で3階層まで（環境変数`CLAUDE_CODE_MAX_SUBAGENT_SPAWN_DEPTH`で変更可能）
- 同時実行できるサブエージェントは既定で20まで（環境変数`CLAUDE_CODE_MAX_CONCURRENT_SUBAGENTS`で変更可能）
- 子エージェントとして呼び出せるサブエージェントの種類自体を絞り込みたい場合、`tools`に`Agent(worker, researcher)`のように許可するsubagent_typeを指定する書き方がある
