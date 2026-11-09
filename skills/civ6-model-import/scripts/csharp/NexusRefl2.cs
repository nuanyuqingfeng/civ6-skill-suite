using System;
using System.IO;
using System.Reflection;
using System.Text;

// 反射列出 granny 动画轨道相关接口的成员
class NexusRefl2
{
    static void Dump(Type t)
    {
        Console.WriteLine("== " + t.FullName);
        const BindingFlags F = BindingFlags.Public | BindingFlags.NonPublic | BindingFlags.Instance | BindingFlags.Static;
        foreach (MethodInfo m in t.GetMethods(F))
        {
            if (m.DeclaringType == t && !m.IsSpecialName)
            {
                ParameterInfo[] ps = m.GetParameters();
                StringBuilder sb = new StringBuilder();
                foreach (ParameterInfo p in ps) sb.Append(p.ParameterType.Name).Append(" ").Append(p.Name).Append(", ");
                Console.WriteLine("  " + m.ReturnType.Name + " " + m.Name + "(" + sb.ToString().TrimEnd(' ', ',') + ")");
            }
        }
        foreach (PropertyInfo p in t.GetProperties(F))
            Console.WriteLine("  prop " + p.PropertyType.Name + " " + p.Name);
        foreach (FieldInfo f in t.GetFields(F))
            Console.WriteLine("  field " + f.FieldType.Name + " " + f.Name);
        foreach (ConstructorInfo c in t.GetConstructors(F))
        {
            ParameterInfo[] ps = c.GetParameters();
            StringBuilder sb = new StringBuilder();
            foreach (ParameterInfo p in ps) sb.Append(p.ParameterType.Name).Append(" ").Append(p.Name).Append(", ");
            Console.WriteLine("  ctor (" + sb.ToString().TrimEnd(' ', ',') + ")");
        }
    }

    static void Main(string[] args)
    {
        string baseDir = AppDomain.CurrentDomain.BaseDirectory;
        string[] dlls = { "CivNexus6.exe", "Firaxis.Granny.dll", "Firaxis.Granny.Impl.dll", "Firaxis.MathEx.dll" };
        string[] wants = { "GrannyAnimationWrapper", "GrannyAnimation", "GrannyTrackGroup", "GrannyTransformTrack", "GrannyCurve", "CurveConstant", "CurveDataType" };
        bool listAll = args.Length > 0 && args[0] == "all";
        foreach (string name in dlls)
        {
            string path = Path.Combine(baseDir, name);
            if (!File.Exists(path)) continue;
            Assembly asm = Assembly.LoadFrom(path);
            foreach (Type t in asm.GetTypes())
            {
                if (listAll)
                {
                    if (t.Name.Contains("Curve") || t.Name.Contains("Track") || t.Name.Contains("Animation"))
                        Console.WriteLine("  type " + t.FullName);
                }
                else if (Array.IndexOf(wants, t.Name) >= 0)
                {
                    Dump(t);
                }
            }
        }
        Console.WriteLine("REFL2_DONE");
    }
}
