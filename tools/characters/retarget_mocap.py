"""Mathematically exact CMU BVH optical MoCap retargeter for MPFB2 `game_engine` rigs.

Converts 120 Hz CMU Vicon BVH clips (Y-up, +Z forward, +X left, T-pose) into seamless
30 fps looping Blender actions on MPFB2's 53-bone `game_engine` skeleton (Z-up, -Y forward,
+X left, A-pose with 42-deg pre-bent elbows), measuring exact metric stride length and
ground-locking stance shoes to Z = 0.000 m.
"""
import math
from pathlib import Path

import bpy
import numpy as np
from mathutils import Euler, Matrix, Quaternion, Vector


# Pure rigid rotation (+90 deg around +X, det=+1): CMU (+X left, +Y up, +Z fwd) -> Blender (+X left, -Y fwd, +Z up).
M_BVH_TO_BL = np.array([
    [1.0,  0.0, 0.0],
    [0.0,  0.0, -1.0],
    [0.0,  1.0, 0.0],
], dtype=np.float64)


def _rx(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[1.0, 0.0, 0.0], [0.0, c, -s], [0.0, s, c]], dtype=np.float64)


def _ry(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, 0.0, s], [0.0, 1.0, 0.0], [-s, 0.0, c]], dtype=np.float64)


def _rz(a: float) -> np.ndarray:
    c, s = math.cos(a), math.sin(a)
    return np.array([[c, -s, 0.0], [s, c, 0.0], [0.0, 0.0, 1.0]], dtype=np.float64)


def _norm(v: np.ndarray) -> np.ndarray:
    n = float(np.linalg.norm(v))
    return v / n if n > 1e-8 else np.array([0.0, 0.0, 1.0], dtype=np.float64)


def _make_frame(primary: np.ndarray, hint: np.ndarray) -> np.ndarray:
    """Right-handed orthonormal frame [X, Y=primary, Z=ortho(hint)] as 3x3 matrix (det = +1)."""
    y = _norm(primary)
    z = hint - np.dot(hint, y) * y
    if np.linalg.norm(z) < 1e-5:
        alt = np.array([0.0, -1.0, 0.0]) if abs(y[1]) < 0.9 else np.array([1.0, 0.0, 0.0])
        z = alt - np.dot(alt, y) * y
    z = _norm(z)
    x = _norm(np.cross(y, z))
    z = np.cross(x, y)
    return np.column_stack([x, y, z])


def parse_bvh(path: Path):
    lines = path.read_text(encoding="utf-8", errors="ignore").splitlines()
    joints, stack = [], []
    i = 0
    ch_off = 0
    while i < len(lines):
        s = lines[i].strip()
        if s.startswith(("ROOT ", "JOINT ")):
            joints.append({
                "name": s.split()[1],
                "parent": stack[-1] if stack else -1,
                "children": [],
                "offset": np.zeros(3, dtype=np.float64),
                "channels": [],
                "ch_off": ch_off,
                "end": None,
            })
            idx = len(joints) - 1
            if stack:
                joints[stack[-1]]["children"].append(idx)
            stack.append(idx)
        elif s.startswith("End Site"):
            i += 1
            while not lines[i].strip().startswith("OFFSET"):
                i += 1
            joints[stack[-1]]["end"] = np.array([float(x) for x in lines[i].strip().split()[1:4]], dtype=np.float64)
            while not lines[i].strip().startswith("}"):
                i += 1
        elif s.startswith("OFFSET"):
            joints[stack[-1]]["offset"] = np.array([float(x) for x in s.split()[1:4]], dtype=np.float64)
        elif s.startswith("CHANNELS"):
            parts = s.split()
            joints[stack[-1]]["channels"] = parts[2:]
            joints[stack[-1]]["ch_off"] = ch_off
            ch_off += int(parts[1])
        elif s == "}":
            stack.pop()
        elif s == "MOTION":
            i += 1
            break
        i += 1
    _nframes = int(lines[i].split(":")[1].strip())
    i += 1
    ftime = float(lines[i].split(":")[1].strip())
    i += 1
    data = np.array([[float(x) for x in l.split()] for l in lines[i:] if l.strip()], dtype=np.float64)
    return joints, ftime, data


def eval_bvh_fk(joints, data: np.ndarray, frame_indices: list[int]):
    """Evaluate world-space joint positions & rotation matrices in Blender space (+X left, -Y fwd, +Z up)."""
    nf = len(frame_indices)
    nj = len(joints)
    pos = np.zeros((nf, nj, 3), dtype=np.float64)
    rot = np.zeros((nf, nj, 3, 3), dtype=np.float64)
    for fi, src_f in enumerate(frame_indices):
        row = data[src_f]
        for ji, j in enumerate(joints):
            ch = j["channels"]
            o = j["ch_off"]
            t = j["offset"].copy()
            R = np.eye(3, dtype=np.float64)
            for k, c in enumerate(ch):
                v = row[o + k]
                if c == "Xposition":
                    t[0] += v
                elif c == "Yposition":
                    t[1] += v
                elif c == "Zposition":
                    t[2] += v
                elif c == "Xrotation":
                    R = R @ _rx(math.radians(v))
                elif c == "Yrotation":
                    R = R @ _ry(math.radians(v))
                elif c == "Zrotation":
                    R = R @ _rz(math.radians(v))
            p = j["parent"]
            if p < 0:
                pos[fi, ji] = t
                rot[fi, ji] = R
            else:
                pos[fi, ji] = pos[fi, p] + rot[fi, p] @ t
                rot[fi, ji] = rot[fi, p] @ R

    # Rotate whole clip from CMU space into Blender space.
    pos_bl = np.einsum("ij,fnj->fni", M_BVH_TO_BL, pos)
    rot_bl = np.einsum("ij,fnjk,lk->fnil", M_BVH_TO_BL, rot, M_BVH_TO_BL)
    return pos_bl, rot_bl


# Canonical bone mapping: MPFB2 game_engine bone -> (CMU BVH joint, child for direction or None, frame mode)
# Modes:
#   "world" : neutral standing orientation aligns directly (pelvis, spine, neck, head)
#   "limb"  : align bone length vector + forward (-Y) hint (thigh, calf, clavicle, upperarm)
#   "foot"  : align bone length vector + up (+Z) hint (foot, ball)
#   "elbow_l" / "elbow_r" : align forearm/hand vector + true anatomical elbow hinge axis
BONE_MAP = [
    ("pelvis",      "Hips",           None,            "world"),
    ("spine_01",    "LowerBack",      None,            "world"),
    ("spine_02",    "Spine",          None,            "world"),
    ("spine_03",    "Spine1",         None,            "world"),
    ("neck_01",     "Neck1",          None,            "world"),
    ("head",        "Head",           None,            "world"),
    ("clavicle_l",  "LeftShoulder",   "LeftArm",       "limb"),
    ("upperarm_l",  "LeftArm",        "LeftForeArm",   "limb"),
    ("lowerarm_l",  "LeftForeArm",    "LeftHand",      "elbow_l"),
    ("hand_l",      "LeftHand",       "LeftHandIndex1","elbow_l"),
    ("clavicle_r",  "RightShoulder",  "RightArm",      "limb"),
    ("upperarm_r",  "RightArm",       "RightForeArm",  "limb"),
    ("lowerarm_r",  "RightForeArm",   "RightHand",     "elbow_r"),
    ("hand_r",      "RightHand",      "RightHandIndex1","elbow_r"),
    ("thigh_l",     "LeftUpLeg",      "LeftLeg",       "limb"),
    ("calf_l",      "LeftLeg",        "LeftFoot",      "limb"),
    ("foot_l",      "LeftFoot",       "LeftToeBase",   "foot"),
    ("ball_l",      "LeftToeBase",    None,            "foot"),
    ("thigh_r",     "RightUpLeg",     "RightLeg",      "limb"),
    ("calf_r",      "RightLeg",       "RightFoot",     "limb"),
    ("foot_r",      "RightFoot",      "RightToeBase",  "foot"),
    ("ball_r",      "RightToeBase",   None,            "foot"),
]


