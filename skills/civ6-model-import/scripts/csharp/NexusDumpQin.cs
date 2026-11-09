using System;
using System.IO;
using System.Text;
using System.Windows.Forms;
using Firaxis.Utility;
using Firaxis.Granny;
using NexusBuddy;

class NexusDumpQin
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
            if (b.Name.ToLower() == name.ToLower())
            {
                float[] iw = b.InverseWorldTransform;
                Console.WriteLine("    bone " + b.Name + " localPos=[" + Fmt(b.LocalTransform.Position, 3) +
                    "] localQuat=[" + Fmt(b.LocalTransform.Orientation, 4) + "]");
                Console.WriteLine("    bone " + b.Name + " invWorld_t=[" +
                    Fmt(new float[] { iw[12], iw[13], iw[14] }, 3) + "]");
                return;
            }
        }
    }

    static void Main(string[] args)
    {
        Application.EnableVisualStyles();
        Form form = new CivNexusSixApplicationForm();
        ctx = Context.Get<GrannyContext>();
        string file = args[0];
        Console.WriteLine("==== " + Path.GetFileName(file));
        IGrannyFile f = ctx.LoadGrannyFile(file);
        foreach (IGrannyModel m in f.Models)
        {
            Console.WriteLine("  Model " + m.Name + " sk=" + m.Skeleton.Name + " bones=" + m.Skeleton.Bones.Count +
                " placement.pos=[" + Fmt(m.InitialPlacement.Position, 3) + "] placement.quat=[" +
                Fmt(m.InitialPlacement.Orientation, 4) + "]");
            int gi = 0;
            foreach (IGrannyBone b in m.Skeleton.Bones)
            {
                if (gi++ < 3)
                {
                    float[] iw = b.InverseWorldTransform;
                    Console.WriteLine("    generic[" + (gi - 1) + "] " + b.Name +
                        " invWorld_t=[" + Fmt(new float[] { iw[12], iw[13], iw[14] }, 3) + "]");
                }
            }
            foreach (string bn in new string[] { "Root", "Pelvis", "Spine", "Spine1", "Neck", "Head",
                                                 "Bip001", "Bip001Pelvis", "Bip001Head" })
            {
                DumpBone(m.Skeleton, bn);
            }
        }
        Console.WriteLine("DUMP_DONE");
    }
}
