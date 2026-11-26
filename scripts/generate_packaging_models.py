"""
generate_packaging_models.py
============================
Generates commercial-grade binary glTF 2.0 (.glb) 3D packaging assets for GOMZI BOB Studio:
  - Protein Jars (100g, 250g, 300g, 500g, 1kg, 2kg, 2.5kg, 3kg, 5kg) with organic spline shoulders,
    base heel chamfer, collar ring, 72-ridge ribbed screw-top lid with recessed crown, and crisp wrap sleeve.
  - Pouches (Stand-up zipper, flat-bottom, 3-side-seal, 4-side-seal, kraft/foil) with crimped borders & gusset.
  - Sachets & Stick Packs (70x110mm, single-serve protein/creatine/BCAA/pre-workout) with 4-side crimped heat seals.
  - Bottles (Capsule, tablet, vitamin, liquid bottles) with realistic tapered necks, shoulders, and ribbed caps.
  - Boxes (Supplement, medicine, cosmetic, square & rectangular cartons) with true 24-vertex face normals & UVs.

All assets are original procedural models created in-house for GOMZI BOB (Commercial & Redistribution Permitted).
"""

import os
import json
import struct
import math
import numpy as np


def build_glb(meshes_data):
    """Constructs a standards-compliant binary glTF 2.0 (.glb) containing multiple named meshes & materials."""
    bin_buffer = bytearray()
    buffer_views = []
    accessors = []
    materials = []
    primitives = []

    for idx, mesh in enumerate(meshes_data):
        pos = np.array(mesh["positions"], dtype=np.float32)
        norm = np.array(mesh["normals"], dtype=np.float32)
        uv = np.array(mesh["uvs"], dtype=np.float32)
        ind = np.array(mesh["indices"], dtype=np.uint16 if len(pos) < 65535 else np.uint32)
        ind_comp_type = 5123 if ind.dtype == np.uint16 else 5125

        # 1. Indices
        ind_bytes = ind.tobytes()
        ind_offset = len(bin_buffer)
        bin_buffer.extend(ind_bytes)
        while len(bin_buffer) % 4 != 0:
            bin_buffer.append(0)
        ind_bv_idx = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": ind_offset, "byteLength": len(ind_bytes), "target": 34963})
        ind_acc_idx = len(accessors)
        accessors.append({
            "bufferView": ind_bv_idx,
            "byteOffset": 0,
            "componentType": ind_comp_type,
            "count": len(ind),
            "type": "SCALAR",
            "max": [int(ind.max())] if len(ind) > 0 else [0],
            "min": [int(ind.min())] if len(ind) > 0 else [0],
        })

        # 2. Positions
        pos_bytes = pos.tobytes()
        pos_offset = len(bin_buffer)
        bin_buffer.extend(pos_bytes)
        while len(bin_buffer) % 4 != 0:
            bin_buffer.append(0)
        pos_bv_idx = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": pos_offset, "byteLength": len(pos_bytes), "target": 34962})
        pos_acc_idx = len(accessors)
        accessors.append({
            "bufferView": pos_bv_idx,
            "byteOffset": 0,
            "componentType": 5126,
            "count": len(pos),
            "type": "VEC3",
            "max": [float(pos[:, 0].max()), float(pos[:, 1].max()), float(pos[:, 2].max())],
            "min": [float(pos[:, 0].min()), float(pos[:, 1].min()), float(pos[:, 2].min())],
        })

        # 3. Normals
        norm_bytes = norm.tobytes()
        norm_offset = len(bin_buffer)
        bin_buffer.extend(norm_bytes)
        while len(bin_buffer) % 4 != 0:
            bin_buffer.append(0)
        norm_bv_idx = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": norm_offset, "byteLength": len(norm_bytes), "target": 34962})
        norm_acc_idx = len(accessors)
        accessors.append({
            "bufferView": norm_bv_idx,
            "byteOffset": 0,
            "componentType": 5126,
            "count": len(norm),
            "type": "VEC3",
        })

        # 4. UVs
        uv_bytes = uv.tobytes()
        uv_offset = len(bin_buffer)
        bin_buffer.extend(uv_bytes)
        while len(bin_buffer) % 4 != 0:
            bin_buffer.append(0)
        uv_bv_idx = len(buffer_views)
        buffer_views.append({"buffer": 0, "byteOffset": uv_offset, "byteLength": len(uv_bytes), "target": 34962})
        uv_acc_idx = len(accessors)
        accessors.append({
            "bufferView": uv_bv_idx,
            "byteOffset": 0,
            "componentType": 5126,
            "count": len(uv),
            "type": "VEC2",
        })

        mat_idx = len(materials)
        col = mesh.get("color", [0.9, 0.9, 0.9, 1.0])
        materials.append({
            "name": mesh.get("material_name", f"Material_{idx}"),
            "pbrMetallicRoughness": {
                "baseColorFactor": col,
                "metallicFactor": mesh.get("metallic", 0.04),
                "roughnessFactor": mesh.get("roughness", 0.42),
            },
            "doubleSided": mesh.get("doubleSided", True),
        })

        primitives.append({
            "attributes": {"POSITION": pos_acc_idx, "NORMAL": norm_acc_idx, "TEXCOORD_0": uv_acc_idx},
            "indices": ind_acc_idx,
            "material": mat_idx,
        })

    nodes = []
    meshes_list = []
    for i, prim in enumerate(primitives):
        meshes_list.append({"name": meshes_data[i]["name"], "primitives": [prim]})
        nodes.append({"name": meshes_data[i]["name"], "mesh": i})

    gltf_dict = {
        "asset": {"version": "2.0", "generator": "GOMZI BOB 3D Packaging Engine", "copyright": "GOMZI BOB In-House Asset"},
        "scene": 0,
        "scenes": [{"nodes": list(range(len(nodes)))}],
        "nodes": nodes,
        "meshes": meshes_list,
        "materials": materials,
        "accessors": accessors,
        "bufferViews": buffer_views,
        "buffers": [{"byteLength": len(bin_buffer)}],
    }

    json_str = json.dumps(gltf_dict, separators=(",", ":"))
    json_bytes = json_str.encode("utf-8")
    while len(json_bytes) % 4 != 0:
        json_bytes += b" "

    total_len = 12 + 8 + len(json_bytes) + 8 + len(bin_buffer)
    header = struct.pack("<4sII", b"glTF", 2, total_len)
    chunk0_hdr = struct.pack("<II", len(json_bytes), 0x4E4F534A)
    chunk1_hdr = struct.pack("<II", len(bin_buffer), 0x004E4942)
    return header + chunk0_hdr + json_bytes + chunk1_hdr + bytes(bin_buffer)


def _compute_lathe_normals(profile):
    """Computes smooth analytical 2D profile normals (nr, ny) from adjacent profile segments."""
    n = len(profile)
    p_norms = []
    for i in range(n):
        if i == 0:
            dr = profile[1][0] - profile[0][0]
            dy = profile[1][1] - profile[0][1]
        elif i == n - 1:
            dr = profile[-1][0] - profile[-2][0]
            dy = profile[-1][1] - profile[-2][1]
        else:
            dr = profile[i + 1][0] - profile[i - 1][0]
            dy = profile[i + 1][1] - profile[i - 1][1]
        # Outward normal in (r, y) plane when profile goes bottom->top is (dy, -dr)
        nr, ny = dy, -dr
        length = math.hypot(nr, ny) or 1.0
        p_norms.append((nr / length, ny / length))
    return p_norms


