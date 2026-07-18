#!/usr/bin/env pwsh
<#
Scaffold an OKF domain (or nested sub-domain) and register it — the PowerShell
port of init_domain.py. Same CLI and file templates.

Usage:
  init_domain.ps1 --slug billing --title "Billing" --description "..."
  init_domain.ps1 --slug billing/eu --title "EU Billing" --description "..."
  init_domain.ps1 --parent billing --slug eu --title "EU Billing" --description "..."

Exit codes: 0 ok, 2 usage/precondition error.
#>
Set-StrictMode -Off
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'KbCommon.psm1') -Force

$Placeholders = @(
    '<!-- Domains are registered here by the kb-init-domain skill. None yet. -->',
    '<!-- Domains registered here. -->',
    '<!-- Sub-domains are registered here by the kb-init-domain skill. None yet. -->'
)

function Get-Today { (Get-Date).ToString('yyyy-MM-dd') }
function Get-NowIso { ([datetimeoffset]::UtcNow).ToString("yyyy-MM-ddTHH:mm:sszzz") }
function ConvertTo-Slug([string]$s) { (($s.Trim().ToLower() -replace '[^a-z0-9]+', '-').Trim('-')) }
function Get-SlugSegments([string]$raw) { @($raw -split '/' | ForEach-Object { ConvertTo-Slug $_ } | Where-Object { $_ -ne '' }) }
function Get-SplitLines([string]$t) { ($t -replace "`r`n", "`n").TrimEnd("`n") -split "`n" }
function Write-File([string]$path, [string]$text) {
    $dir = Split-Path -Parent $path
    if ($dir -and -not (Test-Path -LiteralPath $dir)) { New-Item -ItemType Directory -Force -Path $dir | Out-Null }
    Set-Content -LiteralPath $path -Value $text -NoNewline
}

function Initialize-KbRoot([string]$KbRoot) {
    if (-not (Test-Path -LiteralPath $KbRoot)) { New-Item -ItemType Directory -Force -Path $KbRoot | Out-Null }
    $ri = Join-Path $KbRoot 'index.md'
    if (-not (Test-Path -LiteralPath $ri)) {
        Write-File $ri "---`nokf_version: `"0.1`"`n---`n`n# Knowledge Base`n`n# Domains`n`n<!-- Domains registered here. -->`n"
    }
    $rl = Join-Path $KbRoot 'log.md'
    if (-not (Test-Path -LiteralPath $rl)) { Write-File $rl "# Knowledge Base Log`n`nNewest first.`n" }
}

function Register-Entry([string]$IndexPath, [string]$Heading, [string]$LinkTarget, [string]$Title, [string]$Desc) {
    $entry = "* [$Title]($LinkTarget) - $Desc"
    if (-not (Test-Path -LiteralPath $IndexPath)) {
        Write-File $IndexPath "# $Title's parent`n`n$Heading`n`n$entry`n"; return
    }
    $lines = @(Get-SplitLines (Get-Content -LiteralPath $IndexPath -Raw) | Where-Object { $Placeholders -notcontains $_.Trim() })
    if ($lines -contains $entry) { return }
    $hi = -1
    for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i].Trim() -eq $Heading) { $hi = $i; break } }
    if ($hi -lt 0) {
        while ($lines.Count -gt 0 -and $lines[-1].Trim() -eq '') { $lines = $lines[0..($lines.Count - 2)] }
        $lines = @($lines) + @('', $Heading, '', $entry)
    } else {
        $end = $lines.Count
        for ($j = $hi + 1; $j -lt $lines.Count; $j++) { if ($lines[$j].StartsWith('# ')) { $end = $j; break } }
        $ins = $end
        while ($ins - 1 -gt $hi -and $lines[$ins - 1].Trim() -eq '') { $ins-- }
        $lines = @($lines[0..($ins - 1)]) + @($entry) + @(if ($ins -lt $lines.Count) { $lines[$ins..($lines.Count - 1)] })
    }
    Write-File $IndexPath (($lines -join "`n") + "`n")
}

function Add-LogLine([string]$LogPath, [string]$Line) {
    if (-not (Test-Path -LiteralPath $LogPath)) {
        Write-File $LogPath "# Update Log`n`n## $(Get-Today)`n$Line`n"; return
    }
    $log = Get-Content -LiteralPath $LogPath -Raw
    $stamp = "## $(Get-Today)"
    if ($log.Contains($stamp)) {
        $idx = $log.IndexOf($stamp)
        $log = $log.Substring(0, $idx) + $stamp + "`n" + $Line + $log.Substring($idx + $stamp.Length)
    } else {
        $lines = @(Get-SplitLines $log)
        $at = $lines.Count
        for ($i = 0; $i -lt $lines.Count; $i++) { if ($lines[$i].StartsWith('## ')) { $at = $i; break } }
        $head = if ($at -gt 0) { $lines[0..($at - 1)] } else { @() }
        $tail = if ($at -lt $lines.Count) { $lines[$at..($lines.Count - 1)] } else { @() }
        $lines = @($head) + @($stamp, $Line, '') + @($tail)
        $log = (($lines -join "`n").TrimEnd("`n")) + "`n"
    }
    Write-File $LogPath $log
}

