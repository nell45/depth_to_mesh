bl_info = {
    "name": "Depth to Mesh",
    "author": "",
    "version": (0, 1, 0),
    "blender": (4, 0, 0),
    "location": "View3D > N-panel > Depth to Mesh",
    "description": "Generate a displaced, delighted mesh from an image or video",
    "warning": "Requires a one-time ~100 MB model download on first use",
    "category": "Object",
}

from . import addon_core


def register():
    addon_core.register()


def unregister():
    addon_core.unregister()
