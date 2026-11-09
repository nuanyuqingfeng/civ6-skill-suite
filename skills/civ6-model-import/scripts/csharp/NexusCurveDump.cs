using System;
using System.IO;
using System.Text;
using System.Windows.Forms;
using Firaxis.Utility;
using Firaxis.Granny;
using NexusBuddy;

// 逐通道采样动画曲线原始数值，与基准对照
class NexusCurveDump
{
    static GrannyContext ctx;

    static string Fmt(float[] a)
    {
        StringBuilder sb = new StringBuilder();
        if (a == null) return "null";
        for (int i = 0; i < a.Length; i++) sb.Append(a[i].ToString("F3")).Append(i < a.Length - 1 ? "," : "");
        return sb.ToString();
    }

    static void Main(string[] args)
    {
        Application.EnableVisualStyles();
        Form form = new CivNexusSixApplicationForm();
        ctx = Context.Get<GrannyContext>();

        foreach (string animPath in args)
        {
            IGrannyFile af = ctx.LoadGrannyFile(animPath);
            IGrannyAnimation a = af.Animations[0];
            Console.WriteLine("==== " + Path.GetFileName(animPath) + " " + a.Name + " dur=" + a.Duration.ToString("F3"));
            if (args.Length > 1 && args[args.Length - 1] == "names")
            {
                foreach (IGrannyTrackGroup tg in a.TrackGroups)
                    foreach (IGrannyTransformTrack t in tg.TransformTracks)
                        Console.WriteLine("TRACK " + t.Name);
                continue;
            }
            foreach (IGrannyTrackGroup tg in a.TrackGroups)
            {
                Console.WriteLine("  TG " + tg.Name);
                foreach (string bn in new string[] { "Root", "Bip001", "Bip001Head" })
                {
                    foreach (IGrannyTransformTrack t in tg.TransformTracks)
                    {
                        if (t.Name != bn) continue;
                        float[] p0 = t.PositionCurve != null ? t.PositionCurve.Sample(0f, a.Duration, false, false, false) : null;
                        float[] p1 = t.PositionCurve != null ? t.PositionCurve.Sample(0.5f, a.Duration, false, false, false) : null;
                        float[] o0 = t.OrientationCurve != null ? t.OrientationCurve.Sample(0f, a.Duration, false, false, false) : null;
                        float[] o1 = t.OrientationCurve != null ? t.OrientationCurve.Sample(0.5f, a.Duration, false, false, false) : null;
                        float[] s0 = t.ScaleShearCurve != null ? t.ScaleShearCurve.Sample(0f, a.Duration, false, false, false) : null;
                        Console.WriteLine("    " + bn + " knots p=" + (t.PositionCurve != null ? t.PositionCurve.KnotCount.ToString() : "-") +
                            " o=" + (t.OrientationCurve != null ? t.OrientationCurve.KnotCount.ToString() : "-") +
                            " s=" + (t.ScaleShearCurve != null ? t.ScaleShearCurve.KnotCount.ToString() : "-"));
                        Console.WriteLine("      pos(0)=[ " + Fmt(p0) + "]  pos(.5)=[" + Fmt(p1) + "]");
                        Console.WriteLine("      ori(0)=[ " + Fmt(o0) + "]  ori(.5)=[" + Fmt(o1) + "]");
                        Console.WriteLine("      sca(0)=[ " + Fmt(s0) + "]");
                        break;
                    }
                }
            }
        }
        Console.WriteLine("CURVEDUMP_DONE");
    }
}
