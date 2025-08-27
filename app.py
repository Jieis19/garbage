import os
import math
import requests
from flask import Flask, request, abort

# 使用 v3 SDK 的模块
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage
from linebot.models.events import FollowEvent
app = Flask(__name__)

# 使用环境变量（推荐）
HANNEL_SECRET = "3e312784b5d0a822c5a2971845084a7e"

CHANNEL_ACCESS_TOKEN = "DDS2tqAC4BKlE8EJMFPL+SrTWbzBiYjUsXK9o6NlPX2h0LbG4wYAPGpMavazrKqUmayd5mxe7oJUEK9zMq8JRq2bpOYnUxCslrHJ5d5+iDRo7JX/sRgWmZw0CVy7+J+8zyzpFwmlea3tFPHRIND0EwdB04t89/1O/w1cDnyilFU="

line_bot_api = LineBotApi(CHANNEL_ACCESS_TOKEN)
handler = WebhookHandler(HANNEL_SECRET)

# Haversine 公式计算两点之间的距离（单位：公里）
def haversine(lon1, lat1, lon2, lat2):
    R = 6371  # 地球半径（单位：公里）
    dlon = math.radians(lon2 - lon1)
    dlat = math.radians(lat2 - lat1)
    a = math.sin(dlat / 2) ** 2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    distance = R * c
    return distance

def calculate_time(distance_km, speed_kmh=30):
    return (distance_km / speed_kmh) * 60

def is_near_track(lon, lat, track, threshold=10):
    for path in track:
        for point in path:
            track_lon = float(point["X"])
            track_lat = float(point["Y"])
            if haversine(lon, lat, track_lon, track_lat) < threshold:
                return True
    return False

@app.route("/callback", methods=['POST'])
def callback():
    signature = request.headers.get('X-Line-Signature', '')
    body = request.get_data(as_text=True)
    # print("Request body:", body)  # 日誌，方便除錯
    try:
        handler.handle(body, signature)
    except InvalidSignatureError:
        print("Invalid signature!")
        abort(400)
    return 'OK'
# 收到文字訊息回覆
@handler.add(MessageEvent, message=TextMessage)
def handle_message(event):

    if event.message.text == "垃圾車":
       result = fetch_garbage_truck_info()
       line_bot_api.reply_message(event.reply_token,TextSendMessage(text=f"目前垃圾車: {result}"))
       return
    
# 收到加好友事件回覆
@handler.add(FollowEvent)
def handle_follow(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="謝謝你加我好友！享受到垃圾的樂趣")
    )

def fetch_garbage_truck_info():
    url_location = "https://7966.hccg.gov.tw/WEB/_IMP/API/CleanWeb/getCarLocation"
    url_track = "https://7966.hccg.gov.tw/WEB/_IMP/API/CleanWeb/getRouteTrack"
    payload_location = 'rId=all'
    payload_track = 'rId=112'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    try:
        # 获取车辆信息
        response = requests.post(url_location, headers=headers, data=payload_location, timeout=10,verify=False)
        if response.status_code != 200:
            return "请求失败，HTTP 状态码：" + str(response.status_code)

        data = response.json()
        target_x = "120.95498"
        target_y = "24.8316435"
        find_flag = True

        if data.get("statusCode") == 1 and "data" in data and "car" in data["data"]:
            output = ""
            for car in data["data"]["car"]:
                if car.get("routeName") in ["3-9海濱東大路(次、下午)", "3-5境福中正路(主、晚上)"]:
                    find_flag = False
                    lat1 = float(car['lat'])
                    lon1 = float(car['lon'])
                    lat2 = float(target_y)
                    lon2 = float(target_x)
                    distance = haversine(lon1, lat1, lon2, lat2)
                    time_minutes = calculate_time(distance)
                    output += f"找到符合条件的车辆：{car['carNo']}\n"
                    output += f"路线名称：{car.get('routeName')}\n"
                    output += f"两点之间距离：{distance:.3f} 公里\n"
                    output += f"预计行驶时间（30 km/h）：{time_minutes:.2f} 分钟\n\n"

            if not output:
                output = "没有发现符合条件名称\n正在自动搜索附近车辆...\n"

        else:
            output = "没有发现符合条件名称\n正在自动搜索附近车辆...\n"

        if find_flag:
            # 获取轨迹信息
            track_response = requests.post(url_track, headers=headers, data=payload_track, timeout=10,verify=False)
            track_data = track_response.json()
            car_response = requests.post(url_location, headers=headers, data=payload_location, timeout=10,verify=False)
            car_data = car_response.json()
            tracks = track_data["data"]["track"]
            nearby_cars = []

            for car in car_data["data"]["car"]:
                lon = float(car["lon"])
                lat = float(car["lat"])
                if is_near_track(lon, lat, tracks):
                    nearby_cars.append(car)

            output = "在轨迹附近的车辆信息：\n"
            for car in nearby_cars:
                lat1 = float(car['lat'])
                lon1 = float(car['lon'])
                lat2 = float(target_y)
                lon2 = float(target_x)
                distance = haversine(lon1, lat1, lon2, lat2)
                time_minutes = calculate_time(distance)
                output += f"车辆编号：{car['carNo']}, 位置：({lat1}, {lon1})\n"
                output += f"两点之间距离：{distance:.3f} 公里\n"
                output += f"预计行驶时间（30 km/h）：{time_minutes:.2f} 分钟\n\n"

        return output

    except Exception as e:
        return f"发生错误：{str(e)}"


