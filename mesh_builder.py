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
    H x W x 4 float32 RGBA array. RGB is normalised to [0, 1] by p99;
    alpha is kept as-is, clamped to [0, 1].

    Must be called from the main thread. The temporary image data block
    is removed after the pixels are extracted.
    """
    img = bpy.data.images.load(path)
    try:
        W, H = img.size
        pixels = np.array(img.pixels[:], dtype=np.float32).reshape(H, W, 4)
        rgba = pixels[::-1].copy()
    finally:
        bpy.data.images.remove(img)

    p99 = np.percentile(rgba[:, :, :3], 99)
    if p99 > 0:
        rgba[:, :, :3] = rgba[:, :, :3] / p99
    rgba[:, :, :3] = np.clip(rgba[:, :, :3], 0.0, 1.0)
    rgba[:, :, 3] = np.clip(rgba[:, :, 3], 0.0, 1.0)
    return rgba


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
    has_alpha = array.shape[2] == 4

    img = bpy.data.images.new(
        name, width=W, height=H, float_buffer=is_data, alpha=has_alpha
    )
    img.colorspace_settings.name = "Non-Color" if is_data else "sRGB"

    if has_alpha:
        rgba = array.astype(np.float32)
    else:
        rgba = np.ones((H, W, 4), dtype=np.float32)
        rgba[:, :, :3] = array
    img.pixels[:] = rgba[::-1].reshape(-1)
    img.update()

    return img


# ---------------------------------------------------------------------------
# Public API
# ---------------------------------------------------------------------------

def _apply_edge_falloff(depth: np.ndarray, edge_falloff: float) -> np.ndarray:
    """
    Multiply depth by a cosine falloff mask that is 1.0 at the center and
    fades smoothly to 0.0 at the image borders.

    Args:
        depth:        H x W float32 [0, 1]
        edge_falloff: Width of the fade zone as a fraction of image half-size
                      (e.g. 0.1 = outer 10% fades, 0.5 = outer 50% fades)

    Returns:
        Masked depth array, same shape and dtype as input.
    """
    H, W = depth.shape
    # Normalised coordinates: -1 at left/top edge, +1 at right/bottom edge
    y = np.linspace(-1.0, 1.0, H, dtype=np.float32)
    x = np.linspace(-1.0, 1.0, W, dtype=np.float32)
    xx, yy = np.meshgrid(x, y)

    # Chebyshev distance from centre (0 = centre, 1 = corner)
    dist = np.maximum(np.abs(xx), np.abs(yy))

    # Taper zone: dist in [1 - edge_falloff, 1.0] maps t from 0 to 1
    taper_start = 1.0 - edge_falloff
    t = np.clip((dist - taper_start) / (edge_falloff + 1e-6), 0.0, 1.0)

    # Cosine ease: 1 at centre, 0 at border
    mask = (0.5 * (1.0 + np.cos(np.pi * t))).astype(np.float32)
    return depth * mask


def build(
    albedo: np.ndarray,
    depth: np.ndarray,
    mesh_name: str,
    subdivisions: int,
    displacement_strength: float,
    clean_edges: bool = False,
    edge_falloff: float = 0.1,
    alpha: np.ndarray = None,
    use_bump: bool = False,
    bump_strength: float = 0.5,
    normal_smoothing: float = 5.0,
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
        clean_edges:           If True, taper depth to zero at mesh borders
        edge_falloff:          Width of the taper zone (fraction of half-image)
        alpha:                 Optional H x W float32 [0, 1] — transparency mask.
                               Transparent pixels are not displaced and render
                               as cutouts in the material.

    Returns:
        The newly created bpy.types.Object linked into the scene.
    """
    if alpha is not None:
        depth = depth * alpha
    if clean_edges:
        depth = _apply_edge_falloff(depth, edge_falloff)
    unique_name = mesh_name
    counter = 1
    while unique_name in bpy.data.objects:
        unique_name = f"{mesh_name}.{counter:03d}"
        counter += 1
    mesh_name = unique_name

    segments = 2 ** subdivisions

    # Aspect ratio: scale X so the mesh matches the image proportions
    H_img, W_img = depth.shape
    aspect = W_img / H_img  # > 1 for landscape, < 1 for portrait

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

    # Stretch X vertices to match image aspect ratio.
    # create_grid produces X in [-1, 1]; after scaling X is in [-aspect, +aspect].
    if aspect != 1.0:
        for v in mesh_data.vertices:
            v.co.x *= aspect

    mesh_data.update()

    uv_layer = mesh_data.uv_layers.new(name="UVMap")
    for poly in mesh_data.polygons:
        for loop_idx in poly.loop_indices:
            v_idx = mesh_data.loops[loop_idx].vertex_index
            co = mesh_data.vertices[v_idx].co
            # co.x is in [-aspect, +aspect], co.y is in [-1, +1]
            uv_layer.data[loop_idx].uv = (
                (co.x / aspect + 1.0) / 2.0,
                (co.y + 1.0) / 2.0,
            )
    uv_layer.active = True

    # -----------------------------------------------------------------------
    # Material — Principled BSDF with albedo image texture
    # -----------------------------------------------------------------------
    if alpha is not None:
        albedo_rgba = np.concatenate(
            [albedo, alpha[:, :, np.newaxis]], axis=2
        ).astype(np.float32)
        albedo_img = _array_to_image(mesh_name + _ALBEDO_SUFFIX, albedo_rgba)
    else:
        albedo_img = _array_to_image(mesh_name + _ALBEDO_SUFFIX, albedo)

    mat = bpy.data.materials.new(mesh_name + _MAT_SUFFIX)
    mat.use_nodes = True
    nodes = mat.node_tree.nodes
    links = mat.node_tree.links
    nodes.clear()

    out_node  = nodes.new("ShaderNodeOutputMaterial")
    bsdf_node = nodes.new("ShaderNodeBsdfPrincipled")
    tex_node  = nodes.new("ShaderNodeTexImage")
    uv_node   = nodes.new("ShaderNodeTexCoord")

    tex_node.image = albedo_img
    # EXTEND clamps wall faces to the nearest edge pixel instead of stretching
    tex_node.extension = "EXTEND"

    links.new(uv_node.outputs["Generated"], tex_node.inputs["Vector"])
    links.new(tex_node.outputs["Color"], bsdf_node.inputs["Base Color"])

    if use_bump:
        # Tangent-space normal map derived from depth gradients.
        # Flat regions produce a neutral normal (0.5, 0.5, 1.0); only edges
        # and curves produce coloured normals, so bumps only appear where needed.
        # Blur depth first to suppress high-frequency estimation noise on smooth
        # surfaces; only large-scale features survive to become normals.
        depth_for_normals = depth
        if normal_smoothing > 0.0:
            from PIL import Image, ImageFilter
            depth_u8 = (depth_for_normals * 255.0).clip(0, 255).astype(np.uint8)
            depth_pil = Image.fromarray(depth_u8, mode="L")
            depth_pil = depth_pil.filter(ImageFilter.GaussianBlur(radius=normal_smoothing))
            depth_for_normals = np.array(depth_pil, dtype=np.float32) / 255.0

        dz_dx = np.gradient(depth_for_normals, axis=1)
        dz_dy = np.gradient(depth_for_normals, axis=0)

        # Raw gradients are tiny (depth is in [0,1] over many pixels).
        # Scale so that the typical gradient produces a visible tilt.
        # Divide by the 95th-percentile gradient magnitude so the scale
        # adapts to the actual depth variation in this image.
        grad_mag = np.sqrt(dz_dx ** 2 + dz_dy ** 2)
        p95 = float(np.percentile(grad_mag, 95)) + 1e-6
        amp = 0.5 / p95  # typical strong edge → ~30° tilt

        nx = -dz_dx * amp
        ny =  dz_dy * amp
        nz =  np.ones_like(depth)
        length = np.sqrt(nx ** 2 + ny ** 2 + nz ** 2)
        nx /= length
        ny /= length
        nz /= length

        normal_rgb = np.stack([
            nx * 0.5 + 0.5,
            ny * 0.5 + 0.5,
            nz * 0.5 + 0.5,
        ], axis=2).astype(np.float32)

        normal_img = _array_to_image(mesh_name + "_normal", normal_rgb, is_data=True)

        bump_tex      = nodes.new("ShaderNodeTexImage")
        normalmap_node = nodes.new("ShaderNodeNormalMap")

        bump_tex.image = normal_img
        bump_tex.extension = "EXTEND"
        normalmap_node.inputs["Strength"].default_value = bump_strength

        links.new(uv_node.outputs["Generated"],  bump_tex.inputs["Vector"])
        links.new(bump_tex.outputs["Color"],     normalmap_node.inputs["Color"])
        links.new(normalmap_node.outputs["Normal"], bsdf_node.inputs["Normal"])

        bump_tex.location      = (-350, -300)
        normalmap_node.location = (0,    -300)

    if alpha is not None:
        links.new(tex_node.outputs["Alpha"], bsdf_node.inputs["Alpha"])
        mat.blend_method = "BLEND"

    links.new(bsdf_node.outputs["BSDF"], out_node.inputs["Surface"])

    out_node.location  = (300,   0)
    bsdf_node.location = (0,     0)
    tex_node.location  = (-350,  0)
    uv_node.location   = (-600,  0)

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
