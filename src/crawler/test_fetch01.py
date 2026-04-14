import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import csv
import time
import re
CATALOG_URL = "https://www.zlnow.com/book/yuedu_one.php?id=376&name=%D2%B2%CA%C7%C9%BD%C8%CB%D2%BD%B0%B8"

headers = {
    "User-Agent": "Mozilla/5.0"
}

def get_catalog_links():
    res = requests.get(CATALOG_URL, headers=headers, timeout=10)
    res.encoding = "utf-8"
    # print("状态码：", res.status_code)
    # print("最终URL：", res.url)
    # print("响应长度：", len(res.text))
    # print("前500个字符：")
    # print(res.text[:500])
    # with open("catalog_debug.html", "w", encoding="utf-8", errors="ignore") as f:
    #     f.write(res.text)
    #
    # print("源码已保存到 catalog_debug.html")
    '''下面是HTML的解析方式'''
    # soup = BeautifulSoup(res.text, "html.parser")
    #
    # case_links = []
    # seen = set()
    #
    # for a in soup.find_all("a"):
    #     href = a.get("href", "")
    #     target = a.get("target", "")
    #     title = a.get_text(strip=True)
    #
    #     if "book_show.php" in href and target == "main_show_frame" and title:
    #         full_url = urljoin(CATALOG_URL, href)
    #         if full_url not in seen:
    #             seen.add(full_url)
    #             case_links.append({
    #                 "title": title,
    #                 "url": full_url
    #             })


    html = res.text

    # 正则抓 d.add(1,0,'booktitle','url')
    pattern = r"d\.add\(\d+,\d+,'(.*?)','(.*?)'"

    matches = re.findall(pattern, html)
    case_links = []

    base = "https://www.zlnow.com/book/"

    for title, href in matches[:10]:
        full_url = base + href
        print(title, "=>", full_url)
        case_links.append({"title": title,
                    "url": full_url})

    return case_links


def get_case_content(url):
    res = requests.get(url, headers=headers, timeout=10)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")

    title = ""
    content = ""

    for td in soup.find_all("td"):
        style = td.get("style", "")
        text = td.get_text(" ", strip=True)

        if "font-size:20px" in style and text:
            title = text

        if "font-size:16px" in style and len(text) > 10:
            content = text
        lenth=len(content)
        a=bool(content.strip())

    return {
        "title": title,
        "content": content,
        'lenth': lenth,
        'ismatch':a
    }


if __name__ == "__main__":
    links = get_catalog_links()
    print("目录总数：", len(links))

    results = []

    # 先试爬前5条
    for i, item in enumerate(links[:5], start=1):
        print(f"正在抓取第{i}条：{item['title']}")

        case_data = get_case_content(item["url"])
        results.append({
            "catalog_title": item["title"],
            "url": item["url"],
            "page_title": case_data["title"],
            "content": case_data["content"],
            'lenth': case_data["lenth"],
            'ismatch': case_data["ismatch"]
        })

        time.sleep(1)

    with open("cases_test.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["catalog_title", "url", "page_title", "content",'lenth','ismatch'])
        writer.writeheader()
        writer.writerows(results)

    print("试爬完成，结果已保存到 cases_test.csv")