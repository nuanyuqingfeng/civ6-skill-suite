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

// rest 世界变换 vs 蒙皮绑定矩阵的自洽性实测 + 静止姿势重蒙皮
// 用法: RestVsBind <model.fgx> <outDir>
class RestVsBind
{
    static GrannyContext ctx;
    static IGrannyFile kFile;
    static IGrannyModel kModel;
    static readonly CultureInfo CI = CultureInfo.InvariantCulture;
    static StringBuilder slog = new StringBuilder();
    static string outDir;

    static void Log(string s)
    {
        Console.WriteLine(s);
        slog.AppendLine(s);
    }

    static string F3(float v) { return v.ToString("F3", CI); }
    static string F6(float v) { return v.ToString("F6", CI); }
    static string E6(float v) { return v.ToString("E6", CI); }

    // ============ 原生内存读取 ============
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
        if (!Readable(ap, 8)) throw new InvalidOperationException("unreadable address +" + off);
        return (IntPtr)Marshal.ReadInt64(ap);
    }

    static int RawI32(IntPtr p, int off)
    {
        IntPtr ap = IntPtr.Add(p, off);
        if (!Readable(ap, 4)) throw new InvalidOperationException("unreadable address +" + off);
        return Marshal.ReadInt32(ap);
    }

    static float RawF32(IntPtr p, int off)
    {
        IntPtr ap = IntPtr.Add(p, off);
        if (!Readable(ap, 4)) throw new InvalidOperationException("unreadable address +" + off + " ap=0x" + ap.ToInt64().ToString("X"));
        return Marshal.PtrToStructure<float>(ap);
    }

    static IntPtr MeshNative(IGrannyMesh mesh)
    {
        FieldInfo fi = mesh.GetType().GetField("m_pkMesh", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
        if (fi == null) throw new InvalidOperationException("type " + mesh.GetType().FullName + " has no m_pkMesh");
        object v = fi.GetValue(mesh);
        if (v is IntPtr) return (IntPtr)v;
        unsafe { return (IntPtr)Pointer.Unbox(v); }
    }

    static IntPtr BoneNative(IGrannyBone bone)
    {
        FieldInfo fi = bone.GetType().GetField("m_pkBone", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
        if (fi == null) throw new InvalidOperationException("type " + bone.GetType().FullName + " has no m_pkBone");
        object v = fi.GetValue(bone);
        if (v is IntPtr) return (IntPtr)v;
        unsafe { return (IntPtr)Pointer.Unbox(v); }
    }

    // 骨内 LocalTransform: +16 Position(3), +28 Orientation(4), +44 ScaleShear(9), +80 InverseWorld(16)
    static float[] BoneScaleShear(IGrannyBone bone)
    {
        IntPtr p = BoneNative(bone);
        float[] pos = bone.LocalTransform.Position;
        float[] iw = bone.InverseWorldTransform;
        for (int k = 0; k < 3; k++)
            if (Math.Abs(RawF32(p, 16 + k * 4) - pos[k]) > 1e-6f)
                throw new InvalidOperationException("bone " + bone.Name + " offset +16 is not Position");
        for (int k = 0; k < 4; k++)
            if (Math.Abs(RawF32(p, 28 + k * 4) - bone.LocalTransform.Orientation[k]) > 1e-6f)
                throw new InvalidOperationException("bone " + bone.Name + " offset +28 is not Orientation");
        for (int k = 0; k < 16; k++)
            if (Math.Abs(RawF32(p, 80 + k * 4) - iw[k]) > 1e-6f)
                throw new InvalidOperationException("bone " + bone.Name + " offset +80 is not InverseWorldTransform");
        float[] ss = new float[9];
        for (int k = 0; k < 9; k++) ss[k] = RawF32(p, 44 + k * 4);
        return ss;
    }

    // ============ 矩阵（行向量约定 v_out = v · M，平移在 [12..14]） ============
    static float[] MatId()
    {
        float[] m = new float[16];
        m[0] = 1f; m[5] = 1f; m[10] = 1f; m[15] = 1f;
        return m;
    }

    static float[] MatMul(float[] a, float[] b)
    {
        float[] m = new float[16];
        for (int r = 0; r < 4; r++)
            for (int c = 0; c < 4; c++)
            {
                float s = 0f;
                for (int k = 0; k < 4; k++) s += a[r * 4 + k] * b[k * 4 + c];
                m[r * 4 + c] = s;
            }
        return m;
    }

    static float[] QuatMat(float[] q)
    {
        float x = q[0], y = q[1], z = q[2], w = q[3];
        float[] m = MatId();
        m[0] = 1f - 2f * (y * y + z * z);
        m[1] = 2f * (x * y + z * w);
        m[2] = 2f * (x * z - y * w);
        m[4] = 2f * (x * y - z * w);
        m[5] = 1f - 2f * (x * x + z * z);
        m[6] = 2f * (y * z + x * w);
        m[8] = 2f * (x * z + y * w);
        m[9] = 2f * (y * z - x * w);
        m[10] = 1f - 2f * (x * x + y * y);
        return m;
    }

    static float[] LocalMat(float[] pos, float[] q, float[] ss, int scaleMode)
    {
        float[] r = QuatMat(q);
        float[] m = MatId();
        if (scaleMode == 0)
        {
            for (int i = 0; i < 3; i++) for (int j = 0; j < 3; j++) m[i * 4 + j] = r[i * 4 + j];
        }
        else if (scaleMode == 1)
        {
            for (int i = 0; i < 3; i++)
                for (int j = 0; j < 3; j++)
                {
                    float s = 0f;
                    for (int k = 0; k < 3; k++) s += r[i * 4 + k] * ss[k * 3 + j];
                    m[i * 4 + j] = s;
                }
        }
        else
        {
            for (int i = 0; i < 3; i++)
                for (int j = 0; j < 3; j++)
                {
                    float s = 0f;
                    for (int k = 0; k < 3; k++) s += ss[i * 3 + k] * r[k * 4 + j];
                    m[i * 4 + j] = s;
                }
        }
        m[12] = pos[0]; m[13] = pos[1]; m[14] = pos[2]; m[15] = 1f;
        return m;
    }

    static float Det3(float[] m)
    {
        return m[0] * (m[5] * m[10] - m[6] * m[9])
             - m[1] * (m[4] * m[10] - m[6] * m[8])
             + m[2] * (m[4] * m[9] - m[5] * m[8]);
    }

    static float InvScale(float[] m, string name)
    {
        float d = Det3(m);
        if (Math.Abs(d) < 1e-20f) throw new InvalidOperationException("bone " + name + " InverseWorld 3x3 determinant is zero");
        return (float)Math.Pow(Math.Abs(d), 1.0 / 3.0);
    }

    static float[] Rot3(float[] m, string name)
    {
        float s = InvScale(m, name);
        float[] o = MatId();
        for (int r = 0; r < 3; r++)
            for (int c = 0; c < 3; c++) o[r * 4 + c] = m[r * 4 + c] / s;
        return o;
    }

    static float[] InvRot3(float[] m, string name)
    {
        float s = InvScale(m, name);
        float[] o = MatId();
        for (int r = 0; r < 3; r++)
            for (int c = 0; c < 3; c++) o[c * 4 + r] = m[r * 4 + c] / s;
        return o;
    }

    // 仿射 4x4 求逆（行向量约定）
    static float[] InvAffine(float[] m, string name)
    {
        float d = Det3(m);
        if (Math.Abs(d) < 1e-20f) throw new InvalidOperationException("bone " + name + " InverseWorld 3x3 determinant is zero");
        float[] i9 = new float[9];
        i9[0] = (m[5] * m[10] - m[6] * m[9]) / d;
        i9[1] = (m[2] * m[9] - m[1] * m[10]) / d;
        i9[2] = (m[1] * m[6] - m[2] * m[5]) / d;
        i9[3] = (m[6] * m[8] - m[4] * m[10]) / d;
        i9[4] = (m[0] * m[10] - m[2] * m[8]) / d;
        i9[5] = (m[2] * m[4] - m[0] * m[6]) / d;
        i9[6] = (m[4] * m[9] - m[5] * m[8]) / d;
        i9[7] = (m[1] * m[8] - m[0] * m[9]) / d;
        i9[8] = (m[0] * m[5] - m[1] * m[4]) / d;
        float[] o = MatId();
        for (int r = 0; r < 3; r++)
            for (int c = 0; c < 3; c++) o[r * 4 + c] = i9[r * 3 + c];
        for (int j = 0; j < 3; j++)
            o[12 + j] = -(m[12] * i9[j] + m[13] * i9[3 + j] + m[14] * i9[6 + j]);
        return o;
    }

    static float RotAngleDeg(float[] a, float[] b)
    {
        float tr = 0f;
        for (int i = 0; i < 3; i++)
            for (int k = 0; k < 3; k++) tr += a[k * 4 + i] * b[k * 4 + i];
        float c = (tr - 1f) * 0.5f;
        if (c > 1f) c = 1f;
        if (c < -1f) c = -1f;
        return (float)(Math.Acos(c) * 180.0 / Math.PI);
    }

    static float[] TransformPoint(float[] m, float[] v)
    {
        float[] o = new float[3];
        for (int j = 0; j < 3; j++)
            o[j] = v[0] * m[j] + v[1] * m[4 + j] + v[2] * m[8 + j] + m[12 + j];
        return o;
    }

    static void BuildWorld(float[][] pos, float[][] q, float[][] ss, int[] parent, int n, int scaleMode, out float[][] world)
    {
        world = new float[n][];
        for (int i = 0; i < n; i++)
        {
            float[] local = LocalMat(pos[i], q[i], ss[i], scaleMode);
            if (parent[i] < 0) world[i] = local;
            else world[i] = MatMul(local, world[parent[i]]);
        }
    }

    static float Median(float[] a)
    {
        float[] c = new float[a.Length];
        Array.Copy(a, c, a.Length);
        Array.Sort(c);
        if (c.Length == 0) throw new InvalidOperationException("median of empty");
        if (c.Length % 2 == 1) return c[c.Length / 2];
        return (c[c.Length / 2 - 1] + c[c.Length / 2]) * 0.5f;
    }

    static float Mean(float[] a)
    {
        double s = 0.0;
        for (int i = 0; i < a.Length; i++) s += a[i];
        return (float)(s / a.Length);
    }

    // ============ 顶点成员 ============
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
        throw new InvalidOperationException("unknown vertex member type code " + code);
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
            if (!Readable(entry, stride)) throw new InvalidOperationException("type def array overflow off=" + off);
            int code = Marshal.ReadInt32(entry);
            if (code == 0) break;
            IntPtr np = (IntPtr)Marshal.ReadInt64(IntPtr.Add(entry, nameOff));
            string nm = Readable(np, 2) ? Marshal.PtrToStringAnsi(np) : null;
            if (!PrintableName(nm)) throw new InvalidOperationException("bad type def member name off=" + off + " name=" + (nm == null ? "null" : nm));
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

    static MeshLayout LocateMeshLayout(IGrannyMesh[] meshes)
    {
        MeshLayout lay = new MeshLayout();
        int[] countCandidates = new int[] { 8, 4, 12 };
        int[] arrayCandidates = new int[] { 16, 12, 8, 24 };
        int[] strideCandidates = new int[] { 44, 32 };
        int[] nameCandidates = new int[] { 8, 4 };
        int[] widthCandidates = new int[] { 24, 20, 12 };
        int need = 0;
        foreach (IGrannyMesh m in meshes)
        {
            IntPtr mptr = MeshNative(m);
            bool hit = false;
            for (int off = 8; off <= 72 && !hit; off += 8)
            {
                if (!Readable(IntPtr.Add(mptr, off), 8)) continue;
                IntPtr vtx = (IntPtr)Marshal.ReadInt64(IntPtr.Add(mptr, off));
                if (!Readable(vtx, 32)) continue;
                for (int ci = 0; ci < countCandidates.Length && !hit; ci++)
                {
                    int co = countCandidates[ci];
                    if (Marshal.ReadInt32(IntPtr.Add(vtx, co)) != m.VertexCount) continue;
                    for (int ai = 0; ai < arrayCandidates.Length && !hit; ai++)
                        for (int si = 0; si < strideCandidates.Length && !hit; si++)
                            for (int ni = 0; ni < nameCandidates.Length && !hit; ni++)
                                for (int wi = 0; wi < widthCandidates.Length && !hit; wi++)
                                {
                                    MeshLayout cand = new MeshLayout();
                                    cand.VtxCountOff = co;
                                    cand.VtxArrayOff = arrayCandidates[ai];
                                    cand.TypeDefStride = strideCandidates[si];
                                    cand.TypeDefNameOff = nameCandidates[ni];
                                    cand.TypeDefWidthOff = widthCandidates[wi];
                                    List<VtxMember> members;
                                    if (!TryVertexData(vtx, m, cand, out members)) continue;
                                    cand.VtxOff = off;
                                    lay = cand;
                                    need++;
                                    hit = true;
                                }
                }
            }
            if (!hit) throw new InvalidOperationException("mesh " + m.Name + " PrimaryVertexData not located (verts " + m.VertexCount + ")");
        }
        if (need != meshes.Length) throw new InvalidOperationException("layout candidate mismatch over " + meshes.Length + " meshes");
        return lay;
    }

    static string Family(string boneName)
    {
        if (boneName.StartsWith("Bone_Hair")) return "Bone_Hair";
        if (boneName.StartsWith("Bip001")) return "Bip001";
        if (boneName.StartsWith("Bone_Piao")) return "Bone_Piao";
        if (boneName.StartsWith("Bone_Skirt")) return "Bone_Skirt";
        return "Other";
    }

    static void Main(string[] args)
    {
        if (args.Length < 2)
        {
            Console.WriteLine("usage: RestVsBind <model.fgx> <outDir>");
            Environment.Exit(2);
        }
        string modelPath = args[0];
        outDir = args[1];
        Directory.CreateDirectory(outDir);

        Application.EnableVisualStyles();
        Form form = new CivNexusSixApplicationForm();
        ctx = Context.Get<GrannyContext>();

        Log("### INPUT");
        Log("model=" + modelPath);
        Log("pointer_size=" + IntPtr.Size);

        IGrannyFile mf = ctx.LoadGrannyFile(modelPath);
        kFile = mf;
        IGrannyModel model = mf.Models[0];
        kModel = model;
        IGrannySkeleton sk = model.Skeleton;
        IList<IGrannyBone> bones = sk.Bones;
        int nb = bones.Count;
        Log("model=" + model.Name + " skeleton=" + sk.Name + " bones=" + nb +
            " mesh_bindings=" + model.MeshBindings.Count + " file_meshes=" + mf.Meshes.Count);

        float[][] pos = new float[nb][];
        float[][] q = new float[nb][];
        float[][] ss = new float[nb][];
        float[][] inv = new float[nb][];
        int[] parent = new int[nb];
        string[] bname = new string[nb];
        for (int i = 0; i < nb; i++)
        {
            IGrannyBone b = bones[i];
            bname[i] = b.Name;
            parent[i] = b.ParentIndex;
            pos[i] = b.LocalTransform.Position;
            q[i] = b.LocalTransform.Orientation;
            inv[i] = b.InverseWorldTransform;
            ss[i] = BoneScaleShear(b);
            if (inv[i].Length != 16) throw new InvalidOperationException("bone " + b.Name + " InverseWorldTransform dim " + inv[i].Length);
            if (parent[i] >= i) throw new InvalidOperationException("bone " + b.Name + " parent " + parent[i] + " >= self " + i);
        }
        Log("BONE_READ_OK bones=" + nb + " max_parent=" + MaxOf(parent));
        Log("BONE0 name=" + bname[0] + " parent=" + parent[0]);

        // ScaleShear 偏离单位阵统计（自检 +44 偏移正确）
        int ssNonId = 0; float ssMaxDev = 0f;
        for (int i = 0; i < nb; i++)
        {
            float d = 0f;
            for (int k = 0; k < 9; k++)
            {
                float unit = (k % 4 == 0) ? 1f : 0f;
                d = Math.Max(d, Math.Abs(ss[i][k] - unit));
            }
            if (d > 1e-4f) ssNonId++;
            if (d > ssMaxDev) ssMaxDev = d;
        }
        Log("SS_STATS nonidentity_bones=" + ssNonId + "/" + nb + " max_dev=" + E6(ssMaxDev));

        // 逐骨表
        List<string> boneRows = new List<string>();
        boneRows.Add("idx\tname\tparent\tpx\tpy\tpz\tqx\tqy\tqz\tqw\t" +
            "ss00\tss01\tss02\tss10\tss11\tss12\tss20\tss21\tss22\t" +
            "iw00\tiw01\tiw02\tiw03\tiw10\tiw11\tiw12\tiw13\tiw20\tiw21\tiw22\tiw23\tiw30\tiw31\tiw32\tiw33");
        for (int i = 0; i < nb; i++)
        {
            StringBuilder sb = new StringBuilder();
            sb.Append(i).Append('\t').Append(bname[i]).Append('\t').Append(parent[i]);
            for (int k = 0; k < 3; k++) sb.Append('\t').Append(F6(pos[i][k]));
            for (int k = 0; k < 4; k++) sb.Append('\t').Append(F6(q[i][k]));
            for (int k = 0; k < 9; k++) sb.Append('\t').Append(F6(ss[i][k]));
            for (int k = 0; k < 16; k++) sb.Append('\t').Append(F6(inv[i][k]));
            boneRows.Add(sb.ToString());
        }
        File.WriteAllLines(Path.Combine(outDir, "bones.tsv"), boneRows.ToArray(), new UTF8Encoding(false));

        // ============ 旋转标定：rest 链世界旋转 vs InverseBind 旋转（互逆） ============
        int bestMode = -1;
        float bestAng = float.MaxValue;
        for (int mode = 0; mode < 3; mode++)
        {
            float[][] w;
            BuildWorld(pos, q, ss, parent, nb, mode, out w);
            float worst = 0f;
            for (int i = 0; i < nb; i++)
            {
                float a = RotAngleDeg(Rot3(w[i], bname[i]), InvRot3(inv[i], bname[i]));
                if (a > worst) worst = a;
            }
            Log("CALIB scaleMode=" + mode + " max_angle_deg=" + F3(worst));
            if (worst < bestAng) { bestAng = worst; bestMode = mode; }
        }
        Log("CALIB_CHOSEN scaleMode=" + bestMode + " max_angle_deg=" + F6(bestAng));

        float[][] restWorld;
        BuildWorld(pos, q, ss, parent, nb, bestMode, out restWorld);

        // ============ 第 2 步：invBind⁻¹ 对 rest 世界变换 ============
        float[] dt = new float[nb];
        float[] dang = new float[nb];
        float[] bindScale = new float[nb];
        float[] restScale = new float[nb];
        int over1cm = 0, over10cm = 0, over1deg = 0;
        string maxDtBone = "-", maxAngBone = "-";
        float maxDt = 0f, maxAng = 0f;
        List<string> cmpRows = new List<string>();
        cmpRows.Add("idx\tname\tparent\tfamily\tinvbind_scale\tinvt_x\tinvt_y\tinvt_z\trest_t_x\trest_t_y\trest_t_z\tdt_cm\tdang_deg");
        for (int i = 0; i < nb; i++)
        {
            float[] bindWorld = InvAffine(inv[i], bname[i]);
            bindScale[i] = InvScale(inv[i], bname[i]);
            restScale[i] = InvScale(restWorld[i], bname[i]);
            float[] d = new float[] {
                bindWorld[12] - restWorld[i][12],
                bindWorld[13] - restWorld[i][13],
                bindWorld[14] - restWorld[i][14] };
            dt[i] = (float)Math.Sqrt(d[0] * d[0] + d[1] * d[1] + d[2] * d[2]);
            dang[i] = RotAngleDeg(Rot3(bindWorld, bname[i]), Rot3(restWorld[i], bname[i]));
            if (dt[i] > 1f) over1cm++;
            if (dt[i] > 10f) over10cm++;
            if (dang[i] > 1f) over1deg++;
            if (dt[i] > maxDt) { maxDt = dt[i]; maxDtBone = bname[i]; }
            if (dang[i] > maxAng) { maxAng = dang[i]; maxAngBone = bname[i]; }
            cmpRows.Add(i + "\t" + bname[i] + "\t" + parent[i] + "\t" + Family(bname[i]) + "\t" +
                E6(bindScale[i]) + "\t" +
                F6(bindWorld[12]) + "\t" + F6(bindWorld[13]) + "\t" + F6(bindWorld[14]) + "\t" +
                F6(restWorld[i][12]) + "\t" + F6(restWorld[i][13]) + "\t" + F6(restWorld[i][14]) + "\t" +
                F6(dt[i]) + "\t" + F6(dang[i]));
        }
        File.WriteAllLines(Path.Combine(outDir, "inv_vs_rest.tsv"), cmpRows.ToArray(), new UTF8Encoding(false));

        Log("STEP2 dt_cm median=" + F6(Median(dt)) + " mean=" + F6(Mean(dt)) + " max=" + F6(maxDt) +
            " max_bone=" + maxDtBone + " over_1cm=" + over1cm + "/" + nb + " over_10cm=" + over10cm);
        Log("STEP2 dang_deg median=" + F6(Median(dang)) + " mean=" + F6(Mean(dang)) + " max=" + F6(maxAng) +
            " max_bone=" + maxAngBone + " over_1deg=" + over1deg + "/" + nb);
        {
            float bmin = float.MaxValue, bmax = float.MinValue, rmin = float.MaxValue, rmax = float.MinValue;
            for (int i = 0; i < nb; i++)
            {
                if (bindScale[i] < bmin) bmin = bindScale[i];
                if (bindScale[i] > bmax) bmax = bindScale[i];
                if (restScale[i] < rmin) rmin = restScale[i];
                if (restScale[i] > rmax) rmax = restScale[i];
            }
            Log("STEP2 invbind_scale_min=" + E6(bmin) + " max=" + E6(bmax) +
                " rest_scale_min=" + E6(rmin) + " rest_scale_max=" + E6(rmax));
        }

        // ============ 第 3 步：静止姿势重蒙皮 ============
        float[][] skinRest = new float[nb][];
        for (int i = 0; i < nb; i++) skinRest[i] = MatMul(inv[i], restWorld[i]);

        IGrannyMesh[] meshes = new IGrannyMesh[model.MeshBindings.Count];
        for (int mi = 0; mi < meshes.Length; mi++) meshes[mi] = model.MeshBindings[mi];
        MeshLayout lay = LocateMeshLayout(meshes);
        Log("LAYOUT vtx@" + lay.VtxOff + " count@" + lay.VtxCountOff + " array@" + lay.VtxArrayOff +
            " td_stride=" + lay.TypeDefStride + " td_name@" + lay.TypeDefNameOff + " td_width@" + lay.TypeDefWidthOff);

        Dictionary<string, int> boneIndex = new Dictionary<string, int>();
        for (int i = 0; i < nb; i++)
        {
            if (boneIndex.ContainsKey(bname[i])) throw new InvalidOperationException("duplicate bone name " + bname[i]);
            boneIndex[bname[i]] = i;
        }

        string[] famNames = new string[] { "Bone_Hair", "Bip001", "Bone_Piao", "Bone_Skirt", "Other" };
        int[] famCount = new int[famNames.Length];
        double[] famSumDisp = new double[famNames.Length];
        float[] famMaxDisp = new float[famNames.Length];
        double[] boneMass = new double[nb];
        float[] boneMaxDisp = new float[nb];
        int[] boneDomCount = new int[nb];
        bool[] inPalette = new bool[nb];

        int totalVerts = 0;
        int slotMax = 0;
        float[] vmin = new float[] { float.MaxValue, float.MaxValue, float.MaxValue };
        float[] vmax = new float[] { float.MinValue, float.MinValue, float.MinValue };
        float[] nmin = new float[] { float.MaxValue, float.MaxValue, float.MaxValue };
        float[] nmax = new float[] { float.MinValue, float.MinValue, float.MinValue };
        List<string> vrows = new List<string>();
        vrows.Add("mesh\tvidx\tbx\tby\tbz\tnx\tny\tnz\tdisp\tdx\tdy\tdz\tdom_bone\tfamily\tnz_slots");
        List<float> dispList = new List<float>();
        double dxAcc = 0.0, dyAcc = 0.0, dzAcc = 0.0;

        for (int mi = 0; mi < meshes.Length; mi++)
        {
            IGrannyMesh mesh = meshes[mi];
            int vcount = mesh.VertexCount;
            int palN = mesh.BoneBindings.Count;
            string meshName = mesh.Name;
            IntPtr mptr = MeshNative(mesh);
            IntPtr vtx = RawPtr(mptr, lay.VtxOff);
            List<VtxMember> members = ReadTypeDefs(RawPtr(vtx, 0), lay.TypeDefStride, lay.TypeDefNameOff, lay.TypeDefWidthOff);
            int stride = 0;
            VtxMember mPos = null, mW = null, mI = null;
            foreach (VtxMember m in members)
            {
                stride += m.ElemSize * m.ArrayWidth;
                if (m.MName == "Position") mPos = m;
                if (m.MName == "BoneWeights") mW = m;
                if (m.MName == "BoneIndices") mI = m;
            }
            if (mPos == null || mW == null || mI == null) throw new InvalidOperationException("mesh " + meshName + " missing Position/BoneWeights/BoneIndices");
            int nw = mW.ArrayWidth;
            if (nw != mI.ArrayWidth || nw < 1 || nw > 8) throw new InvalidOperationException("mesh " + meshName + " weight slots bad " + mW.ArrayWidth + "/" + mI.ArrayWidth);
            Log("MESH name=" + meshName + " verts=" + vcount + " stride=" + stride + " palette=" + palN + " slots=" + nw);

            int[] palette = new int[palN];
            for (int k = 0; k < palette.Length; k++)
            {
                int bi;
                if (!boneIndex.TryGetValue(mesh.BoneBindings[k], out bi)) throw new InvalidOperationException("palette bone " + mesh.BoneBindings[k] + " not in skeleton");
                palette[k] = bi;
                inPalette[bi] = true;
            }
            Log("PALETTE0 " + mesh.BoneBindings[0] + " PALETTE_LAST " + mesh.BoneBindings[palette.Length - 1]);

            IntPtr arr = RawPtr(vtx, lay.VtxArrayOff);
            {
                MEMORY_BASIC_INFORMATION mbi2;
                if (VirtualQuery(arr, out mbi2, new IntPtr(Marshal.SizeOf(typeof(MEMORY_BASIC_INFORMATION)))) == IntPtr.Zero)
                    throw new InvalidOperationException("VirtualQuery failed on vertex array");
                Log("VTXARRAY region_size=" + mbi2.RegionSize.ToInt64() +
                    " protect=0x" + mbi2.Protect.ToString("X") + " need_bytes=" + ((long)vcount * stride) +
                    " committed=" + (mbi2.State == 0x1000));
            }
            int vbytes = checked(vcount * stride);
            byte[] vbuf = new byte[vbytes];
            Marshal.Copy(arr, vbuf, 0, vbytes);
            Log("VBUF_BYTES " + vbytes);
            for (int vi = 0; vi < vcount; vi++)
            {
                int bo = vi * stride;
                float[] vb = new float[3];
                vb[0] = BitConverter.ToSingle(vbuf, bo + mPos.Offset);
                vb[1] = BitConverter.ToSingle(vbuf, bo + mPos.Offset + 4);
                vb[2] = BitConverter.ToSingle(vbuf, bo + mPos.Offset + 8);
                int[] w = new int[nw];
                int[] idx = new int[nw];
                int wsum = 0;
                for (int j = 0; j < nw; j++)
                {
                    w[j] = vbuf[bo + mW.Offset + j];
                    idx[j] = vbuf[bo + mI.Offset + j];
                    wsum += w[j];
                }
                if (wsum != 255) throw new InvalidOperationException("mesh " + mesh.Name + " vertex " + vi + " weight sum " + wsum);
                int nz = 0;
                for (int j = 0; j < nw; j++) if (w[j] != 0) nz++;
                if (nz > slotMax) slotMax = nz;
                float[] vo = new float[] { 0f, 0f, 0f };
                for (int j = 0; j < nw; j++)
                {
                    if (w[j] == 0) continue;
                    if (idx[j] >= palette.Length) throw new InvalidOperationException("mesh " + mesh.Name + " vertex " + vi + " index " + idx[j] + " >= palette " + palette.Length);
                    float fw = w[j] / 255f;
                    float[] t = TransformPoint(skinRest[palette[idx[j]]], vb);
                    vo[0] += fw * t[0];
                    vo[1] += fw * t[1];
                    vo[2] += fw * t[2];
                }
                int dom = -1, domW = -1;
                for (int j = 0; j < nw; j++) if (w[j] > domW) { domW = w[j]; dom = j; }
                int domBone = palette[idx[dom]];
                float dx = vo[0] - vb[0], dy = vo[1] - vb[1], dz = vo[2] - vb[2];
                float disp = (float)Math.Sqrt(dx * dx + dy * dy + dz * dz);
                dispList.Add(disp);
                dxAcc += Math.Abs(dx); dyAcc += Math.Abs(dy); dzAcc += Math.Abs(dz);
                for (int j = 0; j < nw; j++)
                    if (w[j] != 0) boneMass[palette[idx[j]]] += (w[j] / 255.0) * disp;
                boneDomCount[domBone]++;
                if (disp > boneMaxDisp[domBone]) boneMaxDisp[domBone] = disp;
                string fam = Family(bname[domBone]);
                int fi = Array.IndexOf(famNames, fam);
                famCount[fi]++;
                famSumDisp[fi] += disp;
                if (disp > famMaxDisp[fi]) famMaxDisp[fi] = disp;
                for (int k = 0; k < 3; k++)
                {
                    if (vb[k] < vmin[k]) vmin[k] = vb[k];
                    if (vb[k] > vmax[k]) vmax[k] = vb[k];
                    if (vo[k] < nmin[k]) nmin[k] = vo[k];
                    if (vo[k] > nmax[k]) nmax[k] = vo[k];
                }
                totalVerts++;
                vrows.Add(mesh.Name + "\t" + vi + "\t" + F3(vb[0]) + "\t" + F3(vb[1]) + "\t" + F3(vb[2]) +
                    "\t" + F3(vo[0]) + "\t" + F3(vo[1]) + "\t" + F3(vo[2]) + "\t" + F6(disp) +
                    "\t" + F6(dx) + "\t" + F6(dy) + "\t" + F6(dz) + "\t" + bname[domBone] + "\t" + fam + "\t" + nz);
            }
        }
        File.WriteAllLines(Path.Combine(outDir, "verts_rest_skin.tsv"), vrows.ToArray(), new UTF8Encoding(false));

        float[] dispArr = dispList.ToArray();
        Log("STEP3 verts=" + totalVerts + " max_nonzero_slots=" + slotMax);
        Log("STEP3 orig_bbox_min=[" + F3(vmin[0]) + "," + F3(vmin[1]) + "," + F3(vmin[2]) + "] max=[" + F3(vmax[0]) + "," + F3(vmax[1]) + "," + F3(vmax[2]) + "]");
        Log("STEP3 new_bbox_min=[" + F3(nmin[0]) + "," + F3(nmin[1]) + "," + F3(nmin[2]) + "] max=[" + F3(nmax[0]) + "," + F3(nmax[1]) + "," + F3(nmax[2]) + "]");
        for (int k = 0; k < 3; k++)
        {
            float os = vmax[k] - vmin[k];
            float ns = nmax[k] - nmin[k];
            Log("STEP3 span_" + "XYZ"[k] + " orig=" + F3(os) + " new=" + F3(ns) + " ratio=" + (os == 0f ? 0f : ns / os).ToString("F6", CI));
        }
        Log("STEP3 disp median=" + F6(Median(dispArr)) + " mean=" + F6(Mean(dispArr)) +
            " max=" + F6(MaxOf(dispArr)));
        Log("STEP3 axis_abs_mean dx=" + F6((float)(dxAcc / totalVerts)) + " dy=" + F6((float)(dyAcc / totalVerts)) + " dz=" + F6((float)(dzAcc / totalVerts)));
        int[] band = new int[6];
        for (int i = 0; i < dispArr.Length; i++)
        {
            float d = dispArr[i];
            if (d < 0.001f) band[0]++;
            else if (d < 0.01f) band[1]++;
            else if (d < 0.1f) band[2]++;
            else if (d < 1f) band[3]++;
            else if (d < 10f) band[4]++;
            else band[5]++;
        }
        Log("STEP3 disp_bands [0,0.001)=" + band[0] + " [0.001,0.01)=" + band[1] + " [0.01,0.1)=" + band[2] +
            " [0.1,1)=" + band[3] + " [1,10)=" + band[4] + " >=10=" + band[5]);

        for (int f = 0; f < famNames.Length; f++)
        {
            float mean = famCount[f] == 0 ? 0f : (float)(famSumDisp[f] / famCount[f]);
            Log("STEP3 FAMILY " + famNames[f] + " verts=" + famCount[f] + " mean_disp=" + F6(mean) + " max_disp=" + F6(famMaxDisp[f]));
        }

        float[] abMin = new float[] { float.MaxValue, float.MaxValue, float.MaxValue };
        float[] abMax = new float[] { float.MinValue, float.MinValue, float.MinValue };
        float[] pbMin = new float[] { float.MaxValue, float.MaxValue, float.MaxValue };
        float[] pbMax = new float[] { float.MinValue, float.MinValue, float.MinValue };
        int palBones = 0;
        for (int i = 0; i < nb; i++)
        {
            for (int k = 0; k < 3; k++)
            {
                float v = restWorld[i][12 + k];
                if (v < abMin[k]) abMin[k] = v;
                if (v > abMax[k]) abMax[k] = v;
                if (!inPalette[i]) continue;
                if (v < pbMin[k]) pbMin[k] = v;
                if (v > pbMax[k]) pbMax[k] = v;
            }
            if (inPalette[i]) palBones++;
        }
        Log("REST_BONE_BBOX ALL bones=" + nb + " min=[" + F3(abMin[0]) + "," + F3(abMin[1]) + "," + F3(abMin[2]) +
            "] max=[" + F3(abMax[0]) + "," + F3(abMax[1]) + "," + F3(abMax[2]) + "] span=[" +
            F3(abMax[0] - abMin[0]) + "," + F3(abMax[1] - abMin[1]) + "," + F3(abMax[2] - abMin[2]) + "]");
        Log("REST_BONE_BBOX PALETTE bones=" + palBones + " min=[" + F3(pbMin[0]) + "," + F3(pbMin[1]) + "," + F3(pbMin[2]) +
            "] max=[" + F3(pbMax[0]) + "," + F3(pbMax[1]) + "," + F3(pbMax[2]) + "] span=[" +
            F3(pbMax[0] - pbMin[0]) + "," + F3(pbMax[1] - pbMin[1]) + "," + F3(pbMax[2] - pbMin[2]) + "]");

        int[] order = new int[nb];
        for (int i = 0; i < nb; i++) order[i] = i;
        Array.Sort(order, delegate (int a, int b) { return boneMass[b].CompareTo(boneMass[a]); });
        List<string> topRows = new List<string>();
        topRows.Add("rank\tbone\tfamily\tparent\tdom_count\tmass_disp\tmax_disp\tdt_cm\tdang_deg");
        Log("### TOP10_BONES");
        for (int r = 0; r < 10; r++)
        {
            int i = order[r];
            Log("TOP " + (r + 1) + " " + bname[i] + " " + Family(bname[i]) + " dom=" + boneDomCount[i] +
                " mass=" + F3((float)boneMass[i]) + " max=" + F3(boneMaxDisp[i]) +
                " dt=" + F6(dt[i]) + " dang=" + F6(dang[i]));
            topRows.Add((r + 1) + "\t" + bname[i] + "\t" + Family(bname[i]) + "\t" + parent[i] + "\t" +
                boneDomCount[i] + "\t" + F6((float)boneMass[i]) + "\t" + F6(boneMaxDisp[i]) +
                "\t" + F6(dt[i]) + "\t" + F6(dang[i]));
        }
        File.WriteAllLines(Path.Combine(outDir, "top_bones.tsv"), topRows.ToArray(), new UTF8Encoding(false));

        Log("STAGE1_DONE");
        File.WriteAllText(Path.Combine(outDir, "summary.txt"), slog.ToString(), new UTF8Encoding(false));
        Console.WriteLine("REST_VS_BIND_DONE");
    }

    static int MaxOf(int[] a)
    {
        int m = int.MinValue;
        for (int i = 0; i < a.Length; i++) if (a[i] > m) m = a[i];
        return m;
    }

    static float MaxOf(float[] a)
    {
        float m = float.MinValue;
        for (int i = 0; i < a.Length; i++) if (a[i] > m) m = a[i];
        return m;
    }
}
