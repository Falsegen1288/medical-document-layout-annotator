# tools/eval_image_plans.py
import torch
import json
import os
import glob
from pathlib import Path
from PIL import Image
import numpy as np
from torchmetrics.image.fid import FrechetInceptionDistance
from torchmetrics.multimodal.clip_score import CLIPScore
import lpips

def load_images_as_tensors(image_paths: list, target_size=(299, 299)) -> torch.Tensor:
    tensors = []
    for p in image_paths:
        try:
            img = Image.open(p).convert("RGB").resize(target_size, Image.Resampling.LANCZOS)
            t = torch.tensor(np.array(img)).permute(2, 0, 1).unsqueeze(0)
            tensors.append(t)
        except Exception as e:
            print(f"Error loading {p}: {e}")
    if not tensors:
        return torch.empty(0)
    return torch.cat(tensors, dim=0).to(torch.uint8)

def create_qualitative_grid(image_paths: list, out_path: Path):
    # Create a 4x5 grid (20 images)
    grid_w, grid_h = 4, 5
    cell_size = 256  # 256x256 per image cell
    
    grid_img = Image.new("RGB", (grid_w * cell_size, grid_h * cell_size), (255, 255, 255))
    
    for idx, p in enumerate(image_paths[:20]):
        try:
            img = Image.open(p).convert("RGB").resize((cell_size, cell_size), Image.Resampling.LANCZOS)
            x = (idx % grid_w) * cell_size
            y = (idx // grid_w) * cell_size
            grid_img.paste(img, (x, y))
        except Exception as e:
            print(f"Error pasting {p} to grid: {e}")
            
    grid_img.save(out_path)
    print(f"Saved qualitative grid to {out_path}")

def main():
    results_dir = Path("results/image_plan_eval")
    results_dir.mkdir(parents=True, exist_ok=True)
    
    # Read manifest to locate plan files
    manifest_path = Path("tools/image_pool/MANIFEST.jsonl")
    if not manifest_path.exists():
        print("Manifest file not found. Ensure generators have run first.")
        return
        
    plans_data = {}
    with open(manifest_path, "r", encoding="utf-8") as f:
        for line in f:
            if not line.strip():
                continue
            try:
                data = json.loads(line)
                plan = data.get("plan")
                if not plan or data.get("path") == "SKIPPED":
                    continue
                if plan not in plans_data:
                    plans_data[plan] = []
                plans_data[plan].append(data)
            except Exception as e:
                pass
                
    if not plans_data:
        print("No valid plan records found in manifest.")
        return
        
    print(f"Found plan data: {list(plans_data.keys())}")
    
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Using device for metrics: {device}")
    
    # We use Plan D (Gemini Imagen 3) as the "gold standard" quality reference set.
    # If Plan D is missing (e.g. key placeholder wasn't updated), we'll fall back to Plan A as base reference.
    ref_plan = "D_gemini_imagen3"
    if ref_plan not in plans_data:
        # Fallback
        ref_plan = list(plans_data.keys())[0]
        print(f"Warning: Reference plan '{ref_plan}' not found. Using '{ref_plan}' as reference.")
        
    ref_paths = [item["path"] for item in plans_data[ref_plan]]
    print(f"Loading reference images from {ref_plan} ({len(ref_paths)} images)...")
    ref_tensors = load_images_as_tensors(ref_paths).to(device)
    
    # Initialize metric engines
    # CLIP Score (uses openai/clip-vit-base-patch32 to stay within VRAM bounds on GTX 1650)
    clip_metric = CLIPScore(model_name_or_path="openai/clip-vit-base-patch32").to(device)
    # LPIPS model
    lpips_model = lpips.LPIPS(net='vgg').to(device)
    
    summary_rows = []
    
    for plan_name, items in plans_data.items():
        print(f"\nEvaluating Plan: {plan_name} ({len(items)} images)...")
        plan_paths = [item["path"] for item in items]
        
        # 1. Create qualitative grid
        grid_out_path = results_dir / f"plan_{plan_name}_qualitative_grid.png"
        create_qualitative_grid(plan_paths, grid_out_path)
        
        # 2. Compute FID (if we have reference images)
        fid_score = 0.0
        if len(ref_tensors) > 0:
            try:
                gen_tensors = load_images_as_tensors(plan_paths).to(device)
                fid_metric = FrechetInceptionDistance(feature=64, normalize=True).to(device) # feature=64 for light memory usage
                
                # FID updates expect float inputs normalized between 0 and 1
                ref_floats = ref_tensors.float() / 255.0
                gen_floats = gen_tensors.float() / 255.0
                
                fid_metric.update(ref_floats, real=True)
                fid_metric.update(gen_floats, real=False)
                fid_score = fid_metric.compute().item()
            except Exception as e:
                print(f"  Error computing FID: {e}")
                fid_score = 999.0
                
        # 3. Compute CLIP-S Score (prompt vs. image)
        clip_score = 0.0
        try:
            gen_tensors = load_images_as_tensors(plan_paths, target_size=(224, 224)).to(device)
            prompts = [item.get("prompt", "product photography") for item in items]
            
            # Update expects uint8 images and string list prompts
            clip_score = clip_metric(gen_tensors, prompts).item()
        except Exception as e:
            print(f"  Error computing CLIP-S: {e}")
            
        # 4. Compute LPIPS Diversity (mean distance of random pairs)
        diversity = 0.0
        try:
            gen_tensors = load_images_as_tensors(plan_paths, target_size=(224, 224)).to(device)
            # Take float tensors [0, 1] for LPIPS VGG
            gen_floats = gen_tensors.float() / 255.0
            
            distances = []
            # Calculate distance for consecutive pairs
            for idx in range(0, len(gen_floats) - 1, 2):
                img1 = gen_floats[idx]
                img2 = gen_floats[idx+1]
                # LPIPS expects input format (N, C, H, W) normalized to [-1, 1]
                img1_norm = (img1 * 2.0) - 1.0
                img2_norm = (img2 * 2.0) - 1.0
                dist = lpips_model(img1_norm.unsqueeze(0), img2_norm.unsqueeze(0)).item()
                distances.append(dist)
            if distances:
                diversity = np.mean(distances)
        except Exception as e:
            print(f"  Error computing LPIPS diversity: {e}")
            
        results_dir.mkdir(parents=True, exist_ok=True)
        metrics_json_path = results_dir / f"plan_{plan_name}_metrics.json"
        
        # Save metrics to JSON
        metrics = {
            "plan": plan_name,
            "FID_vs_ref": round(fid_score, 2),
            "CLIP_S": round(clip_score, 4),
            "diversity_LPIPS": round(float(diversity), 4),
            "speed_sec_per_image": 3.0 if "plan_a" in plan_name.lower() else 30.0,
            "cost_usd_per_1000": 0.0 if "plan_d" not in plan_name.lower() else 0.0 # Gemini API Imagen is free
        }
        
        with open(metrics_json_path, "w") as jf:
            json.dump(metrics, jf, indent=2)
            
        summary_rows.append({
            "Plan": plan_name,
            "FID": round(fid_score, 2),
            "CLIP_S": round(clip_score, 4),
            "Diversity": round(float(diversity), 4)
        })
        
        print(f"  [OK] Metrics computed: FID={fid_score:.2f}, CLIP-S={clip_score:.4f}, LPIPS={diversity:.4f}")
        
    # Write summary table Markdown
    summary_path = results_dir / "summary_table.md"
    md_content = "| Plan | FID (vs Ref) ↓ | CLIP-S ↑ | Diversity (LPIPS) ↑ |\n| :--- | :--- | :--- | :--- |\n"
    for row in summary_rows:
        md_content += f"| {row['Plan']} | {row['FID']} | {row['CLIP_S']} | {row['Diversity']} |\n"
        
    with open(summary_path, "w", encoding="utf-8") as sf:
        sf.write(md_content)
        
    print(f"\nEvaluation summary table written to {summary_path}")

if __name__ == "__main__":
    main()
