# Runs kagex once on Windows and drives it through the engine's REPL file channel
# (krkrz_dev/src/core/doc/REPL.md). Writes steps.md, info.txt, logs and screenshots to -Out.
[CmdletBinding()]
param(
    [Parameter(Mandatory)] [string]$Kagex,
    [Parameter(Mandatory)] [string]$Out,
    [Parameter(Mandatory)] [string]$Mode,
    [string[]]$EngineArgs = @(),
    [ValidateSet('full', 'smoke', 'probe')] [string]$Plan = 'full',
    [int]$BootTimeout = 180
)
$ErrorActionPreference = 'Stop'
# Desktop screenshots are Windows-only; on Linux the engine's own captures are the evidence
if ($IsWindows) { Add-Type -AssemblyName System.Windows.Forms, System.Drawing }

$Kagex   = (Resolve-Path $Kagex).Path
$Out     = (New-Item -ItemType Directory -Force $Out).FullName
$chan    = Join-Path $Kagex 'ci-chan'
$shotDir = Join-Path $Kagex 'ci-out'
$save    = Join-Path $Kagex 'savedata'
foreach ($d in $chan, $shotDir, $save) { Remove-Item -Recurse -Force $d -ErrorAction SilentlyContinue }
New-Item -ItemType Directory -Force $chan, $shotDir | Out-Null

$script:proc   = $null
$script:shotNo = 0
$script:steps  = [System.Collections.Generic.List[object]]::new()

function Invoke-Tjs([string]$Code, [int]$TimeoutSec = 30) {
    if ($script:proc.HasExited) { throw "engine has exited (code $($script:proc.ExitCode))" }
    $tmp = Join-Path $chan 'cmd.tmp'; $cmd = Join-Path $chan 'cmd'; $resp = Join-Path $chan 'resp'
    [IO.File]::WriteAllText($tmp, $Code, [Text.UTF8Encoding]::new($false))
    Move-Item -Force $tmp $cmd
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while (-not (Test-Path $resp)) {
        if ($script:proc.HasExited) { throw "engine exited while running a command (code $($script:proc.ExitCode))" }
        if ($sw.Elapsed.TotalSeconds -gt $TimeoutSec) { throw "no REPL response in ${TimeoutSec}s to: $($Code.Substring(0, [Math]::Min(80, $Code.Length)))" }
        Start-Sleep -Milliseconds 50
    }
    $txt = $null
    for ($i = 0; $i -lt 60 -and $null -eq $txt; $i++) {
        try { $txt = [IO.File]::ReadAllText($resp, [Text.Encoding]::UTF8); Remove-Item -Force $resp }
        catch { $txt = $null; Start-Sleep -Milliseconds 25 }
    }
    $r = $txt | ConvertFrom-Json
    if (-not $r.ok) { throw "TJS: $($r.error)" }
    $v = [string]$r.result
    # Strings come back pretty-printed, i.e. quoted
    if ($v.Length -ge 2 -and $v[0] -eq '"' -and $v[-1] -eq '"') {
        try { $v = [string]($v | ConvertFrom-Json) } catch { $v = $v.Substring(1, $v.Length - 2) }
    }
    return $v
}

function Get-State {
    $h = @{}
    foreach ($kv in (Invoke-Tjs '__ci_state()').Split('|')) {
        $p = $kv.Split('=', 2); $h[$p[0]] = $p[1]
    }
    $h
}
function Format-State($s) { "$($s.storage):$($s.line) stable=$($s.stable) select=$($s.select) trans=$($s.trans)" }

function Wait-State([string]$What, [scriptblock]$Cond, [int]$TimeoutSec = 30, [scriptblock]$OnTick = $null) {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($true) {
        $s = Get-State
        if (& $Cond $s) { return $s }
        if ($sw.Elapsed.TotalSeconds -gt $TimeoutSec) { throw "timed out after ${TimeoutSec}s waiting for $What (now $(Format-State $s))" }
        if ($OnTick) { & $OnTick $sw.Elapsed.TotalSeconds }
        Start-Sleep -Milliseconds 250
    }
}

