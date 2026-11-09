using System;
using System.IO;
using System.Text;
using System.Windows.Forms;
using Firaxis.Utility;
using Firaxis.Granny;
using NexusBuddy;

// 参数化 dump：任意 granny 文件的模型与动画轨道组
class NexusDumpA
{
    static GrannyContext ctx;

    static string Fmt(float[] a, int n)
    {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) sb.Append(a[i].ToString("F3")).Append(i < n - 1 ? "," : "");
        return sb.ToString();
    }

    static void DumpFile(string path)
    {
        Console.WriteLine("==== " + Path.GetFileName(path));
        IGrannyFile f = ctx.LoadGrannyFile(path);
        Console.WriteLine("  Models=" + f.Models.Count + " Meshes=" + f.Meshes.Count + " Anims=" + f.Animations.Count);
        foreach (IGrannyModel m in f.Models)
        {
            Console.WriteLine("  Model " + m.Name + " sk=" + m.Skeleton.Name + " bones=" + m.Skeleton.Bones.Count);
        }
        foreach (IGrannyAnimation a in f.Animations)
        {
            Console.WriteLine("  Anim " + a.Name + " dur=" + a.Duration.ToString("F3") + " groups=" + a.TrackGroups.Count);
            foreach (IGrannyTrackGroup tg in a.TrackGroups)
            {
                Console.WriteLine("    TG " + tg.Name + " tracks=" + tg.TransformTracks.Count);
            }
        }
    }

    static void Main(string[] args)
    {
        Application.EnableVisualStyles();
        Form form = new CivNexusSixApplicationForm();
        ctx = Context.Get<GrannyContext>();
        foreach (string a in args)
        {
            DumpFile(a);
        }
        Console.WriteLine("DUMP_DONE");
    }
}
