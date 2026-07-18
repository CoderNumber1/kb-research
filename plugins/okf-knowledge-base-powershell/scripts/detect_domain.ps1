#!/usr/bin/env pwsh
<#
Rank knowledge-base domains by how well they match a source's topic — the
PowerShell port of detect_domain.py. Same CLI and JSON output.

Usage:
  detect_domain.ps1 --query "stripe webhook signature verification failed"
  detect_domain.ps1 --list [--json]
  detect_domain.ps1 --query "..." --json

Exit codes: 0 ok, 2 no KB found, 3 no domains in the bundle.
#>
Set-StrictMode -Off
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'KbCommon.psm1') -Force

$opts = ConvertFrom-KbArgs -Arguments $args -Switches @('list', 'json')
$asJson = [bool]$opts['json']
$limit = if ($opts['limit']) { [int]$opts['limit'] } else { 5 }

function Load-Domains {
    param([string]$KbRoot)
    $domains = @()
    if (-not (Test-Path -LiteralPath $KbRoot -PathType Container)) { return $domains }
    foreach ($f in (Get-ChildItem -LiteralPath $KbRoot -Recurse -File -Filter 'domain.md' -ErrorAction SilentlyContinue)) {
        $dir = $f.Directory.FullName
        $rel = [System.IO.Path]::GetRelativePath($KbRoot, $dir).Replace('\', '/')
        if ($rel -eq '.') { continue }
        $fm = Get-KbFrontmatter (Get-Content -LiteralPath $f.FullName -Raw)
        $tags = $fm.Meta['tags']
        if ($null -eq $tags) { $tags = @() } elseif ($tags -is [string]) { $tags = @($tags) }
        $strong = Get-KbTokens (("$($fm.Meta['title']) ") + ($tags -join ' '))
        $weak = Get-KbTokens (("$($fm.Meta['description']) ") + $fm.Body)
        $domains += [pscustomobject]@{
            slug        = $rel
            title       = if ($fm.Meta['title']) { $fm.Meta['title'] } else { $rel }
            description = "$($fm.Meta['description'])"
            tags        = @($tags)
            status      = if ($fm.Meta['status']) { $fm.Meta['status'] } else { 'active' }
            Strong      = [System.Collections.Generic.HashSet[string]]::new([string[]]$strong)
            Weak        = [System.Collections.Generic.HashSet[string]]::new([string[]]$weak)
        }
    }
    return @($domains | Sort-Object -Property slug)
}

function Get-Score {
    param($Domain, [string[]]$QTerms)
    $q = [System.Collections.Generic.HashSet[string]]::new([string[]]$QTerms)
    if ($q.Count -eq 0) { return @{ Score = 0.0; Matched = @() } }
    $hitsStrong = [System.Collections.Generic.List[string]]::new()
    $hitsWeak = [System.Collections.Generic.List[string]]::new()
    foreach ($t in $q) {
        if ($Domain.Strong.Contains($t)) { [void]$hitsStrong.Add($t) }
        elseif ($Domain.Weak.Contains($t)) { [void]$hitsWeak.Add($t) }
    }
    $raw = 3.0 * $hitsStrong.Count + 1.0 * $hitsWeak.Count
    $ms = [System.Collections.Generic.List[string]]::new()
    if ($hitsStrong.Count) { $ms.AddRange([string[]]($hitsStrong | Sort-Object)) }
    if ($hitsWeak.Count) { $ms.AddRange([string[]]($hitsWeak | Sort-Object)) }
    return @{ Score = ($raw / $q.Count); Matched = $ms.ToArray() }
}

function Emit($obj) {
    if ($asJson) { $obj | ConvertTo-Json -Depth 8 }
}

$kbRoot = Find-KbRoot -Explicit $opts['kb-root']
if (-not $kbRoot) {
    $msg = 'No knowledge base found in the working directory. Create one with the kb-init-domain skill.'
    if ($asJson) { @{ error = $msg } | ConvertTo-Json } else { [Console]::Error.WriteLine("ERROR: $msg") }
    exit 2
}

$domains = Load-Domains -KbRoot $kbRoot
if ($domains.Count -eq 0) {
    $msg = "No domains found under $kbRoot. Create one with kb-init-domain."
    if ($asJson) { @{ domains = @(); note = $msg } | ConvertTo-Json } else { Write-Output $msg }
    exit 3
}

if ($opts['list'] -or -not $opts['query']) {
    $out = @($domains | ForEach-Object {
            [ordered]@{ slug = $_.slug; title = $_.title; description = $_.description
                tags = @($_.tags); status = $_.status }
        })
    if ($asJson) {
        [ordered]@{ kb_root = $kbRoot; domains = $out } | ConvertTo-Json -Depth 8
    } else {
        Write-Output "Domains in ${kbRoot}:"
        foreach ($d in $out) {
            $tg = if ($d.tags.Count) { "  tags: $($d.tags -join ', ')" } else { '' }
            Write-Output "  - $($d.slug) — $($d.title): $($d.description)$tg"
        }
    }
    exit 0
}

$qTerms = Get-KbTokens $opts['query']
$scored = foreach ($d in $domains) {
    $s = Get-Score -Domain $d -QTerms $qTerms
    [pscustomobject]@{ Domain = $d; Score = $s.Score; Matched = @($s.Matched) }
}
$ranked = @($scored |
    Sort-Object -Property @{Expression = 'Score'; Descending = $true }, @{Expression = { $_.Domain.slug }; Descending = $false } |
    Select-Object -First $limit)

$top = if ($ranked.Count -ge 1) { $ranked[0].Score } else { 0.0 }
$runner = if ($ranked.Count -ge 2) { $ranked[1].Score } else { 0.0 }
if ($top -ge 0.5 -and ($top - $runner) -ge 0.2) { $confidence = 'high' }
elseif ($top -ge 0.25) { $confidence = 'medium' }
else { $confidence = 'low' }
$recommendation = if ($confidence -ne 'low' -and $ranked.Count -ge 1) { $ranked[0].Domain.slug } else { $null }

$rankingOut = @($ranked | ForEach-Object {
        [ordered]@{
            slug          = $_.Domain.slug
            title         = $_.Domain.title
            score         = [math]::Round($_.Score, 3)
            matched_terms = @($_.Matched)
            description   = $_.Domain.description
        }
    })

$result = [ordered]@{
    kb_root        = $kbRoot
    query_terms    = @($qTerms)
    confidence     = $confidence
    recommendation = $recommendation
    ranking        = $rankingOut
}

if ($asJson) {
    $result | ConvertTo-Json -Depth 8
} else {
    Write-Output ("Query terms: " + (($qTerms -join ', ')))
    $rec = if ($recommendation) { "  ->  recommend '$recommendation'" } else { '  ->  no clear match' }
    Write-Output "Confidence: $confidence$rec"
    foreach ($r in $rankingOut) {
        $mt = if ($r.matched_terms.Count) { $r.matched_terms -join ', ' } else { '-' }
        Write-Output ("  {0,5}  {1,-24} matched: {2}" -f $r.score, $r.slug, $mt)
    }
    if ($confidence -eq 'low') {
        Write-Output "`nNo confident match. Consider asking the user, or creating a new domain with kb-init-domain."
    }
}
exit 0