def _src_bone_dir_bl(joints, jidx, src_name: str, child_name):
    j = joints[jidx[src_name]]
    v = None
    if child_name and child_name in jidx and np.linalg.norm(joints[jidx[child_name]]["offset"]) > 1e-5:
        v = joints[jidx[child_name]]["offset"]
    else:
        # Walk BFS through descendants for the first non-zero offset (skips zero-offset CMU dummies like LeftFingerBase).
        queue = list(j["children"])
        while queue:
            ci = queue.pop(0)
            if np.linalg.norm(joints[ci]["offset"]) > 1e-5:
                v = joints[ci]["offset"]
                break
            queue.extend(joints[ci]["children"])
    if v is None and j["end"] is not None and np.linalg.norm(j["end"]) > 1e-5:
        v = j["end"]
    if v is None:
        v = np.array([0.0, 0.0, 1.0])
    return _norm(M_BVH_TO_BL @ v)


def _dst_bone_dir_bl(rig, bone_name: str):
    b = rig.data.bones[bone_name]
    v = np.array(b.tail_local - b.head_local, dtype=np.float64)
    return _norm(v)


def _swing_twist_y(q: Quaternion) -> Quaternion:
    """Extract the axial twist component of a bone-local pose quaternion around local +Y."""
    mag = math.hypot(q.w, q.y)
    if mag < 1e-6:
        return Quaternion((1.0, 0.0, 0.0, 0.0))
    tw = Quaternion((q.w / mag, 0.0, q.y / mag, 0.0))
    if tw.w < 0.0:
        tw = -tw
    return tw


def _cyclic_smooth(arr: np.ndarray, radius: int = 4) -> np.ndarray:
    """Apply a smooth cyclic Gaussian-like kernel to a periodic length-(N+1) curve (arr[N] == arr[0])."""
    n = len(arr) - 1
    if n <= 2:
        return arr.copy()
    core = arr[:n]
    ks = np.arange(-radius, radius + 1)
    w = np.exp(-0.5 * (ks / max(radius * 0.5, 1.0)) ** 2)
    w /= w.sum()
    out = np.zeros(n, dtype=np.float64)
    for k, wk in zip(ks, w):
        out += wk * np.roll(core, -int(k))
    return np.concatenate([out, out[:1]])


def _measure_body_hip_clearance(rig, meshes: list) -> tuple[float, dict, float, dict, float]:
    """Measure target character's equipped hip/thigh lateral half-width (excluding asymmetric bags!), depth by height,
    thigh radius, a right-hip bag's reach by slice fore and aft, and flank half-width between waist and armpit."""
    pelvis_z = float(rig.data.bones["pelvis"].head_local.z)
    knee_z = float(rig.data.bones["calf_l"].head_local.z)
    z_lo = knee_z + 0.06
    z_hi = pelvis_z + 0.14
    xs, flank_xs = [], []
    # How far the outfit reaches before and behind the pelvis, by 4 cm of height: a flared hem stands well before the
    # belt above it. One depth for the whole hip held every hand out that swung past the belt, 30 cm before it.
    depth = {}
    # The bag's reach to the right in each 2 cm slice fore and aft of the pelvis: an arm hanging before or behind it
    # owes it nothing. One reach for the whole bag held the arm out wherever the hand hung level with it.
    bag_reach = {}
    pelvis_y = float(rig.data.bones["pelvis"].head_local.y)
    for obj in meshes:
        lname = obj.name.lower()
        if any(k in lname for k in ("eye", "hair", "brow", "lash", "shoe", "boot", "strap", "belt")):
            continue
        is_bag = "satchel" in lname or "bag" in lname
        arm_groups = {vg.index for vg in obj.vertex_groups if "arm" in vg.name or "hand" in vg.name}
        mw = obj.matrix_world
        for v in obj.data.vertices:
            co = mw @ v.co
            if is_bag:
                if co.x < -0.10 and z_lo - 0.05 <= co.z <= z_hi:
                    fore = math.floor((pelvis_y - co.y) / 0.02)
                    bag_reach[fore] = max(bag_reach.get(fore, 0.0), min(abs(co.x), 0.30))
            elif z_lo <= co.z <= z_hi and abs(co.x) < 0.30:
                xs.append(abs(co.x))
                depth.setdefault(math.floor((co.z - pelvis_z) / 0.04), []).append(pelvis_y - co.y)
            # At a hanging elbow's height, what the arms do not carry is the flank: a sleeve's skin weights tell it
            # from the side panel it hangs beside, where no distance does.
            elif z_hi < co.z <= pelvis_z + 0.28 and sum(g.weight for g in v.groups if g.group in arm_groups) < 0.3:
                flank_xs.append(abs(co.x))
    hip_half_x = float(np.percentile(xs, 95)) if xs else 0.195
    hip_depth = {k: (float(np.percentile(v, 95)), float(-np.percentile(v, 5))) for k, v in depth.items()}  # fore, aft
    # Cap hip half-width cleanly so jacket skirt folds never force arms into an unnatural A-pose!
    hip_half_x = min(hip_half_x, 0.215)
    thigh_r = max(0.095, min(0.135, hip_half_x * 0.56))
    flank_half_x = float(np.percentile(flank_xs, 95)) if flank_xs else hip_half_x
    return hip_half_x, hip_depth, thigh_r, bag_reach, flank_half_x


def _pt_seg_dist(p: Vector, a: Vector, b: Vector) -> float:
    ab = b - a
    l2 = ab.length_squared
    if l2 < 1e-8:
        return (p - a).length
    t = max(0.0, min(1.0, (p - a).dot(ab) / l2))
    return (p - (a + ab * t)).length


def _lift_foot(rig, side: str, dz: float, quats: dict, fi: int, M_rest_local: dict):
    """Raise a foot's joint by dz with two-bone IK on its leg, the knee bending in its own plane; the foot keeps its
    orientation. Reads the current pose, writes frame fi's thigh, calf and foot rotations."""
    pbs = rig.pose.bones
    th, ca, ft = (pbs[f"{b}_{side}"] for b in ("thigh", "calf", "foot"))
    H, K, A = (np.array(p.head, dtype=np.float64) for p in (th, ca, ft))
    l1, l2 = float(np.linalg.norm(K - H)), float(np.linalg.norm(A - K))
    to_t = A + np.array([0.0, 0.0, dz]) - H
    d = float(np.clip(np.linalg.norm(to_t), abs(l1 - l2) + 1e-4, (l1 + l2) * 0.999))
    e = to_t / float(np.linalg.norm(to_t))
    pole = (K - H) - e * float((K - H) @ e)
    if np.linalg.norm(pole) < 1e-6:  # a straight leg bends its knee forward
        pole = np.array([0.0, -1.0, 0.0]) - e * float(-e[1])
    pole /= float(np.linalg.norm(pole))
    cos_a = float(np.clip((l1 * l1 + d * d - l2 * l2) / (2.0 * l1 * d), -1.0, 1.0))
    K2 = H + l1 * (cos_a * e + math.sqrt(1.0 - cos_a * cos_a) * pole)
    A2 = H + e * d
    R1 = np.array(Vector((K - H).tolist()).rotation_difference(Vector((K2 - H).tolist())).to_matrix(), dtype=np.float64)
    R2 = np.array(Vector((R1 @ (A - K)).tolist()).rotation_difference(Vector((A2 - K2).tolist())).to_matrix(), dtype=np.float64)
    R_pel = np.array(pbs["pelvis"].matrix.to_3x3(), dtype=np.float64)
    R_th = R1 @ np.array(th.matrix.to_3x3(), dtype=np.float64)
    R_ca = R2 @ R1 @ np.array(ca.matrix.to_3x3(), dtype=np.float64)
    R_ft = np.array(ft.matrix.to_3x3(), dtype=np.float64)
    for name, R_par, R in ((f"thigh_{side}", R_pel, R_th), (f"calf_{side}", R_th, R_ca), (f"foot_{side}", R_ca, R_ft)):
        q = Matrix((M_rest_local[name].T @ R_par.T @ R).tolist()).to_quaternion().normalized()
        if fi > 0 and quats[name][fi - 1].dot(q) < 0.0:
            q = -q
        quats[name][fi] = q


