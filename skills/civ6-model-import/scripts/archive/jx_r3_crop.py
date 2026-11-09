from PIL import Image
src = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\gen\reports\ingame_r3\01_idle.png"
out = r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\tmp"
im = Image.open(src)
print(im.size)
crops = {
    "face": (700, 250, 1000, 520),
    "lefthand": (900, 520, 1250, 900),
    "hair_edge": (780, 150, 1100, 400),
}
for name, box in crops.items():
    im.crop(box).resize(((box[2]-box[0])*2, (box[3]-box[1])*2), Image.LANCZOS).save(out + "\\crop_" + name + ".png")
    print("saved", name)
