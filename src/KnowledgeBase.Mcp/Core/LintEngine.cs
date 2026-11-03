using System.Globalization;
using System.Text;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;

namespace KnowledgeBase.Mcp.Core;

/// <summary>OKF v0.2 concept-page conformance plus wiki-hygiene lint.</summary>
internal static class LintEngine
{
    private sealed record Finding(string Level, string Code, string Path, string Msg, int Order);

    private static readonly string[] Reserved = { "index.md", "log.md" };
    private static readonly string[] Recommended = { "title", "description" };
    private static readonly HashSet<string> Statuses = new(StringComparer.Ordinal) { "draft", "stable", "deprecated" };
    private static readonly Regex LinkRe = new(@"\[[^\]]*\]\(([^)]+)\)", RegexOptions.Compiled);
    private static readonly Regex FootnoteRe = new(@"\[\^([^\]\s]+)\]", RegexOptions.Compiled);
    private static readonly Regex CitationsHeading = new(@"^#\s+Citations\s*$", RegexOptions.Compiled | RegexOptions.Multiline);
    // Fenced blocks and inline code spans hold examples, not live links or footnotes.
    private static readonly Regex CodeRe = new(@"^(```|~~~).*?^\1[^\n]*$|`[^`\n]+`", RegexOptions.Compiled | RegexOptions.Multiline | RegexOptions.Singleline);
    private static readonly Regex IsoDate = new(@"^\d{4}-\d{2}-\d{2}$", RegexOptions.Compiled);
    private static readonly Regex IsoInstant = new(@"^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}(:\d{2}(\.\d+)?)?(Z|[+-]\d{2}:\d{2})$", RegexOptions.Compiled);
    private static readonly Regex SchemeRe = new(@"^[a-z][a-z0-9+.-]*://", RegexOptions.Compiled | RegexOptions.IgnoreCase);
    private static readonly Dictionary<string, int> Rank = new() { ["ERROR"] = 0, ["WARNING"] = 1, ["INFO"] = 2 };

