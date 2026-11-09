using System;
using System.IO;
using System.Reflection;
using System.Windows.Forms;
using Firaxis.Utility;
using Firaxis.Granny;
using NexusBuddy;

// 反射调用 internal exportNA2，把动画导出为 NA2 文本以便人工检查关键帧
class NexusNA2
{
    static void Main(string[] args)
    {
        Application.EnableVisualStyles();
        Form form = new CivNexusSixApplicationForm();
        GrannyContext ctx = Context.Get<GrannyContext>();

        string modelPath = args[0];
        string animPath = args[1];
        string outPath = args[2];

        IGrannyFile mf = ctx.LoadGrannyFile(modelPath);
        IGrannyFile af = ctx.LoadGrannyFile(animPath);
        Console.WriteLine("MODEL " + mf.Models[0].Name + " ANIM " + af.Animations[0].Name);

        Assembly asm = typeof(CivNexusSixApplicationForm).Assembly;
        Type t = asm.GetType("NexusBuddy.FileOps.NB2NA2FileOps");
        MethodInfo mi = t.GetMethod("exportNA2", BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Static);
        object result = mi.Invoke(null, new object[] { mf.Models[0], af.Animations[0], outPath,
            0f, af.Animations[0].Duration, 30, 3 });
        Console.WriteLine("NA2_EXPORT result=" + result + " -> " + outPath);
        Console.WriteLine("NA2_DONE");
    }
}
