# コマンド集（git-history-rewrite）

`<元>`は元のリポジトリのフォルダ名（SKILL.mdの`<元のリポジトリ>`と同じ。例はドライブの直下に置いた形で、PowerShellでは`D:\<元>`、bashでは`/d/<元>`と書く。実際の場所に合わせて置き換える）、`<名前>`はバックアップフォルダ名、`<バックアップ先>`はバックアップフォルダを置く親フォルダ（リポジトリの外。PowerShellでは`X:\...`、bashでは`/x/...`の形で書く）。メールアドレスを表示するコマンドには、個人メールをマスクする`sed`（下の例の`| sed -E '…'`）を必ず付ける（書き換えに漏れがあったとき、実メールが会話に出ないようにするため）。対象のドメインは、調査で見つかった個人メールのドメインが含まれていることを確認する。bash（Git Bash）の例はClaudeのBashツールやユーザーの`!`で、PowerShellの例はClaudeのPowerShellツールで実行する。

## 調査（Claude、読み取りのみ）

```bash
cd /d/<元>
export LC_ALL=C.UTF-8   # 日本語を含む検索・並べ替えの文字化け・失敗を防ぐ

# 総コミット数・ブランチ数・タグ数
git rev-list --all --count; git branch -a | wc -l; git tag | wc -l

# author | committer の組み合わせと件数（個人メールはマスクして表示）
git log --all --format='%an <%ae> | %cn <%ce>' | sed -E 's/([A-Za-z0-9._%+-]{2})[A-Za-z0-9._%+-]*@((gmail|yahoo|outlook|hotmail|live|icloud)\.[A-Za-z.]+)/\1***@\2/g' | sort | uniq -c

# 消したい語を含む「言い回し」を全履歴から洗い出す（表記の揺れを見落とさないため）
git grep -h -o -P ".{0,20}<消したい語>.{0,20}" $(git rev-list --all) | LC_ALL=C sort | LC_ALL=C uniq -c

# 現在のファイルに残っていないか
git grep -n "<消したい語>"

# 個人を特定し得る文字列が履歴のどのファイルにあるか（ファイル名と件数だけ）
git grep -l -i -E "<ユーザー名>|gmail|<実名>" $(git rev-list --all) | sed 's/^[0-9a-f]*://' | LC_ALL=C sort | LC_ALL=C uniq -c

# コミットメッセージの検索
git log --all --oneline --grep='<文字列>'

# 過去にだけ存在したファイル
comm -23 <(git log --all --format= --name-only | sort -u | grep .) <(git ls-files | sort)

# 旧author（例: ClaudeCode）のコミットのうち、Co-Authored-By が無いものの数（コミット単位で数える）
t=0; w=0; for h in $(git rev-list --all --author=noreply@anthropic.com); do t=$((t+1)); git log -1 --format=%B $h | grep -q "Co-Authored-By:" && w=$((w+1)); done; echo "total=$t with=$w without=$((t-w))"
```

## バックアップ（Claude、PowerShell）

```powershell
$dst = '<バックアップ先>\<名前>'
git -C D:\<元> status --short                      # 何も出ないこと（未コミットの変更なし）
New-Item -ItemType Directory -Path $dst | Out-Null

# 全履歴のbundleと検証
git -C D:\<元> bundle create "$dst\<元>.bundle" --all
git -C D:\<元> bundle verify "$dst\<元>.bundle"

# フォルダ一式のzip（Windows標準のtarをフルパスで。.gitも含まれる）
& C:\Windows\System32\tar.exe -a -c -f "$dst\<元>-worktree.zip" -C D:\ <元>
$list = & C:\Windows\System32\tar.exe -t -f "$dst\<元>-worktree.zip"
"zip entries=$($list.Count)"
"actual=$((Get-ChildItem -LiteralPath D:\<元> -Recurse -Force).Count + 1)"   # ルートを含めた数。zipと一致すること
($list | Select-String -SimpleMatch '<元>/.git/HEAD').Count                 # 1であること

# ハッシュ値の保存
Get-FileHash "$dst\*" -Algorithm SHA256 | ForEach-Object { "$($_.Hash)  $(Split-Path $_.Path -Leaf)" } | Tee-Object -FilePath "$dst\SHA256SUMS.txt"
```

