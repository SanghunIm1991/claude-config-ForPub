---
name: git-history-rewrite
description: 過去のGitコミット履歴から、セキュリティ上・権利上の理由で残したくない情報（秘密情報・個人情報・PCの利用内容など個人を推測させる記述・第三者の著作物等）を取り除く、またはコミットのauthor・committerを修正する（例: 旧規約でauthor=ClaudeCodeにしていたコミットを本人名義に直し、GitHubの貢献に反映させる）ための手順を定める汎用スキル。プロジェクトを問わず適用する。履歴の書き換え・force pushはgit-conventionsスキルの禁止操作のため、本スキルでは**実行はユーザー自身が行い、Claudeは調査・フルバックアップ・書き換え用ファイルの作成・実行前後の検証・手順案内を担当する**という役割分担をとる。ツールはgit filter-repo（anacondaを使わない専用の仮想環境、導入手順・置き場所も本スキルで管理）。ユーザーが「過去のコミットから〇〇を消したい」「過去のファイルの版から〇〇を消したい」「コミット履歴を修正したい」「authorを自分に直したい」「GitHubの貢献に反映させたい」「秘密情報をコミットしてしまった」「履歴を書き換える前にバックアップを取りたい」「git filter-repoを使いたい」などと言ったときに使う。これから作るコミットの規約（author・接頭辞）はgit-conventionsスキルの管轄で、本スキルは扱わない。
---

# Git履歴の修正（ユーザー実行・Claude支援）

## 基本方針

- 履歴を書き換えるコマンド（`git filter-repo`・`git filter-branch`・`git rebase`・`git commit --amend`等）と`git push --force`は、**Claudeは実行しない**（git-conventionsスキルの禁止操作）。`git filter-repo`はdenyリストにも登録されており、`--version`でさえ拒否される。
- ユーザーはプロンプトの先頭に`!`を付けて実行する。結果は会話に残るので、Claudeはそれを見て検証する。
- **`!`のコマンドが動くシェルは、セッションの既定のシェルによって異なる**（Git BashのこともPowerShellのこともある）。環境の情報（`Shell:`）で既定のシェルを確認し、それに合わせた形でコマンドを提示する。PowerShellの形（`D:\...`のパス、`& "..."`）はGit Bashでは動かず、Git Bashの形（`/d/...`のパス、`$(...)`）はPowerShellでは動かないため、どちらか分からないまま提示しない（分からなければユーザーに確認する）。
  - **Git Bashの場合**: bash形式で書く（パスは`/d/...`形式、環境変数は`$LOCALAPPDATA`。Windowsの実行ファイルに渡すパスはGit Bashが自動でWindows形式に変換する）
  - **PowerShellの場合**: `git`に渡すパスはWindows形式（`D:\...`）で書く。`/d/...`はWindows形式に変換されず、`fatal: repository '/d/...' does not exist`になる（2026-09-25に発生）。`$(...)`・`grep`・`mv`・`cp -r`などのbashの書き方が必要な手順（書き換えの実行、`.git`の入れ替え）は、Git Bashを**フルパス**で呼ぶ（`& "C:\Program Files\Git\bin\bash.exe" <スクリプト>`や`-c '<コマンド>'`）。`bash`とだけ書くとWSLのbashが起動することがある。また、Windows PowerShell 5.1はネイティブのコマンドに渡す引数の中の`"`を正しく渡さないため、コールバックを引数に直接展開しない（スクリプトにまとめる。手順5参照）
- settings.jsonのdeny設定や規約を一時的に外す運用、権限を持つサブエージェントを作る運用はとらない（denyと規約はサブエージェントにも適用される）。
- Claudeが担当するのは次のとおり。
  - 読み取り専用の調査
  - フルバックアップの作成（非破壊。保存先はプロジェクト外のため、実行前に承認を得る）
  - 書き換え用の指示ファイルの作成
  - ユーザーが実行するコマンドの提示
  - 実行前後の検証
  - 記録
