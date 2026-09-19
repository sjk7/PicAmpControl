#!/usr/bin/env pwsh
<#
.SYNOPSIS
    Master build script for EasyEDA Pro schematic generation and visualization
.DESCRIPTION
    Orchestrates the full workflow:
    1. Generate component specs from Python generator
    2. Render SVG visualization
    3. Validate layout and design rules
    4. Display results
.PARAMETER Watch
    Enable continuous watch mode (auto-regenerate on changes)
.PARAMETER ValidateOnly
    Skip generation, only run validation
.PARAMETER OpenSVG
    Open SVG in VS Code Insiders after generation
.EXAMPLE
    .\build_schematic.ps1
    .\build_schematic.ps1 -Watch
    .\build_schematic.ps1 -ValidateOnly
    .\build_schematic.ps1 -OpenSVG
#>

param(
    [switch]$Watch,
    [switch]$ValidateOnly,
    [switch]$OpenSVG
)

$ErrorActionPreference = "Stop"

function Write-Step {
    param([string]$Message)
    Write-Host "`n" -NoNewline
    Write-Host "▶ $Message" -ForegroundColor Cyan -BackgroundColor Black
}

function Write-Success {
    param([string]$Message)
    Write-Host "  [OK] $Message" -ForegroundColor Green
}

function Write-ErrorMsg {
    param([string]$Message)
    Write-Host "  [ERROR] $Message" -ForegroundColor Red
    exit 1
}

Write-Host @"

================================================================================
  PICAMPCONTROL SCHEMATIC BUILDER
  
  Generates EasyEDA Pro schematics with SVG visualization and validation
================================================================================

"@ -ForegroundColor Magenta

# Check Python
Write-Step "Checking dependencies..."
try {
    $pythonVersion = python --version 2>&1
    Write-Success "Python: $pythonVersion"
} catch {
    Write-ErrorMsg "Python not found. Install Python 3.8+ and add to PATH."
}

if ($ValidateOnly) {
    Write-Step "Validating existing schematic..."
    python tools/visual_validator.py
    exit 0
}

# Generate specifications
Write-Step "Generating component specifications..."
try {
    python tools/easyeda_pro_generator.py | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "Generator failed"
    }
    Write-Success "Specifications generated"
} catch {
    Write-ErrorMsg "Generation failed: $_"
}

# Render SVG
Write-Step "Rendering SVG visualization..."
try {
    python tools/svg_renderer.py | Out-Null
    if ($LASTEXITCODE -ne 0) {
        Write-ErrorMsg "SVG rendering failed"
    }
    Write-Success "SVG rendered"
} catch {
    Write-ErrorMsg "SVG rendering failed: $_"
}

# Validate
Write-Step "Running design validation..."
try {
    $output = python tools/visual_validator.py 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Success "Validation passed"
    } else {
        Write-Host $output
        Write-Host "  [WARN] Validation warnings/errors found (see above)" -ForegroundColor Yellow
    }
} catch {
    Write-ErrorMsg "Validation failed: $_"
}

# Open SVG if requested
if ($OpenSVG) {
    Write-Step "Opening SVG in VS Code Insiders..."
    try {
        code-insiders out/picampcontrol_schematic.svg
        Write-Success "SVG opened"
    } catch {
        Write-Host "  [WARN] Could not open SVG. Open manually: code-insiders out/picampcontrol_schematic.svg" -ForegroundColor Yellow
    }
}

# Watch mode
if ($Watch) {
    Write-Step "Starting watch mode (Ctrl+C to stop)..."
    Write-Host "`n  Monitoring for changes to:" -ForegroundColor Gray
    Write-Host "    • tools/easyeda_pro_generator.py" -ForegroundColor Gray
    Write-Host "    • out/picampcontrol_easyeda_agent.json" -ForegroundColor Gray
    Write-Host "`n" -NoNewline
    
    python tools/watch_and_render.py
}

Write-Host @"

================================================================================
  BUILD COMPLETE
================================================================================

Outputs:
  * out/picampcontrol_easyeda_agent.json       (EasyEDA Agent format)
  * out/picampcontrol_easyeda_copilot.json     (EasyEDA Copilot format)
  * out/picampcontrol_schematic.svg            (Visual preview)

Next steps:
  1. Review SVG: code-insiders out/picampcontrol_schematic.svg
  2. Watch mode: .\build_schematic.ps1 -Watch
  3. Export to EasyEDA Pro: easyeda sch create --spec out/picampcontrol_easyeda_agent.json

Documentation: docs/hardware/SCHEMATIC_WORKFLOW.md

================================================================================
"@ -ForegroundColor Magenta
