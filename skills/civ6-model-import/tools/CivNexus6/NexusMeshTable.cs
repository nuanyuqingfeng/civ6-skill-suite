using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Reflection;
using System.Runtime.InteropServices;
using System.Text;
using System.Windows.Forms;
using Firaxis.Utility;
using Firaxis.Granny;
using NexusBuddy;

// 网格表读取：逐网格打印名字、顶点数、顶点成员布局、顶点包围盒与 palette 骨
class NexusMeshTable
{
    static GrannyContext ctx;
    static readonly CultureInfo CI = CultureInfo.InvariantCulture;

    static string F4(float v) { return v.ToString("F4", CI); }

    [StructLayout(LayoutKind.Sequential)]
    struct MEMORY_BASIC_INFORMATION
    {
        public IntPtr BaseAddress;
        public IntPtr AllocationBase;
        public uint AllocationProtect;
        public IntPtr RegionSize;
        public uint State;
        public uint Protect;
        public uint Type;
    }

    [DllImport("kernel32.dll")]
    static extern IntPtr VirtualQuery(IntPtr lpAddress, out MEMORY_BASIC_INFORMATION lpBuffer, IntPtr dwLength);

    static bool Readable(IntPtr p, int bytes)
    {
        if (p == IntPtr.Zero) return false;
        MEMORY_BASIC_INFORMATION mbi;
        int qsize = Marshal.SizeOf(typeof(MEMORY_BASIC_INFORMATION));
        if (VirtualQuery(p, out mbi, new IntPtr(qsize)) == IntPtr.Zero) return false;
        if (mbi.State != 0x1000) return false;
        if ((mbi.Protect & 0xEE) == 0) return false;
        long left = mbi.RegionSize.ToInt64() - (p.ToInt64() - mbi.BaseAddress.ToInt64());
        return left >= bytes;
    }

    static IntPtr RawPtr(IntPtr p, int off)
    {
        IntPtr ap = IntPtr.Add(p, off);
        if (!Readable(ap, 8)) throw new InvalidOperationException("不可读地址 0x" + ap.ToInt64().ToString("X") + " (基址 +" + off + ")");
        return (IntPtr)Marshal.ReadInt64(ap);
    }

    static float RawF32(IntPtr p, int off)
    {
        IntPtr ap = IntPtr.Add(p, off);
        if (!Readable(ap, 4)) throw new InvalidOperationException("不可读地址 0x" + ap.ToInt64().ToString("X") + " (基址 +" + off + ")");
        return Marshal.PtrToStructure<float>(ap);
    }