# Screenshots are evidence, not a pass condition: a failed capture is noted, not thrown
function Shot([string]$Name) {
    $script:shotNo++
    $file = '{0:D2}-{1}.png' -f $script:shotNo, $Name
    Invoke-Tjs "Agent.captureScreen(System.exePath + 'ci-out/$file')" | Out-Null
    $p = Join-Path $shotDir $file
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while (-not (Test-Path $p)) {
        if ($sw.Elapsed.TotalSeconds -gt 8) { $script:shotFails++; return "(${file}: capture not written)" }
        Start-Sleep -Milliseconds 100
    }
    Start-Sleep -Milliseconds 300
    $file
}
$script:shotFails = 0

# The engine logs to stdout (redirected to a file it keeps open)
function Read-Log {
    $f = [IO.File]::Open((Join-Path $Out 'stdout.txt'), 'Open', 'Read', 'ReadWrite')
    try { [IO.StreamReader]::new($f).ReadToEnd() } finally { $f.Dispose() }
}

function Desktop-Shot([string]$Name) {
    if (-not $IsWindows) { return }
    try {
        $b = [System.Windows.Forms.SystemInformation]::VirtualScreen
        $bmp = [System.Drawing.Bitmap]::new($b.Width, $b.Height)
        $g = [System.Drawing.Graphics]::FromImage($bmp)
        $g.CopyFromScreen($b.Left, $b.Top, 0, 0, $bmp.Size)
        $g.Dispose()
        $bmp.Save((Join-Path $Out "desktop-$Name.png"), [System.Drawing.Imaging.ImageFormat]::Png)
        $bmp.Dispose()
    } catch { Write-Host "desktop capture failed: $_" }
}

function Step([string]$Name, [scriptblock]$Body) {
    if ($script:proc -and $script:proc.HasExited) {
        $script:steps.Add([pscustomobject]@{ Step = $Name; Result = 'SKIP'; Sec = 0; Note = 'engine not running' })
        Write-Host "[SKIP] $Name"
        return
    }
    $sw = [Diagnostics.Stopwatch]::StartNew()
    try   { $note = (& $Body | Out-String).Trim(); $res = 'PASS' }
    catch { $note = $_.Exception.Message; $res = 'FAIL' }
    $sec = [Math]::Round($sw.Elapsed.TotalSeconds, 1)
    $script:steps.Add([pscustomobject]@{ Step = $Name; Result = $res; Sec = $sec; Note = $note })
    Write-Host "[$res] $Name (${sec}s) $note"
}

# A click that should change the game state; the mouse path is retried once, then the
# action is performed directly so later steps can still run (and the step fails).
function Click-Until([string]$Button, [string]$What, [scriptblock]$Cond, [string]$Fallback, [int]$TimeoutSec = 20) {
    $how = Invoke-Tjs "__ci_click('$Button')"
    try { Wait-State $What $Cond $TimeoutSec | Out-Null; return "clicked $Button ($how)" } catch {}
    $how2 = Invoke-Tjs "__ci_click('$Button')"
    try { Wait-State $What $Cond $TimeoutSec | Out-Null; return "clicked $Button on the 2nd try ($how2)" } catch {}
    $msg = "clicking '$Button' ($how) did not reach $What"
    if ($Fallback) {
        Invoke-Tjs $Fallback | Out-Null
        try { Wait-State $What $Cond $TimeoutSec | Out-Null; $msg += "; reached it with $Fallback" }
        catch { $msg += "; $Fallback did not reach it either: $($_.Exception.Message)" }
    }
    throw $msg
}

function RightClick-Back([string]$What, [scriptblock]$Cond, [string]$Fallback = '', [int]$TimeoutSec = 15) {
    $how = Invoke-Tjs '__ci_clickAt(960, 540, 1)'
    try { Wait-State $What $Cond $TimeoutSec | Out-Null; return "right-click ($how)" } catch {}
    $msg = "right-click ($how) did not return to $What"
    if ($Fallback) {
        Invoke-Tjs $Fallback | Out-Null
        try { Wait-State $What $Cond $TimeoutSec | Out-Null; $msg += "; $Fallback did" } catch { $msg += "; neither did $Fallback" }
    }
    throw $msg
}

