using System;
using System.IO;
using System.Reflection;
using System.Text;

// 反射列出 NexusBuddy 关键类型的公共方法签名
class NexusRefl
{
    static void Main(string[] args)
    {
        Assembly asm = Assembly.LoadFrom(Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "CivNexus6.exe"));
        foreach (string want in new string[] { "FBXImporter", "GrannyContext" })
        {
            foreach (Type t in asm.GetTypes())
            {
                if (t.Name == want)
                {
                    Console.WriteLine("== " + t.FullName);
                    foreach (MethodInfo m in t.GetMethods(BindingFlags.Public | BindingFlags.Static | BindingFlags.Instance))
                    {
                        if (m.DeclaringType == t)
                        {
                            ParameterInfo[] ps = m.GetParameters();
                            StringBuilder sb = new StringBuilder();
                            foreach (ParameterInfo p in ps) sb.Append(p.ParameterType.Name).Append(" ").Append(p.Name).Append(", ");
                            Console.WriteLine("  " + m.ReturnType.Name + " " + m.Name + "(" + sb.ToString().TrimEnd(' ', ',') + ")");
                        }
                    }
                }
            }
        }
        Console.WriteLine("REFL_DONE");
    }
}