    /// <summary>Returns the JSON result and whether ERROR-level findings exist.</summary>
    public static (string Json, bool HasErrors) Run(KbIndex index, string kbRoot, string? domain, bool fixIndex, int staleDays)
    {
        var kbRootFull = Path.GetFullPath(kbRoot);
        var scanRoot = domain is not null ? Path.Combine(kbRootFull, domain) : kbRootFull;
        if (!Directory.Exists(scanRoot)) throw new KbException($"ERROR: {scanRoot} not found.");
        var scanRootFull = Path.GetFullPath(scanRoot);
        var now = DateTimeOffset.UtcNow;

        var findings = new List<Finding>();
        int seq = 0;
        void Add(string level, string code, string path, string msg) => findings.Add(new Finding(level, code, path, msg, seq++));

        string Rel(string full) => KbPaths.Rel(kbRootFull, full);

        var conceptByFull = new Dictionary<string, KbPage>(StringComparer.OrdinalIgnoreCase);
        var titles = new Dictionary<string, List<string>>(StringComparer.Ordinal);
        var resources = new Dictionary<string, List<string>>(StringComparer.Ordinal);
        var linkTargets = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
        var dirChildren = new Dictionary<string, HashSet<string>>(StringComparer.OrdinalIgnoreCase);

        var pages = index.GetPages(kbRootFull)
            .Where(p => KbPaths.IsUnder(scanRootFull, p.FullPath))
            .OrderBy(p => p.FullPath, StringComparer.Ordinal)
            .ToList();

        foreach (var page in pages)
        {
            var full = page.FullPath;
            var fm = page.Fm;

            // The Raw Source Archive is user-owned and opaque to lint.
            if (KbPaths.IsRawArtifact(kbRootFull, full))
                continue;

            if (page.IsReserved)
            {
                LintReserved(page, kbRootFull, Rel(full), Add);
                continue;
            }

            var r = Rel(full);
            if (!fm.Ok) { Add("ERROR", "frontmatter", r, "missing/unparseable frontmatter: " + fm.Err); continue; }
            if (fm.GetString("type").Trim() == "") Add("ERROR", "type", r, "frontmatter missing a non-empty `type`");

            conceptByFull[full] = page;
            var dir = page.DirFullPath;
            if (!dirChildren.TryGetValue(dir, out var set)) { set = new HashSet<string>(StringComparer.Ordinal); dirChildren[dir] = set; }
            set.Add(page.Name);

            foreach (var field in Recommended)
            {
                if (fm.GetString(field).Trim() == "") Add("INFO", "recommended", r, $"missing recommended field `{field}`");
            }

            var title = fm.GetString("title");
            if (title != "") AddToMap(titles, title, r);
            var resource = fm.GetString("resource");
            if (resource != "") AddToMap(resources, resource, r);

            LintLifecycle(fm, r, now, staleDays, Add);
            LintTrust(fm, r, Add);
            var prose = CodeRe.Replace(fm.Body, "");
            var sourceIds = LintSources(fm, page, kbRootFull, r, linkTargets, Add);
            LintFootnotes(fm, prose, sourceIds, r, Add);

            // A link asserts a relationship only when it comes from a concept page:
            // domain.md routing/entry-point links never resolve an orphan.
            bool countsForGraph = page.Name != "domain.md";
            foreach (Match m in LinkRe.Matches(prose))
            {
                var target = m.Groups[1].Value;
                var resolved = ResolveKbPath(target, full, kbRootFull);
                if (resolved is null) continue;
                if (KbPaths.IsUnder(kbRootFull, resolved) && KbPaths.IsRawArtifact(kbRootFull, resolved))
                {
                    Add("WARNING", "raw-link", r, $"body links into the Raw Source Archive ({target}); cite it from `sources` instead");
                    continue;
                }
                if (File.Exists(resolved) || Directory.Exists(resolved))
                {
                    if (countsForGraph) linkTargets.Add(Path.GetFullPath(resolved));
                }
                else Add("WARNING", "broken-link", r, $"link target does not exist: {target}");
            }
        }

        foreach (var full in conceptByFull.Keys)
        {
            if (Path.GetFileName(full) == "domain.md") continue;
            if (!linkTargets.Contains(Path.GetFullPath(full)))
                Add("WARNING", "orphan", Rel(full), "no concept page links here (orphaned)");
        }

        foreach (var (t, ps0) in titles)
        {
            var ps = ps0.OrderBy(x => x, StringComparer.Ordinal).ToList();
            if (ps.Count > 1)
                Add("WARNING", "dup-title", ps[0], "title " + PyRepr(t) + " shared by: " + string.Join(", ", ps));
        }
        foreach (var (res, ps0) in resources)
        {
            var ps = ps0.OrderBy(x => x, StringComparer.Ordinal).ToList();
            if (ps.Count > 1)
                Add("WARNING", "dup-resource", ps[0], "resource " + PyRepr(res) + " shared by: " + string.Join(", ", ps));
        }

        bool wroteFile = false;
        foreach (var (dir, children) in dirChildren)
        {
            var concepts = children.Where(c => !Reserved.Contains(c) && c != "domain.md").OrderBy(c => c, StringComparer.Ordinal).ToList();
            var indexPath = Path.Combine(dir, "index.md");
            bool indexExists = File.Exists(indexPath);
            var listed = new HashSet<string>(StringComparer.Ordinal);
            if (indexExists)
            {
                foreach (Match m in LinkRe.Matches(File.ReadAllText(indexPath)))
                    listed.Add(Path.GetFileName(m.Groups[1].Value.Split('#')[0].Trim().TrimEnd('/')));
            }
            var missing = concepts.Where(c => !listed.Contains(c)).ToList();
            if (missing.Count > 0 && indexExists)
                Add("WARNING", "index-drift", Rel(indexPath), "index.md omits: " + string.Join(", ", missing));

            if (fixIndex && indexExists)
            {
                RewriteIndex(indexPath, dir, concepts, conceptByFull);
                wroteFile = true;
            }
        }
        if (wroteFile) index.Invalidate(kbRootFull);

        var counts = new Dictionary<string, int> { ["ERROR"] = 0, ["WARNING"] = 0, ["INFO"] = 0 };
        foreach (var f in findings) counts[f.Level]++;

        var sorted = findings
            .OrderBy(f => Rank[f.Level])
            .ThenBy(f => f.Code, StringComparer.Ordinal)
            .ThenBy(f => f.Path, StringComparer.Ordinal)
            .ThenBy(f => f.Order)
            .ToList();

        var findingsArr = new JsonArray();
        foreach (var f in sorted)
            findingsArr.Add((JsonNode)new JsonObject { ["level"] = f.Level, ["code"] = f.Code, ["path"] = f.Path, ["msg"] = f.Msg });

        var result = new JsonObject
        {
            ["summary"] = new JsonObject { ["ERROR"] = counts["ERROR"], ["WARNING"] = counts["WARNING"], ["INFO"] = counts["INFO"] },
            ["conformant"] = counts["ERROR"] == 0,
            ["findings"] = findingsArr,
        };
        return (result.ToJsonString(), counts["ERROR"] > 0);
    }

