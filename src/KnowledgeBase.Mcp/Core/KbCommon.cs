using System.Text.RegularExpressions;
using YamlDotNet.Core;
using YamlDotNet.RepresentationModel;

namespace KnowledgeBase.Mcp.Core;

/// <summary>
/// Shared text handling: YAML frontmatter parsing, stemming, and tokenization.
/// </summary>
internal static class KbCommon
{
    private static readonly HashSet<string> Stop = new(StringComparer.Ordinal)
    {
        "a","an","the","of","to","in","on","for","and","or","but","with","without",
        "into","from","by","as","at","is","are","was","were","be","been","being",
        "this","that","these","those","it","its","you","your","we","our","they",
        "their","he","she","his","her","them","us","i","me","my","mine","ours",
        "yours","will","would","can","could","should","may","might","must","do",
        "does","did","done","has","have","had","how","what","when","where","why",
        "who","whom","which","whose","than","then","so","if","else","not","no",
        "yes","about","over","under","again","further","more","most","other","some",
        "such","only","own","same","too","very","just","also","cannot",
    };

    // Longest-first suffix list. Order within a given length is irrelevant:
    // a word has exactly one ending of each length.
    private static readonly string[] Suffixes = new[]
    {
        "ization","ational","ication","fulness","ousness","iveness",
        "ature","ities","ement","ness","tion","sion","ies","ied","ying",
        "ing","ers","er","ed","ly","al","s","y","e",
    }.OrderByDescending(s => s.Length).ToArray();

    private static readonly Regex TokenRe = new("[a-z0-9]+", RegexOptions.Compiled);

    public static string Stem(string word)
    {
        foreach (var suf in Suffixes)
        {
            if (word.Length - suf.Length >= 3 && word.EndsWith(suf, StringComparison.Ordinal))
            {
                return word.Substring(0, word.Length - suf.Length);
            }
        }
        return word;
    }

    /// <summary>Stemmed, non-stopword tokens (length > 1), in text order with duplicates.</summary>
    public static List<string> Tokens(string? text)
    {
        var outList = new List<string>();
        if (string.IsNullOrEmpty(text)) return outList;
        foreach (Match m in TokenRe.Matches(text.ToLowerInvariant()))
        {
            var t = m.Value;
            if (t.Length <= 1 || Stop.Contains(t)) continue;
            outList.Add(Stem(t));
        }
        return outList;
    }

    /// <summary>Unstemmed, non-stopword tokens (length > 1) — used to locate readable snippets.</summary>
    public static List<string> RawWords(string? text)
    {
        var outList = new List<string>();
        if (string.IsNullOrEmpty(text)) return outList;
        foreach (Match m in TokenRe.Matches(text.ToLowerInvariant()))
        {
            var t = m.Value;
            if (t.Length <= 1 || Stop.Contains(t)) continue;
            outList.Add(t);
        }
        return outList;
    }

    public static HashSet<string> TokenSet(string? text) => new(Tokens(text), StringComparer.Ordinal);

    /// <summary>
    /// Parses the YAML frontmatter block. Values become a string (scalar), a
    /// List&lt;object&gt; (sequence), or an ordered List&lt;KeyValuePair&lt;string, object&gt;&gt;
    /// (mapping), so OKF v0.2's nested families (generated, verified, sources)
    /// stay nested instead of leaking into top-level keys.
    /// </summary>
    public static Frontmatter ParseFrontmatter(string? text)
    {
        var meta = new List<KeyValuePair<string, object>>();
        if (text is null || !text.StartsWith("---", StringComparison.Ordinal))
        {
            return new Frontmatter(meta, text ?? "", false, "no frontmatter block");
        }
        var lines = text.Split('\n');
        int end = -1;
        for (int i = 1; i < lines.Length; i++)
        {
            if (lines[i].Trim() == "---") { end = i; break; }
        }
        if (end < 0)
        {
            return new Frontmatter(meta, text, false, "unterminated frontmatter block");
        }

        string body = (end + 1) <= (lines.Length - 1)
            ? string.Join("\n", lines.Skip(end + 1))
            : "";
        var yaml = string.Join("\n", lines.Skip(1).Take(end - 1));

        try
        {
            var stream = new YamlStream();
            stream.Load(new StringReader(yaml));
            if (stream.Documents.Count == 0)
            {
                return new Frontmatter(meta, body, true, "");
            }
            if (stream.Documents[0].RootNode is not YamlMappingNode root)
            {
                return new Frontmatter(meta, body, false, "frontmatter is not a YAML mapping");
            }
            return new Frontmatter(ToMapping(root), body, true, "");
        }
        catch (YamlException ex)
        {
            return new Frontmatter(meta, body, false, $"invalid YAML (line {ex.Start.Line}): {ex.Message}");
        }
    }

    private static List<KeyValuePair<string, object>> ToMapping(YamlMappingNode node) =>
        node.Children
            .Select(kv => new KeyValuePair<string, object>(
                kv.Key is YamlScalarNode k ? k.Value ?? "" : kv.Key.ToString(),
                ToValue(kv.Value)))
            .ToList();

    private static object ToValue(YamlNode node) => node switch
    {
        YamlScalarNode s => s.Value ?? "",
        YamlSequenceNode seq => seq.Children.Select(ToValue).ToList(),
        YamlMappingNode map => ToMapping(map),
        _ => node.ToString(),
    };

    /// <summary>Quotes a scalar for frontmatter when plain YAML would misread it.</summary>
    public static string YamlScalar(string value)
    {
        bool plainOk = value.Length > 0
            && value == value.Trim()
            && !value.Contains(": ", StringComparison.Ordinal)
            && !value.Contains(" #", StringComparison.Ordinal)
            && !value.EndsWith(':')
            && "-?:,[]{}#&*!|>'\"%@`".IndexOf(value[0]) < 0
            && !value.Any(char.IsControl);
        if (plainOk) return value;
        var escaped = value.Replace("\\", "\\\\").Replace("\"", "\\\"");
        return $"\"{escaped}\"";
    }
}

internal sealed class Frontmatter
{
    public List<KeyValuePair<string, object>> Meta { get; }
    public string Body { get; }
    public bool Ok { get; }
    public string Err { get; }

    public Frontmatter(List<KeyValuePair<string, object>> meta, string body, bool ok, string err)
    {
        Meta = meta;
        Body = body;
        Ok = ok;
        Err = err;
    }

    public bool Has(string key) => Meta.Any(kv => kv.Key == key);

    public object? Raw(string key) => Lookup(Meta, key);

    /// <summary>Scalar as-is; a sequence of scalars space-joined; anything else "".</summary>
    public string GetString(string key) => AsString(Raw(key));

    /// <summary>Tag normalization: null → [], scalar → [scalar], sequence → its scalars.</summary>
    public List<string> GetList(string key) => Raw(key) switch
    {
        null => new List<string>(),
        string s => new List<string> { s },
        List<object> l => l.OfType<string>().ToList(),
        _ => new List<string>(),
    };

    public int KeyCount => Meta.Count;
    public IEnumerable<string> Keys => Meta.Select(kv => kv.Key);

    public static object? Lookup(List<KeyValuePair<string, object>> map, string key)
    {
        foreach (var kv in map) if (kv.Key == key) return kv.Value;
        return null;
    }

    public static string AsString(object? value) => value switch
    {
        null => "",
        string s => s,
        List<object> l => string.Join(" ", l.OfType<string>()),
        _ => "",
    };
}
