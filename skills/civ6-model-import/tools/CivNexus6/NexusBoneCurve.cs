using System;
using System.Windows.Forms;
using Firaxis.Utility;
using Firaxis.Granny;
using NexusBuddy;

class NexusBoneCurve
{
    static GrannyContext ctx;

    static void Main(string[] args)
    {
        Application.EnableVisualStyles();
        Form form = new CivNexusSixApplicationForm();
        ctx = Context.Get<GrannyContext>();
        IGrannyFile mf = ctx.LoadGrannyFile(args[0]);
        IGrannyFile af = ctx.LoadGrannyFile(args[1]);
        IGrannyAnimation a = af.Animations[0];
        Console.WriteLine("ANIM " + a.Name + " dur=" + a.Duration.ToString("F4") + " groups=" + a.TrackGroups.Count);
        IGrannyTrackGroup tg = a.TrackGroups[0];
        foreach (IGrannyTransformTrack t in tg.TransformTracks)
        {
            float[] p = t.PositionCurve != null ? t.PositionCurve.Sample(0f, a.Duration, false, false, false) : new float[] { 0f, 0f, 0f };
            float[] q = t.OrientationCurve != null ? t.OrientationCurve.Sample(0f, a.Duration, false, false, false) : new float[] { 0f, 0f, 0f, 1f };
            float[] s = t.ScaleShearCurve != null ? t.ScaleShearCurve.Sample(0f, a.Duration, false, false, false) : new float[] { 1f, 1f, 1f };
            Console.WriteLine("BC " + t.Name + " " + p[0].ToString("R") + " " + p[1].ToString("R") + " " + p[2].ToString("R") + " " +
                q[0].ToString("R") + " " + q[1].ToString("R") + " " + q[2].ToString("R") + " " + q[3].ToString("R") + " " +
                s[0].ToString("R") + " " + s[1].ToString("R") + " " + s[2].ToString("R"));
        }
        Console.WriteLine("BC_DONE");
    }
}
