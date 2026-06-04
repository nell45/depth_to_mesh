import bpy

from . import deps_manager


class DEPTHMESH_OT_install_dependencies(bpy.types.Operator):
    bl_idname = "depthmesh.install_dependencies"
    bl_label = "Install Dependencies"
    bl_description = (
        "Download and install the required Python packages via pip. "
        "This may take several minutes. Blender will be unresponsive during installation"
    )

    def execute(self, context):
        self.report({"INFO"}, "Installing dependencies — please wait...")
        success, log = deps_manager.install_all()
        if success:
            self.report(
                {"INFO"},
                "Depth to Mesh: dependencies installed. Restart Blender to activate them.",
            )
        else:
            # Surface the first meaningful error line rather than the full log
            first_error = next(
                (ln for ln in log.splitlines() if ln.strip()), log[:200]
            )
            self.report({"ERROR"}, f"Installation failed: {first_error}")
        return {"FINISHED"}


class DEPTHMESH_Preferences(bpy.types.AddonPreferences):
    bl_idname = __package__

    def draw(self, context):
        layout = self.layout

        layout.label(text="Required Packages", icon="PREFERENCES")
        box = layout.box()
        col = box.column(align=True)
        all_ok = True
        for import_name, pip_name in deps_manager.PACKAGES:
            installed = deps_manager.is_installed(import_name)
            if not installed:
                all_ok = False
            row = col.row()
            row.label(
                text=pip_name,
                icon="CHECKMARK" if installed else "ERROR",
            )

        layout.separator(factor=0.5)
        if all_ok:
            layout.label(text="All dependencies are installed.", icon="CHECKMARK")
        else:
            col = layout.column(align=True)
            col.label(
                text="Some packages are missing. Click below to install them.",
                icon="INFO",
            )
            col.label(
                text="Blender will be unresponsive for several minutes during download.",
                icon="BLANK1",
            )
            col.separator(factor=0.5)
            col.operator(
                "depthmesh.install_dependencies",
                text="Install Dependencies",
                icon="IMPORT",
            )
