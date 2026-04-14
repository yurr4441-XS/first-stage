import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os
# 1、上层文件夹
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
# 2. data/raw 目录
raw_dir = os.path.join(BASE_DIR, "data", "raw")
os.makedirs(raw_dir, exist_ok=True)   # 没有就创建
# 3. 最终输出文件
output_file = os.path.join(raw_dir, "cases_raw.csv")
if os.path.exists(output_file):
    try:
        df_existing = pd.read_csv(output_file)
        if'url' in df_existing.columns:
            done_urls = set(df_existing["url"])
        else:
            done_urls = set()
    except Exception as e:
        print("读取CSV失败，重置：", e)
        df_existing = pd.DataFrame()
        done_urls = set()

else:
    df_existing = pd.DataFrame()
    done_urls = set()

CATALOG_URL = "https://www.ytzyy.cn/houaihua/1596022668925005824-0-18.html"
base_url = "https://www.ytzyy.cn"

headers = {
    "User-Agent": "Mozilla/5.0"
}

def safe_get(url, retries=3):
    for i in range(retries):
        try:
            res = requests.get(url, headers=headers, timeout=10)
            res.raise_for_status()
            return res
        except Exception as e:
            print(f"重试 {i+1}/{retries}：{e}")
            time.sleep(2)
def get_catalog_links():
    case_links = []
    seen = set()

    # offset从0开始，每次+18
    for page in range(0, 200, 18):  # 先跑0~200测试
        page_url = f"{base_url}/houaihua/1596022668925005824-{page}-18.html"

        print(f"\n正在抓目录页：{page_url}")

        res = safe_get(page_url)
        if res.status_code != 200:
            print("页面不存在，停止")
            break

        res.encoding = "utf-8"
        soup = BeautifulSoup(res.text, "html.parser")

        # 找每条医案入口（你之前那套逻辑）
        items = soup.select("div.cbox-3.p_loopitem")
        print("本页条目数：", len(items))

        if not items:
            print("没有数据，停止翻页")
            break

        for item in items:
            p_tag = item.find("p")
            if not p_tag:
                continue

            a_tag = p_tag.find("a")
            if not a_tag:
                continue

            href = a_tag.get("href", "").strip()
            title = p_tag.get_text(strip=True)

            if "/news/" in href and title:
                full_url = base_url + href if href.startswith("/") else href

                if full_url not in seen:
                    seen.add(full_url)
                    case_links.append({
                        "title": title,
                        "url": full_url,
                        "offset": page
                    })

        time.sleep(1)

    print("\n总共抓到：", len(case_links))
    return case_links
def get_case_content(url):
    res = safe_get(url)
    res.raise_for_status()
    res.encoding = "utf-8"

    soup = BeautifulSoup(res.text, "html.parser")

    # 1. 找所有候选块，不拿第一个
    blocks = soup.select("div.cbox-2-0.p_item")
    print("候选块数量：", len(blocks))

    target_block = None
    for i, block in enumerate(blocks, start=1):
        h1_tag = block.select_one("h1")
        rich_div = block.select_one("div.e_richText-7.s_link")

        print(f"第{i}个块：h1={h1_tag.get_text(strip=True) if h1_tag else '无'}，正文容器是否存在={rich_div is not None}")

        # 只要同时有标题和正文容器，就认为是目标块
        if h1_tag and rich_div:
            target_block = block
            break

    if not target_block:
        return {
            "title": "",
            "p_texts": [],
            "raw": ""
        }

    # 2. 提标题
    h1_tag = target_block.select_one("h1")
    title = h1_tag.get_text(strip=True) if h1_tag else ""

    # 3. 提正文容器
    content_div = target_block.select_one("div.e_richText-7.s_link")
    if not content_div:
        return {
            "title": title,
            "p_texts": [],
            "raw": ""
        }

    # 4. 提正文
    p_texts = []
    for p in content_div.find_all("p"):
        text = p.get_text(" ", strip=True)
        if text:
            p_texts.append(text)

    if not p_texts:
        full_text = content_div.get_text("\n", strip=True)
        if full_text:
            p_texts = [full_text]

    raw = "\n".join(p_texts)

    return {
        "title": title,
        "p_texts": p_texts,
        "raw": raw
    }
if __name__ == "__main__":
    links = get_catalog_links()
    print("目录总数：", len(links))

    results = []

    for i, item in enumerate(links[:103], start=1):
        if item["url"] in done_urls:
            print(f"跳过（已完成）：{item['url']}")
            continue
        print(f"正在抓取第{i}条：{item['title']}")

        try:
            case_data = get_case_content(item["url"])

            results={
                "catalog_title": item["title"],
                "url": item["url"],
                "page_title": case_data["title"],
                "raw": case_data["raw"]
            }
            pd.DataFrame([results]).to_csv(
                output_file,
                mode="a",
                header=not os.path.exists(output_file),
                index=False,
                encoding="utf-8-sig"
            )


        except Exception as e:
            print(f"抓取失败：{item['url']} -> {e}")
            results.append({
                "catalog_title": item["title"],
                "url": item["url"],
                "page_title": "",
                "raw": ""
            })

        time.sleep(1)

