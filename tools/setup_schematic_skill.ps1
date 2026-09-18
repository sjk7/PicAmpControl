<#
.SYNOPSIS
    Sets up the KiCad schematic-design skill and its MCP server for this workspace.
.DESCRIPTION
    Idempotent: safe to re-run any time, including while the MCP server is
    already running in VS Code. Every step checks current state first and
    skips work that is already done instead of failing.
#>

$ErrorActionPreference = 'Stop'
$repoRoot = Split-Path -Parent $PSScriptRoot
Push-Location $repoRoot

function Write-Step($message) {
    Write-Host "==> $message" -ForegroundColor Cyan
}

function Write-Ok($message) {
    Write-Host "    OK: $message" -ForegroundColor Green
}

function Write-Skip($message) {
    Write-Host "    skip: $message" -ForegroundColor DarkGray
}

try {
    # 1. Node.js / npx (required by the `skills` CLI installer)
    Write-Step "Checking Node.js"
    $node = Get-Command node -ErrorAction SilentlyContinue
    if (-not $node) {
        throw "Node.js not found on PATH. Install it first (e.g. 'winget install -e --id OpenJS.NodeJS.LTS'), then re-run this script."
    }
    Write-Ok "node $(node --version)"

    # 2. schematic-design skill
    Write-Step "Checking schematic-design skill"
    $skillPath = Join-Path $repoRoot '.agents\skills\schematic-design\SKILL.md'
    if (Test-Path $skillPath) {
        Write-Skip "already installed at .agents\skills\schematic-design"
    } else {
        Write-Host "    installing productofamerica/mcp-server-kicad@schematic-design ..."
        npx --yes skills add productofamerica/mcp-server-kicad --skill schematic-design --agent github-copilot --copy -y
        if ($LASTEXITCODE -ne 0) {
            throw "skills add failed with exit code $LASTEXITCODE"
        }
        Write-Ok "skill installed"
    }

    # 3. uv / uvx (required to launch the mcp-server-kicad package)
    Write-Step "Checking uv/uvx"
    $uvx = Get-Command uvx -ErrorAction SilentlyContinue
    if (-not $uvx) {
        $userScripts = Join-Path $env:APPDATA 'Python\Python314\Scripts'
        $candidate = Join-Path $userScripts 'uvx.exe'
        if (Test-Path $candidate) {
            $uvx = Get-Item $candidate
        }
    }
    if (-not $uvx) {
        Write-Host "    uvx not found, installing uv via pip ..."
        python -m pip install --user uv
        if ($LASTEXITCODE -ne 0) {
            throw "pip install uv failed with exit code $LASTEXITCODE"
        }
        $userScripts = Join-Path $env:APPDATA 'Python\Python314\Scripts'
        $candidate = Join-Path $userScripts 'uvx.exe'
        if (-not (Test-Path $candidate)) {
            throw "uv installed but uvx.exe not found at $candidate. Locate it manually and update .vscode\mcp.json."
        }
        $uvx = Get-Item $candidate
    }
    $uvxPath = $uvx.Source
    if (-not $uvxPath) { $uvxPath = $uvx.FullName }
    Write-Ok "uvx at $uvxPath"

    # 4. kicad-cli (required for ERC/DRC/exports; read/write tools work without it)
    Write-Step "Checking kicad-cli"
    $kicadCli = Get-Command kicad-cli -ErrorAction SilentlyContinue
    if ($kicadCli) {
        $kicadCliPath = $kicadCli.Source
        Write-Ok "kicad-cli on PATH: $kicadCliPath"
    } else {
        $searchRoots = @('C:\Program Files\KiCad', "$env:LOCALAPPDATA\Programs\KiCad")
        $found = Get-ChildItem -Path $searchRoots -Filter 'kicad-cli.exe' -Recurse -ErrorAction SilentlyContinue |
            Sort-Object FullName -Descending | Select-Object -First 1
        if (-not $found) {
            Write-Host "    kicad-cli.exe not found. Install KiCad 9.x or 10.x, then re-run this script." -ForegroundColor Yellow
            $kicadCliPath = $null
        } else {
            $kicadCliPath = $found.FullName
            Write-Ok "found $kicadCliPath"
        }
    }

    # 5. .vscode/mcp.json
    Write-Step "Checking .vscode/mcp.json"
    $vscodeDir = Join-Path $repoRoot '.vscode'
    $mcpConfigPath = Join-Path $vscodeDir 'mcp.json'
    if (-not (Test-Path $vscodeDir)) {
        New-Item -ItemType Directory -Path $vscodeDir | Out-Null
    }

    $schPath = Join-Path $repoRoot 'docs\hardware\project_schematic_package\generated\pic_amp_protection.kicad_sch'
    $outDir = Join-Path $repoRoot 'out'

    $env = [ordered]@{
        KICAD_SCH_PATH   = '${workspaceFolder}\docs\hardware\project_schematic_package\generated\pic_amp_protection.kicad_sch'
        KICAD_OUTPUT_DIR = '${workspaceFolder}\out'
    }
    if ($kicadCliPath) {
        $env.Insert(0, 'KICAD_CLI_PATH', $kicadCliPath)
    }

    $desiredConfig = [ordered]@{
        servers = [ordered]@{
            kicad = [ordered]@{
                type    = 'stdio'
                command = $uvxPath
                args    = @('--from', 'mcp-server-kicad', 'mcp-server-kicad')
                cwd     = '${workspaceFolder}'
                env     = $env
            }
        }
    }

    if (Test-Path $mcpConfigPath) {
        $existing = Get-Content $mcpConfigPath -Raw
        $desiredJson = $desiredConfig | ConvertTo-Json -Depth 10
        if ($existing.Trim() -eq $desiredJson.Trim()) {
            Write-Skip "mcp.json already up to date"
        } else {
            Write-Host "    updating mcp.json (existing config found, overwriting kicad server entry) ..."
            $desiredJson | Set-Content -Path $mcpConfigPath -Encoding utf8
            Write-Ok "mcp.json updated"
        }
    } else {
        ($desiredConfig | ConvertTo-Json -Depth 10) | Set-Content -Path $mcpConfigPath -Encoding utf8
        Write-Ok "mcp.json created"
    }

    if (-not (Test-Path $schPath)) {
        Write-Host "    note: configured schematic path does not exist yet: $schPath" -ForegroundColor Yellow
    }
    if (-not (Test-Path $outDir)) {
        New-Item -ItemType Directory -Path $outDir | Out-Null
        Write-Ok "created out\ directory"
    }

    # 6. MCP server process — this script never starts or stops it. VS Code
    #    owns that process; running this script while it is already up is a
    #    no-op for this step by design.
    Write-Step "MCP server process"
    Write-Skip "not managed by this script; start/stop it from VS Code's MCP: List Servers command"

    Write-Host ""
    Write-Host "Setup complete." -ForegroundColor Green
}
finally {
    Pop-Location
}
