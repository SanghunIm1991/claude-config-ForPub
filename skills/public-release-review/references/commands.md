# コマンド集（public-release-review）

どれもリポジトリの直下で実行し、ファイルを読むだけで変更はしない（外部への通信を伴うのは、最後の節の外部リンクの確認だけ）。`<...>` は置き換える部分。

- **bash**: WSL・Linux・macOS・Git Bash。日本語を含む検索や並べ替えが崩れる場合は、先に `export LC_ALL=C.UTF-8` を実行する。
- **PowerShell**: Windows。`git` のサブコマンド（`git grep`・`git log`）は同じ形で使える。パイプの先の `grep` は `Select-String`、`sort | uniq -c` は `Group-Object` に置き換える。Windows PowerShell 5.1の `curl` は `Invoke-WebRequest` の別名なので、curlを使うときは `curl.exe` と書く。
  - **最初に文字コードをUTF-8にする**（下のブロック）。既定のままだと、`git log -p` などのUTF-8の出力が文字化けして受け取られ、日本語のキーワードで照合すると、該当があっても0件になる（点検が黙って漏れる）。
  - `Select-String -Path` でファイルを読むときは、`-Encoding UTF8` を付ける（Windows PowerShell 5.1は、BOMの無いUTF-8を正しく読まないことがある）。
- **日本語のファイル名**: 既定のままだと、`git ls-files` などが日本語のファイル名を `"\343..."` の形で出す。ファイル名を扱うコマンドは `git -c core.quotepath=off ...` で実行する（下の例は、そう書いてある）。
- **Python**: スクリプト（`check_links.py`）は、WSL・Linuxでは `python3`、Windowsでは、その環境のCLAUDE.mdが決めているバージョンを明示して（`py -3.<x>`）実行する。下の例の `py -3.<x>` は、その指定に置き換える（標準ライブラリだけで動く）。

```powershell
# PowerShellで点検を始める前に、1回だけ実行する
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$OutputEncoding = [System.Text.Encoding]::UTF8
```

見つかった機微な情報は、会話に全文を出さない。件数・ファイル名・行番号で確かめ、必要なら前後だけを切り出す（`cut -c1-120` 等）。

## 1. コミットの名義

```bash
git log --all --format='%an <%ae> | %cn <%ce>' | sort | uniq -c
```

```powershell
git log --all --format='%an <%ae> | %cn <%ce>' | Group-Object | Select-Object Count, Name
```

**見方**: 公開してよい名義（GitHubのnoreplyアドレス `<ID>+<ユーザー名>@users.noreply.github.com` 等）だけか。実メールが混ざっていれば、そのコミットを調べ、git-history-rewrite スキルで直すかをユーザーと決める。

## 2. メールアドレス（今の版と全履歴）

想定済みのもの（noreply・ダミー・ツールの表記）は除く。除外の一覧は、プロジェクトに合わせて足す。

```bash
EXCL='users\.noreply\.github\.com|noreply@anthropic\.com|@example\.(com|org)|git@github\.com'

git grep -nIE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' | grep -vE "$EXCL"

git log --all -p | grep -oE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' | grep -vE "$EXCL" | sort | uniq -c
```

```powershell
$excl = 'users\.noreply\.github\.com|noreply@anthropic\.com|@example\.(com|org)|git@github\.com'

git grep -nIE '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' | Select-String -NotMatch $excl

git log --all -p | Select-String -AllMatches '[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}' | ForEach-Object { $_.Matches.Value } | Where-Object { $_ -notmatch $excl } | Group-Object | Select-Object Count, Name
```

## 3. 認証情報・ユーザー名・パス・ドライブ

