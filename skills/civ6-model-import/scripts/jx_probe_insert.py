import bpy
import math
import os
import sys

PSK = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\R2T1JinxiMd10011\Model\R2T1JinxiMd10011.psk"
CLIP_DIR = r"G:\Wuwa_3D_Assets\Characters\角色_Jinxi\converted\Client\Content\Aki\Character\Role\FemaleM\Jinxi\CommonAnim"
CLIP = "Stand1_Action01"
LAST = 130

bpy.ops.object.select_all(action='SELECT')
bpy.ops.object.delete(use_global=False)
bpy.ops.import_scene.psk(filepath=PSK)
arm = [o for o in bpy.data.objects if o.type == 'ARMATURE'][0]
bpy.ops.object.select_all(action='DESELECT')
arm.select_set(True)
bpy.context.view_layer.objects.active = arm
bpy.ops.uf.import_ueanim(directory=CLIP_DIR, files=[{'name': CLIP + '.ueanim'}])
act = [a for a in bpy.data.actions if a.name.startswith(CLIP)]
print("PROBE_ACTIONS", [a.name for a in bpy.data.actions][:6], "range", tuple(act[0].frame_range) if act else None)
arm.animation_data.action = act[0]

prev = None
rows = []
for f in range(1, LAST + 1):
    bpy.context.scene.frame_set(f)
    bpy.context.view_layer.update()
    head = arm.pose.bones["Bip001Head"].matrix.to_translation()
    hand = arm.pose.bones["Bip001RHand"].matrix.to_translation()
    lhand = arm.pose.bones["Bip001LHand"].matrix.to_translation()
    cur = {pb.name: pb.rotation_quaternion.copy() for pb in arm.pose.bones}
    worst = 0.0
    if prev is not None:
        for name, q in cur.items():
            p = prev.get(name)
            if p is None:
                continue
            ang = math.degrees(2.0 * math.acos(min(1.0, abs(q.dot(p)))))
            worst = max(worst, ang)
        dh = (hand - prev_hand).length
        dl = (lhand - prev_lhand).length
        rows.append((f, worst, dh, dl))
    prev = cur
    prev_hand, prev_lhand = hand.copy(), lhand.copy()

for f, w, dh, dl in rows:
    print("PROBE %d ang=%.2f hand=%.2f lhand=%.2f" % (f, w, dh, dl))
