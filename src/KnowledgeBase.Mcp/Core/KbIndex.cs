using System.Collections.Concurrent;

namespace KnowledgeBase.Mcp.Core;

/// <summary>
/// Persistent warm index: caches parsed <see cref="KbPage"/> objects per KB root,
/// invalidating individual files by last-write time and size. Turns repeated
/// search/detect/lint/analyze calls from O(KB size on disk) into O(changed files),
/// the structural win a spawn-per-call server cannot match.
/// </summary>
internal sealed class KbIndex
{
    private sealed class Entry
    {
        public long Ticks;
        public long Length;
        public KbPage Page = null!;
    }

    private sealed class RootCache
    {
        public readonly object Gate = new();
        public readonly Dictionary<string, Entry> Files = new(StringComparer.OrdinalIgnoreCase);
    }

    private readonly ConcurrentDictionary<string, RootCache> _roots = new(StringComparer.OrdinalIgnoreCase);

    public static readonly KbIndex Shared = new();

    /// <summary>
    /// Returns every *.md page under <paramref name="kbRootFull"/> (recursively),
    /// reusing cached parses for unchanged files. Order is not significant — all
    /// engines sort their own output — but is stable (by full path).
    /// </summary>
    public IReadOnlyList<KbPage> GetPages(string kbRootFull)
    {
        kbRootFull = Path.GetFullPath(kbRootFull);
        var cache = _roots.GetOrAdd(kbRootFull, _ => new RootCache());

        lock (cache.Gate)
        {
            var present = new HashSet<string>(StringComparer.OrdinalIgnoreCase);
            var pages = new List<KbPage>();

            IEnumerable<string> files;
            try { files = Directory.EnumerateFiles(kbRootFull, "*.md", SearchOption.AllDirectories); }
            catch { files = Array.Empty<string>(); }

            foreach (var raw in files)
            {
                var full = Path.GetFullPath(raw);
                present.Add(full);

                long ticks, length;
                try
                {
                    var fi = new FileInfo(full);
                    ticks = fi.LastWriteTimeUtc.Ticks;
                    length = fi.Length;
                }
                catch { continue; }

                if (cache.Files.TryGetValue(full, out var entry) && entry.Ticks == ticks && entry.Length == length)
                {
                    pages.Add(entry.Page);
                    continue;
                }

                string text;
                try { text = File.ReadAllText(full); }
                catch { continue; }

                var page = KbPage.Build(kbRootFull, full, text);
                cache.Files[full] = new Entry { Ticks = ticks, Length = length, Page = page };
                pages.Add(page);
            }

            // Drop cache entries for files that no longer exist.
            foreach (var stale in cache.Files.Keys.Where(k => !present.Contains(k)).ToList())
            {
                cache.Files.Remove(stale);
            }

            return pages;
        }
    }

    /// <summary>Invalidate a whole root (used after mutating operations like init_domain).</summary>
    public void Invalidate(string kbRootFull)
    {
        _roots.TryRemove(Path.GetFullPath(kbRootFull), out _);
    }
}
