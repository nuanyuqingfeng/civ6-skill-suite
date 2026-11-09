using System;
using System.Collections.Generic;
using System.Globalization;
using System.IO;
using System.Windows.Forms;
using Firaxis.Utility;
using Firaxis.Granny;
using NexusBuddy;

class Na2Tool
{
    static float[] IdentityQuat = new float[] { 0f, 0f, 0f, 1f };
    static float[] ZeroPos = new float[] { 0f, 0f, 0f };
    static CultureInfo CI = CultureInfo.InvariantCulture;
    static string[] Modes = new string[] { "rest", "anim", "probe", "ref", "compose" };

    static double[] QuatMat(float[] q)
    {
        double x = q[0]; double y = q[1]; double z = q[2]; double w = q[3];
        return new double[9] {
            1 - 2 * (y * y + z * z), 2 * (x * y - z * w), 2 * (x * z + y * w),
            2 * (x * y + z * w), 1 - 2 * (x * x + z * z), 2 * (y * z - x * w),
            2 * (x * z - y * w), 2 * (y * z + x * w), 1 - 2 * (x * x + y * y)
        };
    }

    static double[] Mul4(double[] a, double[] b)
    {
        double[] r = new double[16];
        for (int i = 0; i < 4; i++)
            for (int j = 0; j < 4; j++)
            {
                double s = 0;
                for (int k = 0; k < 4; k++) { s += a[i * 4 + k] * b[k * 4 + j]; }
                r[i * 4 + j] = s;
            }
        return r;
    }

    static double[] LocalMatrix(float[] pos, float[] ori)
    {
        double[] R = QuatMat(ori);
        double[] m = new double[16];
        m[0] = R[0]; m[1] = R[1]; m[2] = R[2];
        m[4] = R[3]; m[5] = R[4]; m[6] = R[5];
        m[8] = R[6]; m[9] = R[7]; m[10] = R[8];
        m[12] = pos[0]; m[13] = pos[1]; m[14] = pos[2]; m[15] = 1;
        return m;
    }

    static int[] FrameRange(float duration, float timestep, out int frames)
    {
        frames = 0;
        float time = 0f;
        while (time <= duration) { frames++; time = time + timestep; }
        return null;
    }