def _plant_feet(rig, mapped_names: list, quats: dict, pelvis_locs: list, pelvis_rest_inv, M_rest_local: dict,
                walking: bool) -> float:
    """Keep the feet that bear weight on the ground at every frame; return the largest correction, in cm.

    A sole's height is the lower of its ankle's and ball's heights over their rest heights: the rest pose stands on the
    ground, every sole flat. Standing, both feet bear weight; walking, a foot does while it is within 2 cm of its lowest.
    The pelvis settles by the highest bearing foot's gap, smoothed around the loop, and a foot then below the ground
    lifts by bending its leg.
    """
    pbs, rb = rig.pose.bones, rig.data.bones
    rest_h = {s: (rb[f"foot_{s}"].head_local.z, rb[f"ball_{s}"].head_local.z) for s in "lr"}
    n = len(pelvis_locs)

    def pose(fi):
        for name in mapped_names:
            pbs[name].rotation_mode = "QUATERNION"
            pbs[name].rotation_quaternion = quats[name][fi]
        pbs["pelvis"].location = pelvis_locs[fi]
        bpy.context.view_layer.update()

    def soles():
        return {s: min(pbs[f"foot_{s}"].head.z - rest_h[s][0], pbs[f"ball_{s}"].head.z - rest_h[s][1]) for s in "lr"}

    heights = []
    for fi in range(n):
        pose(fi)
        heights.append(soles())
    h = {s: np.array([x[s] for x in heights]) for s in "lr"}
    bear = {s: (np.clip((0.025 - (h[s] - h[s].min())) / 0.02, 0.0, 1.0) if walking else np.ones(n)) for s in "lr"}
    drop = np.array([max(bear[s][fi] * h[s][fi] for s in "lr") for fi in range(n)])
    drop = _cyclic_smooth(drop, radius=2)
    worst = float(np.abs(drop).max())
    for fi in range(n - 1):
        pelvis_locs[fi] = pelvis_locs[fi] + Vector((pelvis_rest_inv @ np.array([0.0, 0.0, -drop[fi]])).tolist())
        pose(fi)
        for s, h in soles().items():
            if h < -1e-4:
                worst = max(worst, -h)
                _lift_foot(rig, s, -h, quats, fi, M_rest_local)
    pelvis_locs[-1] = pelvis_locs[0].copy()
    for name in mapped_names:
        quats[name][-1] = quats[name][0].copy()
    return worst * 100.0


def _enforce_arm_body_clearance(rig, meshes: list, mapped_names: list, quats: dict, pelvis_locs: list):
    """Universal self-collision solver: prevents hands/forearms from penetrating thighs, hips, pockets, or jackets."""
    hip_half_x, hip_depth, thigh_r, bag_reach, flank_half_x = _measure_body_hip_clearance(rig, meshes)

    def depth_at(fwd: float, z: float) -> float:
        """How far the outfit reaches on this point's side, fore or aft, at its height; above the hips, the waist's."""
        fore, aft = hip_depth.get(math.floor(z / 0.04)) or hip_depth[max(hip_depth) if z > 0.0 else min(hip_depth)]
        return fore if fwd > 0.0 else aft

    hand_margin = 0.036
    thigh_clear = thigh_r + 0.042
    n_frames = len(pelvis_locs)

    # Reset unrelated bones before probing.
    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
        pb.location = Vector((0.0, 0.0, 0.0))

    raw_abd = {"l": np.zeros(n_frames, dtype=np.float64), "r": np.zeros(n_frames, dtype=np.float64)}
    cached_arm_mats = {"l": [], "r": []}
    cached_torso_fwd = []

    for fi in range(n_frames):
        for name in mapped_names:
            rig.pose.bones[name].rotation_quaternion = quats[name][fi]
        rig.pose.bones["pelvis"].location = pelvis_locs[fi]
        bpy.context.view_layer.update()

        pb_pelv = rig.pose.bones["pelvis"]
        pb_sp3 = rig.pose.bones["spine_03"]
        p_org = pb_pelv.head.copy()
        # Character horizontal heading frame from pelvis world matrix (local +X is left, +Z is forward -Y).
        p_mat = pb_pelv.matrix.to_3x3()
        p_left = Vector((p_mat.col[0].x, p_mat.col[0].y, 0.0))
        p_left = p_left.normalized() if p_left.length > 1e-4 else Vector((1.0, 0.0, 0.0))
        p_fwd = Vector((0.0, 0.0, 1.0)).cross(p_left).normalized()  # wait: Z x (+X) = +Y (back), so flip:
        p_fwd = p_left.cross(Vector((0.0, 0.0, 1.0))).normalized()  # (+X) x (+Z) = (0, -1, 0) = forward!
        torso_fwd = pb_sp3.matrix.to_3x3().col[2].normalized()
        cached_torso_fwd.append(torso_fwd)

        for side in ("l", "r"):
            pb_ua = rig.pose.bones[f"upperarm_{side}"]
            pb_la = rig.pose.bones[f"lowerarm_{side}"]
            pb_ha = rig.pose.bones[f"hand_{side}"]
            pb_th = rig.pose.bones[f"thigh_{side}"]
            cached_arm_mats[side].append(pb_ua.matrix.to_3x3().copy())

            sh_pos = pb_ua.head.copy()
            probe_pts = [
                pb_la.head.lerp(pb_la.tail, 0.65),
                pb_ha.head.copy(),
                pb_ha.head.lerp(pb_ha.tail, 0.75),
            ]
            max_pen = 0.0
            max_ang = 0.0
            eff_len = max((pb_ha.head - sh_pos).length, 0.30)
            for pt in probe_pts:
                rel = pt - p_org
                # Only apply body/hip/thigh clearance when arm point is below shoulder and above mid-calf.
                if rel.z > 0.36 or rel.z < -0.52:
                    continue
                lat = rel.dot(p_left) if side == "l" else rel.dot(-p_left)
                fwd = rel.dot(p_fwd)
                # 1. Pelvis / hip / jacket lateral clearance (covers "hands inside pockets" & hip clipping).
                # The hips' outline is rounded: a hand before or behind them needs less room to the side, and none
                # once past them. Held to their full width over their whole depth, it swung wide at each step.
                across = abs(fwd) / (depth_at(fwd, rel.z) + hand_margin)
                if across < 1.0 and -0.28 < rel.z < 0.24:
                    z_scale = 1.0 if rel.z <= 0.08 else max(0.84, 1.0 - (rel.z - 0.08) * 0.7)
                    req_lat = (hip_half_x * z_scale + hand_margin) * (1.0 - across ** 3) ** (1.0 / 3.0)
                    if side == "r" and -0.26 < rel.z < 0.02:
                        req_lat = max(req_lat, bag_reach.get(math.floor(fwd / 0.02), 0.0) + 0.022)
                    if lat < req_lat and lat > -0.06:
                        max_pen = max(max_pen, req_lat - lat)
                # 2. Thigh capsule clearance (prevents hand/fingers clipping into front/side of thigh).
                d_th = _pt_seg_dist(pt, pb_th.head, pb_th.tail)
                if d_th < thigh_clear and lat > -0.05:
                    max_pen = max(max_pen, thigh_clear - d_th)

            # 3. The elbow rests beside the garment's flank: a sleeve that hangs straight down from the shoulder
            # grazes a jacket's side, and two wrinkled cloths that graze cross in shards. The elbow keeps 3 cm off
            # the flank, on its own lever about the shoulder; above it the sleeve presses into the armpit, as cloth
            # does. Held clear along its whole length, the arm stands out like a rest pose.
            pt = pb_la.head
            rel = pt - p_org
            lat = rel.dot(p_left) if side == "l" else rel.dot(-p_left)
            if 0.10 < rel.z < 0.42 and abs(rel.dot(p_fwd)) < depth_at(rel.dot(p_fwd), rel.z) + 0.070 and lat > -0.06:
                max_ang = max(max_ang, math.atan2(flank_half_x + 0.030 - lat, max((pt - sh_pos).length, 0.12)))

            max_ang = max(max_ang, math.atan2(max_pen, eff_len))
            if max_ang > 1e-4:
                raw_abd[side][fi] = min(math.radians(18.0), max_ang)

    # Smooth outward clearance cyclically so arm motion stays fluid with zero popping.
    max_applied = 0.0
    for side in ("l", "r"):
        if float(raw_abd[side].max()) <= 1e-4:
            continue
        # Preserve peak clearance while smoothing ramps using dilated + smoothed envelope.
        smooth = _cyclic_smooth(raw_abd[side], radius=5)
        envelope = np.maximum(raw_abd[side], smooth)
        envelope = _cyclic_smooth(envelope, radius=3)
        max_applied = max(max_applied, float(math.degrees(envelope.max())))
        ua_name = f"upperarm_{side}"
        sgn = 1.0 if side == "l" else -1.0
        for fi in range(n_frames):
            ang = float(envelope[fi])
            if ang <= 1e-5:
                continue
            r_abd = Matrix.Rotation(sgn * ang, 3, cached_torso_fwd[fi])
            r_w = cached_arm_mats[side][fi]
            r_pose_old = quats[ua_name][fi].to_matrix()
            r_pose_new = r_pose_old @ r_w.inverted() @ r_abd @ r_w
            q_new = r_pose_new.to_quaternion().normalized()
            if fi > 0 and quats[ua_name][fi - 1].dot(q_new) < 0.0:
                q_new = -q_new
            quats[ua_name][fi] = q_new
    return max_applied