- 各段階で「目的」と「セキュリティへの影響」を日本語で説明してから進める。判断に迷う点（消す範囲、置き換え後の文字列、公開済みかどうか等）はユーザーに確認する。
- 本スキルによる作業の経緯は、プロジェクトの`docs/qa_log.md`（あれば）に記録する（`qa-log`スキル参照）。消した情報そのもの（旧メールアドレス、消した文言等）は、記録にも会話にも繰り返し書かない。調査結果は件数・ファイル名・コミットIDで伝える。

## 全体の流れ

| 手順 | 担当 | 内容 |
|---|---|---|
| 0 | Claude→ユーザー | ツールの準備（導入済みか確認、未導入なら案内） |
| 1 | Claude→ユーザー | 目的と前提の確認 |
| 2 | Claude | 事前調査（読み取りのみ） |
| 3 | Claude | フルバックアップ（リポジトリ外） |
| 4 | Claude | 書き換え用の指示ファイルの作成（バックアップと同じフォルダ） |
| 5 | ユーザー | 作業用クローンの作成と書き換えの実行 |
| 6 | Claude | 検証（読み取りのみ） |
| 7 | ユーザー（＋Claudeの確認） | 反映（`.git`の入れ替え、push済みならリポジトリの作り直しまたはforce push） |
| 8 | ユーザー | 問題があった場合の復元 |
| 9 | ユーザー（＋Claudeの記録） | 後片付け |

コマンドの具体例は`references/commands.md`、指示ファイルのひな形は`references/templates/`にある。

## 手順0: ツールの準備（git filter-repo）

ツール本体はプロジェクトの外、ユーザー用のフォルダに置く（管理者権限が不要）。本節がこのツールの管理記録を兼ねる。

- 置き場所: `%LOCALAPPDATA%\Programs\git-filter-repo`（専用の仮想環境）
- 使うPython: `py -3.9`（Visual Studio付属）。anacondaのPython（`C:\ProgramData\anaconda3\python.exe`）とbase環境は使わない
- `~/.claude`配下には置かない（Claudeが日常的に編集する場所に履歴書き換えツールを置かないため、また同期対象になり得るため）
- 導入・再導入・削除はユーザーが行う。Claudeは手順の提示と、実行ファイルの有無の確認（読み取りのみ）だけを行う

**毎回の確認**: Claudeは`Test-Path "$env:LOCALAPPDATA\Programs\git-filter-repo\Scripts\git-filter-repo.exe"`で有無だけを確認する。バージョン確認はユーザーが`! "$LOCALAPPDATA/Programs/git-filter-repo/Scripts/git-filter-repo.exe" --version`で行う（バージョン番号ではなく`a40bce548d2c`のような識別子が表示されれば正常）。

**導入手順（ユーザーが`!`付きで1行ずつ実行）**

```bash
py -0p                                                                  # 一覧に 3.9 があることを確認
py -3.9 -m venv "$LOCALAPPDATA/Programs/git-filter-repo"                 # 専用の仮想環境を作る（出力なしで成功）
"$LOCALAPPDATA/Programs/git-filter-repo/Scripts/python.exe" -m pip install git-filter-repo   # PyPIから導入
"$LOCALAPPDATA/Programs/git-filter-repo/Scripts/git-filter-repo.exe" --version               # 動作確認
```

- 2行目を飛ばすと3行目が「No such file or directory」になる。順番どおりに実行する。
- pipの更新を勧める警告は無視してよい。
- 3行目が失敗する場合は、対応するPythonのバージョンを公式ページ（https://github.com/newren/git-filter-repo ）で確認する。
- Visual Studioの更新等でPython 3.9が入れ替わると、仮想環境が動かなくなることがある。その場合はフォルダを削除して2行目から入れ直す。
- （任意）どこからでも`git filter-repo`と打てるようにするには、ユーザー環境変数PATHに`%LOCALAPPDATA%\Programs\git-filter-repo\Scripts`を追加する（ターミナルの開き直しが必要。Claude Codeのセッションには反映されないため、本スキルではフルパスで実行する）。

**削除（不要になったとき、ユーザーが実行）**: フォルダ`%LOCALAPPDATA%\Programs\git-filter-repo`を削除する。PATHに追加していれば、環境変数の設定画面からその行も取り除く。

## 手順1: 目的と前提の確認（Claude → ユーザー）

次を確認し、作業計画として提示する。

