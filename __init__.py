bl_info = {
    "name": "Depth to Mesh",
    "author": "Neel Pal",
    "version": (1, 0, 0),
    "blender": (4, 0, 0),
    "location": "View3D > N-panel > Depth to Mesh",
    "description": (
        "Convert any image into a displaced 3D mesh using AI depth estimation "
        "(Depth Anything V2). Includes delighting, normal maps, clean edges, "
        "and transparent background support."
    ),
    "warning": "Requires Python dependencies — see Add-on Preferences to install",
    "doc_url": "https://github.com/nell45/depth_to_mesh.git",
    "tracker_url": "https://github.com/nell45/depth_to_mesh.git",
    "category": "Object",
}

from . import addon_core


def register():
    addon_core.register()


def unregister():
    addon_core.unregister()