# Advance the current scenario with left clicks until $Done, taking a screenshot every
# $Every clicks. Returns the click count.
function Advance([string]$Tag, [scriptblock]$Done, [int]$Every = 4, [int]$TimeoutSec = 240) {
    $clicks = 0
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ($true) {
        $s = Get-State
        if (& $Done $s) { return $clicks }
        if ($sw.Elapsed.TotalSeconds -gt $TimeoutSec) {
            try { Shot "$Tag-stuck" | Out-Null } catch {}
            throw "stuck at $(Format-State $s) after $clicks clicks"
        }
        if ($s.stable -eq '1' -and $s.select -eq '0' -and $s.queue -eq '0') {
            if ($clicks % $Every -eq 0) { Shot ('{0}-{1:D2}' -f $Tag, $clicks) | Out-Null }
            Invoke-Tjs '__ci_clickAt(960, 400)' | Out-Null
            $clicks++
            Start-Sleep -Milliseconds 350
        } else {
            Start-Sleep -Milliseconds 200
        }
    }
}

$atMenu  = { param($s) $s.storage -eq 's0001.ks' -and $s.select -eq '1' }
$atTitle = { param($s) $s.storage -eq 'title.ks' -and $s.stable -eq '1' -and $s.trans -eq '0' }

function Run-Demo([int]$Index, [string]$Tag) {
    Wait-State 'the demo menu' $atMenu 30 | Out-Null
    Start-Sleep -Milliseconds 900   # let the choices fade in
    $text = Invoke-Tjs "__ci_selectText($Index)"
    $how = Invoke-Tjs "__ci_clickSelect($Index)"
    $forced = ''
    try { Wait-State 'the choice to be taken' { param($s) $s.select -eq '0' } 8 | Out-Null }
    catch { Invoke-Tjs "__ci_forceSelect($Index)" | Out-Null; $forced = ' — MOUSE CLICK IGNORED, forced onButtonClick' }
    $n = Advance $Tag $atMenu
    if ($forced) { throw "'$text': $n clicks back to the menu$forced ($how)" }
    "'$text': $n clicks back to the menu (choice $how)"
}

# The Effects demo (choice 5), which must have drawn its effects: without krkreffekseer or
# OpenGL ES it says so and ends early, which passes Run-Demo
function Effect-Demo {
    $r = Run-Demo 5 'effect'
    $why = Invoke-Tjs "typeof kag.effekseerSystem == 'undefined' || kag.effekseerSystem === void ? 'no effect was played' : kag.effekseerSystem.available ? '' : kag.effekseerSystem.reason"
    if ($why) { throw "$r; Effekseer effects are unavailable: $why" }
    "$r; effects drawn"
}

# After the layer demo, whose last section shows an SVG beside a PNG of it: an SVG draws, turned
# 30 degrees too (layerExVector; a loose file goes through a copy in user://, and a turned picture
# through a raster of it, both worked around in AffineLayer.tjs). 2083 samples when it's all there
function Vector-Image {
    $why = Invoke-Tjs "typeof global.affineVectorImages == 'undefined' ? 'the framework has no SVG support' : affineVectorImages ? '' : 'layerExVector is not loaded'"
    if ($why) { throw $why }
    Invoke-Tjs "kag.tagHandlers.image(%[layer:'0', page:'fore', storage:'emblem', visible:'true', left:'960', top:'540', dafx:'center', dafy:'center']), kag.tagHandlers.layopt(%[layer:'0', page:'fore', rotate:'30']), 1" | Out-Null
    Start-Sleep -Milliseconds 800
    $n = [int](Invoke-Tjs "(function() { var t = new global.Layer(kag, kag.primaryLayer), n = 0; t.assignImages(kag.fore.layers[0]); for (var y = 2; y < t.imageHeight; y += 6) for (var x = 2; x < t.imageWidth; x += 6) if (t.getMaskPixel(x, y) > 200) n++; invalidate t; return n; })()")
    Invoke-Tjs "kag.tagHandlers.freeimage(%[layer:'0', page:'fore']), 1" | Out-Null
    if ($n -lt 1800) { throw "the SVG emblem, turned 30 degrees, drew $n opaque samples (2083 when whole)" }
    "SVG emblem drawn turned: $n opaque samples"
}

# After the transition demo: every transition's plugin (extrans, extNagano) loaded, or the demo
# showed crossfades in their place and passed
function Transition-Plugins {
    $missing = Invoke-Tjs "typeof global.KAGPluginTransitions == 'undefined' ? 'no KAGPluginTransitions' : (function() { var a = []; foreach(KAGPluginTransitions, function(k, v, d, a) { if (v != 'linked') a.add(k); }, a); return a.join(' '); })()"
    if ($missing) { throw "these transitions' plugin isn't loaded: $missing" }
    'extrans and extNagano loaded'
}