```bash
git grep -nIiE 'api[_-]?key|secret|token|passw(or)?d|BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]|github_pat_|sk-[A-Za-z0-9]{10}'

git grep -nIE '/home/[a-z][a-z0-9_-]*/|[A-Za-z]:\\+Users\\+|/mnt/c/Users/'

# ローカルのユーザー名・アカウント名（意図して載せた著作権者の表示とリポジトリのURLは、目視で除外する）
git grep -nIi '<ローカルのユーザー名>'

git grep -nI '<アカウント名>'

# ドライブ文字のパスと、WSLから見たWindowsのドライブ
git grep -nIE '\b[A-Z]:\\[A-Za-z]|/mnt/[a-z]/'

# 全履歴の追加行から（件数だけ）
git log --all -p | grep -E '^\+' | grep -oE '/home/[a-z][a-z0-9_-]*|\b[A-Z]:\\[A-Za-z0-9_.\\-]+|/mnt/[a-z]/[A-Za-z0-9_./-]+' | sort | uniq -c
```

```powershell
git grep -nIiE 'api[_-]?key|secret|token|passw(or)?d|BEGIN [A-Z ]*PRIVATE KEY|ghp_[A-Za-z0-9]|github_pat_|sk-[A-Za-z0-9]{10}'

git grep -nIE '/home/[a-z][a-z0-9_-]*/|[A-Za-z]:\\+Users\\+|/mnt/c/Users/'

git grep -nIi '<ローカルのユーザー名>'

git grep -nI '<アカウント名>'

git grep -nIE '\b[A-Z]:\\[A-Za-z]|/mnt/[a-z]/'

git log --all -p | Select-String '^\+' | Select-String -AllMatches '/home/[a-z][a-z0-9_-]*|\b[A-Z]:\\[A-Za-z0-9_.\\-]+|/mnt/[a-z]/[A-Za-z0-9_./-]+' | ForEach-Object { $_.Matches.Value } | Group-Object | Select-Object Count, Name
```

**見方**: 説明文の一般的な語（「パスワードマネージャー」）や伏せ字（`/home/<ユーザー名>`）にも当たるので、1件ずつ読む。ドライブ文字のパスは、手順書の「例」なのか、実際の保存先・構成を示しているのかを見分ける。

## 4. PC固有の値・利用状況のキーワード

```bash
git grep -nIE '[0-9]+(\.[0-9]+)? ?(GB|GiB|MB|TB)\b'

# キーワードは、ユーザーと相談して決めたものを入れる（一覧を公開する文書に書かない）
K='<キーワード1>|<キーワード2>'

git grep -nIE "$K" | cut -c1-150

git log --all -p | grep -E '^\+' | grep -E "$K" | sort -u | cut -c1-150
```

```powershell
git grep -nIE '[0-9]+(\.[0-9]+)? ?(GB|GiB|MB|TB)\b'

$k = '<キーワード1>|<キーワード2>'

git grep -nIE $k

git log --all -p | Select-String '^\+' | Select-String $k | ForEach-Object { $_.Line } | Sort-Object -Unique
```

## 5. 追跡してはいけないもの・参照・コミットメッセージ

```bash
# 除外すべきフォルダや拡張子は、プロジェクトの .gitignore に合わせて変える
git -c core.quotepath=off ls-files | grep -E '^(notes|ws)/|\.(env|pem|key|p12|pfx|tar|zip|vhdx)$'

# 大きなファイル（上位10件）
git -c core.quotepath=off ls-files -z | xargs -0 du -k 2>/dev/null | sort -rn | head

# ブランチ・タグ・stash
git branch -a; git tag; git stash list

# 過去にだけ存在したファイル
comm -23 <(git -c core.quotepath=off log --all --format= --name-only | sort -u | grep .) <(git -c core.quotepath=off ls-files | sort)

# コミットメッセージ（キーワード・アカウント名・パス等で検索する）
git log --all --format=%B | grep -nE '<パターン>'
```

```powershell
git -c core.quotepath=off ls-files | Select-String -Pattern '^(notes|ws)/|\.(env|pem|key|p12|pfx|tar|zip|vhdx)$'

git -c core.quotepath=off ls-files | ForEach-Object { Get-Item -LiteralPath $_ } | Sort-Object Length -Descending | Select-Object -First 10 Length, FullName

git branch -a; git tag; git stash list

$past = git -c core.quotepath=off log --all --format= --name-only | Where-Object { $_ } | Sort-Object -Unique
$now = git -c core.quotepath=off ls-files
Compare-Object $past $now | Where-Object SideIndicator -eq '<=' | Select-Object -ExpandProperty InputObject

git log --all --format=%B | Select-String '<パターン>'
```

