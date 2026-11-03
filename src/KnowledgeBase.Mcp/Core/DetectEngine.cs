using System.Text.Json.Nodes;

namespace KnowledgeBase.Mcp.Core;

/// <summary>Ranks or lists KB domains for a topic. Deprecated domains are listed but never routed to.</summary>
internal static class DetectEngine
{
    private sealed class Domain
    {
        public required string Slug;
        public required string Title;
        public required string Description;
        public required List<string> Tags;
        public required string Status;
        public required HashSet<string> Strong;
        public required HashSet<string> Weak;
    }

    public static string Run(KbIndex index, string kbRoot, string? query, bool list, int limit)
    {
        var kbRootFull = Path.GetFullPath(kbRoot);
        var domains = LoadDomains(index, kbRootFull);

        if (domains.Count == 0)
        {
            var note = $"No domains found under {kbRoot}. Create one with kb-init-domain.";
            return new JsonObject { ["domains"] = new JsonArray(), ["note"] = note }.ToJsonString();
        }

        if (list || string.IsNullOrEmpty(query))
        {
            var arr = new JsonArray();
            foreach (var d in domains)
            {
                arr.Add((JsonNode)new JsonObject
                {
                    ["slug"] = d.Slug,
                    ["title"] = d.Title,
                    ["description"] = d.Description,
                    ["tags"] = new JsonArray(d.Tags.Select(t => (JsonNode)t!).ToArray()),
                    ["status"] = d.Status,
                });
            }
            return new JsonObject { ["kb_root"] = kbRoot, ["domains"] = arr }.ToJsonString();
        }

        var qTerms = KbCommon.Tokens(query);
        var scored = domains
            .Where(d => d.Status != "deprecated")
            .Select(d => { var (score, matched) = Score(d, qTerms); return (Domain: d, Score: score, Matched: matched); })
            .OrderByDescending(x => x.Score)
            .ThenBy(x => x.Domain.Slug, StringComparer.Ordinal)
            .ToList();

        var ranked = scored.Take(limit).ToList();
        double top = ranked.Count >= 1 ? ranked[0].Score : 0.0;
        double runner = ranked.Count >= 2 ? ranked[1].Score : 0.0;
        string confidence = (top >= 0.5 && (top - runner) >= 0.2) ? "high" : (top >= 0.25 ? "medium" : "low");
        string? recommendation = (confidence != "low" && ranked.Count >= 1) ? ranked[0].Domain.Slug : null;

        var ranking = new JsonArray();
        foreach (var r in ranked)
        {
            ranking.Add((JsonNode)new JsonObject
            {
                ["slug"] = r.Domain.Slug,
                ["title"] = r.Domain.Title,
                ["score"] = Math.Round(r.Score, 3),
                ["matched_terms"] = new JsonArray(r.Matched.Select(t => (JsonNode)t!).ToArray()),
                ["description"] = r.Domain.Description,
            });
        }

        var result = new JsonObject
        {
            ["kb_root"] = kbRoot,
            ["query_terms"] = new JsonArray(qTerms.Select(t => (JsonNode)t!).ToArray()),
            ["confidence"] = confidence,
            ["recommendation"] = recommendation is null ? null : recommendation,
            ["ranking"] = ranking,
        };
        return result.ToJsonString();
    }

    private static List<Domain> LoadDomains(KbIndex index, string kbRootFull)
    {
        var domains = new List<Domain>();
        if (!Directory.Exists(kbRootFull)) return domains;
        foreach (var page in index.GetPages(kbRootFull))
        {
            if (page.Name != "domain.md") continue;
            var rel = Path.GetRelativePath(kbRootFull, page.DirFullPath).Replace('\\', '/');
            if (rel == ".") continue;
            var title = page.Fm.GetString("title");
            var status = page.Fm.GetString("status");
            domains.Add(new Domain
            {
                Slug = rel,
                Title = title != "" ? title : rel,
                Description = page.Fm.GetString("description"),
                Tags = page.Fm.GetList("tags"),
                Status = status != "" ? status : "stable", // OKF v0.2 §5.4 default
                Strong = page.StrongTokens,
                Weak = page.WeakTokens,
            });
        }
        return domains.OrderBy(d => d.Slug, StringComparer.Ordinal).ToList();
    }

    private static (double Score, List<string> Matched) Score(Domain d, List<string> qTerms)
    {
        var q = new HashSet<string>(qTerms, StringComparer.Ordinal);
        if (q.Count == 0) return (0.0, new List<string>());
        var strong = new List<string>();
        var weak = new List<string>();
        foreach (var t in q)
        {
            if (d.Strong.Contains(t)) strong.Add(t);
            else if (d.Weak.Contains(t)) weak.Add(t);
        }
        double raw = 3.0 * strong.Count + 1.0 * weak.Count;
        strong.Sort(StringComparer.Ordinal);
        weak.Sort(StringComparer.Ordinal);
        var matched = new List<string>(strong);
        matched.AddRange(weak);
        return (raw / q.Count, matched);
    }
}
