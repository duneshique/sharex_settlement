import json
import os
from collections import defaultdict

def group_sheets_by_structure(analysis_file):
    if not os.path.exists(analysis_file):
        return {"error": f"Analysis file not found: {analysis_file}"}
    
    with open(analysis_file, "r", encoding="utf-8") as f:
        data = json.load(f)
    
    groups = defaultdict(list)
    
    for sheet in data.get("sheets", []):
        # Create a structure key
        # We use column names and their inferred types as the signature
        cols = sheet.get("columns", [])
        col_signature = tuple((col["column_name"], col["inferred_type"]) for col in cols)
        
        # We can also include column count just to be redundant/safe
        structure_key = (sheet["column_count"], col_signature)
        
        # Store sheet info in the group
        groups[structure_key].append({
            "sheet_name": sheet["sheet_name"],
            "row_count": sheet["row_count"]
        })
    
    # Format the result for output
    grouped_result = []
    for idx, (key, sheets) in enumerate(groups.items(), 1):
        col_count, signature = key
        grouped_result.append({
            "group_id": idx,
            "column_count": col_count,
            "sample_columns": [sig[0] for sig in signature],
            "sheet_count": len(sheets),
            "sheets": sheets
        })
    
    # Sort groups by sheet count (descending) or index
    grouped_result.sort(key=lambda x: x["sheet_count"], reverse=True)
    
    return {
        "file_name": data.get("file_name"),
        "total_sheets": data.get("total_sheets"),
        "total_groups": len(grouped_result),
        "groups": grouped_result
    }

if __name__ == "__main__":
    analysis_file = "structure_analysis.json"
    result = group_sheets_by_structure(analysis_file)
    
    print(f"Grouped Sheets Result (Total Groups: {result['total_groups']}):")
    for group in result["groups"]:
        sheet_names = [s["sheet_name"] for s in group["sheets"]]
        print(f"\n[Group {group['group_id']}] {len(sheet_names)} sheets, {group['column_count']} columns")
        print(f"Columns: {', '.join(group['sample_columns'][:5])}...")
        print(f"Sheets: {', '.join(sheet_names)}")

    # Save to file
    with open("structure_groups.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False)
    print("\nGrouping result saved to structure_groups.json")