    static void Main(string[] args)
    {
        if (args.Length == 0) { Usage(); }
        string mode = args[0];
        Application.EnableVisualStyles();
        Form form = new CivNexusSixApplicationForm();
        GrannyContext ctx = Context.Get<GrannyContext>();

        if (Array.IndexOf(Modes, mode) < 0) { RunDirect(ctx, args); return; }

        if (mode == "rest")
        {
            IGrannyFile mf = ctx.LoadGrannyFile(args[1]);
            IGrannyModel model = mf.Models[0];
            int n = model.Skeleton.Bones.Count;
            StreamWriter w = new StreamWriter(new FileStream(args[2], FileMode.Create));
            for (int i = 0; i < n; i++)
            {
                IGrannyBone b = model.Skeleton.Bones[i];
                float[] p = b.LocalTransform.Position;
                float[] o = b.LocalTransform.Orientation;
                w.WriteLine(b.Name + "\t" + b.ParentIndex.ToString(CI) + "\t"
                    + p[0].ToString("f6", CI) + " " + p[1].ToString("f6", CI) + " " + p[2].ToString("f6", CI) + "\t"
                    + o[0].ToString("f6", CI) + " " + o[1].ToString("f6", CI) + " " + o[2].ToString("f6", CI) + " " + o[3].ToString("f6", CI));
            }
            w.Close();
            Console.WriteLine("REST_DONE bones=" + n + " -> " + args[2]);
            return;
        }

        if (mode == "anim")
        {
            Dictionary<string, float[]> restPosMap = new Dictionary<string, float[]>();
            Dictionary<string, float[]> restOriMap = new Dictionary<string, float[]>();
            foreach (string ln in File.ReadAllLines(args[2]))
            {
                string[] f = ln.Split('\t');
                restPosMap[f[0]] = Parse3(f[2]);
                restOriMap[f[0]] = Parse4(f[3]);
            }
            IGrannyFile af = ctx.LoadGrannyFile(args[1]);
            IGrannyAnimation anim = af.Animations[0];
            int frames;
            FrameRange(anim.Duration, 1f / 30f, out frames);
            int startFrame = args.Length > 4 ? int.Parse(args[4], CI) : 0;
            int frameLimit = args.Length > 5 ? int.Parse(args[5], CI) : frames;
            int endFrame = Math.Min(frames, startFrame + frameLimit);
            StreamWriter w = new StreamWriter(new FileStream(args[3], FileMode.Create));
            int tracks = 0;
            foreach (IGrannyTrackGroup tg in anim.TrackGroups)
            {
                foreach (IGrannyTransformTrack tr in tg.TransformTracks)
                {
                    if (!restPosMap.ContainsKey(tr.Name)) { continue; }
                    tracks++;
                    for (int f = startFrame; f < endFrame; f++)
                    {
                        float t = f * (1f / 30f);
                        float[] p = tr.PositionCurve.KnotCount > 0 ? tr.PositionCurve.Sample(t, anim.Duration, false, false, false) : restPosMap[tr.Name];
                        float[] o = tr.OrientationCurve.KnotCount > 0 ? tr.OrientationCurve.Sample(t, anim.Duration, false, false, false) : restOriMap[tr.Name];
                        w.WriteLine(tr.Name + "\t" + f.ToString(CI) + "\t"
                            + p[0].ToString("f6", CI) + " " + p[1].ToString("f6", CI) + " " + p[2].ToString("f6", CI) + "\t"
                            + o[0].ToString("f6", CI) + " " + o[1].ToString("f6", CI) + " " + o[2].ToString("f6", CI) + " " + o[3].ToString("f6", CI));
                    }
                }
            }
            w.Close();
            Console.WriteLine("ANIM_DONE tracks=" + tracks + " frames=" + frames + " emitted=" + startFrame + ".." + (endFrame - 1) + " duration=" + anim.Duration.ToString("f4") + " -> " + args[3]);
            return;
        }

        if (mode == "probe")
        {
            IGrannyFile pf = ctx.LoadGrannyFile(args[1]);
            IGrannyAnimation pa = pf.Animations[0];
            int pfFrame = int.Parse(args[2], CI);
            float pt = pfFrame * (1f / 30f);
            int idx = 0;
            foreach (IGrannyTrackGroup tg in pa.TrackGroups)
            {
                foreach (IGrannyTransformTrack tr in tg.TransformTracks)
                {
                    Console.WriteLine("TRY " + idx + " " + tr.Name + " t=" + pt.ToString("f4", CI));
                    Console.Out.Flush();
                    tr.PositionCurve.Sample(pt, pa.Duration, false, false, false);
                    tr.OrientationCurve.Sample(pt, pa.Duration, false, false, false);
                    idx++;
                }
            }
            Console.WriteLine("PROBE_OK tracks=" + idx);
            return;
        }

        if (mode == "ref")
        {
            IGrannyFile mf = ctx.LoadGrannyFile(args[1]);
            IGrannyFile af = ctx.LoadGrannyFile(args[2]);
            IGrannyModel model = mf.Models[0];
            IGrannyAnimation anim = af.Animations[0];
            int n = model.Skeleton.Bones.Count;
            HashSet<string> tracked = new HashSet<string>();
            foreach (IGrannyTrackGroup tg in anim.TrackGroups)
                foreach (IGrannyTransformTrack tr in tg.TransformTracks) { tracked.Add(tr.Name); }
            int boneLimit = int.Parse(args[4]);
            int frameLimit = int.Parse(args[5]);
            StreamWriter w = new StreamWriter(new FileStream(args[3], FileMode.Create));
            int taken = 0;
            for (int i = 0; i < n && taken < boneLimit; i++)
            {
                IGrannyBone b = model.Skeleton.Bones[i];
                if (!tracked.Contains(b.Name)) { continue; }
                taken++;
                for (int f = 0; f < frameLimit; f++)
                {
                    float[] v = anim.SampleBone(model, b.Name, f * (1f / 30f));
                    string s = b.Name + "\t" + f.ToString(CI) + "\t";
                    for (int k = 0; k < 16; k++) { s = s + v[k].ToString("f6", CI) + " "; }
                    w.WriteLine(s);
                }
            }
            w.Close();
            Console.WriteLine("REF_DONE bones=" + taken + " frames=" + frameLimit + " -> " + args[3]);
            return;
        }

        if (mode == "compose")
        {
            List<string> names = new List<string>();
            List<int> parent = new List<int>();
            List<float[]> restPos = new List<float[]>();
            List<float[]> restOri = new List<float[]>();
            Dictionary<string, int> boneIndex = new Dictionary<string, int>();
            foreach (string ln in File.ReadAllLines(args[1]))
            {
                string[] f = ln.Split('\t');
                boneIndex[f[0]] = names.Count;
                names.Add(f[0]);
                parent.Add(int.Parse(f[1], CI));
                restPos.Add(Parse3(f[2]));
                restOri.Add(Parse4(f[3]));
            }

            Dictionary<string, float[][]> trackPos = new Dictionary<string, float[][]>();
            Dictionary<string, float[][]> trackOri = new Dictionary<string, float[][]>();
            Dictionary<string, int> trackFrames = new Dictionary<string, int>();
            foreach (string ln in File.ReadAllLines(args[2]))
            {
                string[] f = ln.Split('\t');
                int fi = int.Parse(f[1], CI);
                float[][] arr;
                if (!trackPos.TryGetValue(f[0], out arr)) { arr = new float[4096][]; trackPos[f[0]] = arr; trackOri[f[0]] = new float[4096][]; }
                arr[fi] = Parse3(f[2]);
                trackOri[f[0]][fi] = Parse4(f[3]);
                trackFrames[f[0]] = fi + 1;
            }

            int frames = 0;
            foreach (int c in trackFrames.Values) { if (c > frames) { frames = c; } }
            if (args.Length > 6 && int.Parse(args[6], CI) > 0 && int.Parse(args[6], CI) < frames) { frames = int.Parse(args[6], CI); }
            int n = names.Count;
            int emitAll = args.Length > 5 && args[5] == "tracked" ? 0 : 1;
            List<int> emit = new List<int>();
            for (int i = 0; i < n; i++)
            {
                if (emitAll == 0 && !trackPos.ContainsKey(names[i])) { continue; }
                emit.Add(i);
            }

            StreamWriter w = new StreamWriter(new FileStream(args[3], FileMode.Create));
            w.WriteLine("// Nexus Buddy Animation NA2 - Exported from Nexus Buddy 2");
            w.WriteLine("FrameSets: 1");
            w.WriteLine("FrameCount: " + frames);
            w.WriteLine("FirstFrame: 1");
            w.WriteLine("LastFrame: " + frames);
            w.WriteLine("FPS: 30");
            w.WriteLine("Bones: " + emit.Count);
            double[][] world = new double[n][];
            double[][][] sampled = new double[emit.Count][][];
            for (int ei = 0; ei < emit.Count; ei++) { sampled[ei] = new double[frames][]; }
            for (int f = 0; f < frames; f++)
            {
                for (int i = 0; i < n; i++)
                {
                    float[] p; float[] o;
                    float[][] tp; float[][] to;
                    if (trackPos.TryGetValue(names[i], out tp) && trackOri.TryGetValue(names[i], out to) && f < tp.Length && tp[f] != null) { p = tp[f]; o = to[f]; }
                    else { p = restPos[i]; o = restOri[i]; }
                    double[] local = OutputMatrix(QuatMat(o), new double[] { p[0], p[1], p[2] });
                    int pi = parent[i];
                    world[i] = pi < 0 ? local : Mul4(local, world[pi]);
                }
                for (int ei = 0; ei < emit.Count; ei++) { sampled[ei][f] = world[emit[ei]]; }
            }
            for (int ei = 0; ei < emit.Count; ei++)
            {
                w.WriteLine(names[emit[ei]]);
                for (int f = 0; f < frames; f++)
                {
                    string s = "";
                    for (int k = 0; k < 16; k++) { s = s + sampled[ei][f][k].ToString("f6", CI) + " "; }
                    w.WriteLine(s);
                }
            }
            w.Close();
            Console.WriteLine("COMPOSE_DONE bones=" + emit.Count + " frames=" + frames + " -> " + args[3]);
            return;
        }

        throw new ArgumentException("unknown mode " + mode);
    }

