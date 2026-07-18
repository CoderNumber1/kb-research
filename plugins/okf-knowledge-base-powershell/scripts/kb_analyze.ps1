#!/usr/bin/env pwsh
<#
Find consolidation candidates in the knowledge base — the PowerShell port of
kb_analyze.py. Same CLI, algorithm, and JSON output.

Exit codes: 0 ok, 2 no KB / bad path.
#>
Set-StrictMode -Off
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'KbCommon.psm1') -Force

$opts = ConvertFrom-KbArgs -Arguments $args -Switches @('json', 'include-raw')
$asJson = [bool]$opts['json']
$minSim = if ($opts['min-similarity']) { [double]$opts['min-similarity'] } else { 0.4 }
$minShared = if ($opts['min-shared-terms']) { [int]$opts['min-shared-terms'] } else { 4 }
$maxPostings = if ($opts['max-postings']) { [int]$opts['max-postings'] } else { 200 }
$limit = if ($opts['limit']) { [int]$opts['limit'] } else { 50 }
$reserved = @('index.md', 'log.md')

function Get-PageDomain([string]$KbRoot, [string]$PagePath) {
    $d = Split-Path -Parent $PagePath
    $root = [System.IO.Path]::GetFullPath($KbRoot)
    while ($true) {
        if (Test-Path -LiteralPath (Join-Path $d 'domain.md') -PathType Leaf) {
            $rel = [System.IO.Path]::GetRelativePath($KbRoot, $d).Replace('\', '/')
            return $(if ($rel -eq '.') { '' } else { $rel })
        }
        $parent = Split-Path -Parent $d
        if (([System.IO.Path]::GetFullPath($d)) -eq $root -or [string]::IsNullOrEmpty($parent) -or $parent -eq $d) { return '' }
        $d = $parent
    }
}

function Load-Pages([string]$KbRoot, [string]$ScanRoot, [bool]$IncludeRaw) {
    $pages = @()
    foreach ($f in (Get-ChildItem -LiteralPath $ScanRoot -Recurse -File -Filter '*.md' -ErrorAction SilentlyContinue)) {
        if ($reserved -contains $f.Name -or $f.Name -eq 'domain.md') { continue }
        $relDir = [System.IO.Path]::GetRelativePath($ScanRoot, $f.Directory.FullName)
        if (-not $IncludeRaw -and (($relDir -split '[\\/]') -contains 'raw')) { continue }
        try { $text = Get-Content -LiteralPath $f.FullName -Raw } catch { continue }
        if ($null -eq $text) { $text = '' }
        $fm = Get-KbFrontmatter $text
        $tags = $fm.Meta['tags']; if ($null -eq $tags) { $tags = @() } elseif ($tags -is [string]) { $tags = @($tags) }
        $blob = @("$($fm.Meta['title'])", ($tags -join ' '), "$($fm.Meta['description'])", $fm.Body) -join ' '
        $pages += [pscustomobject]@{
            path   = [System.IO.Path]::GetRelativePath($KbRoot, $f.FullName).Replace('\', '/')
            domain = Get-PageDomain $KbRoot $f.FullName
            tokens = [System.Collections.Generic.HashSet[string]]::new([string[]](Get-KbTokens $blob))
            bytes  = [System.Text.Encoding]::UTF8.GetByteCount($text)
        }
    }
    return @($pages | Sort-Object -Property path)
}

function Get-Inter([System.Collections.Generic.HashSet[string]]$A, [System.Collections.Generic.HashSet[string]]$B) {
    $small = if ($A.Count -le $B.Count) { $A } else { $B }
    $big = if ($A.Count -le $B.Count) { $B } else { $A }
    $c = 0; foreach ($x in $small) { if ($big.Contains($x)) { $c++ } }
    return $c
}

function Get-CandidateEdges($Pages, [double]$MinSim, [int]$MinShared, [int]$MaxPostings) {
    $postings = @{}
    for ($i = 0; $i -lt $Pages.Count; $i++) {
        foreach ($t in $Pages[$i].tokens) {
            if (-not $postings.ContainsKey($t)) { $postings[$t] = [System.Collections.Generic.List[int]]::new() }
            [void]$postings[$t].Add($i)
        }
    }
    $shared = @{}
    foreach ($plist in $postings.Values) {
        if ($plist.Count -lt 2 -or $plist.Count -gt $MaxPostings) { continue }
        for ($a = 0; $a -lt $plist.Count; $a++) {
            for ($b = $a + 1; $b -lt $plist.Count; $b++) {
                $key = "$($plist[$a]),$($plist[$b])"
                if ($shared.ContainsKey($key)) { $shared[$key]++ } else { $shared[$key] = 1 }
            }
        }
    }
    $edges = [System.Collections.Generic.List[object]]::new()
    foreach ($key in $shared.Keys) {
        if ($shared[$key] -lt $MinShared) { continue }
        $ij = $key.Split(','); $i = [int]$ij[0]; $j = [int]$ij[1]
        $inter = Get-Inter $Pages[$i].tokens $Pages[$j].tokens
        $union = $Pages[$i].tokens.Count + $Pages[$j].tokens.Count - $inter
        $jac = if ($union) { $inter / $union } else { 0.0 }
        if ($jac -ge $MinSim) { [void]$edges.Add([pscustomobject]@{ I = $i; J = $j; Jac = $jac }) }
    }
    return $edges
}

function Build-Clusters($Pages, $Edges) {
    $n = $Pages.Count
    $parent = 0..([math]::Max($n - 1, 0))
    function Find([int]$x) {
        while ($parent[$x] -ne $x) { $parent[$x] = $parent[$parent[$x]]; $x = $parent[$x] }
        return $x
    }
    foreach ($e in $Edges) {
        $ra = Find $e.I; $rb = Find $e.J
        if ($ra -ne $rb) { $parent[[math]::Max($ra, $rb)] = [math]::Min($ra, $rb) }
    }
    $jacByRoot = @{}; $membersByRoot = @{}
    foreach ($e in $Edges) {
        $r = Find $e.I
        if (-not $jacByRoot.ContainsKey($r)) { $jacByRoot[$r] = [System.Collections.Generic.List[double]]::new() }
        [void]$jacByRoot[$r].Add($e.Jac)
    }
    for ($idx = 0; $idx -lt $n; $idx++) {
        $r = Find $idx
        if (-not $membersByRoot.ContainsKey($r)) { $membersByRoot[$r] = [System.Collections.Generic.List[int]]::new() }
        [void]$membersByRoot[$r].Add($idx)
    }
    $clusters = @()
    foreach ($r in $membersByRoot.Keys) {
        $members = @($membersByRoot[$r])
        if ($members.Count -lt 2) { continue }
        $members = @($members | Sort-Object -Property @{Expression = { $Pages[$_].path } })
        $jacs = if ($jacByRoot.ContainsKey($r)) { @($jacByRoot[$r]) } else { @() }
        $domains = @($members | ForEach-Object { $Pages[$_].domain } | Sort-Object -Unique)
        $total = ($members | ForEach-Object { $Pages[$_].bytes } | Measure-Object -Sum).Sum
        $biggest = ($members | ForEach-Object { $Pages[$_].bytes } | Measure-Object -Maximum).Maximum
        $clusters += [pscustomobject]@{
            members          = @($members | ForEach-Object { $Pages[$_].path })
            domains          = @($domains)
            scope            = $(if ($domains.Count -eq 1) { 'within-domain' } else { 'cross-domain' })
            jaccard_min      = $(if ($jacs.Count) { [math]::Round(($jacs | Measure-Object -Minimum).Minimum, 3) } else { 0.0 })
            jaccard_max      = $(if ($jacs.Count) { [math]::Round(($jacs | Measure-Object -Maximum).Maximum, 3) } else { 0.0 })
            total_bytes      = [int]$total
            est_saving_bytes = [int]($total - $biggest)
        }
    }
    return @($clusters | Sort-Object -Property @{Expression = 'est_saving_bytes'; Descending = $true }, @{Expression = { $_.members[0] } })
}

$kbRoot = Find-KbRoot -Explicit $opts['kb-root']
if (-not $kbRoot) { [Console]::Error.WriteLine('ERROR: no knowledge base found. Create one with kb-init-domain.'); exit 2 }
$scanRoot = if ($opts['domain']) { Join-Path $kbRoot $opts['domain'] } else { $kbRoot }
if (-not (Test-Path -LiteralPath $scanRoot -PathType Container)) { [Console]::Error.WriteLine("ERROR: $scanRoot not found."); exit 2 }

$pages = Load-Pages $kbRoot $scanRoot ([bool]$opts['include-raw'])
$edges = Get-CandidateEdges $pages $minSim $minShared $maxPostings
$withinEdges = @($edges | Where-Object { $pages[$_.I].domain -eq $pages[$_.J].domain })
$within = @(Build-Clusters $pages $withinEdges | Select-Object -First $limit)
$cross = @(Build-Clusters $pages $edges | Where-Object { $_.scope -eq 'cross-domain' } | Select-Object -First $limit)

$estTotal = 0
foreach ($c in @($within) + @($cross)) { $estTotal += $c.est_saving_bytes }

$result = [ordered]@{
    kb_root        = $kbRoot
    params         = [ordered]@{ min_similarity = $minSim; min_shared_terms = $minShared; max_postings = $maxPostings }
    pages_analyzed = $pages.Count
    within_domain  = @($within)
    cross_domain   = @($cross)
    summary        = [ordered]@{
        within_domain_groups   = $within.Count
        cross_domain_groups    = $cross.Count
        est_total_saving_bytes = $estTotal
    }
}

if ($asJson) {
    $result | ConvertTo-Json -Depth 10
} else {
    Write-Output "Analyzed $($pages.Count) pages in $kbRoot"
    Write-Output ("Within-domain groups: $($within.Count)   Cross-domain groups: $($cross.Count)   Est. savings: $estTotal bytes`n")
    foreach ($pair in @(@('WITHIN-DOMAIN', $within), @('CROSS-DOMAIN', $cross))) {
        $label = $pair[0]; $list = $pair[1]
        if (-not $list.Count) { continue }
        Write-Output "== $label consolidation candidates =="
        foreach ($c in $list) {
            $dom = if ($c.scope -eq 'within-domain') { $c.domains[0] } else { $c.domains -join ', ' }
            Write-Output "  [$dom] jaccard $($c.jaccard_min)–$($c.jaccard_max), ~$($c.est_saving_bytes) bytes savings:"
            foreach ($m in $c.members) { Write-Output "      - $m" }
        }
        Write-Output ''
    }
    if (-not $within.Count -and -not $cross.Count) { Write-Output 'No consolidation candidates above the similarity threshold.' }
}
exit 0