def _revolve_profile(profile, segments=64, ridge_fn=None):
    """Revolves a (radius, y) profile cleanly around Y axis.

    When `ridge_fn` modulates the radius along `theta`, computes true 3D finite-difference
    vertex normals on the revolved surface grid so cap flutes/ribs catch sharp directional
    highlights instead of smooth cylinder shading.
    """
    positions, normals, uvs, indices = [], [], [], []
    verts_per_ring = segments + 1
    n_prof = len(profile)

    for p_idx, (r, y) in enumerate(profile):
        v = 1.0 - (p_idx / max(1, n_prof - 1))
        for s in range(verts_per_ring):
            theta = 2.0 * math.pi * s / segments
            eff_r = r * (1.0 + ridge_fn(p_idx, theta)) if (ridge_fn and r > 0.001) else r
            st, ct = math.sin(theta), math.cos(theta)
            positions.append((eff_r * st, y, eff_r * ct))
            uvs.append((s / segments, v))

    if ridge_fn is not None:
        for p_idx in range(n_prof):
            p0 = max(0, p_idx - 1)
            p1 = min(n_prof - 1, p_idx + 1)
            r_val, y_val = profile[p_idx]
            for s in range(verts_per_ring):
                if r_val <= 0.0005:
                    normals.append((0.0, 1.0 if y_val >= 0 else -1.0, 0.0))
                    continue
                s_base = s % segments
                s_prev = (s_base - 1) % segments
                s_next = (s_base + 1) % segments
                pl = positions[p_idx * verts_per_ring + s_prev]
                pr = positions[p_idx * verts_per_ring + s_next]
                pd = positions[p0 * verts_per_ring + s_base]
                pu = positions[p1 * verts_per_ring + s_base]
                tx = (pr[0] - pl[0], pr[1] - pl[1], pr[2] - pl[2])
                ty = (pu[0] - pd[0], pu[1] - pd[1], pu[2] - pd[2])
                # Outward normal = dP/dtheta x dP/dv
                nx = tx[1] * ty[2] - tx[2] * ty[1]
                ny = tx[2] * ty[0] - tx[0] * ty[2]
                nz = tx[0] * ty[1] - tx[1] * ty[0]
                ln = math.hypot(nx, ny, nz) or 1.0
                normals.append((nx / ln, ny / ln, nz / ln))
    else:
        p_norms = _compute_lathe_normals(profile)
        for p_idx, (r, y) in enumerate(profile):
            nr, ny = p_norms[p_idx]
            for s in range(verts_per_ring):
                if r <= 0.0005:
                    normals.append((0.0, 1.0 if y >= 0 else -1.0, 0.0))
                else:
                    theta = 2.0 * math.pi * s / segments
                    st, ct = math.sin(theta), math.cos(theta)
                    normals.append((nr * st, ny, nr * ct))

    for p_idx in range(n_prof - 1):
        for s in range(segments):
            c1 = p_idx * verts_per_ring + s
            c2 = c1 + 1
            n1 = (p_idx + 1) * verts_per_ring + s
            n2 = n1 + 1
            indices.extend([c1, c2, n1, c2, n2, n1])
    return positions, normals, uvs, indices


def _jar_capacity_specs(preset_id):
    """Returns authentic capacity-specific proportions for injection/blow-molded supplement jars."""
    pid = (preset_id or "jar_1kg").lower()
    if pid in ("jar_100g", "jar_250g", "jar_300g"):
        # Compact wide-lid pre-workout / creatine tub proportions
        return {
            "neck_ratio": 0.855,
            "cap_overhang": 1.056,
            "h_body_frac": 0.650,
            "h_shoulder_frac": 0.132,
            "h_neck_frac": 0.218,
            "shoulder_pow": 1.32,
            "rib_count": 40,
            "rib_depth": 0.023,
            "heel_frac": 0.068,
            "cap_crown_doming": 0.022,
        }
    if pid == "jar_500g":
        # Taller sleek 500g isolate jar
        return {
            "neck_ratio": 0.840,
            "cap_overhang": 1.060,
            "h_body_frac": 0.682,
            "h_shoulder_frac": 0.138,
            "h_neck_frac": 0.180,
            "shoulder_pow": 1.24,
            "rib_count": 44,
            "rib_depth": 0.024,
            "heel_frac": 0.064,
            "cap_crown_doming": 0.025,
        }
    if pid in ("jar_2kg", "jar_2_5kg", "jar_3kg"):
        # Muscular broad-shouldered 2kg-3kg whey & mass tubs
        neck_map = {"jar_2kg": 0.802, "jar_2_5kg": 0.792, "jar_3kg": 0.785}
        return {
            "neck_ratio": neck_map.get(pid, 0.795),
            "cap_overhang": 1.068,
            "h_body_frac": 0.660,
            "h_shoulder_frac": 0.165,
            "h_neck_frac": 0.175,
            "shoulder_pow": 1.04,
            "rib_count": 56,
            "rib_depth": 0.026,
            "heel_frac": 0.072,
            "cap_crown_doming": 0.028,
        }
    if pid == "jar_5kg":
        # Mega 5kg wide-belly bulk tub with deep sturdy knurled cap
        return {
            "neck_ratio": 0.768,
            "cap_overhang": 1.074,
            "h_body_frac": 0.648,
            "h_shoulder_frac": 0.182,
            "h_neck_frac": 0.170,
            "shoulder_pow": 0.96,
            "rib_count": 64,
            "rib_depth": 0.028,
            "heel_frac": 0.078,
            "cap_crown_doming": 0.030,
        }
    # Default: iconic 1kg (1000g) Whey Protein Tub
    return {
        "neck_ratio": 0.832,
        "cap_overhang": 1.064,
        "h_body_frac": 0.674,
        "h_shoulder_frac": 0.146,
        "h_neck_frac": 0.180,
        "shoulder_pow": 1.15,
        "rib_count": 48,
        "rib_depth": 0.025,
        "heel_frac": 0.068,
        "cap_crown_doming": 0.026,
    }


