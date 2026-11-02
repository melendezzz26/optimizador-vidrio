Add-Type -AssemblyName System.Drawing

$figureDirectory = Join-Path $PSScriptRoot 'figures'
New-Item -ItemType Directory -Force -Path $figureDirectory | Out-Null
$resultPath = Join-Path $PSScriptRoot '..\..\..\docs\evidence\sprint-02\SP-004\benchmark-results\sp004_block_v2_results.csv'
$resultRows = Import-Csv -LiteralPath $resultPath
$fontTitle = [System.Drawing.Font]::new('Arial', 20, [System.Drawing.FontStyle]::Bold)
$fontLabel = [System.Drawing.Font]::new('Arial', 14, [System.Drawing.FontStyle]::Bold)
$fontBody = [System.Drawing.Font]::new('Arial', 11, [System.Drawing.FontStyle]::Regular)
$black = [System.Drawing.Pen]::new([System.Drawing.Color]::Black, 2)
$grayPen = [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(100, 100, 100), 2)
$lightBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(220, 220, 220))
$midBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(150, 150, 150))
$whiteBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::White)
$textBrush = [System.Drawing.SolidBrush]::new([System.Drawing.Color]::Black)

function Draw-Triangle($graphics, $x, $y, $size, $inverted, $brush) {
    if ($inverted) {
        $points = [System.Drawing.Point[]]@([System.Drawing.Point]::new($x + $size, $y + $size), [System.Drawing.Point]::new($x, $y + $size), [System.Drawing.Point]::new($x + $size, $y))
    } else {
        $points = [System.Drawing.Point[]]@([System.Drawing.Point]::new($x, $y), [System.Drawing.Point]::new($x + $size, $y), [System.Drawing.Point]::new($x, $y + $size))
    }
    $graphics.FillPolygon($brush, $points)
    $graphics.DrawPolygon($black, $points)
}

$demo = [System.Drawing.Bitmap]::new(1500, 720)
$graphics = [System.Drawing.Graphics]::FromImage($demo)
$graphics.Clear([System.Drawing.Color]::White)
$graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$graphics.DrawString('DEMO DIDÁCTICA — NO PERTENECE AL BENCHMARK OFICIAL', $fontTitle, $textBrush, 32, 24)
$graphics.DrawString('Figura conceptual, no resultado experimental.', $fontBody, $textBrush, 34, 62)
$graphics.DrawString('ANTES: piezas independientes', $fontLabel, $textBrush, 40, 110)
Draw-Triangle $graphics 70 180 180 $false $midBrush
Draw-Triangle $graphics 330 180 180 $true $lightBrush
$graphics.DrawString('A', $fontLabel, $textBrush, 145, 370)
$graphics.DrawString('B', $fontLabel, $textBrush, 405, 370)
$graphics.DrawString('Dos triángulos convexos de 10 × 10 mm', $fontBody, $textBrush, 38, 420)

$graphics.DrawString('BLOQUE TEMPORAL', $fontLabel, $textBrush, 555, 110)
$graphics.DrawString('Composición raster densa (1.0)', $fontBody, $textBrush, 555, 145)
Draw-Triangle $graphics 590 205 240 $false $midBrush
Draw-Triangle $graphics 610 205 240 $true $lightBrush
$graphics.DrawRectangle($grayPen, 589, 204, 261, 241)
$graphics.DrawString('A y B conservan ID, giro y offset propio', $fontBody, $textBrush, 555, 480)

$graphics.DrawString('COLOCACIÓN SOBRE FUENTE', $fontLabel, $textBrush, 1010, 110)
$graphics.DrawRectangle($black, 1010, 180, 414, 230)
$graphics.FillRectangle($midBrush, 1012, 182, 160, 226)
$graphics.DrawRectangle($black, 1012, 182, 160, 226)
Draw-Triangle $graphics 1170 182 230 $false $midBrush
Draw-Triangle $graphics 1190 182 230 $true $lightBrush
$graphics.DrawString('Plancha 18 × 10 mm', $fontBody, $textBrush, 1010, 430)
$graphics.DrawString('Rectángulo 7 × 10 + pareja triangular', $fontBody, $textBrush, 1010, 458)
$graphics.DrawString('La salida contiene dos placements originales.', $fontBody, $textBrush, 1010, 486)
$demo.Save((Join-Path $figureDirectory 'block-packing-demo.png'), [System.Drawing.Imaging.ImageFormat]::Png)
$graphics.Dispose()
$demo.Dispose()

