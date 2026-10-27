# Claude Code status line: model | effort | context usage | plan usage limits
[Console]::OutputEncoding = [System.Text.Encoding]::UTF8
[Console]::InputEncoding = [System.Text.Encoding]::UTF8
$raw = [Console]::In.ReadToEnd()
try { $j = $raw | ConvertFrom-Json } catch { Write-Output 'statusline: invalid input'; exit 0 }

$model = $j.model.display_name
if (-not $model) { $model = $j.model.id }

# effort: the field name may differ by version, so try several
$effort = $null
if ($j.effort -is [string]) { $effort = $j.effort }
elseif ($j.effort.level) { $effort = $j.effort.level }
elseif ($j.model.effort) { $effort = $j.model.effort }
elseif ($j.reasoning_effort) { $effort = $j.reasoning_effort }
elseif ($env:CLAUDE_CODE_EFFORT_LEVEL) { $effort = $env:CLAUDE_CODE_EFFORT_LEVEL }
if (-not $effort) { $effort = '-' }

$ctx = '-'
$cw = $j.context_window
if ($cw -and $null -ne $cw.used_percentage) {
    $ctx = '{0:N0}%' -f [double]$cw.used_percentage
} elseif ($cw -and $cw.current_usage -and $cw.context_window_size) {
    $u = $cw.current_usage
    $used = [double]$u.input_tokens + [double]$u.cache_creation_input_tokens + [double]$u.cache_read_input_tokens
    $ctx = '{0:N0}%' -f ($used * 100 / [double]$cw.context_window_size)
}

# plan usage limits (5-hour / 7-day), shown only when provided
$limits = ''
$rl = $j.rate_limits
if ($rl) {
    $parts = @()
    if ($null -ne $rl.five_hour.used_percentage) { $parts += ('5h: {0:N0}%' -f [double]$rl.five_hour.used_percentage) }
    if ($null -ne $rl.seven_day.used_percentage) { $parts += ('7d: {0:N0}%' -f [double]$rl.seven_day.used_percentage) }
    if ($parts.Count -gt 0) { $limits = ' | plan ' + ($parts -join ' ') }
}

Write-Output ("[{0}] effort: {1} | ctx: {2}{3}" -f $model, $effort, $ctx, $limits)
