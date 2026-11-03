using ModelContextProtocol;

namespace KnowledgeBase.Mcp.Core;

/// <summary>
/// Signals a hard tool error (no KB / bad path), surfaced to the caller as an
/// MCP error result. Deriving from McpException is what makes the SDK pass the
/// message through instead of a generic "An error occurred invoking …".
/// </summary>
internal sealed class KbException : McpException
{
    public KbException(string message) : base(message) { }
}

internal static class KbPaths
{
    /// <summary>True when <paramref name="fullPath"/> is inside <paramref name="rootFull"/> (or equal).</summary>
    public static bool IsUnder(string rootFull, string fullPath)
    {
        var root = rootFull.TrimEnd(Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar);
        if (string.Equals(fullPath, root, StringComparison.OrdinalIgnoreCase)) return true;
        var rel = Path.GetRelativePath(root, fullPath);
        return rel != "." && !rel.StartsWith("..", StringComparison.Ordinal) && !Path.IsPathRooted(rel);
    }

    /// <summary>True when a path is below a directory named <c>raw</c> in the KB.</summary>
    public static bool IsRawArtifact(string kbRootFull, string fullPath)
    {
        var relative = Path.GetRelativePath(kbRootFull, fullPath);
        return relative
            .Split(
                new[] { Path.DirectorySeparatorChar, Path.AltDirectorySeparatorChar },
                StringSplitOptions.RemoveEmptyEntries)
            .Any(segment => string.Equals(segment, "raw", StringComparison.OrdinalIgnoreCase));
    }

    public static string Rel(string kbRootFull, string fullPath) =>
        Path.GetRelativePath(kbRootFull, fullPath).Replace('\\', '/');
}
