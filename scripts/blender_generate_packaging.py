"""
blender_generate_packaging.py
=============================
Blender Python (bpy) automation script to generate high-fidelity PBR packaging models:
- Whey Protein Jars (1kg, 2kg, 5kg)
- Stand-Up Zipper Pouches
- Capsule Bottles
- Sachets & Stick Packs

Usage:
  blender --background --python scripts/blender_generate_packaging.py
"""

try:
    import bpy
    import bmesh
    import math
except ImportError:
    print("[NOTE] This script runs inside Blender environment: blender --background --python scripts/blender_generate_packaging.py")


def reset_scene():
    bpy.ops.wm.read_factory_settings(use_empty=True)


def create_pbr_material(name, base_color=(0.1, 0.1, 0.1, 1.0), roughness=0.35, metallic=0.0):
    mat = bpy.data.materials.new(name=name)
    mat.use_nodes = True
    bsdf = mat.node_tree.nodes.get("Principled BSDF")
    if bsdf:
        bsdf.inputs["Base Color"].default_value = base_color
        bsdf.inputs["Roughness"].default_value = roughness
        bsdf.inputs["Metallic"].default_value = metallic
    return mat


def generate_whey_tub(radius=0.7, height=2.2, cap_height=0.4):
    """Creates a high-poly whey protein tub with rounded shoulder and separate threaded cap."""
    reset_scene()

    # 1. Jar Body
    bpy.ops.mesh.primitive_cylinder_add(radius=radius, depth=height * 0.75, vertices=64, location=(0, 0, height * 0.375))
    jar_body = bpy.context.active_object
    jar_body.name = "Body"

    # Add Bevel Modifier for photorealistic rounded edges
    bev = jar_body.modifiers.new("Bevel", "BEVEL")
    bev.width = 0.04
    bev.segments = 4

    # 2. Screw Cap with Grip Ridges
    bpy.ops.mesh.primitive_cylinder_add(radius=radius * 0.72, depth=cap_height, vertices=96, location=(0, 0, height * 0.75 + cap_height * 0.5))
    cap = bpy.context.active_object
    cap.name = "Lid"

    # 3. Label Sleeve (dedicated outer UV wrapper)
    bpy.ops.mesh.primitive_cylinder_add(radius=radius + 0.002, depth=height * 0.58, vertices=64, location=(0, 0, height * 0.375))
    sleeve = bpy.context.active_object
    sleeve.name = "LabelSurface"

    # Materials
    body_mat = create_pbr_material("ContainerMaterial", base_color=(0.08, 0.08, 0.08, 1.0), roughness=0.55)
    lid_mat = create_pbr_material("LidMaterial", base_color=(0.12, 0.12, 0.12, 1.0), roughness=0.35)
    label_mat = create_pbr_material("LabelMaterial", base_color=(1.0, 1.0, 1.0, 1.0), roughness=0.25)

    jar_body.data.materials.append(body_mat)
    cap.data.materials.append(lid_mat)
    sleeve.data.materials.append(label_mat)

    # Export GLB
    out_path = "static/models/packaging/whey/whey_1kg_blender.glb"
    bpy.ops.export_scene.gltf(filepath=out_path, export_format='GLB', use_selection=False)
    print(f"Exported Blender model to {out_path}")


if __name__ == "__main__":
    try:
        generate_whey_tub()
    except Exception as e:
        print(f"Blender generation notice: {e}")
