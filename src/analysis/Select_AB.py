import pandas as pd
import os
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
PROCESSED_DIR = os.path.join(BASE_DIR, "data", "processed")
OUTPUT_FILE = os.path.join(RAW_DIR, "cases_raw.csv")
OUTPUT_FILE_N = os.path.join(RAW_DIR, "cases_rawN.csv")
OUTPUT_FILE_C = os.path.join(PROCESSED_DIR, "cases_UNC.csv")
df_a = pd.read_csv(OUTPUT_FILE)
df_b = pd.read_csv(OUTPUT_FILE_N)

df = pd.concat([df_a, df_b], ignore_index=True)
df = df.drop_duplicates(subset=["source_url", "case_no"])
df_clean = df[
    df["tcm_diag"].notna() &
    (
        df["chief_complaint"].notna() |
        df["history"].notna()
    )
]
len(df_clean)
print("总数:", len(df))
print("清洗后:", len(df_clean))
print("有主诉:", df_clean["chief_complaint"].notna().sum())
print("有现病史:", df_clean["history"].notna().sum())
print("有中医诊断:", df_clean["tcm_diag"].notna().sum())
print("有处方:", df_clean["prescription"].notna().sum())
df_clean.to_csv(OUTPUT_FILE_C, index=False, encoding="utf-8-sig")
print(df_clean["tcm_diag"].value_counts().head(10))
print(df_clean["prescription"].str.len().describe())
print(df_clean.isna().sum())