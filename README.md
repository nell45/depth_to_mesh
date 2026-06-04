# Depth to Mesh

A Blender 4.x addon that converts any image into a displaced 3D mesh using AI monocular depth estimation. Feed it a photo, get back a textured, camera-ready mesh you can relight, composite, and render.

---

## Features

- **AI depth estimation** via [Depth Anything V2 Small](https://github.com/DepthAnything/Depth-Anything-V2) (~100 MB, downloaded once and cached)
- **Delighting** using Multi-Scale Retinex — removes baked lighting from the texture so the mesh can be re-lit naturally
- **Normal map generation** — derives a tangent-space normal map from the depth data to fake fine surface detail under new lighting
- **Clean Edges** — tapers the depth to zero at mesh borders so the sides stay level rather than forming steep walls
- **Transparent background support** — uses the alpha channel of PNG/EXR images as a cutout mask
- **Aspect-ratio-correct mesh** — rectangular images produce correctly proportioned meshes, not stretched squares
- **Non-destructive** — all displacement is done via a Blender Displace modifier; the depth texture is preserved for further editing
- Supports **PNG, JPG, TIFF, BMP, EXR**

---

## Requirements

- Blender 4.0 or later
- Internet connection on first use (model download)
- The following Python packages (installed via the addon's Preferences panel):
  - Pillow
  - transformers
  - huggingface_hub
  - safetensors
  - timm
  - accelerate

---

## Installation

1. Download `depth_to_mesh.zip`
2. In Blender: **Edit → Preferences → Add-ons → Install**
3. Select the zip file and enable the addon
4. Open **Edit → Preferences → Add-ons → Depth to Mesh**
5. Click **Install Dependencies** and wait for pip to finish (~2–5 minutes)
6. Restart Blender

On the very first **Generate Mesh** run, Depth Anything V2 weights (~100 MB) will be downloaded and cached automatically.

---

## Usage

1. Open the **N-panel** in the 3D Viewport (press `N`) and select the **Depth to Mesh** tab
2. Set your **Input File** to a PNG, JPG, EXR, or TIFF image
3. Adjust settings as needed (see below)
4. Click **Generate Mesh**

The mesh is placed in a **Depth to Mesh** collection in the scene. Each run creates a new uniquely-named object, so existing meshes are never overwritten.

---

## Settings

### Input

| Setting | Description |
|---|---|
| Input File | Path to the source image |
| Transparent Background | Enable to use the alpha channel as a cutout mask (PNG/EXR only) |
| Output Name | Name for the generated object |

### Depth & Mesh

| Setting | Default | Description |
|---|---|---|
| Displacement Strength | 1.0 | How far vertices are pushed by the depth map |
| Delight Image | On | Apply Multi-Scale Retinex to remove baked lighting from the texture |
| Delight Strength | 0.5 | Blend between original (0) and fully delighted (1) |
| Normal Map (Bump) | Off | Generate a tangent-space normal map from depth gradients and apply it to the material |
| Bump Strength | 0.5 | Intensity of the normal map effect |
| Normal Smoothing | 5.0 | Blur radius on depth before computing normals — higher values suppress noise on smooth surfaces |
| Clean Edges | Off | Taper depth to zero at mesh borders to avoid steep side walls |
| Falloff Width | 0.1 | Width of the taper zone (0.1 = outer 10%, 0.5 = outer 50%) |
| Mesh Subdivisions | 7 | Grid resolution as a power of two (7 = 128×128, 8 = 256×256) |

### Model Cache

| Setting | Description |
|---|---|
| Model Cache | Directory where Depth Anything V2 weights are stored (~100 MB) |
| Open Folder | Opens the cache directory in Finder/Explorer |

---

## Tips

- **Delighting** works best for photos with a single dominant light source. For already-flat-lit images, set Delight Strength to 0 or disable it entirely.
- **Normal Smoothing** at 5–10 works well for portraits. Drop it toward 1–2 for hard-surface subjects where you want to capture sharp edges.
- **Clean Edges** pairs well with images that have prominent subjects — it prevents the depth drop-off at image borders from creating harsh walls.
- **Mesh Subdivisions at 7** (128×128) is a good balance of detail and performance. Use 8–9 for high-resolution source images or close-up renders.
- The **Displace modifier** is non-destructive — you can adjust its **Strength** and **Midlevel** directly in the modifier stack after generation.

---

## Troubleshooting

**"No module named X" when enabling the addon**
Open **Edit → Preferences → Add-ons → Depth to Mesh** and click **Install Dependencies**.

**Depth Anything V2 download fails**
Check your internet connection. The weights download to the Model Cache directory on first use. You can change this directory in the addon panel if your system drive is low on space.

**Mesh looks flat / no displacement**
Increase **Displacement Strength**. Also check that the depth image was created (it should appear in the Blender Image Editor after generation).

**Texture is a flat color**
Make sure you are in **Material Preview** or **Rendered** viewport shading — the texture will not show in **Solid** mode.

---

## License

MIT License — see [LICENSE](LICENSE)

---

*Built with [Depth Anything V2](https://github.com/DepthAnything/Depth-Anything-V2) by Lihe Yang et al.*
