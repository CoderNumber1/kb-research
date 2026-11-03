using System.Text.Json;

namespace KnowledgeBase.Mcp.Tests;

/// <summary>A disposable temp repository with a kb/ root path and a CLAUDE.md beside it.</summary>
internal sealed class TestWorkspace : IDisposable
{
    private readonly DirectoryInfo _root = Directory.CreateTempSubdirectory("knowledge-base-mcp-tests-");

    public string Root => _root.FullName;

    public string KbRoot => Path.Combine(Root, "kb");

    public string InstructionsFile => Path.Combine(Root, "CLAUDE.md");

    public void Write(string relativePath, string contents)
    {
        var path = Path.Combine(KbRoot, relativePath);
        Directory.CreateDirectory(Path.GetDirectoryName(path)!);
        File.WriteAllText(path, contents.Replace("\r\n", "\n"));
    }

    public void Dispose()
    {
        if (Directory.Exists(Root))
        {
            Directory.Delete(Root, recursive: true);
        }
    }
}

internal static class TestCalls
{
    public static Dictionary<string, object?> Args(TestWorkspace workspace, params (string Key, object? Value)[] extra)
    {
        var args = new Dictionary<string, object?> { ["kb_root"] = workspace.KbRoot };
        foreach (var (key, value) in extra) args[key] = value;
        return args;
    }

    public static async Task<JsonElement> CallJsonAsync(this McpFixture mcp, string tool, Dictionary<string, object?> args)
    {
        var result = await mcp.CallToolAsync(tool, args);
        if (result.IsError) throw new InvalidOperationException($"{tool} failed: {result.Text}");
        using var document = JsonDocument.Parse(result.Text);
        return document.RootElement.Clone();
    }

    public static JsonElement[] Findings(this JsonElement lint) =>
        lint.GetProperty("findings").EnumerateArray().ToArray();

    public static bool Has(this JsonElement[] findings, string code, string path) =>
        findings.Any(f => f.GetProperty("code").GetString() == code && f.GetProperty("path").GetString() == path);
}