## 6. 権利

```bash
# Markdown・画像以外の追跡ファイル（第三者のファイルが混ざっていないか）
git -c core.quotepath=off ls-files | grep -vE '\.(md|svg|png|jpg)$|^\.git(attributes|ignore)$|^LICENSE'

# SVGの埋め込み画像・外部参照
git grep -nE '<image|href="https?:|base64,' -- '*.svg'

# 出典の注記が無い文書（対象はプロジェクトに合わせる。語の揺れがあるので、出た文書は本文を読む）
grep -LE '出典|出どころ|CC BY|License|ライセンス' docs/*.md

# 配布する重み（.npz）の、各配列の名前と型・形（numpyで読み込まず、zipとして中を見るだけ）。
# 各行の名前が .npy で終わり、descr が '<f4' のような数の型なら問題ない（'|O' はpickleを使う配列）。
# .npy の版1.0のヘッダ（numpyの既定）を前提に、先頭10バイトの後を読む。表示が乱れたら、版（7〜8バイト目）を確かめる。
# 何も表示されないときは、パスが合っているかを確かめる（「問題なし」と取り違えない）
python3 -c "import sys, zipfile; [print(f, n, zipfile.ZipFile(f).read(n)[10:128].split(b'\n')[0].decode().strip()) for f in sys.argv[1:] for n in zipfile.ZipFile(f).namelist()]" path/to/*.npz
```

```powershell
git -c core.quotepath=off ls-files | Select-String -NotMatch '\.(md|svg|png|jpg)$|^\.git(attributes|ignore)$|^LICENSE'

git grep -nE '<image|href="https?:|base64,' -- '*.svg'

Get-ChildItem docs\*.md | Where-Object { -not (Select-String -Path $_ -Pattern '出典|出どころ|CC BY|License|ライセンス' -Encoding UTF8 -Quiet) } | Select-Object -ExpandProperty Name

py -3.<x> -c "import sys, glob, zipfile; [print(f, n, zipfile.ZipFile(f).read(n)[10:128].split(b'\n')[0].decode().strip()) for f in glob.glob(sys.argv[1]) for n in zipfile.ZipFile(f).namelist()]" "path\to\*.npz"
```

## 7. リンク（`check_links.py`）

スクリプトはこのスキルの `references/` にある。リポジトリの直下で、スクリプトのパスを指定して実行する。対象は既定で `README.md` と `docs/*.md`（`--files` で変えられる）。

```bash
python3 ~/.claude/skills/public-release-review/references/check_links.py internal

python3 ~/.claude/skills/public-release-review/references/check_links.py domains
```

```powershell
py -3.<x> "$env:USERPROFILE\.claude\skills\public-release-review\references\check_links.py" internal

py -3.<x> "$env:USERPROFILE\.claude\skills\public-release-review\references\check_links.py" domains
```

`domains` の一覧をユーザーに見せ、外部への通信の承認を得てから確かめる。

```bash
python3 ~/.claude/skills/public-release-review/references/check_links.py external
```

```powershell
py -3.<x> "$env:USERPROFILE\.claude\skills\public-release-review\references\check_links.py" external
```

**見方**: `internal` は、`broken: 0` だけが出れば問題ない。`external` は、失敗したURLだけを出す（`--all` で全件）。ボット対策で失敗するサイト（例: 公式ドキュメントのサイト。ROS 2 の docs.ros.org など）は、原稿のリポジトリ（GitHub等）の同じパスで確かめる（`--rewrite` で置き換えの規則を渡せる。スクリプトの先頭の説明を参照）。名前解決の失敗（`DNS`）は、移転・閉鎖か一時的な不調かを、公式のリポジトリのREADMEやWeb検索で見分ける。
