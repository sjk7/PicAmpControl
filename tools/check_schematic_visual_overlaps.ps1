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
    $rectLeft = [double]$rect.x
    $rectTop = [double]$rect.y
    $rectRight = $rectLeft + [double]$rect.width
    $rectBottom = $rectTop + [double]$rect.height
    if ($rect.width -gt 100 -or $rect.height -gt 100) { continue }

    foreach ($item in $texts) {
        if ($item.Text -notmatch '\s' -and $item.Text.Length -lt 8) { continue }
        $insideBody = $item.Right -gt $rectLeft -and $item.Left -lt $rectRight -and
            $item.Bottom -gt $rectTop -and $item.Top -lt $rectBottom
        if ($insideBody) {
            $overlaps += "'$($item.Text)' overlaps a symbol body rectangle"
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