# page_title：页面标题
# source_url：详情页链接
# case_no：该页面第几例
# chief_complaint：主诉
# history：现病史/病史
# tcm_diag：中医诊断/辨证
# prescription：处方/方药
# raw_text：该病例拼接后的原文
import os
import re
import time
import requests
import pandas as pd
from bs4 import BeautifulSoup
from urllib.parse import urljoin
# 1. 基础配置
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
RAW_DIR = os.path.join(BASE_DIR, "data", "raw")
os.makedirs(RAW_DIR, exist_ok=True)
OUTPUT_FILE = os.path.join(RAW_DIR, "cases_rawN.csv")
BASE_URL = "https://www.chqzyy.com/"
CATALOG_URL = "https://www.chqzyy.com/artclass.php?id=87"
HEADERS = {"User-Agent": "Mozilla/5.0"}
TIMEOUT = 15
SLEEP_SECONDS = 1
# 断点续爬
if os.path.exists(OUTPUT_FILE):
    try:
        df_existing = pd.read_csv(OUTPUT_FILE)
        if'source_url' in df_existing.columns:
            done_urls = set(df_existing["source_url"].dropna())
        else:
            done_urls = set()
    except Exception as e:
        print("读取CSV失败，重置：", e)
        df_existing = pd.DataFrame()
        done_urls = set()
else:
    df_existing = pd.DataFrame()
    done_urls = set()
# 2.多次爬虫
def safe_get(url, retries=3):
    for i in range(retries):
        try:
            res = requests.get(url, headers=HEADERS, timeout=TIMEOUT)
            res.raise_for_status()
            res.encoding = res.apparent_encoding
            return res.text
        except Exception as e:
            print(f"重试 {i+1}/{retries}：{e}")
            time.sleep(2)
    return None
# 3. 文本清洗
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
# 4. 目录页解析
# =========================
def parse_catalog(catalog_html):
    soup = BeautifulSoup(catalog_html, "html.parser")
    items = []
    # 容器 + 空格 + 目标标签 +class，三段式selector，dom限定抓取范围
    for a in soup.select("ul.ul-list a.ul-list__li"):
        href = a.get("href")
        if not href:
            continue
        full_url = urljoin(BASE_URL,href)
        title_node = a.select_one("div.ul-list_title")
        title = title_node.get_text(strip=True) if title_node else a.get_text(strip=True)
        items.append({"catalog_title": title,"url": full_url })
    # 去重
    dedup = []
    seen = set()
    for item in items:
        if item["url"] not in seen:
            dedup.append(item)
            seen.add(item["url"])
    return dedup
# 5. 判断是否新病例开始+是否复诊+无用段落
def is_new_case_start(text):
    # 判断当前段是否意味着新病例开始
    if not isinstance(text, str):
        return False
    patterns = [ r"^(病例[一二三四五六七八九十0-9]+)", r"^(案[一二三四五六七八九十0-9]+)", r"^姓名\s*[:：]",r"^初诊日期\s*[:：]" ]
    return any(re.search(p, text) for p in patterns)
def is_followup_case(text):
    if not isinstance(text, str):
        return False
    followup_keywords = [ "复诊", "复诊日期", "复诊记录"]
    return any(k in text for k in followup_keywords)
def is_useless_paragraph(text):
    """判断是否是无用段落，直接丢弃"""
    if not isinstance(text, str):
        return True
    text = text.strip()
    if not text:
        return True
    bad_keywords = ["心得体会", "体会", "按语", "病例总结", "医案总结",
        "病例一", "病例二", "病例三", "病例四",'更新时间'    ]
    if any(k in text for k in bad_keywords):
        return True
    # 只有日期的段落也不要
    if re.fullmatch(r"\d{4}年\d{1,2}月\d{1,2}日.*", text):
        return True
    return False
# 6. 初始化病例字典
def new_case(page_title, source_url, case_no):
    return {"page_title": page_title,"source_url": source_url,"case_no": case_no,"chief_complaint": None, "history": None,
        "tcm_diag": None,"prescription": None,"wm_diag": None,"raw_parts": []}

