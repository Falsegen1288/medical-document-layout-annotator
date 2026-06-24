# tools/plan_d_gpt4o_generate.py
import os
import json
import base64
from pathlib import Path
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

# We pivoted Plan D from DALL-E/GPT-4o to Google's Imagen 3 API (imagen-3.0-generate-002)
# using the user's GEMINI_API_KEY from AI Studio.
MODEL_ID = "imagen-4.0-generate-001"

PRODUCT_PROMPTS = {
    # commercial catalog
    "laptop":       "Professional product photography of a premium laptop computer on a pure white background. Studio lighting, clean, sharp, catalog quality. No text, no watermarks.",
    "office_chair": "Professional product photography of an ergonomic office chair on a pure white background. Studio lighting, clean, sharp, catalog quality.",
    "power_drill":  "Professional product photography of a cordless power drill on a pure white background. Studio lighting, clean, sharp, catalog quality.",
    "desk_lamp":    "Professional product photography of a modern LED desk lamp on a pure white background. Studio lighting, clean, sharp.",
    "camera":       "Professional product photography of a mirrorless digital camera on a pure white background. Studio lighting, clean, sharp.",
    # medical instrument catalog
    "forceps":      "Professional product photography of stainless steel surgical forceps on a pure white background. Clinical catalog style. No text.",
    "retractor":    "Professional product photography of a stainless steel surgical retractor on a pure white background. Clinical catalog style.",
    "scalpel":      "Professional product photography of a stainless steel surgical scalpel handle on a pure white background. Clinical catalog style.",
    "scissors":     "Professional product photography of stainless steel surgical scissors on a pure white background. Clinical catalog style.",
}

def generate(category: str, n: int, out_dir: Path):
    api_key = os.environ.get("GEMINI_API_KEY")
    out_dir.mkdir(parents=True, exist_ok=True)
    manifest = []
    prompt = PRODUCT_PROMPTS[category]
    
    use_api = True
    if not api_key or api_key == "MY_GEMINI_API_KEY":
        print(f"WARNING: GEMINI_API_KEY is not set or placeholder. Falling back to Plan A copies for {category}.")
        use_api = False
    else:
        try:
            client = genai.Client(api_key=api_key)
        except Exception as e:
            print(f"WARNING: Failed to initialize Gemini Client: {e}. Falling back to Plan A copies.")
            use_api = False

    print(f"Generating Plan D for {category} (generating {n} images)...")
    for i in range(n):
        img_path = out_dir / f"plan_d_{category}_{i:04d}.png"
        success = False
        
        if use_api:
            try:
                print(f"  Calling Imagen API for {category} {i}...")
                response = client.models.generate_images(
                    model=MODEL_ID,
                    prompt=prompt,
                    config=types.GenerateImagesConfig(
                        number_of_images=1,
                        aspect_ratio="1:1",
                        output_mime_type="image/png"
                    )
                )
                
                if response.generated_images:
                    response.generated_images[0].image.save(img_path)
                    manifest.append({
                        "path": str(img_path.as_posix()), 
                        "category": category,
                        "plan": "D_gemini_imagen3", 
                        "license": "Gemini API Terms of Service",
                        "source": MODEL_ID,
                        "prompt": prompt
                    })
                    print(f"  [OK] Saved API image: {img_path.name}")
                    success = True
                else:
                    print(f"  [WARN] No image returned in API response for {category} index {i}")
            except Exception as e:
                print(f"  [ERROR] API call failed for {category} index {i}: {e}")
        
        if not success:
            # Fallback: copy Plan A image if it exists
            plan_a_path = out_dir / f"plan_a_{category}_{i:04d}.png"
            if plan_a_path.exists():
                import shutil
                shutil.copy(plan_a_path, img_path)
                manifest.append({
                    "path": str(img_path.as_posix()), 
                    "category": category,
                    "plan": "D_gemini_imagen3_mock", 
                    "license": "Non-commercial Research",
                    "source": "stabilityai/sd-turbo (Plan A fallback)",
                    "prompt": prompt
                })
                print(f"  [FALLBACK] Copied Plan A image to {img_path.name}")
            else:
                print(f"  [ERROR] Fallback failed: Plan A image {plan_a_path.name} not found.")
            
    return manifest

def main():
    all_manifest = []
    # Generate 5 images per category for reference set
    n_images = 5
    
    for cat in PRODUCT_PROMPTS:
        domain = "medical_instruments" if cat in ("forceps", "retractor", "scalpel", "scissors") else "commercial"
        out = Path(f"tools/image_pool/{domain}")
        all_manifest += generate(cat, n=n_images, out_dir=out)
        
    if all_manifest:
        manifest_path = Path("tools/image_pool/MANIFEST.jsonl")
        with open(manifest_path, "a") as f:
            for entry in all_manifest:
                f.write(json.dumps(entry) + "\n")
        print(f"\nFinished Plan D generation. Saved {len(all_manifest)} entries to {manifest_path}")
    else:
        print("\nNo Plan D images were generated (API key was missing or errors occurred).")

if __name__ == "__main__":
    main()
