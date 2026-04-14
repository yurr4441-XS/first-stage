import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
import csv
import time
import re
CATALOG_URL = "https://www.ytzyy.cn/news/114/"
base_url = "https://www.ytzyy.cn"

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
    soup = BeautifulSoup(res.text, "html.parser")

    case_links = []
    seen = set()

    for a1 in soup.find_all("div",class_="cbox-3 p_loopitem"):
        a2=a1.find("p")
        a=a2.find("a")
        href = a.get("href", "")
        target = a.get("target", "")
        title = a2.get_text(strip=True)

        if "/news/" in href and target == "_self" and title:
            full_url = base_url + href
            if full_url not in seen:
                seen.add(full_url)
                case_links.append({
                    "title": title,
                    "url": full_url
                })
        else:
            case_links.append({
                "title": title,
                "url": full_url
            })
            continue
        continue


    # html = res.text
    #
    # # 正则抓 d.add(1,0,'booktitle','url')
    # pattern = r"d\.add\(\d+,\d+,'(.*?)','(.*?)'"
    #
    # matches = re.findall(pattern, html)
    # case_links = []
    #
    # base = "https://www.zlnow.com/book/"

    # for title, href in matches[:10]:
    #     full_url = base + href
    #     print(title, "=>", full_url)
    #     case_links.append({"title": title,
    #                 "url": full_url})

    return case_links


def get_case_content(url):
    res = requests.get(url, headers=headers, timeout=10)
    res.encoding = "utf-8"
    soup = BeautifulSoup(res.text, "html.parser")
    b=soup.find("div",class_="cbox-2-0 p_item")
    title = b.find('h1').get_text(strip=True)if b.find('h1') else ''
    content_div=b.find("div", class_="richText-7 s_link response-transition")
    if not content_div:
        return {"title": title, "paragraphs": []}
    p_texts=[]
    # 进内容目录抓p
    for td in content_div.find_all("p"):
        content = td.get_text(strip=True)
        if content:
            p_texts.append(content)
    if not p_texts:
        full_text = content_div.get_text("\n", strip=True)
        if full_text:
            p_texts = [full_text]

    return {
      'p_texts': p_texts,
    'title': title
    }
import re

def parse_case_fields(case_data):
    title = case_data.get("title", "")
    paragraphs = case_data.get("paragraphs", [])
    full_text = "\n".join(paragraphs)

    patient_info = ""
    visit_date = ""
    chief_complaint = ""
    present_illness = ""



    # 2. 全文兜底
    if not patient_info:
        m = re.search(r'(患者.*?(?:男|女).*?\d+岁)', full_text)
        if m:
            patient_info = m.group(1)

    if not visit_date:
        m = re.search(r'(\d{4}年\d{1,2}月\d{1,2}日.*?(?:初诊|复诊))', full_text)
        if m:
            visit_date = m.group(1)

    if not chief_complaint:
        m = re.search(r'主诉[:：](.*?)(?=现病史|辨证|诊断|处方|$)', full_text, re.S)
        if m:
            chief_complaint = m.group(1).strip()

    if not present_illness:
        m = re.search(r'现病史[:：](.*?)(?=辨证|诊断|处方|按语|$)', full_text, re.S)
        if m:
            present_illness = m.group(1).strip()

    return {
        "title": title,
        "patient_info": patient_info,
        "visit_date": visit_date,
        "chief_complaint": chief_complaint,
        "present_illness": present_illness,
        "full_text": full_text
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
            "content": case_data["p_texts"],
        })

        time.sleep(1)

    with open("cases_test.csv", "w", newline="", encoding="utf-8-sig") as f:
        writer = csv.DictWriter(f, fieldnames=["catalog_title", "url", "page_title", "content",'lenth','ismatch'])
        writer.writeheader()
        writer.writerows(results)


    print("试爬完成，结果已保存到 cases_test.csv")