using System.Text.Json;
using Xunit;

namespace KnowledgeBase.Mcp.Tests;

public sealed class SearchTests : IClassFixture<McpFixture>
{
    private readonly McpFixture _mcp;

    public SearchTests(McpFixture mcp)
    {
        _mcp = mcp;
    }

    [Fact]
    public async Task OptedInRawSearchIncludesMarkdownWithoutFrontmatter()
    {
        using var workspace = new TestWorkspace();
        WriteFile(
            Path.Combine(workspace.KbRoot, "concept.md"),
            """
            ---
            type: Reference
            title: Compiled concept
            description: Durable compiled knowledge.
            ---

            Compiled knowledge.
            """);
        WriteFile(
            Path.Combine(workspace.KbRoot, "raw", "source.md"),
            "Opaque archive material contains the searchable phrase.\n");

        var result = await _mcp.CallToolAsync(
            "kb_search",
            new Dictionary<string, object?>
            {
                ["kb_root"] = workspace.KbRoot,
                ["query"] = "searchable phrase",
                ["include_raw"] = true,
            });

        Assert.False(result.IsError, result.Text);
        using var document = JsonDocument.Parse(result.Text);
        var hits = document.RootElement.GetProperty("hits").EnumerateArray().ToArray();

        Assert.Contains(
            hits,
            hit => hit.GetProperty("path").GetString() == "raw/source.md");
    }

    [Fact]
    public async Task LocalSearchExcludesRawByDefaultAndNonMarkdownEvenWhenOptedIn()
    {
        using var workspace = new TestWorkspace();
        WriteFile(
            Path.Combine(workspace.KbRoot, "concept.md"),
            """
            ---
            type: Reference
            title: Compiled boundary
            description: Durable compiled knowledge.
            ---

            Compiled boundary knowledge.
            """);
        WriteFile(
            Path.Combine(workspace.KbRoot, "raw", "source.md"),
            "Opaque raw boundary material.\n");
        WriteFile(
            Path.Combine(workspace.KbRoot, "raw", "source.txt"),
            "Opaque non-Markdown boundary material.\n");

        var defaultResult = await _mcp.CallToolAsync(
            "kb_search",
            new Dictionary<string, object?>
            {
                ["kb_root"] = workspace.KbRoot,
                ["query"] = "boundary",
            });

        Assert.False(defaultResult.IsError, defaultResult.Text);
        using var defaultDocument = JsonDocument.Parse(defaultResult.Text);
        var defaultHits = defaultDocument.RootElement.GetProperty("hits").EnumerateArray().ToArray();
        Assert.Contains(
            defaultHits,
            hit => hit.GetProperty("path").GetString() == "concept.md");
        Assert.DoesNotContain(
            defaultHits,
            hit => hit.GetProperty("path").GetString()!.StartsWith("raw/", StringComparison.Ordinal));

        var optedInResult = await _mcp.CallToolAsync(
            "kb_search",
            new Dictionary<string, object?>
            {
                ["kb_root"] = workspace.KbRoot,
                ["query"] = "boundary",
                ["include_raw"] = true,
            });

        Assert.False(optedInResult.IsError, optedInResult.Text);
        using var optedInDocument = JsonDocument.Parse(optedInResult.Text);
        var optedInHits = optedInDocument.RootElement.GetProperty("hits").EnumerateArray().ToArray();
        Assert.Contains(
            optedInHits,
            hit => hit.GetProperty("path").GetString() == "raw/source.md");
        Assert.DoesNotContain(
            optedInHits,
            hit => hit.GetProperty("path").GetString() == "raw/source.txt");
    }

    [Fact]
    public async Task DefaultSearchExcludesRawWhenScopeStartsAtRawDirectory()
    {
        using var workspace = new TestWorkspace();
        WriteFile(
            Path.Combine(workspace.KbRoot, "raw", "source.md"),
            "Scoped raw boundary material.\n");

        var defaultResult = await _mcp.CallToolAsync(
            "kb_search",
            new Dictionary<string, object?>
            {
                ["kb_root"] = workspace.KbRoot,
                ["domain"] = "raw",
                ["query"] = "scoped boundary",
            });

        Assert.False(defaultResult.IsError, defaultResult.Text);
        using var defaultDocument = JsonDocument.Parse(defaultResult.Text);
        Assert.Empty(defaultDocument.RootElement.GetProperty("hits").EnumerateArray());

        var optedInResult = await _mcp.CallToolAsync(
            "kb_search",
            new Dictionary<string, object?>
            {
                ["kb_root"] = workspace.KbRoot,
                ["domain"] = "raw",
                ["query"] = "scoped boundary",
                ["include_raw"] = true,
            });

        Assert.False(optedInResult.IsError, optedInResult.Text);
        using var optedInDocument = JsonDocument.Parse(optedInResult.Text);
        Assert.Contains(
            optedInDocument.RootElement.GetProperty("hits").EnumerateArray(),
            hit => hit.GetProperty("path").GetString() == "raw/source.md");
    }

    private static void WriteFile(string path, string contents)
    {
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, contents);
    }

    private sealed class TestWorkspace : IDisposable
    {
        private readonly DirectoryInfo _root =
            Directory.CreateTempSubdirectory("knowledge-base-mcp-search-tests-");

        public string KbRoot => _root.FullName;

        public void Dispose()
        {
            if (Directory.Exists(_root.FullName))
            {
                Directory.Delete(_root.FullName, recursive: true);
            }
        }
    }
}
