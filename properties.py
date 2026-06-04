import os

import bpy


class DepthToMeshProperties(bpy.types.PropertyGroup):
    input_path: bpy.props.StringProperty(
        name="Input File",
        description="Path to an image (PNG, JPG, EXR, TIFF)",
        subtype="FILE_PATH",
    )

    use_delight: bpy.props.BoolProperty(
        name="Delight Image",
        description=(
            "Apply Multi-Scale Retinex to remove lighting from the texture. "
            "Disable to use the original image as-is"
        ),
        default=True,
    )

    delight_strength: bpy.props.FloatProperty(
        name="Delight Strength",
        description=(
            "Blend between the original image (0.0) and the fully delighted "
            "result (1.0)"
        ),
        default=0.5,
        min=0.0,
        max=1.0,
        step=5,
        precision=2,
    )

    displacement_strength: bpy.props.FloatProperty(
        name="Displacement Strength",
        description="Scale factor applied to the estimated depth when displacing the mesh",
        default=1.0,
        min=0.0,
        max=5.0,
        step=10,
        precision=2,
    )

    mesh_subdivisions: bpy.props.IntProperty(
        name="Mesh Subdivisions",
        description=(
            "Grid resolution as a power of two (e.g. 7 = 128×128 segments, "
            "8 = 256×256 segments). Higher values capture more detail but use more memory"
        ),
        default=7,
        min=2,
        max=10,
    )

    output_mesh_name: bpy.props.StringProperty(
        name="Output Name",
        description="Name for the generated mesh object in the scene",
        default="DepthMesh",
    )

    cache_dir: bpy.props.StringProperty(
        name="Model Cache",
        description=(
            "Directory where Depth Anything V2 weights are downloaded and cached. "
            "Requires ~100 MB on first use"
        ),
        subtype="DIR_PATH",
        default=os.path.join(os.path.expanduser("~"), ".cache", "depth_to_mesh"),
    )

    use_bump: bpy.props.BoolProperty(
        name="Normal Map (Bump)",
        description=(
            "Derive a bump map from the image luminance and apply it to the "
            "material's Normal input. Fakes fine surface detail that the depth "
            "map cannot capture"
        ),
        default=False,
    )

    bump_strength: bpy.props.FloatProperty(
        name="Bump Strength",
        description="Strength of the normal map effect (0 = off, 1 = full)",
        default=0.5,
        min=0.0,
        max=2.0,
        step=5,
        precision=2,
    )

    normal_smoothing: bpy.props.FloatProperty(
        name="Normal Smoothing",
        description=(
            "Gaussian blur radius applied to the depth map before computing "
            "normals. Higher values keep only large-scale features and suppress "
            "fine noise on smooth surfaces"
        ),
        default=5.0,
        min=0.0,
        max=30.0,
        step=10,
        precision=1,
    )

    use_alpha: bpy.props.BoolProperty(
        name="Transparent Background",
        description=(
            "Use the image's alpha channel as a cutout mask. "
            "Enable for PNG/EXR images with a transparent background"
        ),
        default=False,
    )

    clean_edges: bpy.props.BoolProperty(
        name="Clean Edges",
        description=(
            "Taper the depth map to zero at the mesh border so the sides "
            "of the displaced mesh are level rather than steep and uneven"
        ),
        default=False,
    )

    edge_falloff: bpy.props.FloatProperty(
        name="Falloff Width",
        description=(
            "Width of the taper zone as a fraction of the image size. "
            "0.1 = only the outermost 10% fades; 0.5 = outer half fades"
        ),
        default=0.1,
        min=0.01,
        max=0.5,
        step=1,
        precision=2,
    )

    status_text: bpy.props.StringProperty(
        name="Status",
        description="Current pipeline status message",
        default="",
    )
