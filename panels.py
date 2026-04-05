import bpy

_CATEGORY = "Depth to Mesh"


class DEPTHMESH_PT_main(bpy.types.Panel):
    bl_label = "Depth to Mesh"
    bl_idname = "DEPTHMESH_PT_main"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = _CATEGORY

    def draw(self, context):
        layout = self.layout
        props = context.scene.depth_to_mesh

        col = layout.column(align=True)
        col.scale_y = 1.6
        col.operator(
            "depthmesh.run_pipeline",
            text="Generate Mesh",
            icon="MESH_GRID",
        )

        if props.status_text:
            layout.separator(factor=0.5)
            layout.row().label(text=props.status_text, icon="INFO")

        layout.separator(factor=0.5)
        layout.operator(
            "depthmesh.clear_output",
            text="Clear Output",
            icon="TRASH",
        )


class DEPTHMESH_PT_input(bpy.types.Panel):
    bl_label = "Input"
    bl_idname = "DEPTHMESH_PT_input"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = _CATEGORY
    bl_parent_id = "DEPTHMESH_PT_main"

    def draw(self, context):
        layout = self.layout
        props = context.scene.depth_to_mesh

        layout.prop(props, "input_path", text="")
        layout.prop(props, "use_alpha")
        layout.prop(props, "output_mesh_name")


class DEPTHMESH_PT_depth_settings(bpy.types.Panel):
    bl_label = "Depth & Mesh"
    bl_idname = "DEPTHMESH_PT_depth_settings"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = _CATEGORY
    bl_parent_id = "DEPTHMESH_PT_main"

    def draw(self, context):
        layout = self.layout
        props = context.scene.depth_to_mesh

        col = layout.column(align=True)
        col.prop(props, "displacement_strength", slider=True)
        col.prop(props, "use_delight")
        if props.use_delight:
            col.prop(props, "delight_strength", slider=True)

        col.separator(factor=0.5)
        col.prop(props, "clean_edges")
        if props.clean_edges:
            col.prop(props, "edge_falloff", slider=True)

        col.separator(factor=0.5)
        col.prop(props, "mesh_subdivisions")
        subdivs = props.mesh_subdivisions
        segments = 2 ** subdivs
        col.label(
            text=f"  → {segments}×{segments} segments  ({segments * segments:,} faces)",
            icon="BLANK1",
        )


class DEPTHMESH_PT_model_cache(bpy.types.Panel):
    bl_label = "Model Cache"
    bl_idname = "DEPTHMESH_PT_model_cache"
    bl_space_type = "VIEW_3D"
    bl_region_type = "UI"
    bl_category = _CATEGORY
    bl_parent_id = "DEPTHMESH_PT_main"
    bl_options = {"DEFAULT_CLOSED"}

    def draw(self, context):
        layout = self.layout
        props = context.scene.depth_to_mesh

        layout.label(text="Depth Anything V2 Small (~100 MB)", icon="IMPORT")
        layout.prop(props, "cache_dir", text="")
        layout.operator(
            "depthmesh.open_cache_dir",
            text="Open Folder",
            icon="FILE_FOLDER",
        )