def build_protein_jar(preset_id, dia_mm, h_mm, label_h_mm):
    """Builds a commercial-grade blow-molded Protein Jar + injection-molded screw cap.

    Exports distinct identifiable meshes while preserving studio_3d.js color/slot hooks:
      - BottomRing: molded bottom punt, resting foot ring, heel curve & lower label bumper
      - JarBody: subtly recessed cylindrical label-bay backing wall
      - JarShoulder: upper label collar & blow-molded ergonomic shoulder curve
      - JarNeck: visible recessed shadow-gap collar & internal threaded neck
      - CapGripRibs: screw cap lower skirt flange + high-definition vertical fluted grip ribs
      - CapCrown: upper cap bevel chamfer & molded tamper/seal deck crown
      - LabelSurface: exact 360-degree cylindrical UV wrap seated flush in label bay
    """
    s = 0.005
    r_body = (dia_mm * s) * 0.5
    h_tot = h_mm * s
    specs = _jar_capacity_specs(preset_id)

    h_body = h_tot * specs["h_body_frac"]
    h_shoulder = h_tot * specs["h_shoulder_frac"]
    h_neck = h_tot * specs["h_neck_frac"]
    r_neck = r_body * specs["neck_ratio"]
    r_cap = r_neck * specs["cap_overhang"]

    y_bot = -h_tot * 0.5
    heel_h = max(0.018, h_body * specs["heel_frac"])
    bumper_h = max(0.007, min(0.015, r_body * 0.032))
    y_waist_bot = y_bot + heel_h + bumper_h
    y_waist_top = y_bot + h_body - bumper_h
    y_shoulder_end = y_bot + h_body + h_shoulder

    # Subtle recessed cylindrical label wall (~0.45% inset behind molded heel/shoulder bumpers)
    r_wall = r_body * 0.995
    r_bumper = r_body * 1.003

    # 1. BottomRing: recessed center punt + standing support foot ring + rounded base heel + lower bumper
    punt_lift = max(0.008, h_tot * 0.014)
    bottom_profile = [
        (0.0, y_bot + punt_lift),
        (r_body * 0.52, y_bot + punt_lift * 0.92),
        (r_body * 0.70, y_bot + punt_lift * 0.35),
        (r_body * 0.77, y_bot),
        (r_body * 0.855, y_bot),
        (r_body * 0.905, y_bot + heel_h * 0.14),
        (r_body * 0.948, y_bot + heel_h * 0.34),
        (r_body * 0.980, y_bot + heel_h * 0.62),
        (r_body * 0.996, y_bot + heel_h * 0.88),
        (r_bumper, y_bot + heel_h),
        (r_bumper, y_bot + heel_h + bumper_h * 0.45),
        (r_wall, y_waist_bot),
    ]
    br_pos, br_norm, br_uv, br_ind = _revolve_profile(bottom_profile, segments=96)

    # 2. JarBody: cylindrical wall backing the recessed label panel
    body_profile = [
        (r_wall, y_waist_bot),
        (r_wall, (y_waist_bot + y_waist_top) * 0.5),
        (r_wall, y_waist_top),
    ]
    jb_pos, jb_norm, jb_uv, jb_ind = _revolve_profile(body_profile, segments=96)

    # 3. JarShoulder: upper label protection bumper + smooth multi-step blow-molded shoulder
    shoulder_profile = [
        (r_wall, y_waist_top),
        (r_bumper, y_waist_top + bumper_h * 0.55),
        (r_bumper, y_waist_top + bumper_h),
        (r_body * 0.996, y_waist_top + bumper_h + h_shoulder * 0.06),
    ]
    n_sh = 14
    spow = specs["shoulder_pow"]
    y_sh_start = y_waist_top + bumper_h + h_shoulder * 0.06
    h_sh_span = max(0.01, y_shoulder_end - y_sh_start)
    for k in range(1, n_sh + 1):
        t = k / float(n_sh)
        ease = 0.5 * (1.0 - math.cos((t ** spow) * math.pi))
        rk = (r_body * 0.996) + (r_neck * 1.008 - r_body * 0.996) * ease
        yk = y_sh_start + h_sh_span * t
        shoulder_profile.append((rk, yk))
    # Crisp horizontal shoulder-to-neck step shelf for authentic collar line
    shoulder_profile.extend([
        (r_neck * 0.990, y_shoulder_end + 0.004),
        (r_neck * 0.945, y_shoulder_end + 0.006),
    ])
    js_pos, js_norm, js_uv, js_ind = _revolve_profile(shoulder_profile, segments=96)

    # 4. JarNeck: visible shadow-gap reveal collar + molded thread ring inside screw cap
    gap_h = max(0.010, h_neck * 0.145)
    y_cap_bot = y_shoulder_end + gap_h
    y_neck_top = y_shoulder_end + h_neck * 0.72
    neck_profile = [
        (r_neck * 0.945, y_shoulder_end + 0.004),
        (r_neck * 0.935, y_shoulder_end + gap_h * 0.55),
        (r_neck * 0.955, y_cap_bot + 0.002),
        (r_neck * 0.985, y_cap_bot + gap_h * 0.8),
        (r_neck * 0.955, y_cap_bot + gap_h * 1.5),
        (r_neck * 0.950, y_neck_top),
        (0.0, y_neck_top),
    ]
    jn_pos, jn_norm, jn_uv, jn_ind = _revolve_profile(neck_profile, segments=72)

    # 5. CapGripRibs: Screw cap lower chamfered skirt flange + fluted vertical grip ribs
    h_cap = (h_bot_to_top := (y_bot + h_tot) - y_cap_bot)
    y_cap_top = y_cap_bot + h_cap
    rib_count = specs["rib_count"]
    rib_amp = specs["rib_depth"]
    # Dense theta subdivision (6 segments per rib) gives crisp flat rib lands & beveled valleys
    rib_segments = rib_count * 6

    grip_profile = [
        (r_neck * 0.910, y_cap_bot + h_cap * 0.01),   # Bottom inner skirt return (hides edge)
        (r_cap * 1.006, y_cap_bot),                     # Lower flared cap flange rim
        (r_cap * 1.012, y_cap_bot + h_cap * 0.045),     # Flange outer band bottom
        (r_cap * 1.012, y_cap_bot + h_cap * 0.105),     # Flange outer band top
        (r_cap * 0.984, y_cap_bot + h_cap * 0.145),     # Recessed shadow groove below ribs
        (r_cap * 0.996, y_cap_bot + h_cap * 0.185),     # Rib bottom chamfer flare
        (r_cap * 0.996, y_cap_bot + h_cap * 0.480),     # Mid-rib vertical grip
        (r_cap * 0.994, y_cap_bot + h_cap * 0.770),     # Top-rib grip edge
        (r_cap * 0.986, y_cap_bot + h_cap * 0.820),     # Rib fade-out into crown bevel
    ]

    def _fluted_cap_ribs(p_idx, theta):
        # Smooth flute envelope across indices 5..7, tapering gently at 4 & 8
        weights = {5: 0.82, 6: 1.0, 7: 0.96, 8: 0.25}
        w = weights.get(p_idx, 0.0)
        if w <= 0.0:
            return 0.0
        # Clamped trapezoidal flute shape (crisp ridges + concave valleys)
        c = math.cos(theta * rib_count)
        flute = math.tanh(2.45 * c) / math.tanh(2.45)
        return rib_amp * w * flute

    cg_pos, cg_norm, cg_uv, cg_ind = _revolve_profile(grip_profile, segments=rib_segments, ridge_fn=_fluted_cap_ribs)

    # 6. CapCrown: Smooth beveled upper cap shoulder & slightly recessed/domed seal deck
    dome = h_cap * specs["cap_crown_doming"]
    crown_profile = [
        (r_cap * 0.986, y_cap_bot + h_cap * 0.818),
        (r_cap * 0.976, y_cap_bot + h_cap * 0.865),
        (r_cap * 0.952, y_cap_bot + h_cap * 0.920),
        (r_cap * 0.912, y_cap_bot + h_cap * 0.968),
        (r_cap * 0.858, y_cap_top),                     # Outer crown deck ridge
        (r_cap * 0.785, y_cap_top - dome * 0.65),       # Subtle molded top recess groove
        (r_cap * 0.735, y_cap_top - dome * 0.72),       # Inner recessed deck edge
        (r_cap * 0.400, y_cap_top - dome * 0.22),       # Gentle shallow dome swell
        (0.0, y_cap_top - dome * 0.05),                 # Mold center crown point
    ]
    cc_pos, cc_norm, cc_uv, cc_ind = _revolve_profile(crown_profile, segments=96)

    # 7. LabelSurface: Exact 360-degree cylindrical UV wrap inside recessed label bay
    # Preserves theta = (u - 0.5) * 2 * pi so u=0.5 faces +Z with zero mirroring!
    r_sleeve = r_wall + 0.0014
    max_bay_h = max(0.02, y_waist_top - y_waist_bot)
    label_h = min(label_h_mm * s, max_bay_h * 0.955)
    y_mid = (y_waist_bot + y_waist_top) * 0.5
    y_l0 = y_mid - label_h * 0.5
    y_l1 = y_mid + label_h * 0.5

    l_pos, l_norm, l_uv, l_ind = [], [], [], []
    rings_y = [
        y_l0,
        y_l0 + label_h * 0.25,
        y_mid,
        y_l0 + label_h * 0.75,
        y_l1,
    ]
    seg_lbl = 96
    for r_idx, yv in enumerate(rings_y):
        v = 1.0 - (r_idx / float(len(rings_y) - 1))
        for seg in range(seg_lbl + 1):
            u = seg / float(seg_lbl)
            theta = (u - 0.5) * 2.0 * math.pi
            st, ct = math.sin(theta), math.cos(theta)
            l_pos.append((r_sleeve * st, yv, r_sleeve * ct))
            l_norm.append((st, 0.0, ct))
            l_uv.append((u, v))
    verts_per_ring = seg_lbl + 1
    for r_idx in range(len(rings_y) - 1):
        for seg in range(seg_lbl):
            c1 = r_idx * verts_per_ring + seg
            c2 = c1 + 1
            n1 = (r_idx + 1) * verts_per_ring + seg
            n2 = n1 + 1
            l_ind.extend([c1, c2, n1, c2, n2, n1])

    return [
        {"name": "BottomRing", "positions": br_pos, "normals": br_norm, "uvs": br_uv, "indices": br_ind, "material_name": "ContainerMaterial", "color": [0.09, 0.09, 0.11, 1.0], "roughness": 0.54},
        {"name": "JarBody", "positions": jb_pos, "normals": jb_norm, "uvs": jb_uv, "indices": jb_ind, "material_name": "ContainerMaterial", "color": [0.09, 0.09, 0.11, 1.0], "roughness": 0.56},
        {"name": "JarShoulder", "positions": js_pos, "normals": js_norm, "uvs": js_uv, "indices": js_ind, "material_name": "ContainerMaterial", "color": [0.09, 0.09, 0.11, 1.0], "roughness": 0.50},
        {"name": "JarNeck", "positions": jn_pos, "normals": jn_norm, "uvs": jn_uv, "indices": jn_ind, "material_name": "ContainerMaterial", "color": [0.07, 0.07, 0.09, 1.0], "roughness": 0.62},
        {"name": "CapGripRibs", "positions": cg_pos, "normals": cg_norm, "uvs": cg_uv, "indices": cg_ind, "material_name": "LidMaterial", "color": [0.08, 0.08, 0.10, 1.0], "roughness": 0.42},
        {"name": "CapCrown", "positions": cc_pos, "normals": cc_norm, "uvs": cc_uv, "indices": cc_ind, "material_name": "LidMaterial", "color": [0.08, 0.08, 0.10, 1.0], "roughness": 0.36},
        {"name": "LabelSurface", "positions": l_pos, "normals": l_norm, "uvs": l_uv, "indices": l_ind, "material_name": "LabelMaterial", "color": [1.0, 1.0, 1.0, 1.0], "roughness": 0.34},
    ]


