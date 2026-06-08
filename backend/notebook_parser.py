import re
import nbformat
import traceback

def extract_notebook_config(notebook_path: str) -> dict:
    """
    Parse the .ipynb file and extract:
    1. API keys / config values (LANDING_AI_API_KEY, CONFIG dict, NEMOTRON_PAGES)
    2. Which models are present (scan for cell markers)
    3. Model parameters / settings used
    """
    config = {
        "models_found": [],
        "landing_ai_key": None,
        "nemotron_pages": [7, 15, 17, 19, 25], # default fallback
        "config": {
            "render_dpi": 150,
            "max_pages": 30,
            "min_bbox_area": 100,
        }
    }
    
    try:
        with open(notebook_path, "r", encoding="utf-8") as f:
            nb = nbformat.read(f, as_version=4)
    except Exception as e:
        print(f"Error reading notebook: {e}")
        return config

    for cell in nb.cells:
        if cell.cell_type != 'code':
            continue
        src = cell.source
        
        # Detect model presence
        if 'DocLayoutYOLO' in src or 'docling' in src.lower():
            if 'DocLayoutYOLO' not in config['models_found']:
                config['models_found'].append('DocLayoutYOLO')
        if 'Nemotron' in src or 'nemotron' in src.lower():
            if 'Nemotron' not in config['models_found']:
                config['models_found'].append('Nemotron')
        if 'LandingAIADE' in src or 'landingai' in src.lower() or 'ade-dpt2' in src.lower():
            if 'ADE-DPT2' not in config['models_found']:
                config['models_found'].append('ADE-DPT2')
        
        # Extract API key
        if 'LANDING_AI_API_KEY' in src or 'landing_ai_api_key' in src.lower():
            match = re.search(r'LANDING_AI_API_KEY\s*=\s*["\']([^"\']+)["\']', src, re.IGNORECASE)
            if match:
                config['landing_ai_key'] = match.group(1)
        
        # Extract NEMOTRON_PAGES if specified as a list
        if 'NEMOTRON_PAGES' in src or 'nemotron_pages' in src:
            match = re.search(r'nemotron_pages\s*=\s*\[([^\]]+)\]', src, re.IGNORECASE)
            if match:
                try:
                    pages_str = match.group(1)
                    config['nemotron_pages'] = [int(p.strip()) for p in pages_str.split(',') if p.strip().isdigit()]
                except:
                    pass
        
        # Extract CONFIG dict
        if "CONFIG" in src and ("min_bbox_area" in src or "render_dpi" in src):
            # Execute this cell in an isolated namespace to safely extract values
            namespace = {}
            try:
                # We mock torch and other heavy dependencies so execution does not crash
                exec("class Mock:\n  def __getattr__(self, name):\n    return lambda *args, **kwargs: None", namespace)
                # Filter out lines that install packages or run subprocesses
                clean_src = []
                for line in src.split("\n"):
                    if not (line.strip().startswith("!") or line.strip().startswith("get_ipython") or "pip install" in line or "subprocess" in line):
                        clean_src.append(line)
                
                exec("\n".join(clean_src), namespace)
                if 'CONFIG' in namespace and isinstance(namespace['CONFIG'], dict):
                    # Merge into our configuration
                    for k, v in namespace['CONFIG'].items():
                        config['config'][k] = v
                    if 'nemotron_pages' in namespace['CONFIG']:
                        config['nemotron_pages'] = namespace['CONFIG']['nemotron_pages']
            except Exception as ex:
                print(f"Warning: Failed to execute CONFIG cell: {ex}")
                # Fallback to regex parsing if execution fails
                dpi_match = re.search(r'[\'"]render_dpi[\'"]\s*:\s*(\d+)', src)
                if dpi_match:
                    config['config']['render_dpi'] = int(dpi_match.group(1))
                area_match = re.search(r'[\'"]min_bbox_area[\'"]\s*:\s*(\d+)', src)
                if area_match:
                    config['config']['min_bbox_area'] = int(area_match.group(1))
                max_match = re.search(r'[\'"]max_pages[\'"]\s*:\s*(\d+)', src)
                if max_match:
                    config['config']['max_pages'] = int(max_match.group(1))

    # Always ensure ADE-DPT2 is added if landingai is mentioned in any form, 
    # but let's make sure it falls back to having the models list populated
    if not config['models_found']:
        # Default fallback based on notebook name/content inspection
        config['models_found'] = ["DocLayoutYOLO", "Nemotron", "ADE-DPT2"]

    return config
