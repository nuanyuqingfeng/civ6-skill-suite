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

// bind 感知的顶点位移校验：读出每骨 InverseBind/父级、网格 palette、顶点权重与索引，
// 计算 bind 姿态与动画 t=0 姿态下的顶点位移，输出 top-20 与逐骨归因
class NexusDumpBind
{
    static GrannyContext ctx;
    static readonly CultureInfo CI = CultureInfo.InvariantCulture;
    static StringBuilder slog = new StringBuilder();

    static void Log(string s)
    {
        Console.WriteLine(s);
        slog.AppendLine(s);
    }

    static string F(float v) { return v.ToString("F4", CI); }
    static string F3(float v) { return v.ToString("F3", CI); }
    static string F2(float v) { return v.ToString("F2", CI); }
    static string F6(float v) { return v.ToString("F6", CI); }

    static string JoinInt(int[] a)
    {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < a.Length; i++)
        {
            if (i > 0) sb.Append(',');
            sb.Append(a[i]);
        }
        return sb.ToString();
    }

    // ============ 原生内存读取（x64，经 VirtualQuery 判定可读） ============
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

    static int RawI32(IntPtr p, int off)
    {
        IntPtr ap = IntPtr.Add(p, off);
        if (!Readable(ap, 4)) throw new InvalidOperationException("不可读地址 0x" + ap.ToInt64().ToString("X") + " (基址 +" + off + ")");
        return Marshal.ReadInt32(ap);
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

    static IntPtr BoneNative(IGrannyBone bone)
    {
        FieldInfo fi = bone.GetType().GetField("m_pkBone", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance);
        if (fi == null) throw new InvalidOperationException("类型 " + bone.GetType().FullName + " 缺少字段 m_pkBone");
        object v = fi.GetValue(bone);
        if (v is IntPtr) return (IntPtr)v;
        unsafe { return (IntPtr)Pointer.Unbox(v); }
    }

    // 骨内 LocalTransform：+12 Flags、+16 Position、+28 Orientation、+44 ScaleShear、+80 InverseWorld
    // IGrannyTransform.ScaleShear 从 +28 起读（早四个浮点），这里按 +44 直读原生内存
    static float[] BoneScaleShear(IGrannyBone bone)
    {
        IntPtr p = BoneNative(bone);
        float[] pos = bone.LocalTransform.Position;
        float[] iw = bone.InverseWorldTransform;
        for (int k = 0; k < 3; k++)
            if (Math.Abs(RawF32(p, 16 + k * 4) - pos[k]) > 1e-6f)
                throw new InvalidOperationException("骨 " + bone.Name + " 的 +16 三个浮点不是 Position");
        for (int k = 0; k < 4; k++)
            if (Math.Abs(RawF32(p, 80 + k * 4) - iw[k]) > 1e-6f)
                throw new InvalidOperationException("骨 " + bone.Name + " 的 +80 不是 InverseWorldTransform");
        float[] ss = new float[9];
        for (int k = 0; k < 9; k++) ss[k] = RawF32(p, 44 + k * 4);
        return ss;
    }

    // ============ 矩阵（行向量约定：v_out = v · M） ============
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

    static float[] QuatMat(float[] q, int order)
    {
        float x, y, z, w;
        if (order == 0) { x = q[0]; y = q[1]; z = q[2]; w = q[3]; }
        else { w = q[0]; x = q[1]; y = q[2]; z = q[3]; }
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

    static float[] LocalMat(float[] pos, float[] q, float[] ss, int order, int scaleMode)
    {
        float[] r = QuatMat(q, order);
        float[] m = MatId();
        if (scaleMode == 0 || ss == null)
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

    static float MatIdDev(float[] m)
    {
        float[] id = MatId();
        float d = 0f;
        for (int i = 0; i < 16; i++) d = Math.Max(d, Math.Abs(m[i] - id[i]));
        return d;
    }

    static float RotAngleDeg(float[] a, float[] b)
    {
        float tr = 0f;
        for (int i = 0; i < 3; i++)
            for (int k = 0; k < 3; k++)
                tr += a[k * 4 + i] * b[k * 4 + i];
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

    // ============ 顶点成员定义 ============
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
            case 10: return 4;  // 32bit float
            case 11: return 1;  // int8
            case 12: return 1;  // uint8
            case 13: return 2;  // int16
            case 14: return 1;  // uint8
            case 15: return 2;  // uint16
            case 16: return 4;  // int32
            case 17: return 4;  // uint32
            case 21: return 2;  // 16bit float
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

    // ============ 网格原生布局定位 ============
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

    static MeshLayout LocateMeshLayout(IGrannyMesh[] meshes)
    {
        MeshLayout lay = new MeshLayout();
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
        foreach (IGrannyMesh m in meshes)
        {
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
                                    need++;
                                    goto nextMesh;
                                }
                    }
                }
            }
            throw new InvalidOperationException("网格 " + m.Name + " 无法定位 PrimaryVertexData（顶点数 " + m.VertexCount + "）");
        nextMesh: ;
        }
        if (need != meshes.Length) throw new InvalidOperationException("布局候选对 " + meshes.Length + " 个网格不一致");
        return lay;
    }

    static void Main(string[] args)
    {
        if (args.Length < 3)
        {
            Console.WriteLine("usage: NexusDumpBind <model.fgx> <anim.fgx> <outDir>");
            Environment.Exit(2);
        }
        string modelPath = args[0];
        string animPath = args[1];
        string outDir = args[2];
        Directory.CreateDirectory(outDir);

        Application.EnableVisualStyles();
        Form form = new CivNexusSixApplicationForm();
        ctx = Context.Get<GrannyContext>();

        Log("### 输入");
        Log("model=" + modelPath);
        Log("anim=" + animPath);
        Log("pointer_size=" + IntPtr.Size);

        IGrannyFile mf = ctx.LoadGrannyFile(modelPath);
        IGrannyModel model = mf.Models[0];
        IGrannySkeleton sk = model.Skeleton;
        IList<IGrannyBone> bones = sk.Bones;
        int nb = bones.Count;
        Log("model_name=" + model.Name + " skeleton=" + sk.Name + " bones=" + nb +
            " meshes=" + model.MeshBindings.Count + " file_meshes=" + mf.Meshes.Count);

        IGrannyFile af = ctx.LoadGrannyFile(animPath);
        IGrannyAnimation anim = af.Animations[0];
        Log("anim_name=" + anim.Name + " duration=" + F3(anim.Duration) + " groups=" + anim.TrackGroups.Count);
        Log("MODELFILE models=" + mf.Models.Count + " meshes=" + mf.Meshes.Count);
        Log("MODEL_PLACEMENT p=[" + F3(model.InitialPlacement.Position[0]) + "," + F3(model.InitialPlacement.Position[1]) + "," + F3(model.InitialPlacement.Position[2]) + "]" +
            " q=[" + F(model.InitialPlacement.Orientation[0]) + "," + F(model.InitialPlacement.Orientation[1]) + "," +
            F(model.InitialPlacement.Orientation[2]) + "," + F(model.InitialPlacement.Orientation[3]) + "]");
        Log("ANIMFILE models=" + af.Models.Count + " meshes=" + af.Meshes.Count);
        foreach (IGrannyModel am in af.Models)
            Log("ANIMFILE_MODEL name=" + am.Name + " skeleton=" + am.Skeleton.Name + " bones=" + am.Skeleton.Bones.Count +
                " bindings=" + am.MeshBindings.Count +
                " place_p=[" + F3(am.InitialPlacement.Position[0]) + "," + F3(am.InitialPlacement.Position[1]) + "," + F3(am.InitialPlacement.Position[2]) + "]" +
                " place_q=[" + F(am.InitialPlacement.Orientation[0]) + "," + F(am.InitialPlacement.Orientation[1]) + "," +
                F(am.InitialPlacement.Orientation[2]) + "," + F(am.InitialPlacement.Orientation[3]) + "]");
        foreach (IGrannyTrackGroup g in anim.TrackGroups)
            Log("  trackgroup=" + g.Name + " tracks=" + g.TransformTracks.Count);
        IGrannyTrackGroup tg = null;
        if (anim.TrackGroups.Count > 0)
        {
            tg = anim.TrackGroups[0];
            for (int i = 0; i < anim.TrackGroups.Count; i++)
            {
                IGrannyTrackGroup g = anim.TrackGroups[i];
                if (g.Name == sk.Name && g.TransformTracks.Count == nb) { tg = g; break; }
            }
            Log("使用轨道组=" + tg.Name + " tracks=" + tg.TransformTracks.Count);
        }
        else
        {
            Log("动画无轨道组：t=0 姿态按 rest 处理（该情形引擎侧不驱动模型）");
        }

        // 逐骨 rest（bind 局部）与 InverseBind
        float[][] restPos = new float[nb][];
        float[][] restQ = new float[nb][];
        float[][] restSS = new float[nb][];
        float[][] invBind = new float[nb][];
        int[] parent = new int[nb];
        string[] boneName = new string[nb];
        for (int i = 0; i < nb; i++)
        {
            IGrannyBone b = bones[i];
            boneName[i] = b.Name;
            parent[i] = b.ParentIndex;
            restPos[i] = b.LocalTransform.Position;
            restQ[i] = b.LocalTransform.Orientation;
            restSS[i] = BoneScaleShear(b);
            invBind[i] = b.InverseWorldTransform;
            if (restPos[i] == null || restQ[i] == null) throw new InvalidOperationException("骨 " + b.Name + " rest 变换缺通道");
            if (invBind[i] == null || invBind[i].Length != 16) throw new InvalidOperationException("骨 " + b.Name + " InverseWorldTransform 维度异常");
            if (parent[i] >= i) throw new InvalidOperationException("骨 " + b.Name + " 父索引 " + parent[i] + " 不小于自身索引 " + i);
        }
        Log("骨 InverseBind 与父索引读取成功: " + nb + " 根（父索引最大值 " + MaxOf(parent) + "）");
        float ss0dev = 0f;
        for (int k = 0; k < 9; k++)
        {
            float unit = (k % 4 == 0) ? 1f : 0f;
            ss0dev = Math.Max(ss0dev, Math.Abs(restSS[0][k] - unit));
        }
        Log("BONE0_SS name=" + boneName[0] +
            " ss=[" + F(restSS[0][0]) + "," + F(restSS[0][1]) + "," + F(restSS[0][2]) +
            "," + F(restSS[0][3]) + "," + F(restSS[0][4]) + "," + F(restSS[0][5]) +
            "," + F(restSS[0][6]) + "," + F(restSS[0][7]) + "," + F(restSS[0][8]) + "]" +
            " max_dev_vs_identity=" + F(ss0dev));

        IntPtr[] meshPtr = new IntPtr[model.MeshBindings.Count];
        for (int mi = 0; mi < model.MeshBindings.Count; mi++) meshPtr[mi] = MeshNative(model.MeshBindings[mi]);
        MeshLayout lay = LocateMeshLayout(model.MeshBindings.ToArray());
        Log("网格原生布局: Name@" + lay.NameOff + " PrimaryVertexData@" + lay.VtxOff +
            " VertexCount@" + lay.VtxCountOff + " VerticesArray@" + lay.VtxArrayOff +
            " TypeDefStride=" + lay.TypeDefStride + " TypeDefName@" + lay.TypeDefNameOff +
            " TypeDefWidth@" + lay.TypeDefWidthOff);

        // 骨名 → 骨架索引
        Dictionary<string, int> boneIndex = new Dictionary<string, int>();
        for (int i = 0; i < nb; i++)
        {
            if (boneIndex.ContainsKey(boneName[i]))
                throw new InvalidOperationException("骨架存在重名骨 " + boneName[i] + "，按名映射不成立");
            boneIndex[boneName[i]] = i;
        }

        // 姿态局部：t=0 采样，缺通道取 rest
        float[][] posePos = new float[nb][];
        float[][] poseQ = new float[nb][];
        float[][] poseSS = new float[nb][];
        Dictionary<string, IGrannyTransformTrack> trackByName = new Dictionary<string, IGrannyTransformTrack>();
        if (tg != null)
        {
            foreach (IGrannyTransformTrack t in tg.TransformTracks)
            {
                if (trackByName.ContainsKey(t.Name))
                    throw new InvalidOperationException("轨道组存在重名轨道 " + t.Name);
                trackByName[t.Name] = t;
            }
        }
        int matched = 0;
        for (int i = 0; i < nb; i++)
        {
            IGrannyTransformTrack t;
            if (!trackByName.TryGetValue(boneName[i], out t))
            {
                posePos[i] = restPos[i];
                poseQ[i] = restQ[i];
                poseSS[i] = restSS[i];
                continue;
            }
            matched++;
            posePos[i] = t.PositionCurve != null ? t.PositionCurve.Sample(0f, anim.Duration, false, false, false) : restPos[i];
            poseQ[i] = t.OrientationCurve != null ? t.OrientationCurve.Sample(0f, anim.Duration, false, false, false) : restQ[i];
            poseSS[i] = t.ScaleShearCurve != null ? t.ScaleShearCurve.Sample(0f, anim.Duration, false, false, false) : restSS[i];
        }
        Log("轨道↔骨匹配: " + matched + "/" + nb + "（未匹配者取 rest）");

        // 标定：InverseBind 的旋转部分（按 3x3 行列式归一化去掉缩放）应与 rest 链世界旋转互逆
        int bestCompose = -1, bestOrder = -1, bestMode = -1;
        float bestRot = float.MaxValue;
        for (int compose = 0; compose < 2; compose++)
            for (int order = 0; order < 2; order++)
                for (int mode = 0; mode < 3; mode++)
                {
                    float[][] bw;
                    BuildWorld(restPos, restQ, restSS, parent, nb, order, mode, compose, out bw);
                    float err = 0f;
                    for (int i = 0; i < nb; i++)
                    {
                        float[] invRot = InvRotOnly(invBind[i], boneName[i]);
                        float ang = RotAngleDeg(Rot3(bw[i], boneName[i]), invRot);
                        if (ang > err) err = ang;
                    }
                    Log("旋转标定 compose=" + compose + " order=" + order + " scaleMode=" + mode +
                        " 最大夹角=" + err.ToString("F3", CI));
                    if (err < bestRot) { bestRot = err; bestCompose = compose; bestOrder = order; bestMode = mode; }
                }
        Log("旋转标定选定 compose=" + bestCompose + " order=" + bestOrder + " scaleMode=" + bestMode +
            " 最大夹角=" + bestRot.ToString("F4", CI));

        float[][] invUse = invBind;

        float[][] bindWorld;
        BuildWorld(restPos, restQ, restSS, parent, nb, bestOrder, bestMode, bestCompose, out bindWorld);
        float[][] poseWorld;
        BuildWorld(posePos, poseQ, poseSS, parent, nb, bestOrder, bestMode, bestCompose, out poseWorld);
        float[][] poseWorldS;
        BuildWorld(posePos, poseQ, poseSS, parent, nb, bestOrder, 1, bestCompose, out poseWorldS);
        float[] poseBoxMin, poseBoxMax, poseBoxCtr;
        BoneBox(poseWorldS, nb, out poseBoxMin, out poseBoxMax, out poseBoxCtr);
        Log("骨架 t=0 姿态世界位置包围盒 min=[" + F3(poseBoxMin[0]) + "," + F3(poseBoxMin[1]) + "," + F3(poseBoxMin[2]) +
            "] max=[" + F3(poseBoxMax[0]) + "," + F3(poseBoxMax[1]) + "," + F3(poseBoxMax[2]) +
            "] span=[" + F3(poseBoxMax[0] - poseBoxMin[0]) + "," + F3(poseBoxMax[1] - poseBoxMin[1]) + "," + F3(poseBoxMax[2] - poseBoxMin[2]) + "]");

        // 判据 B：t=0 姿态世界旋转与模型 rest 世界旋转逐骨对照
        string[] CORE_CHAIN = new string[] { "Root", "Bip001", "Bip001Pelvis", "Bip001Spine", "Bip001Head" };
        List<string> poseRows = new List<string>();
        poseRows.Add("bone\tparent\tdAng_deg");
        float poseMax = 0f; string poseMaxBone = "-"; float poseSum = 0f;
        int poseOver45 = 0, poseOver15 = 0, poseUnder5 = 0;
        for (int i = 0; i < nb; i++)
        {
            float a = RotAngleDeg(bindWorld[i], poseWorld[i]);
            poseRows.Add(boneName[i] + "\t" + parent[i] + "\t" + F(a));
            poseSum += a;
            if (a > poseMax) { poseMax = a; poseMaxBone = boneName[i]; }
            if (a > 45f) poseOver45++;
            if (a > 15f) poseOver15++;
            if (a < 5f) poseUnder5++;
        }
        Log("POSE_CRITERIA bones=" + nb + " matched=" + matched + " max=" + F(poseMax) + " bone=" + poseMaxBone +
            " mean=" + F(poseSum / nb) + " over45=" + poseOver45 + " over15=" + poseOver15 + " under5=" + poseUnder5);
        Log("ROOTBONE0 name=" + boneName[0] + " angle=" + F(RotAngleDeg(bindWorld[0], poseWorld[0])));
        foreach (string cn in CORE_CHAIN)
        {
            int ci = Array.IndexOf(boneName, cn);
            Log("  CORE " + cn + " " + (ci < 0 ? "MISSING" : F(RotAngleDeg(bindWorld[ci], poseWorld[ci])) + "deg"));
        }
        Log("ROOT_WORLD name=" + boneName[0] + " rot16=" + MatLine(bindWorld[0]) +
            " local_pos=[" + F3(restPos[0][0]) + "," + F3(restPos[0][1]) + "," + F3(restPos[0][2]) + "]" +
            " local_q=[" + F(restQ[0][0]) + "," + F(restQ[0][1]) + "," + F(restQ[0][2]) + "," + F(restQ[0][3]) + "]");
        List<string> restRows = new List<string>();
        restRows.Add("bone\tparent\tpx\tpy\tpz\tqx\tqy\tqz\tqw\tw00\tw01\tw02\tw10\tw11\tw12\tw20\tw21\tw22");
        for (int i = 0; i < nb; i++)
        {
            StringBuilder wr = new StringBuilder();
            for (int r = 0; r < 3; r++)
                for (int c = 0; c < 3; c++)
                    wr.Append("\t").Append(F6(bindWorld[i][c * 4 + r]));
            restRows.Add(boneName[i] + "\t" + parent[i] + "\t" +
                F3(restPos[i][0]) + "\t" + F3(restPos[i][1]) + "\t" + F3(restPos[i][2]) + "\t" +
                F(restQ[i][0]) + "\t" + F(restQ[i][1]) + "\t" + F(restQ[i][2]) + "\t" + F(restQ[i][3]) + wr.ToString());
        }

        // 蒙皮取带 ScaleShear 的姿态世界矩阵：引擎按通道 3x3 缩放构造局部矩阵
        float[][] skin = new float[nb][];
        for (int i = 0; i < nb; i++) skin[i] = MatMul(invUse[i], poseWorldS[i]);

        // rest 姿态蒙皮：v_world = v_bind · InverseBind · restWorld，两套 scaleMode 口径并出
        float[][] restWorldZero;
        BuildWorld(restPos, restQ, restSS, parent, nb, bestOrder, 0, bestCompose, out restWorldZero);

        // 判据：InvBind 3x3 与 restWorld 旋转部分互逆的夹角（逐骨取最大，行列式归一化去除缩放）
        for (int variant = 0; variant < 2; variant++)
        {
            float[][] worldInv = variant == 0 ? bindWorld : restWorldZero;
            float worst = 0f; float sumAng = 0f; string worstName = "-";
            for (int i = 0; i < nb; i++)
            {
                float ang = RotAngleDeg(Rot3(worldInv[i], boneName[i]), InvRotOnly(invBind[i], boneName[i]));
                sumAng += ang;
                if (ang > worst) { worst = ang; worstName = boneName[i]; }
            }
            Log("INVBIND_ANGLE 口径=" + (variant == 0 ? "A(compose=" + bestCompose + " order=" + bestOrder + " scaleMode=" + bestMode + ")" : "B(scaleMode=0)") +
                " bones=" + nb + " max=" + worst.ToString("F4", CI) + " bone=" + worstName +
                " mean=" + (sumAng / nb).ToString("F4", CI));
        }
        float[][] skinRestSel = new float[nb][];
        float[][] skinRestZero = new float[nb][];
        for (int i = 0; i < nb; i++)
        {
            skinRestSel[i] = MatMul(invUse[i], bindWorld[i]);
            skinRestZero[i] = MatMul(invUse[i], restWorldZero[i]);
        }
        float[] restBoxSelMin, restBoxSelMax, restBoxSelCtr;
        float[] restBoxZeroMin, restBoxZeroMax, restBoxZeroCtr;
        BoneBox(bindWorld, nb, out restBoxSelMin, out restBoxSelMax, out restBoxSelCtr);
        BoneBox(restWorldZero, nb, out restBoxZeroMin, out restBoxZeroMax, out restBoxZeroCtr);
        Log("骨架 rest 世界位置包围盒口径 A（标定 scaleMode=" + bestMode + "） min=[" + F3(restBoxSelMin[0]) + "," + F3(restBoxSelMin[1]) + "," + F3(restBoxSelMin[2]) +
            "] max=[" + F3(restBoxSelMax[0]) + "," + F3(restBoxSelMax[1]) + "," + F3(restBoxSelMax[2]) + "]");
        Log("骨架 rest 世界位置包围盒口径 B（scaleMode=0） min=[" + F3(restBoxZeroMin[0]) + "," + F3(restBoxZeroMin[1]) + "," + F3(restBoxZeroMin[2]) +
            "] max=[" + F3(restBoxZeroMax[0]) + "," + F3(restBoxZeroMax[1]) + "," + F3(restBoxZeroMax[2]) + "]");
        float[] vRestSelMin = new float[] { float.MaxValue, float.MaxValue, float.MaxValue };
        float[] vRestSelMax = new float[] { float.MinValue, float.MinValue, float.MinValue };
        float[] vRestZeroMin = new float[] { float.MaxValue, float.MaxValue, float.MaxValue };
        float[] vRestZeroMax = new float[] { float.MinValue, float.MinValue, float.MinValue };

        int[] depth = new int[nb];
        for (int i = 0; i < nb; i++) depth[i] = parent[i] < 0 ? 0 : depth[parent[i]] + 1;

        // InverseBind 的缩放因子与隐含 bind 位置：判定骨架 rest 空间与蒙皮 bind 空间是否一致
        float sMin = float.MaxValue, sMax = float.MinValue;
        float[] sBone = new float[nb];
        float[] impliedLen = new float[nb];
        float[] restLen = new float[nb];
        for (int i = 0; i < nb; i++)
        {
            float s = InvScale(invBind[i], boneName[i]);
            sBone[i] = s;
            if (s < sMin) sMin = s;
            if (s > sMax) sMax = s;
            float[] p = ImpliedBindPos(invBind[i], boneName[i]);
            impliedLen[i] = (float)Math.Sqrt(Sq(p[0]) + Sq(p[1]) + Sq(p[2]));
            restLen[i] = (float)Math.Sqrt(Sq(bindWorld[i][12]) + Sq(bindWorld[i][13]) + Sq(bindWorld[i][14]));
        }
        Log("InverseBind 3x3 缩放因子: min=" + sMin.ToString("E6", CI) + " max=" + sMax.ToString("E6", CI));

        // 检验 InverseBind 的旋转部分是否符合 stored = G · rest 或 stored = G · rest⁻¹（G=R_x(±90)）
        for (int sign = -1; sign <= 1; sign += 2)
        {
            float[] g = RotX90(sign);
            float devFwd = 0f, devInv = 0f;
            for (int i = 0; i < nb; i++)
            {
                float[] stored = Rot3(invBind[i], boneName[i]);
                float[] rest = Rot3(bindWorld[i], boneName[i]);
                devFwd = Math.Max(devFwd, MaxDev3(MatMul(g, rest), stored));
                devInv = Math.Max(devInv, MaxDev3(MatMul(g, MatTr3(rest)), stored));
            }
            Log("旋转模型 G=R_x(" + (sign > 0 ? "+90" : "-90") + ")：stored=G·rest 最大偏差=" + devFwd.ToString("E6", CI) +
                "  stored=G·restInv 最大偏差=" + devInv.ToString("E6", CI));
        }
        float impMax = 0f, restMax = 0f;
        for (int i = 0; i < nb; i++)
        {
            if (impliedLen[i] > impMax) impMax = impliedLen[i];
            if (restLen[i] > restMax) restMax = restLen[i];
        }
        Log("隐含 bind 位置最大模长=" + F3(impMax) + "  rest 位置最大模长=" + F3(restMax) +
            "  比值=" + (impMax / restMax).ToString("F3", CI));
        for (int i = 0; i < 3; i++)
        {
            Log("  原始 invBind[" + i + "] " + boneName[i] + " = " + MatLine(invBind[i]));
            Log("  原始 restWorld[" + i + "] = " + MatLine(bindWorld[i]));
        }
        for (int i = 0; i < Math.Min(10, nb); i++)
            Log("  骨[" + i + "] " + boneName[i] + " depth=" + depth[i] +
                " rest_p=(" + F3(restPos[i][0]) + "," + F3(restPos[i][1]) + "," + F3(restPos[i][2]) + ")" +
                " invBind_t=(" + F3(invBind[i][12]) + "," + F3(invBind[i][13]) + "," + F3(invBind[i][14]) + ")" +
                " scale=" + sBone[i].ToString("F5", CI) +
                " 隐含bind模长=" + F3(impliedLen[i]) + " rest模长=" + F3(restLen[i]));
        Log("骨架 rest 包围盒中心口径 A=[" + F3(restBoxSelCtr[0]) + "," + F3(restBoxSelCtr[1]) + "," + F3(restBoxSelCtr[2]) + "] 口径 B=[" + F3(restBoxZeroCtr[0]) + "," + F3(restBoxZeroCtr[1]) + "," + F3(restBoxZeroCtr[2]) + "]");

        // ============ 顶点位移 ============
        List<string> vtxRows = new List<string>();
        vtxRows.Add("mesh\tvidx\tbind_x\tbind_y\tbind_z\tout_x\tout_y\tout_z\tdisp\tdom_bone\tdom_w\tweights\tindices");
        List<double> boneMass = new List<double>();
        int[] boneDomCount = new int[nb];
        float[] boneMaxDisp = new float[nb];
        double[] boneWeightSum = new double[nb];
        for (int i = 0; i < nb; i++) { boneMass.Add(0.0); boneMaxDisp[i] = 0f; }
        double totalWeightAll = 0.0;

        int totalVerts = 0;
        float globalMaxDisp = 0f;
        int over100 = 0, over1000 = 0, over10000 = 0;
        int[] coordBand = new int[5];
        int[] dispBand = new int[6];
        bool[] inPalette = new bool[nb];
        Dictionary<int, int> bigDispByBone = new Dictionary<int, int>();
        float[] bboxMin = new float[] { float.MaxValue, float.MaxValue, float.MaxValue };
        float[] bboxMax = new float[] { float.MinValue, float.MinValue, float.MinValue };
        float[] pvMin = new float[] { float.MaxValue, float.MaxValue, float.MaxValue };
        float[] pvMax = new float[] { float.MinValue, float.MinValue, float.MinValue };

        // 逐顶点记录用于排序
        List<VtxRec> recs = new List<VtxRec>();

        for (int mi = 0; mi < model.MeshBindings.Count; mi++)
        {
            IGrannyMesh mesh = model.MeshBindings[mi];
            IntPtr vtx = RawPtr(meshPtr[mi], lay.VtxOff);
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
            StringBuilder layoutLine = new StringBuilder();
            foreach (VtxMember m in members) layoutLine.Append(m.MName).Append("[t").Append(m.Code).Append(" x").Append(m.ArrayWidth).Append(" @").Append(m.Offset).Append("] ");
            Log("网格 " + mesh.Name + " verts=" + mesh.VertexCount + " stride=" + stride + " palette=" + mesh.BoneBindings.Count);
            Log("  成员 " + layoutLine.ToString().TrimEnd());
            if (mPos == null || mW == null || mI == null)
                throw new InvalidOperationException("网格 " + mesh.Name + " 缺少 Position/BoneWeights/BoneIndices 成员");
            int nw = mW.ArrayWidth;
            if (nw != mI.ArrayWidth || nw < 1 || nw > 8)
                throw new InvalidOperationException("网格 " + mesh.Name + " 权重/索引宽度异常（" + mW.ArrayWidth + "/" + mI.ArrayWidth + "）");
            Log("  权重槽位数=" + nw);

            int[] palette = new int[mesh.BoneBindings.Count];
            for (int k = 0; k < palette.Length; k++)
            {
                int bi;
                if (!boneIndex.TryGetValue(mesh.BoneBindings[k], out bi))
                    throw new InvalidOperationException("网格 " + mesh.Name + " palette 骨名 " + mesh.BoneBindings[k] + " 不在骨架中");
                palette[k] = bi;
                inPalette[bi] = true;
            }

            IntPtr arr = RawPtr(vtx, lay.VtxArrayOff);
            for (int vi = 0; vi < mesh.VertexCount; vi++)
            {
                IntPtr p = IntPtr.Add(arr, vi * stride);
                float[] vb = new float[3];
                vb[0] = RawF32(p, mPos.Offset);
                vb[1] = RawF32(p, mPos.Offset + 4);
                vb[2] = RawF32(p, mPos.Offset + 8);
                int[] w = new int[nw];
                int[] idx = new int[nw];
                int wsum = 0;
                for (int j = 0; j < nw; j++)
                {
                    w[j] = Marshal.ReadByte(p, mW.Offset + j);
                    idx[j] = Marshal.ReadByte(p, mI.Offset + j);
                    wsum += w[j];
                }
                if (wsum != 255) throw new InvalidOperationException("顶点 " + mesh.Name + "#" + vi + " 权重合计 " + wsum + " 非 255");
                for (int j = 0; j < nw; j++)
                    if (idx[j] >= palette.Length)
                        throw new InvalidOperationException("顶点 " + mesh.Name + "#" + vi + " 骨索引 " + idx[j] + " 超出 palette 长度 " + palette.Length);
                float[] vo = new float[] { 0f, 0f, 0f };
                float[] vrSel = new float[] { 0f, 0f, 0f };
                float[] vrZero = new float[] { 0f, 0f, 0f };
                float acc = 0f;
                for (int j = 0; j < nw; j++)
                {
                    if (w[j] == 0) continue;
                    float fw = w[j] / 255f;
                    acc += fw;
                    float[] t = TransformPoint(skin[palette[idx[j]]], vb);
                    vo[0] += fw * t[0];
                    vo[1] += fw * t[1];
                    vo[2] += fw * t[2];
                    float[] ts = TransformPoint(skinRestSel[palette[idx[j]]], vb);
                    vrSel[0] += fw * ts[0];
                    vrSel[1] += fw * ts[1];
                    vrSel[2] += fw * ts[2];
                    float[] tz = TransformPoint(skinRestZero[palette[idx[j]]], vb);
                    vrZero[0] += fw * tz[0];
                    vrZero[1] += fw * tz[1];
                    vrZero[2] += fw * tz[2];
                }
                for (int k = 0; k < 3; k++)
                {
                    if (vrSel[k] < vRestSelMin[k]) vRestSelMin[k] = vrSel[k];
                    if (vrSel[k] > vRestSelMax[k]) vRestSelMax[k] = vrSel[k];
                    if (vrZero[k] < vRestZeroMin[k]) vRestZeroMin[k] = vrZero[k];
                    if (vrZero[k] > vRestZeroMax[k]) vRestZeroMax[k] = vrZero[k];
                    if (vo[k] < pvMin[k]) pvMin[k] = vo[k];
                    if (vo[k] > pvMax[k]) pvMax[k] = vo[k];
                }
                float[] dv = new float[] { vo[0] - vb[0], vo[1] - vb[1], vo[2] - vb[2] };
                float disp = (float)Math.Sqrt(dv[0] * dv[0] + dv[1] * dv[1] + dv[2] * dv[2]);

                int dom = -1; int domW = -1;
                for (int j = 0; j < nw; j++) if (w[j] > domW) { domW = w[j]; dom = j; }
                int domBone = palette[idx[dom]];

                totalWeightAll += acc;
                for (int j = 0; j < nw; j++)
                {
                    if (w[j] == 0) continue;
                    boneMass[palette[idx[j]]] += (w[j] / 255.0) * disp;
                }
                boneWeightSum[domBone] += domW / 255.0;
                boneDomCount[domBone]++;
                if (disp > boneMaxDisp[domBone]) boneMaxDisp[domBone] = disp;

                totalVerts++;
                if (disp > globalMaxDisp) globalMaxDisp = disp;
                if (disp > 100f) over100++;
                if (disp > 1000f) over1000++;
                if (disp > 10000f)
                {
                    over10000++;
                    int c;
                    bigDispByBone.TryGetValue(domBone, out c);
                    bigDispByBone[domBone] = c + 1;
                }
                float cmax = Math.Max(Math.Abs(vb[0]), Math.Max(Math.Abs(vb[1]), Math.Abs(vb[2])));
                if (cmax < 50f) coordBand[0]++;
                else if (cmax < 200f) coordBand[1]++;
                else if (cmax < 1000f) coordBand[2]++;
                else if (cmax < 5000f) coordBand[3]++;
                else coordBand[4]++;
                if (disp < 1f) dispBand[0]++;
                else if (disp < 10f) dispBand[1]++;
                else if (disp < 100f) dispBand[2]++;
                else if (disp < 1000f) dispBand[3]++;
                else if (disp < 10000f) dispBand[4]++;
                else dispBand[5]++;
                for (int k = 0; k < 3; k++)
                {
                    if (vb[k] < bboxMin[k]) bboxMin[k] = vb[k];
                    if (vb[k] > bboxMax[k]) bboxMax[k] = vb[k];
                }
                VtxRec rec = new VtxRec();
                rec.Mesh = mesh.Name;
                rec.Vi = vi;
                rec.Vb = vb;
                rec.Vo = vo;
                rec.Disp = disp;
                rec.DomBone = domBone;
                rec.DomW = domW;
                rec.W = w;
                rec.Idx = idx;
                rec.Palette = palette;
                recs.Add(rec);

                if (disp > 1000f || vi < 4)
                    vtxRows.Add(mesh.Name + "\t" + vi + "\t" + F3(vb[0]) + "\t" + F3(vb[1]) + "\t" + F3(vb[2]) +
                        "\t" + F3(vo[0]) + "\t" + F3(vo[1]) + "\t" + F3(vo[2]) + "\t" + F3(disp) +
                        "\t" + boneName[domBone] + "\t" + (domW / 255f).ToString("F3", CI) +
                        "\t" + JoinInt(w) + "\t" + JoinInt(idx));
            }
        }

        Log("顶点总数=" + totalVerts + " 最大位移=" + F3(globalMaxDisp) +
            " 位移>100=" + over100 + " >1000=" + over1000 + " >10000=" + over10000);
        Log("bind 包围盒 min=[" + F3(bboxMin[0]) + "," + F3(bboxMin[1]) + "," + F3(bboxMin[2]) +
            "] max=[" + F3(bboxMax[0]) + "," + F3(bboxMax[1]) + "," + F3(bboxMax[2]) + "]");
        Log("### 顶点空间判定（Pose 取 rest）");
        VSpaceReport("A-标定 scaleMode=" + bestMode, restBoxSelMin, restBoxSelMax, restBoxSelCtr, vRestSelMin, vRestSelMax, totalVerts);
        VSpaceReport("B-scaleMode=0", restBoxZeroMin, restBoxZeroMax, restBoxZeroCtr, vRestZeroMin, vRestZeroMax, totalVerts);
        Log("### 顶点空间判定（Pose 取 t=0 动画）");
        VSpaceReport("C-动画t=0", poseBoxMin, poseBoxMax, poseBoxCtr, pvMin, pvMax, totalVerts);

        // 仅参与蒙皮的骨：网格 palette 之外的骨（CameraPosition/WeaponProp 等辅助节点）不产生形变，
        // 它们进骨包围盒会污染身高与中心距，故再出一种只含 palette 骨的口径
        float[] palPoseMin = new float[] { float.MaxValue, float.MaxValue, float.MaxValue };
        float[] palPoseMax = new float[] { float.MinValue, float.MinValue, float.MinValue };
        float[] palRestMin = new float[] { float.MaxValue, float.MaxValue, float.MaxValue };
        float[] palRestMax = new float[] { float.MinValue, float.MinValue, float.MinValue };
        int palCount = 0;
        for (int i = 0; i < nb; i++)
        {
            if (!inPalette[i]) continue;
            palCount++;
            for (int k = 0; k < 3; k++)
            {
                float v = poseWorldS[i][12 + k];
                if (v < palPoseMin[k]) palPoseMin[k] = v;
                if (v > palPoseMax[k]) palPoseMax[k] = v;
                float r = bindWorld[i][12 + k];
                if (r < palRestMin[k]) palRestMin[k] = r;
                if (r > palRestMax[k]) palRestMax[k] = r;
            }
        }
        float[] palPoseCtr = new float[] {
            (palPoseMin[0] + palPoseMax[0]) * 0.5f,
            (palPoseMin[1] + palPoseMax[1]) * 0.5f,
            (palPoseMin[2] + palPoseMax[2]) * 0.5f };
        float[] palRestCtr = new float[] {
            (palRestMin[0] + palRestMax[0]) * 0.5f,
            (palRestMin[1] + palRestMax[1]) * 0.5f,
            (palRestMin[2] + palRestMax[2]) * 0.5f };
        Log("PALETTE 骨数=" + palCount + "/" + nb);
        VSpaceReport("D-动画t=0 仅参与者骨", palPoseMin, palPoseMax, palPoseCtr, pvMin, pvMax, totalVerts);
        VSpaceReport("E-rest 仅参与者骨", palRestMin, palRestMax, palRestCtr, vRestSelMin, vRestSelMax, totalVerts);
        Log("### 顶点包围盒各轴比（动画 t=0 ÷ 模型 rest）");
        for (int k = 0; k < 3; k++)
        {
            float restSpan = vRestSelMax[k] - vRestSelMin[k];
            float poseSpan = pvMax[k] - pvMin[k];
            Log("VTX_AXIS_RATIO axis=" + "XYZ"[k] +
                " rest=[" + F3(vRestSelMin[k]) + "," + F3(vRestSelMax[k]) + "] rest_span=" + F3(restSpan) +
                " pose=[" + F3(pvMin[k]) + "," + F3(pvMax[k]) + "] pose_span=" + F3(poseSpan) +
                " ratio=" + (poseSpan / restSpan).ToString("F5", CI) +
                " rest_ctr=" + F3((vRestSelMin[k] + vRestSelMax[k]) * 0.5f) +
                " pose_ctr=" + F3((pvMin[k] + pvMax[k]) * 0.5f));
        }
        Log("### 骨架世界位置包围盒各轴比（动画 t=0 ÷ 模型 rest）");
        for (int k = 0; k < 3; k++)
        {
            float restSpan = restBoxSelMax[k] - restBoxSelMin[k];
            float poseSpan = poseBoxMax[k] - poseBoxMin[k];
            Log("BONE_AXIS_RATIO axis=" + "XYZ"[k] +
                " rest_span=" + F3(restSpan) + " pose_span=" + F3(poseSpan) +
                " ratio=" + (poseSpan / restSpan).ToString("F5", CI) +
                " rest_ctr=" + F3((restBoxSelMin[k] + restBoxSelMax[k]) * 0.5f) +
                " pose_ctr=" + F3((poseBoxMin[k] + poseBoxMax[k]) * 0.5f));
        }
        Log("bind 坐标最大分量分布: <50=" + coordBand[0] + " [50,200)=" + coordBand[1] + " [200,1000)=" + coordBand[2] +
            " [1000,5000)=" + coordBand[3] + " >=5000=" + coordBand[4]);
        Log("位移分布: <1=" + dispBand[0] + " [1,10)=" + dispBand[1] + " [10,100)=" + dispBand[2] +
            " [100,1000)=" + dispBand[3] + " [1000,10000)=" + dispBand[4] + " >=10000=" + dispBand[5]);
        List<KeyValuePair<int, int>> bigList = new List<KeyValuePair<int, int>>(bigDispByBone);
        bigList.Sort(delegate (KeyValuePair<int, int> a, KeyValuePair<int, int> b) { return b.Value.CompareTo(a.Value); });
        for (int i = 0; i < Math.Min(8, bigList.Count); i++)
            Log("  位移>=10000 顶点的主导骨: " + boneName[bigList[i].Key] + " = " + bigList[i].Value);

        // ============ 逐骨差异与归因 ============
        double[] boneMassShare = new double[nb];
        for (int i = 0; i < nb; i++)
        {
            double tot = 0.0;
            foreach (double d in boneMass) tot += d;
            boneMassShare[i] = boneMass[i] / tot;
        }

        List<string> boneRows = new List<string>();
        boneRows.Add("bone\tparent\tmass\tshare\tdom_count\tweight_sum\tmax_disp_dom\tdAng_deg\tdPos\tskin_angle\tskin_trans\tpull");
        for (int i = 0; i < nb; i++)
        {
            float dAng = RotAngleDeg(bindWorld[i], poseWorld[i]);
            float dPos = (float)Math.Sqrt(Sq(poseWorld[i][12] - bindWorld[i][12]) + Sq(poseWorld[i][13] - bindWorld[i][13]) + Sq(poseWorld[i][14] - bindWorld[i][14]));
            float skinAng = RotAngleDeg(MatId(), skin[i]);
            float skinTrans = (float)Math.Sqrt(Sq(skin[i][12]) + Sq(skin[i][13]) + Sq(skin[i][14]));
            float[] bp = new float[] { bindWorld[i][12], bindWorld[i][13], bindWorld[i][14] };
            float[] moved = TransformPoint(skin[i], bp);
            float pull = (float)Math.Sqrt(Sq(moved[0] - bp[0]) + Sq(moved[1] - bp[1]) + Sq(moved[2] - bp[2]));
            boneRows.Add(boneName[i] + "\t" + parent[i] + "\t" + boneMass[i].ToString("F3", CI) + "\t" +
                (boneMassShare[i] * 100.0).ToString("F4", CI) + "\t" + boneDomCount[i] + "\t" +
                boneWeightSum[i].ToString("F3", CI) + "\t" + F3(boneMaxDisp[i]) + "\t" + F3(dAng) + "\t" +
                F3(dPos) + "\t" + F3(skinAng) + "\t" + F3(skinTrans) + "\t" + F3(pull));
        }

        // ============ top-20 ============
        recs.Sort(delegate (VtxRec a, VtxRec b) { return b.Disp.CompareTo(a.Disp); });
        List<string> topRows = new List<string>();
        topRows.Add("rank\tmesh\tvidx\tdisp\tdom_bone\tdom_w\tbind_pos\tout_pos\tbone_local\tdom_dAng\tdom_dPos\tdom_pull\tskin_angle\tskin_trans");
        int topN = Math.Min(20, recs.Count);
        Log("### top-20 位移顶点");
        Log("rank\tmesh\tvidx\tdisp\tdom_bone\tdom_w\tbind_pos\tout_pos\tbone_local\tdom_dAng\tdom_dPos\tpull\tskin_ang\tskin_trans");
        for (int r = 0; r < topN; r++)
        {
            VtxRec rec = recs[r];
            int db = rec.DomBone;
            float dAng = RotAngleDeg(bindWorld[db], poseWorld[db]);
            float dPos = (float)Math.Sqrt(Sq(poseWorld[db][12] - bindWorld[db][12]) + Sq(poseWorld[db][13] - bindWorld[db][13]) + Sq(poseWorld[db][14] - bindWorld[db][14]));
            float skinAng = RotAngleDeg(MatId(), skin[db]);
            float skinTrans = (float)Math.Sqrt(Sq(skin[db][12]) + Sq(skin[db][13]) + Sq(skin[db][14]));
            float[] bp = new float[] { bindWorld[db][12], bindWorld[db][13], bindWorld[db][14] };
            float[] moved = TransformPoint(skin[db], bp);
            float pull = (float)Math.Sqrt(Sq(moved[0] - bp[0]) + Sq(moved[1] - bp[1]) + Sq(moved[2] - bp[2]));
            string bindPos = "(" + F3(rec.Vb[0]) + "," + F3(rec.Vb[1]) + "," + F3(rec.Vb[2]) + ")";
            string outPos = "(" + F3(rec.Vo[0]) + "," + F3(rec.Vo[1]) + "," + F3(rec.Vo[2]) + ")";
            float[] loc = TransformPoint(invUse[db], rec.Vb);
            string localPos = "(" + F2(loc[0]) + "," + F2(loc[1]) + "," + F2(loc[2]) + ")";
            string line = (r + 1) + "\t" + rec.Mesh + "\t" + rec.Vi + "\t" + F3(rec.Disp) + "\t" +
                boneName[db] + "\t" + (rec.DomW / 255f).ToString("F3", CI) + "\t" + bindPos + "\t" + outPos +
                "\t" + localPos + "\t" + F3(dAng) + "\t" + F3(dPos) + "\t" + F3(pull) + "\t" + F3(skinAng) + "\t" + F3(skinTrans);
            Log(line);
            topRows.Add(line);
        }

        // ============ 五个离群骨判定 + 反事实 ============
        string[] outliers = new string[] { "WeaponProp06", "Bip001LHand", "Bip001LForearm", "Bip001_L_Elbow_F", "Bip001_L_Elbow_B" };
        Log("### 离群骨逐条");
        Log("bone\tmass\tshare_pct\tdom_count\tmax_disp_dom\tdAng_deg\tdPos\tpull\tcounterfact_max_disp\tcounterfact_over1000");
        List<string> outRows = new List<string>();
        outRows.Add("bone\tmass\tshare_pct\tdom_count\tmax_disp_dom\tdAng_deg\tdPos\tpull\tcf_max_disp\tcf_over1000\tcf_over100");
        foreach (string name in outliers)
        {
            int bi;
            if (!boneIndex.TryGetValue(name, out bi))
            {
                Log("bone=" + name + " 不在骨架中");
                outRows.Add(name + "\tNOT_IN_SKELETON");
                continue;
            }
            float dAng = RotAngleDeg(bindWorld[bi], poseWorld[bi]);
            float dPos = (float)Math.Sqrt(Sq(poseWorld[bi][12] - bindWorld[bi][12]) + Sq(poseWorld[bi][13] - bindWorld[bi][13]) + Sq(poseWorld[bi][14] - bindWorld[bi][14]));
            float[] bp = new float[] { bindWorld[bi][12], bindWorld[bi][13], bindWorld[bi][14] };
            float[] moved = TransformPoint(skin[bi], bp);
            float pull = (float)Math.Sqrt(Sq(moved[0] - bp[0]) + Sq(moved[1] - bp[1]) + Sq(moved[2] - bp[2]));

            float cfMax = 0f; int cfOver1000 = 0; int cfOver100 = 0;
            foreach (VtxRec rec in recs)
            {
                float[] vo = new float[] { 0f, 0f, 0f };
                for (int j = 0; j < rec.W.Length; j++)
                {
                    if (rec.W[j] == 0) continue;
                    int b = rec.Palette[rec.Idx[j]];
                    float fw = rec.W[j] / 255f;
                    if (b == bi)
                    {
                        vo[0] += fw * rec.Vb[0];
                        vo[1] += fw * rec.Vb[1];
                        vo[2] += fw * rec.Vb[2];
                    }
                    else
                    {
                        float[] t = TransformPoint(skin[b], rec.Vb);
                        vo[0] += fw * t[0];
                        vo[1] += fw * t[1];
                        vo[2] += fw * t[2];
                    }
                }
                float dx = vo[0] - rec.Vb[0], dy = vo[1] - rec.Vb[1], dz = vo[2] - rec.Vb[2];
                float d = (float)Math.Sqrt(dx * dx + dy * dy + dz * dz);
                if (d > cfMax) cfMax = d;
                if (d > 1000f) cfOver1000++;
                if (d > 100f) cfOver100++;
            }
            string line = name + "\t" + boneMass[bi].ToString("F2", CI) + "\t" + (boneMassShare[bi] * 100.0).ToString("F3", CI) + "\t" +
                boneDomCount[bi] + "\t" + F3(boneMaxDisp[bi]) + "\t" + F3(dAng) + "\t" + F3(dPos) + "\t" + F3(pull) +
                "\t" + F3(cfMax) + "\t" + cfOver1000 + "\t" + cfOver100;
            Log(line);
            outRows.Add(line);
        }

        // 归因排名：按 mass 排序取前 10
        int[] rankOrder = new int[nb];
        for (int i = 0; i < nb; i++) rankOrder[i] = i;
        Array.Sort(rankOrder, delegate (int a, int b) { return boneMass[b].CompareTo(boneMass[a]); });
        Log("### 位移归因 top-10（bone\tmass\tshare_pct\tdAng\tdPos\tpull\tdom_count）");
        for (int r = 0; r < Math.Min(10, nb); r++)
        {
            int bi = rankOrder[r];
            float dAng = RotAngleDeg(bindWorld[bi], poseWorld[bi]);
            float dPos = (float)Math.Sqrt(Sq(poseWorld[bi][12] - bindWorld[bi][12]) + Sq(poseWorld[bi][13] - bindWorld[bi][13]) + Sq(poseWorld[bi][14] - bindWorld[bi][14]));
            float[] bp = new float[] { bindWorld[bi][12], bindWorld[bi][13], bindWorld[bi][14] };
            float[] moved = TransformPoint(skin[bi], bp);
            float pull = (float)Math.Sqrt(Sq(moved[0] - bp[0]) + Sq(moved[1] - bp[1]) + Sq(moved[2] - bp[2]));
            Log(boneName[bi] + "\t" + boneMass[bi].ToString("F1", CI) + "\t" + (boneMassShare[bi] * 100.0).ToString("F2", CI) +
                "\t" + F3(dAng) + "\t" + F3(dPos) + "\t" + F3(pull) + "\t" + boneDomCount[bi]);
        }

        // 反事实：把全部 skin 置为单位矩阵时位移必须为 0（自校验）
        float selfMax = 0f;
        foreach (VtxRec rec in recs)
        {
            float[] vo = new float[] { 0f, 0f, 0f };
            for (int j = 0; j < rec.W.Length; j++)
            {
                if (rec.W[j] == 0) continue;
                float fw = rec.W[j] / 255f;
                vo[0] += fw * rec.Vb[0];
                vo[1] += fw * rec.Vb[1];
                vo[2] += fw * rec.Vb[2];
            }
            float dx = vo[0] - rec.Vb[0], dy = vo[1] - rec.Vb[1], dz = vo[2] - rec.Vb[2];
            float d = (float)Math.Sqrt(dx * dx + dy * dy + dz * dz);
            if (d > selfMax) selfMax = d;
        }
        Log("自校验：skin 全置单位矩阵时最大位移=" + selfMax.ToString("E3", CI));

        // ============ Root / Bip001 逐骨明细 ============
        string[] DETAIL_BONES = new string[] { boneName[0], "Root", "Bip001" };
        List<string> detailRows = new List<string>();
        detailRows.Add("bone\tparent\trest_local_p\trest_world_p\tin_p\tout_p\tdelta_vs_rest\trest_ss0\trest_ss4\tanim_ss0\tanim_ss4");
        foreach (string dn in DETAIL_BONES)
        {
            int di = Array.IndexOf(boneName, dn);
            if (di < 0) { Log("BONEDETAIL " + dn + " MISSING"); detailRows.Add(dn + "\tMISSING"); continue; }
            float[] rp = restPos[di];
            float[] rw = new float[] { bindWorld[di][12], bindWorld[di][13], bindWorld[di][14] };
            float[] ip = posePos[di];
            float[] ow = new float[] { poseWorld[di][12], poseWorld[di][13], poseWorld[di][14] };
            float dv = (float)Math.Sqrt(Sq(ow[0] - rw[0]) + Sq(ow[1] - rw[1]) + Sq(ow[2] - rw[2]));
            string ssR = "[" + F3(restSS[di][0]) + "," + F3(restSS[di][1]) + "," + F3(restSS[di][2]) + "," +
                F3(restSS[di][3]) + "," + F3(restSS[di][4]) + "," + F3(restSS[di][5]) + "," +
                F3(restSS[di][6]) + "," + F3(restSS[di][7]) + "," + F3(restSS[di][8]) + "]";
            string ssA = "[" + F3(poseSS[di][0]) + "," + F3(poseSS[di][1]) + "," + F3(poseSS[di][2]) + "," +
                F3(poseSS[di][3]) + "," + F3(poseSS[di][4]) + "," + F3(poseSS[di][5]) + "," +
                F3(poseSS[di][6]) + "," + F3(poseSS[di][7]) + "," + F3(poseSS[di][8]) + "]";
            Log("BONEDETAIL " + dn + " parent=" + parent[di] +
                " rest_local_p=(" + F3(rp[0]) + "," + F3(rp[1]) + "," + F3(rp[2]) + ")" +
                " rest_world_p=(" + F3(rw[0]) + "," + F3(rw[1]) + "," + F3(rw[2]) + ")" +
                " in_p=(" + F3(ip[0]) + "," + F3(ip[1]) + "," + F3(ip[2]) + ")" +
                " out_p=(" + F3(ow[0]) + "," + F3(ow[1]) + "," + F3(ow[2]) + ")" +
                " delta=" + F(dv) + " rest_ss=" + ssR + " anim_ss=" + ssA);
            detailRows.Add(dn + "\t" + parent[di] +
                "\t(" + F3(rp[0]) + "," + F3(rp[1]) + "," + F3(rp[2]) + ")" +
                "\t(" + F3(rw[0]) + "," + F3(rw[1]) + "," + F3(rw[2]) + ")" +
                "\t(" + F3(ip[0]) + "," + F3(ip[1]) + "," + F3(ip[2]) + ")" +
                "\t(" + F3(ow[0]) + "," + F3(ow[1]) + "," + F3(ow[2]) + ")" +
                "\t" + F(dv) + "\t" + F3(restSS[di][0]) + "\t" + F3(restSS[di][4]) +
                "\t" + F3(poseSS[di][0]) + "\t" + F3(poseSS[di][4]));
        }
        List<string> chanRows = new List<string>();
        chanRows.Add("bone\tpx\tpy\tpz\tqx\tqy\tqz\tqw\tss0\tss4\tss8");
        for (int i = 0; i < nb; i++)
        {
            chanRows.Add(boneName[i] + "\t" + F6(posePos[i][0]) + "\t" + F6(posePos[i][1]) + "\t" + F6(posePos[i][2]) +
                "\t" + F6(poseQ[i][0]) + "\t" + F6(poseQ[i][1]) + "\t" + F6(poseQ[i][2]) + "\t" + F6(poseQ[i][3]) +
                "\t" + F6(poseSS[i][0]) + "\t" + F6(poseSS[i][4]) + "\t" + F6(poseSS[i][8]));
        }
        File.WriteAllLines(Path.Combine(outDir, "anim_channels.tsv"), chanRows.ToArray(), Encoding.UTF8);
        List<string> scaleRows = new List<string>();
        scaleRows.Add("bone\tss0\tss1\tss2\tss3\tss4\tss5\tss6\tss7\tss8\trest_ss0\trest_ss4");
        for (int i = 0; i < nb; i++)
        {
            StringBuilder sb = new StringBuilder(boneName[i]);
            for (int k = 0; k < 9; k++) sb.Append("\t").Append(F6(poseSS[i][k]));
            sb.Append("\t").Append(F6(restSS[i][0])).Append("\t").Append(F6(restSS[i][4]));
            scaleRows.Add(sb.ToString());
        }
        File.WriteAllLines(Path.Combine(outDir, "animss.tsv"), scaleRows.ToArray(), Encoding.UTF8);
        File.WriteAllLines(Path.Combine(outDir, "bonedetail.tsv"), detailRows.ToArray(), Encoding.UTF8);
        File.WriteAllLines(Path.Combine(outDir, "vertices.tsv"), vtxRows.ToArray(), Encoding.UTF8);
        File.WriteAllLines(Path.Combine(outDir, "bones.tsv"), boneRows.ToArray(), Encoding.UTF8);
        File.WriteAllLines(Path.Combine(outDir, "top20.tsv"), topRows.ToArray(), Encoding.UTF8);
        File.WriteAllLines(Path.Combine(outDir, "outliers.tsv"), outRows.ToArray(), Encoding.UTF8);
        File.WriteAllLines(Path.Combine(outDir, "posecmp.tsv"), poseRows.ToArray(), Encoding.UTF8);
        File.WriteAllLines(Path.Combine(outDir, "restlocal.tsv"), restRows.ToArray(), Encoding.UTF8);
        File.WriteAllText(Path.Combine(outDir, "summary.txt"), slog.ToString(), new UTF8Encoding(false));
        Log("BIND_DUMP_DONE");
    }

    class VtxRec
    {
        public string Mesh;
        public int Vi;
        public float[] Vb;
        public float[] Vo;
        public float Disp;
        public int DomBone;
        public int DomW;
        public int[] W;
        public int[] Idx;
        public int[] Palette;
    }

    static void BoneBox(float[][] w, int n, out float[] bmin, out float[] bmax, out float[] ctr)
    {
        bmin = new float[] { float.MaxValue, float.MaxValue, float.MaxValue };
        bmax = new float[] { float.MinValue, float.MinValue, float.MinValue };
        for (int i = 0; i < n; i++)
            for (int k = 0; k < 3; k++)
            {
                float v = w[i][12 + k];
                if (v < bmin[k]) bmin[k] = v;
                if (v > bmax[k]) bmax[k] = v;
            }
        ctr = new float[3];
        for (int k = 0; k < 3; k++) ctr[k] = (bmin[k] + bmax[k]) * 0.5f;
    }

    static void VSpaceReport(string tag, float[] boneMin, float[] boneMax, float[] boneCtr,
        float[] vtxMin, float[] vtxMax, int verts)
    {
        float[] vCtr = new float[3];
        for (int k = 0; k < 3; k++) vCtr[k] = (vtxMin[k] + vtxMax[k]) * 0.5f;
        float height = 0f; int boneAxis = 0;
        for (int k = 0; k < 3; k++)
        {
            float s = boneMax[k] - boneMin[k];
            if (s > height) { height = s; boneAxis = k; }
        }
        float vSpan = 0f; int vAxis = 0;
        for (int k = 0; k < 3; k++)
        {
            float s = vtxMax[k] - vtxMin[k];
            if (s > vSpan) { vSpan = s; vAxis = k; }
        }
        float dx = vCtr[0] - boneCtr[0], dy = vCtr[1] - boneCtr[1], dz = vCtr[2] - boneCtr[2];
        float dist = (float)Math.Sqrt(dx * dx + dy * dy + dz * dz);
        float limit = 0.2f * height;
        float vMag = 0f;
        for (int k = 0; k < 3; k++)
        {
            vMag = Math.Max(vMag, Math.Abs(vtxMin[k]));
            vMag = Math.Max(vMag, Math.Abs(vtxMax[k]));
        }
        float bMag = 0f;
        for (int k = 0; k < 3; k++)
        {
            bMag = Math.Max(bMag, Math.Abs(boneMin[k]));
            bMag = Math.Max(bMag, Math.Abs(boneMax[k]));
        }
        Log("VSPACE 口径=" + tag + " verts=" + verts +
            " bone_min=[" + F3(boneMin[0]) + "," + F3(boneMin[1]) + "," + F3(boneMin[2]) + "]" +
            " bone_max=[" + F3(boneMax[0]) + "," + F3(boneMax[1]) + "," + F3(boneMax[2]) + "]" +
            " bone_ctr=[" + F3(boneCtr[0]) + "," + F3(boneCtr[1]) + "," + F3(boneCtr[2]) + "]" +
            " bone_span=[" + F3(boneMax[0] - boneMin[0]) + "," + F3(boneMax[1] - boneMin[1]) + "," + F3(boneMax[2] - boneMin[2]) + "]" +
            " bone_axis=" + "XYZ"[boneAxis] +
            " vtx_min=[" + F3(vtxMin[0]) + "," + F3(vtxMin[1]) + "," + F3(vtxMin[2]) + "]" +
            " vtx_max=[" + F3(vtxMax[0]) + "," + F3(vtxMax[1]) + "," + F3(vtxMax[2]) + "]" +
            " vtx_ctr=[" + F3(vCtr[0]) + "," + F3(vCtr[1]) + "," + F3(vCtr[2]) + "]" +
            " vtx_span=[" + F3(vtxMax[0] - vtxMin[0]) + "," + F3(vtxMax[1] - vtxMin[1]) + "," + F3(vtxMax[2] - vtxMin[2]) + "]" +
            " vtx_axis=" + "XYZ"[vAxis] +
            " vtx_mag_log10=" + Math.Log10(vMag).ToString("F2", CI) +
            " bone_mag_log10=" + Math.Log10(bMag).ToString("F2", CI) +
            " height=" + F3(height) + " ctr_dist=" + F3(dist) + " limit=" + F3(limit) +
            " same_axis=" + (boneAxis == vAxis) + " dist_ok=" + (dist <= limit));
    }

    static float Sq(float v) { return v * v; }

    static string MatLine(float[] m)
    {
        StringBuilder sb = new StringBuilder("[");
        for (int i = 0; i < 16; i++)
        {
            sb.Append(m[i].ToString("F4", CI));
            if (i < 15) sb.Append(i % 4 == 3 ? " | " : ",");
        }
        return sb.Append("]").ToString();
    }

    static int MaxOf(int[] a)
    {
        int m = int.MinValue;
        foreach (int v in a) if (v > m) m = v;
        return m;
    }

    static void BuildWorld(float[][] pos, float[][] q, float[][] ss, int[] parent, int n, int order, int mode, int compose, out float[][] world)
    {
        world = new float[n][];
        for (int i = 0; i < n; i++)
        {
            float[] local = LocalMat(pos[i], q[i], ss[i], order, mode);
            if (parent[i] < 0) world[i] = local;
            else world[i] = compose == 0 ? MatMul(local, world[parent[i]]) : MatMul(world[parent[i]], local);
        }
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
        if (Math.Abs(d) < 1e-20f) throw new InvalidOperationException("骨 " + name + " InverseBind 3x3 行列式为 0");
        return (float)Math.Pow(Math.Abs(d), 1.0 / 3.0);
    }

    static float[] InvRotOnly(float[] m, string name)
    {
        float s = InvScale(m, name);
        float[] o = MatId();
        for (int r = 0; r < 3; r++)
            for (int c = 0; c < 3; c++) o[c * 4 + r] = m[r * 4 + c] / s;
        return o;
    }

    static float[] ImpliedBindPos(float[] m, string name)
    {
        float d = Det3(m);
        if (Math.Abs(d) < 1e-20f) throw new InvalidOperationException("骨 " + name + " InverseBind 3x3 行列式为 0");
        float[] inv = new float[9];
        inv[0] = (m[5] * m[10] - m[6] * m[9]) / d;
        inv[1] = (m[2] * m[9] - m[1] * m[10]) / d;
        inv[2] = (m[1] * m[6] - m[2] * m[5]) / d;
        inv[3] = (m[6] * m[8] - m[4] * m[10]) / d;
        inv[4] = (m[0] * m[10] - m[2] * m[8]) / d;
        inv[5] = (m[2] * m[4] - m[0] * m[6]) / d;
        inv[6] = (m[4] * m[9] - m[5] * m[8]) / d;
        inv[7] = (m[1] * m[8] - m[0] * m[9]) / d;
        inv[8] = (m[0] * m[5] - m[1] * m[4]) / d;
        float[] p = new float[3];
        for (int j = 0; j < 3; j++)
            p[j] = -(m[12] * inv[j] + m[13] * inv[3 + j] + m[14] * inv[6 + j]);
        return p;
    }

    static float[] Rot3(float[] m, string name)
    {
        float s = InvScale(m, name);
        float[] o = MatId();
        for (int r = 0; r < 3; r++)
            for (int c = 0; c < 3; c++) o[r * 4 + c] = m[r * 4 + c] / s;
        return o;
    }

    static float[] MatTr3(float[] m)
    {
        float[] o = MatId();
        for (int r = 0; r < 3; r++)
            for (int c = 0; c < 3; c++) o[r * 4 + c] = m[c * 4 + r];
        return o;
    }

    static float MaxDev3(float[] a, float[] b)
    {
        float d = 0f;
        for (int r = 0; r < 3; r++)
            for (int c = 0; c < 3; c++)
                d = Math.Max(d, Math.Abs(a[r * 4 + c] - b[r * 4 + c]));
        return d;
    }

    static float[] RotX90(int sign)
    {
        float[] m = MatId();
        m[5] = 0f;
        m[6] = sign > 0 ? 1f : -1f;
        m[9] = sign > 0 ? -1f : 1f;
        m[10] = 0f;
        return m;
    }

    static float[] MatTr(float[] m)
    {
        float[] o = new float[16];
        for (int r = 0; r < 4; r++)
            for (int c = 0; c < 4; c++) o[r * 4 + c] = m[c * 4 + r];
        return o;
    }

}
