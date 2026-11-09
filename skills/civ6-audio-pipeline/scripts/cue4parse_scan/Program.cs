using System;
using System.Collections.Concurrent;
using System.Collections.Generic;
using System.Diagnostics;
using System.IO;
using System.Linq;
using System.Threading;
using System.Threading.Tasks;
using CUE4Parse.FileProvider;
using CUE4Parse.Compression;
using CUE4Parse.Encryption.Aes;
using CUE4Parse.UE4.Assets.Exports;
using CUE4Parse.UE4.Objects.Core.Misc;
using CUE4Parse.UE4.Versions;
using Newtonsoft.Json;
using Newtonsoft.Json.Linq;
using OodleDotNet;

// 通用 CUE4Parse 本地批量工具（与 FModel 同源 DLL，AES 密钥走本机 FModel 已存设置）。
//
// 扫描模式（枚举 + 批量属性导出）：
//   CueScan --game-dir <游戏根目录> [--game GAME_XXX] [--oodle <oo2core.dll>]
//           [--settings <AppSettings.json>] [--settings-key <PerDirectory 键>]
//           <输出目录> [--prefix <虚拟路径前缀>] [--export-type <导出类名>] [--limit N]
//   输出：
//     inventory.tsv   前缀过滤后的全部文件（path \t size）
//     objects.jsonl   命中包的每个导出对象一行 {path, name, exportType, object}
//     errors.log
//
// 导出模式（按映射批量导出文件原始字节，路径区分大小写不敏感）：
//   CueScan --export <映射.tsv> [其余挂载参数同上]
//   映射.tsv 行格式：虚拟路径<TAB>目标绝对路径

static string Arg(string[] args, string name, string fallback = null)
{
    for (int i = 0; i < args.Length - 1; i++)
        if (args[i] == name) return args[i + 1];
    return fallback;
}

static string NormalizeHex(string s)
{
    s = s.Trim();
    if (s.StartsWith("0x", StringComparison.OrdinalIgnoreCase)) s = s.Substring(2);
    return s;
}

var gameDir = Arg(args, "--game-dir") ?? throw new InvalidOperationException("missing --game-dir");
var gameName = Arg(args, "--game", "GAME_WutheringWaves");
var oodlePath = Arg(args, "--oodle");
var settingsPath = Arg(args, "--settings",
    Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.ApplicationData), "FModel", "AppSettings.json"));
var settingsKey = Arg(args, "--settings-key", gameDir);
var exportMapPath = Arg(args, "--export");
var exportType = Arg(args, "--export-type");

if (OodleHelper.Instance == null)
{
    if (oodlePath == null || !File.Exists(oodlePath))
        throw new FileNotFoundException("--oodle 未提供或文件不存在（CUE4Parse 需要 Oodle 原生库解压）");
    OodleHelper.Initialize(new Oodle(oodlePath));
}

// 从本机 FModel 已存设置读取 AES 密钥（不在输出中打印任何密钥值）
var settings = JObject.Parse(File.ReadAllText(settingsPath));
var perDir = settings["PerDirectory"].Children<JProperty>()
    .FirstOrDefault(p => string.Equals(p.Name, settingsKey, StringComparison.OrdinalIgnoreCase))?.Value
    ?? throw new InvalidOperationException($"FModel settings missing entry: {settingsKey}");
var aesKeys = new Dictionary<FGuid, FAesKey>();
string mainKeyHex = (string)perDir["AesKeys"]?["mainKey"];
if (!string.IsNullOrEmpty(mainKeyHex))
    aesKeys[new FGuid(0u)] = new FAesKey(NormalizeHex(mainKeyHex));
foreach (var dyn in (JArray)perDir["AesKeys"]?["dynamicKeys"] ?? new JArray())
    aesKeys[new FGuid((string)dyn["guid"])] = new FAesKey(NormalizeHex((string)dyn["key"]));
Console.WriteLine($"keys loaded: {aesKeys.Count}");

var game = (EGame)Enum.Parse(typeof(EGame), gameName, ignoreCase: true);
var versions = new VersionContainer(game);
var provider = new DefaultFileProvider(gameDir, SearchOption.AllDirectories, versions, StringComparer.OrdinalIgnoreCase);
provider.Initialize();
provider.Mount();
provider.SubmitKeys(aesKeys);
provider.PostMount();
Console.WriteLine($"files indexed: {provider.Files.Count}");