- 対象リポジトリとブランチ（全ブランチ・タグを対象にするのが原則）
- 修正の種類:
  - (a) ファイルを全履歴から削除する
  - (b) 文字列を全履歴のファイル内容で置き換える（過去の版にだけ残っている記述を消す場合もこれ）
  - (c) コミットメッセージを修正する
  - (d) author・committerを修正する
- リモートへpush済みか。済みなら、共同作業者・フォーク・Pull Requestの有無。**未pushなら、初回push前に修正するのが最も確実**（GitHub側のキャッシュ等の問題が生じない）
- 秘密情報（APIキー・パスワード・トークン等）が含まれる場合: **履歴から消しても、すでに漏れた可能性は消えない**。先にユーザーがキーの無効化・再発行を行う（最優先）
- (d)の場合の新しいメールアドレス: GitHubの貢献に反映させるには、GitHubアカウントに紐づくアドレスであること。推奨はnoreplyアドレス（`<ID>+<ユーザー名>@users.noreply.github.com`、GitHubのSettings→Emailsで確認できる）。今後のコミットで個人メールが記録されないよう、`git config --global user.email`もnoreplyにしておく（ユーザーが設定。git-conventionsスキル参照）
- Claudeの関与を残すかどうか（`Co-Authored-By: Claude <noreply@anthropic.com>`トレーラーを付ける）

## 手順2: 事前調査（Claude、読み取り専用）

修正対象が履歴のどこにあるかを洗い出し、件数を記録する（手順6の検証の基準になる）。具体的なコマンドは`references/commands.md`の「調査」節。

- author / committerの組み合わせと件数（メールアドレスはマスクして表示する）
- 消したい文字列を含むファイルの版の数、および**表記の揺れ（言い回しの違い）をすべて洗い出す**。1つの表現だけを置き換えると、別の言い回しが残る
- 現在のファイルにも残っていないか（記録文書の中で旧記述を「引用」している場合がある。見つけたら先に現在のファイルを直してコミットする）
- 消したい情報以外の個人情報（ユーザー名入りのパス、実メールアドレス等）が履歴に無いか
- コミットメッセージの検索
- 過去にだけ存在したファイル（今は削除済み）の一覧
- 日本語を含む検索は`LC_ALL=C.UTF-8`と`git grep -P`を使う（既定のロケールでは`sort`等がマルチバイト文字で失敗する）

## 手順3: フルバックアップ（Claudeが作成、保存先はユーザーが承認）

