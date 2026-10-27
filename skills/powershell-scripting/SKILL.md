---
name: powershell-scripting
description: このユーザーのWindows環境でPowerShellスクリプトを書く・実行する・デバッグする際の汎用的な技術メモを集めたスキル。プロジェクトを問わず適用する。Claude CodeのPowerShellツール/Bashツールがツール呼び出しごとにPATH・作業ディレクトリ(cwd)をリセットする挙動、GUI(tkinter等)やsubprocess起動が絡むテストをBashツール(Git Bash/MSYS)経由で実行した場合の誤検知とPowerShellツールでの実行推奨、`run_in_background`実行時に終了コードが実際のプログラム状態と食い違う既知の問題、PowerShellのパイプライン結果が1件だけの場合に配列ではなく単一値(Scalar)になり`[0]`インデックスアクセスで文字列の1文字目だけが返ってしまう罠(`@()`による明示的な配列化で対策)、Windows PowerShell 5.1の`ConvertTo-Json`がデフォルトDepth=2でネストの深いJSON(設定ファイル等)をサイレントに切り詰める罠(`-Depth`明示で対策)を扱う。「PowerShellスクリプトを書きたい」「PowerShellでコマンドが見つからないエラーが出た」「テストが不安定/誤検知する」「バックグラウンド実行の終了コードがおかしい」「値が先頭1文字だけになる/切り詰められる」「JSON設定ファイルを読み書きしたら一部の項目が消えた/壊れた」といった場面で使う。特定プロジェクトの業務ロジックやビルド手順は扱わず、PowerShell/Claude Codeツールの挙動に関する汎用的な技術知識に特化する。
---

# PowerShellスクリプティングの技術メモ

Windows環境でPowerShellスクリプトを書く・Claude CodeのPowerShellツール/Bashツールを使う際に繰り返し遭遇してきた技術的な罠と対策をまとめる。プロジェクト固有の業務ロジックは扱わない。

## Claude CodeのPowerShell/Bashツールでシェル状態がリセットされる

ツール呼び出しごとにPATH等のシェル状態がリセットされることがある。`git`など通常あるはずのコマンドが「見つからない」となったら、以下でPATHを通してから再実行する。

```powershell
[System.Environment]::SetEnvironmentVariable("PATH", [System.Environment]::GetEnvironmentVariable("PATH","Machine") + ";" + [System.Environment]::GetEnvironmentVariable("PATH","User"), "Process")
```

このPATH不足は、コマンドが「見つからない」という分かりやすいエラーだけでなく、ビルドツール（PyInstaller等）が依存DLL/共有ライブラリを解決できないという形でも現れる。この場合ビルド自体はエラーを出さずに完了してしまい、生成物を実行した時点で初めて失敗が発覚するため気づきにくい（例: Anaconda環境で`C:\ProgramData\anaconda3\python.exe -m PyInstaller`を実行する際、PATHに`C:\ProgramData\anaconda3\Library\bin`が含まれていないと、tkinter依存の`tcl86t.dll`/`tk86t.dll`を同梱できず`ImportError: DLL load failed`で実行時エラーになる）。ネイティブ依存を持つビルドを行う際は、PATHに必要なディレクトリが含まれているか事前に確認するとともに、ビルドログに`Library not found`等の依存解決警告が出ていないかを確認すること。

同様に、Bashツールの**作業ディレクトリ（cwd）もツール呼び出しのたびにプライマリ作業ディレクトリへリセットされる**（`cd`はそのツール呼び出し内でしか有効でない）。そのため、プライマリ作業ディレクトリ外（例: `~/.claude`）で継続的にコマンドを実行したい場合、毎回`cd <path> && <command>`と書くか、コマンド自体にパス指定オプションがあればそちらを使う（例: `git -C "<path>" status`）。後者の方が`permissions.allow`の許可パターン（`Bash(git -C * status*)`等）を安定して一致させやすく、承認プロンプトを減らせる。

## テスト実行・バックグラウンド実行時の信頼性

GUI（tkinter等）やWindowsの`.bat`/subprocess起動が絡むテスト（pytest等）をBashツール（Git Bash/MSYS）経由で実行すると、実装・テスト内容とは無関係な誤検知（`_tkinter.TclError`、サブプロセス終了コードの不一致等）が発生することがある。この種のテストはPowerShellツールで実行する方が安定する。単純な構文チェック等、GUI/subprocessを伴わない処理はBashツールのままで問題ない。