def build_jar_or_bottle(dia_mm, h_mm, label_h_mm, is_bottle=False, segments=64, preset_id="jar_1kg"):
    if not is_bottle:
        return build_protein_jar(preset_id, dia_mm, h_mm, label_h_mm)
    """
    Builds realistic HDPE supplement tub or bottle geometry with:
    - Rounded base heel & underside
    - Cylindrical wrap waist
    - Smooth 6-step spline shoulder
    - Neck ring & collar
    - Tactile 72-ridge screw-top lid with beveled top & crown recess
    - Concentric outer LabelSurface mesh with non-mirrored glTF UVs
    """
    s = 0.005
    r_body = (dia_mm * s) * 0.5
    h_tot = h_mm * s

    if is_bottle:
        h_body = h_tot * 0.62
        h_shoulder = h_tot * 0.20
        h_neck = h_tot * 0.18
        r_neck = r_body * 0.52
        r_cap = r_neck * 1.12
    else:
        h_body = h_tot * 0.68
        h_shoulder = h_tot * 0.14
        h_neck = h_tot * 0.18
        r_neck = r_body * 0.84
        r_cap = r_neck * 1.06

    y_bot = -h_tot * 0.5
    y_waist_bot = y_bot + h_body * 0.07
    y_waist_top = y_bot + h_body
    y_neck_base = y_waist_top + h_shoulder
    y_neck_top = y_neck_base + h_neck * 0.45

    body_profile = [
        (0.0, y_bot + 0.005),
        (r_body * 0.84, y_bot),
        (r_body * 0.94, y_bot + h_body * 0.025),
        (r_body * 0.99, y_bot + h_body * 0.05),
        (r_body, y_waist_bot),
        (r_body, y_waist_top * 0.5 + y_waist_bot * 0.5),
        (r_body, y_waist_top),
    ]
    # Smooth 6-step shoulder curve (ease in-out cubic)
    for k in range(1, 7):
        t = k / 6.0
        ease = 0.5 * (1.0 - math.cos(t * math.pi))
        rk = r_body + (r_neck - r_body) * ease
        yk = y_waist_top + h_shoulder * t
        body_profile.append((rk, yk))
    body_profile.extend([
        (r_neck * 1.02, y_neck_base + 0.01),
        (r_neck, y_neck_base + 0.02),
        (r_neck, y_neck_top),
        (0.0, y_neck_top),
    ])
    b_pos, b_norm, b_uv, b_ind = _revolve_profile(body_profile, segments=segments)

    # Ribbed Screw Cap with chamfered crown recess
    y_cap_bot = y_neck_base + h_neck * 0.08
    h_cap = h_neck * 0.92
    cap_profile = [
        (r_neck * 0.96, y_cap_bot),
        (r_cap, y_cap_bot + h_cap * 0.05),
        (r_cap, y_cap_bot + h_cap * 0.45),
        (r_cap, y_cap_bot + h_cap * 0.86),
        (r_cap * 0.96, y_cap_bot + h_cap * 0.95),
        (r_cap * 0.88, y_cap_bot + h_cap),
        (r_cap * 0.80, y_cap_bot + h_cap * 0.96),
        (0.0, y_cap_bot + h_cap * 0.96),
    ]

    def cap_ridges(p_idx, theta):
        if p_idx in (1, 2, 3):
            return 0.014 * math.cos(theta * 72.0)
        return 0.0

    c_pos, c_norm, c_uv, c_ind = _revolve_profile(cap_profile, segments=96, ridge_fn=cap_ridges)

    # Label sleeve covering waist cleanly
    r_sleeve = r_body + 0.0022
    label_h = min(label_h_mm * s, (y_waist_top - y_waist_bot) * 0.95)
    y_mid = (y_waist_bot + y_waist_top) * 0.5
    y_l0 = y_mid - label_h * 0.5
    y_l1 = y_mid + label_h * 0.5

    l_pos, l_norm, l_uv, l_ind = [], [], [], []
    # Vertical rings for smoother curvature speculars
    rings_y = [y_l0, y_mid, y_l1]
    for r_idx, yv in enumerate(rings_y):
        v = 1.0 - (r_idx / 2.0)  # v=1 at bottom, v=0 at top (matches glTF flipY=false when canvas drawn top-down)
        for seg in range(segments + 1):
            # Front of model sits on +Z axis when u=0.5 (theta=0 -> +Z)
            # We wrap seam along back (-Z, theta = -pi..pi) so u=0.5 centers cleanly at +Z!
            u = seg / segments
            theta = (u - 0.5) * 2.0 * math.pi
            st, ct = math.sin(theta), math.cos(theta)
            l_pos.append((r_sleeve * st, yv, r_sleeve * ct))
            l_norm.append((st, 0.0, ct))
            l_uv.append((u, v))
    verts_per_ring = segments + 1
    for r_idx in range(len(rings_y) - 1):
        for seg in range(segments):
            c1 = r_idx * verts_per_ring + seg
            c2 = c1 + 1
            n1 = (r_idx + 1) * verts_per_ring + seg
            n2 = n1 + 1
            l_ind.extend([c1, c2, n1, c2, n2, n1])

    return [
        {"name": "Body", "positions": b_pos, "normals": b_norm, "uvs": b_uv, "indices": b_ind, "material_name": "ContainerMaterial", "color": [0.09, 0.09, 0.11, 1.0], "roughness": 0.58},
        {"name": "Lid", "positions": c_pos, "normals": c_norm, "uvs": c_uv, "indices": c_ind, "material_name": "LidMaterial", "color": [0.08, 0.08, 0.10, 1.0], "roughness": 0.45},
        {"name": "LabelSurface", "positions": l_pos, "normals": l_norm, "uvs": l_uv, "indices": l_ind, "material_name": "LabelMaterial", "color": [1.0, 1.0, 1.0, 1.0], "roughness": 0.28},
    ]


def _compute_grid_normals(grid_pos, seg_x, seg_y, invert=False):
    """Computes smooth finite-difference 3D normals across a (seg_y+1) x (seg_x+1) surface grid."""
    normals = []
    stride = seg_x + 1
    for iy in range(seg_y + 1):
        iy0 = max(0, iy - 1)
        iy1 = min(seg_y, iy + 1)
        for ix in range(seg_x + 1):
            ix0 = max(0, ix - 1)
            ix1 = min(seg_x, ix + 1)
            p_l = grid_pos[iy * stride + ix0]
            p_r = grid_pos[iy * stride + ix1]
            p_d = grid_pos[iy0 * stride + ix]
            p_u = grid_pos[iy1 * stride + ix]
            tx = (p_r[0] - p_l[0], p_r[1] - p_l[1], p_r[2] - p_l[2])
            ty = (p_u[0] - p_d[0], p_u[1] - p_d[1], p_u[2] - p_d[2])
            # Cross product tx x ty gives outward normal for (+X right, +Y up) -> +Z
            nx = tx[1] * ty[2] - tx[2] * ty[1]
            ny = tx[2] * ty[0] - tx[0] * ty[2]
            nz = tx[0] * ty[1] - tx[1] * ty[0]
            if invert:
                nx, ny, nz = -nx, -ny, -nz
            ln = math.hypot(nx, ny, nz) or 1.0
            normals.append((nx / ln, ny / ln, nz / ln))
    return normals


def _stitch_perimeter_rim(front_grid, back_grid, seg_x, seg_y):
    """Builds a watertight side-seam/seal thickness ribbon joining Front and Back boundary loops."""
    stride = seg_x + 1
    ring_f = []
    ring_b = []
    # Trace boundary CCW when looking from +Z: bottom (L->R), right (B->T), top (R->L), left (T->B)
    for ix in range(seg_x):
        idx = ix
        ring_f.append(front_grid[idx])
        ring_b.append(back_grid[idx])
    for iy in range(seg_y):
        idx = iy * stride + seg_x
        ring_f.append(front_grid[idx])
        ring_b.append(back_grid[idx])
    for ix in range(seg_x, 0, -1):
        idx = seg_y * stride + ix
        ring_f.append(front_grid[idx])
        ring_b.append(back_grid[idx])
    for iy in range(seg_y, 0, -1):
        idx = iy * stride
        ring_f.append(front_grid[idx])
        ring_b.append(back_grid[idx])

    pos, norm, uv, ind = [], [], [], []
    m = len(ring_f)
    for i in range(m):
        j = (i + 1) % m
        pf0, pf1 = ring_f[i], ring_f[j]
        pb0, pb1 = ring_b[i], ring_b[j]
        # Tangent along rim
        ex, ey, ez = pf1[0] - pf0[0], pf1[1] - pf0[1], pf1[2] - pf0[2]
        # Across thickness (+Z -> -Z)
        ax, ay, az = pb0[0] - pf0[0], pb0[1] - pf0[1], pb0[2] - pf0[2]
        nx = ey * az - ez * ay
        ny = ez * ax - ex * az
        nz = ex * ay - ey * ax
        ln = math.hypot(nx, ny, nz) or 1.0
        nvec = (nx / ln, ny / ln, nz / ln)

        base = len(pos)
        u0, u1 = i / m, (i + 1) / m
        pos.extend([pf0, pb0, pb1, pf1])
        norm.extend([nvec] * 4)
        uv.extend([(u0, 0.0), (u0, 1.0), (u1, 1.0), (u1, 0.0)])
        ind.extend([base, base + 1, base + 2, base, base + 2, base + 3])
    return pos, norm, uv, ind


