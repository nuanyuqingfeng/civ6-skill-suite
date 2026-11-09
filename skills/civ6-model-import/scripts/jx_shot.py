import argparse
import ctypes
from ctypes import wintypes

from PIL import Image

PW_RENDERFULLCONTENT = 0x00000002

u = ctypes.windll.user32
g = ctypes.windll.gdi32


class RECT(ctypes.Structure):
    _fields_ = [("left", ctypes.c_long), ("top", ctypes.c_long),
                ("right", ctypes.c_long), ("bottom", ctypes.c_long)]


class POINT(ctypes.Structure):
    _fields_ = [("x", ctypes.c_long), ("y", ctypes.c_long)]


class BITMAPINFOHEADER(ctypes.Structure):
    _fields_ = [("biSize", wintypes.DWORD), ("biWidth", ctypes.c_long),
                ("biHeight", ctypes.c_long), ("biPlanes", wintypes.WORD),
                ("biBitCount", wintypes.WORD), ("biCompression", wintypes.DWORD),
                ("biSizeImage", wintypes.DWORD), ("biXPelsPerMeter", ctypes.c_long),
                ("biYPelsPerMeter", ctypes.c_long), ("biClrUsed", wintypes.DWORD),
                ("biClrImportant", wintypes.DWORD)]


def find_window(substr):
    found = []

    def cb(hwnd, _):
        if not u.IsWindowVisible(hwnd):
            return True
        n = u.GetWindowTextLengthW(hwnd)
        if n == 0:
            return True
        buf = ctypes.create_unicode_buffer(n + 1)
        u.GetWindowTextW(hwnd, buf, n + 1)
        if substr in buf.value:
            found.append((hwnd, buf.value))
        return True

    u.EnumWindows(ctypes.WINFUNCTYPE(wintypes.BOOL, wintypes.HWND, wintypes.LPARAM)(cb), 0)
    return found


def capture_client(hwnd, path):
    wr = RECT()
    u.GetWindowRect(hwnd, ctypes.byref(wr))
    win_w = wr.right - wr.left
    win_h = wr.bottom - wr.top

    hdc_screen = u.GetDC(hwnd)
    hdc_mem = g.CreateCompatibleDC(hdc_screen)
    bmp = g.CreateCompatibleBitmap(hdc_screen, win_w, win_h)
    g.SelectObject(hdc_mem, bmp)
    ok = u.PrintWindow(hwnd, hdc_mem, PW_RENDERFULLCONTENT)

    bi = BITMAPINFOHEADER()
    bi.biSize = ctypes.sizeof(BITMAPINFOHEADER)
    bi.biWidth = win_w
    bi.biHeight = -win_h
    bi.biPlanes = 1
    bi.biBitCount = 32
    bi.biCompression = 0
    buf = ctypes.create_string_buffer(win_w * win_h * 4)
    g.GetDIBits(hdc_mem, bmp, 0, win_h, buf, ctypes.byref(bi), 0)

    img = Image.frombuffer("RGBA", (win_w, win_h), buf, "raw", "BGRA", 0, 1).convert("RGB")

    origin = POINT(0, 0)
    u.ClientToScreen(hwnd, ctypes.byref(origin))
    left = origin.x - wr.left
    top = origin.y - wr.top
    cr = RECT()
    u.GetClientRect(hwnd, ctypes.byref(cr))
    client_w = cr.right - cr.left
    client_h = cr.bottom - cr.top

    if 0 <= left and 0 <= top and left + client_w <= win_w and top + client_h <= win_h:
        img = img.crop((left, top, left + client_w, top + client_h))

    img.save(path)
    g.DeleteObject(bmp)
    g.DeleteDC(hdc_mem)
    u.ReleaseDC(hwnd, hdc_screen)
    print("SHOT|ok=" + str(bool(ok)) + "|win=" + str(win_w) + "x" + str(win_h) +
          "|client=" + str(client_w) + "x" + str(client_h) + "|path=" + path)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--title", default="Civilization VI")
    ap.add_argument("--out", required=True)
    a = ap.parse_args()
    wins = find_window(a.title)
    if not wins:
        raise SystemExit("找不到窗口：" + a.title)
    hwnd, title = wins[0]
    print("SHOT|hwnd=" + str(hwnd) + "|title=" + title)
    capture_client(hwnd, a.out)


main()
