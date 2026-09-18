param(
    [Parameter(Mandatory = $true)]
    [string] $SvgPath
)

$ErrorActionPreference = 'Stop'
[xml] $svg = Get-Content -LiteralPath $SvgPath -Raw
$namespaces = New-Object System.Xml.XmlNamespaceManager($svg.NameTable)
$namespaces.AddNamespace('svg', 'http://www.w3.org/2000/svg')
$texts = @()

foreach ($node in $svg.SelectNodes('//svg:text', $namespaces)) {
    $text = ($node.InnerText -replace '\s+', ' ').Trim()
    if ([string]::IsNullOrWhiteSpace($text)) { continue }

    $x = [double]$node.x
    $y = [double]$node.y
    $fontSize = if ($node.'font-size') { [double]$node.'font-size' } else { 1.27 }
    $width = if ($node.textLength) { [double]$node.textLength } else { $text.Length * $fontSize * 0.55 }

    switch ($node.'text-anchor') {
        'middle' { $left = $x - ($width / 2); $right = $x + ($width / 2) }
        'end' { $left = $x - $width; $right = $x }
        default { $left = $x; $right = $x + $width }
    }

    $texts += [pscustomobject]@{
        Text = $text
        Left = $left
        Right = $right
        Top = $y - $fontSize
        Bottom = $y + ($fontSize * 0.25)
    }
}

$overlaps = @()
for ($first = 0; $first -lt $texts.Count; $first++) {
    for ($second = $first + 1; $second -lt $texts.Count; $second++) {
        $a = $texts[$first]
        $b = $texts[$second]
        if ($a.Right -le $b.Left -or $b.Right -le $a.Left -or
            $a.Bottom -le $b.Top -or $b.Bottom -le $a.Top) { continue }
        if ($a.Text -eq $b.Text -and
            [math]::Abs($a.Left - $b.Left) -lt 0.01 -and
            [math]::Abs($a.Top - $b.Top) -lt 0.01) { continue }
        $overlaps += "'$($a.Text)' overlaps '$($b.Text)'"
    }
}

# Catch long free-text annotations placed on top of a symbol body. Short
# pin names and fields are handled by the text-to-text and pin checks; a
# descriptive annotation inside a component rectangle is always suspect.
foreach ($rect in $svg.SelectNodes('//svg:rect', $namespaces)) {
    $style = $rect.ParentNode.style
    if (-not $style -or $style -notmatch '#840000') { continue }
    $clearance = 0.5
    $rectLeft = [double]$rect.x - $clearance
    $rectTop = [double]$rect.y - $clearance
    $rectRight = [double]$rect.x + [double]$rect.width + $clearance
    $rectBottom = [double]$rect.y + [double]$rect.height + $clearance
    if ($rect.width -gt 100 -or $rect.height -gt 100) { continue }

    foreach ($item in $texts) {
        $isPinToken = $item.Text -match '^(\d+|[+-]|B[0-2]|VDD|VSS|MCLR|RE3|R[ABC]\d(?:/.*)?|RC\d(?:/.*)?)$'
        if ($isPinToken) { continue }
        $insideBody = $item.Right -gt $rectLeft -and $item.Left -lt $rectRight -and
            $item.Bottom -gt $rectTop -and $item.Top -lt $rectBottom
        if ($insideBody) {
            $overlaps += "'$($item.Text)' overlaps a symbol body rectangle"
        }
        $isConnectorField = $item.Text -match '^(J\d+|FAN|LCD|PTT|ENC|TX|SWR|ADC|NTC)$'
        $nearConnectorBody = $isConnectorField -and
            $item.Right -gt ($rectLeft - 8) -and $item.Left -lt ($rectRight + 8) -and
            $item.Bottom -gt ($rectTop - 5) -and $item.Top -lt ($rectBottom + 5)
        if ($nearConnectorBody) {
            $overlaps += "'$($item.Text)' is too close to a connector body"
        }
    }
}

foreach ($circle in $svg.SelectNodes('//svg:circle', $namespaces)) {
    $style = $circle.ParentNode.style
    if (-not $style -or $style -notmatch '#840000') { continue }
    $clearance = 0.5
    $circleLeft = [double]$circle.cx - [double]$circle.r - $clearance
    $circleTop = [double]$circle.cy - [double]$circle.r - $clearance
    $circleRight = [double]$circle.cx + [double]$circle.r + $clearance
    $circleBottom = [double]$circle.cy + [double]$circle.r + $clearance

    foreach ($item in $texts) {
        $isPinToken = $item.Text -match '^(\d+|[+-]|B[0-2]|VDD|VSS|MCLR|RE3|R[ABC]\d(?:/.*)?|RC\d(?:/.*)?)$'
        if ($isPinToken) { continue }
        $nearBody = $item.Right -gt $circleLeft -and $item.Left -lt $circleRight -and
            $item.Bottom -gt $circleTop -and $item.Top -lt $circleBottom
        if ($nearBody) {
            $overlaps += "'$($item.Text)' overlaps a symbol body circle"
        }
    }
}

# Check visible text against short rendered wire/graphic segments. Long page
# frames are ignored; local pin and connection segments are not.
foreach ($path in $svg.SelectNodes('//svg:path', $namespaces)) {
    $style = ($path.style, $path.ParentNode.style | Where-Object { $_ }) -join ' '
    if ($style -notmatch '#840000') { continue }
    $numbers = [regex]::Matches($path.d, '[-+]?\d*\.?\d+') | ForEach-Object { [double]$_.Value }
    for ($index = 0; $index + 3 -lt $numbers.Count; $index += 2) {
        $x1 = $numbers[$index]; $y1 = $numbers[$index + 1]
        $x2 = $numbers[$index + 2]; $y2 = $numbers[$index + 3]
        if ([math]::Abs($x2 - $x1) + [math]::Abs($y2 - $y1) -gt 20) { continue }
        $left = [math]::Min($x1, $x2) - 0.25
        $right = [math]::Max($x1, $x2) + 0.25
        $top = [math]::Min($y1, $y2) - 0.25
        $bottom = [math]::Max($y1, $y2) + 0.25
        foreach ($item in $texts) {
            $isPinToken = $item.Text -match '^(\d+|[+-]|B[0-2]|VDD|VSS|MCLR|RE3|R[ABC]\d(?:/.*)?|RC\d(?:/.*)?)$'
            if ($isPinToken) { continue }
            if ($item.Right -gt $left -and $item.Left -lt $right -and
                $item.Bottom -gt $top -and $item.Top -lt $bottom) {
                $overlaps += "'$($item.Text)' overlaps a rendered wire segment"
            }
        }
    }
}

# A4 title block and its reserved drawing area.
$titleBlock = @{ Left = 177.0; Top = 166.0; Right = 285.0; Bottom = 198.0 }
foreach ($item in $texts) {
    $isHeaderOrSheetText = $item.Text -match '^(J\d|LCD|PTT|ENC|TX|SWR|ADC|FAN|ANALOG|SENSE|band_change)'
    $touchesTitleBlock = $item.Right -gt $titleBlock.Left -and
        $item.Left -lt $titleBlock.Right -and
        $item.Bottom -gt $titleBlock.Top -and
        $item.Top -lt $titleBlock.Bottom
    if ($isHeaderOrSheetText -and $touchesTitleBlock) {
        $overlaps += "'$($item.Text)' enters the reserved title-block area"
    }
}

if ($overlaps.Count -gt 0) {
    Write-Error ("Visual overlap check failed with {0} collision(s):`n{1}" -f $overlaps.Count, ($overlaps -join "`n"))
    exit 1
}

Write-Host 'Visual overlap check passed.'
exit 0