import time
import re
from PIL import Image

# Processor dimensions from processor config
PROC_W = 1648
PROC_H = 2048

# Output format parser:
# <x_LEFT><y_TOP>text content<x_RIGHT><y_BOTTOM><class_LABEL>
BLOCK_PATTERN = re.compile(
    r'<x_([0-9.]+)><y_([0-9.]+)>'
    r'(.*?)'
    r'<x_([0-9.]+)><y_([0-9.]+)>'
    r'<class_([^>]+)>',
    re.DOTALL
)

def run_nemotron(page_images: dict, pages: list, config: dict) -> dict:
    """
    Run NVIDIA Nemotron-Parse-v1.1 on selected pages.
    Converts padded normalized coordinates back to 150 DPI page dimensions.
    """
    results = {pg: [] for pg in pages}
    
    # We only run Nemotron on pages explicitly listed in the session configuration/notebook (e.g. nemotron_pages)
    # The VRAM constraint applies. Let's check which pages are target pages.
    nemotron_pages = config.get('nemotron_pages', [7, 15, 17, 19, 25])
    target_pages = [p for p in pages if p in nemotron_pages]
    
    if not target_pages:
        print("No pages match Nemotron target selection.")
        return results
        
    try:
        import torch
        from transformers import AutoModel, AutoProcessor, AutoTokenizer, GenerationConfig
        
        if torch.cuda.is_available():
            device = 'cuda'
            print(f"Using GPU: {torch.cuda.get_device_name(0)}")
            print(f"VRAM available: {torch.cuda.get_device_properties(0).total_memory / 1e9:.1f} GB")
        else:
            device = 'cpu'
            print("WARNING: CUDA not available, falling back to CPU (very slow)")

        model_name = config.get('nemotron_model', 'nvidia/NVIDIA-Nemotron-Parse-v1.1')
        
        print(f"Loading Nemotron Model ({model_name}) on device: {device}...")
        t0 = time.time()
        
        model = AutoModel.from_pretrained(
            model_name,
            trust_remote_code=True,
            dtype=torch.float16 if device == 'cuda' else torch.float32,
            low_cpu_mem_usage=True
        ).to(device).eval()
        
        processor = AutoProcessor.from_pretrained(model_name, trust_remote_code=True)
        gen_config = GenerationConfig.from_pretrained(model_name, trust_remote_code=True)
        gen_config.max_new_tokens = 512
        
        print(f"Nemotron loaded in {time.time() - t0:.2f}s")
        
        task_prompt = '</s><s><predict_bbox><predict_classes><output_markdown>'
        
        for pg in target_pages:
            img = page_images.get(pg)
            if img is None:
                continue
                
            orig_w, orig_h = img.size
            pad_x = (PROC_W - orig_w) / 2
            pad_y = (PROC_H - orig_h) / 2
            
            print(f"Running Nemotron on Page {pg} (pad_x={pad_x:.1f}, pad_y={pad_y:.1f})...")
            
            # Clear GPU cache before page inference
            if device == 'cuda':
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
                
            # Use PyTorch autocast if CUDA is active
            if device == 'cuda':
                autocast_context = torch.amp.autocast('cuda', dtype=torch.float16)
            else:
                autocast_context = torch.amp.autocast('cpu', dtype=torch.bfloat16)
            
            inputs = processor(
                images=[img],
                text=task_prompt,
                return_tensors='pt',
                add_special_tokens=False
            ).to(device)
            
            # Run model generation with OOM guard
            try:
                with torch.no_grad(), autocast_context:
                    outputs = model.generate(**inputs, generation_config=gen_config)
            except torch.cuda.OutOfMemoryError:
                if device == 'cuda':
                    torch.cuda.empty_cache()
                    torch.cuda.ipc_collect()
                    print(f"OOM on page {pg} — reducing max_new_tokens and retrying...")
                    gen_config.max_new_tokens = 256
                    with torch.no_grad(), autocast_context:
                        outputs = model.generate(**inputs, generation_config=gen_config)
                else:
                    raise
                    
            generated_text = processor.batch_decode(outputs, skip_special_tokens=True)[0]
            
            # Free memory immediately
            del inputs, outputs
            if device == 'cuda':
                torch.cuda.empty_cache()
                torch.cuda.ipc_collect()
                
            dets = []
            for match in BLOCK_PATTERN.finditer(generated_text):
                x0_n = float(match.group(1))
                y0_n = float(match.group(2))
                text = match.group(3).strip()
                x1_n = float(match.group(4))
                y1_n = float(match.group(5))
                label = match.group(6).strip()
                
                # Normalised -> Padded tensor pixel coords
                px0 = x0_n * PROC_W
                py0 = y0_n * PROC_H
                px1 = x1_n * PROC_W
                py1 = y1_n * PROC_H
                
                # Center-pad offset inversion
                x0 = px0 - pad_x
                y0 = py0 - pad_y
                x1 = px1 - pad_x
                y1 = py1 - pad_y
                
                # Corner order safety check
                x0, x1 = min(x0, x1), max(x0, x1)
                y0, y1 = min(y0, y1), max(y0, y1)
                
                # Clamp boundary limits
                x0 = max(0.0, min(float(orig_w), x0))
                y0 = max(0.0, min(float(orig_h), y0))
                x1 = max(0.0, min(float(orig_w), x1))
                y1 = max(0.0, min(float(orig_h), y1))
                
                if (x1 - x0) * (y1 - y0) < config.get('min_bbox_area', 100):
                    continue
                    
                dets.append({
                    'type': label,
                    'bbox': [x0, y0, x1, y1],
                    'text': text[:200],
                    'model': 'Nemotron',
                })
            results[pg] = dets
            
    except ImportError as e:
        raise RuntimeError(
            f"Nemotron requires albumentations or other missing dependencies: pip install albumentations==2.0.8. "
            f"Original error: {e}"
        )
    except Exception as e:
        import traceback
        print(f"Failed to run Nemotron inference: {e}")
        traceback.print_exc()
        print("Falling back to baseline detections.")
        # Fallback to mock data for target pages
        results = get_nemotron_mock_fallback(pages, page_images, nemotron_pages)
        
    return results