function Draw-Chart($fileName, $title, $valueSelector, $maxValue, $logScale = $false, $percent = $false) {
    $width = 1700
    $height = 900
    $bitmap = [System.Drawing.Bitmap]::new($width, $height)
    $g = [System.Drawing.Graphics]::FromImage($bitmap)
    $g.Clear([System.Drawing.Color]::White)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.DrawString($title, $fontTitle, $textBrush, 45, 26)
    $plotLeft, $plotTop, $plotWidth, $plotHeight = 120, 110, 1510, 630
    $g.DrawLine($black, $plotLeft, $plotTop + $plotHeight, $plotLeft + $plotWidth, $plotTop + $plotHeight)
    $caseNames = @('EXP-SMALL-001', 'EXP-MEDIUM-001', 'EXP-COMPLEX-001', 'BLOCK-DISCRIMINANT-001', 'BLOCK-V2-OBLIQUE-TRIANGLES-001', 'BLOCK-V2-MIXED-TRIANGLE-CIRCLE-001')
    $methodNames = @('FF', 'BF', 'WF', 'Pair-Block-v2')
    $caseWidth = [int]($plotWidth / $caseNames.Count)
    $barWidth = 36
    $gap = 8
    for ($tick = 0; $tick -le 4; $tick++) {
        $fraction = $tick / 4
        $y = $plotTop + $plotHeight - [int]($plotHeight * $fraction)
        $g.DrawLine([System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(220,220,220), 1), $plotLeft, $y, $plotLeft + $plotWidth, $y)
        $labelValue = if ($logScale) { [Math]::Pow($maxValue, $fraction) } elseif ($percent) { 100 * $fraction } else { $maxValue * $fraction }
        $suffix = if ($percent) { '%' } elseif ($logScale) { ' ms' } else { '' }
        $g.DrawString([string]::Format('{0:0.##}{1}', $labelValue, $suffix), $fontBody, $textBrush, 28, $y - 10)
    }
    $brushes = @($black, $grayPen, [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(145,145,145), 2), [System.Drawing.Pen]::new([System.Drawing.Color]::FromArgb(60,60,60), 2))
    $fills = @($midBrush, $whiteBrush, $lightBrush, [System.Drawing.SolidBrush]::new([System.Drawing.Color]::FromArgb(185,185,185)))
    for ($caseIndex = 0; $caseIndex -lt $caseNames.Count; $caseIndex++) {
        $caseName = $caseNames[$caseIndex]
        for ($methodIndex = 0; $methodIndex -lt $methodNames.Count; $methodIndex++) {
            $methodName = $methodNames[$methodIndex]
            $item = $resultRows | Where-Object { $_.case -eq $caseName -and $_.method -eq $methodName } | Select-Object -First 1
            $raw = [double](& $valueSelector $item)
            $fraction = if ($logScale) { [Math]::Log([Math]::Max(1, $raw), $maxValue) } else { if ($maxValue -gt 0) { $raw / $maxValue } else { 0 } }
            $barHeight = [Math]::Max(1, [int]($plotHeight * $fraction))
            $x = $plotLeft + $caseIndex * $caseWidth + 26 + $methodIndex * ($barWidth + $gap)
            $y = $plotTop + $plotHeight - $barHeight
            $rectangle = [System.Drawing.Rectangle]::new($x, $y, $barWidth, $barHeight)
            $g.FillRectangle($fills[$methodIndex], $rectangle)
            $g.DrawRectangle($brushes[$methodIndex], $rectangle)
            $g.DrawString([string]::Format('{0:0.##}', $raw), $fontBody, $textBrush, $x - 2, $y - 25)
        }
        $caption = $caseName.Replace('EXP-', '').Replace('BLOCK-DISCRIMINANT-', 'DISC-').Replace('BLOCK-V2-OBLIQUE-TRIANGLES-001', 'OBL-TRI').Replace('BLOCK-V2-MIXED-TRIANGLE-CIRCLE-001', 'MIXED')
        $g.DrawString($caption, $fontBody, $textBrush, $plotLeft + $caseIndex * $caseWidth + 20, $plotTop + $plotHeight + 20)
    }
    for ($methodIndex = 0; $methodIndex -lt $methodNames.Count; $methodIndex++) {
        $x = 140 + $methodIndex * 270
        $g.FillRectangle($fills[$methodIndex], $x, 825, 28, 22)
        $g.DrawRectangle($brushes[$methodIndex], $x, 825, 28, 22)
        $g.DrawString($methodNames[$methodIndex], $fontBody, $textBrush, $x + 38, 824)
    }
    $bitmap.Save((Join-Path $figureDirectory $fileName), [System.Drawing.Imaging.ImageFormat]::Png)
    $g.Dispose()
    $bitmap.Dispose()
}

Draw-Chart 'utilization-by-method.png' 'Aprovechamiento por caso y método' { param($row) [double]$row.utilization_pct } 100 $false $true
Draw-Chart 'sources-by-method.png' 'Fuentes utilizadas por caso y método' { param($row) ([int]$row.remnants_used + [int]$row.sheets_used) } 8
Draw-Chart 'runtime-by-method.png' 'Tiempo total por caso y método (escala logarítmica)' { param($row) [double]$row.runtime_ms } 10000 $true

$fontTitle.Dispose()
$fontLabel.Dispose()
$fontBody.Dispose()
$black.Dispose()
$grayPen.Dispose()
$lightBrush.Dispose()
$midBrush.Dispose()
$whiteBrush.Dispose()
$textBrush.Dispose()
Write-Output "Figuras escritas en $figureDirectory"