# 7. 从单段 p 里抽字段
def fill_case_field(case_dict, text):
    if not isinstance(text, str):
        return case_dict
    extracted = extract_labeled_fields(text)

    # 如果这一段一个标签都没识别到，但又不是废段，可视情况保留到 raw_parts
    if not extracted:
        return case_dict

    if extracted.get("chief_complaint"):
        case_dict["chief_complaint"] = extracted["chief_complaint"]
        case_dict["raw_parts"].append("主诉：" + extracted["chief_complaint"])

    if extracted.get("history"):
        case_dict["history"] = extracted["history"]
        case_dict["raw_parts"].append("现病史：" + extracted["history"])

    if extracted.get("tcm_diag"):
        case_dict["tcm_diag"] = extracted["tcm_diag"]
        case_dict["raw_parts"].append("中医诊断：" + extracted["tcm_diag"])

    if extracted.get("wm_diag"):
        case_dict["wm_diag"] = extracted["wm_diag"]
        case_dict["raw_parts"].append("西医诊断：" + extracted["wm_diag"])

    if extracted.get("prescription"):
        value = normalize_prescription(extracted["prescription"])
        if value:
            case_dict["prescription"] = value
            case_dict["raw_parts"].append("处方：" + value)
    if not case_dict.get("history"):
        if len(text) > 20 and not any(k in text for k in ["诊断", "处方", "方药"]):
            case_dict["history"] = text

    return case_dict
# 判断药物处方边界
def extract_labeled_fields(text):
    """
        一段里同时抽多个字段：
        主诉 / 现病史 / 中医诊断 / 西医诊断 / 处方
        """
    if not isinstance(text, str):
        return {}
    text = clean_text(text)
    field_patterns = {
        "chief_complaint": r"(主诉)\s*[:：]?\s*(.*?)(?=(现病史|病史|中医诊断|中医辨证|辨证|证型|西医诊断|西诊|处方|方药|药用|。|$))",
        "history": r"(现病史|病史)\s*[:：]?\s*(.*?)(?=(主诉|中医诊断|中医辨证|辨证|证型|西医诊断|西诊|处方|方药|药用|。|$))",
        "tcm_diag": r"(中医诊断|中医辨证|辨证|证型)\s*[:：]?\s*(.*?)(?=(西医诊断|西诊|处方|方药|药用|主诉|现病史|病史|。|$))",
        "wm_diag": r"(西医诊断|西诊)\s*[:：]?\s*(.*?)(?=(处方|方药|药用|主诉|现病史|病史|中医诊断|中医辨证|辨证|证型|。|$))",
        "prescription": r"(处方|方药|药用)\s*[:：]?\s*(.*?)(?=(主诉|现病史|病史|中医诊断|中医辨证|辨证|证型|西医诊断|西诊|。|$))"
    }
    result = {}
    for field, pattern in field_patterns.items():
        m = re.search(pattern, text, flags=re.S)
        if m:
            value = m.group(2).strip(" ：:;；，,。. ")
            if value:
                result[field] = value
    return result
def normalize_prescription(text):
    if not isinstance(text, str):
        return None

    text = clean_text(text)

    bad_words = ["针灸", "推拿", "热敷", "按摩", "外洗", "砭石", "耳穴", "关节松解"]
    if any(w in text for w in bad_words):
        return None

    # ===== 新增：中药特征词 =====
    herb_keywords = ["甘草", "白术", "茯苓", "当归", "川芎", "黄芪", "半夏", "陈皮", "生姜"]

    herb_hit = sum(1 for h in herb_keywords if h in text)

    has_dose = bool(re.search(r"\d+\s*(g|克|ml|毫升)", text, flags=re.I))
    has_take_method = bool(re.search(r"(水煎服|每日|日\d+剂|一日\d+剂|共\d+剂|分.*次服)", text))
    has_many_commas = text.count("，") + text.count(",") >= 3

    # ===== 放宽策略 =====
    if has_dose or has_take_method or has_many_commas or herb_hit >= 2:
        return text.strip("；;。 ")

    return None
# 统一打包到一个单位
def finalize_case(case_dict):
    raw_parts = case_dict.get("raw_parts", [])
    case_dict["raw_text"] = "\n".join(raw_parts).strip()
    del case_dict["raw_parts"]
    return case_dict
