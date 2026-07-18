#!/usr/bin/env pwsh
<#
Lint the knowledge base for OKF conformance and LLM-wiki hygiene — the
PowerShell port of kb_lint.py. Same checks, CLI, JSON output, and exit codes.

Exit code: 0 if no ERRORs, 1 if any ERROR, 2 on bad invocation / no KB.
#>
Set-StrictMode -Off
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'KbCommon.psm1') -Force

$opts = ConvertFrom-KbArgs -Arguments $args -Switches @('json', 'fix-index')
$asJson = [bool]$opts['json']
$staleDays = if ($opts['stale-days']) { [int]$opts['stale-days'] } else { 0 }
$reserved = @('index.md', 'log.md')
$recommended = @('title', 'description', 'timestamp')
$linkRe = [regex]'\[[^\]]*\]\(([^)]+)\)'
$isoDate = [regex]'^\d{4}-\d{2}-\d{2}$'

$script:findings = [System.Collections.Generic.List[object]]::new()
$script:seq = 0
function Add-Finding([string]$Level, [string]$Code, [string]$Path, [string]$Msg) {
    $script:findings.Add([pscustomobject]@{ level = $Level; code = $Code; path = $Path; msg = $Msg; Order = $script:seq })
    $script:seq++
}

function ConvertTo-PyRepr([string]$s) {
    $quote = "'"
    if ($s.Contains("'") -and -not $s.Contains('"')) { $quote = '"' }
    $sb = [System.Text.StringBuilder]::new()
    [void]$sb.Append($quote)
    foreach ($ch in $s.ToCharArray()) {
        if ($ch -eq '\') { [void]$sb.Append('\\') }
        elseif ($ch -eq "`n") { [void]$sb.Append('\n') }
        elseif ($ch -eq "`r") { [void]$sb.Append('\r') }
        elseif ($ch -eq "`t") { [void]$sb.Append('\t') }
        elseif ($ch -eq $quote[0]) { [void]$sb.Append('\' + $ch) }
        else { [void]$sb.Append($ch) }
    }
    [void]$sb.Append($quote)
    return $sb.ToString()
}

function Get-Rel([string]$KbRoot, [string]$Path) {
    return [System.IO.Path]::GetRelativePath($KbRoot, $Path).Replace('\', '/')
}

function Resolve-KbLink([string]$Target, [string]$PagePath, [string]$KbRoot) {
    $t = $Target.Split('#')[0].Trim()
    if (-not $t -or $t -match '^[a-z][a-z0-9+.-]*://' -or $t.StartsWith('mailto:')) { return $null }
    if ($t.StartsWith('/')) { return [System.IO.Path]::GetFullPath((Join-Path $KbRoot ($t.TrimStart('/')))) }
    return [System.IO.Path]::GetFullPath((Join-Path (Split-Path -Parent $PagePath) $t))
}

$kbRoot = Find-KbRoot -Explicit $opts['kb-root']
if (-not $kbRoot) {
    [Console]::Error.WriteLine('ERROR: no knowledge base found. Create one with kb-init-domain.'); exit 2
}
$kbRoot = [System.IO.Path]::GetFullPath($kbRoot)
$scanRoot = if ($opts['domain']) { Join-Path $kbRoot $opts['domain'] } else { $kbRoot }
if (-not (Test-Path -LiteralPath $scanRoot -PathType Container)) {
    [Console]::Error.WriteLine("ERROR: $scanRoot not found."); exit 2
}

$conceptPages = [ordered]@{}     # fullpath -> meta hashtable
$titles = @{}                    # title -> list of rel paths
$resources = @{}                 # resource -> list of rel paths
$linkTargets = [System.Collections.Generic.HashSet[string]]::new()
$dirChildren = @{}               # dir -> set of concept filenames

function Lint-Reserved([string]$Name, [string]$Full, [string]$Text) {
    $r = Get-Rel $kbRoot $Full
    $fm = Get-KbFrontmatter $Text
    if ($Name -eq 'index.md') {
        $isRoot = (Split-Path -Parent ([System.IO.Path]::GetFullPath($Full))) -eq $kbRoot
        $onlyOkf = $true
        foreach ($k in $fm.Meta.Keys) { if ($k -ne 'okf_version') { $onlyOkf = $false } }
        if ($fm.Ok -and $fm.Meta.Count -gt 0 -and -not ($isRoot -and $onlyOkf)) {
            Add-Finding 'ERROR' 'index-frontmatter' $r ('index.md must not carry frontmatter (except okf_version in the bundle-root index.md) — OKF §6/§11')
        }
    } elseif ($Name -eq 'log.md') {
        foreach ($line in ($Text -split "`n")) {
            if ($line.StartsWith('## ') -and -not $isoDate.IsMatch($line.Substring(3).Trim())) {
                Add-Finding 'WARNING' 'log-date' $r ("log heading is not ISO YYYY-MM-DD: " + (ConvertTo-PyRepr $line.Trim()))
            }
        }
    }
}

foreach ($f in (Get-ChildItem -LiteralPath $scanRoot -Recurse -File -Filter '*.md' -ErrorAction SilentlyContinue)) {
    $full = $f.FullName
    $text = Get-Content -LiteralPath $full -Raw
    if ($reserved -contains $f.Name) { Lint-Reserved $f.Name $full $text; continue }

    $fm = Get-KbFrontmatter $text
    $r = Get-Rel $kbRoot $full
    if (-not $fm.Ok) { Add-Finding 'ERROR' 'frontmatter' $r ("missing/unparseable frontmatter: " + $fm.Err); continue }
    if ("$($fm.Meta['type'])".Trim() -eq '') { Add-Finding 'ERROR' 'type' $r 'frontmatter missing a non-empty `type`' }

    $conceptPages[$full] = $fm.Meta
    $dir = $f.Directory.FullName
    if (-not $dirChildren.ContainsKey($dir)) { $dirChildren[$dir] = [System.Collections.Generic.HashSet[string]]::new() }
    [void]$dirChildren[$dir].Add($f.Name)

    foreach ($field in $recommended) {
        if ("$($fm.Meta[$field])".Trim() -eq '') { Add-Finding 'INFO' 'recommended' $r ("missing recommended field ``$field``") }
    }
    if ($fm.Meta['title']) {
        $t = $fm.Meta['title']; if (-not $titles.ContainsKey($t)) { $titles[$t] = @() }; $titles[$t] += $r
    }
    if ($fm.Meta['resource']) {
        $res = $fm.Meta['resource']; if (-not $resources.ContainsKey($res)) { $resources[$res] = @() }; $resources[$res] += $r
    }
    if ($staleDays -and $fm.Meta['timestamp']) {
        $ts = "$($fm.Meta['timestamp'])"
        try {
            $dto = [datetimeoffset]::Parse($ts.Replace('Z', '+00:00'), [cultureinfo]::InvariantCulture)
            $age = ([datetime]::UtcNow - $dto.UtcDateTime).Days
            if ($age -gt $staleDays) { Add-Finding 'INFO' 'stale' $r "last updated $age days ago" }
        } catch {
            Add-Finding 'WARNING' 'timestamp' $r ("unparseable timestamp: " + (ConvertTo-PyRepr $ts))
        }
    }
    foreach ($m in $linkRe.Matches($fm.Body)) {
        $target = $m.Groups[1].Value
        $resolved = Resolve-KbLink $target $full $kbRoot
        if ($null -eq $resolved) { continue }
        if (Test-Path -LiteralPath $resolved) { [void]$linkTargets.Add($resolved) }
        else { Add-Finding 'WARNING' 'broken-link' $r ("link target does not exist: $target") }
    }
}

foreach ($full in $conceptPages.Keys) {
    if ((Split-Path -Leaf $full) -eq 'domain.md') { continue }
    if (-not $linkTargets.Contains([System.IO.Path]::GetFullPath($full))) {
        Add-Finding 'WARNING' 'orphan' (Get-Rel $kbRoot $full) 'no other page links here (orphaned)'
    }
}

foreach ($t in $titles.Keys) {
    $ps = @($titles[$t] | Sort-Object)
    if ($ps.Count -gt 1) {
        Add-Finding 'WARNING' 'dup-title' $ps[0] ("title " + (ConvertTo-PyRepr $t) + " shared by: " + ($ps -join ', '))
    }
}
foreach ($res in $resources.Keys) {
    $ps = @($resources[$res] | Sort-Object)
    if ($ps.Count -gt 1) {
        Add-Finding 'WARNING' 'dup-resource' $ps[0] ("resource " + (ConvertTo-PyRepr $res) + " shared by: " + ($ps -join ', '))
    }
}

# Index drift + optional regeneration.
foreach ($dir in $dirChildren.Keys) {
    $concepts = @($dirChildren[$dir] | Where-Object { $_ -notin $reserved -and $_ -ne 'domain.md' } | Sort-Object)
    $indexPath = Join-Path $dir 'index.md'
    $listed = [System.Collections.Generic.HashSet[string]]::new()
    if (Test-Path -LiteralPath $indexPath -PathType Leaf) {
        foreach ($m in $linkRe.Matches((Get-Content -LiteralPath $indexPath -Raw))) {
            [void]$listed.Add((Split-Path -Leaf ($m.Groups[1].Value.Split('#')[0].Trim().TrimEnd('/'))))
        }
    }
    $missing = @($concepts | Where-Object { -not $listed.Contains($_) })
    if ($missing.Count -gt 0 -and (Test-Path -LiteralPath $indexPath -PathType Leaf)) {
        Add-Finding 'WARNING' 'index-drift' (Get-Rel $kbRoot $indexPath) ("index.md omits: " + ($missing -join ', '))
    }
    if ($opts['fix-index'] -and (Test-Path -LiteralPath $indexPath -PathType Leaf)) {
        $lines = @('', '# Concepts', '')
        foreach ($c in $concepts) {
            $meta = $conceptPages[(Join-Path $dir $c)]
            $title = if ($meta -and $meta['title']) { $meta['title'] } else { $c.Substring(0, $c.Length - 3) }
            $desc = if ($meta) { "$($meta['description'])" } else { '' }
            $lines += ("* [$title]($c)" + $(if ($desc) { " - $desc" } else { '' }))
        }
        $block = ($lines -join "`n") + "`n"
        $text = Get-Content -LiteralPath $indexPath -Raw
        if ($text.Contains('# Concepts')) {
            $head = $text.Substring(0, $text.IndexOf('# Concepts'))
            $rest = $text.Substring($text.IndexOf('# Concepts'))
            $nl = $rest.IndexOf("`n# ")
            $tail = if ($nl -ge 0) { $rest.Substring($nl) } else { '' }
            $text = $head.TrimEnd() + "`n" + $block + $tail
        } else {
            $text = $text.TrimEnd() + "`n" + $block
        }
        Set-Content -LiteralPath $indexPath -Value $text -NoNewline
    }
}

# Report
$rank = @{ ERROR = 0; WARNING = 1; INFO = 2 }
$sorted = @($script:findings | Sort-Object `
    @{Expression = { $rank[$_.level] } }, @{Expression = 'code' }, @{Expression = 'path' }, @{Expression = 'Order' })
$counts = [ordered]@{ ERROR = 0; WARNING = 0; INFO = 0 }
foreach ($f in $sorted) { $counts[$f.level]++ }

if ($asJson) {
    $out = [ordered]@{
        summary    = $counts
        conformant = ($counts['ERROR'] -eq 0)
        findings   = @($sorted | ForEach-Object { [ordered]@{ level = $_.level; code = $_.code; path = $_.path; msg = $_.msg } })
    }
    $out | ConvertTo-Json -Depth 8
} elseif ($sorted.Count -eq 0) {
    Write-Output "✓ Knowledge base is clean — OKF-conformant, no hygiene issues."
} else {
    foreach ($f in $sorted) { Write-Output ("{0,-7} [{1}] {2}`n         {3}" -f $f.level, $f.code, $f.path, $f.msg) }
    Write-Output ("`nSummary: $($counts['ERROR']) error(s), $($counts['WARNING']) warning(s), $($counts['INFO']) info.")
    if ($counts['ERROR'] -eq 0) { Write-Output 'OKF-conformant.' } else { Write-Output 'NOT OKF-conformant — fix the errors above.' }
}
exit ([int]($counts['ERROR'] -gt 0))
