<#
Shared helpers for the OKF knowledge-base PowerShell scripts — the PowerShell
port of kb_common.py. Imported by the other scripts via:
    Import-Module (Join-Path $PSScriptRoot 'KbCommon.psm1')
Behaviour (frontmatter parsing, stemming, KB discovery) mirrors the Python
variant so the two produce identical results.
#>

$script:Stop = [System.Collections.Generic.HashSet[string]]::new(
    [string[]]@(
        'a','an','the','of','to','in','on','for','and','or','but','with','without',
        'into','from','by','as','at','is','are','was','were','be','been','being',
        'this','that','these','those','it','its','you','your','we','our','they',
        'their','he','she','his','her','them','us','i','me','my','mine','ours',
        'yours','will','would','can','could','should','may','might','must','do',
        'does','did','done','has','have','had','how','what','when','where','why',
        'who','whom','which','whose','than','then','so','if','else','not','no',
        'yes','about','over','under','again','further','more','most','other','some',
        'such','only','own','same','too','very','just','also','cannot'
    ))

# Longest-first suffix list (matches kb_common._SUFFIXES).
$script:Suffixes = @(
    'ization','ational','ication','fulness','ousness','iveness',
    'ature','ities','ement','ness','tion','sion','ies','ied','ying',
    'ing','ers','er','ed','ly','al','s','y','e'
) | Sort-Object -Property Length -Descending

function Convert-KbScalar {
    param([string]$Value)
    $v = $Value.Trim()
    if ($v.Length -ge 2 -and $v[0] -eq $v[$v.Length - 1] -and ($v[0] -eq '"' -or $v[0] -eq "'")) {
        return $v.Substring(1, $v.Length - 2)
    }
    return $v
}

function ConvertTo-KbStem {
    param([string]$Word)
    foreach ($suf in $script:Suffixes) {
        if (($Word.Length - $suf.Length) -ge 3 -and $Word.EndsWith($suf)) {
            return $Word.Substring(0, $Word.Length - $suf.Length)
        }
    }
    return $Word
}

function Get-KbTokens {
    param([string]$Text)
    $out = [System.Collections.Generic.List[string]]::new()
    if ([string]::IsNullOrEmpty($Text)) { return , $out.ToArray() }
    foreach ($m in [regex]::Matches($Text.ToLower(), '[a-z0-9]+')) {
        $t = $m.Value
        if ($t.Length -le 1 -or $script:Stop.Contains($t)) { continue }
        [void]$out.Add((ConvertTo-KbStem $t))
    }
    return , $out.ToArray()
}

function Get-KbRawWords {
    <# Unstemmed, non-stopword tokens (length > 1) — used to locate readable
       snippets, mirroring kb_search.py's raw_words. #>
    param([string]$Text)
    $out = [System.Collections.Generic.List[string]]::new()
    if ([string]::IsNullOrEmpty($Text)) { return , $out.ToArray() }
    foreach ($m in [regex]::Matches($Text.ToLower(), '[a-z0-9]+')) {
        $t = $m.Value
        if ($t.Length -le 1 -or $script:Stop.Contains($t)) { continue }
        [void]$out.Add($t)
    }
    return , $out.ToArray()
}