def build_sachet_model(w_mm, h_mm, depth_mm):
    """
    Generates Reference Image 1 commercial metallic foil pillow sachet with FULL-BLEED artwork faces:
    - Entire front and back surfaces map [0..1]x[0..1] edge-to-edge (no floating sticker cutout!)
    - Top & bottom heat-sealed margins with fine vertical crimp ribs & side cross-ribs molded directly
      into FrontSurface and BackSurface so artwork prints seamlessly across the crimped foil seals
    - Left & right V tear notches near upper seal shoulder
    - Deeper pillow swell + realistic diagonal foil tension wrinkles & smooth finite-difference normals
    - Thin watertight FoilSealRim perimeter thickness band (1.8mm edge only)
    """
    s = 0.005
    w, h, d = w_mm * s, h_mm * s, depth_mm * s
    hw, hh = w * 0.5, h * 0.5
    seg_x, seg_y = 56, 68

    is_stickpack = (w_mm < 45 and h_mm > 90)
    seal_x = 0.072 if is_stickpack else 0.052
    seal_y = 0.070 if is_stickpack else 0.082
    seam_half_z = 0.0018

    def _sachet_eval(nx, ny, sign, is_front):
        notch = math.exp(-((ny - 0.895) / 0.011) ** 2) * (0.022 * w)
        edge_tuck = notch * (max(0.0, 1.0 - nx / 0.04) + max(0.0, 1.0 - (1.0 - nx) / 0.04))
        x = -hw + nx * w + (edge_tuck if nx < 0.5 else -edge_tuck)
        y = -hh + ny * h

        if ny <= seal_y or ny >= (1.0 - seal_y):
            y_inf = 0.0
            vy_norm = 0.0 if ny <= seal_y else 1.0
        else:
            vy_norm = (ny - seal_y) / (1.0 - 2.0 * seal_y)
            y_inf = math.sin(vy_norm * math.pi) ** 0.68
            y_inf *= (1.10 - 0.16 * vy_norm)

        if nx <= seal_x or nx >= (1.0 - seal_x):
            x_inf = 0.0
            ux_norm = 0.0 if nx <= seal_x else 1.0
        else:
            ux_norm = (nx - seal_x) / (1.0 - 2.0 * seal_x)
            x_inf = math.sin(ux_norm * math.pi) ** 0.72

        core_belly = (d * 0.68) * x_inf * y_inf

        top_mask = max(0.0, min(1.0, (ny - (1.0 - seal_y - 0.01)) / 0.024))
        bot_mask = max(0.0, min(1.0, ((seal_y + 0.01) - ny) / 0.024))
        side_mask = max(
            max(0.0, min(1.0, ((seal_x + 0.01) - nx) / 0.02)),
            max(0.0, min(1.0, (nx - (1.0 - seal_x - 0.01)) / 0.02)),
        )
        crimp_v = (top_mask + bot_mask) * 0.0028 * math.sin(nx * math.pi * 64.0)
        crimp_s = side_mask * (1.0 - max(top_mask, bot_mask)) * 0.0016 * math.sin(ny * math.pi * 56.0)

        foil_wrinkle = 0.0
        if x_inf > 0.01 and y_inf > 0.01:
            phase_seed = 0.0 if is_front else 1.25
            pinch_top_bot = math.exp(-((vy_norm - 0.055) * 13.0) ** 2) + math.exp(-((vy_norm - 0.945) * 13.0) ** 2)
            corner_diag1 = math.sin((ux_norm * 4.4 + vy_norm * 3.2 + phase_seed) * math.pi)
            corner_diag2 = math.sin(((1.0 - ux_norm) * 4.6 + (1.0 - vy_norm) * 3.5 + phase_seed) * math.pi)
            foil_wrinkle = (
                0.0038 * (corner_diag1 + 0.85 * corner_diag2) * (1.0 - 0.42 * x_inf * y_inf)
                + 0.0030 * pinch_top_bot * math.cos(ux_norm * math.pi * 6.5)
            ) * x_inf

        z = sign * (seam_half_z + core_belly + crimp_v + crimp_s + foil_wrinkle)
        return (x, y, z)

    def _sachet_face(is_front=True):
        grid_pos, uvs, ind = [], [], []
        sign = 1.0 if is_front else -1.0
        stride = seg_x + 1
        for iy in range(seg_y + 1):
            ny = iy / seg_y
            for ix in range(seg_x + 1):
                nx = ix / seg_x
                grid_pos.append(_sachet_eval(nx, ny, sign, is_front))
                uvs.append((nx if is_front else (1.0 - nx), 1.0 - ny))
        norm = _compute_grid_normals(grid_pos, seg_x, seg_y, invert=(not is_front))
        for iy in range(seg_y):
            for ix in range(seg_x):
                c1 = iy * stride + ix
                c2 = c1 + 1
                n1 = (iy + 1) * stride + ix
                n2 = n1 + 1
                if is_front:
                    ind.extend([c1, c2, n1, c2, n2, n1])
                else:
                    ind.extend([c1, n1, c2, c2, n1, n2])
        return grid_pos, norm, uvs, ind

    f_pos, f_norm, f_uv, f_ind = _sachet_face(True)
    b_pos, b_norm, b_uv, b_ind = _sachet_face(False)
    r_pos, r_norm, r_uv, r_ind = _stitch_perimeter_rim(f_pos, b_pos, seg_x, seg_y)

    return [
        {"name": "FrontSurface", "positions": f_pos, "normals": f_norm, "uvs": f_uv, "indices": f_ind, "material_name": "FrontLabelMaterial", "color": [1.0, 1.0, 1.0, 1.0], "metallic": 0.48, "roughness": 0.25},
        {"name": "BackSurface", "positions": b_pos, "normals": b_norm, "uvs": b_uv, "indices": b_ind, "material_name": "BackLabelMaterial", "color": [1.0, 1.0, 1.0, 1.0], "metallic": 0.48, "roughness": 0.25},
        {"name": "FoilSealRim", "positions": r_pos, "normals": r_norm, "uvs": r_uv, "indices": r_ind, "material_name": "SealMaterial", "color": [0.85, 0.71, 0.38, 1.0], "metallic": 0.88, "roughness": 0.24},
    ]


