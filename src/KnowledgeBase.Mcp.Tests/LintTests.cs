using Xunit;

namespace KnowledgeBase.Mcp.Tests;

public sealed class LintTests : IClassFixture<McpFixture>
{
    private const string RootIndex = "---\nokf_version: \"0.2\"\n---\n\n# Knowledge Base\n";
    private const string DomainMd = "---\ntype: Domain\ntitle: Billing\ndescription: Invoices and payments.\ngenerated: { by: human:test, at: 2026-10-01T00:00:00Z }\n---\n\n# Scope\n";

    private readonly McpFixture _mcp;

    public LintTests(McpFixture mcp)
    {
        _mcp = mcp;
    }

    private Task<System.Text.Json.JsonElement> Lint(TestWorkspace workspace, params (string, object?)[] extra) =>
        _mcp.CallJsonAsync("kb_lint", TestCalls.Args(workspace, extra));

    private static string Page(string frontmatter, string body = "Body.", string title = "T") =>
        $"---\ntype: Reference\ntitle: {title}\ndescription: D.\n{frontmatter}---\n\n{body}\n";

    [Fact]
    public async Task TreatsRootAndLegacyRawMarkdownAsOpaque()
    {
        using var workspace = new TestWorkspace();
        workspace.Write("index.md", RootIndex);
        workspace.Write("raw/root-source.md", "Opaque root source with a [broken link](missing.md).\n");
        workspace.Write("billing/raw/legacy-source.md", "Opaque legacy source with a [broken link](missing.md).\n");
        workspace.Write("billing/raw/first.md", "---\ntype: Reference\ntitle: Duplicate raw title\nresource: https://example.test/raw\n---\n\nRaw.\n");
        workspace.Write("billing/raw/second.md", "---\ntype: Reference\ntitle: Duplicate raw title\nresource: https://example.test/raw\n---\n\nRaw.\n");
        workspace.Write("billing/raw/index.md", "# Raw archive\n\n[missing](not-there.md)\n");
        workspace.Write("billing/raw/log.md", "# Raw archive log\n\n## not a date\n");

        var lint = await Lint(workspace);

        Assert.Equal(0, lint.GetProperty("summary").GetProperty("ERROR").GetInt32());
        Assert.Empty(lint.Findings());
    }

    [Fact]
    public async Task BodyLinksIntoRawWarnAndNeverCountForGraphHealth()
    {
        using var workspace = new TestWorkspace();
        workspace.Write("index.md", RootIndex);
        workspace.Write("billing/domain.md", DomainMd);
        workspace.Write("billing/log.md", "# Billing log\n\n[missing log target](missing-log.md)\n");
        workspace.Write("billing/concept.md", Page("", "Evidence is in the [raw source](raw/source.md)."));
        workspace.Write("billing/broken.md", Page("", "[missing concept target](missing-concept.md)"));
        workspace.Write("billing/raw/source.md", "Raw material can link to [the concept](../concept.md).\n");

        var findings = (await Lint(workspace)).Findings();

        Assert.True(findings.Has("raw-link", "billing/concept.md"));
        Assert.True(findings.Has("orphan", "billing/concept.md"));
        Assert.True(findings.Has("broken-link", "billing/broken.md"));
        Assert.False(findings.Has("broken-link", "billing/log.md"));
        Assert.DoesNotContain(findings, f => f.GetProperty("path").GetString()!.Contains("/raw/", StringComparison.Ordinal));
    }

    [Fact]
    public async Task DomainMdLinksDoNotResolveOrphansButConceptLinksDo()
    {
        using var workspace = new TestWorkspace();
        workspace.Write("index.md", RootIndex);
        workspace.Write("billing/domain.md", DomainMd + "\n# Entry points\n\n[a](a.md), [b](b.md)\n");
        workspace.Write("billing/a.md", Page("", "See [b](/billing/b.md)."));
        workspace.Write("billing/b.md", Page(""));

        var findings = (await Lint(workspace)).Findings();

        Assert.True(findings.Has("orphan", "billing/a.md"));
        Assert.False(findings.Has("orphan", "billing/b.md"));
    }

