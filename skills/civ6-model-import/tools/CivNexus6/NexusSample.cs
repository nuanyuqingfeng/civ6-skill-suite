using System;
using System.IO;
using System.Text;
using System.Windows.Forms;
using Firaxis.Utility;
using Firaxis.Granny;
using NexusBuddy;

// 用模型骨架采样动画轨道数值，并与基准对照
class NexusSample
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

        string modelPath = args[0];
        string animPath = args[1];

        IGrannyFile mf = ctx.LoadGrannyFile(modelPath);
        IGrannyModel m = mf.Models[0];
        Console.WriteLine("MODEL " + Path.GetFileName(modelPath) + " sk=" + m.Skeleton.Name + " bones=" + m.Skeleton.Bones.Count);

        IGrannyFile af = ctx.LoadGrannyFile(animPath);
        IGrannyAnimation a = af.Animations[0];
        Console.WriteLine("ANIM " + a.Name + " dur=" + a.Duration.ToString("F3") + " groups=" + a.TrackGroups.Count);

        foreach (IGrannyTrackGroup tg in a.TrackGroups)
        {
            Console.WriteLine("  TG " + tg.Name + " tracks=" + tg.TransformTracks.Count);
            foreach (string bn in new string[] { "Root", "Bip001", "Bip001Pelvis", "Bip001Head" })
            {
                foreach (IGrannyTransformTrack t in tg.TransformTracks)
                {
                    if (t.Name == bn)
                    {
                        Console.WriteLine("    track " + bn + " flags=" + t.Flags +
                            " posCurve=" + (t.PositionCurve != null) + " oriCurve=" + (t.OrientationCurve != null) +
                            " scaleCurve=" + (t.ScaleShearCurve != null));
                        break;
                    }
                }
            }
        }

        foreach (float tm in new float[] { 0f, 0.5f })
        {
            foreach (string bn in new string[] { "Root", "Bip001", "Bip001Pelvis", "Bip001Head" })
            {
                float[] s = a.SampleBone(m, bn, tm);
                Console.WriteLine("  t=" + tm.ToString("F2") + " " + bn + " sample=[" + Fmt(s) + "]");
            }
        }
        Console.WriteLine("SAMPLE_DONE");
    }
}
