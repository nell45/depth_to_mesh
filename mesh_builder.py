"""
Blender scene construction.

All bpy calls live here. This module is always called from the main thread.
"""

import bmesh
import bpy
import numpy as np

_COLLECTION_NAME = "DepthMeshOutput"
_ALBEDO_SUFFIX = "_albedo"
_DEPTH_SUFFIX = "_depth"
_DEPTH_TEX_SUFFIX = "_depth_tex"
_MAT_SUFFIX = "_mat"


# ---------------------------------------------------------------------------
# EXR loader (must run on the main thread — uses bpy)
# ---------------------------------------------------------------------------

def load_exr(path: str) -> np.ndarray:
    """
    Load an EXR file via Blender's OpenImageIO backend and return it as a
    H x W x 3 float32 array in [0, 1].

    Must be called from the main thread. The temporary image data block
    is removed after the pixels are extracted.
    """
    img = bpy.data.images.load(path)
    try:
        W, H = img.size
        pixels = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)
        rgb = pixels[::-1, :, :3].copy()
    finally:
        bpy.data.images.remove(img)

    p99 = np.percentile(rgb, 99)
    if p99 > 0:
        rgb = rgb / p99
    return np.clip(rgb, 0.0, 1.0)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _get_or_create_collection(name: str) -> bpy.types.Collection:
    if name in bpy.data.collections:
        return bpy.data.collections[name]
    col = bpy.data.collections.new(name)
    bpy.context.scene.collection.children.link(col)
    return col


def _array_to_image(
    name: str,
    array: np.ndarray,
    is_data: bool = False,
) -> bpy.types.Image:
    """
    Create a Blender image data block from a numpy array.

    Args:
        name:    Data block name.
        array:   H x W x 3 float32 (RGB) or H x W float32 (grayscale), [0, 1].
        is_data: Use 'Non-Color' color space (correct for depth maps).
    """
    if array.ndim == 2:
        array = np.stack([array, array, array], axis=2)

    H, W = array.shape[:2]

    img = bpy.data.images.new(
        name, width=W, height=H, float_buffer=is_data, alpha=False
    )
    img.colorspace_settings.name = "Non-Color" if is_data else "sRGB"

    rgba = np.ones((H, W, 4), dtype=np.float32)
    rgba[:, :, :3] = array
    img.pixels[:] = rgba[::-1].reshape(-1)
    img.update()

    return img


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def build(
    albedo: np.ndarray,
    depth: np.ndarray,
    mesh_name: str,
    subdivisions: int,
    displacement_strength: float,
) -> bpy.types.Object:
    """
    Build a subdivided plane mesh displaced by the depth map and textured
    with the albedo image.

    Args:
        albedo:                H x W x 3 float32 [0, 1] — color texture
        depth:                 H x W     float32 [0, 1] — displacement map
        mesh_name:             Name for the output object and related data blocks
        subdivisions:          Grid resolution as a power of two (segments = 2^n)
        displacement_strength: Displace modifier strength

    Returns:
        The newly created bpy.types.Object linked into the scene.
    """
    unique_name = mesh_name
    counter = 1
    while unique_name in bpy.data.objects:
        unique_name = f"{mesh_name}.{counter:03d}"
        counter += 1
    mesh_name = unique_name

    segments = 2 ** subdivisions

    # -----------------------------------------------------------------------
    # Geometry — subdivided grid via bmesh
    # -----------------------------------------------------------------------
    mesh_data = bpy.data.meshes.new(mesh_name)
    obj = bpy.data.objects.new(mesh_name, mesh_data)

    col = _get_or_create_collection(_COLLECTION_NAME)
    col.objects.link(obj)

    bm = bmesh.new()
    bmesh.ops.create_grid(
        bm,
        x_segments=segments,
        y_segments=segments,
        size=1.0,
        calc_uvs=False,
    )
    bm.to_mesh(mesh_data)
    bm.free()
    mesh_data.update()

    uv_layer = mesh_data.uv_layers.new(name="UVMap")
    for poly in mesh_data.polygons:
        for loop_idx in poly.loop_indices:
            v_idx = mesh_data.loops[loop_idx].vertex_index
            co = mesh_data.vertices[v_idx].co
            uv_layer.data[loop_idx].uv = ((co.x + 1.0) / 2.0, (co.y + 1.0) / 2.0)
    uv_layer.active = True

    # -----------------------------------------------------------------------
    # Material — Principled BSDF with albedo image texture
    # -----------------------------------------------------------------------
    albedo_img = _array_to_image(mesh_name + _ALBEDO_SUFFIX, albedo)

    mat = bpy.data.materials.new(mesh_name + _MAT_SUFFIX)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out_node = nodes.new("ShaderNodeOutputMaterial")
    bsdf_node = nodes.new("ShaderNodeBsdfPrincipled")
    tex_node = nodes.new("ShaderNodeTexImage")
    uv_node = nodes.new("ShaderNodeTexCoord")

    tex_node.image = albedo_img

    links.new(uv_node.outputs["Generated"], tex_node.inputs["Vector"])
    links.new(tex_node.outputs["Color"], bsdf_node.inputs["Base Color"])
    links.new(bsdf_node.outputs["BSDF"], out_node.inputs["Surface"])

    out_node.location = (300, 0)
    bsdf_node.location = (0, 0)
    tex_node.location = (-350, 0)
    uv_node.location = (-600, 0)

    mesh_data.materials.append(mat)

    # -----------------------------------------------------------------------
    # Displacement — non-destructive Displace modifier
    # -----------------------------------------------------------------------
    depth_img = _array_to_image(mesh_name + _DEPTH_SUFFIX, depth, is_data=True)

    depth_tex = bpy.data.textures.new(mesh_name + _DEPTH_TEX_SUFFIX, type="IMAGE")
    depth_tex.image = depth_img

    mod = obj.modifiers.new("Displace", "DISPLACE")
    mod.texture = depth_tex
    mod.texture_coords = "UV"
    mod.direction = "Z"
    mod.strength = displacement_strength

    # -----------------------------------------------------------------------
    # View layer — make the object selectable and active
    # -----------------------------------------------------------------------
    bpy.context.view_layer.objects.active = obj
    obj.select_set(True)

    return obj