if (exportMapPath != null)
{
    await RunExport(provider, exportMapPath);
    return;
}

var outDir = Path.GetFullPath(args[^1]);
Directory.CreateDirectory(outDir);
var prefix = Arg(args, "--prefix");
int? limit = null;
for (int i = 0; i < args.Length - 1; i++)
    if (args[i] == "--limit") limit = int.Parse(args[i + 1]);

var files = provider.Files.Values
    .Where(f => prefix == null || f.Path.StartsWith(prefix, StringComparison.OrdinalIgnoreCase))
    .Where(f => f.Path.EndsWith(".uasset", StringComparison.OrdinalIgnoreCase))
    .OrderBy(f => f.Path, StringComparer.OrdinalIgnoreCase)
    .ToList();
if (limit.HasValue) files = files.Take(limit.Value).ToList();
Console.WriteLine($"files to parse: {files.Count}");

using (var w = new StreamWriter(Path.Combine(outDir, "inventory.tsv")))
    foreach (var f in provider.Files.Values.Where(f => prefix == null || f.Path.StartsWith(prefix, StringComparison.OrdinalIgnoreCase)).OrderBy(f => f.Path, StringComparer.OrdinalIgnoreCase))
        w.WriteLine($"{f.Path}\t{f.Size}");

var errors = new ConcurrentBag<string>();
var lockObj = new object();
var sw = Stopwatch.StartNew();
await Parallel.ForEachAsync(files, new ParallelOptions { MaxDegreeOfParallelism = 8 }, async (file, ct) =>
{
    try
    {
        var package = provider.LoadPackage(file);
        foreach (var export in package.GetExports())
        {
            if (exportType != null && !string.Equals(export.ExportType, exportType, StringComparison.OrdinalIgnoreCase))
                continue;
            var rec = new JObject
            {
                ["path"] = file.Path,
                ["name"] = export.Name,
                ["exportType"] = export.ExportType,
                ["object"] = JObject.FromObject(export)
            };
            lock (lockObj)
                File.AppendAllText(Path.Combine(outDir, "objects.jsonl"), rec.ToString(Formatting.None) + "\n");
        }
    }
    catch (Exception e)
    {
        errors.Add($"{file.Path}\t{e.GetType().Name}\t{e.Message}");
    }
    int done = Interlocked.Increment(ref State.Done);
    if (done % 500 == 0)
        Console.WriteLine($"parsed {done}/{files.Count} ({sw.Elapsed.TotalSeconds:F0}s)");
});
File.WriteAllLines(Path.Combine(outDir, "errors.log"), errors);
Console.WriteLine($"done: {files.Count} packages, {errors.Count} errors, {sw.Elapsed.TotalSeconds:F0}s");

static async Task RunExport(DefaultFileProvider provider, string mapPath)
{
    var entries = File.ReadAllLines(mapPath)
        .Where(l => l.Length > 0)
        .Select(l => l.Split('\t'))
        .Select(p => (vPath: p[0], dest: p[1]))
        .ToList();
    Console.WriteLine($"export entries: {entries.Count}");
    var errors = new ConcurrentBag<string>();
    var sw = Stopwatch.StartNew();
    await Parallel.ForEachAsync(entries, new ParallelOptions { MaxDegreeOfParallelism = 8 }, async (entry, ct) =>
    {
        try
        {
            if (!provider.Files.TryGetValue(entry.vPath, out var file))
                throw new FileNotFoundException("not in provider", entry.vPath);
            var bytes = file.Read();
            Directory.CreateDirectory(Path.GetDirectoryName(entry.dest)!);
            await File.WriteAllBytesAsync(entry.dest, bytes, ct);
        }
        catch (Exception e)
        {
            errors.Add($"{entry.vPath}\t{e.GetType().Name}\t{e.Message}");
        }
        int done = Interlocked.Increment(ref State.Done);
        if (done % 2000 == 0)
            Console.WriteLine($"exported {done}/{entries.Count} ({sw.Elapsed.TotalSeconds:F0}s)");
    });
    File.WriteAllLines(Path.Combine(Path.GetDirectoryName(mapPath)!, "export_errors.log"), errors);
    Console.WriteLine($"export done: {entries.Count} entries, {errors.Count} errors, {sw.Elapsed.TotalSeconds:F0}s");
}

internal static class State
{
    public static int Done;
}
