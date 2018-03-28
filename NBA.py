import re
import string
import sys
import json
import requests
import time
import threading
from datetime import datetime

requests.packages.urllib3.disable_warnings()

rs = requests.session()

player_list = []

for word in list(string.ascii_uppercase):
    page_url = 'http://tw.global.nba.com/stats2/league/playerlist.json?lastName=' + word + '&locale=zh_TW'
    player_list.append(page_url)

def crawler(url_list):
    count, p_id = 0, 0
    total = len(url_list)
    # 開始爬網頁
    while url_list:
        url = url_list.pop(0)
        res = rs.get(url, verify=False)
        players = json.loads(res.text)['payload']['players']
        count += 1
        for player in players:
            # 先得到每位球員的 url
            link = player['playerProfile']['code']
            if (link):
                URL = 'http://tw.global.nba.com/stats2/player/stats.json?ds=career&locale=zh_TW&playerCode=' + link
                p_id = p_id + 1
                # 避免被認為攻擊網站
                time.sleep(0.1)
                # 開始爬數據內容
                parseGos(URL, p_id)
        print("進度：" + str(100 * count / total) + "%")
        # 避免被認為攻擊網站
        time.sleep(0.1)

def parseGos(link, p_id):
    res = rs.get(link, verify=False)
    name = json.loads(res.text)['payload']['player']['playerProfile']['displayName']
    teams = json.loads(res.text)['payload']['player']['stats']['regularSeasonStat']['playerTeams']
    # recent_team 球員最近的隊伍
    try:
        recent_team = teams[0]['profile']['code']
    except:
        print(teams[-1]['profile'])

    # points 得分
    points = []

    # rebs 籃板
    rebs = []

    # assists 助攻
    assists = []

    # fgpcts 投籃命中率
    fgpcts = []

    for index, team in enumerate(teams):
        if team['profile'] is not None:
            current_team = team['profile']['code']
        else:
            current_team = teams[index - 1]['profile']['code']

        if current_team == recent_team:
            points.append(team['statAverage']['pointsPg'])
            rebs.append(team['statAverage']['rebsPg'])
            assists.append(team['statAverage']['assistsPg'])
            fgpcts.append(team['statAverage']['fgpct'])
        else:
            break
    
    data = {
        "球員": name,
        "球隊": recent_team,
        "平均得分": round(sum(points) / len(points), 2),
        "平均籃板": round(sum(rebs) / len(rebs), 2),
        "平均助攻": round(sum(assists) / len(assists), 2),
        "投籃%": round(sum(fgpcts) / len(fgpcts), 2)
    }

    json_data = json.dumps(data, ensure_ascii=False, indent=4, sort_keys=True) + ','
    store(json_data)


def store(data):
    with open(fileName, 'a') as f:
        f.write(data.encode(sys.stdin.encoding, "replace").decode(sys.stdin.encoding))


if __name__ == "__main__":
    start_time = time.time()
    threads = []
    threadNum = 4
    print('開始爬NBA球員生涯數據')
    fileName = 'NBA.json'

    for i in range(0, threadNum):
        t = threading.Thread(target=crawler, args=(player_list,))
        threads.append(t)
    for t in threads:
        t.start()
    for t in threads:
        t.join()

    # 移除最後一個  "," 號
    with open(fileName, 'r') as f:
        content = f.read()
    with open(fileName, 'w') as f:
        f.write(content[:-1] + "\n]")

    print("爬蟲結束")
    print("執行時間：" + str(time.time() - start_time) + "秒")