def build_pouch_or_sachet(w_mm, h_mm, depth_mm, is_sachet=False, variant="standup"):
    """
    Dispatcher building either:
      - Metallic foil pillow sachet (Reference Image 1), or
      - Commercial Stand-Up Doypack Pouch with flared bottom gusset, molded top zipper ridge,
        sealed side fins, natural pouch folds, and smooth finite-difference normals (Reference Image 2).
    """
    if is_sachet:
        return build_sachet_model(w_mm, h_mm, depth_mm)

    s = 0.005
    w, h, d = w_mm * s, h_mm * s, depth_mm * s
    hw, hh = w * 0.5, h * 0.5
    seg_x, seg_y = 56, 68
    is_flat_bottom = (w_mm >= 230 or depth_mm >= 105)

    # Doypack vertical landmarks (ny: 0=bottom, 1=top)
    ny_zip_bot, ny_zip_top = 0.835, 0.895
    ny_seal_top = 0.90
    side_fin = 0.042
    seam_half_z = 0.0020

    def _doypack_half_depth(nx, ny):
        # Outer left/right sealed edge fins stay pinched flat except right at bottom gusset corners
        if nx <= side_fin or nx >= (1.0 - side_fin):
            x_bell = 0.0
            ux = 0.0 if nx <= side_fin else 1.0
        else:
            ux = (nx - side_fin) / (1.0 - 2.0 * side_fin)
            x_bell = math.sin(ux * math.pi) ** 0.62

        # Vertical Doypack silhouette: open wide at bottom (ny=0..0.18), taper smoothly to zipper (ny=0.835)
        if ny >= ny_seal_top:
            y_bell = 0.0
        elif ny >= ny_zip_bot:
            # Pinched zipper transition + raised press-to-close zipper rib!
            t_zip = (ny - ny_zip_bot) / (ny_seal_top - ny_zip_bot)
            base_taper = (1.0 - t_zip) * 0.14
            rib1 = math.exp(-((ny - 0.858) / 0.0065) ** 2) * 0.032
            rib2 = math.exp(-((ny - 0.876) / 0.0055) ** 2) * 0.024
            y_bell = base_taper + (rib1 + rib2) / max(0.08, d * 0.5)
        elif ny <= 0.14:
            # Bottom standing gusset flare: reaches max depth quickly from bottom lip ny=0..0.14
            t_bot = ny / 0.14
            y_bell = 0.72 + 0.28 * math.sin(t_bot * math.pi * 0.5)
            # Soften center bottom tuck slightly for authentic Doypack foot curve
            if ny < 0.035:
                y_bell *= (0.86 + 0.14 * (ny / 0.035))
        else:
            # Full belly tapering gracefully from lower swell (ny=0.14) up to zipper (ny=0.835)
            t_mid = (ny - 0.14) / (ny_zip_bot - 0.14)
            y_bell = (1.0 - 0.86 * (t_mid ** 1.25))

        if is_flat_bottom:
            # Flat-bottom 2kg box pouch keeps squarer shoulders horizontally
            x_bell = math.sin(ux * math.pi) ** 0.42 if (side_fin < nx < 1.0 - side_fin) else 0.0

        z_core = (d * 0.50) * x_bell * y_bell

        # Natural stand-up pouch corner creases & subtle laminate ripples (more tactile definition)
        fold = 0.0
        if x_bell > 0.04 and 0.03 < ny < ny_zip_bot:
            v_rel = (ny - 0.03) / (ny_zip_bot - 0.03)
            # Corner diagonal stress folds near bottom gusset + zipper pinch crease
            c_left = math.exp(-((ux - 0.16 * (1.0 - v_rel)) / 0.085) ** 2) * math.sin(v_rel * math.pi * 3.0)
            c_right = math.exp(-(((1.0 - ux) - 0.16 * (1.0 - v_rel)) / 0.085) ** 2) * math.sin(v_rel * math.pi * 3.0)
            zip_pinch = math.exp(-((ny - 0.815) / 0.022) ** 2) * math.sin(ux * math.pi * 5.0)
            mid_rip = math.sin((ux * 3.2 + v_rel * 4.5) * math.pi) * (1.0 - 0.50 * math.sin(ux * math.pi))
            fold = (0.0052 * (c_left + c_right) * (1.0 - 0.65 * v_rel) + 0.0024 * mid_rip + 0.0022 * zip_pinch) * min(1.0, y_bell * 1.4)

        # Heat-seal horizontal micro-crimp along top flange above zipper
        top_crimp = 0.0
        if ny > ny_zip_top:
            crimp_fade = (ny - ny_zip_top) / (1.0 - ny_zip_top)
            top_crimp = 0.0022 * crimp_fade * math.sin(nx * math.pi * 56.0)

        return seam_half_z + z_core * 1.12 + fold + top_crimp

    def _pouch_side(is_front=True):
        grid_pos, uvs, ind = [], [], []
        sign = 1.0 if is_front else -1.0
        stride = seg_x + 1

        for iy in range(seg_y + 1):
            ny = iy / seg_y
            y = -hh + ny * h

            # Stand-up pouch subtle waist silhouette: gently wider bottom corners, subtle waist, clean top seal
            width_scale = 1.0 - 0.025 * math.sin(ny * math.pi * 0.85) if ny < ny_seal_top else 0.985
            notch = math.exp(-((ny - 0.922) / 0.011) ** 2) * (0.020 * w)

            for ix in range(seg_x + 1):
                nx = ix / seg_x
                edge_tuck = notch * (max(0.0, 1.0 - nx / 0.04) + max(0.0, 1.0 - (1.0 - nx) / 0.04))
                x = (-hw + nx * w) * width_scale + (edge_tuck if nx < 0.5 else -edge_tuck)
                z = sign * _doypack_half_depth(nx, ny)
                grid_pos.append((x, y, z))
                u = nx if is_front else (1.0 - nx)
                v = 1.0 - ny
                uvs.append((u, v))

        norm = _compute_grid_normals(grid_pos, seg_x, seg_y, invert=(not is_front))
        for iy in range(seg_y):
            for ix in range(seg_x):
                c1 = iy * stride + ix
                c2 = c1 + 1
                n1 = (iy + 1) * stride + ix
                n2 = n1 + 1
                if is_front:
                    ind.extend([c1, c2, n1, c2, n2, n1])
                else:
                    ind.extend([c1, n1, c2, c2, n1, n2])
        return grid_pos, norm, uvs, ind

    f_pos, f_norm, f_uv, f_ind = _pouch_side(True)
    b_pos, b_norm, b_uv, b_ind = _pouch_side(False)

    # Authentic concave W-fold bottom gusset spanning Front(iy=0) <-> Back(iy=0)
    g_pos, g_uv, g_ind = [], [], []
    seg_g = 12
    for ig in range(seg_g + 1):
        tg = ig / seg_g  # 0 at front bottom edge, 1 at back bottom edge
        # Tuck upward cleanly into an arched interior pocket inside the base!
        arch = math.sin(tg * math.pi)
        for ix in range(seg_x + 1):
            nx = ix / seg_x
            pf = f_pos[ix]
            pb = b_pos[ix]
            gx = pf[0]
            gz = pf[2] + (pb[2] - pf[2]) * tg
            x_bell = math.sin(max(0.0, min(1.0, (nx - side_fin) / (1.0 - 2.0 * side_fin))) * math.pi) if (side_fin < nx < 1.0 - side_fin) else 0.0
            gy = -hh + (d * 0.28) * arch * x_bell
            g_pos.append((gx, gy, gz))
            g_uv.append((nx, tg))
    g_norm = _compute_grid_normals(g_pos, seg_x, seg_g, invert=True)
    for ig in range(seg_g):
        for ix in range(seg_x):
            c1 = ig * (seg_x + 1) + ix
            c2 = c1 + 1
            n1 = (ig + 1) * (seg_x + 1) + ix
            n2 = n1 + 1
            g_ind.extend([c1, n1, c2, c2, n1, n2])

    # Side & Top heat-sealed rim stitching Front & Back edges (exclude bottom edge closed by BottomGusset)
    stride = seg_x + 1
    rim_f, rim_b = [], []
    for iy in range(seg_y):
        rim_f.append(f_pos[iy * stride + seg_x])
        rim_b.append(b_pos[iy * stride + seg_x])
    for ix in range(seg_x, 0, -1):
        rim_f.append(f_pos[seg_y * stride + ix])
        rim_b.append(b_pos[seg_y * stride + ix])
    for iy in range(seg_y, -1, -1):
        rim_f.append(f_pos[iy * stride])
        rim_b.append(b_pos[iy * stride])

    r_pos, r_norm, r_uv, r_ind = [], [], [], []
    for i in range(len(rim_f) - 1):
        pf0, pf1 = rim_f[i], rim_f[i + 1]
        pb0, pb1 = rim_b[i], rim_b[i + 1]
        ex, ey, ez = pf1[0] - pf0[0], pf1[1] - pf0[1], pf1[2] - pf0[2]
        ax, ay, az = pb0[0] - pf0[0], pb0[1] - pf0[1], pb0[2] - pf0[2]
        nx_v = ey * az - ez * ay
        ny_v = ez * ax - ex * az
        nz_v = ex * ay - ey * ax
        ln = math.hypot(nx_v, ny_v, nz_v) or 1.0
        nv = (nx_v / ln, ny_v / ln, nz_v / ln)
        base = len(r_pos)
        u0, u1 = i / max(1, len(rim_f) - 1), (i + 1) / max(1, len(rim_f) - 1)
        r_pos.extend([pf0, pb0, pb1, pf1])
        r_norm.extend([nv] * 4)
        r_uv.extend([(u0, 0.0), (u0, 1.0), (u1, 1.0), (u1, 0.0)])
        r_ind.extend([base, base + 1, base + 2, base, base + 2, base + 3])

    return [
        {"name": "FrontSurface", "positions": f_pos, "normals": f_norm, "uvs": f_uv, "indices": f_ind, "material_name": "FrontLabelMaterial", "color": [1.0, 1.0, 1.0, 1.0], "roughness": 0.42},
        {"name": "BackSurface", "positions": b_pos, "normals": b_norm, "uvs": b_uv, "indices": b_ind, "material_name": "BackLabelMaterial", "color": [1.0, 1.0, 1.0, 1.0], "roughness": 0.42},
        {"name": "BottomGusset", "positions": g_pos, "normals": g_norm, "uvs": g_uv, "indices": g_ind, "material_name": "GussetMaterial", "color": [0.92, 0.93, 0.95, 1.0], "roughness": 0.46},
        {"name": "PouchSealRim", "positions": r_pos, "normals": r_norm, "uvs": r_uv, "indices": r_ind, "material_name": "SealMaterial", "color": [0.90, 0.91, 0.93, 1.0], "roughness": 0.44},
    ]


