import os
import pandas as pd


# =========================
# 1. 路径
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
processed_dir = os.path.join(BASE_DIR, "data", "processed")
input_path = os.path.join(processed_dir, "cases_check_final_a.csv")
output_path = os.path.join(processed_dir, "cases_high_quality_a.csv")
# =========================
# 2. 读取抽取后的数据
# =========================
df = pd.read_csv(input_path)

print("原始抽取数据量：", len(df))
# =========================
# 3. 只保留核心字段齐全的数据
#    history + tcm_diag + prescription
# =========================
df_clean = df[
    df["history"].notna() &
    df["tcm_diag"].notna() &
    df["prescription"].notna()
].copy()
print("保留 核心三字段 非空后：", len(df_clean))
# =========================
# 4. 规则化中医诊断：必须包含关键词
# =========================
def valid_tcm_diag(text):
    if not isinstance(text, str):
        return False
    text = text.strip()

    # 太短直接不要
    if len(text) < 2:
        return False
    if len(text) > 20:
        return False
    # 合格中医诊断关键词
    keywords = [
        "证", "气", "血", "阴", "阳",
        "虚", "实", "湿", "热", "寒",
        "瘀", "痰", "郁", "毒", "滞",'两','心','肝','脾','肺','肾','络','不足','结','下焦','中焦','上焦'
    ]
    return any(k in text for k in keywords)
df_clean = df_clean[df_clean["tcm_diag"].apply(valid_tcm_diag)].copy()

print("保留 符合关键词 的中医诊断后：", len(df_clean))


# =========================
# 5. 去掉明显错误诊断
#    比如只有病名、癌病、肿瘤病，而没有证候意味
# =========================
def remove_bad_diag(text):
    if not isinstance(text, str):
        return False

    text = text.strip()

    # 明显偏病名而非辨证
    bad_patterns = [
        "癌病", "肿瘤病", "妇科癌病"
    ]

    if text in bad_patterns:
        return False

    # 如果含“癌/瘤/病”但完全没有证候关键词，也不要
    disease_words = ["癌", "瘤", "病"]
    syndrome_words = [
        "证", "气", "血", "阴", "阳",
        "虚", "实", "湿", "热", "寒",
        "瘀", "痰", "郁", "毒", "滞",'两','心','肝','脾','肺','肾','络','不足','结','下焦','中焦','上焦'
    ]

    if any(w in text for w in disease_words):
        if not any(k in text for k in syndrome_words):
            return False

    return True


df_clean = df_clean[df_clean["tcm_diag"].apply(remove_bad_diag)].copy()

print("去掉明显错误诊断后：", len(df_clean))


# =========================
# 6. 再做一点轻度清洗（可选但推荐）
# =========================
# 去重：按 raw_text 或 title+diagnosis+prescription 任选
if "raw_text" in df_clean.columns:
    df_clean = df_clean.drop_duplicates(subset=["raw_text"]).reset_index(drop=True)
else:
    df_clean = df_clean.drop_duplicates(
        subset=["title", "tcm_diag", "prescription"]
    ).reset_index(drop=True)

print("去重后最终数量：", len(df_clean))


# =========================
# 7. 保存高质量数据
# =========================
# 你可以只保留关键列
keep_cols = [
    "title",
    "gender",
    "age",
    "tcm_diag",
    "history",
    "prescription",
    "raw_text"
]

# 防止有列不存在时报错
keep_cols = [col for col in keep_cols if col in df_clean.columns]

df_final = df_clean[keep_cols].copy()

df_final.to_csv(output_path, index=False, encoding="utf-8-sig")

print("\n高质量数据已保存：", output_path)
print("最终高质量数据量：", len(df_final))

print("\n前5条预览：")
print(df_final.head())