using System.Globalization;
using System.Reflection;
using System.Text;
using System.Text.RegularExpressions;

namespace KnowledgeBase.Mcp.Core;

/// <summary>Creates a KB root (with its capture directive) and scaffolds OKF v0.2 domains.</summary>
internal static class InitEngine
{
    /// <summary>Actor (OKF v0.2 §7) recorded in generated.by for files this tool writes.</summary>
    public const string Actor = "okf-knowledge-base/0.2.0";

    private static readonly string[] Placeholders =
    {
        "<!-- Domains are registered here by the kb-init-domain skill. None yet. -->",
        "<!-- Domains registered here. -->",
        "<!-- Sub-domains are registered here by the kb-init-domain skill. None yet. -->",
    };

    private static readonly Regex DirectiveBlock =
        new(@"<knowledge-base>.*?</knowledge-base>", RegexOptions.Compiled | RegexOptions.Singleline);
    private static readonly Regex NonSlug = new("[^a-z0-9]+", RegexOptions.Compiled);

    private static string Today() => DateTime.UtcNow.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture);
    private static string NowIso() => DateTimeOffset.UtcNow.ToString("yyyy-MM-ddTHH:mm:ssZ", CultureInfo.InvariantCulture);

    private static string Slugify(string s) => NonSlug.Replace(s.Trim().ToLowerInvariant(), "-").Trim('-');

    private static List<string> SlugSegments(string raw) =>
        raw.Split('/').Select(Slugify).Where(x => x != "").ToList();

    private static string[] SplitLines(string t) =>
        t.Replace("\r\n", "\n").TrimEnd('\n').Split('\n');

    private static void WriteFile(string path, string text)
    {
        var dir = Path.GetDirectoryName(path);
        if (!string.IsNullOrEmpty(dir) && !Directory.Exists(dir)) Directory.CreateDirectory(dir);
        File.WriteAllText(path, text, new UTF8Encoding(false));
    }

    /// <summary>
    /// Creates the KB root files if absent and writes (or replaces) the capture
    /// directive block in the instructions file. Safe to re-run: switching
    /// capture mode or picking up a newer directive replaces the block in place.
    /// </summary>
    public static string InitKb(KbIndex index, string kbRoot, string captureMode, string? instructionsFile)
    {
        var resource = captureMode switch
        {
            "automatic" => "sentinel-automatic.md",
            "agent" => "sentinel-search.md",
            _ => throw new KbException($"ERROR: capture_mode must be 'automatic' or 'agent', not '{captureMode}'."),
        };

        var kbRootFull = Path.GetFullPath(kbRoot);
        var report = new List<string>();

        Directory.CreateDirectory(kbRootFull);
        var rootIndex = Path.Combine(kbRootFull, "index.md");
        if (!File.Exists(rootIndex))
        {
            WriteFile(rootIndex, "---\nokf_version: \"0.2\"\n---\n\n# Knowledge Base\n\n# Domains\n\n<!-- Domains registered here. -->\n");
            report.Add($"Created {rootIndex}.");
        }
        var rootLog = Path.Combine(kbRootFull, "log.md");
        if (!File.Exists(rootLog))
        {
            WriteFile(rootLog, $"# Knowledge Base Log\n\n## {Today()}\n* **Initialization**: Created the knowledge base.\n");
            report.Add($"Created {rootLog}.");
        }
        if (report.Count == 0) report.Add($"KB root {kbRootFull} already exists; left unchanged.");

        var target = Path.GetFullPath(!string.IsNullOrEmpty(instructionsFile)
            ? instructionsFile
            : Path.Combine(Path.GetDirectoryName(kbRootFull.TrimEnd('/', '\\')) ?? ".", "CLAUDE.md"));
        var kbPath = Path.GetRelativePath(Path.GetDirectoryName(target)!, kbRootFull).Replace('\\', '/') + "/";
        var block = LoadDirective(resource).Replace("{{kb_path}}", kbPath, StringComparison.Ordinal);
        report.Add(WriteDirective(target, block) + $" ({captureMode} capture)");

        index.Invalidate(kbRootFull);
        return "OK: " + string.Join("\n", report);
    }

    private static string LoadDirective(string resourceName)
    {
        using var stream = Assembly.GetExecutingAssembly().GetManifestResourceStream(resourceName)
            ?? throw new KbException($"ERROR: embedded directive {resourceName} is missing from this build.");
        using var reader = new StreamReader(stream, Encoding.UTF8);
        return reader.ReadToEnd().Replace("\r\n", "\n").Trim('\n');
    }

    private static string WriteDirective(string path, string block)
    {
        if (!File.Exists(path))
        {
            WriteFile(path, block + "\n");
            return $"Wrote the capture directive to new file {path}.";
        }
        var existing = File.ReadAllText(path).Replace("\r\n", "\n");
        var match = DirectiveBlock.Match(existing);
        if (match.Success)
        {
            if (match.Value == block) return $"Capture directive in {path} is already current.";
            WriteFile(path, existing.Substring(0, match.Index) + block + existing.Substring(match.Index + match.Length));
            return $"Replaced the capture directive in {path}.";
        }
        var trimmed = existing.TrimEnd('\n');
        WriteFile(path, trimmed + (trimmed.Length > 0 ? "\n\n" : "") + block + "\n");
        return $"Appended the capture directive to {path}.";
    }

    public static string InitDomain(KbIndex index, string kbRoot, string slugArg, string title, string desc,
        string? parent, string? tagsArg, bool force)
    {
        var raw = !string.IsNullOrEmpty(parent) ? $"{parent}/{slugArg}" : slugArg;
        var segments = SlugSegments(raw);
        if (segments.Count == 0) throw new KbException("ERROR: slug produced an empty identifier.");

        var slug = string.Join("/", segments);
        bool isSub = segments.Count > 1;
        var parentSegments = isSub ? segments.Take(segments.Count - 1).ToList() : new List<string>();
        var leaf = segments[^1];

        var kbRootFull = Path.GetFullPath(kbRoot);
        if (!File.Exists(Path.Combine(kbRootFull, "index.md")))
            throw new KbException($"ERROR: no knowledge base at {kbRootFull} (missing index.md). Initialize it with kb-init first.");

        var domainDir = Path.Combine(new[] { kbRootFull }.Concat(segments).ToArray());
        if (Directory.Exists(domainDir) && !force)
            throw new KbException($"ERROR: {domainDir} already exists. Use force to reuse.");

        if (isSub)
        {
            var parentDomainMd = Path.Combine(Path.Combine(new[] { kbRootFull }.Concat(parentSegments).ToArray()), "domain.md");
            if (!File.Exists(parentDomainMd))
                throw new KbException($"ERROR: parent domain '{string.Join("/", parentSegments)}' not found (expected {parentDomainMd}). Create it first with kb-init-domain.");
        }

        var tags = (tagsArg ?? "").Split(',').Select(x => x.Trim()).Where(x => x != "").ToList();
        var kind = isSub ? "sub-domain" : "domain";
        var tagStr = "[" + string.Join(", ", tags.Select(KbCommon.YamlScalar)) + "]";

        var domainMd =
            "---\n" +
            "type: Domain\n" +
            $"title: {KbCommon.YamlScalar(title)}\n" +
            $"description: {KbCommon.YamlScalar(desc)}\n" +
            $"slug: {slug}\n" +
            $"tags: {tagStr}\n" +
            $"generated: {{ by: {Actor}, at: {NowIso()} }}\n" +
            "---\n\n" +
            "# Scope\n\n" +
            $"{desc}\n\n" +
            $"**In scope:** _describe what belongs in this {kind}._\n\n" +
            "**Out of scope:** _describe what does not, and where it lives instead._\n\n" +
            "# Concept types\n\n" +
            "_List the kinds of concept pages this " + kind + " will hold (e.g. Entity, Playbook,\n" +
            "Reference, Metric). Add subdirectories (or nested sub-domains) as it grows._\n\n" +
            "# Entry points\n\n" +
            "_Link the most important pages here once they exist._\n";
        WriteFile(Path.Combine(domainDir, "domain.md"), domainMd);

        var indexMd =
            $"# {title}\n\n" +
            $"{desc}\n\n" +
            "See [domain.md](domain.md) for scope and conventions.\n\n" +
            "# Concepts\n\n" +
            "<!-- Concept pages are listed here as they are ingested. None yet. -->\n";
        WriteFile(Path.Combine(domainDir, "index.md"), indexMd);

        WriteFile(Path.Combine(domainDir, "log.md"),
            $"# {title} — Update Log\n\n## {Today()}\n* **Initialization**: Created the {title} {kind}.\n");

        string reg;
        if (isSub)
        {
            var parentDir = Path.Combine(new[] { kbRootFull }.Concat(parentSegments).ToArray());
            RegisterEntry(Path.Combine(parentDir, "index.md"), "# Sub-domains", $"{leaf}/index.md", title, desc);
            AddLogLine(Path.Combine(parentDir, "log.md"), $"* **Creation**: Established the [{title}]({leaf}/index.md) sub-domain.");
            reg = $"Registered as a sub-domain under '{string.Join("/", parentSegments)}' in {Path.Combine(parentDir, "index.md")}.";
        }
        else
        {
            RegisterEntry(Path.Combine(kbRootFull, "index.md"), "# Domains", $"{slug}/index.md", title, desc);
            AddLogLine(Path.Combine(kbRootFull, "log.md"), $"* **Creation**: Established the [{title}]({slug}/index.md) domain.");
            reg = $"Registered in {Path.Combine(kbRootFull, "index.md")}.";
        }

        index.Invalidate(kbRootFull);

        return $"OK: created {kind} '{slug}' at {domainDir}\n" +
               "Files: domain.md, index.md, log.md\n" +
               reg;
    }

    private static void RegisterEntry(string indexPath, string heading, string linkTarget, string title, string desc)
    {
        var entry = $"* [{title}]({linkTarget}) - {desc}";
        if (!File.Exists(indexPath))
        {
            WriteFile(indexPath, $"# {title}'s parent\n\n{heading}\n\n{entry}\n");
            return;
        }
        var lines = SplitLines(File.ReadAllText(indexPath)).Where(l => !Placeholders.Contains(l.Trim())).ToList();
        if (lines.Contains(entry)) return;

        int hi = -1;
        for (int i = 0; i < lines.Count; i++) if (lines[i].Trim() == heading) { hi = i; break; }
        if (hi < 0)
        {
            while (lines.Count > 0 && lines[^1].Trim() == "") lines.RemoveAt(lines.Count - 1);
            lines.AddRange(new[] { "", heading, "", entry });
        }
        else
        {
            int end = lines.Count;
            for (int j = hi + 1; j < lines.Count; j++) if (lines[j].StartsWith("# ", StringComparison.Ordinal)) { end = j; break; }
            int ins = end;
            while (ins - 1 > hi && lines[ins - 1].Trim() == "") ins--;
            lines.Insert(ins, entry);
        }
        WriteFile(indexPath, string.Join("\n", lines) + "\n");
    }

    private static void AddLogLine(string logPath, string line)
    {
        if (!File.Exists(logPath))
        {
            WriteFile(logPath, $"# Update Log\n\n## {Today()}\n{line}\n");
            return;
        }
        var log = File.ReadAllText(logPath);
        var stamp = $"## {Today()}";
        if (log.Contains(stamp, StringComparison.Ordinal))
        {
            int idx = log.IndexOf(stamp, StringComparison.Ordinal);
            log = log.Substring(0, idx) + stamp + "\n" + line + log.Substring(idx + stamp.Length);
        }
        else
        {
            var lines = SplitLines(log).ToList();
            int at = lines.Count;
            for (int i = 0; i < lines.Count; i++) if (lines[i].StartsWith("## ", StringComparison.Ordinal)) { at = i; break; }
            var head = at > 0 ? lines.Take(at) : Enumerable.Empty<string>();
            var tail = at < lines.Count ? lines.Skip(at) : Enumerable.Empty<string>();
            var merged = head.Concat(new[] { stamp, line, "" }).Concat(tail).ToList();
            log = string.Join("\n", merged).TrimEnd('\n') + "\n";
        }
        WriteFile(logPath, log);
    }
}
