import bpy
import bmesh
import json
import math
import os
import sys
from mathutils import Matrix

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

def arg_flag(name):
    return name in ARGV

PSK = arg("--psk")
OUT = arg("--out")
if not PSK or not OUT:
    raise SystemExit("必须给 --psk 与 --out")

TOOLS = arg("--tools", r"D:\documents\Firaxis ModBuddy\Civilization VI\Jinzhou_Jinhsi\workspace\_tools")
SCALE = float(arg("--scale", "0.01"))
DECIMATE = float(arg("--decimate", "0.28"))
TARGET = int(arg("--target-bones", "60"))
ROT_Z = float(arg("--rot-z", "90"))
FPS = int(arg("--fps", "30"))
RIG_NAME = arg("--rig-name", "UnitRig")
MESH_NAME = arg("--mesh-name", "UnitBody")
REST_ACTION = arg("--rest-action")
EXTRAS = [x for x in arg("--extras", "").split(",") if x]
EXTRA_PREFIX = arg_all("--extra-prefix")
ANIM_SPECS = arg_all("--anim")

CORE = [
    "Root", "Bip001", "Bip001Pelvis", "Bip001Spine", "Bip001Spine1", "Bip001Spine2",
    "Bip001Neck", "Bip001Head",
    "Bip001LClavicle", "Bip001LUpperArm", "Bip001LForearm", "Bip001LHand",
    "Bip001RClavicle", "Bip001RUpperArm", "Bip001RForearm", "Bip001RHand",
    "Bip001LThigh", "Bip001LCalf", "Bip001LFoot", "Bip001LToe0",
    "Bip001RThigh", "Bip001RCalf", "Bip001RFoot", "Bip001RToe0",
    "Bip001LForeTwist", "Bip001LForeTwist1", "Bip001RForeTwist", "Bip001RForeTwist1",
    "Bip001LUpArmTwist", "Bip001LUpArmTwist1", "Bip001LUpArmTwist2",
    "Bip001RUpArmTwist", "Bip001RUpArmTwist1", "Bip001RUpArmTwist2",
    "Bip001LThighTwist", "Bip001LThighTwist1", "Bip001RThighTwist", "Bip001RThighTwist1",
    "Bip001_L_Calf", "Bip001_L_CalfTwist", "Bip001_R_Calf", "Bip001_R_CalfTwist",
]

bpy.ops.wm.read_factory_settings(use_empty=True)
sys.path.insert(0, TOOLS)
import bl_bootstrap

bpy.ops.import_scene.psk(filepath=PSK)
arms = [o for o in bpy.data.objects if o.type == 'ARMATURE']
meshes = [o for o in bpy.data.objects if o.type == 'MESH']
if len(arms) != 1:
    raise SystemExit("源文件必须只有 1 副骨架，实际 %d 副；多余骨架请在 Blender 里先删掉" % len(arms))
full = arms[0]
mesh = max(meshes, key=lambda o: len(o.data.vertices))
full.name = RIG_NAME + "_Source"
mesh.name = MESH_NAME
if mesh.data.shape_keys:
    mesh.shape_key_clear()
print("IMPORT bones=%d verts=%d polys=%d" % (len(full.data.bones), len(mesh.data.vertices), len(mesh.data.polygons)))

all_bones = [b.name for b in full.data.bones]
missing_core = [b for b in CORE if b not in all_bones]
if missing_core:
    raise SystemExit("源骨架缺少核心骨，无法继续：%s" % missing_core)

keep = [b for b in CORE if b in all_bones]

# 附属骨：先取显式 --extras，再按 --extra-prefix 顺序补足到 --target-bones
for name in EXTRAS:
    if name in all_bones and name not in keep:
        keep.append(name)
remaining = TARGET - len(keep)
if remaining > 0 and EXTRA_PREFIX:
    for prefix in EXTRA_PREFIX:
        for name in all_bones:
            if remaining <= 0:
                break
            if name in keep or not name.startswith(prefix):
                continue
            keep.append(name)
            remaining -= 1
    if remaining > 0:
        raise SystemExit("按 --extra-prefix 补骨后仍差 %d 根到 %d；请补 --extras 或调整前缀" % (remaining, TARGET))
if len(keep) > TARGET:
    raise SystemExit("保留骨 %d 根超过上限 %d；请缩减 --extras 或前缀" % (len(keep), TARGET))
if len(keep) < TARGET and not EXTRA_PREFIX:
    raise SystemExit("保留骨只有 %d 根，不足 %d；请给 --extras 或 --extra-prefix 补足" % (len(keep), TARGET))
keep_set = set(keep)
print("KEEP_BONES %d" % len(keep))

scale = Matrix.Scale(SCALE, 4)
full.data.transform(scale)
mesh.data.transform(scale)
mesh.matrix_world = Matrix.Identity(4)
bpy.context.view_layer.update()
print("SCALE %s" % (tuple(round(v, 4) for v in mesh.dimensions),))

parent = {b.name: (b.parent.name if b.parent else None) for b in full.data.bones}

