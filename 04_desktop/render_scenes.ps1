# Renders static Tkinter backgrounds from the original inline SVG scene.
# Run from the project root: powershell -ExecutionPolicy Bypass -File 04_desktop/render_scenes.ps1
$ErrorActionPreference = 'Stop'
$root = Split-Path -Parent $PSScriptRoot
$assetDir = Join-Path $PSScriptRoot 'assets'
New-Item -ItemType Directory -Force $assetDir | Out-Null
$html = Get-Content (Join-Path $root 'index.html') -Raw
$start = $html.IndexOf('<svg class="scene"')
$end = $html.IndexOf('</svg>', $start) + 6
if ($start -lt 0 -or $end -lt 6) { throw 'Could not locate the source SVG scene in index.html.' }
$source = $html.Substring($start, $end - $start)
$source = $source.Replace('<svg class="scene"', '<svg class="scene" width="1440" height="660"')
$style = '<style>#player-trolley,#beam-1,#beam-2,#beam-3,#worker-walk,#auto-trolley,#auto-beam,#bird-strike,#crash-overlay,#debris,#target-1,#target-2,#target-3,#target-label-1,#target-label-2,#target-label-3,#tower-bolts{display:none!important}</style>'
$source = $source.Replace('<title id="scene-title">', "$style<title id=`"scene-title`">")
$layouts = @(
    @{ Rows = @(458, 376, 294, 261) },
    @{ Rows = @(458, 382, 300, 261) },
    @{ Rows = @(458, 398, 318, 261) },
    @{ Rows = @(458, 385, 335, 261) },
    @{ Rows = @(458, 400, 325, 261) }
)
$edge = 'C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe'
if (-not (Test-Path -LiteralPath $edge)) { throw 'Microsoft Edge was not found to render the static scene assets.' }
foreach ($i in 0..4) {
    $rows = $layouts[$i].Rows
    $cross = ($rows | ForEach-Object { "M617 $_ h206" }) -join ' '
    $segments = @()
    for ($j = 0; $j -lt $rows.Length - 1; $j++) {
        $lower = $rows[$j]
        $upper = $rows[$j + 1]
        $segments += "M625 $lower L815 $upper"
        $segments += "M815 $lower L625 $upper"
    }
    $brace = $segments -join ' '
    $variant = $source
    $variant = [regex]::Replace($variant, '(<path id="tower-crossbeams" )d="[^"]+"', [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $m.Groups[1].Value + 'd="' + $cross + '"' })
    $variant = [regex]::Replace($variant, '(<path id="tower-braces" )d="[^"]+"', [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $m.Groups[1].Value + 'd="' + $brace + '"' })
    $variant = [regex]::Replace($variant, '(<path id="tower-gold-braces" )d="[^"]+"', [System.Text.RegularExpressions.MatchEvaluator]{ param($m) $m.Groups[1].Value + 'd="' + $brace + '"' })
    $svgPath = Join-Path $assetDir "scene-level-$($i + 1).svg"
    [System.IO.File]::WriteAllText($svgPath, $variant, [System.Text.UTF8Encoding]::new($false))
    foreach ($percent in @(60, 70, 80, 90, 100)) {
        $width = [int](1440 * $percent / 100)
        $height = [int](660 * $percent / 100)
        $scaled = $variant.Replace('<svg class="scene" width="1440" height="660"', "<svg class=`"scene`" width=`"$width`" height=`"$height`"")
        $renderPath = Join-Path $assetDir 'scene-render.svg'
        $pngPath = Join-Path $assetDir "scene-level-$($i + 1)-$percent.png"
        [System.IO.File]::WriteAllText($renderPath, $scaled, [System.Text.UTF8Encoding]::new($false))
        $uri = ([System.Uri](Get-Item -LiteralPath $renderPath).FullName).AbsoluteUri
        & $edge --headless=old --no-sandbox --disable-gpu --disable-gpu-sandbox --disable-software-rasterizer --disable-features=VizDisplayCompositor --hide-scrollbars --force-device-scale-factor=1 --window-size="$width,$height" --user-data-dir="$(Join-Path $assetDir 'edge-profile')" --screenshot="$pngPath" $uri | Out-Null
        if (-not (Test-Path -LiteralPath $pngPath)) { throw "Edge did not render $pngPath" }
    }
}
Remove-Item -LiteralPath (Join-Path $assetDir 'scene-render.svg')