# ---------------------------------------------------------------------------------------
$exe = Join-Path $Kagex $(if ($IsWindows) { 'krkrz.exe' } else { 'krkrz' })
$argList = @('-datapath=savedata/', "-replfile=$chan") + $EngineArgs
Write-Host "== $Mode : $exe $($argList -join ' ')"
$script:proc = Start-Process -FilePath $exe -ArgumentList $argList -WorkingDirectory $Kagex -PassThru `
    -RedirectStandardOutput (Join-Path $Out 'stdout.txt') -RedirectStandardError (Join-Path $Out 'stderr.txt')

Step 'boot: REPL channel answers' {
    try { Invoke-Tjs '1' $BootTimeout | Out-Null }
    catch { Desktop-Shot 'boot-failure'; throw }
    'REPL channel up'
}
Step 'kag window created' {
    $sw = [Diagnostics.Stopwatch]::StartNew()
    while ((Invoke-Tjs 'typeof global.kag') -ne 'Object') {
        if ($sw.Elapsed.TotalSeconds -gt 60) {
            Desktop-Shot 'no-kag'
            $why = (Read-Log) -split "`r?`n" | Select-String -Pattern 'Failed to create SDL Window|GLES context is unavailable|Script exception raised' |
                   Select-Object -First 3 | ForEach-Object { $_.Line }
            throw "kag was never created: $($why -join ' / ')"
        }
        Start-Sleep -Milliseconds 500
    }
    'kag exists'
}
Step 'SDL window opened' {
    $bad = (Read-Log) -split "`r?`n" | Where-Object { $_ -match 'Failed to create SDL Window' } | Select-Object -First 1
    if ($bad) { throw $bad }
    'no window-creation error in the log'
}
Step 'load CI helpers' {
    # With a BOM, so the engine does not read it in the system code page
    $src = [IO.File]::ReadAllText((Join-Path $PSScriptRoot 'ci-helper.tjs'), [Text.Encoding]::UTF8)
    [IO.File]::WriteAllText((Join-Path $Kagex 'ci-helper.tjs'), $src, [Text.UTF8Encoding]::new($true))
    Invoke-Tjs "Scripts.execStorage(System.exePath + 'ci-helper.tjs')" | Out-Null
    $t = Invoke-Tjs 'typeof global.__ci_state'
    if ($t -ne 'Object') { throw "helpers not defined (typeof __ci_state = $t)" }
    'ok'
}
Step 'engine / plugin / font info' {
    $i = Invoke-Tjs '__ci_info()'
    Set-Content -Encoding utf8 (Join-Path $Out 'info.txt') $i
    ($i -split "`n" | Select-String 'platformTag|versionString|drawDevice|getClassNames|RichText|CSVParser|font MS Gothic|font Roboto') -join "`n"
}
Step 'logo -> title screen' {
    $s = Wait-State 'the title screen' $atTitle 90 {
        param($t) if ($t -gt 20 -and [int]$t % 5 -eq 0) { Invoke-Tjs '__ci_clickAt(960, 540)' | Out-Null }
    }
    Start-Sleep -Milliseconds 500
    $f = Shot 'title'
    try { Invoke-Tjs "__ci_piled(System.exePath + 'ci-out/title-layers.png')" | Out-Null } catch { Write-Host "piledCopy: $_" }
    Desktop-Shot 'title'
    "$f; buttons: $(Invoke-Tjs '__ci_buttons()')"
}
Step 'title: START -> demo menu' {
    $r = Click-Until 'start' 'the demo menu' $atMenu "kag.process('title.ks', '*gamestart')"
    Start-Sleep -Milliseconds 900
    "$r; $(Shot 'demo-menu'); $(Invoke-Tjs '__ci_selectCount()') choices"
}

if ($Plan -eq 'probe') {
    Step 'font probe' {
        $r = Invoke-Tjs "__ci_fontprobe(System.exePath + 'ci-out/fontprobe.png')" 120
        Set-Content -Encoding utf8 (Join-Path $Out 'fontprobe.txt') $r
        $r
    }
} elseif ($Plan -eq 'smoke') {
    Step 'demo: KAGEX layer' { Run-Demo 0 'layer' }
    Step 'vector: an SVG image draws' { Vector-Image }
    Step 'demo: World transitions' { Run-Demo 3 'transition' }
    Step 'transitions: their plugins loaded' { Transition-Plugins }
    Step 'demo: Effekseer effects' { Effect-Demo }
} else {
    $demos = 'layer', 'char', 'envlayer', 'transition', 'action', 'effect'
    for ($d = 0; $d -lt $demos.Count; $d++) {
        Step "demo $($d + 1): $($demos[$d]).ks" { Run-Demo $d $demos[$d] }
    }
}

# Words must not break across history lines: a line break between two letters that the
# scenario writes as one word ("over|lap") is a split, one it writes with a space is a wrap
Step 'history: no word split across lines' {
    $lines = @((Invoke-Tjs '__ci_histlines()') -split "`n")
    $src = (Get-ChildItem (Join-Path $Kagex 'data/scenario') -Filter *.ks | ForEach-Object { [IO.File]::ReadAllText($_.FullName, [Text.Encoding]::UTF8) }) -join "`n"
    $src = [regex]::Replace([regex]::Replace($src, '\[[^\]]*\]', ' '), '\s+', ' ')
    $bad = @(); $pairs = 0
    for ($i = 0; $i -lt $lines.Count - 1; $i++) {
        $a = [regex]::Match($lines[$i], '([A-Za-z]+)$').Groups[1].Value
        $b = [regex]::Match($lines[$i + 1], '^([A-Za-z]+)').Groups[1].Value
        if ($a -and $b) {
            $pairs++
            if ($src.Contains($a + $b) -and -not $src.Contains("$a $b")) { $bad += "[$($lines[$i])] / [$($lines[$i + 1])]" }
        }
    }
    Set-Content -Encoding utf8 (Join-Path $Out 'history-lines.txt') $lines
    if ($bad) { throw "split inside a word: $($bad -join ' ; ')" }
    "$($lines.Count) history lines; $pairs breaks between letters, none inside a word"
}