    private static void LintReserved(KbPage page, string kbRootFull, string r, Action<string, string, string, string> add)
    {
        var fm = page.Fm;
        if (page.Name == "index.md")
        {
            bool isRoot = string.Equals(Path.GetDirectoryName(Path.GetFullPath(page.FullPath)), kbRootFull, StringComparison.OrdinalIgnoreCase);
            bool onlyOkf = fm.Keys.All(k => k == "okf_version");
            if (fm.Ok && fm.KeyCount > 0 && !(isRoot && onlyOkf))
            {
                add("ERROR", "index-frontmatter", r,
                    "index.md must not carry frontmatter (except okf_version in the bundle-root index.md)");
            }
            if (isRoot && fm.Ok && fm.Has("okf_version") && fm.GetString("okf_version") != "0.2")
            {
                add("INFO", "okf-version", r, $"bundle declares okf_version {PyRepr(fm.GetString("okf_version"))}; this plugin targets 0.2");
            }
        }
        else if (page.Name == "log.md")
        {
            foreach (var line in page.RawText.Split('\n'))
            {
                if (line.StartsWith("## ", StringComparison.Ordinal) && !IsoDate.IsMatch(line.Substring(3).Trim()))
                {
                    add("WARNING", "log-date", r, "log heading is not ISO YYYY-MM-DD: " + PyRepr(line.Trim()));
                }
            }
        }
    }

    private static void LintLifecycle(Frontmatter fm, string r, DateTimeOffset now, int staleDays, Action<string, string, string, string> add)
    {
        if (fm.Has("status") && !Statuses.Contains(fm.GetString("status")))
            add("WARNING", "status", r, $"status {PyRepr(fm.GetString("status"))} is not one of draft, stable, deprecated");

        if (fm.Has("stale_after"))
        {
            var raw = fm.GetString("stale_after");
            if (!TryInstant(raw, out var staleAfter))
                add("WARNING", "datetime", r, "stale_after is not an ISO 8601 datetime with a UTC offset: " + PyRepr(raw));
            else if (now >= staleAfter)
                add("INFO", "stale", r, $"stale since {raw} (stale_after)");
        }

        // Freshness: v0.2 generated.at, falling back to the legacy v0.1 timestamp.
        var generatedAt = AsMap(fm.Raw("generated")) is { } gen ? Frontmatter.AsString(Frontmatter.Lookup(gen, "at")) : "";
        var legacy = fm.GetString("timestamp");
        if (!fm.Has("generated"))
        {
            if (legacy != "")
                add("INFO", "legacy", r, "uses the v0.1 `timestamp`; v0.2 records it as `generated: { by, at }`");
            else
                add("INFO", "recommended", r, "missing recommended field `generated`");
        }
        if (legacy != "" && !TryLegacyInstant(legacy, out _))
            add("WARNING", "timestamp", r, "unparseable timestamp: " + PyRepr(legacy));

        if (staleDays != 0)
        {
            var basis = generatedAt != "" ? generatedAt : legacy;
            if (basis != "" && TryLegacyInstant(basis, out var changed))
            {
                var age = (now - changed).Days;
                if (age > staleDays) add("INFO", "stale", r, $"last changed {age} days ago");
            }
        }
    }

