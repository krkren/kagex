# Fails unless every step a release package must pass did pass in a run-kagex.ps1 smoke run.
param([Parameter(Mandatory)] [string]$Steps)
$lines = Get-Content $Steps
$must = 'boot:', 'kag window created', 'SDL window opened', 'load CI helpers', 'logo -> title', 'title: START',
        'demo: KAGEX layer', 'vector:', 'clip and zip:', 'demo: World', 'transitions:', 'demo: Effekseer', 'history: no word split', 'in game:', 'history log', 'quit', 'engine log'
$bad = foreach ($m in $must) {
    $l = $lines | Where-Object { $_ -like "| $m*" } | Select-Object -First 1
    if (-not $l -or $l -notmatch '\| PASS \|') { "$m -> $l" }
}
$bad += $lines | Where-Object { $_ -match '^\| (exit code|cleanup) \|' }
if ($bad) { $bad; throw 'package smoke test failed; not publishing' }
'smoke test passed'