また、`run_in_background`で長時間コマンドを実行した場合、捕捉・エコーされる終了コードが実際のプログラムの終了状態と食い違うことがある（正常終了したにもかかわらず終了コード127が記録された実例あり）。終了コードのみで成否を判断せず、出力ファイルの実在・内容やプログラム自身の完了ログ等、具体的な成果物で確認すること。

## パイプライン結果が1件だけの場合、配列ではなくScalarになる罠

`$x = パイプライン | Where-Object {...}` のようにパイプラインの結果を変数へ代入するコードで、結果が**1件だけ**の場合、PowerShellは要素数1の配列ではなく**単一の値そのもの**を代入する。そこへ`$x[0]`でインデックスアクセスすると、文字列も「文字の配列」として扱えるため、「配列の1番目の要素(文字列全体)」ではなく「**文字列の1文字目**」が返ってしまう。

対策は、結果件数に関わらず`@(...)`で明示的に配列化すること。

```powershell
# NG: 結果が1件のとき $deviceLines が文字列そのものになり、[0]が先頭1文字を返す
$deviceLines = $devicesOutput | Where-Object { $_ -match "device\s*$" }
$serial = $deviceLines[0]   # 例: "R"(1文字)になってしまう

# OK: @()で常に配列化する
$deviceLines = @($devicesOutput | Where-Object { $_ -match "device\s*$" })
$serial = $deviceLines[0]   # 正しく文字列全体が返る
```

**症状からの見分け方**: 値が先頭1文字だけになる・想定より短く切り詰められる症状を見たら、まず`$x[0].GetType().Name`で型を確認する。`String`を期待している箇所で`Char`が返っていれば、この罠に該当する。エンコーディング仮説(文字化け・NUL混入等)に飛びつく前に、この型チェックを先に行うこと。特に「フィルタ条件に一致する件数が実運用ではほぼ常に1件になる」ケース(接続機器が1台のみ、対象ファイルが1件のみ等)は、テスト時に複数件で動作確認していても本番相当の条件(1件)で初めて発現するため見落としやすい。

## .ps1に日本語を書く際はBOM付きUTF-8で保存する

Writeツールで既定(UTF-8、BOMなし)のまま`.ps1`ファイルに日本語コメント/文字列を保存すると、Windows PowerShell 5.1のパーサーが既定でシステムのANSIコードページ(日本語環境ではcp932)としてファイルを読み込み、マルチバイト文字が化けて構文エラー(`The string is missing the terminator`等、本来無関係な箇所を指すエラーとして出ることが多い)になる。

日本語を含む`.ps1`を新規作成・編集した後は、実行前に以下でBOM付きUTF-8へ変換する(Get-Content/Set-Contentとも`-Encoding UTF8`を明示。指定しないとこの環境の既定はANSI)。

```powershell
$content = Get-Content -Raw -Encoding UTF8 -Path <path>
Set-Content -Path <path> -Value $content -Encoding UTF8 -NoNewline
```

変換後は`[System.Management.Automation.Language.Parser]::ParseFile`で構文エラーが消えたことを確認してから実行する。

## `ConvertTo-Json`のデフォルトDepthでネストが切り詰められる罠

`Get-Content -Raw | ConvertFrom-Json` でJSONファイル（設定ファイル等）を読み込み、一部のプロパティだけ変更してから`ConvertTo-Json`で書き戻すと、ネストが深い部分（配列→オブジェクト→配列→オブジェクトのような4階層以上の構造）が**エラーなくサイレントに省略・文字列化されて壊れる**ことがある。

Windows PowerShell 5.1の`ConvertTo-Json`は、`-Depth`オプションを省略するとデフォルトで**Depth=2**までしかシリアライズしない。3階層目以降は`"System.Object[]"`や`"@{...}"`のような文字列表現に潰される。Claude Code設定ファイル（`~/.claude/settings.json`の`hooks`セクション等）はこの深さを超えやすいため、特に注意。

対策:

```powershell
$s = Get-Content $path -Raw | ConvertFrom-Json
# ...一部プロパティを変更...
$json = $s | ConvertTo-Json -Depth 20   # 十分大きい値を明示指定
```

設定ファイルのような重要なJSONを書き戻す際は、事前にバックアップを取り、書き戻し後に新旧のトップレベルキー一覧・主要な値（配列の件数など）を比較検証してからバックアップを削除する、という手順も併用すると安全。

**症状からの見分け方**: JSON往復後に一部のネストしたキー・配列が消えている/文字列化されている場合、まず変更に使ったコマンドに`-Depth`指定があるかを疑う。