    private static void LintTrust(Frontmatter fm, string r, Action<string, string, string, string> add)
    {
        if (fm.Has("generated"))
        {
            if (AsMap(fm.Raw("generated")) is not { } gen)
                add("WARNING", "generated", r, "`generated` must be a mapping with `by` (and usually `at`)");
            else
            {
                if (Frontmatter.AsString(Frontmatter.Lookup(gen, "by")).Trim() == "")
                    add("WARNING", "generated", r, "`generated.by` is required (an actor, e.g. agent/model or human:<id>)");
                var at = Frontmatter.AsString(Frontmatter.Lookup(gen, "at"));
                if (at != "" && !TryInstant(at, out _))
                    add("WARNING", "datetime", r, "generated.at is not an ISO 8601 datetime with a UTC offset: " + PyRepr(at));
            }
        }

        if (fm.Has("verified"))
        {
            // A bare mapping is a one-element list (OKF v0.2 §5.2).
            var raw = fm.Raw("verified");
            var events = raw is List<object> list ? list : new List<object> { raw! };
            foreach (var ev in events)
            {
                if (AsMap(ev) is not { } map)
                {
                    add("WARNING", "verified", r, "each `verified` entry must be a mapping with `by` and `at`");
                    continue;
                }
                if (Frontmatter.AsString(Frontmatter.Lookup(map, "by")).Trim() == "")
                    add("WARNING", "verified", r, "a `verified` entry is missing `by`");
                var at = Frontmatter.AsString(Frontmatter.Lookup(map, "at"));
                if (at == "")
                    add("WARNING", "verified", r, "a `verified` entry is missing `at`");
                else if (!TryInstant(at, out _))
                    add("WARNING", "datetime", r, "verified.at is not an ISO 8601 datetime with a UTC offset: " + PyRepr(at));
            }
        }
    }

    private static HashSet<string> LintSources(Frontmatter fm, KbPage page, string kbRootFull, string r,
        HashSet<string> linkTargets, Action<string, string, string, string> add)
    {
        var ids = new HashSet<string>(StringComparer.Ordinal);
        if (!fm.Has("sources")) return ids;
        if (fm.Raw("sources") is not List<object> entries)
        {
            add("WARNING", "sources", r, "`sources` must be a list of entries");
            return ids;
        }

        foreach (var entry in entries)
        {
            if (AsMap(entry) is not { } map)
            {
                add("WARNING", "sources", r, "each `sources` entry must be a mapping with `resource`");
                continue;
            }
            var id = Frontmatter.AsString(Frontmatter.Lookup(map, "id"));
            if (id != "" && !ids.Add(id))
                add("WARNING", "sources", r, $"duplicate sources id {PyRepr(id)}");

            var res = Frontmatter.AsString(Frontmatter.Lookup(map, "resource")).Trim();
            if (res == "")
            {
                add("WARNING", "sources", r, "a `sources` entry is missing `resource`");
                continue;
            }
            var lastModified = Frontmatter.AsString(Frontmatter.Lookup(map, "last_modified"));
            if (lastModified != "" && !TryInstant(lastModified, out _))
                add("WARNING", "datetime", r, "sources.last_modified is not an ISO 8601 datetime with a UTC offset: " + PyRepr(lastModified));

            // A resource is a path only when it looks like one; otherwise it is a
            // URL or a scope descriptor (e.g. "conversation on 2026-10-26").
            if (!LooksLikePath(res)) continue;
            var resolved = ResolveKbPath(res, page.FullPath, kbRootFull);
            if (resolved is null) continue;
            if (!File.Exists(resolved) && !Directory.Exists(resolved))
                add("WARNING", "broken-source", r, $"sources resource does not exist: {res}");
            else if (page.Name != "domain.md" && !KbPaths.IsRawArtifact(kbRootFull, resolved))
                linkTargets.Add(Path.GetFullPath(resolved)); // lineage edge (OKF v0.2 §5.1)
        }
        return ids;
    }

