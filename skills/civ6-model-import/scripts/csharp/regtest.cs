using System;
using System.Runtime.InteropServices;
using System.Security.Principal;
using Microsoft.Win32;
class RegTest {
  [DllImport("advapi32.dll", CharSet = CharSet.Unicode)]
  static extern int RegOpenKeyEx(UIntPtr hKey, string subKey, int options, int sam, out UIntPtr result);
  [DllImport("advapi32.dll")]
  static extern int RegCloseKey(UIntPtr hKey);

  static UIntPtr HKEY_CURRENT_USER = (UIntPtr)0x80000001u;

  static void RawOpen(string path, int sam) {
    UIntPtr k;
    int err = RegOpenKeyEx(HKEY_CURRENT_USER, path, 0, sam, out k);
    Console.WriteLine("RegOpenKeyEx(" + path + ", 0x" + sam.ToString("X") + ") -> err=" + err);
    if (err == 0) RegCloseKey(k);
  }

  static void Main() {
    WindowsIdentity id = WindowsIdentity.GetCurrent();
    Console.WriteLine("user=" + id.Name + " owner=" + id.Owner);
    foreach (IdentityReference g in id.Groups) {
      try {
        NTAccount acct = (NTAccount)g.Translate(typeof(NTAccount));
        if (acct.Value.Contains("Mandatory")) Console.WriteLine("group: " + acct.Value);
      } catch {}
    }
    Console.WriteLine("IsElevated=" + (id.Owner != new NTAccount("BUILTIN", "Users")));
    const int KEY_READ = 0x20019;
    const int KEY_WRITE = 0x20006;
    const int KEY_ALL_ACCESS = 0xF003F;
    RawOpen("Software\\Firaxis\\Projects", KEY_READ);
    RawOpen("Software\\Firaxis\\Projects", KEY_WRITE);
    RawOpen("Software", KEY_WRITE);
    RawOpen("Software\\Microsoft\\Windows\\CurrentVersion", KEY_READ);
    var k2 = Registry.CurrentUser.OpenSubKey("Software", false);
    Console.WriteLine("managed read Software -> " + (k2 != null));
    if (k2 != null) k2.Close();
  }
}
