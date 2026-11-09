using System;
using System.IO;
using System.Reflection;
using System.Windows.Forms;
using NexusBuddy;
using NexusBuddy.FileOps;
using Firaxis.Utility;
using Firaxis.Granny;

class NexusBatch
{
    static string fbxDir;
    static string outDir;
    static string node;
    static GrannyContext ctx;
    static MethodInfo writeGeo;
    static MethodInfo importCN6MI;

    static void ImportCN6(string src, string tmp)
    {
        if (importCN6MI == null)
        {
            Type ct = typeof(CivNexusSixApplicationForm).Assembly.GetType("NexusBuddy.FileOps.CN6FileOps");
            importCN6MI = ct.GetMethod("importCN6");
        }
        importCN6MI.Invoke(null, new object[] { src, tmp, ctx, 0 });
    }

    static void WriteGeoAnim(IGrannyFile file)
    {
        if (writeGeo == null)
        {
            Type mt = typeof(CivNexusSixApplicationForm).Assembly.GetType("NexusBuddy.FileOps.MetadataWriter");
            writeGeo = mt.GetMethod("WriteGeoAnimFile");
        }
        writeGeo.Invoke(null, new object[] { file, 0, "Leader" });
    }

    static string cfgCn6;
    static string cfgFbx;
    static string cfgTmp;
    static string cfgDst;
    static string cfgNode;
    static int cfgPlacement;
    static System.Collections.Generic.List<string> anims = new System.Collections.Generic.List<string>();

    static void Fail(string message)
    {
        Console.WriteLine("ANIMSET_ERROR " + message);
        Environment.Exit(2);
    }

    // 动画名表外置：<exe 名>.animset.tsv 与 exe 同目录，启动即读，缺项即退出
    static void LoadAnimSet()
    {
        string cfg = Path.Combine(Path.GetDirectoryName(Application.ExecutablePath),
            Path.GetFileNameWithoutExtension(Application.ExecutablePath) + ".animset.tsv");
        if (!File.Exists(cfg)) Fail("FILE_MISSING " + cfg);
        Console.WriteLine("ANIMSET " + cfg);
        string[] lines = File.ReadAllLines(cfg, System.Text.Encoding.UTF8);
        bool hasCn6 = false;
        bool hasFbx = false;
        bool hasTmp = false;
        bool hasDst = false;
        bool hasNode = false;
        bool hasPlacement = false;
        for (int i = 0; i < lines.Length; i++)
        {
            string raw = lines[i].Trim();
            if (raw.Length == 0 || raw.StartsWith("#")) continue;
            string[] parts = raw.Split('\t');
            if (parts.Length != 2) Fail("FIELD_COUNT line=" + (i + 1) + " " + raw);
            string key = parts[0].Trim();
            string val = parts[1].Trim();
            if (val.Length == 0) Fail("EMPTY_VALUE line=" + (i + 1) + " " + raw);
            switch (key)
            {
                case "model.cn6":
                    if (hasCn6) Fail("DUP_KEY line=" + (i + 1) + " " + key);
                    cfgCn6 = val;
                    hasCn6 = true;
                    break;
                case "model.fbx":
                    if (hasFbx) Fail("DUP_KEY line=" + (i + 1) + " " + key);
                    cfgFbx = val;
                    hasFbx = true;
                    break;
                case "model.tmp":
                    if (hasTmp) Fail("DUP_KEY line=" + (i + 1) + " " + key);
                    cfgTmp = val;
                    hasTmp = true;
                    break;
                case "model.dst":
                    if (hasDst) Fail("DUP_KEY line=" + (i + 1) + " " + key);
                    cfgDst = val;
                    hasDst = true;
                    break;
                case "model.node":
                    if (hasNode) Fail("DUP_KEY line=" + (i + 1) + " " + key);
                    cfgNode = val;
                    hasNode = true;
                    break;
                case "model.placement":
                    if (hasPlacement) Fail("DUP_KEY line=" + (i + 1) + " " + key);
                    int parsed;
                    if (!int.TryParse(val, out parsed)) Fail("PLACEMENT_NOT_INT line=" + (i + 1) + " " + val);
                    cfgPlacement = parsed;
                    hasPlacement = true;
                    break;
                case "anim":
                    if (anims.Contains(val)) Fail("DUP_ANIM line=" + (i + 1) + " " + val);
                    anims.Add(val);
                    break;
                default:
                    Fail("UNKNOWN_KEY line=" + (i + 1) + " " + key);
                    break;
            }
        }
        if (!hasCn6) Fail("KEY_MISSING model.cn6");
        if (!hasFbx) Fail("KEY_MISSING model.fbx");
        if (!hasTmp) Fail("KEY_MISSING model.tmp");
        if (!hasDst) Fail("KEY_MISSING model.dst");
        if (!hasNode) Fail("KEY_MISSING model.node");
        if (!hasPlacement) Fail("KEY_MISSING model.placement");
        if (anims.Count == 0) Fail("ANIM_EMPTY");
        Console.WriteLine("ANIMSET_MODEL " + cfgCn6 + " " + cfgFbx + " -> " + cfgDst + " node=" + cfgNode + " placement=" + cfgPlacement);
        Console.WriteLine("ANIMSET_ANIMS " + anims.Count + " " + string.Join(",", anims.ToArray()));
    }

