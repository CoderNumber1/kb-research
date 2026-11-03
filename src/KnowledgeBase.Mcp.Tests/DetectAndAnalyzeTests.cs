using Xunit;

namespace KnowledgeBase.Mcp.Tests;

public sealed class DetectAndAnalyzeTests : IClassFixture<McpFixture>
{
    private readonly McpFixture _mcp;

    public DetectAndAnalyzeTests(McpFixture mcp)
    {
        _mcp = mcp;
    }

    private static string Domain(string title, string description, string extra = "") =>
        $"---\ntype: Domain\ntitle: {title}\ndescription: {description}\n{extra}---\n\n# Scope\n";

    [Fact]
    public async Task DeprecatedDomainsAreListedButNeverRoutedTo()
    {
        using var workspace = new TestWorkspace();
        workspace.Write("index.md", "---\nokf_version: \"0.2\"\n---\n");
        workspace.Write("billing/domain.md", Domain("Billing", "Invoices, payments, webhook retries."));
        workspace.Write("legacy-billing/domain.md", Domain("Legacy Billing", "Invoices, payments, webhook retries.", "status: deprecated\n"));

        var listing = await _mcp.CallJsonAsync("kb_detect_domain", TestCalls.Args(workspace, ("list", true)));
        var statuses = listing.GetProperty("domains").EnumerateArray()
            .ToDictionary(d => d.GetProperty("slug").GetString()!, d => d.GetProperty("status").GetString());
        Assert.Equal("stable", statuses["billing"]);
        Assert.Equal("deprecated", statuses["legacy-billing"]);

        var routed = await _mcp.CallJsonAsync("kb_detect_domain", TestCalls.Args(workspace, ("query", "webhook retries for invoices")));
        Assert.Equal("billing", routed.GetProperty("recommendation").GetString());
        Assert.DoesNotContain(routed.GetProperty("ranking").EnumerateArray(),
            r => r.GetProperty("slug").GetString() == "legacy-billing");
    }

    [Fact]
    public async Task AnalyzeCanBeScopedToOneDomain()
    {
        using var workspace = new TestWorkspace();
        const string body = "Webhook deliveries retry with exponential backoff for twenty four hours before dead lettering the event payload.";
        foreach (var domain in new[] { "billing", "payments" })
        {
            workspace.Write($"{domain}/domain.md", Domain(domain, "Scope."));
            workspace.Write($"{domain}/retry-a.md", $"---\ntype: Reference\ntitle: Retry policy\n---\n\n{body}\n");
            workspace.Write($"{domain}/retry-b.md", $"---\ntype: Reference\ntitle: Retry policy copy\n---\n\n{body}\n");
        }

        var all = await _mcp.CallJsonAsync("kb_analyze", TestCalls.Args(workspace));
        var scoped = await _mcp.CallJsonAsync("kb_analyze", TestCalls.Args(workspace, ("domain", "billing")));

        Assert.Equal(4, all.GetProperty("pages_analyzed").GetInt32());
        Assert.True(all.GetProperty("cross_domain").GetArrayLength() > 0);
        Assert.Equal(2, scoped.GetProperty("pages_analyzed").GetInt32());
        Assert.Equal(0, scoped.GetProperty("cross_domain").GetArrayLength());
        Assert.All(scoped.GetProperty("within_domain").EnumerateArray().SelectMany(g => g.GetProperty("members").EnumerateArray()),
            m => Assert.StartsWith("billing/", m.GetString()));
    }
}

/// <summary>The CI gate: the committed knowledge base must be OKF-conformant.</summary>
public sealed class CommittedKbTests : IClassFixture<McpFixture>
{
    private readonly McpFixture _mcp;

    public CommittedKbTests(McpFixture mcp)
    {
        _mcp = mcp;
    }

    [Fact]
    public async Task CommittedKnowledgeBaseIsConformant()
    {
        var kbRoot = Path.Combine(McpFixture.FindRepoRoot(), "kb");
        var lint = await _mcp.CallJsonAsync("kb_lint", new Dictionary<string, object?> { ["kb_root"] = kbRoot });

        var errors = lint.Findings().Where(f => f.GetProperty("level").GetString() == "ERROR")
            .Select(f => $"{f.GetProperty("path").GetString()}: {f.GetProperty("msg").GetString()}");
        Assert.True(lint.GetProperty("conformant").GetBoolean(), string.Join("\n", errors));
    }
}