書き換え前の状態に確実に戻せるようにする。保存先は次の条件を満たす場所をユーザーと決める（例: `<バックアップ先>\<リポジトリ名>-<日付>\`）。

- リポジトリの**外**。リポジトリ内に置くと次の問題がある:
  - `.gitignore`の書き間違いや`git add -f`で、消したい情報ごとコミットしてしまう危険
  - フォルダの入れ替え時や`git clean -fdx`で一緒に消える危険
  - zipが作成中の自分自身を含んでしまう
  - 検索で旧情報が出続ける
- OneDrive等の**クラウド同期フォルダではない**場所（バックアップには消したい情報がそのまま入っている）

作成するもの（コマンドは`references/commands.md`の「バックアップ」節。PowerShellで実行する）:

1. `git bundle create ... --all`で全ブランチ・全タグの全履歴を1ファイルにし、`git bundle verify`で検証する
2. フォルダ一式（`.git`、未追跡ファイル、`.gitignore`対象を含む）のzip。**Windows標準の`C:\Windows\System32\tar.exe`をフルパスで使う**（Git Bashの`tar`はGNU tarでzipを作れない）。zip内の項目数が実際のファイル・フォルダ数と一致すること、`.git/HEAD`が含まれることを確認する
3. 上記のSHA256ハッシュ値を`SHA256SUMS.txt`に保存する
4. push済みの場合は`git clone --mirror`でリモート側の状態も控える
5. **復元テスト**: bundleから一時フォルダへcloneし、HEAD・コミット数が一致し`git fsck --full`がエラーなしであることを確認して、一時フォルダを削除する

作業前に`git status`がクリーンであること（未コミットの変更がないこと）を確認する。バックアップの作成と検証が済むまで、次の手順に進まない。

## 手順4: 書き換え用の指示ファイルの作成（Claude）

ひな形は`references/templates/`にある。**指示ファイルにも消したい情報が入るため、リポジトリの外（バックアップと同じフォルダ）に置く。**

- **文字列の置換（`replace-text.txt`）**: 1行に1件、`消したい文字列==>置き換える文字列`。`regex:`で正規表現も使える。置き換え後の文字列を省略すると`***REMOVED***`になる
  - 現在のファイルですでに中立化済みの記述なら、**置き換え後の文字列を現在の表現と完全に同じにする**。こうすると最新の版は書き換え前と1バイトも変わらず、検証（ツリーのハッシュ値の一致）が簡単になる
  - 手順2で見つけた表記の揺れをすべて行として並べる。長い、文脈を含む文字列にすると、意図しない箇所を置き換えにくい
  - **UTF-8（BOMなし）**で保存する
- **author・committerの修正とトレーラーの追加（`commit-callback.py`）**: mailmapとコールバックの適用順に依存しないよう、名義の変更とトレーラーの追加を1つのコールバックで行う。トレーラーが既にあるコミットには追加しない
- コミットメッセージの置換（`--replace-message`、書式は`replace-text.txt`と同じ）、ファイルの削除（`--path <パス> --invert-paths`）も必要に応じて使う
- 作成したら、各行が手順2の件数どおりに該当することを確認する（Claudeによる事前チェック）

## 手順5: 書き換えの実行（ユーザー）

`git filter-repo`は既定で「新しくcloneしたリポジトリ」でしか動かない（誤操作防止）。Claudeは次の2行を完成形で提示し、ユーザーが`!`付きで順に実行する。

```bash
# 1. 作業用クローンを作る（元のフォルダ・バックアップには触れない）
git clone --no-local /d/<元のリポジトリ> /d/<元のリポジトリ>-rewrite

