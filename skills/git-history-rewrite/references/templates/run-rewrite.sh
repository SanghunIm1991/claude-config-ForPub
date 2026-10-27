#!/bin/bash
# 作業用クローンの中だけで git filter-repo を実行するスクリプトのひな形（`!` がPowerShellで動く環境用）。
# バックアップと同じフォルダに置き、改行コードはLFにする。Git Bashをフルパスで指定して実行する:
#   ! & "C:\Program Files\Git\bin\bash.exe" <バックアップ先>/<名前>/run-rewrite.sh
# 元のリポジトリ・バックアップには触れない。使わないオプション（--replace-text 等）の行は削除する。
set -eu
B=<バックアップ先>/<名前>
R=/d/<元のリポジトリ>-rewrite
[ -d "$R/.git" ] || { echo "ERROR: $R がありません（先に clone してください）"; exit 1; }
cd "$R"
"$LOCALAPPDATA/Programs/git-filter-repo/Scripts/git-filter-repo.exe" \
  --replace-text "$B/replace-text.txt" \
  --commit-callback "$(grep -v '^#' "$B/commit-callback.py")"