# In-game UI on char.ks: it uses [initscene], which adds the msg_* buttons (layer.ks clears them)
if ($Plan -ne 'probe') {
Step 'in game: message window + rich text' {
    Wait-State 'the demo menu' $atMenu 30 | Out-Null
    Start-Sleep -Milliseconds 900
    Invoke-Tjs '__ci_clickSelect(1)' | Out-Null
    Wait-State 'char.ks' { param($s) $s.storage -eq 'char.ks' -and $s.stable -eq '1' } 30 | Out-Null
    for ($k = 0; $k -lt 2; $k++) {
        Invoke-Tjs '__ci_clickAt(960, 400)' | Out-Null
        Start-Sleep -Milliseconds 500
        Wait-State 'a click wait' { param($s) $s.stable -eq '1' -and $s.queue -eq '0' } 20 | Out-Null
    }
    "$(Shot 'ingame'); $(Invoke-Tjs '__ci_richtext()'); buttons: $(Invoke-Tjs '__ci_buttons()')"
}
Step 'history log (msg_log)' {
    $r = Click-Until 'msg_log' 'the history log' { param($s) $s.history -eq '1' } 'kag.showHistory()' 10
    Start-Sleep -Milliseconds 600
    $f = Shot 'history'
    $b = RightClick-Back 'history closed' { param($s) $s.history -eq '0' } 'kag.hideHistory()'
    "$r; $f; closed by $b"
}
}

