import ctypes
import subprocess
from ctypes import wintypes

import numpy as np
from PIL import Image

PW_RENDERFULLCONTENT = 0x00000002
u = ctypes.windll.user32
g = ctypes.windll.gdi32


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


def game_pids():
    p = subprocess.run(["powershell", "-NoProfile", "-Command",
                        "Get-Process CivilizationVI* -ErrorAction SilentlyContinue | "
                        "Select-Object -ExpandProperty Id"], capture_output=True, text=True)
    return {int(x) for x in p.stdout.split()}


def capture(hwnd, w, h):
    hdc = u.GetDC(hwnd)
    mem = g.CreateCompatibleDC(hdc)
    bmp = g.CreateCompatibleBitmap(hdc, w, h)
    g.SelectObject(mem, bmp)
    u.PrintWindow(hwnd, mem, PW_RENDERFULLCONTENT)
    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.biWidth = w
    bi.biHeight = -h
    bi.biPlanes = 1
    bi.biBitCount = 32
    buf = ctypes.create_string_buffer(w * h * 4)
    g.GetDIBits(mem, bmp, 0, h, buf, ctypes.byref(bi), 0)
    img = Image.frombuffer("RGBA", (w, h), buf, "raw", "BGRA", 0, 1).convert("RGB")
    g.DeleteObject(bmp)
    g.DeleteDC(mem)
    u.ReleaseDC(hwnd, hdc)
    return img


def main():
    pids = game_pids()
    rows = []

    def cb(hwnd, _):
        pid = wintypes.DWORD()
        u.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        if pid.value not in pids:
            return True
        n = u.GetWindowTextLengthW(hwnd)
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(hwnd, buf, n + 1)
        r = RECT()
        u.GetWindowRect(hwnd, ctypes.byref(r))
        w, h = r.right - r.left, r.bottom - r.top
        if w < 200 or h < 200:
            return True
        rows.append((hwnd, buf.value, w, h, bool(u.IsWindowVisible(hwnd))))
        return True

    u.EnumWindows(ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(cb), 0)
    for i, (hwnd, title, w, h, vis) in enumerate(rows):
        img = capture(hwnd, w, h)
        a = np.asarray(img).astype(np.int32)
        mean = round(float(a.mean()), 2)
        out = "workspace/tmp/win%d.png" % i
        img.save(out)
        print("WIN", i, "hwnd", hwnd, "vis", vis, "size", w, h, "mean", mean, title[:40], out)


main()