def nearest_kept(name):
    p = parent[name]
    while p and p not in keep_set:
        p = parent[p]
    return p

target_name = {}
for g in mesh.vertex_groups:
    target_name[g.index] = g.name if g.name in keep_set else nearest_kept(g.name)

stored = []
for v in mesh.data.vertices:
    acc = {}
    for ge in v.groups:
        name = target_name.get(ge.group)
        if name is None:
            continue
        acc[name] = acc.get(name, 0.0) + ge.weight
    s = sum(acc.values())
    if s <= 0:
        raise SystemExit("顶点 %d 没有任何保留骨权重，权重重定向有遗漏" % v.index)
    for name in list(acc):
        acc[name] /= s
    stored.append(acc)

mesh.vertex_groups.clear()
for name in sorted(keep_set):
    mesh.vertex_groups.new(name=name)
name_to_index = {g.name: g.index for g in mesh.vertex_groups}
bm = bmesh.new()
bm.from_mesh(mesh.data)
dl = bm.verts.layers.deform.verify()
bm.verts.ensure_lookup_table()
for v, acc in zip(bm.verts, stored):
    d = v[dl]
    d.clear()
    for name, w in acc.items():
        d[name_to_index[name]] = w
bm.to_mesh(mesh.data)
bm.free()
print("WEIGHTS verts=%d groups=%d" % (len(stored), len(mesh.vertex_groups)))

for m in list(mesh.modifiers):
    if m.type == 'ARMATURE':
        mesh.modifiers.remove(m)
mod = mesh.modifiers.new(name="UnitDecimate", type='DECIMATE')
mod.decimate_type = 'COLLAPSE'
mod.ratio = DECIMATE
mod.use_collapse_triangulate = True
bpy.context.view_layer.objects.active = mesh
mesh.select_set(True)
bpy.ops.object.modifier_apply(modifier=mod.name)
print("DECIMATE verts=%d polys=%d" % (len(mesh.data.vertices), len(mesh.data.polygons)))

hier = []
def walk(b):
    hier.append(b.name)
    for c in b.children:
        walk(c)
for b in full.data.bones:
    if b.parent is None:
        walk(b)

reduced = full.copy()
reduced.data = full.data.copy()
reduced.name = RIG_NAME
bpy.context.scene.collection.objects.link(reduced)
bpy.context.view_layer.objects.active = reduced
bpy.ops.object.mode_set(mode='EDIT')
for b in list(reduced.data.edit_bones):
    if b.name not in keep_set:
        reduced.data.edit_bones.remove(b)
for b in reduced.data.edit_bones:
    if b.name == "Root":
        continue
    reduced.data.edit_bones[b.name].parent = reduced.data.edit_bones.get(nearest_kept(b.name))
bpy.ops.object.mode_set(mode='OBJECT')
print("REDUCED_BONES %d" % len(reduced.data.bones))
if len(reduced.data.bones) != TARGET:
    raise SystemExit("缩减后骨数为 %d，与目标 %d 不符" % (len(reduced.data.bones), TARGET))

ROT = Matrix.Rotation(math.radians(ROT_Z), 4, 'Z')
if abs(ROT_Z) > 1e-9:
    bpy.ops.object.mode_set(mode='EDIT')
    for eb_ in reduced.data.edit_bones:
        eb_.matrix = ROT @ eb_.matrix
    bpy.ops.object.mode_set(mode='OBJECT')
    mesh.data.transform(ROT)
    bpy.context.view_layer.update()
    print("ROT_Z_DONE deg=%s" % ROT_Z)

mesh.parent = reduced
mesh.matrix_parent_inverse = reduced.matrix_world.inverted()
amod = mesh.modifiers.new(name="Armature", type='ARMATURE')
amod.object = reduced

full.hide_set(True)
full.hide_render = True

bpy.context.scene.render.fps = FPS
for b in full.data.bones:
    local = b.matrix_local if b.parent is None else b.parent.matrix_local.inverted() @ b.matrix_local
    loc, quat, _ = local.decompose()
    b["orig_loc"] = loc
    b["orig_quat"] = quat.conjugated()
    b["post_quat"] = quat
print("REST_PROPS %d" % len(full.data.bones))

def import_action(path):
    before = set(bpy.data.actions)
    bpy.ops.object.select_all(action='DESELECT')
    full.select_set(True)
    bpy.context.view_layer.objects.active = full
    bpy.ops.uf.import_ueanim(directory=os.path.dirname(path), files=[{'name': os.path.basename(path)}])
    new = [a for a in bpy.data.actions if a not in before]
    if len(new) != 1:
        raise SystemExit("导入 %s 得到 %d 个动作，应为 1" % (path, len(new)))
    act = new[0]
    full.animation_data_create()
    full.animation_data.action = act
    return act

