using System.ComponentModel;
using KnowledgeBase.Mcp.Core;
using ModelContextProtocol.Server;

namespace KnowledgeBase.Mcp.Tools;

// Parameter names are deliberately snake_case so the generated MCP input schema
// matches the argument names the skills pass (kb_root, include_raw, …).
#pragma warning disable IDE1006 // Naming Styles

[McpServerToolType]
internal sealed class KbTools
{
    private const string KbRootDescription =
        "Absolute path to the knowledge base root (the kb/ directory holding index.md and the domain folders). Required; makes the call independent of the working directory.";

    private static readonly KbIndex Index = KbIndex.Shared;

    [McpServerTool(Name = "kb_search", ReadOnly = true)]
    [Description("Ranks concept pages by query relevance and returns compact JSON hits with snippets and matched terms. Used by the kb-search skill, which wraps it with orientation, cross-link traversal, and citation — prefer that skill for answering questions.")]
    public string KbSearch(
        [Description(KbRootDescription)] string kb_root,
        [Description("The natural-language search query.")] string query,
        [Description("Restrict the search to one (sub-)domain slug, e.g. \"billing\" or \"billing/eu\".")] string? domain = null,
        [Description("Restrict to a frontmatter type, e.g. \"Playbook\".")] string? type = null,
        [Description("Maximum number of hits to return (default 10).")] int limit = 10,
        [Description("Also search user-owned Markdown Raw Artifacts under raw/ (off by default).")] bool include_raw = false)
    {
        return SearchEngine.Run(Index, kb_root, query, domain, type, limit, include_raw);
    }

    [McpServerTool(Name = "kb_detect_domain", ReadOnly = true)]
    [Description("Routes a topic to the best-matching knowledge-base domain, or lists all domains. With a query, returns ranked domains plus a confidence and recommendation (deprecated domains are never routed to); with list=true or no query, returns the domain catalog. Used by the kb-ingest and kb-capture skills. This routes; it does not search page content (use kb_search for that).")]
    public string KbDetectDomain(
        [Description(KbRootDescription)] string kb_root,
        [Description("Topic text to route to a domain. Omit (or set list=true) to list domains.")] string? query = null,
        [Description("List all domains instead of scoring a query.")] bool list = false,
        [Description("Maximum number of ranked domains to return (default 5).")] int limit = 5)
    {
        return DetectEngine.Run(Index, kb_root, query, list, limit);
    }

    [McpServerTool(Name = "kb_lint")]
    [Description("Lints the knowledge base for OKF v0.2 concept-page conformance and wiki hygiene (frontmatter, provenance/trust/lifecycle fields, broken links, orphans, index drift, staleness) and returns JSON with summary, conformant, and findings. conformant=false means ERROR-level findings exist; that is a valid response, not a tool failure. Used by the kb-lint skill and after every write.")]
    public string KbLint(
        [Description(KbRootDescription)] string kb_root,
        [Description("Restrict linting to one (sub-)domain slug.")] string? domain = null,
        [Description("Rewrite drifted index.md concept lists in place to match the pages on disk.")] bool fix_index = false,
        [Description("Also flag pages whose generated.at (or legacy timestamp) is older than this many days (0 disables; stale_after is always checked).")] int stale_days = 0)
    {
        return LintEngine.Run(Index, kb_root, domain, fix_index, stale_days).Json;
    }

    [McpServerTool(Name = "kb_analyze", ReadOnly = true)]
    [Description("Finds consolidation candidates: clusters of concept pages with high term overlap that may be duplicates, split into within-domain and cross-domain groups with similarity and estimated byte savings. Used by the kb-consolidate skill.")]
    public string KbAnalyze(
        [Description(KbRootDescription)] string kb_root,
        [Description("Analyze within one (sub-)domain only.")] string? domain = null,
        [Description("Minimum Jaccard similarity to report a pair (default 0.4).")] double min_similarity = 0.4,
        [Description("Minimum number of shared terms to report a pair (default 4).")] int min_shared_terms = 4,
        [Description("Skip ultra-common terms appearing in more than this many pages (default 200).")] int max_postings = 200,
        [Description("Maximum number of groups to return per scope (default 50).")] int limit = 50,
        [Description("Also include Markdown Raw Artifacts from raw/ directories (off by default).")] bool include_raw = false)
    {
        return AnalyzeEngine.Run(Index, kb_root, min_similarity, min_shared_terms, max_postings, limit, include_raw, domain);
    }

    [McpServerTool(Name = "kb_init", Destructive = true, ReadOnly = false)]
    [Description("Bootstraps a knowledge base: creates the kb/ root (index.md declaring okf_version 0.2, and log.md) if absent, and writes or replaces the <knowledge-base> capture directive in the repository instructions file. capture_mode 'automatic' writes the full directive (search first, end-of-turn kb-capture); 'agent' writes a search-only directive and leaves capture to the knowledge-curator agent. Re-running switches mode or refreshes the directive. Used by the kb-init skill.")]
    public string KbInit(
        [Description("Absolute path of the kb/ root to create or reuse.")] string kb_root,
        [Description("'automatic' (directive runs kb-capture every turn) or 'agent' (search-only directive; capture only via the knowledge-curator agent).")] string capture_mode,
        [Description("Instructions file to write the directive into (default: CLAUDE.md beside kb/).")] string? instructions_file = null)
    {
        return InitEngine.InitKb(Index, kb_root, capture_mode, instructions_file);
    }

    [McpServerTool(Name = "kb_init_domain", Destructive = true, ReadOnly = false)]
    [Description("Scaffolds a new OKF v0.2 domain (or nested sub-domain) with domain.md, index.md, and log.md, and registers it in the parent catalog. Requires an existing KB root (run kb-init first). Returns a status line. Used by the kb-init-domain skill, which settles naming and scope first.")]
    public string KbInitDomain(
        [Description(KbRootDescription)] string kb_root,
        [Description("Domain slug (kebab-case). Use \"parent/child\" or the parent argument for a sub-domain.")] string slug,
        [Description("Human-readable domain title.")] string title,
        [Description("One-sentence scope description; the key input for auto-routing.")] string description,
        [Description("Parent domain slug when creating a sub-domain.")] string? parent = null,
        [Description("Comma-separated tags for the domain frontmatter.")] string? tags = null,
        [Description("Reuse an existing domain directory instead of erroring.")] bool force = false)
    {
        return InitEngine.InitDomain(Index, kb_root, slug, title, description, parent, tags, force);
    }
}