```bash
# 復元テスト（一時フォルダにcloneして確認し、削除する）
T=<一時フォルダ>/restore-test
git clone -q <バックアップ先>/<名前>/<元>.bundle "$T" && git -C "$T" rev-parse HEAD && git -C "$T" rev-list --all --count && git -C "$T" fsck --full; rm -rf "$T"
```

## 指示ファイルの事前チェック（Claude）

```bash
# replace-text.txt の各行が、全履歴で何個のファイルの版に該当するか
export LC_ALL=C.UTF-8
while IFS= read -r line; do k="${line%%==>*}"; echo "$(git -C /d/<元> grep -c -F "$k" $(git -C /d/<元> rev-list --all) | wc -l) hits"; done < <バックアップ先>/<名前>/replace-text.txt

# BOMが無いこと（先頭がEF BB BFでないこと）
head -c3 <バックアップ先>/<名前>/replace-text.txt | od -An -tx1
```

## 書き換え（ユーザーが`!`付きで実行）

```bash
git clone --no-local /d/<元> /d/<元>-rewrite
cd /d/<元>-rewrite && "$LOCALAPPDATA/Programs/git-filter-repo/Scripts/git-filter-repo.exe" --replace-text <バックアップ先>/<名前>/replace-text.txt --commit-callback "$(grep -v '^#' <バックアップ先>/<名前>/commit-callback.py)"
```

`!`がPowerShellで動く場合（書き換えは`templates/run-rewrite.sh`をバックアップのフォルダに置いて使う）:

```powershell
! git clone --no-local D:\<元> D:\<元>-rewrite
! & "C:\Program Files\Git\bin\bash.exe" <バックアップ先>/<名前>/run-rewrite.sh
```

```bash
# Claudeによる run-rewrite.sh の事前チェック
grep -c $'\r' <バックアップ先>/<名前>/run-rewrite.sh     # 0であること（LF）
bash -n <バックアップ先>/<名前>/run-rewrite.sh && echo SYNTAX_OK
```

他のオプションの例:

```bash
# ファイルを全履歴から削除する
... --path <削除するパス> --invert-paths

# コミットメッセージの文字列を置き換える
... --replace-message <バックアップ先>/<名前>/replace-message.txt
```

## 検証（Claude、読み取りのみ）

```bash
R=/d/<元>-rewrite; O=/d/<元>; export LC_ALL=C.UTF-8
git -C $R rev-list --all --count; git -C $O rev-list --all --count                       # コミット数（新/旧）
git -C $R log --all --format='%an <%ae> | %cn <%ce>' | sed -E 's/([A-Za-z0-9._%+-]{2})[A-Za-z0-9._%+-]*@((gmail|yahoo|outlook|hotmail|live|icloud)\.[A-Za-z.]+)/\1***@\2/g' | sort | uniq -c   # 名義
git -C $R grep -l -F "<消したい語>" $(git -C $R rev-list --all) | wc -l                   # 0であること
n=0; for h in $(git -C $R rev-list --all); do git -C $R log -1 --format=%B $h | grep -q "Co-Authored-By:" || n=$((n+1)); done; echo "no-trailer=$n"
echo "tree old=$(git -C $O rev-parse HEAD^{tree}) new=$(git -C $R rev-parse HEAD^{tree})" # 一致を確認
diff <(git -C $O log --format=%s | sort) <(git -C $R log --format=%s | sort)              # 除去されたコミットの特定
git -C $R fsck --full
```

## 反映後の確認（Claude）

