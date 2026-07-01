# layout_benchmark/build_scorecard.py
import os
import json
import pandas as pd

def build_scorecard():
    results_dir = r"d:\antigravity\benchmarking\layout_benchmark\results"
    
    # 1. Load custom results for layers
    df_l1 = pd.read_csv(os.path.join(results_dir, "custom_results_layer1.csv"))
    df_l2 = pd.read_csv(os.path.join(results_dir, "custom_results_layer2.csv"))
    df_l3 = pd.read_csv(os.path.join(results_dir, "custom_results_layer3.csv"))
    df_l4 = pd.read_csv(os.path.join(results_dir, "custom_results_layer4.csv"))
    
    scorecard_rows = []
    
    # helper to format
    def get_val(df, gt_var, model, col):
        sub = df[(df["GT_Variant"] == gt_var) & (df["Model"] == model)]
        if len(sub) > 0:
            val = sub.iloc[0][col]
            return f"{val:.4f}" if isinstance(val, float) else str(val)
        return ""
        
    # --- Layer 1: Geometric ---
    metrics_l1 = ["Precision", "Recall", "F1", "mean_iou", "Class_Acc"]
    for m in metrics_l1:
        for gt in ["GT-raw", "GT-tight"]:
            yolo = get_val(df_l1, gt, "DocLayoutYOLO", m)
            nemo = get_val(df_l1, gt, "Nemotron", m)
            
            # Tolerant versions
            yolo_tol = get_val(df_l1, gt, "DocLayoutYOLO", f"{m}_tol") if f"{m}_tol" in df_l1.columns else ""
            nemo_tol = get_val(df_l1, gt, "Nemotron", f"{m}_tol") if f"{m}_tol" in df_l1.columns else ""
            
            footnote = "IoU-sensitive metric, affected by ground-truth padding." if m in ["Precision", "Recall", "F1", "mean_iou"] else ""
            
            scorecard_rows.append({
                "Layer": "Layer 1: Geometric",
                "Metric": m,
                "GT_Variant": gt,
                "DocLayoutYOLO": yolo,
                "Nemotron": nemo,
                "Tolerant_DocLayoutYOLO": yolo_tol,
                "Tolerant_Nemotron": nemo_tol,
                "Footnote": footnote
            })
            
    # --- Layer 2: COTe ---
    metrics_l2 = ["Coverage", "Overlap", "Trespass", "Excess"]
    for m in metrics_l2:
        for gt in ["GT-raw", "GT-tight"]:
            yolo = get_val(df_l2, gt, "DocLayoutYOLO", m)
            nemo = get_val(df_l2, gt, "Nemotron", m)
            
            footnote = "Robust to uniform padding bias, measures localization quality." if m in ["Coverage", "Trespass"] else "Slightly sensitive to padding borders."
            
            scorecard_rows.append({
                "Layer": "Layer 2: COTe",
                "Metric": m,
                "GT_Variant": gt,
                "DocLayoutYOLO": yolo,
                "Nemotron": nemo,
                "Tolerant_DocLayoutYOLO": "",
                "Tolerant_Nemotron": "",
                "Footnote": footnote
            })
            
    # --- Layer 3: LED ---
    # Layer 3 has counts rather than fractions
    metrics_l3 = ['Missing', 'Hallucination', 'Size-Error', 'Split', 'Merge', 'Overlap-Pred', 'Duplicate', 'Misclassification']
    for m in metrics_l3:
        for gt in ["GT-raw", "GT-tight"]:
            yolo = get_val(df_l3, gt, "DocLayoutYOLO", m)
            nemo = get_val(df_l3, gt, "Nemotron", m)
            
            footnote = "Count-based error metric."
            
            scorecard_rows.append({
                "Layer": "Layer 3: LED",
                "Metric": m,
                "GT_Variant": gt,
                "DocLayoutYOLO": yolo,
                "Nemotron": nemo,
                "Tolerant_DocLayoutYOLO": "",
                "Tolerant_Nemotron": "",
                "Footnote": footnote
            })
            
    # --- Layer 4: Reading Order ---
    metrics_l4 = ["ROKT", "ROA"]
    for m in metrics_l4:
        for gt in ["GT-raw", "GT-tight"]:
            yolo = get_val(df_l4, gt, "DocLayoutYOLO", m)
            nemo = get_val(df_l4, gt, "Nemotron", m)
            
            footnote = "Calculated on IoU >= 0.30 matched segments, unaffected by minor padding."
            
            scorecard_rows.append({
                "Layer": "Layer 4: Reading Order",
                "Metric": m,
                "GT_Variant": gt,
                "DocLayoutYOLO": yolo,
                "Nemotron": nemo,
                "Tolerant_DocLayoutYOLO": "",
                "Tolerant_Nemotron": "",
                "Footnote": footnote
            })
            
    df_scorecard = pd.DataFrame(scorecard_rows)
    scorecard_path = os.path.join(results_dir, "consolidated_scorecard.csv")
    df_scorecard.to_csv(scorecard_path, index=False)
    print(f"Consolidated scorecard compiled and saved to: {scorecard_path}")
    
    # print Markdown-formatted preview of L1 & L2 for console validation
    l12_mask = df_scorecard["Layer"].isin(["Layer 1: Geometric", "Layer 2: COTe"])
    print("\n--- Layer 1 & 2 Results Preview ---")
    print(df_scorecard[l12_mask][["Layer", "Metric", "GT_Variant", "DocLayoutYOLO", "Nemotron"]].to_string(index=False))

if __name__ == "__main__":
    build_scorecard()