def _build_live_finger_quats(rig, n_out: int, mode: str, pos_w: np.ndarray, scale: float, jidx: dict) -> dict:
    """Build adducted, naturally curved, per-frame LIVING finger quaternions driven by MoCap arm motion.

    Eliminates both splayed V-gap fingers and stiff frozen mannequin hands while keeping exact loop seams.
    """
    # Compute smooth cyclic normalized hand activity (speed + height) per side from MoCap wrists.
    activity = {}
    for side, jname in (("l", "LeftHand"), ("r", "RightHand")):
        h_pos = pos_w[:, jidx[jname]] * scale
        hips = pos_w[:, jidx["Hips"]] * scale
        rel_z = h_pos[:, 2] - hips[:, 2]
        # Cyclic wrist velocity magnitude.
        vel = np.linalg.norm(np.roll(h_pos[:n_out], -1, axis=0) - h_pos[:n_out], axis=1)
        vel = np.concatenate([vel, vel[:1]])
        vel_s = _cyclic_smooth(vel, radius=4)
        z_s = _cyclic_smooth(rel_z, radius=4)
        v_norm = np.clip((vel_s - 0.004) / 0.045, 0.0, 1.0)
        z_norm = np.clip((z_s + 0.16) / 0.42, 0.0, 1.0)
        activity[side] = (v_norm, z_norm)

    # Finger curl specification: (seg01_curl, seg02_curl, seg03_curl, phase_off). The hand's position of rest flexes
    # at the knuckles first: fingers that hook at the two end joints from straight knuckles read as a claw.
    finger_specs = {
        "index":  (32.0, 30.0, 12.0, 0.00),
        "middle": (36.0, 33.0, 13.0, 0.22),
        "ring":   (40.0, 36.0, 14.0, 0.44),
        "pinky":  (44.0, 38.0, 14.0, 0.66),
    }

    out = {}
    for side in ("l", "r"):
        t_bone = rig.data.bones.get(f"thumb_01_{side}")
        i_bone = rig.data.bones.get(f"index_01_{side}")
        m_bone = rig.data.bones.get(f"middle_01_{side}")
        p_bone = rig.data.bones.get(f"pinky_01_{side}")
        h_bone = rig.data.bones.get(f"hand_{side}")
        if None in (t_bone, i_bone, m_bone, p_bone, h_bone):
            continue
        thumb_vec = (t_bone.head_local - p_bone.head_local).normalized()
        hand_dir = (h_bone.tail_local - h_bone.head_local).normalized()
        palm_n = (hand_dir.cross(thumb_vec) if side == "l" else thumb_vec.cross(hand_dir)).normalized()
        curl_axis = (-thumb_vec) if side == "l" else thumb_vec

        # Measure exact rest-pose splay vectors directly from the skeleton so fingers close parallel
        # and the thumb tucks naturally alongside the index finger with zero sign ambiguity.
        m_dir = (m_bone.tail_local - m_bone.head_local).normalized()
        i_dir = (i_bone.tail_local - i_bone.head_local).normalized()
        t_dir = (t_bone.tail_local - t_bone.head_local).normalized()
        adduct_info = {}
        for finger in ("index", "middle", "ring", "pinky"):
            fb = rig.data.bones.get(f"{finger}_01_{side}")
            if fb is None or finger == "middle":
                adduct_info[finger] = (None, 0.0)
                continue
            f_dir = (fb.tail_local - fb.head_local).normalized()
            # Project splay onto palm plane so adduction closes side-to-side gap cleanly without twisting curl.
            f_proj = (f_dir - palm_n * f_dir.dot(palm_n)).normalized()
            m_proj = (m_dir - palm_n * m_dir.dot(palm_n)).normalized()
            cross_v = f_proj.cross(m_proj)
            ang = math.acos(max(-1.0, min(1.0, f_proj.dot(m_proj))))
            if cross_v.length > 1e-5 and ang > 1e-4:
                # Close 82% of MPFB2's splayed rest fan (pinky/ring slightly extra to form a cohesive hand).
                close_frac = 0.88 if finger == "pinky" else 0.82
                adduct_info[finger] = (cross_v.normalized(), ang * close_frac)
            else:
                adduct_info[finger] = (None, 0.0)

        t_to_i_cross = t_dir.cross(i_dir)
        t_to_i_axis = t_to_i_cross.normalized() if t_to_i_cross.length > 1e-5 else palm_n
        t_to_i_ang = math.acos(max(-1.0, min(1.0, t_dir.dot(i_dir)))) * 0.68
        t_to_palm_cross = t_dir.cross(palm_n)
        t_to_palm_axis = t_to_palm_cross.normalized() if t_to_palm_cross.length > 1e-5 else curl_axis

        side_phase = 0.0 if side == "l" else math.pi
        v_norm, z_norm = activity[side]

        f_names = [f"{f}_{s}_{side}" for f in ("index", "middle", "ring", "pinky", "thumb") for s in ("01", "02", "03")]
        m_rests = {}
        for fn in f_names:
            b = rig.data.bones.get(fn)
            if b is not None:
                m_rests[fn] = (b.matrix_local.to_3x3(), b.matrix_local.to_3x3().inverted())
                out[fn] = []

        for fi in range(n_out + 1):
            u = (fi % n_out) / float(n_out)
            tau = 2.0 * math.pi * u
            if mode == "talk":
                open_base = float(np.clip(0.16 + 0.50 * z_norm[fi] + 0.36 * v_norm[fi] + 0.08 * math.sin(tau + side_phase), 0.0, 0.85))
            elif mode == "walk":
                open_base = float(np.clip(0.14 + 0.14 * math.sin(tau + side_phase) + 0.10 * v_norm[fi], 0.0, 0.42))
            else:
                open_base = float(np.clip(0.12 + 0.12 * math.sin(tau + side_phase * 0.5) + 0.05 * math.sin(2.0 * tau), 0.0, 0.34))

            for finger, (c1, c2, c3, ph) in finger_specs.items():
                wave = 0.07 * math.sin(tau + ph + side_phase * 0.35)
                f_open = max(0.0, min(1.0, open_base + wave))
                curl_mul = 1.0 - 0.50 * f_open
                add_axis, add_rad = adduct_info[finger]
                for seg, c_deg in (("01", c1), ("02", c2), ("03", c3)):
                    fn = f"{finger}_{seg}_{side}"
                    if fn not in m_rests:
                        continue
                    m_r, m_ri = m_rests[fn]
                    r_w = Matrix.Rotation(math.radians(c_deg * curl_mul), 3, curl_axis)
                    if seg == "01" and add_axis is not None:
                        r_w = r_w @ Matrix.Rotation(add_rad * (1.0 - 0.25 * f_open), 3, add_axis)
                    q = (m_ri @ r_w @ m_r).to_quaternion().normalized()
                    if out[fn] and out[fn][-1].dot(q) < 0.0:
                        q = -q
                    out[fn].append(q)

            # Thumb: close 68% of the 53-deg rest L-gap directly toward index_01 + soft tuck toward palm.
            t_open = max(0.0, min(1.0, open_base + 0.05 * math.cos(tau + side_phase)))
            t_mul = 1.0 - 0.36 * t_open
            for seg, close_scale, palm_deg in (("01", 1.0, 18.0), ("02", 0.0, 18.0), ("03", 0.0, 14.0)):
                fn = f"thumb_{seg}_{side}"
                if fn not in m_rests:
                    continue
                m_r, m_ri = m_rests[fn]
                r_w = Matrix.Rotation(math.radians(palm_deg * t_mul), 3, t_to_palm_axis)
                if close_scale > 0.0:
                    r_w = r_w @ Matrix.Rotation(t_to_i_ang * close_scale * (1.0 - 0.22 * t_open), 3, t_to_i_axis)
                q = (m_ri @ r_w @ m_r).to_quaternion().normalized()
                if out[fn] and out[fn][-1].dot(q) < 0.0:
                    q = -q
                out[fn].append(q)

        # Guarantee bit-exact loop seam on every finger bone.
        for fn in f_names:
            if fn in out and len(out[fn]) >= 2:
                out[fn][-1] = out[fn][0].copy()
    return out


