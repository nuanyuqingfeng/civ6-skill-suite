using System;
using System.IO;
using System.Windows.Forms;
using Firaxis.Utility;
using Firaxis.Granny;
using NexusBuddy;

// 输出模型全部骨名与动画全部轨道名供集合对比
class NexusNames
{
    static GrannyContext ctx;

    static void Main(string[] args)
    {
        Application.EnableVisualStyles();
        Form form = new CivNexusSixApplicationForm();
        ctx = Context.Get<GrannyContext>();

        string modelPath = args[0];
        string animPath = args[1];

        IGrannyFile mf = ctx.LoadGrannyFile(modelPath);
        foreach (IGrannyBone b in mf.Models[0].Skeleton.Bones)
            Console.WriteLine("BONE " + b.Name);

        IGrannyFile af = ctx.LoadGrannyFile(animPath);
        foreach (IGrannyTrackGroup tg in af.Animations[0].TrackGroups)
            foreach (IGrannyTransformTrack t in tg.TransformTracks)
                Console.WriteLine("TRACK " + t.Name);

        Console.WriteLine("NAMES_DONE");
    }
}