# 2. クローンの中で書き換える
cd /d/<元のリポジトリ>-rewrite && "$LOCALAPPDATA/Programs/git-filter-repo/Scripts/git-filter-repo.exe" --replace-text <バックアップ先>/<名前>/replace-text.txt --commit-callback "$(grep -v '^#' <バックアップ先>/<名前>/commit-callback.py)"
```

- `--commit-callback`には、コールバックの**コメント行を除いて**渡す（`grep -v '^#'`）。日本語のコメントがコマンドライン経由で文字化けし、エラーになるのを防ぐため。コールバック本体には日本語を書かない
- 正常時の出力: `NOTICE: Removing 'origin' remote`（仕様。手順7で必要なら戻す）、`Parsed N commits`、`HEAD is now at ...`、`Completely finished after ...`

**`!`がPowerShellで動く場合**: 2行目をスクリプト（`run-rewrite.sh`、ひな形は`references/templates/`。バックアップと同じフォルダに置き、改行コードはLF）にまとめ、Git Bashをフルパスで呼ぶ。Claudeは作成後に`grep -c $'\r'`（0であること）と`bash -n`（構文）で確認する。

```powershell
! git clone --no-local D:\<元のリポジトリ> D:\<元のリポジトリ>-rewrite
! & "C:\Program Files\Git\bin\bash.exe" <バックアップ先>/<名前>/run-rewrite.sh
```

## 手順6: 検証（Claude、読み取り専用）

作業用クローンで次を確認し、結果を表で報告する。コマンドは`references/commands.md`の「検証」節。問題があれば作業用クローンを破棄してやり直す（元のリポジトリとバックアップは無傷）。

- 手順2で数えた対象（文字列・古いauthor/committer・ファイル）が、全履歴で**0件**になった
- トレーラーを付けた場合、付いていないコミットが0件になった（コミット単位で数える。メッセージの行単位で数えると誤る）
- 最新のツリーのハッシュ値（`git rev-parse HEAD^{tree}`）が、意図した変更以外は元と一致する（置換後の文字列を現在の表現にそろえた場合は完全一致する）
- コミット数: 元より減った場合は、**置換によって変更前後が同じになったコミット（空になったコミット）が自動で取り除かれた**ためであることを、コミットの件名を比較して特定し、ユーザーに説明する
- `git fsck --full`でエラーがない
- ビルド・テスト: ツリーが完全一致なら反映後に1回実行すればよい。一致しない場合は作業用クローンでも実行する

## 手順7: 反映（ユーザー、確認はClaude）

- **ローカル**: Claudeのセッションは元のフォルダを作業フォルダとして使っていることが多く、フォルダごとの入れ替えはできない。**`.git`フォルダだけを入れ替える**（ビルド成果物や`.gitignore`対象のファイルも残る）。ユーザーが`!`付きで実行する。

  ```bash
  mv /d/<元のリポジトリ>/.git <バックアップ先>/<名前>/original.git
  cp -r /d/<元のリポジトリ>-rewrite/.git /d/<元のリポジトリ>/.git
  ```

  - `!`がPowerShellで動く場合は、各行を`! & "C:\Program Files\Git\bin\bash.exe" -c '<上の1行>'`の形で実行する（PowerShellの`Copy-Item`は隠しファイルの扱いに不安があるため使わない）
  - 入れ替え後の`.git/config`には`origin`と上流ブランチの設定が無い（`git filter-repo`の仕様）。元の`.git/config`（`original.git/config`）にあった他のリポジトリ単位の設定（`user.email`等）が無くなっていないか、Claudeが比較して確認する。`.git/info/exclude`と独自のフック（`.git/hooks`の`*.sample`以外）も、新しい`.git`では消えるため、`original.git`と比べて確認する（戻す必要があればユーザーに伝える）
  - 1行目で「使用中」のエラーが出たら、そのフォルダを開いているエディタ等を閉じてやり直す。途中で失敗しても、退避した`original.git`を戻せば復旧できる
  - 入れ替え直後は、インデックスに記録されたファイルのサイズ・日時が作業フォルダと合わず、`git status`で多数のファイルが「変更あり」と表示される（特に`core.autocrlf=true`の環境）。Claudeが`git diff`で内容の差分が無いことを確かめ、`git update-index --refresh`でインデックスを更新して`git status`がクリーンになることを確認する（`git add -A`は、未追跡で`.gitignore`対象でないファイルまでステージしてしまうため使わない）。内容・履歴は変わらない
  - その後、Claudeがログ・名義・`git fsck`を確認し、ビルド・テストを実行する
- **push済みの場合**: **force pushだけでは、古いコミットがGitHubに残る**。ブランチから外れても、コミットIDを直接指定すれば参照できる（2026-09-25、あるプロジェクトで、force push後に`gh api repos/<owner>/<repo>/commits/<旧HEADのID>`が中身を返すことを確認）。そこで、**pushの前に反映の方法を決める**。まずClaudeが`gh`で読み取り、公開範囲と、Issue・Pull Request・フォーク・共同作業者・Webhook・Deploy keys・Actionsのsecrets・ブランチ保護・Pages・説明文・topicsの有無を確認して、作り直すと失うものを伝える。`git filter-repo`は`origin`の設定を外すため、どちらの方法でも、ユーザーが`git remote add origin <URL>`で戻してからpushする。
  - **A. リポジトリの作り直し（未公開〈private〉で、失うものが無い場合に推奨）**: ユーザーがWeb画面でGitHubのリポジトリを削除し、同名で作り直す（README等は追加しない）。その後、通常の`git push -u origin <ブランチ>`（タグがあれば`git push --tags`）でpushする。force pushは不要。作り直した後、Claudeは作成日時（`created_at`）が新しくなったこと、旧HEADのIDが`No commit found`（HTTP 422）になることを確認する。なお、削除したリポジトリは所有者が一定期間（通常90日）復元できるため、その間はGitHub側に旧履歴が残る（参照できるのは所有者だけ）。誤って復元しないよう、記録（QA表等）に残す
  - **B. force push（公開済み、Issue等を残したい場合）**: ユーザーが`git push --force --all`と`git push --force --tags`を実行し、GitHubサポートへ古いデータの削除を依頼する（GitHub Docs「Removing sensitive data from a repository」）
  - どちらの場合も、フォーク・他人のクローンからは消せない
  - 共同作業者には、古いクローンを使わず取り直すよう連絡する（古い履歴を再pushされると戻ってしまう）
  - 自分の別環境（WSL・別PC）のクローンも同様に取り直す。Gitの管理外のファイル（メモ・練習用のフォルダ等）が入っていることがあるため、いきなり削除せず、名前を変えて退避し→cloneし直し→管理外のファイルを移し→退避したものを削除する。
    - 退避する前に、`git fetch`をせずに`git merge-base --is-ancestor main <書き換え前のHEAD>`を実行して、そのクローンにしか無いコミットが無いことを確かめる。結果は3通りある: `未pushのコミットなし`と表示される（問題なし）／何も表示されずに終わる（そのクローンにしか無いコミットがある。退避する前にユーザーと扱いを相談する）／`fatal: Not a valid commit name`と表示される（そのクローンが遅れていて書き換え前のHEADを持っていない。代わりに、fetchせずに`git log --oneline origin/main..main`が空であることで確かめる）。main以外のローカルブランチ（`git branch`）とstash（`git stash list`）も確認する
    - cloneし直したクローンには、リポジトリ単位のgit設定（`user.email`等）が引き継がれない。退避したクローンと`git config --local --list`を比べ、必要な設定をユーザーが設定し直す（2026-09-25、あるプロジェクトで、WSLのクローンの`user.email`が未設定になった）
    - 退避したクローン（`.old`）には古い履歴が残るため、手順9の削除の対象に含める
- コミットIDがすべて変わるため、Issue・Pull Request・ドキュメント等に書かれたコミットIDへの参照は切れる。

## 手順8: 復元方法（問題があった場合、ユーザー）

- `.git`の入れ替え直後なら: 入れ替えた`.git`を削除し、`original.git`を元の場所に戻す
- bundleから: `git clone <バックアップ先>/<名前>/<元のリポジトリ>.bundle <復元先>`
- zipから: `C:\Windows\System32\tar.exe -x -f <zip> -C <展開先>`
- リモートを元に戻す場合: 復元したリポジトリ（またはミラー）から`git push --force --all`・`--tags`（手順7のAで作り直した後なら、作り直したリポジトリへのpushになる）。**消したい情報を含む旧履歴がリモートに戻る**ため、Claudeは実行前に目的（本当に旧履歴に戻す必要があるか、書き換えのやり直しで足りないか）をユーザーに確認する

## 手順9: 後片付け

- 反映後、しばらく使って問題が無いこと（公開済みならGitHub上の履歴・貢献グラフ）を確認してから、次を削除する（ユーザーが判断・実行。ごみ箱も空にする）:
  - 作業用クローン（`<元のリポジトリ>-rewrite`）
  - バックアップフォルダ（bundle・zip・`original.git`・指示ファイル。消したい情報が入っている）
  - 別環境で退避した古いクローン（`<クローン>.old`）
- git-filter-repoは他のリポジトリでも使えるため、残すか削除するかはユーザーが決める（削除方法は手順0）。
- 経緯を`docs/qa_log.md`に記録する（消した情報の内容そのものは書かない）。
- 未公開のリポジトリを公開する場合は、書き換え後の最新コミットまでpush前スキャンをやり直してから、pushの承認を得る。

## 実施例

- 2026-09-23 あるプロジェクト（公開前に実施）: 旧規約で作った95コミットをnoreplyアドレス名義に直し、Co-Authored-Byを84件に追加。3ファイルの過去の版に残っていた、残したくない記述（4通りの言い回し）を全履歴で中立化。最新ツリーは完全一致、99→98コミット（中立化コミットが空になり除去）、全テスト成功。
- 2026-09-25 別のプロジェクト（push済みで実施）: 旧規約で作った80コミットの名義をnoreplyアドレスに直し、Co-Authored-Byを2件に追加。`docs/qa_log.md`の過去の15版に残っていた残したくない記述を、現在の表現と同じ文字列に置換（最新ツリーは完全一致、80→80コミット）。`!`がPowerShellで動く環境だったため、書き換えはスクリプト＋Git Bashのフルパス呼び出しで実行。force push後も旧コミットがGitHubで参照できたため、リポジトリを作り直してpushし直した（この経験から、手順7で反映の方法をpushの前に決める順に改めた）。WSL内のクローンも退避・再cloneしたが、リポジトリ単位の`user.email`が消えたため設定し直した。
