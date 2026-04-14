import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import os

output_file = "cases_test1.csv"

if os.path.exists(output_file):
    df_existing = pd.read_csv(output_file)
    done_urls = set(df_existing["url"])
else:
    df_existing = pd.DataFrame()
    done_urls = set()

CATALOG_URL = "https://www.ytzyy.cn/houaihua/1596022668925005824-0-18.html"
base_url = "https://www.ytzyy.cn"

headers = {
    "User-Agent": "Mozilla/5.0"
}


def get_catalog_links():
    case_links = []
    seen = set()

    # offset从0开始，每次+18
    for page in range(0, 200, 18):  # 先跑0~200测试
        page_url = f"{base_url}/houaihua/1596022668925005824-{page}-18.html"

        print(f"\n正在抓目录页：{page_url}")

        res = requests.get(page_url, headers=headers, timeout=10)
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

'''
def get_case_content(url):
    print("\n" + "=" * 60)
    print("正在抓详情页：", url)

    res = requests.get(url, headers=headers, timeout=10)
    print("状态码：", res.status_code)
    print("最终URL：", res.url)

    res.raise_for_status()
    res.encoding = "utf-8"

    # 先保存源码，别猜
    with open("detail_debug.html", "w", encoding="utf-8", errors="ignore") as f:
        f.write(res.text)

    print("详情页源码长度：", len(res.text))
    print("源码前500字符：")
    print(res.text[:500])

    soup = BeautifulSoup(res.text, "html.parser")

    # 先试最宽松的 h1
    h1_tag = soup.find("h1")
    print("全页 h1 是否找到：", h1_tag is not None)
    if h1_tag:
        print("h1文本：", h1_tag.get_text(strip=True))

    # 再试总块
    b = soup.select_one("div.cbox-2-0.p_item")
    print("总块 b 是否找到：", b is not None)

    if not b:
        return {
            "title": "",
            "p_texts": [],
            "raw": ""
        }

    h1_tag = b.select_one("h1")
    title = h1_tag.get_text(strip=True) if h1_tag else ""
    print("块内标题：", title)

    # 先宽松找 richText，不要一开始写太死
    content_div = b.find("div", class_=lambda x: x and "richText" in " ".join(x) if isinstance(x, list) else x and "richText" in x)
    print("content_div 是否找到：", content_div is not None)

    if not content_div:
        # 再打印块内前500字，看看里面到底长啥样
        print("块内文本前500字：")
        print(b.get_text("\n", strip=True)[:500])

        return {
            "title": title,
            "p_texts": [],
            "raw": ""
        }

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

    print("段落数：", len(p_texts))
    print("raw前200字：", raw[:200])

    return {
        "title": title,
        "p_texts": p_texts,
        "raw": raw
    }
    '''
def get_case_content(url):
    res = requests.get(url, headers=headers, timeout=10)
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

    # 先试爬前5条
    for i, item in enumerate(links[:33], start=1):
        if item["url"] in done_urls:
            print(f"跳过（已完成）：{item['url']}")
            continue

        print(f"正在抓取第{i}条：{item['title']}")

        try:
            case_data = get_case_content(item["url"])

            results.append({
                "catalog_title": item["title"],
                "url": item["url"],
                "page_title": case_data["title"],
                "raw": case_data["raw"]
            })

        except Exception as e:
            print(f"抓取失败：{item['url']} -> {e}")
            results.append({
                "catalog_title": item["title"],
                "url": item["url"],
                "page_title": "",
                "raw": ""
            })

        time.sleep(1)

    df = pd.DataFrame(results)

    print(df.head())
    print("数据形状：", df.shape)

    df.to_csv("cases_test1.csv", index=False, encoding="utf-8-sig")

    print("试爬完成，结果已保存到 cases_test1.csv")