def build_clean_box_geometry(w, h, d, y_offset=0.0):
    """Builds true 24-vertex box geometry so each face has sharp normals & exact 0..1 UVs."""
    hw, hh, hd = w * 0.5, h * 0.5, d * 0.5
    yo = y_offset
    faces = [
        # Front (+Z)
        ([(-hw, -hh + yo, hd), (hw, -hh + yo, hd), (hw, hh + yo, hd), (-hw, hh + yo, hd)], (0, 0, 1)),
        # Back (-Z)
        ([(hw, -hh + yo, -hd), (-hw, -hh + yo, -hd), (-hw, hh + yo, -hd), (hw, hh + yo, -hd)], (0, 0, -1)),
        # Right (+X)
        ([(hw, -hh + yo, hd), (hw, -hh + yo, -hd), (hw, hh + yo, -hd), (hw, hh + yo, hd)], (1, 0, 0)),
        # Left (-X)
        ([(-hw, -hh + yo, -hd), (-hw, -hh + yo, hd), (-hw, hh + yo, hd), (-hw, hh + yo, -hd)], (-1, 0, 0)),
        # Top (+Y)
        ([(-hw, hh + yo, hd), (hw, hh + yo, hd), (hw, hh + yo, -hd), (-hw, hh + yo, -hd)], (0, 1, 0)),
        # Bottom (-Y)
        ([(-hw, -hh + yo, -hd), (hw, -hh + yo, -hd), (hw, -hh + yo, hd), (-hw, -hh + yo, hd)], (0, -1, 0)),
    ]
    pos, norm, uv, ind = [], [], [], []
    for f_idx, (verts, nvec) in enumerate(faces):
        base = f_idx * 4
        pos.extend(verts)
        norm.extend([nvec] * 4)
        uv.extend([(0, 1), (1, 1), (1, 0), (0, 0)])
        ind.extend([base, base + 1, base + 2, base, base + 2, base + 3])
    return pos, norm, uv, ind


def build_carton_box(w_mm, h_mm, depth_mm):
    """
    Builds a crisp commercial folding carton with 6 independent printable surface meshes
    (Front, Back, Left, Right, Top, Bottom) with non-mirrored glTF UVs + inset cardboard core.
    """
    s = 0.005
    w, h, d = w_mm * s, h_mm * s, depth_mm * s
    hw, hh, hd = w * 0.5, h * 0.5, d * 0.5
    eps = 0.0008

    # Slightly inset core body (visible only at crisp 0.8mm cardboard edge seams)
    b_pos, b_norm, b_uv, b_ind = build_clean_box_geometry(w * 0.996, h * 0.996, d * 0.996)

    def _face_quad(verts, nvec):
        return verts, [nvec] * 4, [(0, 1), (1, 1), (1, 0), (0, 0)], [0, 1, 2, 0, 2, 3]

    # Exact outward orientation & non-mirrored screen-space UVs when viewing each face straight-on
    front_p, front_n, front_u, front_i = _face_quad(
        [(-hw, -hh, hd + eps), (hw, -hh, hd + eps), (hw, hh, hd + eps), (-hw, hh, hd + eps)], (0, 0, 1)
    )
    back_p, back_n, back_u, back_i = _face_quad(
        [(hw, -hh, -hd - eps), (-hw, -hh, -hd - eps), (-hw, hh, -hd - eps), (hw, hh, -hd - eps)], (0, 0, -1)
    )
    right_p, right_n, right_u, right_i = _face_quad(
        [(hw + eps, -hh, hd), (hw + eps, -hh, -hd), (hw + eps, hh, -hd), (hw + eps, hh, hd)], (1, 0, 0)
    )
    left_p, left_n, left_u, left_i = _face_quad(
        [(-hw - eps, -hh, -hd), (-hw - eps, -hh, hd), (-hw - eps, hh, hd), (-hw - eps, hh, -hd)], (-1, 0, 0)
    )
    top_p, top_n, top_u, top_i = _face_quad(
        [(-hw, hh + eps, hd), (hw, hh + eps, hd), (hw, hh + eps, -hd), (-hw, hh + eps, -hd)], (0, 1, 0)
    )
    bot_p, bot_n, bot_u, bot_i = _face_quad(
        [(-hw, -hh - eps, -hd), (hw, -hh - eps, -hd), (hw, -hh - eps, hd), (-hw, -hh - eps, hd)], (0, -1, 0)
    )

    return [
        {"name": "CartonBody", "positions": b_pos, "normals": b_norm, "uvs": b_uv, "indices": b_ind, "material_name": "ContainerMaterial", "color": [0.76, 0.62, 0.45, 1.0], "roughness": 0.78},
        {"name": "BoxFrontSurface", "positions": front_p, "normals": front_n, "uvs": front_u, "indices": front_i, "material_name": "BoxFrontMaterial", "color": [1.0, 1.0, 1.0, 1.0], "roughness": 0.45},
        {"name": "BoxBackSurface", "positions": back_p, "normals": back_n, "uvs": back_u, "indices": back_i, "material_name": "BoxBackMaterial", "color": [1.0, 1.0, 1.0, 1.0], "roughness": 0.45},
        {"name": "BoxLeftSurface", "positions": left_p, "normals": left_n, "uvs": left_u, "indices": left_i, "material_name": "BoxLeftMaterial", "color": [1.0, 1.0, 1.0, 1.0], "roughness": 0.45},
        {"name": "BoxRightSurface", "positions": right_p, "normals": right_n, "uvs": right_u, "indices": right_i, "material_name": "BoxRightMaterial", "color": [1.0, 1.0, 1.0, 1.0], "roughness": 0.45},
        {"name": "BoxTopSurface", "positions": top_p, "normals": top_n, "uvs": top_u, "indices": top_i, "material_name": "BoxTopMaterial", "color": [1.0, 1.0, 1.0, 1.0], "roughness": 0.48},
        {"name": "BoxBottomSurface", "positions": bot_p, "normals": bot_n, "uvs": bot_u, "indices": bot_i, "material_name": "BoxBottomMaterial", "color": [1.0, 1.0, 1.0, 1.0], "roughness": 0.52},
    ]


