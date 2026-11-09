import bpy
import addon_utils
import json
import os
import sys

ARGV = sys.argv[sys.argv.index("--") + 1:] if "--" in sys.argv else []

def arg(name, default=None):
    if name in ARGV:
        return ARGV[ARGV.index(name) + 1]
    return default

def arg_all(name):
    out = []
    for i, a in enumerate(ARGV):
        if a == name and i + 1 < len(ARGV):
            out.append(ARGV[i + 1])
    return out

TEX_EXTS = (".png", ".dds", ".tga", ".tif", ".jpg")

def strip_material_prefix(name):
    """材质名去掉常见实例前缀，得到贴图命名基名。

    Civ6 单位材质多以 MI_ 开头，贴图以 T_ 开头，两者之间的公共部分是角色与部位。
    这里只做可配置的前缀剥除，不假设固定前后缀。
    """
    base = name
    for pre in ("MI_", "M_", "MAT_"):
        if base.startswith(pre):
            base = base[len(pre):]
            break
    for suf in ("_Mat", "_Inst", "_MAT"):
        if base.endswith(suf):
            base = base[: -len(suf)]
            break
    return base

def find_texture(tex_dir, mat_name):
    """按候选规则在目录里找贴图。

    候选顺序：<贴图基名>_D、T_<贴图基名>_D、<材质名>_D、<贴图基名>、T_<贴图基名>。
    逐个扩展名尝试，首个命中即返回；全部不中返回 None，由调用方报错。
    """
    base = strip_material_prefix(mat_name)
    stems = []
    for cand in (base + "_D", "T_" + base + "_D", mat_name + "_D", base, "T_" + base):
        if cand not in stems:
            stems.append(cand)
    for stem in stems:
        for ext in TEX_EXTS:
            p = os.path.join(tex_dir, stem + ext)
            if os.path.isfile(p):
                return p
    return None

FBX = arg("--fbx")
PROJECT = arg("--project")
if not FBX or not PROJECT:
    raise SystemExit("必须给 --fbx 与 --project")

ASSET = arg("--asset", "Unit")
RIG_NAME = arg("--rig-name", "UnitRig")
MESH_NAME = arg("--mesh-name", "UnitBody")
DSG = arg("--dsg", "potential_any_graph")
TEX_DIR = arg("--tex-dir")
TEX_MAP = arg_all("--tex")
SLOTS = arg_all("--slot")
MAX_TEX = int(arg("--max-tex", "1024"))

bpy.ops.wm.read_factory_settings(use_empty=True)
if not addon_utils.enable("CivModelTool", default_set=True):
    raise SystemExit("CivModelTool 未加载；请设 BLENDER_USER_SCRIPTS 指向 blender portable/scripts")

bpy.ops.import_scene.fbx(filepath=FBX)
arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
if len(arms) != 1:
    raise SystemExit("FBX 里应只有 1 副骨架，实际 %d" % len(arms))
arm = arms[0]
mesh = max([o for o in bpy.data.objects if o.type == 'MESH'], key=lambda o: len(o.data.vertices))
arm.name = RIG_NAME
mesh.name = MESH_NAME
print("IMPORTED bones=%d verts=%d mats=%d" % (len(arm.data.bones), len(mesh.data.vertices), len(mesh.material_slots)))

acts = {}
for a in list(bpy.data.actions):
    short = a.name.split("|")[-1]
    a.name = short
    for s in a.slots:
        s.name_display = arm.name
    acts[short] = a
print("ACTIONS %d" % len(acts))

tex_map = {}
for spec in TEX_MAP:
    if "=" not in spec:
        raise SystemExit("--tex 需写成 材质名=贴图路径，实际 %s" % spec)
    k, v = spec.split("=", 1)
    if not os.path.isfile(v):
        raise SystemExit("贴图不存在：%s" % v)
    tex_map[k] = v

