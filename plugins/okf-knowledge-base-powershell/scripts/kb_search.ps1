#!/usr/bin/env pwsh
<#
Search the knowledge base and return ranked concept pages with snippets — the
PowerShell port of kb_search.py. Same CLI and JSON output.

Usage:
  kb_search.ps1 "how do webhooks retry"
  kb_search.ps1 "invoice dunning" --domain billing --limit 8 --json

Exit codes: 0 ok (even with no hits), 2 no KB / bad path.
#>
Set-StrictMode -Off
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'KbCommon.psm1') -Force

$opts = ConvertFrom-KbArgs -Arguments $args -Switches @('json', 'include-raw')
$asJson = [bool]$opts['json']
$limit = if ($opts['limit']) { [int]$opts['limit'] } else { 10 }
$reserved = @('index.md', 'log.md')

$queryText = if ($opts['query']) { $opts['query'] } else { ($opts._Positional -join ' ') }

function Get-PageScore {
    param([hashtable]$Meta, [string]$Body, [string[]]$QTerms)
    if ($QTerms.Count -eq 0) { return @{ Score = 0.0; Matched = [ordered]@{} } }
    $title = [System.Collections.Generic.HashSet[string]]::new([string[]](Get-KbTokens ("$($Meta['title'])")))
    $desc = [System.Collections.Generic.HashSet[string]]::new([string[]](Get-KbTokens ("$($Meta['description'])")))
    $tags = $Meta['tags']; if ($null -eq $tags) { $tags = @() } elseif ($tags -is [string]) { $tags = @($tags) }
    $tagtok = [System.Collections.Generic.HashSet[string]]::new([string[]](Get-KbTokens ($tags -join ' ')))
    $typetok = [System.Collections.Generic.HashSet[string]]::new([string[]](Get-KbTokens ("$($Meta['type'])")))
    $bodyCount = @{}
    foreach ($t in (Get-KbTokens $Body)) { $bodyCount[$t] = ([int]$bodyCount[$t]) + 1 }

    $total = 0.0; $matched = [ordered]@{}
    foreach ($t in ([System.Collections.Generic.HashSet[string]]::new([string[]]$QTerms))) {
        $s = 0.0
        if ($title.Contains($t)) { $s += 6.0 }
        if ($tagtok.Contains($t)) { $s += 4.0 }
        if ($typetok.Contains($t)) { $s += 3.0 }
        if ($desc.Contains($t)) { $s += 3.0 }
        if ($bodyCount.ContainsKey($t)) { $s += 1.0 + 0.3 * [math]::Min($bodyCount[$t] - 1, 5) }
        if ($s -gt 0) { $matched[$t] = [math]::Round($s, 2); $total += $s }
    }
    $coverage = $matched.Count / ([System.Collections.Generic.HashSet[string]]::new([string[]]$QTerms)).Count
    return @{ Score = ($total * (0.5 + 0.5 * $coverage)); Matched = $matched }
}

function Get-Snippet {
    param([string]$Body, [string[]]$RawWords, [int]$Width = 160)
    $low = $Body.ToLower()
    foreach ($w in $RawWords) {
        $i = $low.IndexOf($w)
        if ($i -ge 0) {
            $start = [math]::Max(0, $i - [int]($Width / 2))
            $end = [math]::Min($Body.Length, $i + [int]($Width / 2))
            $frag = ($Body.Substring($start, $end - $start) -replace "`n", ' ').Trim()
            return (($(if ($start) { [char]0x2026 } else { '' })) + $frag + $(if ($end -lt $Body.Length) { [char]0x2026 } else { '' }))
        }
    }
    $flat = ($Body -replace "`n", ' ').Trim()
    if ($flat.Length -gt $Width) { return $flat.Substring(0, $Width) } else { return $flat }
}

$kbRoot = Find-KbRoot -Explicit $opts['kb-root']
if (-not $kbRoot) {
    [Console]::Error.WriteLine('ERROR: no knowledge base found. Create one with kb-init-domain.')
    exit 2
}
$root = if ($opts['domain']) { Join-Path $kbRoot $opts['domain'] } else { $kbRoot }
if (-not (Test-Path -LiteralPath $root -PathType Container)) {
    [Console]::Error.WriteLine("ERROR: $root not found."); exit 2
}

$qTerms = Get-KbTokens $queryText
$rawWords = Get-KbRawWords $queryText

$results = @()
foreach ($f in (Get-ChildItem -LiteralPath $root -Recurse -File -Filter '*.md' -ErrorAction SilentlyContinue)) {
    if ($reserved -contains $f.Name) { continue }
    $relDir = [System.IO.Path]::GetRelativePath($root, $f.Directory.FullName)
    if (-not $opts['include-raw'] -and (($relDir -split '[\\/]') -contains 'raw')) { continue }
    try { $text = Get-Content -LiteralPath $f.FullName -Raw } catch { continue }
    $fm = Get-KbFrontmatter $text
    if ($opts['type'] -and ("$($fm.Meta['type'])".ToLower() -ne $opts['type'].ToLower())) { continue }
    $sc = Get-PageScore -Meta $fm.Meta -Body $fm.Body -QTerms $qTerms
    if ($sc.Score -le 0) { continue }
    $results += [pscustomobject]@{
        path          = [System.IO.Path]::GetRelativePath($kbRoot, $f.FullName).Replace('\', '/')
        title         = if ($fm.Meta['title']) { $fm.Meta['title'] } else { $f.Name.Substring(0, $f.Name.Length - 3) }
        type          = "$($fm.Meta['type'])"
        description   = "$($fm.Meta['description'])"
        score         = [math]::Round($sc.Score, 2)
        matched_terms = $sc.Matched
        snippet       = Get-Snippet -Body $fm.Body -RawWords $rawWords
    }
}
$results = @($results | Sort-Object -Property @{Expression = 'score'; Descending = $true }, @{Expression = 'path'; Descending = $false } | Select-Object -First $limit)

if ($asJson) {
    [ordered]@{ kb_root = $kbRoot; query_terms = @($qTerms); hits = @($results) } | ConvertTo-Json -Depth 8
} else {
    if ($results.Count -eq 0) {
        Write-Output "No matches for: $queryText"
        Write-Output 'The knowledge base may not cover this yet — consider ingesting a source with kb-ingest.'
        exit 0
    }
    Write-Output ("Query terms: " + ($qTerms -join ', ') + "   ($($results.Count) hits)`n")
    foreach ($r in $results) {
        Write-Output ("[{0,6}] {1}" -f $r.score, $r.path)
        Write-Output "         $($r.type): $($r.title)"
        if ($r.description) { Write-Output "         $($r.description)" }
        Write-Output "         …$($r.snippet)`n"
    }
}
exit 0
