using Xunit;

namespace KnowledgeBase.Mcp.Tests;

public sealed class InitTests : IClassFixture<McpFixture>
{
    private readonly McpFixture _mcp;

    public InitTests(McpFixture mcp)
    {
        _mcp = mcp;
    }

    private Task<McpToolResult> InitKb(TestWorkspace workspace, string mode, string? instructionsFile = null) =>
        _mcp.CallToolAsync("kb_init", new Dictionary<string, object?>
        {
            ["kb_root"] = workspace.KbRoot,
            ["capture_mode"] = mode,
            ["instructions_file"] = instructionsFile,
        });

    private Task<McpToolResult> InitDomain(TestWorkspace workspace, string slug, string title, string description,
        string? parent = null, bool force = false) =>
        _mcp.CallToolAsync("kb_init_domain", new Dictionary<string, object?>
        {
            ["kb_root"] = workspace.KbRoot,
            ["slug"] = slug,
            ["title"] = title,
            ["description"] = description,
            ["parent"] = parent,
            ["force"] = force,
        });

    private static int Count(string text, string value) => text.Split(value, StringSplitOptions.None).Length - 1;

    [Fact]
    public async Task InitCreatesV02RootAndAutomaticDirectiveInClaudeMd()
    {
        using var workspace = new TestWorkspace();
        File.WriteAllText(workspace.InstructionsFile, "# Project\n\nExisting guidance.\n");

        var result = await InitKb(workspace, "automatic");

        Assert.False(result.IsError, result.Text);
        Assert.StartsWith("---\nokf_version: \"0.2\"\n---", File.ReadAllText(Path.Combine(workspace.KbRoot, "index.md")));
        Assert.True(File.Exists(Path.Combine(workspace.KbRoot, "log.md")));

        var instructions = File.ReadAllText(workspace.InstructionsFile);
        Assert.StartsWith("# Project\n\nExisting guidance.\n\n<knowledge-base>", instructions);
        Assert.Equal(1, Count(instructions, "<knowledge-base>"));
        Assert.Contains("**kb-search**", instructions);
        Assert.Contains("**kb-capture**", instructions);
        Assert.Contains("knowledge base at `kb/`", instructions);
        Assert.DoesNotContain("{{kb_path}}", instructions);
        Assert.DoesNotContain("self-improvement", instructions, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task AgentModeWritesSearchOnlyDirectiveWithNoCaptureInstructions()
    {
        using var workspace = new TestWorkspace();

        var result = await InitKb(workspace, "agent");

        Assert.False(result.IsError, result.Text);
        var instructions = File.ReadAllText(workspace.InstructionsFile);
        Assert.Contains("**kb-search**", instructions);
        Assert.DoesNotContain("capture", instructions, StringComparison.OrdinalIgnoreCase);
    }

    [Fact]
    public async Task RerunningInitSwitchesModeInPlaceAndIsIdempotent()
    {
        using var workspace = new TestWorkspace();
        Assert.False((await InitKb(workspace, "automatic")).IsError);
        File.AppendAllText(workspace.InstructionsFile, "\n## After\n\nKept.\n");
        File.AppendAllText(Path.Combine(workspace.KbRoot, "log.md"), "* user edit\n");
        var logBefore = File.ReadAllText(Path.Combine(workspace.KbRoot, "log.md"));

        var switched = await InitKb(workspace, "agent");
        Assert.False(switched.IsError, switched.Text);
        Assert.Contains("Replaced", switched.Text);
        var instructions = File.ReadAllText(workspace.InstructionsFile);
        Assert.Equal(1, Count(instructions, "<knowledge-base>"));
        Assert.DoesNotContain("kb-capture", instructions);
        Assert.EndsWith("## After\n\nKept.\n", instructions);
        Assert.Equal(logBefore, File.ReadAllText(Path.Combine(workspace.KbRoot, "log.md")));

        var again = await InitKb(workspace, "agent");
        Assert.Contains("already current", again.Text);
        Assert.Equal(instructions, File.ReadAllText(workspace.InstructionsFile));
    }

    [Fact]
    public async Task InitWritesOnlyToTheNamedInstructionsFile()
    {
        using var workspace = new TestWorkspace();
        var custom = Path.Combine(workspace.Root, "docs", "AGENTS.md");

        Assert.False((await InitKb(workspace, "automatic", custom)).IsError);
        Assert.False((await InitDomain(workspace, "billing", "Billing", "Invoices and payments.")).IsError);

        Assert.Contains("knowledge base at `../kb/`", File.ReadAllText(custom));
        Assert.False(File.Exists(workspace.InstructionsFile));
    }

    [Fact]
    public async Task InitRejectsUnknownCaptureMode()
    {
        using var workspace = new TestWorkspace();
        var result = await InitKb(workspace, "sometimes");
        Assert.True(result.IsError);
        Assert.False(File.Exists(workspace.InstructionsFile));
    }

    [Fact]
    public async Task InitDomainRequiresAnInitializedRoot()
    {
        using var workspace = new TestWorkspace();
        var result = await InitDomain(workspace, "billing", "Billing", "Invoices and payments.");
        Assert.True(result.IsError);
        Assert.Contains("Initialize it with kb-init first", result.Text); // the real message reaches the model
        Assert.False(Directory.Exists(Path.Combine(workspace.KbRoot, "billing")));
    }

    [Fact]
    public async Task CreatesTopLevelDomainWithV02FrontmatterAndNoRawScaffolding()
    {
        using var workspace = new TestWorkspace();
        Assert.False((await InitKb(workspace, "automatic")).IsError);
        var instructionsBefore = File.ReadAllText(workspace.InstructionsFile);

        var result = await InitDomain(workspace, "billing", "Billing: Invoices", "Invoices #1 and payments: the full cycle.");

        Assert.False(result.IsError, result.Text);
        Assert.Contains("Files: domain.md, index.md, log.md", result.Text);
        var billing = Path.Combine(workspace.KbRoot, "billing");
        Assert.Equal(new[] { "domain.md", "index.md", "log.md" },
            Directory.EnumerateFiles(billing).Select(Path.GetFileName).OrderBy(n => n).ToArray());
        Assert.Empty(Directory.EnumerateDirectories(billing));

        var domainMd = File.ReadAllText(Path.Combine(billing, "domain.md"));
        Assert.Contains("title: \"Billing: Invoices\"", domainMd);
        Assert.Contains("description: \"Invoices #1 and payments: the full cycle.\"", domainMd);
        Assert.Matches(@"generated: \{ by: okf-knowledge-base/0\.2\.0, at: \d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}Z \}", domainMd);
        Assert.DoesNotContain("status:", domainMd);
        Assert.DoesNotContain("timestamp:", domainMd);

        foreach (var file in new[] { Path.Combine(billing, "index.md"), Path.Combine(workspace.KbRoot, "index.md") })
        {
            var text = File.ReadAllText(file);
            Assert.DoesNotContain("# Sources", text);
            Assert.DoesNotContain("raw/", text);
        }
        Assert.Contains("* [Billing: Invoices](billing/index.md) - Invoices #1 and payments: the full cycle.",
            File.ReadAllText(Path.Combine(workspace.KbRoot, "index.md")));
        Assert.Contains("* **Creation**: Established the [Billing: Invoices](billing/index.md) domain.",
            File.ReadAllText(Path.Combine(workspace.KbRoot, "log.md")));

        // Domain creation never touches the instructions file, and the new domain lints clean.
        Assert.Equal(instructionsBefore, File.ReadAllText(workspace.InstructionsFile));
        var lint = await _mcp.CallJsonAsync("kb_lint", TestCalls.Args(workspace));
        Assert.Empty(lint.Findings());
    }

    [Fact]
    public async Task CreatesNestedDomainRegisteredUnderItsParent()
    {
        using var workspace = new TestWorkspace();
        Assert.False((await InitKb(workspace, "automatic")).IsError);
        Assert.False((await InitDomain(workspace, "billing", "Billing", "Invoices and payments.")).IsError);

        var nested = await InitDomain(workspace, "eu", "EU Billing", "European invoicing rules.", parent: "billing");

        Assert.False(nested.IsError, nested.Text);
        var nestedPath = Path.Combine(workspace.KbRoot, "billing", "eu");
        Assert.Equal(new[] { "domain.md", "index.md", "log.md" },
            Directory.EnumerateFiles(nestedPath).Select(Path.GetFileName).OrderBy(n => n).ToArray());
        Assert.Contains("slug: billing/eu", File.ReadAllText(Path.Combine(nestedPath, "domain.md")));
        Assert.Contains("* [EU Billing](eu/index.md) - European invoicing rules.",
            File.ReadAllText(Path.Combine(workspace.KbRoot, "billing", "index.md")));
        Assert.Contains("* **Creation**: Established the [EU Billing](eu/index.md) sub-domain.",
            File.ReadAllText(Path.Combine(workspace.KbRoot, "billing", "log.md")));
        Assert.DoesNotContain("eu/index.md", File.ReadAllText(Path.Combine(workspace.KbRoot, "index.md")));
    }

    [Fact]
    public async Task PreservesDuplicateForceAndMissingParentBehavior()
    {
        using var workspace = new TestWorkspace();
        Assert.False((await InitKb(workspace, "automatic")).IsError);
        Assert.False((await InitDomain(workspace, "billing", "Billing", "Invoices and payments.")).IsError);

        var rawFile = Path.Combine(workspace.KbRoot, "billing", "raw", "user-owned.md");
        Directory.CreateDirectory(Path.GetDirectoryName(rawFile)!);
        File.WriteAllText(rawFile, "user-owned bytes\n");

        Assert.True((await InitDomain(workspace, "billing", "Billing", "Invoices and payments.")).IsError);
        Assert.False((await InitDomain(workspace, "billing", "Billing", "Invoices and payments.", force: true)).IsError);
        Assert.Equal("user-owned bytes\n", File.ReadAllText(rawFile));

        Assert.True((await InitDomain(workspace, "child", "Child", "Should fail.", parent: "missing")).IsError);
        Assert.False(Directory.Exists(Path.Combine(workspace.KbRoot, "missing")));
        Assert.Equal(1, Count(File.ReadAllText(Path.Combine(workspace.KbRoot, "index.md")), "* [Billing](billing/index.md)"));
    }
}
