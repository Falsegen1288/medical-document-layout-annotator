import sys
import os

# Set environment variable to make sure cache directory is standard
os.environ["HF_HUB_DISABLE_SYMLINKS_WARNING"] = "1"

from datasets import load_dataset

print("Testing loading PubLayNet with streaming and small batch_size...")
try:
    # Let's try passing batch_size=1 to load_dataset
    pub = load_dataset(
        "shunk031/PubLayNet",
        split="validation",
        trust_remote_code=True,
        streaming=True,
        batch_size=10
    )
    print("Dataset loaded. Iterating first 3 samples...")
    iterator = iter(pub)
    for i in range(3):
        item = next(iterator)
        print(f"Sample {i}: keys = {list(item.keys())}")
        if 'image' in item:
            print(f"  Image size: {item['image'].size}")
    print("Success!")
except Exception as e:
    import traceback
    traceback.print_exc()
