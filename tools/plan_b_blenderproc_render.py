# tools/plan_b_blenderproc_render.py
import os
import json
import subprocess
import shutil
from pathlib import Path
import objaverse

# Map categories to LVIS annotations or similar Objaverse text searches
CATEGORY_MAPPING = {
    "laptop":       ["laptop"],
    "office_chair": ["chair", "desk"],
    "power_drill":  ["drill"],
    "desk_lamp":    ["lamp"],
    "camera":       ["camera"],
    "forceps":      ["scissors", "pliers"], # LVIS proxies for medical hand tools
    "retractor":    ["scissors", "pliers"],
    "scalpel":      ["knife"],
    "scissors":     ["scissors"],
}

BLENDER_RENDER_SCRIPT = """
import blenderproc as bproc
import sys
import os
import bpy
from pathlib import Path

# Fix Windows path slashes
glb_path = sys.argv[-2].replace('\\\\', '/')
out_dir = Path(sys.argv[-1].replace('\\\\', '/'))
out_dir.mkdir(parents=True, exist_ok=True)

bproc.init()

# Clear default Blender items
for obj in bpy.data.objects:
    if obj.name in ["Light", "Cube"]:
        bpy.data.objects.remove(obj, do_unlink=True)

# Studio setup
bproc.renderer.set_output_format("PNG")
bpy.context.scene.render.film_transparent = True
bproc.renderer.set_max_amount_of_samples(32) # Lower samples for speed on GTX 1650

# Load GLB asset
try:
    print(f"Loading object from: {glb_path}")
    # Use standard blender import for gltf/glb
    bpy.ops.import_scene.gltf(filepath=glb_path)
    
    # Get imported meshes
    imported_objs = [obj for obj in bpy.context.scene.objects if obj.type == 'MESH']
    
    if not imported_objs:
        raise ValueError("No meshes found in the GLB file")
        
    # Scale and center the main imported object
    for obj in imported_objs:
        obj.location = (0, 0, 0)
        # Normalize scale to fit in a 1-unit bounding box
        dims = obj.dimensions
        max_dim = max(dims) if max(dims) > 0 else 1.0
        obj.scale = (1.0/max_dim, 1.0/max_dim, 1.0/max_dim)
        
except Exception as e:
    print(f"Error loading model: {e}")
    sys.exit(1)

# 3-point studio lighting using native bpy
def add_light(location, energy):
    light_data = bpy.data.lights.new(name="PointLight", type='POINT')
    light_data.energy = energy
    light_object = bpy.data.objects.new(name="PointLight", object_data=light_data)
    bpy.context.collection.objects.link(light_object)
    light_object.location = location

add_light([3, -3, 3], 500)   # key
add_light([-3, -2, 2], 200)  # fill
add_light([0, 3, 3], 100)    # rim

# 4 camera positions
# camera poses: (location, target_point)
poses = [
    ([0, -2, 1], [0, 0, 0.2]),   # Front slightly elevated
    ([-1.5, -1.5, 1], [0, 0, 0.2]), # 3/4 Left
    ([1.5, -1.5, 1], [0, 0, 0.2]),  # 3/4 Right
    ([0, -0.1, 2], [0, 0, 0])     # Top-down
]

# Set camera positions and render
import numpy as np

for i, (loc, target) in enumerate(poses):
    forward_vec = np.array(target) - np.array(loc)
    # Calculate 3x3 rotation matrix
    rotation_matrix = bproc.camera.rotation_from_forward_vec(forward_vec, up_axis='Y')
    # Build 4x4 cam2world transformation matrix
    cam2world_matrix = bproc.math.build_transformation_mat(loc, rotation_matrix)
    bproc.camera.add_camera_pose(cam2world_matrix)

# Render and save color images
data = bproc.renderer.render()
for i in range(len(poses)):
    out_path = out_dir / f"angle_{i:02d}.png"
    # Composite transparent background onto white
    import numpy as np
    from PIL import Image
    
    rgba = data["colors"][i]
    # If the rendering returned RGB instead of RGBA, convert it
    if rgba.shape[2] == 3:
        # Pad with full alpha
        alpha = np.ones((rgba.shape[0], rgba.shape[1], 1), dtype=rgba.dtype) * 255
        rgba = np.concatenate([rgba, alpha], axis=2)
        
    # Composite on white background
    white_bg = Image.new("RGBA", (rgba.shape[1], rgba.shape[0]), (255, 255, 255, 255))
    fg_img = Image.fromarray(rgba, "RGBA")
    composited = Image.alpha_composite(white_bg, fg_img).convert("RGB")
    composited.save(out_path)
    print(f"Saved angle {i} to {out_path}")
"""

