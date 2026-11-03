using System.Text;

namespace KnowledgeBase.Mcp.Core;

/// <summary>
/// A parsed knowledge-base markdown file with precomputed token structures.
/// Built once per (path, mtime, size) and cached by <see cref="KbIndex"/>.
/// </summary>
internal sealed class KbPage
{
    public required string FullPath { get; init; }
    public required string RelPath { get; init; }      // relative to kb root, forward slashes
    public required string Name { get; init; }         // file name
    public required string DirFullPath { get; init; }
    public required string RawText { get; init; }
    public required long ByteCount { get; init; }
    public required Frontmatter Fm { get; init; }
    public bool IsReserved { get; init; }

    // Precomputed token structures (concept-page ranking + analysis).
    public HashSet<string> TitleTokens { get; init; } = new();
    public HashSet<string> DescTokens { get; init; } = new();
    public HashSet<string> TagTokens { get; init; } = new();
    public HashSet<string> TypeTokens { get; init; } = new();
    public Dictionary<string, int> BodyTokenCounts { get; init; } = new();
    public HashSet<string> BlobTokens { get; init; } = new();
    // Domain routing (domain.md pages).
    public HashSet<string> StrongTokens { get; init; } = new();
    public HashSet<string> WeakTokens { get; init; } = new();

    public static readonly HashSet<string> Reserved = new(StringComparer.Ordinal) { "index.md", "log.md" };

    public static KbPage Build(string kbRootFull, string fullPath, string text)
    {
        var fm = KbCommon.ParseFrontmatter(text);
        var name = Path.GetFileName(fullPath);
        var tags = fm.GetList("tags");
        var tagsJoined = string.Join(" ", tags);

        var bodyCounts = new Dictionary<string, int>(StringComparer.Ordinal);
        foreach (var t in KbCommon.Tokens(fm.Body))
        {
            bodyCounts[t] = bodyCounts.TryGetValue(t, out var c) ? c + 1 : 1;
        }

        var blob = string.Join(" ", new[] { fm.GetString("title"), tagsJoined, fm.GetString("description"), fm.Body });

        return new KbPage
        {
            FullPath = fullPath,
            RelPath = Path.GetRelativePath(kbRootFull, fullPath).Replace('\\', '/'),
            Name = name,
            DirFullPath = Path.GetDirectoryName(fullPath)!,
            RawText = text,
            ByteCount = Encoding.UTF8.GetByteCount(text),
            Fm = fm,
            IsReserved = Reserved.Contains(name),
            TitleTokens = KbCommon.TokenSet(fm.GetString("title")),
            DescTokens = KbCommon.TokenSet(fm.GetString("description")),
            TagTokens = KbCommon.TokenSet(tagsJoined),
            TypeTokens = KbCommon.TokenSet(fm.GetString("type")),
            BodyTokenCounts = bodyCounts,
            BlobTokens = KbCommon.TokenSet(blob),
            StrongTokens = KbCommon.TokenSet(fm.GetString("title") + " " + tagsJoined),
            WeakTokens = KbCommon.TokenSet(fm.GetString("description") + " " + fm.Body),
        };
    }
}
