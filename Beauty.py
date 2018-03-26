import re
import sys
import json
import requests
import time
from datetime import datetime
from bs4 import BeautifulSoup

requests.packages.urllib3.disable_warnings()

rs = requests.session()


def getPageNumber(content):
    startIndex = content.find('index')
    endIndex = content.find('.html')
    pageNumber = content[startIndex + 5: endIndex]
    return pageNumber


def over18(board):
    res = rs.get('https://www.ptt.cc/bbs/' + board + '/index.html', verify=False)
    # 先檢查網址是否包含'over18'字串 ,如有則為18禁網站
    if (res.url.find('over18') > -1):
        print("18禁網頁")
        load = {
            'from': '/bbs/' + board + '/index.html',
            'yes': 'yes'
        }
        res = rs.post('https://www.ptt.cc/ask/over18', verify=False, data=load)
        return BeautifulSoup(res.text, 'html.parser')
    return BeautifulSoup(res.text, 'html.parser')


def crawler(url_list):
    count, g_id = 0, 0
    total = len(url_list)
    # 開始爬網頁
    while url_list:
        url = url_list.pop(0)
        res = rs.get(url, verify=False)
        soup = BeautifulSoup(res.text, 'html.parser')
        # 如網頁忙線中,則先將網頁加入 index_list 並休息1秒後再連接
        if (soup.title.text.find('Service Temporarily') > -1):
            url_list.append(url)
            time.sleep(1)
        else:
            count += 1
            for r_ent in soup.find_all(class_="r-ent"):
                # 先得到每篇文章的篇url
                link = r_ent.find('a')
                if (link):
                    # 確定得到url
                    URL = 'https://www.ptt.cc' + link['href']
                    g_id = g_id + 1
                    # 避免被認為攻擊網站
                    time.sleep(0.1)
                    # 開始爬文章內容
                    parseGos(URL, g_id)
            print("進度：" + str(100 * count / total) + "%")
        # 避免被認為攻擊網站
        time.sleep(0.1)


def checkformat(soup, class_tag, data, index, link):
    # 避免有些文章會被使用者自行刪除 標題列 時間  之類......
    try:
        content = soup.select(class_tag)[index].text
    except Exception as e:
        print('此網址資料格式有誤：', link)
        content = "無" + data
    return content


def parseGos(link, g_id):
    res = rs.get(link, verify=False)
    soup = BeautifulSoup(res.text, 'html.parser')

    # author 作者
    author = checkformat(soup, '.article-meta-value', 'author', 0, link)

    # title 標題
    title = checkformat(soup, '.article-meta-value', 'title', 2, link)

    # date 時間
    date = checkformat(soup, '.article-meta-value', 'date', 3, link)

    # ip po文IP
    try:
        targetIP = u'※ 發信站: 批踢踢實業坊'
        ip = soup.find(string=re.compile(targetIP))
        ip = re.search(r"[0-9]*\.[0-9]*\.[0-9]*\.[0-9]*", ip).group()
    except:
        ip = "查無IP!"

    # urls 內文網址
    try:
        urls = soup.find(id='main-content').find_all('a')
        img_urls = []
        for url in urls:
            if re.match(r'^https?://(i.)?(m.)?imgur.com', url['href']):
                img_urls.append(url['href'])
            else:
                img_urls.append('查無圖片!')
    except Exception as e:
        img_urls = 'Error'
        print('此網址的內文有誤：' + link)

    # messageNum 推文總數
    good, bad = 0, 0

    for tag in soup.select('div.push'):
        try:
            # push_tag 推文標籤
            push_tag = tag.find("span", {'class': 'push-tag'}).text

            # 計算推噓文數量
            if push_tag == u'推 ':
                good += 1
            elif push_tag == u'噓 ':
                bad += 1
        except Exception as e:
            print("此網址存在的推文有誤：" + link)

    messageNum = {"推": good, "噓": bad}

    post = {
        "作者": author,
        "標題": title,
        "時間": date,
        "po文IP": ip,
        "第一張圖片網址": img_urls[0],
        "推文總數": messageNum
    }

    # json.dumps 序列化時預設為對中文使用 ascii 編碼
    json_data = json.dumps(post, ensure_ascii=False, indent=4, sort_keys=True) + ','
    store(json_data)


def store(data):
    with open(fileName, 'a') as f:
        f.write(data.encode(sys.stdin.encoding, "replace").decode(sys.stdin.encoding))


if __name__ == "__main__":
    PttName, ParsingPage = 'Beauty', 1
    start_time = time.time()
    print('開始爬' + PttName)
    fileName = PttName + '-' + datetime.now().strftime('%Y%m%d') + '.json'
    # 檢查看板是否為 18 禁
    soup = over18(PttName)
    ALLpageURL = soup.select('.btn.wide')[1]['href']
    # 得到本看板全部的index數量
    ALLpage = int(getPageNumber(ALLpageURL)) + 1
    index_list = []
    for index in range(ALLpage, ALLpage - int(ParsingPage), -1):
        page_url = 'https://www.ptt.cc/bbs/' + PttName + '/index' + str(index) + '.html'
        index_list.append(page_url)

    store('[\n')
    crawler(index_list)

    # 移除最後一個  "," 號
    with open(fileName, 'r') as f:
        content = f.read()
    with open(fileName, 'w') as f:
        f.write(content[:-1] + "\n]")

    print("爬蟲結束")
    print("執行時間：" + str(time.time() - start_time) + "秒")