# =========================
# 8. 详情页解析
def parse_detail(detail_html, source_url):
    soup = BeautifulSoup(detail_html, "html.parser")
    title_node = soup.select_one("div.art_title")
    page_title = title_node.get_text(strip=True) if title_node else ""
    content_div = soup.select_one("div.artcontent")
    if not content_div:
        return []
    paragraphs = content_div.select("p")
    if not paragraphs:
        return []
    cases = []
    case_no = 1
    current_case = new_case(page_title, source_url, case_no)
    for p in paragraphs:
        text = clean_text(p.get_text(" ", strip=True))
        if not text:
            continue
        # 无用段直接删
        if is_useless_paragraph(text):
            continue
        # 碰到复诊或新病例边界，先把当前病例打包
        if is_new_case_start(text) or is_followup_case(text):
            if current_case["raw_parts"]:
                current_case = finalize_case(current_case)
                cases.append(current_case)
            case_no += 1
            current_case = new_case(page_title, source_url, case_no)
            # 边界行本身不进入新病例
            continue
        # 只把合格段写进去
        current_case = fill_case_field(current_case, text)
    # 最后一例
    if current_case["raw_parts"]:
        current_case = finalize_case(current_case)
        cases.append(current_case)
    return cases
# =========================
# 9. 主流程
def main():
    print("当前脚本路径：", __file__)
    print("BASE_DIR：", BASE_DIR)
    print("RAW_DIR：", RAW_DIR)
    print("OUTPUT_FILE：", OUTPUT_FILE)
    print("RAW_DIR是否存在：", os.path.exists(RAW_DIR))

    # 统计字典
    stats = {
        "catalog_total": 0,
        "skipped_urls": 0,
        "detail_fetch_fail": 0,
        "detail_parse_empty": 0,
        "cases_total": 0,
        "saved_total": 0,
        "has_chief_complaint": 0,
        "has_history": 0,
        "has_tcm_diag": 0,
        "has_wm_diag": 0,
        "has_prescription": 0
    }

    # debug样本池
    debug_rows = []

    # 最终结果缓存
    merged_df = pd.DataFrame()

    catalog_html = safe_get(CATALOG_URL)
    if not catalog_html:
        print("目录页获取失败")
        return

    detail_items = parse_catalog(catalog_html)
    stats["catalog_total"] = len(detail_items)
    print(f"目录页共抓到 {len(detail_items)} 个详情页链接")

    for idx, item in enumerate(detail_items, start=1):
        url = item["url"]
        catalog_title = item["catalog_title"]

        if url in done_urls:
            print(f"[跳过] {url}")
            stats["skipped_urls"] += 1
            continue

        print(f"[{idx}/{len(detail_items)}] 抓取：{catalog_title} -> {url}")

        detail_html = safe_get(url)
        if not detail_html:
            print("  详情页请求失败")
            stats["detail_fetch_fail"] += 1
            continue

        cases = parse_detail(detail_html, url)
        if not cases:
            print("  未解析出病例")
            stats["detail_parse_empty"] += 1
            continue

        # 给当前页病例补 catalog_title
        for case in cases:
            case["catalog_title"] = catalog_title

        # ===== 统计与debug =====
        for case in cases:
            stats["cases_total"] += 1

            if case.get("chief_complaint"):
                stats["has_chief_complaint"] += 1
            if case.get("history"):
                stats["has_history"] += 1
            if case.get("tcm_diag"):
                stats["has_tcm_diag"] += 1
            if case.get("wm_diag"):
                stats["has_wm_diag"] += 1
            if case.get("prescription"):
                stats["has_prescription"] += 1

            # debug样本1：没有处方
            if case.get("raw_text") and not case.get("prescription"):
                debug_rows.append({
                    "source_url": case.get("source_url"),
                    "case_no": case.get("case_no"),
                    "page_title": case.get("page_title"),
                    "problem_type": "missing_prescription",
                    "chief_complaint": case.get("chief_complaint"),
                    "history": case.get("history"),
                    "tcm_diag": case.get("tcm_diag"),
                    "wm_diag": case.get("wm_diag"),
                    "prescription": case.get("prescription"),
                    "raw_text": case.get("raw_text")
                })

            # debug样本2：主诉里混了现病史
            if case.get("chief_complaint") and "现病史" in str(case.get("chief_complaint")):
                debug_rows.append({
                    "source_url": case.get("source_url"),
                    "case_no": case.get("case_no"),
                    "page_title": case.get("page_title"),
                    "problem_type": "chief_contains_history",
                    "chief_complaint": case.get("chief_complaint"),
                    "history": case.get("history"),
                    "tcm_diag": case.get("tcm_diag"),
                    "wm_diag": case.get("wm_diag"),
                    "prescription": case.get("prescription"),
                    "raw_text": case.get("raw_text")
                })

            # debug样本3：中医诊断里混了西医诊断
            if case.get("tcm_diag") and "西医诊断" in str(case.get("tcm_diag")):
                debug_rows.append({
                    "source_url": case.get("source_url"),
                    "case_no": case.get("case_no"),
                    "page_title": case.get("page_title"),
                    "problem_type": "tcm_contains_wm",
                    "chief_complaint": case.get("chief_complaint"),
                    "history": case.get("history"),
                    "tcm_diag": case.get("tcm_diag"),
                    "wm_diag": case.get("wm_diag"),
                    "prescription": case.get("prescription"),
                    "raw_text": case.get("raw_text")
                })

            # debug样本4：有主诉但没现病史
            if case.get("chief_complaint") and not case.get("history"):
                debug_rows.append({
                    "source_url": case.get("source_url"),
                    "case_no": case.get("case_no"),
                    "page_title": case.get("page_title"),
                    "problem_type": "chief_without_history",
                    "chief_complaint": case.get("chief_complaint"),
                    "history": case.get("history"),
                    "tcm_diag": case.get("tcm_diag"),
                    "wm_diag": case.get("wm_diag"),
                    "prescription": case.get("prescription"),
                    "raw_text": case.get("raw_text")
                })
            #     debug5：疑似
            if case.get("prescription") and len(case.get("prescription")) < 10:
                debug_rows.append({
                    "source_url": case.get("source_url"),
                    "case_no": case.get("case_no"),
                    "page_title": case.get("page_title"),
                    "problem_type": "chief_without_history",
                    "chief_complaint": case.get("chief_complaint"),
                    "history": case.get("history"),
                    "tcm_diag": case.get("tcm_diag"),
                    "wm_diag": case.get("wm_diag"),
                    "prescription": case.get("prescription"),
                    "raw_text": case.get("raw_text")
                })

        # ===== 只保存当前页，不再用all_rows =====
        new_df = pd.DataFrame(cases)

        if os.path.exists(OUTPUT_FILE):
            try:
                old_df = pd.read_csv(OUTPUT_FILE)
                merged_df = pd.concat([old_df, new_df], ignore_index=True)
                merged_df = merged_df.drop_duplicates(
                    subset=["source_url", "case_no"]
                ).reset_index(drop=True)
            except Exception as e:
                print("  读取旧文件失败，改为仅保存当前页：", e)
                merged_df = new_df
        else:
            merged_df = new_df

        merged_df.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
        stats["saved_total"] = len(merged_df)

        print(f"  当前页解析病例数：{len(cases)}")
        print(f"  当前累计保存条数：{len(merged_df)}")

        time.sleep(SLEEP_SECONDS)

    # 保存debug文件
    debug_file = os.path.join(RAW_DIR, "cases_debug_main.csv")
    if debug_rows:
        pd.DataFrame(debug_rows).drop_duplicates().to_csv(
            debug_file, index=False, encoding="utf-8-sig"
        )

    print("\n抓取完成")
    print("保存文件：", OUTPUT_FILE)
    print("保存后文件是否存在：", os.path.exists(OUTPUT_FILE))
    print("当前保存条数：", stats["saved_total"])

    print("\n===== 统计结果 =====")
    print(f"目录页链接数：{stats['catalog_total']}")
    print(f"跳过链接数：{stats['skipped_urls']}")
    print(f"详情页请求失败：{stats['detail_fetch_fail']}")
    print(f"详情页解析为空：{stats['detail_parse_empty']}")
    print(f"病例总数：{stats['cases_total']}")
    print(f"有主诉：{stats['has_chief_complaint']}")
    print(f"有现病史：{stats['has_history']}")
    print(f"有中医诊断：{stats['has_tcm_diag']}")
    print(f"有西医诊断：{stats['has_wm_diag']}")
    print(f"有处方：{stats['has_prescription']}")

    if debug_rows:
        print(f"debug样本已保存：{debug_file}")

if __name__ == "__main__":
    main()