for slot in mesh.material_slots:
    mat = slot.material
    path = tex_map.get(mat.name)
    if path is None and TEX_DIR:
        path = find_texture(TEX_DIR, mat.name)
    if path is None:
        raise SystemExit("材质 %s 找不到贴图；用 --tex 材质名=路径 指定，或给 --tex-dir 让脚本按材质名派生候选" % mat.name)
    mat.use_nodes = True
    nt = mat.node_tree
    nt.nodes.clear()
    out = nt.nodes.new("ShaderNodeOutputMaterial")
    bsdf = nt.nodes.new("ShaderNodeBsdfPrincipled")
    tex = nt.nodes.new("ShaderNodeTexImage")
    img = bpy.data.images.load(path, check_existing=True)
    if max(img.size) > MAX_TEX:
        s = float(MAX_TEX) / max(img.size)
        img.scale(int(img.size[0] * s), int(img.size[1] * s))
    tex.image = img
    nt.links.new(tex.outputs["Color"], bsdf.inputs["Base Color"])
    nt.links.new(tex.outputs["Alpha"], bsdf.inputs["Alpha"])
    nt.links.new(bsdf.outputs["BSDF"], out.inputs["Surface"])
    mat.blend_method = 'CLIP'
    print("MAT %s %s %s" % (mat.name, path, tuple(img.size)))

data = bpy.context.scene.CMT.ExporterSettings
data.ProjectPath = PROJECT
data.UVCount = 1
data.IsTriangulation = False
data.IsExportModel = True
data.IsExportAnimation = True
data.IsGenerateRef = True
data.IsExportAst = True
data.IsExportMaterial = True
data.IsExportArtdef = False
data.OverwriteTextures = True

geo = data.GeoList.add()
geo.FileName = ASSET
geo.Class = "Unit"
geo.Geometries.add().value = mesh

ast = data.AstList.add()
ast.FileName = ASSET
ast.Class = "Unit"
ast.DSG = DSG
ast.Geometries.add().value = ASSET

if not SLOTS:
    raise SystemExit("至少给一个 --slot 槽位名=片段名")
slot_map = {}
for spec in SLOTS:
    if "=" not in spec:
        raise SystemExit("--slot 需写成 槽位名=片段名，实际 %s" % spec)
    k, v = spec.split("=", 1)
    if v not in acts:
        raise SystemExit("片段 %s 不在 FBX 里；现有：%s" % (v, sorted(acts)))
    slot_map[k] = acts[v]

assigned = 0
seen = set()
for item in ast.Animations:
    if item.text in slot_map:
        item.value = slot_map[item.text]
        assigned += 1
        seen.add(item.text)
unmatched_slots = sorted(set(slot_map) - seen)
unmatched_wanted = [item.text for item in ast.Animations if not item.value]
print("SLOTS_ASSIGNED %d" % assigned)
if unmatched_slots:
    print("SLOTS_NOT_IN_AST %s" % unmatched_slots)
print("AST_SLOTS_LEFT_EMPTY %d %s" % (len(unmatched_wanted), unmatched_wanted[:20]))

for name in sorted(acts):
    an = data.AnimationList.add()
    an.value = acts[name]
    an.Class = "Unit"

for slot in mesh.material_slots:
    ml = data.MaterialList.add()
    ml.FileName = slot.material.name
    ml.Class = "Unit"

print("LISTS geo=%d ast=%d anim=%d mat=%d" % (len(data.GeoList), len(data.AstList), len(data.AnimationList), len(data.MaterialList)))
bpy.ops.cmt.exporter_ot_automatchtextures()
bpy.ops.cmt.exporter_ot_export()
print("EXPORT_DONE")

out = []
before = os.path.getmtime(FBX)
for root, dirs, files in os.walk(PROJECT):
    for f in files:
        p = os.path.join(root, f)
        if os.path.getmtime(p) > before - 5:
            out.append([os.path.relpath(p, PROJECT), os.path.getsize(p)])
out.sort()
with open(os.path.join(os.path.dirname(FBX), "unit_export.json"), "w", encoding="utf-8") as fh:
    json.dump(out, fh, ensure_ascii=False, indent=1)
print("EXPORT_FILES %d" % len(out))
for p, s in out:
    print("  FILE %s %d" % (p, s))
print("UNIT_EXPORT_OK")