if ($Plan -eq 'full') {
    $inGame = { param($s) $s.storage -eq 'char.ks' -and $s.stable -eq '1' }
    Step 'save screen: save to slot 1' {
        $r = Click-Until 'msg_save' 'save.ks' { param($s) $s.storage -eq 'save.ks' -and $s.stable -eq '1' } "startSave()"
        Start-Sleep -Milliseconds 800
        $f1 = Shot 'save'
        Invoke-Tjs "__ci_click('save0')" | Out-Null
        Start-Sleep -Milliseconds 2500
        $f2 = Shot 'save-after-slot1'
        $bm = Invoke-Tjs '__ci_bookmarkFile(0)'
        $b = RightClick-Back 'back in the game' $inGame
        if ($bm -notmatch 'exists=1') { throw "$r; $f1; $f2; bookmark not written: $bm" }
        "$r; $f1; $f2; $bm; back by $b"
    }
    Step 'load screen (shows the slot 1 thumbnail)' {
        $r = Click-Until 'msg_load' 'load.ks' { param($s) $s.storage -eq 'load.ks' -and $s.stable -eq '1' } "startLoad()"
        Start-Sleep -Milliseconds 800
        $f = Shot 'load'
        $b = RightClick-Back 'back in the game' $inGame
        "$r; $f; back by $b"
    }
    Step 'config screen from the game' {
        $r = Click-Until 'msg_config' 'config.ks' { param($s) $s.storage -eq 'config.ks' -and $s.stable -eq '1' } "startConfig()"
        Start-Sleep -Milliseconds 800
        $f = Shot 'config-ingame'
        $b = RightClick-Back 'back in the game' $inGame
        "$r; $f; back by $b"
    }
    Step 'back to title' {
        Invoke-Tjs "kag.process('title.ks', '*start')" | Out-Null
        Wait-State 'the title screen' $atTitle 30 | Out-Null
        'kag.process(title.ks, *start)'
    }
    foreach ($t in @(
            @{ Button = 'config';   Storage = 'config.ks'  },
            @{ Button = 'extra';    Storage = 'cgmode.ks'  },
            @{ Button = 'continue'; Storage = 'load.ks'    })) {
        Step "title: $($t.Button)" {
            Start-Sleep -Milliseconds 600
            $st = $t.Storage
            $r = Click-Until $t.Button $st { param($s) $s.storage -eq $st -and $s.stable -eq '1' } '' 15
            Start-Sleep -Milliseconds 800
            $f = Shot "title-$($t.Button)"
            $b = RightClick-Back 'the title screen' $atTitle
            "$r; $f; back by $b"
        }
    }
}

if ($Plan -eq 'full') {
    # Window <-> full screen goes through SetWindowControlMenu, which throws on this engine
    Step 'config: Window mode, then Fullscreen again' {
        Wait-State 'the title screen' $atTitle 20 | Out-Null
        Start-Sleep -Milliseconds 600
        Click-Until 'config' 'config.ks' { param($s) $s.storage -eq 'config.ks' -and $s.stable -eq '1' } '' 15 | Out-Null
        Start-Sleep -Milliseconds 600
        $geo = "'fullScreen=' + kag.fullScreen + ' inner=' + kag.innerWidth + 'x' + kag.innerHeight + ' window=' + kag.left + ',' + kag.top + ' ' + kag.width + 'x' + kag.height + ' zoom=' + kag.zoomNumer + '/' + kag.zoomDenom"
        $before = Invoke-Tjs $geo
        Invoke-Tjs "__ci_click('config_window')" | Out-Null
        Start-Sleep -Seconds 3
        $win = Invoke-Tjs $geo
        Desktop-Shot 'windowed'
        $f1 = Shot 'config-windowed'
        Invoke-Tjs "__ci_click('config_fullscreen')" | Out-Null
        Start-Sleep -Seconds 3
        $full = Invoke-Tjs $geo
        Desktop-Shot 'fullscreen-again'
        $f2 = Shot 'config-fullscreen-again'
        $b = RightClick-Back 'the title screen' $atTitle
        $notices = @((Read-Log) -split "`r?`n" | Where-Object { $_ -match 'Failed to transition' } | Select-Object -Skip 1)
        $msg = "before: $before; after Window: $win; after Fullscreen: $full; $f1; $f2; back by $b"
        if ($win -notmatch 'fullScreen=0' -or $full -notmatch 'fullScreen=1' -or $notices.Count) { throw "$msg; log: $($notices -join ' / ')" }
        $msg
    }
    Step 'edge/shadow: engine vs richtext' {
        $r = Invoke-Tjs "__ci_effectprobe(System.exePath + 'ci-out/effectprobe.png')" 60
        if ($r -ne 'ok') { throw $r }
        'effectprobe.png'
    }
    Step 'title: EXIT' {
        Start-Sleep -Milliseconds 600
        $how = Invoke-Tjs "__ci_click('exit')"
        if ($script:proc.WaitForExit(8000)) { return "clicked exit ($how); engine exited, code $($script:proc.ExitCode)" }
        Desktop-Shot 'exit-asks'
        $f = Shot 'exit-asks'
        # The dialog's focus starts on No: Left moves it to Yes, Enter confirms
        Invoke-Tjs '__ci_key(37)' 10 | Out-Null
        Start-Sleep -Milliseconds 300
        Invoke-Tjs '__ci_key(13)' 10 | Out-Null
        if ($script:proc.WaitForExit(8000)) { return "clicked exit ($how); it asked first ($f); Left+Enter chose Yes; exit code $($script:proc.ExitCode)" }
        $f2 = Shot 'exit-after-yes'
        throw "clicked exit ($how); still running after the prompt and Left+Enter (see $f, $f2)"
    }
}