    [Fact]
    public async Task EmptyDomainsAreValid()
    {
        using var workspace = new TestWorkspace();
        workspace.Write("index.md", RootIndex);
        workspace.Write("billing/domain.md", DomainMd);
        workspace.Write("billing/index.md", "# Billing\n\n# Concepts\n");

        Assert.Empty((await Lint(workspace)).Findings());
    }

    [Fact]
    public async Task AcceptsWellFormedV02FamiliesIncludingBareVerifiedMapping()
    {
        using var workspace = new TestWorkspace();
        workspace.Write("index.md", RootIndex);
        workspace.Write("billing/domain.md", DomainMd);
        workspace.Write("billing/hub.md", Page("generated: { by: human:test, at: 2026-10-01T00:00:00Z }\n", "[retry](retry.md)"));
        workspace.Write("billing/retry.md", """
            ---
            type: Reference
            title: Retry policy
            description: How deliveries retry.
            resource: https://api.example.test/webhooks
            status: stable
            stale_after: 2999-01-01T00:00:00Z
            generated: { by: claude-code/claude-opus-5-5, at: 2026-10-01T12:00:00+02:00 }
            verified: { by: human:test, at: 2026-10-02T00:00:00Z }
            sources:
              - id: vendor-docs
                resource: https://docs.example.test/retries
                title: Vendor retry docs
                last_modified: 2026-09-01T00:00:00Z
              - id: chat
                resource: conversation on 2026-10-01
            ---

            Deliveries retry for 24 hours.[^vendor-docs] Agreed in review.[^chat]

            [^vendor-docs]: Vendor retry docs
            [^chat]: Design review
            """);
        workspace.Write("billing/hub2.md", Page("generated: { by: human:test, at: 2026-10-01T00:00:00Z }\nverified:\n  - { by: process:nightly, at: 2026-10-03T00:00:00Z }\n", "[hub](hub.md)"));

        var lint = await Lint(workspace);
        var findings = lint.Findings();

        Assert.DoesNotContain(findings, f => f.GetProperty("path").GetString() == "billing/retry.md");
        Assert.DoesNotContain(findings, f => f.GetProperty("code").GetString() is "verified" or "generated" or "sources" or "datetime" or "footnote");
    }

    [Fact]
    public async Task NestedSourceResourcesNeverLeakIntoTheTopLevelResource()
    {
        using var workspace = new TestWorkspace();
        workspace.Write("index.md", RootIndex);
        foreach (var name in new[] { "a", "b" })
        {
            workspace.Write($"billing/{name}.md", Page(
                $"resource: https://asset.example.test/{name}\nsources:\n  - id: shared\n    resource: https://docs.example.test/shared\n",
                "Claim.[^shared]", title: $"Page {name}"));
        }

        var findings = (await Lint(workspace)).Findings();

        Assert.DoesNotContain(findings, f => f.GetProperty("code").GetString() == "dup-resource");
    }

    [Fact]
    public async Task FlagsMalformedV02Families()
    {
        using var workspace = new TestWorkspace();
        workspace.Write("index.md", RootIndex);
        workspace.Write("bad/status.md", Page("status: active\n"));
        workspace.Write("bad/generated.md", Page("generated: { at: 2026-10-01T00:00:00Z }\n"));
        workspace.Write("bad/no-offset.md", Page("generated: { by: human:x, at: 2026-10-01T00:00:00 }\n"));
        workspace.Write("bad/verified.md", Page("verified:\n  - { by: human:x }\n"));
        workspace.Write("bad/sources.md", Page("sources:\n  - id: x\n    title: no resource\n  - id: x\n    resource: https://e.test\n"));
        workspace.Write("bad/footnote.md", Page("sources:\n  - id: real\n    resource: https://e.test\n", "Claim.[^typo]"));
        workspace.Write("bad/broken-source.md", Page("sources:\n  - id: gone\n    resource: /bad/missing.md\n", "Claim.[^gone]"));
        workspace.Write("bad/expired.md", Page("stale_after: 2001-01-01T00:00:00Z\n"));
        workspace.Write("bad/yaml.md", "---\ntype: Reference\ndescription: Cloud probe: VM facts\n---\n\nBody.\n");

        var findings = (await Lint(workspace)).Findings();

        Assert.True(findings.Has("status", "bad/status.md"));
        Assert.True(findings.Has("generated", "bad/generated.md"));
        Assert.True(findings.Has("datetime", "bad/no-offset.md"));
        Assert.True(findings.Has("verified", "bad/verified.md"));
        Assert.Equal(2, findings.Count(f => f.GetProperty("code").GetString() == "sources" && f.GetProperty("path").GetString() == "bad/sources.md"));
        Assert.True(findings.Has("footnote", "bad/footnote.md"));
        Assert.True(findings.Has("broken-source", "bad/broken-source.md"));
        Assert.True(findings.Has("stale", "bad/expired.md"));
        Assert.True(findings.Has("frontmatter", "bad/yaml.md"));
    }