    static double[] Mul3(double[] a, double[] b)
    {
        double[] r = new double[9];
        for (int i = 0; i < 3; i++)
            for (int j = 0; j < 3; j++)
            {
                double s = 0;
                for (int k = 0; k < 3; k++) { s += a[i * 3 + k] * b[k * 3 + j]; }
                r[i * 3 + j] = s;
            }
        return r;
    }

    static double[] OutputMatrix(double[] rot, double[] pos)
    {
        double[] r = new double[16];
        r[0] = rot[0]; r[1] = rot[3]; r[2] = rot[6]; r[3] = 0;
        r[4] = rot[1]; r[5] = rot[4]; r[6] = rot[7]; r[7] = 0;
        r[8] = rot[2]; r[9] = rot[5]; r[10] = rot[8]; r[11] = 0;
        r[12] = pos[0]; r[13] = pos[1]; r[14] = pos[2]; r[15] = 1;
        return r;
    }

    static double[] GrannyMatrix(double[] m)
    {
        double[] r = new double[16];
        r[0] = m[0]; r[1] = m[4]; r[2] = m[8]; r[3] = 0;
        r[4] = m[1]; r[5] = m[5]; r[6] = m[9]; r[7] = 0;
        r[8] = m[2]; r[9] = m[6]; r[10] = m[10]; r[11] = 0;
        r[12] = m[12]; r[13] = m[13]; r[14] = m[14]; r[15] = 1;
        return r;
    }

