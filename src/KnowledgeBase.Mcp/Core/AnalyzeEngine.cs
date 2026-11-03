using System.Text.Json.Nodes;

namespace KnowledgeBase.Mcp.Core;

/// <summary>Consolidation-candidate clustering over concept pages.</summary>
internal static class AnalyzeEngine
{
    private sealed class Page
    {
        public required string Path;
        public required string Domain;
        public required HashSet<string> Tokens;
        public required long Bytes;
    }

    private readonly record struct Edge(int I, int J, double Jac);

    public static string Run(KbIndex index, string kbRoot, double minSim, int minShared, int maxPostings, int limit, bool includeRaw, string? domain)
    {
        var kbRootFull = Path.GetFullPath(kbRoot);
        var scanRoot = domain is not null ? Path.Combine(kbRootFull, domain) : kbRootFull;
        return Run(index, kbRoot, scanRoot, minSim, minShared, maxPostings, limit, includeRaw, domain);
    }

    private static string Run(KbIndex index, string kbRoot, string scanRoot, double minSim, int minShared, int maxPostings, int limit, bool includeRaw, string? domain)
    {
        var kbRootFull = Path.GetFullPath(kbRoot);
        if (!Directory.Exists(scanRoot)) throw new KbException($"ERROR: {scanRoot} not found.");
        var scanRootFull = Path.GetFullPath(scanRoot);

        var pages = LoadPages(index, kbRootFull, scanRootFull, includeRaw);
        var edges = CandidateEdges(pages, minSim, minShared, maxPostings);
        var withinEdges = edges.Where(e => pages[e.I].Domain == pages[e.J].Domain).ToList();
        var within = BuildClusters(pages, withinEdges).Take(limit).ToList();
        var cross = BuildClusters(pages, edges).Where(c => (string)c["scope"]! == "cross-domain").Take(limit).ToList();

        long estTotal = 0;
        foreach (var c in within.Concat(cross)) estTotal += (long)c["est_saving_bytes"]!;

        var result = new JsonObject
        {
            ["kb_root"] = kbRoot,
            ["params"] = new JsonObject
            {
                ["min_similarity"] = minSim,
                ["min_shared_terms"] = minShared,
                ["max_postings"] = maxPostings,
            },
            ["pages_analyzed"] = pages.Count,
            ["within_domain"] = new JsonArray(within.Cast<JsonNode>().ToArray()),
            ["cross_domain"] = new JsonArray(cross.Cast<JsonNode>().ToArray()),
            ["summary"] = new JsonObject
            {
                ["within_domain_groups"] = within.Count,
                ["cross_domain_groups"] = cross.Count,
                ["est_total_saving_bytes"] = estTotal,
            },
        };
        return result.ToJsonString();
    }

    private static List<Page> LoadPages(KbIndex index, string kbRootFull, string scanRootFull, bool includeRaw)
    {
        var pages = new List<Page>();
        foreach (var page in index.GetPages(kbRootFull))
        {
            if (page.IsReserved || page.Name == "domain.md") continue;
            if (!KbPaths.IsUnder(scanRootFull, page.FullPath)) continue;
            var relDir = Path.GetRelativePath(scanRootFull, page.DirFullPath);
            if (!includeRaw && relDir.Split('\\', '/').Contains("raw")) continue;
            pages.Add(new Page
            {
                Path = page.RelPath,
                Domain = PageDomain(kbRootFull, page.FullPath),
                Tokens = page.BlobTokens,
                Bytes = page.ByteCount,
            });
        }
        return pages.OrderBy(p => p.Path, StringComparer.Ordinal).ToList();
    }

    private static string PageDomain(string kbRootFull, string pagePath)
    {
        var d = Path.GetDirectoryName(pagePath)!;
        var root = Path.GetFullPath(kbRootFull);
        while (true)
        {
            if (File.Exists(Path.Combine(d, "domain.md")))
            {
                var rel = Path.GetRelativePath(kbRootFull, d).Replace('\\', '/');
                return rel == "." ? "" : rel;
            }
            var parent = Path.GetDirectoryName(d);
            if (Path.GetFullPath(d) == root || string.IsNullOrEmpty(parent) || parent == d) return "";
            d = parent;
        }
    }