```bash
cd /d/<元>
git status --short | wc -l          # 多数表示される場合は次の2行
git diff --stat | tail -1           # 内容の差分が無いこと（改行コードの警告のみ）
git update-index --refresh >/dev/null; git status --short | wc -l   # 0であること（git add -A は未追跡のファイルまでステージするため使わない）
git log --all --format='%ae|%ce' | sed -E 's/([A-Za-z0-9._%+-]{2})[A-Za-z0-9._%+-]*@((gmail|yahoo|outlook|hotmail|live|icloud)\.[A-Za-z.]+)/\1***@\2/g' | sort | uniq -c
git fsck --full
git config --file <バックアップ先>/<名前>/original.git/config --list; git config --local --list   # 消えた設定の確認（originと上流以外に無いこと）
diff <バックアップ先>/<名前>/original.git/info/exclude .git/info/exclude                       # 差分が無いこと
ls <バックアップ先>/<名前>/original.git/hooks | grep -v '\.sample$'                              # 独自のフックが無いこと（あれば戻す必要をユーザーに伝える）
# その後、プロジェクトの標準コマンドでビルド・テスト
```

`.git`の入れ替え（`!`がPowerShellで動く場合、ユーザーが1行ずつ実行）:

```powershell
! & "C:\Program Files\Git\bin\bash.exe" -c 'mv /d/<元>/.git <バックアップ先>/<名前>/original.git'
! & "C:\Program Files\Git\bin\bash.exe" -c 'cp -r /d/<元>-rewrite/.git /d/<元>/.git'
```

## GitHubへの反映後の確認（Claude、読み取りのみ）

```bash
gh api repos/<owner>/<repo> --jq '{private, created_at, forks_count}'        # 作り直した場合（手順7のA）、created_atが新しいこと
gh api repos/<owner>/<repo>/commits/<書き換え前のHEADのID> --jq .sha           # "No commit found"（HTTP 422）であること。IDが返るなら旧コミットが残っている
git ls-remote origin                                                          # ローカルのmainと一致すること
gh api --paginate "repos/<owner>/<repo>/commits?per_page=100" --jq '.[] | "\(.commit.author.email)|\(.commit.committer.email)"' | sed -E 's/([A-Za-z0-9._%+-]{2})[A-Za-z0-9._%+-]*@((gmail|yahoo|outlook|hotmail|live|icloud)\.[A-Za-z.]+)/\1***@\2/g' | sort | uniq -c

# 作り直しで失うものの確認（作り直す前）
gh issue list -R <owner>/<repo> --state all; gh pr list -R <owner>/<repo> --state all
gh api repos/<owner>/<repo>/collaborators --jq '.[].login'; gh api repos/<owner>/<repo>/hooks --jq length
gh api repos/<owner>/<repo>/keys --jq length; gh api repos/<owner>/<repo>/actions/secrets --jq .total_count
gh api repos/<owner>/<repo> --jq '{description, homepage, topics, has_pages}'; gh api repos/<owner>/<repo>/branches --jq '.[] | select(.protected) | .name'
```

## 別環境のクローンの取り直し（ユーザーがその環境のターミナルで実行）

```bash
cd <クローン>
git status --short                                                    # 何も出ないこと
git merge-base --is-ancestor main <書き換え前のHEADのID> && echo "未pushのコミットなし"   # fetchする前に実行
# ↑の結果: 「未pushのコミットなし」→問題なし／何も出ない→そのクローンにしか無いコミットがある（退避前に相談）／
#          「fatal: Not a valid commit name」→クローンが遅れている。fetchせずに次が空であることで確かめる
git log --oneline origin/main..main
git branch; git stash list                                            # main以外のブランチ・stashが無いこと（あれば退避前に相談）
git status --short --ignored                                          # 移す必要のある管理外のファイル
git config --local --list                                             # リポジトリ単位の設定（user.email等）を控える
cd ..; mv <クローン> <クローン>.old
git clone "$(git -C <クローン>.old remote get-url origin)" <クローン>
git -C <クローン> config user.email "<noreplyアドレス>"                  # 控えた設定を設定し直す（user.name等も同様）
git -C <クローン> config --show-origin user.email                        # file:.git/config と noreply が表示されること
# 管理外のファイルを移して確認した後: rm -rf <クローン>.old
```