    static float[] Parse3(string s)
    {
        string[] p = s.Split(' ');
        return new float[] { float.Parse(p[0], CI), float.Parse(p[1], CI), float.Parse(p[2], CI) };
    }

    static float[] Parse4(string s)
    {
        string[] p = s.Split(' ');
        return new float[] { float.Parse(p[0], CI), float.Parse(p[1], CI), float.Parse(p[2], CI), float.Parse(p[3], CI) };
    }

    static void Usage()
    {
        Console.Error.WriteLine("usage: Na2Tool.exe <model.fgx> <anim.fgx> <out.na2> [startFrame] [endFrame]");
        Environment.Exit(2);
    }

    // 单命令通道：rest -> anim -> compose 三段在同一进程内按 f6 文本口径串接，骨选择与三段式 tracked 口径一致
    static void RunDirect(GrannyContext ctx, string[] args)
    {
        if (args.Length < 3) { Usage(); }
        IGrannyFile mf = ctx.LoadGrannyFile(args[0]);
        IGrannyModel model = mf.Models[0];
        int n = model.Skeleton.Bones.Count;
        List<string> names = new List<string>();
        List<int> parent = new List<int>();
        List<float[]> restPos = new List<float[]>();
        List<float[]> restOri = new List<float[]>();
        Dictionary<string, float[]> restPosMap = new Dictionary<string, float[]>();
        Dictionary<string, float[]> restOriMap = new Dictionary<string, float[]>();
        for (int i = 0; i < n; i++)
        {
            IGrannyBone b = model.Skeleton.Bones[i];
            float[] p = b.LocalTransform.Position;
            float[] o = b.LocalTransform.Orientation;
            string line = b.Name + "\t" + b.ParentIndex.ToString(CI) + "\t"
                + p[0].ToString("f6", CI) + " " + p[1].ToString("f6", CI) + " " + p[2].ToString("f6", CI) + "\t"
                + o[0].ToString("f6", CI) + " " + o[1].ToString("f6", CI) + " " + o[2].ToString("f6", CI) + " " + o[3].ToString("f6", CI);
            string[] f = line.Split('\t');
            names.Add(f[0]);
            parent.Add(int.Parse(f[1], CI));
            restPos.Add(Parse3(f[2]));
            restOri.Add(Parse4(f[3]));
            restPosMap[f[0]] = Parse3(f[2]);
            restOriMap[f[0]] = Parse4(f[3]);
        }

        IGrannyFile af = ctx.LoadGrannyFile(args[1]);
        IGrannyAnimation anim = af.Animations[0];
        int frames;
        FrameRange(anim.Duration, 1f / 30f, out frames);
        int startFrame = args.Length > 3 ? int.Parse(args[3], CI) : 0;
        int lastFrame = args.Length > 4 ? int.Parse(args[4], CI) : frames;
        if (lastFrame > frames) { lastFrame = frames; }
        List<string> animLines = new List<string>();
        foreach (IGrannyTrackGroup tg in anim.TrackGroups)
        {
            foreach (IGrannyTransformTrack tr in tg.TransformTracks)
            {
                if (!restPosMap.ContainsKey(tr.Name)) { continue; }
                for (int f = startFrame; f < lastFrame; f++)
                {
                    float t = f * (1f / 30f);
                    float[] p = tr.PositionCurve.KnotCount > 0 ? tr.PositionCurve.Sample(t, anim.Duration, false, false, false) : restPosMap[tr.Name];
                    float[] o = tr.OrientationCurve.KnotCount > 0 ? tr.OrientationCurve.Sample(t, anim.Duration, false, false, false) : restOriMap[tr.Name];
                    animLines.Add(tr.Name + "\t" + f.ToString(CI) + "\t"
                        + p[0].ToString("f6", CI) + " " + p[1].ToString("f6", CI) + " " + p[2].ToString("f6", CI) + "\t"
                        + o[0].ToString("f6", CI) + " " + o[1].ToString("f6", CI) + " " + o[2].ToString("f6", CI) + " " + o[3].ToString("f6", CI));
                }
            }
        }

        Dictionary<string, float[][]> trackPos = new Dictionary<string, float[][]>();
        Dictionary<string, float[][]> trackOri = new Dictionary<string, float[][]>();
        Dictionary<string, int> trackFrames = new Dictionary<string, int>();
        foreach (string ln in animLines)
        {
            string[] f = ln.Split('\t');
            int fi = int.Parse(f[1], CI);
            float[][] arr;
            if (!trackPos.TryGetValue(f[0], out arr)) { arr = new float[4096][]; trackPos[f[0]] = arr; trackOri[f[0]] = new float[4096][]; }
            arr[fi] = Parse3(f[2]);
            trackOri[f[0]][fi] = Parse4(f[3]);
            trackFrames[f[0]] = fi + 1;
        }

        int composeFrames = 0;
        foreach (int c in trackFrames.Values) { if (c > composeFrames) { composeFrames = c; } }
        if (lastFrame > 0 && lastFrame < composeFrames) { composeFrames = lastFrame; }
        List<int> emit = new List<int>();
        for (int i = 0; i < n; i++)
        {
            if (!trackPos.ContainsKey(names[i])) { continue; }
            emit.Add(i);
        }

        StreamWriter w = new StreamWriter(new FileStream(args[2], FileMode.Create));
        w.WriteLine("// Nexus Buddy Animation NA2 - Exported from Nexus Buddy 2");
        w.WriteLine("FrameSets: 1");
        w.WriteLine("FrameCount: " + composeFrames);
        w.WriteLine("FirstFrame: 1");
        w.WriteLine("LastFrame: " + composeFrames);
        w.WriteLine("FPS: 30");
        w.WriteLine("Bones: " + emit.Count);
        double[][] world = new double[n][];
        double[][][] sampled = new double[emit.Count][][];
        for (int ei = 0; ei < emit.Count; ei++) { sampled[ei] = new double[composeFrames][]; }
        for (int f = 0; f < composeFrames; f++)
        {
            for (int i = 0; i < n; i++)
            {
                float[] p; float[] o;
                float[][] tp; float[][] to;
                if (trackPos.TryGetValue(names[i], out tp) && trackOri.TryGetValue(names[i], out to) && f < tp.Length && tp[f] != null) { p = tp[f]; o = to[f]; }
                else { p = restPos[i]; o = restOri[i]; }
                double[] local = OutputMatrix(QuatMat(o), new double[] { p[0], p[1], p[2] });
                int pi = parent[i];
                world[i] = pi < 0 ? local : Mul4(local, world[pi]);
            }
            for (int ei = 0; ei < emit.Count; ei++) { sampled[ei][f] = world[emit[ei]]; }
        }
        for (int ei = 0; ei < emit.Count; ei++)
        {
            w.WriteLine(names[emit[ei]]);
            for (int f = 0; f < composeFrames; f++)
            {
                string s = "";
                for (int k = 0; k < 16; k++) { s = s + sampled[ei][f][k].ToString("f6", CI) + " "; }
                w.WriteLine(s);
            }
        }
        w.Close();
        Console.WriteLine("DIRECT_DONE bones=" + emit.Count + " frames=" + composeFrames + " start=" + startFrame + " end=" + lastFrame + " -> " + args[2]);
    }
}
