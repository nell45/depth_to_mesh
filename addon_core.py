import bpy

from . import operators, panels, preferences, properties

_classes = [
    preferences.DEPTHMESH_Preferences,
    preferences.DEPTHMESH_OT_install_dependencies,
    properties.DepthToMeshProperties,
    operators.DEPTHMESH_OT_run_pipeline,
    operators.DEPTHMESH_OT_open_cache_dir,
    operators.DEPTHMESH_OT_clear_output,
    panels.DEPTHMESH_PT_main,
    panels.DEPTHMESH_PT_input,
    panels.DEPTHMESH_PT_depth_settings,
    panels.DEPTHMESH_PT_model_cache,
]


def register():
    for cls in _classes:
        bpy.utils.register_class(cls)
    bpy.types.Scene.depth_to_mesh = bpy.props.PointerProperty(
        type=properties.DepthToMeshProperties
    )


def unregister():
    del bpy.types.Scene.depth_to_mesh
    for cls in reversed(_classes):
        bpy.utils.unregister_class(cls)
