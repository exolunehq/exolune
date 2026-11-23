"""Animation clips of the Navette AAA: rigid parts keyed in world space, and shape keys.

Every moving part is its own object. A clip gives it a pose: a function of the phase u, from 0
(the rest pose the asset is built in) to 1, returning the 4x4 world transform applied to the part
at rest. bake() keys one sample per frame, so arcs stay arcs, and stacks the action on an NLA
track named after the clip: the glTF exporter merges the tracks of one name into one animation.

All clips start on frame 0, which is the rest pose: gear down, airbrake and hatch closed, wings in.
"""
import math

import bpy
import numpy as np
from mathutils import Matrix

FPS = 24
CLIPS = {"Train": 84, "Aerofrein": 30, "Trappe_Arriere": 72, "Ailes": 96}   # length in frames; u = frame / length


def about(point, axis, angle):
    """4x4 rotation by angle (radians) about the line through point along axis."""
    axis = np.asarray(axis, dtype=float)
    x, y, z = axis / np.linalg.norm(axis)
    c, s = math.cos(angle), math.sin(angle)
    r = np.array([[c + x * x * (1 - c), x * y * (1 - c) - z * s, x * z * (1 - c) + y * s],
                  [y * x * (1 - c) + z * s, c + y * y * (1 - c), y * z * (1 - c) - x * s],
                  [z * x * (1 - c) - y * s, z * y * (1 - c) + x * s, c + z * z * (1 - c)]])
    m = np.eye(4)
    m[:3, :3] = r
    m[:3, 3] = np.asarray(point, dtype=float) - r @ np.asarray(point, dtype=float)
    return m


def shift(vector):
    m = np.eye(4)
    m[:3, 3] = vector
    return m


def ease(u, start=0.0, end=1.0):
    """Smooth 0 to 1 ramp of the phase u between start and end: parts of one clip move in turn."""
    t = min(max((u - start) / (end - start), 0.0), 1.0)
    return t * t * (3.0 - 2.0 * t)


def bake(obj, clip, pose):
    """Key obj over a clip. pose(u) -> 4x4 world transform of the part, identity at u = 0."""
    length = CLIPS[clip]
    rest = Matrix(obj.matrix_world)
    obj.rotation_mode = "QUATERNION"
    last = None
    for frame in range(length + 1):
        loc, quat, _ = (Matrix(np.asarray(pose(frame / length)).tolist()) @ rest).decompose()
        if last is not None and quat.dot(last) < 0.0:          # the same rotation, on the near side
            quat.negate()
        last = quat.copy()
        obj.location, obj.rotation_quaternion = loc, quat
        obj.keyframe_insert("location", frame=frame)
        obj.keyframe_insert("rotation_quaternion", frame=frame)
    _stack(obj, clip)
    obj.matrix_world = rest


def bake_value(owner, path, clip, curve):
    """Key one property of a datablock over a clip, such as a shape key's value: curve(u), 0 at rest."""
    length = CLIPS[clip]
    holder, attr = path.rsplit(".", 1)
    holder = owner.path_resolve(holder)
    for frame in range(length + 1):
        setattr(holder, attr, curve(frame / length))
        owner.keyframe_insert(data_path=path, frame=frame)
    _stack(owner, clip)
    setattr(holder, attr, curve(0.0))


def _stack(owner, clip):
    """Move the datablock's new action onto an NLA track named after the clip."""
    data = owner.animation_data
    action = data.action
    action.name = f"{clip}_{owner.name}"
    track = data.nla_tracks.new()
    track.name = clip
    track.strips.new(clip, 0, action)
    data.action = None


def animated():
    """Every datablock of the scene that carries clips: its objects, and their shape keys."""
    owners = list(bpy.context.scene.objects)
    owners += [o.data.shape_keys for o in bpy.context.scene.objects
               if o.type == "MESH" and o.data.shape_keys is not None]
    return [o for o in owners if o.animation_data is not None]


def show(phases):
    """Pose the scene for a review: phases maps clip names to u; the clips left out stay at rest.

    The strips are frozen on the asked instant. Do not save the scene afterwards.
    """
    for owner in animated():
        for track in owner.animation_data.nla_tracks:
            for strip in track.strips:
                strip.use_animated_time = True
                strip.strip_time = phases.get(track.name, 0.0) * CLIPS[track.name]
    bpy.context.scene.frame_set(1)
    bpy.context.view_layer.update()