    static IntPtr MeshNative(IGrannyMesh mesh)
    {
        FieldInfo fi = mesh.GetType().GetField("m_pkMesh", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
        if (fi == null) throw new InvalidOperationException("类型 " + mesh.GetType().FullName + " 缺少字段 m_pkMesh");
        object v = fi.GetValue(mesh);
        if (v is IntPtr) return (IntPtr)v;
        unsafe { return (IntPtr)Pointer.Unbox(v); }
    }

    class VtxMember
    {
        public int Code;
        public string MName;
        public int ArrayWidth;
        public int ElemSize;
        public int Offset;
    }

    static int TypeSize(int code)
    {
        switch (code)
        {
            case 10: return 4;
            case 11: return 1;
            case 12: return 1;
            case 13: return 2;
            case 14: return 1;
            case 15: return 2;
            case 16: return 4;
            case 17: return 4;
            case 21: return 2;
        }
        throw new InvalidOperationException("未知顶点成员类型码 " + code);
    }

    static bool PrintableName(string s)
    {
        if (string.IsNullOrEmpty(s)) return false;
        foreach (char ch in s) if (ch < 32 || ch > 126) return false;
        return true;
    }

    static List<VtxMember> ReadTypeDefs(IntPtr arr, int stride, int nameOff, int widthOff)
    {
        List<VtxMember> list = new List<VtxMember>();
        int off = 0;
        while (true)
        {
            IntPtr entry = IntPtr.Add(arr, off);
            if (!Readable(entry, stride)) throw new InvalidOperationException("类型定义数组越界 off=" + off);
            int code = Marshal.ReadInt32(entry);
            if (code == 0) break;
            IntPtr np = (IntPtr)Marshal.ReadInt64(IntPtr.Add(entry, nameOff));
            string nm = Readable(np, 2) ? Marshal.PtrToStringAnsi(np) : null;
            if (!PrintableName(nm)) throw new InvalidOperationException("类型定义成员名非法 off=" + off + " name=" + (nm == null ? "null" : nm));
            VtxMember m = new VtxMember();
            m.Code = code;
            m.MName = nm;
            m.ArrayWidth = Marshal.ReadInt32(IntPtr.Add(entry, widthOff));
            m.ElemSize = TypeSize(code);
            list.Add(m);
            off += stride;
        }
        int cur = 0;
        foreach (VtxMember m in list)
        {
            m.Offset = cur;
            cur += m.ElemSize * m.ArrayWidth;
        }
        return list;
    }

    class MeshLayout
    {
        public int NameOff = -1;
        public int VtxOff = -1;
        public int VtxCountOff = -1;
        public int VtxArrayOff = -1;
        public int TypeDefStride = -1;
        public int TypeDefNameOff = -1;
        public int TypeDefWidthOff = -1;
    }

    static bool TryVertexData(IntPtr vtx, IGrannyMesh mesh, MeshLayout lay, out List<VtxMember> members)
    {
        members = null;
        if (!Readable(vtx, 32)) return false;
        int count = Marshal.ReadInt32(IntPtr.Add(vtx, lay.VtxCountOff));
        if (count != mesh.VertexCount) return false;
        IntPtr td = (IntPtr)Marshal.ReadInt64(vtx);
        if (!Readable(td, lay.TypeDefStride)) return false;
        IntPtr arr = (IntPtr)Marshal.ReadInt64(vtx, lay.VtxArrayOff);
        if (!Readable(arr, 4)) return false;
        try
        {
            List<VtxMember> list = ReadTypeDefs(td, lay.TypeDefStride, lay.TypeDefNameOff, lay.TypeDefWidthOff);
            bool hasPos = false;
            int sum = 0;
            foreach (VtxMember m in list)
            {
                if (m.MName == "Position") hasPos = true;
                sum += m.ElemSize * m.ArrayWidth;
            }
            if (!hasPos || sum <= 0) return false;
            members = list;
            return true;
        }
        catch (InvalidOperationException)
        {
            return false;
        }
    }

    static MeshLayout LocateMeshLayout(IGrannyMesh[] meshes, out int[] vtxOffs)
    {
        MeshLayout lay = new MeshLayout();
        vtxOffs = new int[meshes.Length];
        IGrannyMesh probe = meshes[0];
        IntPtr mp = MeshNative(probe);

        int nameOff = -1;
        for (int off = 0; off <= 72; off += 8)
        {
            if (!Readable(IntPtr.Add(mp, off), 8)) continue;
            IntPtr s = (IntPtr)Marshal.ReadInt64(IntPtr.Add(mp, off));
            if (!Readable(s, 2)) continue;
            string str = Marshal.PtrToStringAnsi(s);
            if (str == probe.Name) { nameOff = off; break; }
        }
        if (nameOff < 0) throw new InvalidOperationException("未能定位 granny_mesh.Name 字段偏移（探测网格 " + probe.Name + "）");
        lay.NameOff = nameOff;

        int[] countCandidates = new int[] { 8, 4, 12 };
        int[] arrayCandidates = new int[] { 16, 12, 8, 24 };
        int[] strideCandidates = new int[] { 44, 32 };
        int[] nameCandidates = new int[] { 8, 4 };
        int[] widthCandidates = new int[] { 24, 20, 12 };

        int need = 0;
        int foundOff = -1;
        for (int mi = 0; mi < meshes.Length; mi++)
        {
            IGrannyMesh m = meshes[mi];
            IntPtr mptr = MeshNative(m);
            for (int off = 8; off <= 72; off += 8)
            {
                if (!Readable(IntPtr.Add(mptr, off), 8)) continue;
                IntPtr vtx = (IntPtr)Marshal.ReadInt64(IntPtr.Add(mptr, off));
                if (!Readable(vtx, 32)) continue;
                foreach (int co in countCandidates)
                {
                    if (Marshal.ReadInt32(IntPtr.Add(vtx, co)) != m.VertexCount) continue;
                    foreach (int ao in arrayCandidates)
                    {
                        foreach (int so in strideCandidates)
                            foreach (int no in nameCandidates)
                                foreach (int wo in widthCandidates)
                                {
                                    MeshLayout cand = new MeshLayout();
                                    cand.VtxCountOff = co;
                                    cand.VtxArrayOff = ao;
                                    cand.TypeDefStride = so;
                                    cand.TypeDefNameOff = no;
                                    cand.TypeDefWidthOff = wo;
                                    List<VtxMember> members;
                                    if (!TryVertexData(vtx, m, cand, out members)) continue;
                                    cand.NameOff = nameOff;
                                    cand.VtxOff = off;
                                    lay = cand;
                                    foundOff = off;
                                    need++;
                                    goto nextMesh;
                                }
                    }
                }
            }
            throw new InvalidOperationException("网格 " + m.Name + " 无法定位 PrimaryVertexData（顶点数 " + m.VertexCount + "）");
        nextMesh:
            vtxOffs[mi] = foundOff;
        }
        if (need != meshes.Length) throw new InvalidOperationException("布局候选对 " + meshes.Length + " 个网格不一致");
        return lay;
    }

    static void Main(string[] args)
    {
        if (args.Length < 1)
        {
            Console.WriteLine("usage: NexusMeshTable <model.fgx>");
            Environment.Exit(2);
        }
        string modelPath = args[0];

        Application.EnableVisualStyles();
        Form form = new CivNexusSixApplicationForm();
        ctx = Context.Get<GrannyContext>();

        IGrannyFile mf = ctx.LoadGrannyFile(modelPath);
        Console.WriteLine("file=" + modelPath);
        Console.WriteLine("file_models=" + mf.Models.Count + " file_meshes=" + mf.Meshes.Count);
        for (int i = 0; i < mf.Meshes.Count; i++)
            Console.WriteLine("FILE_MESH[" + i + "] name=\"" + mf.Meshes[i].Name + "\" verts=" + mf.Meshes[i].VertexCount);

        for (int mi2 = 0; mi2 < mf.Models.Count; mi2++)
        {
            IGrannyModel model = mf.Models[mi2];
            IGrannySkeleton sk = model.Skeleton;
            Console.WriteLine("MODEL[" + mi2 + "] name=\"" + model.Name + "\" skeleton=\"" + sk.Name + "\" bones=" + sk.Bones.Count +
                " mesh_bindings=" + model.MeshBindings.Count);
            Console.WriteLine("  placement p=(" + F4(model.InitialPlacement.Position[0]) + "," + F4(model.InitialPlacement.Position[1]) + "," +
                F4(model.InitialPlacement.Position[2]) + ")");

            IGrannyMesh[] meshes = new IGrannyMesh[model.MeshBindings.Count];
            for (int i = 0; i < meshes.Length; i++) meshes[i] = model.MeshBindings[i];
            int[] vtxOffs;
            MeshLayout lay = LocateMeshLayout(meshes, out vtxOffs);
            Console.WriteLine("  layout Name@" + lay.NameOff + " PrimaryVertexData@" + lay.VtxOff + " VertexCount@" + lay.VtxCountOff +
                " VerticesArray@" + lay.VtxArrayOff + " TypeDefStride=" + lay.TypeDefStride);

            for (int i = 0; i < meshes.Length; i++)
            {
                IGrannyMesh mesh = meshes[i];
                IntPtr mptr = MeshNative(mesh);
                IntPtr vtx = RawPtr(mptr, vtxOffs[i]);
                List<VtxMember> members = ReadTypeDefs(RawPtr(vtx, 0), lay.TypeDefStride, lay.TypeDefNameOff, lay.TypeDefWidthOff);
                VtxMember mPos = null;
                int stride = 0;
                StringBuilder layoutLine = new StringBuilder();
                foreach (VtxMember m in members)
                {
                    stride += m.ElemSize * m.ArrayWidth;
                    if (m.MName == "Position") mPos = m;
                    layoutLine.Append(m.MName).Append("[t").Append(m.Code).Append(" x").Append(m.ArrayWidth).Append(" @").Append(m.Offset).Append("] ");
                }
                if (mPos == null) throw new InvalidOperationException("网格 " + mesh.Name + " 缺少 Position 成员");

                float[] mn = new float[] { float.MaxValue, float.MaxValue, float.MaxValue };
                float[] mx = new float[] { float.MinValue, float.MinValue, float.MinValue };
                IntPtr arr = RawPtr(vtx, lay.VtxArrayOff);
                for (int vi = 0; vi < mesh.VertexCount; vi++)
                {
                    IntPtr p = IntPtr.Add(arr, vi * stride);
                    for (int k = 0; k < 3; k++)
                    {
                        float v = RawF32(p, mPos.Offset + k * 4);
                        if (v < mn[k]) mn[k] = v;
                        if (v > mx[k]) mx[k] = v;
                    }
                }
                Console.WriteLine("MESH[" + i + "] name=\"" + mesh.Name + "\" verts=" + mesh.VertexCount + " stride=" + stride +
                    " palette=" + mesh.BoneBindings.Count);
                Console.WriteLine("  members " + layoutLine.ToString().TrimEnd());
                Console.WriteLine("  bbox_min=(" + F4(mn[0]) + ", " + F4(mn[1]) + ", " + F4(mn[2]) + ")");
                Console.WriteLine("  bbox_max=(" + F4(mx[0]) + ", " + F4(mx[1]) + ", " + F4(mx[2]) + ")");
                Console.WriteLine("  bbox_span=(" + F4(mx[0] - mn[0]) + ", " + F4(mx[1] - mn[1]) + ", " + F4(mx[2] - mn[2]) + ")");
                StringBuilder pal = new StringBuilder();
                for (int k = 0; k < mesh.BoneBindings.Count; k++)
                {
                    if (k > 0) pal.Append(",");
                    pal.Append(mesh.BoneBindings[k]);
                }
                Console.WriteLine("  palette=[" + pal.ToString() + "]");

                // 逐顶点主导骨按骨族聚合：段间位移若来自骨骼侧，各段会落在不同骨族上
                VtxMember mW = null, mI = null;
                foreach (VtxMember m in members)
                {
                    if (m.MName == "BoneWeights") mW = m;
                    if (m.MName == "BoneIndices") mI = m;
                }
                if (mW == null || mI == null) throw new InvalidOperationException("网格 " + mesh.Name + " 缺少 BoneWeights/BoneIndices");
                int nw = mW.ArrayWidth;
                Dictionary<string, int> famCount = new Dictionary<string, int>();
                Dictionary<string, float[]> famMin = new Dictionary<string, float[]>();
                Dictionary<string, float[]> famMax = new Dictionary<string, float[]>();
                for (int vi = 0; vi < mesh.VertexCount; vi++)
                {
                    IntPtr p = IntPtr.Add(arr, vi * stride);
                    int best = -1, bestW = -1;
                    for (int j = 0; j < nw; j++)
                    {
                        int w = Marshal.ReadByte(p, mW.Offset + j);
                        if (w > bestW) { bestW = w; best = j; }
                    }
                    if (bestW <= 0) throw new InvalidOperationException("顶点 " + mesh.Name + "#" + vi + " 全零权重");
                    int palIdx = Marshal.ReadByte(p, mI.Offset + best);
                    if (palIdx >= mesh.BoneBindings.Count) throw new InvalidOperationException("顶点 " + mesh.Name + "#" + vi + " 骨索引 " + palIdx + " 超出 palette");
                    string bn = mesh.BoneBindings[palIdx];
                    string fam;
                    if (bn.StartsWith("Bone_Hair")) fam = "Bone_Hair*";
                    else if (bn.StartsWith("Bone_Piao")) fam = "Bone_Piao*";
                    else if (bn.StartsWith("Bone_Skirt")) fam = "Bone_Skirt*";
                    else if (bn.StartsWith("Bip001")) fam = "Bip001*";
                    else if (bn.StartsWith("WeaponProp")) fam = "WeaponProp*";
                    else fam = "Other(" + bn + ")";
                    int c;
                    famCount.TryGetValue(fam, out c);
                    famCount[fam] = c + 1;
                    float[] fmn, fmx;
                    if (!famMin.TryGetValue(fam, out fmn)) { fmn = new float[] { float.MaxValue, float.MaxValue, float.MaxValue }; famMin[fam] = fmn; }
                    if (!famMax.TryGetValue(fam, out fmx)) { fmx = new float[] { float.MinValue, float.MinValue, float.MinValue }; famMax[fam] = fmx; }
                    for (int k = 0; k < 3; k++)
                    {
                        float v = RawF32(p, mPos.Offset + k * 4);
                        if (v < fmn[k]) fmn[k] = v;
                        if (v > fmx[k]) fmx[k] = v;
                    }
                }
                foreach (KeyValuePair<string, int> kv in famCount)
                {
                    float[] fmn = famMin[kv.Key];
                    float[] fmx = famMax[kv.Key];
                    Console.WriteLine("  FAM " + kv.Key + " verts=" + kv.Value +
                        " z=[" + F4(fmn[2]) + ", " + F4(fmx[2]) + "] span=" + F4(fmx[2] - fmn[2]) +
                        " x=[" + F4(fmn[0]) + ", " + F4(fmx[0]) + "] y=[" + F4(fmn[1]) + ", " + F4(fmx[1]) + "]");
                }
            }
        }
    }
}
