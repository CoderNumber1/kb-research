using System.Diagnostics;
using System.Text.Json;
using Xunit;

namespace KnowledgeBase.Mcp.Tests;

public sealed record McpToolResult(bool IsError, string Text);

public sealed class McpFixture : IAsyncLifetime
{
    private readonly SemaphoreSlim _requestGate = new(1, 1);
    private Process? _process;
    private StreamReader? _output;
    private StreamWriter? _input;
    private Task<string>? _errorOutput;
    private int _nextRequestId = 1;

    public async Task InitializeAsync()
    {
        // KB_MCP_SERVER=python runs the suite against the plugin's Python server
        // (plugins/okf-knowledge-base/server/kb_mcp.py) instead of this C# project;
        // KB_MCP_PYTHON overrides the interpreter (default python3).
        var repoRoot = FindRepoRoot();
        var usePython = string.Equals(Environment.GetEnvironmentVariable("KB_MCP_SERVER"), "python", StringComparison.OrdinalIgnoreCase);
        var startInfo = new ProcessStartInfo
        {
            FileName = usePython ? Environment.GetEnvironmentVariable("KB_MCP_PYTHON") ?? "python3" : "dotnet",
            WorkingDirectory = repoRoot,
            UseShellExecute = false,
            CreateNoWindow = true,
            RedirectStandardInput = true,
            RedirectStandardOutput = true,
            RedirectStandardError = true,
        };
        startInfo.Environment["DOTNET_CLI_TELEMETRY_OPTOUT"] = "1";

        var arguments = usePython
            ? new[] { Path.Combine(FindPluginRoot(), "server", "kb_mcp.py") }
            : new[] { "run", "--project", Path.Combine(repoRoot, "src", "KnowledgeBase.Mcp", "KnowledgeBase.Mcp.csproj"), "-c", "Release", "-v", "quiet" };
        foreach (var argument in arguments)
        {
            startInfo.ArgumentList.Add(argument);
        }

        _process = new Process { StartInfo = startInfo };
        if (!_process.Start())
        {
            throw new InvalidOperationException("The knowledge-base MCP server did not start.");
        }

        _input = _process.StandardInput;
        _input.NewLine = "\n";
        _input.AutoFlush = true;
        _output = _process.StandardOutput;
        _errorOutput = _process.StandardError.ReadToEndAsync();

        var initialize = await SendRequestAsync(
            "initialize",
            new
            {
                protocolVersion = "2025-06-18",
                capabilities = new { },
                clientInfo = new
                {
                    name = "knowledge-base-xunit-tests",
                    version = "1.0",
                },
            });

        if (!initialize.TryGetProperty("result", out _))
        {
            throw new InvalidOperationException("The MCP server did not complete initialization.");
        }

        await SendNotificationAsync("notifications/initialized", new { });
    }

    public async Task<McpToolResult> CallToolAsync(string name, object arguments)
    {
        var response = await SendRequestAsync(
            "tools/call",
            new
            {
                name,
                arguments,
            });

        if (!response.TryGetProperty("result", out var result))
        {
            throw new InvalidOperationException("The MCP tool response did not contain a result.");
        }

        var content = result.GetProperty("content");
        var text = content[0].GetProperty("text").GetString() ?? string.Empty;
        var isError = result.TryGetProperty("isError", out var error) && error.GetBoolean();
        return new McpToolResult(isError, text);
    }

    public async Task<string[]> ListToolNamesAsync()
    {
        var response = await SendRequestAsync("tools/list", new { });
        return response.GetProperty("result").GetProperty("tools").EnumerateArray()
            .Select(tool => tool.GetProperty("name").GetString()!)
            .OrderBy(name => name, StringComparer.Ordinal)
            .ToArray();
    }

    public async Task DisposeAsync()
    {
        if (_process is null)
        {
            _requestGate.Dispose();
            return;
        }

        var wasKilled = false;
        if (!_process.HasExited)
        {
            _input?.Close();
            try
            {
                using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(5));
                await _process.WaitForExitAsync(timeout.Token);
            }
            catch (OperationCanceledException)
            {
                if (!_process.HasExited)
                {
                    _process.Kill(entireProcessTree: true);
                    wasKilled = true;
                }

                await _process.WaitForExitAsync();
            }
        }

        var errorOutput = _errorOutput is null
            ? string.Empty
            : await _errorOutput;
        var exitCode = _process.ExitCode;
        _process.Dispose();
        _requestGate.Dispose();

        if (!wasKilled && exitCode != 0)
        {
            throw new InvalidOperationException(
                $"The knowledge-base MCP server exited with code {exitCode}. {errorOutput}");
        }
    }

    private async Task<JsonElement> SendRequestAsync(string method, object parameters)
    {
        await _requestGate.WaitAsync();
        try
        {
            var id = _nextRequestId++;
            var message = JsonSerializer.Serialize(new
            {
                jsonrpc = "2.0",
                id,
                method,
                @params = parameters,
            });

            await WriteMessageAsync(message);
            var response = await ReadMessageAsync();
            if (!response.TryGetProperty("id", out var responseId) || responseId.GetInt32() != id)
            {
                throw new InvalidOperationException($"Expected MCP response id {id}.");
            }

            return response;
        }
        finally
        {
            _requestGate.Release();
        }
    }

    private async Task SendNotificationAsync(string method, object parameters)
    {
        var message = JsonSerializer.Serialize(new
        {
            jsonrpc = "2.0",
            method,
            @params = parameters,
        });
        await WriteMessageAsync(message);
    }

    private async Task WriteMessageAsync(string message)
    {
        if (_input is null)
        {
            throw new InvalidOperationException("The MCP server input stream is not available.");
        }

        await _input.WriteLineAsync(message);
        await _input.FlushAsync();
    }

    private async Task<JsonElement> ReadMessageAsync()
    {
        if (_output is null)
        {
            throw new InvalidOperationException("The MCP server output stream is not available.");
        }

        using var timeout = new CancellationTokenSource(TimeSpan.FromSeconds(30));
        var line = await _output.ReadLineAsync(timeout.Token);
        if (line is null)
        {
            var errorOutput = _errorOutput is null ? string.Empty : await _errorOutput;
            throw new InvalidOperationException(
                $"The MCP server closed stdout without a response. {errorOutput}");
        }

        try
        {
            using var document = JsonDocument.Parse(line);
            return document.RootElement.Clone();
        }
        catch (JsonException exception)
        {
            throw new InvalidOperationException(
                $"The MCP server wrote invalid JSON to stdout: {line}", exception);
        }
    }

    internal static string FindRepoRoot()
    {
        var current = new DirectoryInfo(AppContext.BaseDirectory);
        while (current is not null)
        {
            if (File.Exists(Path.Combine(current.FullName, "src", "KnowledgeBase.Mcp", "KnowledgeBase.Mcp.csproj")))
            {
                return current.FullName;
            }

            current = current.Parent;
        }

        throw new DirectoryNotFoundException("Could not locate the repository root from the test output directory.");
    }

    internal static string FindPluginRoot() =>
        Path.Combine(FindRepoRoot(), "plugins", "okf-knowledge-base");
}
