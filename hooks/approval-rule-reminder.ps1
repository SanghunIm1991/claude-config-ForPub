# UserPromptSubmit hook: remind the approval-description rule every turn
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
Write-Output '[ルール] 承認を求めうる操作の前には、本文に日本語で「目的」「実行する内容」「危険度（低・中・高と根拠）」を併記する。Bash・PowerShellの description も「目的: … / 実行内容: … / 危険度: 低|中|高（根拠）」の形で書く。'
