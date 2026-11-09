using System;
using System.IO;
using System.Text;
using System.Windows.Forms;
using Firaxis.Utility;
using Firaxis.Granny;
using NexusBuddy;

// 全骨对照：模型 rest 局部 vs 动画曲线 t=0 采样，输出标定数据行
class NexusCalibCompare
{
    static GrannyContext ctx;

    static string Fmt(float[] a, int n)
    {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) sb.Append(a[i].ToString("F4")).Append(i < n - 1 ? "," : "");
        return sb.ToString();
    }

    static void Main(string[] args)
    {
        Application.EnableVisualStyles();
        Form form = new CivNexusSixApplicationForm();
        ctx = Context.Get<GrannyContext>();

        IGrannyFile mf = ctx.LoadGrannyFile(args[0]);
        IGrannyModel m = mf.Models[0];
        IGrannyFile af = ctx.LoadGrannyFile(args[1]);
        IGrannyAnimation a = af.Animations[0];
        IGrannyTrackGroup tg = a.TrackGroups[0];

        foreach (IGrannyBone b in m.Skeleton.Bones)
        {
            float[] rp = b.LocalTransform.Position;
            float[] ro = b.LocalTransform.Orientation;
            string line = "ROW " + b.Name +
                " | rest_p=" + Fmt(rp, 3) +
                " | rest_q=" + Fmt(ro, 4);
            foreach (IGrannyTransformTrack t in tg.TransformTracks)
            {
                if (t.Name != b.Name) continue;
                float[] cp = t.PositionCurve != null ? t.PositionCurve.Sample(0f, a.Duration, false, false, false) : null;
                float[] co = t.OrientationCurve != null ? t.OrientationCurve.Sample(0f, a.Duration, false, false, false) : null;
                line += " | cur_p=" + (cp != null ? Fmt(cp, 3) : "none") +
                        " | cur_q=" + (co != null ? Fmt(co, 4) : "none");
                break;
            }
            Console.WriteLine(line);
        }
        Console.WriteLine("CALIB_DUMP_DONE");
    }
}