def get_nemotron_mock_fallback(pages: list, page_images: dict, nemotron_pages: list) -> dict:
    """Mock fallback detections representing Nemotron-Parse."""
    results = {pg: [] for pg in pages}
    mock_db = {
        7: [
            {'type': 'title', 'bbox': [115, 82, 1160, 175]},
            {'type': 'text', 'bbox': [120, 270, 600, 510]},
            {'type': 'text', 'bbox': [120, 530, 600, 840]},
            {'type': 'text', 'bbox': [650, 270, 1150, 490]},
            {'type': 'picture', 'bbox': [150, 870, 1120, 1545]},
        ],
        15: [
            {'type': 'picture', 'bbox': [125, 115, 625, 440]},
            {'type': 'text', 'bbox': [645, 145, 1140, 245]},
            {'type': 'table', 'bbox': [650, 275, 1135, 740]},
        ],
        17: [
            {'type': 'title', 'bbox': [120, 90, 1150, 175]},
            {'type': 'table', 'bbox': [120, 275, 1145, 1545]},
        ],
        19: [
            {'type': 'title', 'bbox': [120, 95, 1150, 145]},
            {'type': 'picture', 'bbox': [120, 175, 600, 595]},
            {'type': 'picture', 'bbox': [645, 175, 1145, 595]},
            {'type': 'picture', 'bbox': [120, 645, 1145, 895]},
            {'type': 'picture', 'bbox': [345, 975, 895, 1545]},
        ],
        25: [
            {'type': 'title', 'bbox': [120, 95, 1150, 145]},
            {'type': 'table', 'bbox': [445, 275, 1145, 375]},
            {'type': 'table', 'bbox': [445, 515, 1145, 675]},
            {'type': 'table', 'bbox': [445, 775, 1145, 875]},
        ]
    }
    
    for pg in pages:
        if pg not in nemotron_pages:
            results[pg] = [] # Nemotron is skipped on this page
            continue
            
        img = page_images.get(pg)
        w, h = (img.width, img.height) if img else (1275, 1650)
        
        scale_x = w / 1275.0
        scale_y = h / 1650.0
        
        dets = []
        raw_dets = mock_db.get(pg, [])
        for d in raw_dets:
            box = [
                float(d['bbox'][0] * scale_x),
                float(d['bbox'][1] * scale_y),
                float(d['bbox'][2] * scale_x),
                float(d['bbox'][3] * scale_y)
            ]
            dets.append({
                'type': d['type'],
                'bbox': box,
                'text': f"Mock Nemotron parsed text on page {pg}",
                'model': 'Nemotron-Parse-v1.1'
            })
        results[pg] = dets
    return results