if REST_ACTION:
    rest_src = import_action(REST_ACTION)
    full.animation_data.action = rest_src
    if bpy.app.version >= (4, 4, 0) and rest_src.slots:
        full.animation_data.action_slot = rest_src.slots[0]
    bpy.context.scene.frame_set(int(rest_src.frame_range[0]))
    bpy.context.view_layer.update()
    rest_world = {n: (ROT @ full.pose.bones[n].matrix) for n in hier if n in full.pose.bones}
    full.animation_data.action = None
    for pb in full.pose.bones:
        pb.matrix_basis.identity()
    bpy.context.view_layer.update()
    bpy.ops.object.select_all(action='DESELECT')
    reduced.select_set(True)
    bpy.context.view_layer.objects.active = reduced
    bpy.ops.object.mode_set(mode='EDIT')
    for name, m in rest_world.items():
        if name in reduced.data.edit_bones:
            reduced.data.edit_bones[name].matrix = m
    bpy.ops.object.mode_set(mode='OBJECT')
    bpy.context.view_layer.update()
    print("REST_FROM_ACTION %s" % REST_ACTION)

def bake(src_act, name):
    start = int(round(src_act.frame_range[0]))
    end = int(round(src_act.frame_range[1]))
    reduced.animation_data_create()
    new_act = bpy.data.actions.new(name)
    reduced.animation_data.action = new_act
    for pb in reduced.pose.bones:
        pb.rotation_mode = 'QUATERNION'
    rest = {b.name: b.matrix_local.copy() for b in reduced.data.bones}
    for f in range(start, end + 1):
        full.animation_data.action = src_act
        bpy.context.scene.frame_set(f)
        bpy.context.view_layer.update()
        world = {}
        for bname in hier:
            if bname not in reduced.pose.bones:
                continue
            par = reduced.data.bones[bname].parent
            m = ROT @ full.pose.bones[bname].matrix
            if par is None and bname == "Root":
                m = rest[bname].copy()
                m.translation.x = 0.0
                m.translation.y = 0.0
            if par is None:
                basis = rest[bname].inverted() @ m
            else:
                basis = (rest[par.name].inverted() @ rest[bname]).inverted() @ (world[par.name].inverted() @ m)
            world[bname] = m
            db = reduced.pose.bones[bname]
            db.matrix_basis = basis
            db.keyframe_insert(data_path="location", frame=f, group=bname)
            db.keyframe_insert(data_path="rotation_quaternion", frame=f, group=bname)
            db.keyframe_insert(data_path="scale", frame=f, group=bname)
    new_act.frame_start = start
    new_act.frame_end = end
    for slot in new_act.slots:
        slot.name_display = RIG_NAME
    print("BAKED %s %d %d" % (name, start, end))
    return new_act

if not ANIM_SPECS:
    raise SystemExit("至少给一个 --anim SLOT=动画文件路径")

actions = {}
for spec in ANIM_SPECS:
    if "=" not in spec:
        raise SystemExit("--anim 需写成 SLOT=路径，实际 %s" % spec)
    slot, path = spec.split("=", 1)
    if not os.path.isfile(path):
        raise SystemExit("动作文件不存在：%s" % path)
    src = import_action(path)
    actions[slot] = bake(src, slot)

reduced.animation_data.action = None
full.animation_data.action = None
for pb in reduced.pose.bones:
    pb.matrix_basis.identity()
bpy.context.view_layer.update()

ad = reduced.animation_data
for slot in sorted(actions):
    a = actions[slot]
    track = ad.nla_tracks.new()
    track.name = a.name
    strip = track.strips.new(a.name, int(a.frame_range[0]), a)
    strip.name = a.name
print("NLA_TRACKS %d" % len(ad.nla_tracks))

bpy.ops.object.select_all(action='DESELECT')
reduced.select_set(True)
mesh.select_set(True)
bpy.context.view_layer.objects.active = reduced
os.makedirs(OUT, exist_ok=True)
fbx = os.path.join(OUT, RIG_NAME + ".fbx")
bpy.ops.export_scene.fbx(
    filepath=fbx,
    use_selection=True,
    object_types={'ARMATURE', 'MESH'},
    apply_unit_scale=False,
    global_scale=1.0,
    axis_forward='-Z',
    axis_up='Y',
    bake_anim=True,
    bake_anim_simplify_factor=0.0,
    add_leaf_bones=False,
    bake_anim_use_nla_strips=True,
    bake_anim_use_all_actions=False,
    mesh_smooth_type='OFF',
    use_mesh_modifiers=True,
)

summary = {
    "fbx": fbx,
    "rig": RIG_NAME,
    "bones": len(reduced.data.bones),
    "vertices": len(mesh.data.vertices),
    "polygons": len(mesh.data.polygons),
    "dimensions": [round(v, 4) for v in mesh.dimensions],
    "rot_z_deg": ROT_Z,
    "fps": FPS,
    "actions": {k: [int(v.frame_start), int(v.frame_end)] for k, v in actions.items()},
}
with open(os.path.join(OUT, "unit_build.json"), "w", encoding="utf-8") as fh:
    json.dump(summary, fh, ensure_ascii=False, indent=1)
print("FBX_EXPORTED %s %d" % (fbx, os.path.getsize(fbx)))
print("UNIT_BUILD_OK")
