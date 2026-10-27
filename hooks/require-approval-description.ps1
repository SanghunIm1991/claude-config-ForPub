# PreToolUse hook: require 目的 / 実行内容 / 危険度 in the description of Bash and PowerShell calls
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
$raw = [Console]::In.ReadToEnd()
try { $j = $raw | ConvertFrom-Json } catch { exit 0 }
$desc = [string]$j.tool_input.description
$missing = @()
if ($desc -notmatch '目的') { $missing += '目的' }
if ($desc -notmatch '実行(する)?内容') { $missing += '実行内容' }
if ($desc -notmatch '危険度[:：]\s*[低中高]') { $missing += '危険度（低・中・高）' }
if ($missing.Count -eq 0) { exit 0 }
$reason = 'description（承認ダイアログに出る説明欄）に ' + ($missing -join '・') + ' がありません。' +
  '「目的: … / 実行内容: … / 危険度: 低|中|高（根拠）」の形で日本語で書き直して、もう一度呼び出してください。'
@{ hookSpecificOutput = @{ hookEventName = 'PreToolUse'; permissionDecision = 'deny'; permissionDecisionReason = $reason } } | ConvertTo-Json -Depth 4 -Compress
exit 0
