# tools/plan_a_flux_generate.py
import torch
import json
import os
from pathlib import Path
from diffusers import AutoPipelineForText2Image

# Using stabilityai/sd-turbo as a lightweight local proxy for low VRAM (GTX 1650 4GB)
MODEL_ID = "stabilityai/sd-turbo"

PRODUCT_PROMPTS = {
    # commercial catalog
    "laptop":       "product photography, laptop computer, white background, studio lighting, sharp focus, 8k",
    "office_chair": "product photography, ergonomic office chair, white background, studio lighting, sharp focus",
    "power_drill":  "product photography, cordless power drill, white background, studio lighting, sharp focus",
    "desk_lamp":    "product photography, modern LED desk lamp, white background, studio lighting, sharp focus",
    "camera":       "product photography, mirrorless digital camera, white background, studio lighting, sharp focus",
    # medical instrument catalog
    "forceps":      "product photography, surgical forceps, stainless steel, white background, studio lighting, medical catalog",
    "retractor":    "product photography, surgical retractor, stainless steel instrument, white background, studio lighting",
    "scalpel":      "product photography, surgical scalpel handle, stainless steel, white background, clinical lighting",
    "scissors":     "product photography, surgical scissors, stainless steel, white background, studio lighting",
}

BRANDS = ["", "Dell", "HP", "Lenovo", "Apple", "ASUS", "Acer"]

def generate(category: str, n: int, out_dir: Path, seed_offset: int = 42):
    device = "cuda" if torch.cuda.is_available() else "cpu"
    print(f"Loading {MODEL_ID} on {device}...")
    
    # Load model with float16 to keep memory footprint under 2.5GB VRAM
    dtype = torch.float16 if device == "cuda" else torch.float32
    pipe = AutoPipelineForText2Image.from_pretrained(
        MODEL_ID, 
        torch_dtype=dtype, 
        variant="fp16" if device == "cuda" else None
    ).to(device)
    
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    prompt_template = PRODUCT_PROMPTS[category]
    
    for i in range(n):
        brand = BRANDS[i % len(BRANDS)]
        prompt = prompt_template.format(brand=brand).strip()
        
        # sd-turbo works perfectly in 1 step with guidance_scale=0.0
        result = pipe(
            prompt,
            num_inference_steps=1,
            guidance_scale=0.0,
            height=512, 
            width=512,
            generator=torch.manual_seed(seed_offset + i),
        )
        
        img_path = out_dir / f"plan_a_{category}_{i:04d}.png"
        result.images[0].save(img_path)
        
        manifest.append({
            "path": str(img_path.as_posix()), 
            "category": category,
            "plan": "A_flux_schnell_proxy", 
            "license": "Non-commercial Research",
            "source": MODEL_ID,
            "prompt": prompt
        })
        
    return manifest

def main():
    all_manifest = []
    # Generate 5 images per category for local testing/evaluation subset
    n_images = 5
    
    for cat in PRODUCT_PROMPTS:
        domain = "medical_instruments" if cat in ("forceps", "retractor", "scalpel", "scissors") else "commercial"
        out = Path(f"tools/image_pool/{domain}")
        print(f"\nGenerating {n_images} images for category: {cat} in {domain}...")
        all_manifest += generate(cat, n=n_images, out_dir=out)
        
    manifest_path = Path("tools/image_pool/MANIFEST.jsonl")
    with open(manifest_path, "a") as f:
        for entry in all_manifest:
            f.write(json.dumps(entry) + "\n")
            
    print(f"\nFinished Plan A generation. Saved {len(all_manifest)} entries to {manifest_path}")

if __name__ == "__main__":
    main()