# --- main ---
$opts = ConvertFrom-KbArgs -Arguments $args -Switches @('force')
foreach ($req in @('slug', 'title', 'description')) {
    if (-not $opts[$req]) { [Console]::Error.WriteLine("ERROR: --$req is required."); exit 2 }
}

$raw = if ($opts['parent']) { "$($opts['parent'])/$($opts['slug'])" } else { $opts['slug'] }
$segments = Get-SlugSegments $raw
if ($segments.Count -eq 0) { [Console]::Error.WriteLine('ERROR: --slug produced an empty identifier.'); exit 2 }

$slug = $segments -join '/'
$isSub = $segments.Count -gt 1
$parentSegments = if ($isSub) { $segments[0..($segments.Count - 2)] } else { @() }
$leaf = $segments[-1]

$kbRoot = (Find-KbRoot -Explicit $opts['kb-root'])
if (-not $kbRoot) { $kbRoot = 'kb' }
$kbRoot = $kbRoot.TrimEnd('/')

$domainDir = Join-Path $kbRoot ($segments -join [System.IO.Path]::DirectorySeparatorChar)
if ((Test-Path -LiteralPath $domainDir) -and -not $opts['force']) {
    [Console]::Error.WriteLine("ERROR: $domainDir already exists. Use --force to reuse."); exit 2
}

Initialize-KbRoot $kbRoot

if ($isSub) {
    $parentDomainMd = Join-Path (Join-Path $kbRoot ($parentSegments -join [System.IO.Path]::DirectorySeparatorChar)) 'domain.md'
    if (-not (Test-Path -LiteralPath $parentDomainMd -PathType Leaf)) {
        [Console]::Error.WriteLine("ERROR: parent domain '$($parentSegments -join '/')' not found (expected $parentDomainMd). Create it first with kb-init-domain.")
        exit 2
    }
}

$tags = @($opts['tags'] -split ',' | ForEach-Object { $_.Trim() } | Where-Object { $_ -ne '' })
New-Item -ItemType Directory -Force -Path (Join-Path $domainDir 'raw') | Out-Null
$kind = if ($isSub) { 'sub-domain' } else { 'domain' }
$tagStr = if ($tags.Count) { '[' + ($tags -join ', ') + ']' } else { '[]' }
$title = $opts['title']; $desc = $opts['description']

$domainMd = @"
---
type: Domain
title: $title
description: $desc
slug: $slug
tags: $tagStr
status: active
timestamp: $(Get-NowIso)
---

# Scope

$desc

**In scope:** _describe what belongs in this $kind._

**Out of scope:** _describe what does not, and where it lives instead._

# Concept types

_List the kinds of concept pages this $kind will hold (e.g. Entity, Playbook,
Reference, Metric). Add subdirectories (or nested sub-domains) as it grows._

# Entry points

_Link the most important pages here once they exist._

# Sources

Raw source material for this $kind is snapshotted under [``raw/``](raw/index.md).
"@
Write-File (Join-Path $domainDir 'domain.md') $domainMd

$indexMd = @"
# $title

$desc

See [domain.md](domain.md) for scope and conventions.

# Concepts

<!-- Concept pages are listed here as they are ingested. None yet. -->

# Sources

* [Raw sources](raw/) - immutable snapshots of ingested material.
"@
Write-File (Join-Path $domainDir 'index.md') $indexMd

Write-File (Join-Path $domainDir 'log.md') "# $title — Update Log`n`n## $(Get-Today)`n* **Initialization**: Created the $title $kind.`n"

Write-File (Join-Path $domainDir 'raw/index.md') "# Raw Sources`n`nImmutable snapshots of material ingested here. Concept pages cite back to these.`nDo not edit source snapshots after they are written.`n`n<!-- Sources are listed here by the kb-ingest skill. None yet. -->`n"

if ($isSub) {
    $parentDir = Join-Path $kbRoot ($parentSegments -join [System.IO.Path]::DirectorySeparatorChar)
    Register-Entry (Join-Path $parentDir 'index.md') '# Sub-domains' "$leaf/index.md" $title $desc
    Add-LogLine (Join-Path $parentDir 'log.md') "* **Creation**: Established the [$title]($leaf/index.md) sub-domain."
    $reg = "Registered as a sub-domain under '$($parentSegments -join '/')' in $(Join-Path $parentDir 'index.md')."
} else {
    Register-Entry (Join-Path $kbRoot 'index.md') '# Domains' "$slug/index.md" $title $desc
    Add-LogLine (Join-Path $kbRoot 'log.md') "* **Creation**: Established the [$title]($slug/index.md) domain."
    $reg = "Registered in $(Join-Path $kbRoot 'index.md')."
}

Write-Output "OK: created $kind '$slug' at $domainDir"
Write-Output 'Files: domain.md, index.md, log.md, raw/index.md'
Write-Output $reg
exit 0
