#!/usr/bin/env pwsh
<#
SessionStart hook: detect an OKF knowledge base in the working directory — the
PowerShell port of kb_detect.py. Emits SessionStart context announcing the KB
(and its domains) if one is present; stays silent otherwise.
#>
Set-StrictMode -Off
$ErrorActionPreference = 'Stop'
Import-Module (Join-Path $PSScriptRoot 'KbCommon.psm1') -Force

$kbRoot = Find-KbRoot
if (-not $kbRoot) { exit 0 }   # no knowledge base here — contribute no context

$domains = @()
foreach ($f in (Get-ChildItem -LiteralPath $kbRoot -Recurse -File -Filter 'domain.md' -ErrorAction SilentlyContinue)) {
    $rel = [System.IO.Path]::GetRelativePath($kbRoot, $f.Directory.FullName).Replace('\', '/')
    if ($rel -ne '.') { $domains += $rel }
}
$domains = @($domains | Sort-Object)

$rel = [System.IO.Path]::GetRelativePath((Get-Location).Path, $kbRoot).Replace('\', '/')
$loc = if ($rel.StartsWith('..')) { $rel } else { "./$rel" }

if ($domains.Count -gt 0) {
    $shown = ($domains | Select-Object -First 12) -join ', '
    if ($domains.Count -gt 12) { $shown += ' …' }
    $context = "An Open Knowledge Format knowledge base is present at $loc " +
    "($($domains.Count) domain(s): $shown). It is a Karpathy-style LLM wiki " +
    "where knowledge compounds into cross-linked pages. Use the kb-search " +
    "skill to answer from it (cite the pages); kb-ingest to capture sources or " +
    "findings (it auto-routes to a domain by description); kb-init-domain for a " +
    "new area; kb-lint for health checks — or the knowledge-curator agent for " +
    "sustained work. Prefer the compiled wiki over re-deriving from raw " +
    "sources, and capture durable new knowledge back into it before finishing."
} else {
    $context = "An empty Open Knowledge Format knowledge base is present at $loc " +
    "(no domains yet). Use the kb-init-domain skill to create the first domain, " +
    "then kb-ingest to populate it."
}

@{ hookSpecificOutput = @{ hookEventName = 'SessionStart'; additionalContext = $context } } |
    ConvertTo-Json -Depth 6 -Compress
exit 0