def retarget_bvh_to_action(
    rig,
    meshes: list,
    bvh_path: Path,
    action_name: str,
    frame_start: int,
    frame_end: int,
    mode: str = "walk",
    target_fps: int = 30,
) -> dict:
    """Retarget a CMU BVH clip segment onto an MPFB2 `game_engine` rig as a seamless looping NLA strip.

    Returns dict with `duration_s`, `stride_m`, `frames`, `bvh`.
    """
    joints, ftime, data = parse_bvh(bvh_path)
    jidx = {j["name"]: idx for idx, j in enumerate(joints)}
    frame_end = min(frame_end, len(data) - 1)
    src_fps = round(1.0 / max(ftime, 1e-5))
    stride_step = max(1, round(src_fps / float(target_fps)))

    # Sample evenly so final frame == frame_end (cleanly downsampled from 120Hz -> 30Hz).
    n_out = max(12, round((frame_end - frame_start) / float(stride_step)))
    sample_idx = [int(round(frame_start + (frame_end - frame_start) * (k / float(n_out)))) for k in range(n_out + 1)]
    pos_bl, rot_bl = eval_bvh_fk(joints, data, sample_idx)

    if mode == "talk":
        # A conversation loop keeps both hands below the shoulders. A wider gesture, repeated every few seconds by a
        # passer-by, reads as a signal; it also opens the underarm of a fitted sleeve past what its cut allows.
        arm_len = float(np.linalg.norm(joints[jidx["LeftForeArm"]]["offset"]) + np.linalg.norm(joints[jidx["LeftHand"]]["offset"]))
        reach = max(float((pos_bl[:, jidx[hand], 2] - pos_bl[:, jidx[shoulder], 2]).max())
                    for hand, shoulder in (("LeftHand", "LeftArm"), ("RightHand", "RightArm"))) / arm_len
        if reach > -0.05:
            raise ValueError(f"{action_name}: a hand rises {reach:+.2f} arm length above its shoulder; choose a calmer window")
        # Nor does an upper arm rise more than 50 deg from hanging: an arm held out level to the side passed the hand
        # rule and read as a stop sign.
        lift = max(float(np.degrees(np.arccos(np.clip(
            -(pos_bl[:, jidx[elbow], 2] - pos_bl[:, jidx[shoulder], 2])
            / np.maximum(np.linalg.norm(pos_bl[:, jidx[elbow]] - pos_bl[:, jidx[shoulder]], axis=1), 1e-6), -1.0, 1.0))).max())
                   for elbow, shoulder in (("LeftForeArm", "LeftArm"), ("RightForeArm", "RightArm")))
        if lift > 50.0:
            raise ValueError(f"{action_name}: an upper arm rises {lift:.0f} deg from hanging; choose a calmer window")

    # Yaw-align whole clip so character faces / walks straight along Blender -Y (0, -1, 0).
    if mode == "walk":
        disp = pos_bl[-1, 0] - pos_bl[0, 0]
        cur_yaw = math.atan2(disp[0], -disp[1])  # 0 when walking along -Y
    else:
        fwd_vecs = np.einsum("fij,j->fi", rot_bl[:, 0], np.array([0.0, -1.0, 0.0]))
        mean_fwd = fwd_vecs.mean(axis=0)
        cur_yaw = math.atan2(mean_fwd[0], -mean_fwd[1])
    R_yaw = _rz(cur_yaw)  # rotates (sin a, -cos a, 0) -> (0, -1, 0)
    pos_w = np.einsum("ij,fnj->fni", R_yaw, pos_bl)
    rot_w = np.einsum("ij,fnjk->fnik", R_yaw, rot_bl)

    # Exact leg-length metric scaling (CMU BVH units -> target character meters).
    src_leg = float(
        np.linalg.norm(joints[jidx["LeftLeg"]]["offset"])
        + np.linalg.norm(joints[jidx["LeftFoot"]]["offset"])
    )
    dst_thigh = rig.data.bones["thigh_l"]
    dst_calf = rig.data.bones["calf_l"]
    dst_foot = rig.data.bones["foot_l"]
    dst_leg = float((dst_calf.head_local - dst_thigh.head_local).length + (dst_foot.head_local - dst_calf.head_local).length)
    scale = dst_leg / max(src_leg, 1e-4)

    # Measure exact metric stride before stripping linear forward travel.
    hip_disp = (pos_w[-1, 0] - pos_w[0, 0]) * scale
    stride_m = float(math.hypot(hip_disp[0], hip_disp[1])) if mode == "walk" else 0.0

    # Compute exact anatomical rest-frame calibration matrix R_calib[dst_bone] = F_src_rest @ inv(F_dst_rest) @ R_dst_rest.
    # For any frame f: desired world rotation of dst_bone = rot_w[f, src] @ R_calib[dst_bone].
    # Use the actual thumb-to-pinky anatomical vector on MPFB2's hands so forearm & palm twist match CMU T-pose
    # (where thumbs point forward -Y and palms face down -Z) with zero supination/pronation error on either arm.
    def _hand_thumb_dir(side: str):
        t = rig.data.bones.get(f"thumb_01_{side}")
        p = rig.data.bones.get(f"pinky_01_{side}")
        if t is not None and p is not None:
            return _norm(np.array(t.head_local - p.head_local, dtype=np.float64))
        return np.array([0.0, -1.0, 0.0], dtype=np.float64)

    dst_thumb_l = _hand_thumb_dir("l")
    dst_thumb_r = _hand_thumb_dir("r")
    src_thumb = np.array([0.0, -1.0, 0.0], dtype=np.float64)  # CMU T-pose thumbs point forward (-Y)

    # A capture subject's marker fit leaves a constant offset on the shoulders, neck and head: CMU's rest shoulders sit
    # ~15-20 deg higher than MPFB2's natural collar, and its head leans 9 to 19 deg forward on average, by subject.
    # Only the motion around a clip's own mean carriage transfers; the rig's rest carriage is the level one. The trunk
    # keeps the capture's own lean: a body stands and walks slightly forward over its feet, and MPFB2's female rest
    # leans 2 deg back over a deep lumbar curve. Given that rest carriage, the women stood arched.
    carriage_mean_inv = {}
    for cname in ("LeftShoulder", "RightShoulder", "Neck1", "Head"):
        ci = jidx[cname]
        q_sum = Quaternion((0.0, 0.0, 0.0, 0.0))
        q_ref = None
        for fi in range(n_out + 1):
            q = Matrix(rot_w[fi, ci].tolist()).to_quaternion().normalized()
            if q_ref is None:
                q_ref = q
            elif q_ref.dot(q) < 0.0:
                q = -q
            q_sum = Quaternion((q_sum.w + q.w, q_sum.x + q.x, q_sum.y + q.y, q_sum.z + q.z))
        q_mean = q_sum.normalized()
        carriage_mean_inv[cname] = np.array(q_mean.inverted().to_matrix(), dtype=np.float64)

    R_calib = {}
    R_dst_rest = {}
    M_rest_local = {}
    for dst_name, src_name, child_name, fmode in BONE_MAP:
        b = rig.data.bones[dst_name]
        r_rest = np.array(b.matrix_local.to_3x3(), dtype=np.float64)
        R_dst_rest[dst_name] = r_rest
        if b.parent is not None:
            r_par = np.array(b.parent.matrix_local.to_3x3(), dtype=np.float64)
            M_rest_local[dst_name] = r_par.T @ r_rest
        else:
            M_rest_local[dst_name] = r_rest

        if fmode == "world" or dst_name.startswith("clavicle_"):
            R_calib[dst_name] = r_rest
        else:
            v_src = _src_bone_dir_bl(joints, jidx, src_name, child_name)
            v_dst = _dst_bone_dir_bl(rig, dst_name)
            if fmode == "limb":
                F_src = _make_frame(v_src, np.array([0.0, -1.0, 0.0]))
                F_dst = _make_frame(v_dst, np.array([0.0, -1.0, 0.0]))
            elif fmode == "foot":
                F_src = _make_frame(v_src, np.array([0.0, 0.0, 1.0]))
                F_dst = _make_frame(v_dst, np.array([0.0, 0.0, 1.0]))
            elif fmode == "elbow_l":
                F_src = _make_frame(v_src, src_thumb)
                F_dst = _make_frame(v_dst, dst_thumb_l)
            elif fmode == "elbow_r":
                F_src = _make_frame(v_src, src_thumb)
                F_dst = _make_frame(v_dst, dst_thumb_r)
            else:
                F_src = np.eye(3)
                F_dst = np.eye(3)
            R_calib[dst_name] = F_src @ F_dst.T @ r_rest

    # A walking leg extends once per step: the flexion a walking knee never releases over a clip is its subject's marker
    # fit (subjects 02 and 35 never extend within 9 and 13 deg). Standing, the weight-bearing leg is nearly straight and
    # the other relaxed: both knees lose the flexion the bearing one never releases, and the relaxed one stays bent.
    # Straightened each by its own, the two legs lengthened apart and one foot floated 3 cm; left as captured, both
    # knees stood bent 11 and 22 deg, and the figure crouched.
    knee_fit = {}
    for side, up, low in (("l", "LeftUpLeg", "LeftLeg"), ("r", "RightUpLeg", "RightLeg")):
        thigh_y = np.einsum("fij,j->fi", rot_w[:, jidx[up]], R_calib[f"thigh_{side}"][:, 1])
        calf_y = np.einsum("fij,j->fi", rot_w[:, jidx[low]], R_calib[f"calf_{side}"][:, 1])
        flex = np.degrees(np.arccos(np.clip(np.einsum("fi,fi->f", thigh_y, calf_y), -1.0, 1.0)))
        rest_flex = math.degrees(math.acos(float(np.clip(R_dst_rest[f"thigh_{side}"][:, 1] @ R_dst_rest[f"calf_{side}"][:, 1], -1.0, 1.0))))
        knee_fit[f"calf_{side}"] = math.radians(max(0.0, float(np.percentile(flex, 5)) - rest_flex))
    if mode != "walk":
        bearing = min(knee_fit.values())
        knee_fit = {k: bearing for k in knee_fit}

    # A foot's sole lies flat: the roll a foot keeps over a whole clip, about its own heel-to-toe line, is the fit between
    # the two skeletons' foot frames. Every clip stood both feet 10 to 23 deg on their edges, mirrored left and right.
    # Turned about that line, the foot keeps its pitch and its heading.
    # A foot turns out about 8 deg, standing or walking, and the whole leg turns with it from the hip, the knee over the
    # toes. Subject 18 stands with one foot 12 deg in and the other 25 deg out; subject 35 walks with one foot 15 deg in.
    foot_level, leg_turn = {}, {}
    for side, src in (("l", "LeftFoot"), ("r", "RightFoot")):
        R_feet = np.einsum("fij,jk->fik", rot_w[:, jidx[src]], R_calib[f"foot_{side}"])
        X, Y = R_feet[:, :, 0], R_feet[:, :, 1]
        YxX = np.cross(Y, X)
        level = -np.arctan(X[:, 2] / np.where(np.abs(YxX[:, 2]) > 1e-3, YxX[:, 2], 1e-3))
        mean_level = float(np.mean(level))
        foot_level[side] = [np.array(Matrix.Rotation(mean_level, 3, Vector(Y[fi].tolist())), dtype=np.float64)
                            for fi in range(n_out + 1)]
        out = np.degrees(np.arctan2(Y[:, 0], -Y[:, 1])) * (1.0 if side == "l" else -1.0)
        turn = math.radians(8.0 - float(np.mean(out)))
        leg_turn[side] = np.array(Matrix.Rotation(turn if side == "l" else -turn, 3, "Z"), dtype=np.float64)

    # Pelvis world translation deltas in meters (relative to pelvis rest head_local).
    pelvis_rest_pos = np.array(rig.data.bones["pelvis"].head_local, dtype=np.float64)
    hips_m = pos_w[:, 0] * scale
    if mode == "walk":
        # Strip constant linear forward/lateral drift so the walk cycles cleanly in place while preserving sway & surges.
        u = np.linspace(0.0, 1.0, n_out + 1)[:, None]
        trend = hips_m[0:1] * (1.0 - u) + hips_m[-1:] * u
        pelvis_xy = hips_m[:, :2] - trend[:, :2]
        pelvis_xy -= pelvis_xy.mean(axis=0, keepdims=True)
    else:
        # Keep natural weight shift centered around origin.
        pelvis_xy = hips_m[:, :2] - hips_m[:, :2].mean(axis=0, keepdims=True)
    pelvis_z = hips_m[:, 2] - hips_m[:, 2].mean()

    # Build pose quaternions & pelvis translations for all frames.
    mapped_names = [x[0] for x in BONE_MAP]
    quats = {name: [] for name in mapped_names}
    pelvis_locs = []
    pelvis_rest_inv = np.array(rig.data.bones["pelvis"].matrix_local.to_3x3().inverted(), dtype=np.float64)

    for fi in range(n_out + 1):
        R_world_cur = {}
        # Root bone stays at identity pose.
        if "Root" in rig.data.bones:
            R_world_cur["Root"] = np.array(rig.data.bones["Root"].matrix_local.to_3x3(), dtype=np.float64)

        for dst_name, src_name, _child_name, _fmode in BONE_MAP:
            b = rig.data.bones[dst_name]
            if b.parent is not None and b.parent.name in R_world_cur:
                R_par = R_world_cur[b.parent.name]
            elif b.parent is not None:
                R_par = np.array(b.parent.matrix_local.to_3x3(), dtype=np.float64)
            else:
                R_par = np.eye(3, dtype=np.float64)

            if dst_name.startswith("clavicle_"):
                # Scapulohumeral rhythm: lower/raise clavicle smoothly by ~24% of the humerus elevation
                # relative to MPFB2's 49-deg A-pose, eliminating blocky A-pose shoulder steps when arms hang down,
                # plus 20% of CMU's dynamic shrug relative to clip mean.
                side = dst_name[-1]
                arm_dst = f"upperarm_{side}"
                arm_src = "LeftArm" if side == "l" else "RightArm"
                R_arm_des = rot_w[fi, jidx[arm_src]] @ R_calib[arm_dst]
                v_arm_cur = R_arm_des[:, 1]
                v_arm_rest = R_dst_rest[arm_dst][:, 1]
                elev_cur = math.asin(float(np.clip(v_arm_cur[2], -1.0, 1.0)))
                elev_rest = math.asin(float(np.clip(v_arm_rest[2], -1.0, 1.0)))
                # Negative angle around forward axis (-Y) drops left clavicle; positive drops right clavicle.
                drop = max(math.radians(-11.0), min(math.radians(10.0), 0.24 * (elev_cur - elev_rest)))
                ang_fwd = drop if side == "l" else -drop
                # Torso forward axis in world space (spine_03 local Z points along -Y forward).
                torso_fwd = _norm(R_par[:, 2])
                R_scap = np.array(Matrix.Rotation(ang_fwd, 3, Vector(torso_fwd.tolist())), dtype=np.float64)

                R_rel = rot_w[fi, jidx[src_name]] @ carriage_mean_inv[src_name]
                q_rel = Quaternion((1.0, 0.0, 0.0, 0.0)).slerp(Matrix(R_rel.tolist()).to_quaternion().normalized(), 0.20)
                R_des = np.array(q_rel.to_matrix(), dtype=np.float64) @ R_scap @ R_par @ M_rest_local[dst_name]
            elif src_name in carriage_mean_inv:
                R_des = rot_w[fi, jidx[src_name]] @ carriage_mean_inv[src_name] @ R_calib[dst_name]
            else:
                R_des = rot_w[fi, jidx[src_name]] @ R_calib[dst_name]

            if dst_name[:-2] in ("foot", "ball"):
                R_des = foot_level[dst_name[-1]][fi] @ R_des
            if dst_name[:-2] in ("thigh", "calf", "foot", "ball"):
                R_des = leg_turn[dst_name[-1]] @ R_des
            if dst_name in knee_fit:
                # Extend the knee about its own axis by its fit, never past straight.
                axis = np.cross(R_des[:, 1], R_world_cur[f"thigh_{dst_name[-1]}"][:, 1])
                sin_flex = float(np.linalg.norm(axis))
                if sin_flex > 1e-4:
                    ang = min(knee_fit[dst_name], math.atan2(sin_flex, float(R_des[:, 1] @ R_world_cur[f"thigh_{dst_name[-1]}"][:, 1])))
                    R_des = np.array(Matrix.Rotation(ang, 3, Vector((axis / sin_flex).tolist())), dtype=np.float64) @ R_des

            R_world_cur[dst_name] = R_des
            R_local = R_par.T @ R_des
            R_pose = M_rest_local[dst_name].T @ R_local
            q = Matrix(R_pose.tolist()).to_quaternion().normalized()
            if dst_name.startswith("hand_"):
                # The CMU wrist joint only twists: any swing here is a fit offset between the two hand axes, not motion.
                q = _swing_twist_y(q)
                # Mildly smooth high-frequency CMU wrist jitter while keeping full conversational expressiveness.
                if mode != "talk":
                    q = Quaternion((1.0, 0.0, 0.0, 0.0)).slerp(q, 0.65).normalized()
            if quats[dst_name] and quats[dst_name][-1].dot(q) < 0.0:
                q = -q
            quats[dst_name].append(q)

        # World translation delta from rest pelvis position -> pelvis pose-bone local space.
        delta_w = np.array([pelvis_xy[fi, 0], pelvis_xy[fi, 1], pelvis_z[fi]], dtype=np.float64)
        pelvis_locs.append(Vector((pelvis_rest_inv @ delta_w).tolist()))

    # Universal torso/hip/thigh clearance pass: guarantees zero hand-in-thigh/pocket penetration on any outfit.
    clearance_deg = _enforce_arm_body_clearance(rig, meshes, mapped_names, quats, pelvis_locs)

    # Seamless cyclic seam blending across the final K frames so frame[N] == frame[0] with zero pop.
    blend_k = min(10, max(4, n_out // 4))
    for name in mapped_names:
        qs = quats[name]
        q0 = qs[0]
        qn = qs[-1]
        if q0.dot(qn) < 0.0:
            q0 = -q0
        q_delta = qn.inverted() @ q0  # satisfies qn @ q_delta == q0
        for j in range(blend_k + 1):
            idx = n_out - blend_k + j
            u = j / float(blend_k)
            s = u * u * (3.0 - 2.0 * u)
            qs[idx] = (qs[idx] @ Quaternion((1.0, 0.0, 0.0, 0.0)).slerp(q_delta, s)).normalized()
        qs[-1] = qs[0].copy()

    # Populate leaf arm twist bones (upperarm_twist_01_l/r, lowerarm_twist_01_l/r) if present on the rig.
    twist_bones = []
    for side in ("l", "r"):
        uat = f"upperarm_twist_01_{side}"
        if uat in rig.pose.bones:
            twist_bones.append(uat)
            quats[uat] = []
            for fi in range(n_out + 1):
                q_tw = _swing_twist_y(quats[f"upperarm_{side}"][fi])
                # Counter-twist deltoid cap by 62% of humeral roll so shirt/skin shoulders stay smooth.
                q_cnt = Quaternion((1.0, 0.0, 0.0, 0.0)).slerp(q_tw.inverted(), 0.62).normalized()
                if quats[uat] and quats[uat][-1].dot(q_cnt) < 0.0:
                    q_cnt = -q_cnt
                quats[uat].append(q_cnt)
            quats[uat][-1] = quats[uat][0].copy()
        lat = f"lowerarm_twist_01_{side}"
        if lat in rig.pose.bones:
            twist_bones.append(lat)
            quats[lat] = []
            for fi in range(n_out + 1):
                q_tw = _swing_twist_y(quats[f"hand_{side}"][fi])
                # Distribute 55% of wrist pronation/supination smoothly down the distal forearm.
                q_flw = Quaternion((1.0, 0.0, 0.0, 0.0)).slerp(q_tw, 0.55).normalized()
                if quats[lat] and quats[lat][-1].dot(q_flw) < 0.0:
                    q_flw = -q_flw
                quats[lat].append(q_flw)
            quats[lat][-1] = quats[lat][0].copy()

    p_err = pelvis_locs[0] - pelvis_locs[-1]
    for j in range(blend_k + 1):
        idx = n_out - blend_k + j
        u = j / float(blend_k)
        s = u * u * (3.0 - 2.0 * u)
        pelvis_locs[idx] = pelvis_locs[idx] + p_err * s
    pelvis_locs[-1] = pelvis_locs[0].copy()

    # A body rests on its feet at every moment: standing on both, walking on the one in stance. The pelvis settles until
    # the highest bearing sole meets the ground,
    # then the other leg bends to keep its foot on it; the ground lock below then sets the soles' level from
    # the boots themselves. A ground lock over the whole clip left one foot 1 to 3 cm up.
    plant_gap_cm = _plant_feet(rig, mapped_names, quats, pelvis_locs, pelvis_rest_inv, M_rest_local, mode == "walk")

    # Ground-lock: evaluate actual deformed shoe/foot min-Z across the clip and shift pelvis Z so stance touches Z=0.
    depsgraph = bpy.context.evaluated_depsgraph_get()
    shoe_objs = [o for o in meshes if "shoe" in o.name.lower()] or meshes
    min_zs = []
    head_pitches = []
    knee_flex = []
    check_step = max(1, n_out // 16)
    for fi in range(0, n_out, check_step):
        for name in mapped_names:
            pb = rig.pose.bones[name]
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = quats[name][fi]
        rig.pose.bones["pelvis"].location = pelvis_locs[fi]
        bpy.context.view_layer.update()
        head_up = rig.pose.bones["head"].matrix.to_3x3().col[1]
        head_pitches.append(math.atan2(-head_up.y, head_up.z))
        pbs = rig.pose.bones
        knee_flex.append([(pbs[f"calf_{s}"].head - pbs[f"thigh_{s}"].head).angle(pbs[f"foot_{s}"].head - pbs[f"calf_{s}"].head) for s in "lr"])
        z_lo = 1e9
        for obj in shoe_objs:
            eval_obj = obj.evaluated_get(depsgraph)
            me = eval_obj.to_mesh()
            mw = eval_obj.matrix_world
            for v in me.vertices:
                wz = (mw @ v.co).z
                if wz < z_lo:
                    z_lo = wz
            eval_obj.to_mesh_clear()
        min_zs.append(z_lo)
    # 10th percentile represents planted stance sole without over-reacting to a single outlier toe vertex.
    z_floor = float(np.percentile(min_zs, 10))
    z_shift_local = Vector((pelvis_rest_inv @ np.array([0.0, 0.0, -z_floor], dtype=np.float64)).tolist())
    for fi in range(n_out + 1):
        pelvis_locs[fi] = pelvis_locs[fi] + z_shift_local

    # The carriage rule's own check: over the clip, the head rides level, as in the rest pose (-Y forward, +Z up).
    rest_up = rig.data.bones["head"].matrix_local.to_3x3().col[1]
    head_pitch_deg = math.degrees(float(np.mean(head_pitches)) - math.atan2(-rest_up.y, rest_up.z))
    if abs(head_pitch_deg) > 4.0:
        raise ValueError(f"{action_name}: the head leans {head_pitch_deg:+.1f} deg on average; its carriage must stay level")
    # The knee rule's own check: each walking leg extends to the rig's rest at least once per cycle.
    rb = rig.data.bones
    knee_rest_deg = math.degrees((rb["calf_l"].head_local - rb["thigh_l"].head_local).angle(rb["foot_l"].head_local - rb["calf_l"].head_local))
    knee_min_deg = np.degrees(np.min(knee_flex, axis=0))
    if mode == "walk" and float(knee_min_deg.max()) > knee_rest_deg + 5.0:
        raise ValueError(f"{action_name}: a knee never extends below {knee_min_deg.max():.1f} deg; the rig rests at {knee_rest_deg:.1f}")

    # Build adducted, naturally curved, per-frame living finger animation (no splayed/frozen hands).
    finger_quats = _build_live_finger_quats(rig, n_out, mode, pos_w, scale, jidx)

    # Write Blender Action & push to NLA strip for glTF multi-clip export.
    bpy.context.scene.render.fps = target_fps
    action = bpy.data.actions.new(name=action_name)
    if rig.animation_data is None:
        rig.animation_data_create()
    rig.animation_data.action = action

    for pb in rig.pose.bones:
        pb.rotation_mode = "QUATERNION"
        pb.rotation_quaternion = Quaternion((1.0, 0.0, 0.0, 0.0))
        pb.location = Vector((0.0, 0.0, 0.0))
        pb.scale = Vector((1.0, 1.0, 1.0))

    all_anim_bones = list(mapped_names) + twist_bones
    finger_bones = list(finger_quats.keys())

    for fi in range(n_out + 1):
        frame = fi + 1
        for name in all_anim_bones:
            pb = rig.pose.bones[name]
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = quats[name][fi]
            pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        for fb in finger_bones:
            pb = rig.pose.bones[fb]
            pb.rotation_mode = "QUATERNION"
            pb.rotation_quaternion = finger_quats[fb][fi]
            pb.keyframe_insert(data_path="rotation_quaternion", frame=frame)
        rig.pose.bones["pelvis"].location = pelvis_locs[fi]
        rig.pose.bones["pelvis"].keyframe_insert(data_path="location", frame=frame)

    if hasattr(action, "fcurves"):
        for fc in action.fcurves:
            for kp in fc.keyframe_points:
                kp.interpolation = "LINEAR"

    track = rig.animation_data.nla_tracks.new()
    track.name = action_name
    strip = track.strips.new(action_name, 1, action)
    strip.action_frame_start = 1
    strip.action_frame_end = n_out + 1
    rig.animation_data.action = None

    return {
        "bvh": bvh_path.name,
        "frames": n_out,
        "duration_s": round(n_out / float(target_fps), 3),
        "stride_m": round(stride_m, 4),
        "z_floor_corrected_m": round(z_floor, 4),
        "arm_clearance_max_deg": round(clearance_deg, 2),
        "head_pitch_mean_deg": round(head_pitch_deg, 2),
        "knee_fit_removed_deg": [round(math.degrees(knee_fit.get(f"calf_{s}", 0.0)), 1) for s in "lr"],
        "planted_correction_max_cm": round(plant_gap_cm, 2),
        "knee_min_deg": [round(float(v), 1) for v in knee_min_deg],
    }