function Get-KbFrontmatter {
    <# Returns a hashtable: Meta (ordered), Body, Ok, Err. Lenient parser. #>
    param([string]$Text)
    $meta = [ordered]@{}
    if ($null -eq $Text -or -not $Text.StartsWith('---')) {
        return @{ Meta = $meta; Body = $Text; Ok = $false; Err = 'no frontmatter block' }
    }
    $lines = $Text -split "`n"
    $end = -1
    for ($i = 1; $i -lt $lines.Count; $i++) {
        if ($lines[$i].Trim() -eq '---') { $end = $i; break }
    }
    if ($end -lt 0) {
        return @{ Meta = $meta; Body = $Text; Ok = $false; Err = 'unterminated frontmatter block' }
    }
    $ok = $true; $err = ''; $key = $null
    for ($i = 1; $i -lt $end; $i++) {
        $raw = $lines[$i]
        if ([string]::IsNullOrWhiteSpace($raw) -or $raw.TrimStart().StartsWith('#')) { continue }
        if (($raw[0] -eq ' ' -or $raw[0] -eq "`t") -and $raw.Trim().StartsWith('- ') -and $key) {
            if ($meta[$key] -isnot [System.Collections.IList]) { $meta[$key] = @() }
            $meta[$key] = @($meta[$key]) + (Convert-KbScalar ($raw.Trim().Substring(2)))
            continue
        }
        $idx = $raw.IndexOf(':')
        if ($idx -ge 0) {
            $key = $raw.Substring(0, $idx).Trim()
            $v = $raw.Substring($idx + 1).Trim()
            if ($v -eq '') {
                $meta[$key] = ''
            } elseif ($v.StartsWith('[') -and $v.EndsWith(']')) {
                $inner = $v.Substring(1, $v.Length - 2).Trim()
                if ($inner -eq '') { $meta[$key] = @() }
                else {
                    $meta[$key] = @($inner -split ',' |
                        Where-Object { $_.Trim() -ne '' } |
                        ForEach-Object { Convert-KbScalar $_.Trim() })
                }
            } else {
                $meta[$key] = Convert-KbScalar $v
            }
        } else {
            $ok = $false; $err = "unparseable frontmatter line: '$raw'"
        }
    }
    $body = if (($end + 1) -le ($lines.Count - 1)) { ($lines[($end + 1)..($lines.Count - 1)] -join "`n") } else { '' }
    return @{ Meta = $meta; Body = $body; Ok = $ok; Err = $err }
}

function Test-KbBundleRoot {
    param([string]$Path)
    if (-not (Test-Path -LiteralPath $Path -PathType Container)) { return $false }
    $index = Join-Path $Path 'index.md'
    if (Test-Path -LiteralPath $index -PathType Leaf) {
        $fm = Get-KbFrontmatter (Get-Content -LiteralPath $index -Raw)
        if ($fm.Meta.Contains('okf_version') -and "$($fm.Meta['okf_version'])".Trim() -ne '') {
            return $true
        }
    }
    foreach ($d in (Get-ChildItem -LiteralPath $Path -Directory -ErrorAction SilentlyContinue)) {
        if (Test-Path -LiteralPath (Join-Path $d.FullName 'domain.md') -PathType Leaf) { return $true }
    }
    return $false
}

function Find-KbRoot {
    <# Resolve the KB root: explicit, then $env:KB_ROOT, then a search from the
       working directory upward. Returns a path string or $null. #>
    param([string]$Explicit, [string]$Start)
    if ($Explicit) { return $Explicit }
    if ($env:KB_ROOT) { return $env:KB_ROOT }
    $cur = if ($Start) { (Resolve-Path -LiteralPath $Start).Path } else { (Get-Location).Path }
    while ($true) {
        $child = Join-Path $cur 'kb'
        if (Test-KbBundleRoot $child) { return $child }
        if (Test-KbBundleRoot $cur) { return $cur }
        $parent = Split-Path -Parent $cur
        if ([string]::IsNullOrEmpty($parent) -or $parent -eq $cur) { return $null }
        $cur = $parent
    }
}

function ConvertFrom-KbArgs {
    <# Parse a Python-style "--flag value" / "--switch" argument array so all
       three variants share one CLI. Unrecognized bare tokens go to _Positional. #>
    param([string[]]$Arguments, [string[]]$Switches = @())
    $opts = @{ _Positional = @() }
    for ($i = 0; $i -lt $Arguments.Count; $i++) {
        $a = $Arguments[$i]
        if ($a -like '--*') {
            $name = $a.Substring(2)
            if ($Switches -contains $name) {
                $opts[$name] = $true
            } else {
                $i++
                $opts[$name] = if ($i -lt $Arguments.Count) { $Arguments[$i] } else { '' }
            }
        } else {
            $opts._Positional = @($opts._Positional) + $a
        }
    }
    return $opts
}

Export-ModuleMember -Function Convert-KbScalar, ConvertTo-KbStem, Get-KbTokens,
    Get-KbRawWords, Get-KbFrontmatter, Test-KbBundleRoot, Find-KbRoot, ConvertFrom-KbArgs