    private static void LintFootnotes(Frontmatter fm, string prose, HashSet<string> sourceIds, string r, Action<string, string, string, string> add)
    {
        var reported = new HashSet<string>(StringComparer.Ordinal);
        foreach (Match m in FootnoteRe.Matches(prose))
        {
            var label = m.Groups[1].Value;
            if (!sourceIds.Contains(label) && reported.Add(label))
                add("WARNING", "footnote", r, $"footnote [^{label}] has no matching `sources` id");
        }
        if (!fm.Has("sources") && CitationsHeading.IsMatch(fm.Body))
            add("INFO", "legacy", r, "uses a v0.1 `# Citations` list; v0.2 records provenance in `sources` with [^id] footnotes");
    }

    private static List<KeyValuePair<string, object>>? AsMap(object? value) =>
        value as List<KeyValuePair<string, object>>;

    private static bool TryInstant(string value, out DateTimeOffset instant)
    {
        instant = default;
        return IsoInstant.IsMatch(value)
            && DateTimeOffset.TryParse(value, CultureInfo.InvariantCulture, DateTimeStyles.None, out instant);
    }

    private static bool TryLegacyInstant(string value, out DateTimeOffset instant) =>
        DateTimeOffset.TryParse(value.Replace("Z", "+00:00"), CultureInfo.InvariantCulture,
            DateTimeStyles.AssumeUniversal, out instant);

    private static bool LooksLikePath(string value) =>
        !SchemeRe.IsMatch(value) && !value.Contains(' ')
        && (value.StartsWith('/') || value.StartsWith("./", StringComparison.Ordinal)
            || value.StartsWith("../", StringComparison.Ordinal) || value.EndsWith(".md", StringComparison.OrdinalIgnoreCase));

    private static void AddToMap(Dictionary<string, List<string>> map, string key, string value)
    {
        if (!map.TryGetValue(key, out var l)) { l = new List<string>(); map[key] = l; }
        l.Add(value);
    }

    private static string? ResolveKbPath(string target, string pagePath, string kbRootFull)
    {
        var t = target.Split('#')[0].Trim();
        if (t == "" || SchemeRe.IsMatch(t) || t.StartsWith("mailto:", StringComparison.Ordinal)) return null;
        if (t.StartsWith("/", StringComparison.Ordinal))
            return Path.GetFullPath(Path.Combine(kbRootFull, t.TrimStart('/')));
        return Path.GetFullPath(Path.Combine(Path.GetDirectoryName(pagePath)!, t));
    }

    private static void RewriteIndex(string indexPath, string dir, List<string> concepts, Dictionary<string, KbPage> conceptByFull)
    {
        var lines = new List<string> { "", "# Concepts", "" };
        foreach (var c in concepts)
        {
            conceptByFull.TryGetValue(Path.Combine(dir, c), out var page);
            var title = page is not null && page.Fm.GetString("title") != "" ? page.Fm.GetString("title") : c.Substring(0, c.Length - 3);
            var desc = page is not null ? page.Fm.GetString("description") : "";
            lines.Add($"* [{title}]({c})" + (desc != "" ? $" - {desc}" : ""));
        }
        var block = string.Join("\n", lines) + "\n";
        var text = File.ReadAllText(indexPath);
        if (text.Contains("# Concepts", StringComparison.Ordinal))
        {
            int at = text.IndexOf("# Concepts", StringComparison.Ordinal);
            var head = text.Substring(0, at);
            var rest = text.Substring(at);
            int nl = rest.IndexOf("\n# ", StringComparison.Ordinal);
            var tail = nl >= 0 ? rest.Substring(nl) : "";
            text = head.TrimEnd() + "\n" + block + tail;
        }
        else
        {
            text = text.TrimEnd() + "\n" + block;
        }
        File.WriteAllText(indexPath, text, new UTF8Encoding(false));
    }

    /// <summary>Python-style repr for quoted values in messages.</summary>
    private static string PyRepr(string s)
    {
        char quote = '\'';
        if (s.Contains('\'') && !s.Contains('"')) quote = '"';
        var sb = new StringBuilder();
        sb.Append(quote);
        foreach (var ch in s)
        {
            if (ch == '\\') sb.Append("\\\\");
            else if (ch == '\n') sb.Append("\\n");
            else if (ch == '\r') sb.Append("\\r");
            else if (ch == '\t') sb.Append("\\t");
            else if (ch == quote) sb.Append('\\').Append(ch);
            else sb.Append(ch);
        }
        sb.Append(quote);
        return sb.ToString();
    }
}