    [Fact]
    public async Task CodeExamplesAreNotLinksOrFootnotes()
    {
        using var workspace = new TestWorkspace();
        workspace.Write("index.md", RootIndex);
        workspace.Write("docs/example.md", Page("", """
            Attribute a claim with `[^example-id]`, and link with `[x](/nowhere/x.md)`.

            ```markdown
            A fenced claim.[^fenced] See [missing](/missing.md).
            ```

            A real broken [link](/gone.md) and a real dangling footnote.[^real]
            """));

        var findings = (await Lint(workspace)).Findings();
        var messages = findings.Select(f => f.GetProperty("msg").GetString()!).ToArray();

        Assert.Single(findings, f => f.GetProperty("code").GetString() == "broken-link");
        Assert.Contains(messages, m => m.Contains("/gone.md"));
        Assert.Single(findings, f => f.GetProperty("code").GetString() == "footnote");
        Assert.Contains(messages, m => m.Contains("[^real]"));
    }

    [Fact]
    public async Task SourcesPointingAtConceptPagesAreLineageEdges()
    {
        using var workspace = new TestWorkspace();
        workspace.Write("index.md", RootIndex);
        workspace.Write("billing/derived.md", Page("sources:\n  - id: base\n    resource: /billing/base.md\n", "Built on it.[^base]"));
        workspace.Write("billing/base.md", Page(""));

        var findings = (await Lint(workspace)).Findings();

        Assert.False(findings.Has("orphan", "billing/base.md"));
    }

    [Fact]
    public async Task ReportsLegacyV01ShapesAsInformational()
    {
        using var workspace = new TestWorkspace();
        workspace.Write("index.md", "---\nokf_version: \"0.1\"\n---\n\n# Knowledge Base\n");
        workspace.Write("billing/old.md", Page("timestamp: 2026-01-01T00:00:00Z\n", "Fact.\n\n# Citations\n\n[1] Somewhere"));

        var lint = await Lint(workspace);
        var findings = lint.Findings();

        Assert.True(lint.GetProperty("conformant").GetBoolean());
        Assert.True(findings.Has("okf-version", "index.md"));
        Assert.Equal(2, findings.Count(f => f.GetProperty("code").GetString() == "legacy"));
        Assert.All(findings.Where(f => f.GetProperty("code").GetString() is "legacy" or "okf-version"),
            f => Assert.Equal("INFO", f.GetProperty("level").GetString()));
    }

    [Fact]
    public async Task StaleDaysUsesGeneratedAtThenLegacyTimestamp()
    {
        using var workspace = new TestWorkspace();
        workspace.Write("index.md", RootIndex);
        workspace.Write("billing/new.md", Page("generated: { by: human:x, at: 2001-01-01T00:00:00Z }\ntimestamp: 2999-01-01T00:00:00Z\n"));
        workspace.Write("billing/legacy.md", Page("timestamp: 2001-01-01T00:00:00Z\n"));

        var findings = (await Lint(workspace, ("stale_days", 30))).Findings();

        Assert.True(findings.Has("stale", "billing/new.md"));
        Assert.True(findings.Has("stale", "billing/legacy.md"));
    }
}
