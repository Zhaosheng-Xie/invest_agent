"""临时测试脚本：验证巨潮 API 不同参数格式。"""
import requests
import time

url = "http://www.cninfo.com.cn/new/hisAnnouncement/query"
headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}


def test_query(desc, **extra):
    payload = {
        "pageNum": 1, "pageSize": 5, "column": "", "tabName": "fulltext",
        "stock": "", "searchkey": "", "category": "", "seDate": "",
        "sortName": "", "sortType": "", "isHLtitle": "true",
    }
    payload.update(extra)
    resp = requests.post(url, data=payload, headers=headers, timeout=15)
    r = resp.json()
    total = r.get("totalAnnouncement", 0)
    anns = r.get("announcements") or []
    print(f"{desc}: total={total}, got={len(anns)}")
    if anns:
        print(f"  First: {anns[0].get('announcementTitle', '')[:60]}")
    time.sleep(1)


# 1. stock=002428 (当前做法) - 失败
test_query("stock=002428", stock="002428")

# 2. column=szse + stock=002428
test_query("column=szse, stock=002428", column="szse", stock="002428")

# 3. searchkey=002428
test_query("searchkey=002428", searchkey="002428")

# 4. searchkey=云南锗业
test_query("searchkey=yunnan_ge", searchkey="云南锗业")

# 5. stock=002428 with seDate
test_query("stock=002428 + seDate", stock="002428", seDate="2026-03-01~2026-04-30")

# 6. 尝试把 tabName 改为 fulltext 并 column=szse
test_query("tabName=fulltext, column=szse, stock=002428", 
           tabName="fulltext", column="szse", stock="002428")
