import pandas as pd
import numpy as np
import os
import requests
from io import BytesIO

def aggregate_daily_data(input_urls, output_path, start_date_str, end_date_str):
    """
    Aggregates multiple daily ClearGuide Excel exports into one period workbook.
    """
    dfs_meta, dfs_int, dfs_app, dfs_mov = [], [], [], []
    
    print(f"Aggregating {len(input_urls)} files into {output_path}...")
    
    for url in input_urls:
        print(f"  Downloading {url}...")
        response = requests.get(url)
        response.raise_for_status()
        xls = pd.ExcelFile(BytesIO(response.content))
        
        dfs_meta.append(pd.read_excel(xls, "Metadata"))
        dfs_int.append(pd.read_excel(xls, "Intersection"))
        dfs_app.append(pd.read_excel(xls, "By Approach"))
        dfs_mov.append(pd.read_excel(xls, "By Movement"))

    def aggregate_sheet(dfs, group_cols):
        df_combined = pd.concat(dfs, ignore_index=True)
        
        # Identify numeric columns
        numeric_cols = df_combined.select_dtypes(include=[np.number]).columns.tolist()
        weight_col = "Vehicle Samples 1"
        
        if weight_col not in df_combined.columns:
            # Fallback if weight column is missing
            if not group_cols:
                return df_combined.mean(numeric_only=True).to_frame().T
            return df_combined.groupby(group_cols, sort=False).mean(numeric_only=True).reset_index()

        metrics = [c for c in numeric_cols if c != weight_col]
        
        def weighted_avg(group):
            d = {}
            total_weight = group[weight_col].sum()
            d[weight_col] = total_weight
            for m in metrics:
                if total_weight > 0:
                    # Calculate weighted average
                    # Handle cases where m might be all NaN
                    valid_mask = group[m].notna() & group[weight_col].notna()
                    if valid_mask.any():
                        w = group.loc[valid_mask, weight_col]
                        v = group.loc[valid_mask, m]
                        if w.sum() > 0:
                            d[m] = (v * w).sum() / w.sum()
                        else:
                            d[m] = v.mean()
                    else:
                        d[m] = np.nan
                else:
                    d[m] = group[m].mean()
            return pd.Series(d)

        if not group_cols:
            res = weighted_avg(df_combined).to_frame().T
        else:
            res = df_combined.groupby(group_cols, sort=False).apply(weighted_avg, include_groups=False).reset_index()
        
        # Restore original column order and static values from the first file
        orig_cols = dfs[0].columns.tolist()
        for c in orig_cols:
            if c not in res.columns:
                # For non-numeric columns not in group_cols, take the value from the first occurrence
                res[c] = dfs[0][c].iloc[0]
        
        return res[orig_cols]

    # Process sheets
    print("  Processing Intersection sheet...")
    agg_int = aggregate_sheet(dfs_int, [])
    print("  Processing By Approach sheet...")
    agg_app = aggregate_sheet(dfs_app, ["Approach"])
    print("  Processing By Movement sheet...")
    agg_mov = aggregate_sheet(dfs_mov, ["Approach", "Movement"])
    
    # Update Metadata
    print("  Updating Metadata...")
    new_meta = dfs_meta[0].copy()
    # Find columns dynamically as they might vary (though usually col 0 is key, col 1 is value)
    key_col = new_meta.columns[0]
    val_col = new_meta.columns[1]
    
    new_meta.loc[new_meta[key_col].astype(str).str.strip() == "Start Date", val_col] = start_date_str
    new_meta.loc[new_meta[key_col].astype(str).str.strip() == "End Date", val_col] = end_date_str
    
    # Save output
    output_dir = os.path.dirname(output_path)
    if output_dir and not os.path.exists(output_dir):
        os.makedirs(output_dir, exist_ok=True)
        
    print(f"  Saving to {output_path}...")
    with pd.ExcelWriter(output_path, engine="openpyxl") as writer:
        new_meta.to_excel(writer, sheet_name="Metadata", index=False)
        agg_int.to_excel(writer, sheet_name="Intersection", index=False)
        agg_app.to_excel(writer, sheet_name="By Approach", index=False)
        agg_mov.to_excel(writer, sheet_name="By Movement", index=False)
    print("Done.")

if __name__ == "__main__":
    urls_2025 = [
        "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/No.447_JacksonSt_and_Ave48/J.S._A48.1d/1_SignalTrends_JacksonSt_and_Ave48_04092025.xlsx",
        "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/No.447_JacksonSt_and_Ave48/J.S._A48.1d/2_SignalTrends_JacksonSt_and_Ave48_04102025.xlsx",
        "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/No.447_JacksonSt_and_Ave48/J.S._A48.1d/3_SignalTrends_JacksonSt_and_Ave48_04112025.xlsx",
        "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/No.447_JacksonSt_and_Ave48/J.S._A48.1d/4_SignalTrends_JacksonSt_and_Ave48_04122025.xlsx",
        "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/No.447_JacksonSt_and_Ave48/J.S._A48.1d/5_SignalTrends_JacksonSt_and_Ave48_04132025.xlsx",
        "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/No.447_JacksonSt_and_Ave48/J.S._A48.1d/6_SignalTrends_JacksonSt_and_Ave48_04142025.xlsx",
        "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/No.447_JacksonSt_and_Ave48/J.S._A48.1d/7_SignalTrends_JacksonSt_and_Ave48_04152025.xlsx",
    ]
    
    urls_2026 = [
        "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/No.447_JacksonSt_and_Ave48/J.S._A48.1d/SignalTrends_JacksonSt_and_Ave48_04082026.xlsx",
        "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/No.447_JacksonSt_and_Ave48/J.S._A48.1d/SignalTrends_JacksonSt_and_Ave48_04092026.xlsx",
        "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/No.447_JacksonSt_and_Ave48/J.S._A48.1d/SignalTrends_JacksonSt_and_Ave48_04102026.xlsx",
        "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/No.447_JacksonSt_and_Ave48/J.S._A48.1d/SignalTrends_JacksonSt_and_Ave48_04112026.xlsx",
        "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/No.447_JacksonSt_and_Ave48/J.S._A48.1d/SignalTrends_JacksonSt_and_Ave48_04122026.xlsx",
        "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/No.447_JacksonSt_and_Ave48/J.S._A48.1d/SignalTrends_JacksonSt_and_Ave48_04132026.xlsx",
        "https://raw.githubusercontent.com/chrquija/BrownBag_Dashboard/main/data/No.447_JacksonSt_and_Ave48/J.S._A48.1d/SignalTrends_JacksonSt_and_Ave48_04142026.xlsx",
    ]
    
    out1 = "data/No.447_JacksonSt_and_Ave48/aggregated/SignalTrends_JacksonSt_and_Ave48_04092025_to_04152025_aggregated.xlsx"
    out2 = "data/No.447_JacksonSt_and_Ave48/aggregated/SignalTrends_JacksonSt_and_Ave48_04082026_to_04142026_aggregated.xlsx"
    
    aggregate_daily_data(urls_2025, out1, "2025-04-09", "2025-04-15")
    aggregate_daily_data(urls_2026, out2, "2026-04-08", "2026-04-14")
