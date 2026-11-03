#!/usr/bin/env bash
# Publishes self-contained kb-mcp binaries from the C# project into src/publish/<rid>/
# (git-ignored). The plugin itself runs the Python server (plugins/okf-knowledge-base/
# server/kb_mcp.py); use these binaries only to run the C# server instead, e.g. by
# pointing a local .mcp.json at src/publish/<rid>/kb-mcp.
set -euo pipefail
here="$(cd "$(dirname "$0")" && pwd)"
for rid in linux-x64 win-x64; do
  dotnet publish "$here/KnowledgeBase.Mcp/KnowledgeBase.Mcp.csproj" -c Release -r "$rid" -o "$here/publish/$rid"
done
ls -la "$here"/publish/*/kb-mcp*
