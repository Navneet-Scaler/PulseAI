import os
import sqlite3
import pandas as pd

DB_PATH = os.environ.get("DATABASE_URL", "sqlite:///pulse_ai.db").replace("sqlite:///", "")
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "../../exported_assets")

def export_tables():
    os.makedirs(OUTPUT_DIR, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    
    tables = ["encounters", "ai_coding_logs", "audit_logs", "claims"]
    for t in tables:
        df = pd.read_sql_query(f"SELECT * FROM {t}", conn)
        out_path = os.path.join(OUTPUT_DIR, f"{t}.csv")
        df.to_csv(out_path, index=False)
        print(f"Exported table '{t}' to {out_path} ({len(df)} rows)")
        
    conn.close()
    print("All tables successfully exported!")

if __name__ == "__main__":
    export_tables()
