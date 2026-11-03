using System.Text.Json.Nodes;

namespace KnowledgeBase.Mcp.Core;

/// <summary>Ranked concept-page search with snippets.</summary>
internal static class SearchEngine
{
    public static string Run(KbIndex index, string kbRoot, string query, string? domain, string? type, int limit, bool includeRaw)
    {
        var kbRootFull = Path.GetFullPath(kbRoot);
        var scanRoot = domain is not null ? Path.Combine(kbRootFull, domain) : kbRootFull;
        if (!Directory.Exists(scanRoot)) throw new KbException($"ERROR: {scanRoot} not found.");
        var scanRootFull = Path.GetFullPath(scanRoot);

        var qTerms = KbCommon.Tokens(query);
        var uniqueQ = Distinct(qTerms);
        var rawWords = KbCommon.RawWords(query);

        var hits = new List<(double Score, string Path, JsonObject Obj)>();
        foreach (var page in index.GetPages(kbRootFull))
        {
            if (page.IsReserved) continue;
            if (!KbPaths.IsUnder(scanRootFull, page.FullPath)) continue;
            var isRaw = KbPaths.IsRawArtifact(kbRootFull, page.FullPath);
            if (isRaw && !includeRaw) continue;
            if (type is not null && !string.Equals(page.Fm.GetString("type"), type, StringComparison.OrdinalIgnoreCase)) continue;

            var (score, matched) = Score(page, uniqueQ);
            if (score <= 0) continue;

            var titleStr = page.Fm.GetString("title");
            var obj = new JsonObject
            {
                ["path"] = page.RelPath,
                ["title"] = titleStr != "" ? titleStr : page.Name.Substring(0, page.Name.Length - 3),
                ["type"] = page.Fm.GetString("type"),
                ["description"] = page.Fm.GetString("description"),
                ["score"] = Math.Round(score, 2),
                ["matched_terms"] = matched,
                ["snippet"] = Snippet(page.Fm.Body, rawWords),
            };
            hits.Add((Math.Round(score, 2), page.RelPath, obj));
        }

        var ordered = hits
            .OrderByDescending(h => h.Score)
            .ThenBy(h => h.Path, StringComparer.Ordinal)
            .Take(limit)
            .Select(h => (JsonNode)h.Obj)
            .ToArray();

        var result = new JsonObject
        {
            ["kb_root"] = kbRoot,
            ["query_terms"] = new JsonArray(qTerms.Select(t => (JsonNode)t!).ToArray()),
            ["hits"] = new JsonArray(ordered),
        };
        return result.ToJsonString();
    }

    private static (double Score, JsonObject Matched) Score(KbPage page, List<string> uniqueQ)
    {
        var matched = new JsonObject();
        if (uniqueQ.Count == 0) return (0.0, matched);
        double total = 0.0;
        int matchedCount = 0;
        foreach (var t in uniqueQ)
        {
            double s = 0.0;
            if (page.TitleTokens.Contains(t)) s += 6.0;
            if (page.TagTokens.Contains(t)) s += 4.0;
            if (page.TypeTokens.Contains(t)) s += 3.0;
            if (page.DescTokens.Contains(t)) s += 3.0;
            if (page.BodyTokenCounts.TryGetValue(t, out var c)) s += 1.0 + 0.3 * Math.Min(c - 1, 5);
            if (s > 0) { matched[t] = Math.Round(s, 2); total += s; matchedCount++; }
        }
        double coverage = (double)matchedCount / uniqueQ.Count;
        return (total * (0.5 + 0.5 * coverage), matched);
    }

    private static string Snippet(string body, List<string> rawWords, int width = 160)
    {
        var low = body.ToLowerInvariant();
        foreach (var w in rawWords)
        {
            int i = low.IndexOf(w, StringComparison.Ordinal);
            if (i >= 0)
            {
                int start = Math.Max(0, i - width / 2);
                int end = Math.Min(body.Length, i + width / 2);
                var frag = body.Substring(start, end - start).Replace("\n", " ").Trim();
                return (start != 0 ? "\u2026" : "") + frag + (end < body.Length ? "\u2026" : "");
            }
        }
        var flat = body.Replace("\n", " ").Trim();
        return flat.Length > width ? flat.Substring(0, width) : flat;
    }

    private static List<string> Distinct(List<string> items)
    {
        var seen = new HashSet<string>(StringComparer.Ordinal);
        var outList = new List<string>();
        foreach (var t in items) if (seen.Add(t)) outList.Add(t);
        return outList;
    }
}
