using System;
using System.IO;
using System.Text;
using System.Windows.Forms;
using Firaxis.Utility;
using Firaxis.Granny;
using NexusBuddy;

class NexusDump
{
    static GrannyContext ctx;

    static string Fmt(float[] a, int n)
    {
        StringBuilder sb = new StringBuilder();
        for (int i = 0; i < n; i++) sb.Append(a[i].ToString("F3")).Append(i < n - 1 ? "," : "");
        return sb.ToString();
    }

    static void DumpBone(IGrannySkeleton sk, string name)
    {
        foreach (IGrannyBone b in sk.Bones)
        {
            if (b.Name == name)
            {
                float[] iw = b.InverseWorldTransform;
                Console.WriteLine("    bone " + name + " localPos=[" + Fmt(b.LocalTransform.Position, 3) +
                    "] localQuat=[" + Fmt(b.LocalTransform.Orientation, 4) + "]");
                Console.WriteLine("    bone " + name + " invWorld_t=[" + Fmt(new float[] { iw[12], iw[13], iw[14] }, 3) + "]");
                return;
            }
        }
        Console.WriteLine("    bone " + name + " MISSING");
    }

    static void DumpFile(string path, bool withAnims)
    {
        Console.WriteLine("==== " + Path.GetFileName(path));
        IGrannyFile f = ctx.LoadGrannyFile(path);
        Console.WriteLine("  Models=" + f.Models.Count + " Meshes=" + f.Meshes.Count + " Anims=" + f.Animations.Count);
        foreach (IGrannyModel m in f.Models)
        {
            IGrannySkeleton sk = m.Skeleton;
            Console.WriteLine("  Model " + m.Name + " skeleton=" + sk.Name + " bones=" + sk.Bones.Count +
                " initialPlacement.pos=[" + Fmt(m.InitialPlacement.Position, 3) + "]");
            StringBuilder names = new StringBuilder();
            int i = 0;
            foreach (IGrannyBone b in sk.Bones)
            {
                if (i++ < 10) names.Append(b.Name).Append(" | ");
            }
            Console.WriteLine("  firstBones: " + names);
            foreach (string bn in new string[] { "Root", "Bip001", "Bip001Pelvis", "Bip001Head" })
            {
                DumpBone(sk, bn);
            }
        }
        if (withAnims)
        {
            foreach (IGrannyAnimation a in f.Animations)
            {
                Console.WriteLine("  Anim " + a.Name + " dur=" + a.Duration.ToString("F3") +
                    " step=" + a.TimeStep.ToString("F4") + " groups=" + a.TrackGroups.Count);
                foreach (IGrannyTrackGroup tg in a.TrackGroups)
                {
                    Console.WriteLine("    TG " + tg.Name + " tracks=" + tg.TransformTracks.Count);
                    StringBuilder tn = new StringBuilder();
                    int i = 0;
                    foreach (IGrannyTransformTrack t in tg.TransformTracks)
                    {
                        if (i++ < 8) tn.Append(t.Name).Append(" | ");
                    }
                    Console.WriteLine("    firstTracks: " + tn);
                }
            }
        }
    }

    static void Main(string[] args)
    {
        Application.EnableVisualStyles();
        Form form = new CivNexusSixApplicationForm();
        ctx = Context.Get<GrannyContext>();
        if (args.Length > 0)
        {
            foreach (string a in args)
            {
                DumpFile(a, false);
            }
            Console.WriteLine("DUMP_DONE");
            return;
        }
        string vanilla = @"F:\Steam\steamapps\common\Sid Meier's Civilization VI SDK Assets\Civ6\pantry\Geometries\LEAD_CHIN_Qin.fgx";
        string deniaModel = @"D:\desktop\mods-CIV6\others\Denia_Pack\Denia_Pack\Geometries\DaniyaModelGeo.fgx";
        string deniaAnim = @"D:\desktop\mods-CIV6\others\Denia_Pack\Denia_Pack\Animations\Dny_IDLE.fgx";
        string proj = @"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\Jinzhou_Jinhsi";
        DumpFile(vanilla, false);
        DumpFile(deniaModel, false);
        DumpFile(deniaAnim, true);
        DumpFile(Path.Combine(proj, @"Geometries\LEAD_Jinhsi_QYQXP.fgx"), false);
        DumpFile(@"E:\SoftWares\civ6_nexus_work\jinhsi_fgx\LEAD_Jinhsi_QYQXP.fgx", false);
        DumpFile(@"E:\SoftWares\civ6_nexus_work\jinhsi_fgx\JX_IDLE.fgx", true);
        DumpFile(@"E:\SoftWares\civ6_nexus_work\jinhsi_fgx\JX_FirstMeet.fgx", true);
        Console.WriteLine("DUMP_DONE");
    }
}
