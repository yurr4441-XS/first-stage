import os
import re
import pandas as pd


# =========================
# 1. 文本清洗
# =========================
def clean_text(text):
    if not isinstance(text, str):
        return ""

    # HTML残留 / 空白污染
    text = text.replace("&nbsp;", " ")
    text = text.replace("NBSP", " ")
    text = text.replace("\xa0", " ")
    text = text.replace("\u3000", " ")

    # 不可见字符
    text = re.sub(r"[\u200b-\u200f\u202a-\u202e]", "", text)

    # 标点与空白规范
    text = re.sub(r"：\s+", "：", text)
    text = re.sub(r"(\d+)\s+岁", r"\1岁", text)
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n+", "\n", text)

    return text.strip()


# =========================
# 2. 基础字段：性别 / 年龄
# =========================
def extract_gender(text):
    if not isinstance(text, str):
        return None

    # 性别：男/女
    m = re.search(r"性别\s*：?\s*(男|女)", text)
    if m:
        return m.group(1)

    # 男性 / 女性
    m = re.search(r"(女性|男性)", text)
    if m:
        return "女" if m.group(1) == "女性" else "男"

    # 某某，男，54岁 / 某某 女 67岁
    m = re.search(r"[，,\s](男|女)[，,\s]", text)
    if m:
        return m.group(1)

    return None


def extract_age(text):
    if not isinstance(text, str):
        return None

    m = re.search(r"(\d{1,3})\s*岁", text)
    return int(m.group(1)) if m else None


# =========================
# 3. 通用字段抽取
# =========================
def extract_field(text, field_aliases, next_fields=None, extra_stops=None):
    """
    field_aliases: 当前字段可能名称
    next_fields: 后续字段，作为终止条件
    extra_stops: 额外终止词
    """
    if not isinstance(text, str):
        return None

    field_pattern = "|".join([re.escape(f) for f in field_aliases])

    stop_parts = []

    if next_fields:
        next_pattern = "|".join([re.escape(f) for f in next_fields])
        stop_parts.append(rf"(?:{next_pattern})\s*：?")

    # 默认统一停止条件
    default_stops = [
        r"二诊",
        r"三诊",
        r"四诊",
        r"五诊",
        r"复诊",
        r"按语",
        r"按",
        r"病案分析",
        r"体会",
        r"复按",
        r"签名"
    ]
    stop_parts.extend(default_stops)

    if extra_stops:
        stop_parts.extend([re.escape(x) for x in extra_stops])

    stop_pattern = "|".join(stop_parts)

    pattern = rf"(?:{field_pattern})\s*：?\s*(.*?)(?=\s*(?:{stop_pattern})|$)"
    m = re.search(pattern, text, flags=re.S)

    if m:
        result = m.group(1).strip()

        # 清掉首尾多余标点
        result = re.sub(r"^[，,；;。\s]+", "", result)
        result = re.sub(r"[，,；;。\s]+$", "", result)

        return result if result else None

    return None


# =========================
# 4. 中医诊断：最后一版收紧
# =========================
def extract_tcm_diag(text):
    result = extract_field(
        text,
        ["中医诊断", "中医辨证", "辨证", "证型", "证候诊断"],
        ["西医诊断", "西诊", "治则", "治法", "治拟", "处方", "方药", "药用", "予方"]
    )

    if not result:
        return None

    # 收紧边界：如果里面混进了后续字段，强制截掉
    result = re.split(r"(西医诊断|西诊|治则|治法|治拟|处方|方药|药用|予方)", result)[0].strip()

    # 再做一层保守切断：常见“。治宜...”这类
    result = re.split(r"(治宜|治疗以|治以|予以)", result)[0].strip()

    # 太长就截一刀，防止整段病机/治法吞进去
    if len(result) > 30:
        # 优先按逗号句号切
        result = re.split(r"[，。；;]", result)[0].strip()

    return result if result else None


# =========================
# 5. 西医诊断：标准抓取 + fallback
# =========================
def extract_wm_diag(text):
    result = extract_field(
        text,
        ["西医诊断", "西诊"],
        ["治则", "治法", "治拟", "处方", "方药", "药用", "予方"]
    )
    if result:
        result = re.split(r"(治则|治法|治拟|处方|方药|药用|予方)", result)[0].strip()
        return result if result else None

    # fallback：抓“诊断：xxx”，但尽量避开中医
    m = re.search(r"诊断\s*：\s*(.*?)(?=治则|治法|治拟|处方|方药|药用|予方|$)", text, re.S)
    if m:
        candidate = m.group(1).strip()
        if "中医" not in candidate and "辨证" not in candidate:
            candidate = re.split(r"[。；;\n]", candidate)[0].strip()
            return candidate if candidate else None

    return None


# =========================
# 6. 现病史
# =========================
def extract_history(text):
    result = extract_field(
        text,
        ["现病史", "病史", "病程"],
        ["中医诊断", "中医辨证", "辨证", "证型", "西医诊断", "西诊", "治则", "治法", "治拟", "处方", "方药", "药用", "予方"]
    )
    if result:
        result = re.split(r"(中医诊断|中医辨证|辨证|证型|西医诊断|西诊|治则|治法|治拟|处方|方药|药用|予方)", result)[0].strip()
        return result if result else None
    return None


# =========================
# 7. 处方
# =========================
def extract_prescription(text):
    result = extract_field(
        text,
        ["处方", "方药", "药用", "予方", "组成"],
        ["病案分析", "按语", "按", "体会", "复按", "签名"]
    )
    if result:
        result = re.split(r"(病案分析|按语|体会|复按|签名)", result)[0].strip()
        return result if result else None
    return None


# =========================
# 8. 主流程
# =========================
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
raw_path = os.path.join(BASE_DIR, "data", "raw", "cases_raw.csv")
processed_dir = os.path.join(BASE_DIR, "data", "processed")
os.makedirs(processed_dir, exist_ok=True)

df = pd.read_csv(raw_path)
df.columns = ["title", "source_url", "sub_title", "raw_text"]

# 基础清洗
df = df.dropna(subset=["raw_text"]).copy()
df["raw_text"] = df["raw_text"].apply(clean_text)

# 抽取
df["gender"] = df["raw_text"].apply(extract_gender)
df["age"] = df["raw_text"].apply(extract_age)
df["tcm_diag"] = df["raw_text"].apply(extract_tcm_diag)
df["wm_diag"] = df["raw_text"].apply(extract_wm_diag)
df["history"] = df["raw_text"].apply(extract_history)
df["prescription"] = df["raw_text"].apply(extract_prescription)

# =========================
# 9. 保存
# =========================
full_output_path = os.path.join(processed_dir, "cases_extracted_final_a.csv")
check_output_path = os.path.join(processed_dir, "cases_check_final_a.csv")

df.to_csv(full_output_path, index=False, encoding="utf-8-sig")

check_df = df[[
    "title",
    "gender",
    "age",
    "tcm_diag",
    "wm_diag",
    "history",
    "prescription",
    "raw_text"
]]
check_df.to_csv(check_output_path, index=False, encoding="utf-8-sig")

# =========================
# 10. 输出统计
# =========================
print("结果概览：")
print(df[["title", "gender", "age", "tcm_diag", "wm_diag", "history", "prescription"]].info())

print("\n缺失统计：")
print(df[["gender", "age", "tcm_diag", "wm_diag", "history", "prescription"]].isnull().sum())

print("\n全量结果已保存：", full_output_path)
print("检查结果已保存：", check_output_path)