    private static int Intersect(HashSet<string> a, HashSet<string> b)
    {
        var (small, big) = a.Count <= b.Count ? (a, b) : (b, a);
        int c = 0;
        foreach (var x in small) if (big.Contains(x)) c++;
        return c;
    }

    private static List<Edge> CandidateEdges(List<Page> pages, double minSim, int minShared, int maxPostings)
    {
        var postings = new Dictionary<string, List<int>>(StringComparer.Ordinal);
        for (int i = 0; i < pages.Count; i++)
        {
            foreach (var t in pages[i].Tokens)
            {
                if (!postings.TryGetValue(t, out var l)) { l = new List<int>(); postings[t] = l; }
                l.Add(i);
            }
        }

        var shared = new Dictionary<(int, int), int>();
        foreach (var plist in postings.Values)
        {
            if (plist.Count < 2 || plist.Count > maxPostings) continue;
            for (int a = 0; a < plist.Count; a++)
                for (int b = a + 1; b < plist.Count; b++)
                {
                    var key = (plist[a], plist[b]);
                    shared[key] = shared.TryGetValue(key, out var c) ? c + 1 : 1;
                }
        }

        var edges = new List<Edge>();
        foreach (var (key, count) in shared)
        {
            if (count < minShared) continue;
            int i = key.Item1, j = key.Item2;
            int inter = Intersect(pages[i].Tokens, pages[j].Tokens);
            int union = pages[i].Tokens.Count + pages[j].Tokens.Count - inter;
            double jac = union != 0 ? (double)inter / union : 0.0;
            if (jac >= minSim) edges.Add(new Edge(i, j, jac));
        }
        return edges;
    }

    private static List<JsonObject> BuildClusters(List<Page> pages, List<Edge> edges)
    {
        int n = pages.Count;
        var parent = new int[Math.Max(n, 1)];
        for (int i = 0; i < parent.Length; i++) parent[i] = i;

        int Find(int x)
        {
            while (parent[x] != x) { parent[x] = parent[parent[x]]; x = parent[x]; }
            return x;
        }

        foreach (var e in edges)
        {
            int ra = Find(e.I), rb = Find(e.J);
            if (ra != rb) parent[Math.Max(ra, rb)] = Math.Min(ra, rb);
        }

        var jacByRoot = new Dictionary<int, List<double>>();
        foreach (var e in edges)
        {
            int r = Find(e.I);
            if (!jacByRoot.TryGetValue(r, out var l)) { l = new List<double>(); jacByRoot[r] = l; }
            l.Add(e.Jac);
        }
        var membersByRoot = new Dictionary<int, List<int>>();
        for (int idx = 0; idx < n; idx++)
        {
            int r = Find(idx);
            if (!membersByRoot.TryGetValue(r, out var l)) { l = new List<int>(); membersByRoot[r] = l; }
            l.Add(idx);
        }

        var clusters = new List<JsonObject>();
        foreach (var (r, membersRaw) in membersByRoot)
        {
            if (membersRaw.Count < 2) continue;
            var members = membersRaw.OrderBy(m => pages[m].Path, StringComparer.Ordinal).ToList();
            var jacs = jacByRoot.TryGetValue(r, out var jl) ? jl : new List<double>();
            var domains = members.Select(m => pages[m].Domain).Distinct().OrderBy(x => x, StringComparer.Ordinal).ToList();
            long total = members.Sum(m => pages[m].Bytes);
            long biggest = members.Max(m => pages[m].Bytes);
            clusters.Add(new JsonObject
            {
                ["members"] = new JsonArray(members.Select(m => (JsonNode)pages[m].Path).ToArray()),
                ["domains"] = new JsonArray(domains.Select(x => (JsonNode)x!).ToArray()),
                ["scope"] = domains.Count == 1 ? "within-domain" : "cross-domain",
                ["jaccard_min"] = jacs.Count > 0 ? Math.Round(jacs.Min(), 3) : 0.0,
                ["jaccard_max"] = jacs.Count > 0 ? Math.Round(jacs.Max(), 3) : 0.0,
                ["total_bytes"] = total,
                ["est_saving_bytes"] = total - biggest,
            });
        }

        return clusters
            .OrderByDescending(c => (long)c["est_saving_bytes"]!)
            .ThenBy(c => (string)((JsonArray)c["members"]!)[0]!, StringComparer.Ordinal)
            .ToList();
    }
}
