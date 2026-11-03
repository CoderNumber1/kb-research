using System.Text.Json;
using System.Text.RegularExpressions;
using Xunit;

namespace KnowledgeBase.Mcp.Tests;

public sealed class PackageSurfaceTests : IClassFixture<McpFixture>
{
    private static readonly string[] Skills =
    {
        "kb-capture", "kb-consolidate", "kb-ingest", "kb-init", "kb-init-domain", "kb-lint", "kb-raw-audit", "kb-search",
    };

    private readonly McpFixture _mcp;

    public PackageSurfaceTests(McpFixture mcp)
    {
        _mcp = mcp;
    }

    private static string PluginRoot => McpFixture.FindPluginRoot();

    private static string[] RelativeFiles(string root) =>
        Directory.EnumerateFiles(root, "*", SearchOption.AllDirectories)
            .Select(path => Path.GetRelativePath(root, path).Replace(Path.DirectorySeparatorChar, '/'))
            .OrderBy(path => path, StringComparer.Ordinal)
            .ToArray();

    private static IEnumerable<string> Instructions() =>
        Directory.EnumerateFiles(Path.Combine(PluginRoot, "skills"), "SKILL.md", SearchOption.AllDirectories)
            .Append(Path.Combine(PluginRoot, "agents", "knowledge-curator.md"));

    [Fact]
    public void ServerToolsAreTheScriptEquivalentsPlusInit()
    {
        var tools = _mcp.ListToolNamesAsync().GetAwaiter().GetResult();
        Assert.Equal(new[] { "kb_analyze", "kb_detect_domain", "kb_init", "kb_init_domain", "kb_lint", "kb_search" }, tools);
    }

    [Fact]
    public async Task EveryToolNamedBySkillsAndTheAgentExists()
    {
        var tools = (await _mcp.ListToolNamesAsync()).ToHashSet(StringComparer.Ordinal);
        foreach (var file in Instructions())
        {
            foreach (Match match in Regex.Matches(File.ReadAllText(file), @"\bkb_[a-z_]+\b"))
            {
                if (match.Value is "kb_root") continue;
                Assert.True(tools.Contains(match.Value), $"{Path.GetRelativePath(PluginRoot, file)} names unknown tool {match.Value}");
            }
        }
    }

    [Fact]
    public void PluginShipsSkillsAgentDoctrineDirectivesAndTheServerOnly()
    {
        Assert.Equal(Skills, Directory.EnumerateDirectories(Path.Combine(PluginRoot, "skills"))
            .Select(Path.GetFileName).OrderBy(n => n, StringComparer.Ordinal).ToArray());
        foreach (var skill in Skills)
        {
            Assert.Contains($"name: {skill}\n", File.ReadAllText(Path.Combine(PluginRoot, "skills", skill, "SKILL.md")).Replace("\r\n", "\n"));
        }

        Assert.Equal(new[] { "knowledge-base.md", "sentinel-automatic.md", "sentinel-search.md" },
            RelativeFiles(Path.Combine(PluginRoot, "references")));
        // The plugin ships the Python server as source; no built artifacts are committed.
        Assert.Equal(
            new[] { "kb_mcp.py", "kbmcp/__init__.py", "kbmcp/analyze.py", "kbmcp/common.py", "kbmcp/detect.py",
                    "kbmcp/index.py", "kbmcp/init.py", "kbmcp/lint.py", "kbmcp/search.py" },
            RelativeFiles(Path.Combine(PluginRoot, "server")).Where(p => !p.Contains("__pycache__")).ToArray());
        Assert.False(Directory.Exists(Path.Combine(PluginRoot, "bin")));
        Assert.False(Directory.Exists(Path.Combine(PluginRoot, "scripts")));
        Assert.False(Directory.Exists(Path.Combine(PluginRoot, "hooks")));

        using var mcpJson = JsonDocument.Parse(File.ReadAllText(Path.Combine(PluginRoot, ".mcp.json")));
        var server = mcpJson.RootElement.GetProperty("mcpServers").GetProperty("knowledge-base");
        Assert.Equal("python3", server.GetProperty("command").GetString());
        Assert.Equal(new[] { "${CLAUDE_PLUGIN_ROOT}/server/kb_mcp.py" },
            server.GetProperty("args").EnumerateArray().Select(a => a.GetString()).ToArray());

        using var marketplace = JsonDocument.Parse(File.ReadAllText(
            Path.Combine(McpFixture.FindRepoRoot(), ".claude-plugin", "marketplace.json")));
        Assert.Equal(new[] { "okf-knowledge-base" },
            marketplace.RootElement.GetProperty("plugins").EnumerateArray().Select(p => p.GetProperty("name").GetString()).ToArray());
    }

    [Fact]
    public void InstructionsAvoidRetiredScriptsSpecsAndRawWrites()
    {
        foreach (var file in Instructions().Append(Path.Combine(PluginRoot, "README.md")))
        {
            var contents = File.ReadAllText(file);
            foreach (var retired in new[]
            {
                "references/llm-wiki.md", "references/okf-spec.md", "/scripts/", "pwsh",
                "raw/index", "snapshot the raw", "snapshot raw", "kb_internal_filter", "kb_federated_filter",
                "SessionStart", "Mistakes You've Made",
            })
            {
                Assert.False(contents.Contains(retired, StringComparison.OrdinalIgnoreCase),
                    $"{Path.GetRelativePath(PluginRoot, file)} still mentions {retired}");
            }
        }
    }

    [Fact]
    public void DirectivesCarryTheKbPathAndOnlyTheAutomaticOneCaptures()
    {
        var automatic = File.ReadAllText(Path.Combine(PluginRoot, "references", "sentinel-automatic.md"));
        var search = File.ReadAllText(Path.Combine(PluginRoot, "references", "sentinel-search.md"));

        foreach (var directive in new[] { automatic, search })
        {
            Assert.StartsWith("<knowledge-base>", directive);
            Assert.EndsWith("</knowledge-base>", directive.TrimEnd());
            Assert.Contains("{{kb_path}}", directive);
            Assert.Contains("**kb-search**", directive);
            Assert.DoesNotContain("self-improvement", directive, StringComparison.OrdinalIgnoreCase);
        }
        Assert.Contains("**kb-capture**", automatic);
        Assert.DoesNotContain("capture", search, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public void ReadmeAndMetadataDescribeTheModel()
    {
        Assert.Contains("user-owned Raw Source Archive", File.ReadAllText(Path.Combine(PluginRoot, "README.md")));
        using var metadata = JsonDocument.Parse(File.ReadAllText(Path.Combine(PluginRoot, ".claude-plugin", "plugin.json")));
        Assert.Contains("v0.2", metadata.RootElement.GetProperty("description").GetString());
    }

    [Fact]
    public void RawAuditIsExplicitAndTwoPhase()
    {
        var contents = File.ReadAllText(Path.Combine(PluginRoot, "skills", "kb-raw-audit", "SKILL.md"));

        Assert.Contains("disable-model-invocation: true", contents, StringComparison.Ordinal);
        Assert.Contains("exactly one explicit KB root", contents, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("read-only", contents, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("remediation scope", contents, StringComparison.OrdinalIgnoreCase);
        Assert.Contains("never removed automatically", contents, StringComparison.OrdinalIgnoreCase);
    }
}
