using System;
using System.IO;
using System.Windows.Forms;
using System.Runtime.InteropServices;
using Firaxis.Utility;
using Firaxis.Granny;
using NexusBuddy;
using NexusBuddy.GrannyWrappers;

class BoundsDump
{
    static GrannyContext ctx;

    static float ReadF(IntPtr p, int offset)
    {
        return Marshal.PtrToStructure<float>(new IntPtr(p.ToInt64() + offset));
    }

    static string F(float[] a)
    {
        return a[0].ToString("F1") + "," + a[1].ToString("F1") + "," + a[2].ToString("F1");
    }

    static void DumpFile(string path)
    {
        Console.WriteLine("==== " + Path.GetFileName(path));
        IGrannyFile f = ctx.LoadGrannyFile(path);
        System.Collections.Generic.List<IGrannyMesh> meshes =
            new System.Collections.Generic.List<IGrannyMesh>(f.Meshes);
        if (meshes.Count == 0 && f.Models.Count > 0)
        {
            meshes = new System.Collections.Generic.List<IGrannyMesh>(f.Models[0].MeshBindings);
        }
        foreach (IGrannyMesh im in meshes)
        {
            GrannyMeshWrapper w = new GrannyMeshWrapper(im);
            int n = w.getNumVertices();
            IntPtr vp = w.getVerticesPtr();
            if (n == 0 || vp == IntPtr.Zero)
            {
                Console.WriteLine("  mesh " + im.Name + " verts=0");
                continue;
            }
            int bestStride = 0;
            float bestRange = -1f;
            float[] bestMin = null;
            float[] bestMax = null;
            foreach (int stride in new int[] { 32, 40, 44, 48, 56, 60, 64, 68, 72, 76, 80, 84, 88, 96 })
            {
                float mn0 = float.MaxValue, mn1 = float.MaxValue, mn2 = float.MaxValue;
                float mx0 = float.MinValue, mx1 = float.MinValue, mx2 = float.MinValue;
                bool ok = true;
                for (int i = 0; i < n && ok; i++)
                {
                    IntPtr p = new IntPtr(vp.ToInt64() + (long)i * stride);
                    float x = ReadF(p, 0);
                    float y = ReadF(p, 4);
                    float z = ReadF(p, 8);
                    if (Single.IsNaN(x) || Single.IsNaN(y) || Single.IsNaN(z) ||
                        Math.Abs(x) > 50000f || Math.Abs(y) > 50000f || Math.Abs(z) > 50000f)
                    {
                        ok = false;
                        break;
                    }
                    mn0 = Math.Min(mn0, x); mx0 = Math.Max(mx0, x);
                    mn1 = Math.Min(mn1, y); mx1 = Math.Max(mx1, y);
                    mn2 = Math.Min(mn2, z); mx2 = Math.Max(mx2, z);
                }
                if (ok)
                {
                    float range = Math.Max(mx0 - mn0, Math.Max(mx1 - mn1, mx2 - mn2));
                    if (range > bestRange)
                    {
                        bestRange = range;
                        bestStride = stride;
                        bestMin = new float[] { mn0, mn1, mn2 };
                        bestMax = new float[] { mx0, mx1, mx2 };
                    }
                }
            }
            if (bestMin != null)
            {
                Console.WriteLine("  mesh " + im.Name + " verts=" + n + " stride=" + bestStride +
                    " min=[" + F(bestMin) + "] max=[" + F(bestMax) + "]");
            }
            else
            {
                Console.WriteLine("  mesh " + im.Name + " verts=" + n + " stride=?");
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
        Console.WriteLine("BOUNDS_DONE");
    }
}
