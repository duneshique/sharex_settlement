import pandas as pd
import os
import json
import glob
from datetime import datetime

class DateTimeEncoder(json.JSONEncoder):
    def default(self, obj):
        if isinstance(obj, datetime):
            return obj.isoformat()
        if isinstance(obj, pd.Timestamp):
            return obj.isoformat()
        return super().default(obj)

def analyze_sheet_structure(file_path=None):
    if file_path is None:
        files = glob.glob("*.xlsx")
        if not files:
            return {"error": "No xlsx files found in current directory"}
        file_path = files[0]

    if not os.path.exists(file_path):
        return {"error": f"File not found: {file_path}"}
    
    try:
        excel_file = pd.ExcelFile(file_path)
        sheet_names = excel_file.sheet_names
        
        analysis_result = {
            "file_name": os.path.basename(file_path),
            "total_sheets": len(sheet_names),
            "sheets": []
        }
        
        for sheet_name in sheet_names:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
            
            sheet_info = {
                "sheet_name": sheet_name,
                "row_count": len(df),
                "column_count": len(df.columns),
                "columns": []
            }
            
            for col in df.columns:
                col_info = {
                    "column_name": str(col),
                    "inferred_type": str(df[col].dtype),
                    "non_null_count": int(df[col].count()),
                    "sample_values": df[col].dropna().head(3).tolist()
                }
                sheet_info["columns"].append(col_info)
            
            analysis_result["sheets"].append(sheet_info)
            
        return analysis_result
    
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    import sys
    
    target_file = None
    if len(sys.argv) > 1:
        target_file = sys.argv[1]
    
    result = analyze_sheet_structure(target_file)
    
    if "error" in result:
        print(f"Error: {result['error']}")
    else:
        print(f"Analyzing: {result['file_name']}...")
        json_output = json.dumps(result, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
        # Avoid flooding terminal if output is too large, but user asked for output
        # Print only first 100 lines for preview if it's huge, or just print all if it's reasonable
        if len(json_output.splitlines()) > 500:
            print("\n".join(json_output.splitlines()[:100]))
            print("... (truncated for terminal display) ...")
        else:
            print(json_output)

    with open("structure_analysis.json", "w", encoding="utf-8") as f:
        json.dump(result, f, indent=2, ensure_ascii=False, cls=DateTimeEncoder)
    print("\nFull analysis saved to structure_analysis.json")