def fetch_uids(category: str, n: int = 2) -> list[str]:
    """Retrieve object UIDs using LVIS categories."""
    annotations = objaverse.load_lvis_annotations()
    lvis_cats = CATEGORY_MAPPING.get(category, [category])
    
    matching_uids = []
    for lvis_cat in lvis_cats:
        for c in annotations:
            if lvis_cat.lower() in c.lower():
                matching_uids.extend(annotations[c])
                
    # Return unique UIDs up to the count requested
    unique_uids = list(set(matching_uids))
    return unique_uids[:n]

def main():
    # Setup temporary directory for blender scripts
    temp_dir = Path("tools/temp_blender")
    temp_dir.mkdir(parents=True, exist_ok=True)
    script_path = temp_dir / "blender_render.py"
    script_path.write_text(BLENDER_RENDER_SCRIPT)
    
    manifest = []
    # Render 1 asset per category for local testing (producing 4 angles each)
    assets_per_category = 1
    
    for category in CATEGORY_MAPPING:
        print(f"\n{'='*50}\nCategory: {category}\n{'='*50}")
        uids = fetch_uids(category, n=assets_per_category)
        if not uids:
            print(f"No UIDs found for category {category}")
            continue
            
        print(f"Fetching 3D assets for UIDs: {uids}")
        objects = objaverse.load_objects(uids)
        
        domain = "medical_instruments" if category in ("forceps", "retractor", "scalpel", "scissors") else "commercial"
        out_root = Path(f"tools/image_pool/{domain}")
        out_root.mkdir(parents=True, exist_ok=True)
        
        for idx, (uid, glb_filepath) in enumerate(objects.items()):
            print(f"Rendering model {uid} ({glb_filepath})...")
            render_out_dir = out_root / f"plan_b_{category}_{uid}"
            
            # Execute BlenderProc subprocess
            try:
                # Resolve script path and GLB file path to absolute paths
                abs_script = script_path.resolve()
                abs_glb = Path(glb_filepath).resolve()
                abs_out = render_out_dir.resolve()
                
                # Use the virtual environment executable on Windows
                blenderproc_path = str(Path("venv/Scripts/blenderproc.exe").resolve())
                cmd = [
                    blenderproc_path, "run", str(abs_script),
                    str(abs_glb), str(abs_out)
                ]
                print(f"Running BlenderProc command: {' '.join(cmd)}")
                result = subprocess.run(cmd, capture_output=True, text=True, check=True)
                print(result.stdout)
                
                # Check for output files
                rendered_files = sorted(render_out_dir.glob("angle_*.png"))
                for i, r_file in enumerate(rendered_files):
                    # Copy and rename to flat directory structure
                    target_name = f"plan_b_{category}_{uid}_angle{i}.png"
                    target_path = out_root / target_name
                    shutil.copy(r_file, target_path)
                    
                    manifest.append({
                        "path": str(target_path.as_posix()),
                        "category": category,
                        "plan": "B_blenderproc",
                        "license": "CC-BY / Sketchfab (Objaverse)",
                        "source": f"objaverse:{uid}",
                        "angle": i
                    })
                    print(f"  [OK] Saved final render: {target_path}")
                    
                # Clean up render directory
                shutil.rmtree(render_out_dir)
                
            except subprocess.CalledProcessError as e:
                print(f"BlenderProc error rendering {uid}: {e}")
                print(e.stderr)
            except Exception as ex:
                print(f"Unexpected error rendering {uid}: {ex}")
                
    # Append to MANIFEST.jsonl
    if manifest:
        manifest_path = Path("tools/image_pool/MANIFEST.jsonl")
        with open(manifest_path, "a") as f:
            for entry in manifest:
                f.write(json.dumps(entry) + "\n")
        print(f"\nFinished Plan B generation. Saved {len(manifest)} entries to {manifest_path}")
        
    # Clean up temp blender script folder
    if temp_dir.exists():
        shutil.rmtree(temp_dir)

if __name__ == "__main__":
    main()