def main():
    base_dir = "static/models/packaging"
    os.makedirs(base_dir, exist_ok=True)
    os.makedirs(os.path.join(base_dir, "thumbnails"), exist_ok=True)

    manifest = {
        "platform": "GOMZI BOB 3D Packaging Studio",
        "version": "3.0.0",
        "engine": "Three.js / WebGL / GLTFLoader / PBR",
        "categories": [
            {
                "id": "jar",
                "name": "Protein Jar",
                "thumbnail": "/static/models/packaging/thumbnails/jar.png",
                "presets": [
                    {"id": "jar_100g", "name": "100 g Jar", "capacity": "100 g", "dia": 72, "h": 88, "label_w": 225, "label_h": 55, "file": "whey/whey_100g.glb", "recommended_ratio": "3:1"},
                    {"id": "jar_250g", "name": "250 g Jar", "capacity": "250 g", "dia": 92, "h": 110, "label_w": 288, "label_h": 72, "file": "whey/whey_250g.glb", "recommended_ratio": "3:1"},
                    {"id": "jar_300g", "name": "300 g Pre-Workout Jar", "capacity": "300 g", "dia": 98, "h": 118, "label_w": 308, "label_h": 78, "file": "whey/whey_300g.glb", "recommended_ratio": "3:1"},
                    {"id": "jar_500g", "name": "500 g Protein Jar", "capacity": "500 g", "dia": 108, "h": 162, "label_w": 338, "label_h": 110, "file": "whey/whey_500g.glb", "recommended_ratio": "3:1"},
                    {"id": "jar_1kg", "name": "1 kg (1000 g)", "capacity": "1 kg (1000 g)", "dia": 144, "h": 215, "label_w": 452, "label_h": 142, "file": "whey/whey_1kg.glb", "recommended_ratio": "3:1"},
                    {"id": "jar_2kg", "name": "2 kg (2000 g)", "capacity": "2 kg (2000 g)", "dia": 178, "h": 272, "label_w": 560, "label_h": 178, "file": "whey/whey_2kg.glb", "recommended_ratio": "3:1"},
                    {"id": "jar_2_5kg", "name": "2.5 kg Tub", "capacity": "2.5 kg", "dia": 190, "h": 295, "label_w": 595, "label_h": 192, "file": "whey/whey_2_5kg.glb", "recommended_ratio": "3:1"},
                    {"id": "jar_3kg", "name": "3 kg Mass Gainer", "capacity": "3 kg", "dia": 205, "h": 318, "label_w": 640, "label_h": 205, "file": "whey/whey_3kg.glb", "recommended_ratio": "3:1"},
                    {"id": "jar_5kg", "name": "5 kg Mega Tub", "capacity": "5 kg", "dia": 240, "h": 370, "label_w": 750, "label_h": 240, "file": "whey/whey_5kg.glb", "recommended_ratio": "3:1"},
                ],
            },
            {
                "id": "pouch",
                "name": "Pouch",
                "thumbnail": "/static/models/packaging/thumbnails/pouch.png",
                "presets": [
                    {"id": "pouch_100g", "name": "100 g Stand-up Zipper", "capacity": "100 g", "w": 110, "h": 170, "depth": 60, "label_w": 110, "label_h": 140, "file": "pouches/standup_100g.glb", "recommended_ratio": "2:3"},
                    {"id": "pouch_250g", "name": "250 g Stand-up Zipper", "capacity": "250 g", "w": 130, "h": 200, "depth": 70, "label_w": 130, "label_h": 170, "file": "pouches/standup_250g.glb", "recommended_ratio": "2:3"},
                    {"id": "pouch_500g", "name": "500 g Stand-up Pouch", "capacity": "500 g", "w": 160, "h": 240, "depth": 80, "label_w": 160, "label_h": 200, "file": "pouches/standup_500g.glb", "recommended_ratio": "2:3"},
                    {"id": "pouch_1kg", "name": "1 kg Protein Refill Pouch", "capacity": "1 kg", "w": 190, "h": 290, "depth": 90, "label_w": 190, "label_h": 240, "file": "pouches/standup_1kg.glb", "recommended_ratio": "2:3"},
                    {"id": "pouch_2kg", "name": "2 kg Flat-Bottom Pouch", "capacity": "2 kg", "w": 240, "h": 340, "depth": 110, "label_w": 240, "label_h": 280, "file": "pouches/standup_2kg.glb", "recommended_ratio": "2:3"},
                ],
            },
            {
                "id": "sachet",
                "name": "Sachet",
                "thumbnail": "/static/models/packaging/thumbnails/sachet.png",
                "presets": [
                    {"id": "sachet_70x110", "name": "70 × 110 mm Sachet", "capacity": "30 g Serve", "w": 70, "h": 110, "depth": 16, "label_w": 70, "label_h": 110, "file": "sachets/sachet_10g.glb", "recommended_ratio": "7:11"},
                    {"id": "sachet_protein", "name": "Single-Serve Protein Sachet", "capacity": "35 g", "w": 90, "h": 140, "depth": 20, "label_w": 90, "label_h": 140, "file": "sachets/sachet_30g.glb", "recommended_ratio": "7:11"},
                    {"id": "stickpack_5g", "name": "5 g Stick Pack", "capacity": "5 g", "w": 32, "h": 135, "depth": 12, "label_w": 32, "label_h": 135, "file": "sachets/stickpack_5g.glb", "recommended_ratio": "9:16"},
                ],
            },
            {
                "id": "bottle",
                "name": "Bottle",
                "thumbnail": "/static/models/packaging/thumbnails/bottle.png",
                "presets": [
                    {"id": "capsule_30", "name": "30 Capsules Bottle", "capacity": "30 caps", "dia": 46, "h": 82, "label_w": 144, "label_h": 48, "file": "bottles/capsule_30.glb", "recommended_ratio": "3:1"},
                    {"id": "capsule_60", "name": "60 Capsules Bottle", "capacity": "60 caps", "dia": 54, "h": 98, "label_w": 168, "label_h": 60, "file": "bottles/capsule_60.glb", "recommended_ratio": "3:1"},
                    {"id": "capsule_90", "name": "90 Capsules Bottle", "capacity": "90 caps", "dia": 60, "h": 114, "label_w": 188, "label_h": 72, "file": "bottles/capsule_90.glb", "recommended_ratio": "3:1"},
                    {"id": "capsule_120", "name": "120 Capsules Bottle", "capacity": "120 caps", "dia": 66, "h": 128, "label_w": 206, "label_h": 82, "file": "bottles/capsule_120.glb", "recommended_ratio": "3:1"},
                    {"id": "capsule_180", "name": "180 Capsules Bottle", "capacity": "180 caps", "dia": 74, "h": 148, "label_w": 230, "label_h": 96, "file": "bottles/capsule_180.glb", "recommended_ratio": "3:1"},
                ],
            },
            {
                "id": "box",
                "name": "Box",
                "thumbnail": "/static/models/packaging/thumbnails/box.png",
                "presets": [
                    {"id": "box_supplement", "name": "Supplement Carton Box", "capacity": "Standard", "w": 120, "h": 180, "depth": 100, "label_w": 120, "label_h": 180, "file": "boxes/carton_box.glb", "recommended_ratio": "2:3"},
                    {"id": "box_square", "name": "Square Gift Carton", "capacity": "120×120×120", "w": 120, "h": 120, "depth": 120, "label_w": 120, "label_h": 120, "file": "boxes/square_box.glb", "recommended_ratio": "1:1"},
                    {"id": "box_cosmetic", "name": "Medicine / Cosmetic Box", "capacity": "65×145×50", "w": 65, "h": 145, "depth": 50, "label_w": 65, "label_h": 145, "file": "boxes/cosmetic_box.glb", "recommended_ratio": "2:3"},
                ],
            },
        ],
        "materials": [
            {"id": "matte", "name": "Matte Plastic", "roughness": 0.68, "metalness": 0.02, "clearcoat": 0.05},
            {"id": "glossy", "name": "Glossy Plastic", "roughness": 0.14, "metalness": 0.02, "clearcoat": 0.85},
            {"id": "satin", "name": "Satin Plastic", "roughness": 0.36, "metalness": 0.03, "clearcoat": 0.35},
            {"id": "soft_touch", "name": "Soft Touch", "roughness": 0.82, "metalness": 0.0, "clearcoat": 0.0},
            {"id": "transparent", "name": "Transparent PET", "roughness": 0.08, "metalness": 0.0, "transmission": 0.85, "opacity": 0.55},
            {"id": "frosted", "name": "Frosted Plastic", "roughness": 0.45, "metalness": 0.0, "transmission": 0.6, "opacity": 0.75},
            {"id": "metallic_foil", "name": "Metallic Foil", "roughness": 0.24, "metalness": 0.88, "clearcoat": 0.35},
            {"id": "matte_foil", "name": "Matte Foil", "roughness": 0.48, "metalness": 0.72, "clearcoat": 0.1},
            {"id": "glossy_foil", "name": "Glossy Foil", "roughness": 0.14, "metalness": 0.90, "clearcoat": 0.85},
            {"id": "kraft_paper", "name": "Kraft Paper", "roughness": 0.88, "metalness": 0.0, "clearcoat": 0.0},
            {"id": "cardboard", "name": "Cardboard", "roughness": 0.82, "metalness": 0.0, "clearcoat": 0.0},
        ],
        "lighting_presets": [
            {"id": "studio", "name": "Studio", "key": "#ffffff", "fill": "#e8edf2", "rim": "#cbd5e1", "keyInt": 1.15, "fillInt": 0.72, "env": 1.0},
            {"id": "soft", "name": "Soft", "key": "#fffdf7", "fill": "#f1f5f9", "rim": "#cbd5e1", "keyInt": 0.88, "fillInt": 0.85, "env": 0.9},
            {"id": "natural", "name": "Natural", "key": "#fff5d6", "fill": "#dceeff", "rim": "#fed7aa", "keyInt": 1.08, "fillInt": 0.76, "env": 0.95},
            {"id": "dramatic", "name": "Dramatic", "key": "#ffffff", "fill": "#475569", "rim": "#e2e8f0", "keyInt": 1.55, "fillInt": 0.35, "env": 0.65},
        ],
    }

    with open(os.path.join(base_dir, "manifest.json"), "w", encoding="utf-8") as f:
        json.dump(manifest, f, indent=2)

    for cat in manifest["categories"]:
        cat_id = cat["id"]
        for preset in cat["presets"]:
            out_full = os.path.join(base_dir, preset["file"])
            os.makedirs(os.path.dirname(out_full), exist_ok=True)
            if cat_id in ("jar", "bottle"):
                meshes = build_jar_or_bottle(
                    preset["dia"], preset["h"], preset["label_h"],
                    is_bottle=(cat_id == "bottle"),
                    preset_id=preset["id"],
                )
            elif cat_id in ("pouch", "sachet"):
                meshes = build_pouch_or_sachet(preset["w"], preset["h"], preset["depth"], is_sachet=(cat_id == "sachet"))
            else:
                meshes = build_carton_box(preset["w"], preset["h"], preset["depth"])
            glb_bytes = build_glb(meshes)
            with open(out_full, "wb") as fout:
                fout.write(glb_bytes)
            print(f"OK GLB: {preset['file']} ({len(glb_bytes)} bytes)")


if __name__ == "__main__":
    main()
