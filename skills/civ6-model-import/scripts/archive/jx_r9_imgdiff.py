import bpy

A = bpy.data.images.load(r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\reports\r9\mouth_035.png")
B = bpy.data.images.load(r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\reports\r9\mouth_100.png")
pa = list(A.pixels)
pb = list(B.pixels)
w, h = A.size
diff = 0.0
count = 0
minx, maxx, miny, maxy = w, -1, h, -1
for y in range(h):
    row = y * w * 4
    for x in range(w):
        i = row + x * 4
        d = abs(pa[i] - pb[i]) + abs(pa[i + 1] - pb[i + 1]) + abs(pa[i + 2] - pb[i + 2])
        if d > 0.02:
            count += 1
            diff += d
            minx = min(minx, x)
            maxx = max(maxx, x)
            miny = min(miny, y)
            maxy = max(maxy, y)
print("DIFF pixels", count, "of", w * h, "mean", round(diff / max(1, count), 4))
print("DIFF bbox", minx, maxx, miny, maxy)
