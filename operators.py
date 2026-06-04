import os
import queue
import subprocess
import sys
import threading

import bpy

from . import mesh_builder, pipeline_runner

_DONE = object()


class DEPTHMESH_OT_run_pipeline(bpy.types.Operator):
    bl_idname = "depthmesh.run_pipeline"
    bl_label = "Generate Mesh"
    bl_description = (
        "Run Depth Anything V2 depth estimation on the selected input "
        "and build a displaced mesh"
    )
    bl_options = {"REGISTER", "UNDO"}

    _thread: threading.Thread = None
    _queue: queue.Queue = None
    _result: tuple = None
    _error: Exception = None

    @classmethod
    def poll(cls, context):
        props = context.scene.depth_to_mesh
        return bool(props.input_path.strip())

    def execute(self, context):
        props = context.scene.depth_to_mesh
        input_path = bpy.path.abspath(props.input_path)
        cache_dir = bpy.path.abspath(props.cache_dir)
        use_delight = props.use_delight
        delight_strength = props.delight_strength

        # EXR must be loaded on the main thread before spawning
        preloaded_image = None
        if os.path.splitext(input_path)[1].lower() == ".exr":
            try:
                props.status_text = "Loading EXR..."
                preloaded_image = mesh_builder.load_exr(input_path)
            except Exception as e:
                props.status_text = f"Error loading EXR: {e}"
                self.report({"ERROR"}, str(e))
                return {"CANCELLED"}

        self._queue = queue.Queue()
        self._result = None
        self._error = None

        def progress(msg: str):
            self._queue.put(msg)

        def thread_fn():
            try:
                albedo, depth, alpha = pipeline_runner.run(
                    input_path=input_path,
                    cache_dir=cache_dir,
                    use_ml_depth=True,
                    use_delight=use_delight,
                    delight_strength=delight_strength,
                    progress_callback=progress,
                    preloaded_image=preloaded_image,
                )
                self._result = (albedo, depth, alpha)
            except Exception as e:
                self._error = e
            finally:
                self._queue.put(_DONE)

        props.status_text = "Starting..."
        self._thread = threading.Thread(target=thread_fn, daemon=True)
        self._thread.start()

        wm = context.window_manager
        wm.modal_handler_add(self)
        self._timer = wm.event_timer_add(0.1, window=context.window)
        return {"RUNNING_MODAL"}

    def modal(self, context, event):
        if event.type != "TIMER":
            return {"PASS_THROUGH"}

        props = context.scene.depth_to_mesh
        done = False

        while True:
            try:
                item = self._queue.get_nowait()
            except queue.Empty:
                break
            if item is _DONE:
                done = True
            else:
                props.status_text = item
                for area in context.screen.areas:
                    if area.type == "VIEW_3D":
                        area.tag_redraw()

        if not done:
            return {"RUNNING_MODAL"}

        context.window_manager.event_timer_remove(self._timer)

        if self._error is not None:
            props.status_text = f"Error: {self._error}"
            self.report({"ERROR"}, str(self._error))
            return {"CANCELLED"}

        albedo, depth, alpha = self._result
        if not props.use_alpha:
            alpha = None
        mesh_builder.build(
            albedo=albedo,
            depth=depth,
            mesh_name=props.output_mesh_name,
            subdivisions=props.mesh_subdivisions,
            displacement_strength=props.displacement_strength,
            clean_edges=props.clean_edges,
            edge_falloff=props.edge_falloff,
            alpha=alpha,
            use_bump=props.use_bump,
            bump_strength=props.bump_strength,
            normal_smoothing=props.normal_smoothing,
        )

        props.status_text = "Done"
        self.report({"INFO"}, f"Depth to Mesh: '{props.output_mesh_name}' created")
        return {"FINISHED"}

    def cancel(self, context):
        context.window_manager.event_timer_remove(self._timer)
        context.scene.depth_to_mesh.status_text = "Cancelled"


class DEPTHMESH_OT_open_cache_dir(bpy.types.Operator):
    bl_idname = "depthmesh.open_cache_dir"
    bl_label = "Open Cache Folder"
    bl_description = "Open the model cache directory in the system file manager"

    def execute(self, context):
        props = context.scene.depth_to_mesh
        cache_dir = bpy.path.abspath(props.cache_dir)
        os.makedirs(cache_dir, exist_ok=True)

        if sys.platform == "darwin":
            subprocess.Popen(["open", cache_dir])
        elif sys.platform == "win32":
            subprocess.Popen(["explorer", cache_dir])
        else:
            subprocess.Popen(["xdg-open", cache_dir])

        return {"FINISHED"}


class DEPTHMESH_OT_clear_output(bpy.types.Operator):
    bl_idname = "depthmesh.clear_output"
    bl_label = "Clear Output"
    bl_description = (
        "Remove all meshes, materials, and images generated by this addon from the scene"
    )
    bl_options = {"REGISTER", "UNDO"}

    def execute(self, context):
        col = bpy.data.collections.get(mesh_builder._COLLECTION_NAME)
        if col is None or not col.objects:
            self.report({"INFO"}, "Depth to Mesh: nothing to clear")
            return {"FINISHED"}

        # Gather materials and images before unlinking objects
        materials = set()
        images = set()
        for obj in list(col.objects):
            for slot in obj.material_slots:
                mat = slot.material
                if mat is None:
                    continue
                materials.add(mat)
                if mat.use_nodes:
                    for node in mat.node_tree.nodes:
                        if node.type == "TEX_IMAGE" and node.image:
                            images.add(node.image)
            mesh = obj.data
            bpy.data.objects.remove(obj, do_unlink=True)
            if mesh and mesh.users == 0:
                bpy.data.meshes.remove(mesh)

        for mat in materials:
            if mat.users == 0:
                bpy.data.materials.remove(mat)
        for img in images:
            if img.users == 0:
                bpy.data.images.remove(img)

        if not col.objects:
            bpy.data.collections.remove(col)

        context.scene.depth_to_mesh.status_text = ""
        self.report({"INFO"}, "Depth to Mesh: output cleared")
        return {"FINISHED"}