Step 'quit' {
    try { Invoke-Tjs 'System.terminate(0)' 5 | Out-Null } catch {}
    if (-not $script:proc.WaitForExit(20000)) { throw 'engine did not exit within 20s of System.terminate(0)' }
    "exit code $($script:proc.ExitCode)"
}

# ---------------------------------------------------------------------------------------
if (-not $script:proc.HasExited) {
    Desktop-Shot 'at-kill'
    Stop-Process -Id $script:proc.Id -Force -ErrorAction SilentlyContinue
    $script:steps.Add([pscustomobject]@{ Step = 'cleanup'; Result = 'FAIL'; Sec = 0; Note = 'engine still running at the end; killed' })
} elseif ($script:proc.ExitCode -ne 0) {
    $script:steps.Add([pscustomobject]@{ Step = 'exit code'; Result = 'FAIL'; Sec = 0; Note = ('0x{0:X8}' -f $script:proc.ExitCode) })
}

# Script exceptions in the engine log. Plugins.link of optional plugins that this build
# does not provide throws inside kagex's try/catch; those are listed separately.
$optional = 'layerExDraw|gfxEffect|flashPlayer|AlphaMovie|windowEx'
$lines = (Read-Log) -split "`r?`n"
$excs = @(); $expected = @()
for ($n = 0; $n -lt $lines.Count; $n++) {
    if ($lines[$n] -match 'An exception occured at (.+?)\[') {
        $where = $Matches[1]
        $ctx = ($lines[$n..([Math]::Min($n + 3, $lines.Count - 1))] -join "`n")
        if ($ctx -match "Plugins\.link\(`"plugin/($optional)\.dll`"\)") { $expected += "$where (Plugins.link $($Matches[1]).dll)" }
        elseif ($where -match 'kagenvironment\.tjs\(\d+\)' -and $lines[$n] -match 'loadBGFromCache') {
            # KAGEnvStage tries the time-of-day background (bg01_02...) and falls back to bg01_01 + colour correction
            $expected += "$where (loadBGFromCache: time-of-day background missing, falls back by design)"
        }
        else {
            $msg = ($lines[$n..([Math]::Min($n + 40, $lines.Count - 1))] | Where-Object { $_ -match 'Script exception raised|Error|does not exist|trace :' } | Select-Object -First 3) -join ' / '
            $excs += "$where :: $msg"
        }
    }
}
$warn = $lines | Where-Object { $_ -match '^\S+ ! .*(Fail|fail|error|Error)' -and $_ -notmatch 'Loading configuration file' }
@("Unexpected exceptions:", $excs, "", "Expected, caught by kagex:", $expected, "", "Engine warnings:", $warn) |
    Set-Content -Encoding utf8 (Join-Path $Out 'exceptions.txt')
$script:steps.Add([pscustomobject]@{ Step = 'engine log'; Result = $(if ($excs.Count) { 'FAIL' } else { 'PASS' }); Sec = 0
    Note = "$($excs.Count) unexpected script exception(s)$(if ($excs.Count) { ': ' + (($excs | Select-Object -Unique) -join ' | ') }); $($expected.Count) expected caught exception(s) (optional plugins, time-of-day backgrounds); $($warn.Count) engine warning(s); $script:shotFails failed capture(s)" })
Get-ChildItem $save -ErrorAction SilentlyContinue | Select-Object Name, Length | Format-Table | Out-String | Set-Content (Join-Path $Out 'savedata.txt')
Get-ChildItem $shotDir -File -ErrorAction SilentlyContinue | Move-Item -Destination $Out -Force

$md = @("Engine args: ``$($argList -join ' ')``", '', '| Step | Result | s | Note |', '|---|---|---|---|')
foreach ($s in $script:steps) {
    $note = ($s.Note -replace '\r?\n', ' / ' -replace '\|', '\|')
    if ($note.Length -gt 600) { $note = $note.Substring(0, 600) + '…' }
    $md += "| $($s.Step) | $($s.Result) | $($s.Sec) | $note |"
}
$md | Set-Content -Encoding utf8 (Join-Path $Out 'steps.md')
$md | Write-Host