    [STAThread]
    static void Main(string[] args)
    {
        LoadAnimSet();
        fbxDir = args[0];
        outDir = args[1];
        node = args[2];
        Directory.CreateDirectory(outDir);

        Application.EnableVisualStyles();
        Form form = new CivNexusSixApplicationForm();
        appForm = form;
        FieldInfo fi = typeof(CivNexusSixApplicationForm).GetField("nodeTextBox",
            BindingFlags.NonPublic | BindingFlags.Instance);
        ((TextBox)fi.GetValue(form)).Text = node;
        form.Show();
        Application.DoEvents();
        Console.WriteLine("FORM_SHOWN");

        ctx = Context.Get<GrannyContext>();
        Console.WriteLine("CTX_OK");

        ConvertModel();
        foreach (string name in anims)
        {
            ConvertAnim(name);
        }
        Console.WriteLine("CONVERT_DONE");
    }

    static Form appForm;

    static string DummyWigPath()
    {
        FieldInfo fi = typeof(CivNexusSixApplicationForm).GetField("dummyWigFilename",
            BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
        return (string)fi.GetValue(appForm);
    }

    static void WriteGeoModel(IGrannyFile f, string dst)
    {
        System.Collections.Generic.IEnumerable<IGrannyMesh> meshes =
            f.Meshes.Count > 0 ? f.Meshes : f.Models[0].MeshBindings;
        string dir = Path.GetDirectoryName(dst);
        string name = Path.GetFileNameWithoutExtension(dst);
        string wig = Path.Combine(dir, name + ".wig");
        File.Copy(DummyWigPath(), wig, true);
        System.Text.StringBuilder sb = new System.Text.StringBuilder();
        sb.AppendLine("<?xml version=\"1.0\" encoding=\"UTF-8\" ?>");
        sb.AppendLine("<AssetObjects:GeometryInstance>");
        sb.AppendLine("<m_CookParams>");
        sb.AppendLine("<m_Values/>");
        sb.AppendLine("</m_CookParams>");
        sb.AppendLine("<m_Version>");
        sb.AppendLine("<major>0</major>");
        sb.AppendLine("<minor>0</minor>");
        sb.AppendLine("<build>0</build>");
        sb.AppendLine("<revision>0</revision>");
        sb.AppendLine("</m_Version>");
        sb.AppendLine("<m_Meshes>");
        foreach (IGrannyMesh mesh in meshes)
        {
            sb.AppendLine("<Element>");
            sb.AppendLine("<m_Name text=\"" + mesh.Name + "\"/>");
            sb.AppendLine("<m_Groups>");
            int prims = 0;
            foreach (IGrannyTriMaterialGroup g in mesh.TriangleMaterialGroups)
            {
                sb.AppendLine("<Element>");
                sb.AppendLine("<m_Name text=\"" + mesh.MaterialBindings[g.MaterialIndex].Name + "\"/>");
                sb.AppendLine("<m_nFirstPrim>" + g.TriFirst + "</m_nFirstPrim>");
                sb.AppendLine("<m_nPrims>" + g.TriCount + "</m_nPrims>");
                sb.AppendLine("</Element>");
                prims += g.TriCount;
            }
            sb.AppendLine("</m_Groups>");
            sb.AppendLine("<m_nBoundBoneCount>" + mesh.BoneBindings.Count + "</m_nBoundBoneCount>");
            sb.AppendLine("<m_nPrimitiveCount>" + prims + "</m_nPrimitiveCount>");
            sb.AppendLine("<m_nVertexCount>" + mesh.VertexCount + "</m_nVertexCount>");
            sb.AppendLine("</Element>");
        }
        sb.AppendLine("</m_Meshes>");
        sb.AppendLine("<m_Bones>");
        foreach (IGrannyBone b in f.Models[0].Skeleton.Bones)
        {
            sb.AppendLine("<Element text=\"" + b.Name + "\"/>");
        }
        sb.AppendLine("</m_Bones>");
        sb.AppendLine("<m_ModelName text=\"" + f.Models[0].Skeleton.Name + "\"/>");
        sb.AppendLine("<m_SourceFilePath text=\"\"/>");
        sb.AppendLine("<m_SourceObjectName text=\"\"/>");
        sb.AppendLine("<m_ImportedTime>0</m_ImportedTime>");
        sb.AppendLine("<m_ExportedTime>0</m_ExportedTime>");
        sb.AppendLine("<m_ClassName text=\"Leader\"/>");
        sb.AppendLine("<m_DataFiles>");
        sb.AppendLine("<Element>");
        sb.AppendLine("<m_ID text=\"GR2\"/>");
        sb.AppendLine("<m_RelativePath text=\"" + name + ".fgx\"/>");
        sb.AppendLine("</Element>");
        sb.AppendLine("<Element>");
        sb.AppendLine("<m_ID text=\"WIG\"/>");
        sb.AppendLine("<m_RelativePath text=\"" + name + ".wig\"/>");
        sb.AppendLine("</Element>");
        sb.AppendLine("</m_DataFiles>");
        sb.AppendLine("<m_Name text=\"" + name + "\"/>");
        sb.AppendLine("<m_Description text=\"" + name + "\"/>");
        sb.AppendLine("<m_Tags>");
        sb.AppendLine("<Element text=\"Leader\"/>");
        sb.AppendLine("</m_Tags>");
        sb.AppendLine("</AssetObjects:GeometryInstance>");
        File.WriteAllText(dst.Replace(".fgx", ".geo"), sb.ToString());
        Console.WriteLine("GEO_WRITTEN meshes=" + new System.Collections.Generic.List<IGrannyMesh>(meshes).Count);
    }

    static void ZeroPlacement(IGrannyFile f, int idx)
    {
        // placement 四元数候选（三轴挨个试）：把 rest 链的整体朝向旋转到引擎竖直
        float[][] QUATS = new float[][] {
            new float[] { 0f, 0f, 0f, 1f },                     // identity
            new float[] { 0f, 0f, 0.7071f, 0.7071f },           // +Z 90
            new float[] { 0f, 0f, -0.7071f, 0.7071f },          // -Z 90
            new float[] { 0.7071f, 0f, 0f, 0.7071f },           // +X 90
            new float[] { -0.7071f, 0f, 0f, 0.7071f },          // -X 90
            new float[] { 0f, 0.7071f, 0f, 0.7071f },           // +Y 90
            new float[] { 0f, -0.7071f, 0f, 0.7071f },          // -Y 90
        };
        if (idx < 0 || idx >= QUATS.Length) Fail("PLACEMENT_RANGE idx=" + idx + " max=" + (QUATS.Length - 1));
        float[] q = QUATS[idx];
        foreach (IGrannyModel m in f.Models)
        {
            NexusBuddy.GrannyWrappers.GrannyTransformWrapper tw =
                new NexusBuddy.GrannyWrappers.GrannyTransformWrapper(m.InitialPlacement);
            tw.Position = new float[] { 0f, 0f, 0f };
            tw.Orientation = q;
        }
        Console.WriteLine("PLACEMENT_SET idx=" + idx + " q=[" + string.Join(",", q) + "] models=" + f.Models.Count);
    }

    static void ConvertModel()
    {
        string srcCn6 = Path.Combine(fbxDir, cfgCn6);
        string srcFbx = Path.Combine(fbxDir, cfgFbx);
        string tmp = Path.Combine(outDir, cfgTmp);
        string dst = Path.Combine(outDir, cfgDst);
        if (File.Exists(srcCn6))
        {
            ImportCN6(srcCn6, tmp);
            Console.WriteLine("CN6_IMPORT " + srcCn6);
        }
        else
        {
            bool ok = FBXImporter.ImportFBXFile(srcFbx, tmp, cfgNode);
            Console.WriteLine("FBX_IMPORT " + ok);
        }
        IGrannyFile f = ctx.LoadGrannyFile(tmp);
        Console.WriteLine("MODEL_LOADED meshes=" + f.Meshes.Count + " models=" + f.Models.Count +
            " anims=" + f.Animations.Count +
            " bindings=" + (f.Models.Count > 0 ? f.Models[0].MeshBindings.Count : 0) +
            " bones=" + (f.Models.Count > 0 ? f.Models[0].Skeleton.Bones.Count : 0));
        f.Filename = dst;
        f.Save();
        IGrannyFile f2 = ctx.LoadGrannyFile(dst);
        ZeroPlacement(f2, cfgPlacement);
        f2.Save();
        IGrannyFile f3 = ctx.LoadGrannyFile(dst);
        WriteGeoModel(f3, dst);
        Console.WriteLine("MODEL_DONE " + dst);
    }

    static void ConvertAnim(string name)
    {
        string src = Path.Combine(fbxDir, name + ".fbx");
        if (!File.Exists(src)) Fail("ANIM_SRC_MISSING " + src);
        string tmp = Path.Combine(outDir, name + "_src.fgx");
        string output = Path.Combine(outDir, name + ".fgx");
        FBXImporter.ImportFBXFile(src, tmp, node);
        IGrannyFile fa = ctx.LoadGrannyFile(tmp);
        fa.Animations[0].Name = name;
        Console.WriteLine("ANIM_LOADED " + name + " anims=" + fa.Animations.Count +
            " dur=" + (fa.Animations.Count > 0 ? fa.Animations[0].Duration.ToString() : "none"));
        IGrannyFile g = ctx.CreateEmptyGrannyFile(output);
        g.AddAnimationReference(fa.Animations[0]);
        try { g.AddArtToolAndExporterReference(fa); }
        catch (Exception e) { Console.WriteLine("ARTTOOL_SKIP " + name + " " + e.GetType().Name); }
        g.Save();
        WriteGeoAnim(g);
        Console.WriteLine("ANIM_DONE " + name);
    }
}
