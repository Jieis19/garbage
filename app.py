import os,math,io
import base64
import requests
from flask import Flask, request, abort,send_file
import matplotlib.pyplot as plt
# 使用 v3 SDK 的模块
from linebot import LineBotApi, WebhookHandler
from linebot.exceptions import InvalidSignatureError
from linebot.models import MessageEvent, TextMessage, TextSendMessage, ImageSendMessage
from linebot.models.events import FollowEvent
app = Flask(__name__)

# 使用环境变量（推荐）
HANNEL_SECRET = "37386e7c6e3281ab80eb0ba61f3a00a3"

CHANNEL_ACCESS_TOKEN = "wvyDe3P/k8r8Cu4nvfGdPdhoJkPrvsRXeqbVqksAz4DZrOkU706pQeQseLptAg9ulWF2aVLWezArTAJTu88FrSc825WtVct/x7pOGZUHjo/goY+nyENdcAv+X+/LuL0rLPCc9InUp7QPHUfNXKdlUgdB04t89/1O/w1cDnyilFU="

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

def is_near_track(lon, lat, track, threshold=3):
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
        line_bot_api.reply_message(
            event.reply_token,
            TextSendMessage(text="🔍 正在查詢垃圾車位置，請稍候...")
        )
        user_id = event.source.user_id        
        # 再去抓資料
        result = fetch_garbage_truck_info(user_id)
        
        # 把結果「推播」給使用者
        line_bot_api.push_message(
            event.source.user_id,
            TextSendMessage(text=f"目前垃圾車資訊：\n{result}")
        )

        image_url = "https://garbage-xcnc.onrender.com/plot"
        message = ImageSendMessage(
            original_content_url=image_url,
            preview_image_url=image_url
        )
        line_bot_api.push_message(user_id, message)
    
    
# 收到加好友事件回覆
@handler.add(FollowEvent)
def handle_follow(event):
    line_bot_api.reply_message(
        event.reply_token,
        TextSendMessage(text="謝謝你加我好友！享受到垃圾的樂趣\n輸入垃圾車獲取時間")
    )
def generate_plot_image(lat2, lon2):
    lat1, lon1, label1 = 24.819735, 120.954769, "chayi"
    label2 = "car"
    lat3, lon3, label3 = 24.819032, 120.954563, 'park'

    distance = haversine(lon1, lat1, lon2, lat2)

    buf = io.BytesIO()
    plt.figure(figsize=(6,6))
    plt.scatter([lon1, lon2, lon3], [lat1, lat2, lat3], color="red")
    plt.plot([lon1, lon2, lon3], [lat1, lat2, lat3], "b--")
    plt.text(lon1, lat1, f" {label1}", color="red")
    plt.text(lon2, lat2, f" {label2}", color="red")
    plt.text(lon3, lat3, f" {label3}", color="red")
    plt.text((lon1+lon2)/2, (lat1+lat2)/2, f"{distance:.2f} km", color="blue", ha="center")
    plt.savefig(buf, format="png")
    plt.close()
    buf.seek(0)
    return buf
@app.route("/plot")
def send_plot():
    lat2 = float(request.args.get("lat2", 22.627))  # 預設高雄
    lon2 = float(request.args.get("lon2", 120.301))
    buf = generate_plot_image(lat2, lon2)
    return send_file(buf, mimetype="image/png")    
def fetch_garbage_truck_info(user_id=None):
    url_location = "https://7966.hccg.gov.tw/WEB/_IMP/API/CleanWeb/getCarLocation"
    url_track = "https://7966.hccg.gov.tw/WEB/_IMP/API/CleanWeb/getRouteTrack"
    payload_location = 'rId=all'
    payload_track = 'rId=112'
    headers = {'Content-Type': 'application/x-www-form-urlencoded'}

    try:
        # 获取车辆信息
        response = requests.post(url_location, headers=headers, data=payload_location, timeout=10,verify=False)
        if response.status_code != 200:
            return "請求失敗，HTTP 狀態碼：" + str(response.status_code)

        data = response.json()
        target_x = "120.954769"
        target_y = "24.819735"
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
                    send_plot(lat1,lon1)
                    distance = haversine(lon1, lat1, lon2, lat2)
                    time_minutes = calculate_time(distance)
                    output += f"找到符合條件的車輛：{car['carNo']}\n"
                    output += f"路線名稱：{car.get('routeName')}\n"
                    output += f"兩點之間距離：{distance:.3f} 公里\n"
                    output += f"預計行駛時間（30 km/h）：{time_minutes:.2f} 分鐘\n\n"
                    # 推播圖片給 Line
                    if user_id:
                        buf = generate_plot_image(lat1, lon1)
                        img_b64 = base64.b64encode(buf.getvalue()).decode()
                        image_message = ImageSendMessage(
                            original_content_url=f"data:image/png;base64,{img_b64}",
                            preview_image_url=f"data:image/png;base64,{img_b64}"
                        )
                        line_bot_api.push_message(user_id, image_message)
            if not output:
                output = "沒有發現符合條件名稱\n正在自動搜尋附近車輛...\n"

        else:
            output = "沒有發現符合條件名稱\n正在自動搜尋附近車輛...\n"

        if find_flag:
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

            output = "在軌跡附近的車輛訊息：\n"
            for car in nearby_cars:
                lat1 = float(car['lat'])
                lon1 = float(car['lon'])
                lat2 = float(target_y)
                lon2 = float(target_x)
                distance = haversine(lon1, lat1, lon2, lat2)
                # 推播圖片給 Line
                if user_id:
                    buf = generate_plot_image(lat1, lon1)
                    img_b64 = base64.b64encode(buf.getvalue()).decode()
                    image_message = ImageSendMessage(
                        original_content_url=f"data:image/png;base64,{img_b64}",
                        preview_image_url=f"data:image/png;base64,{img_b64}"
                    )
                    line_bot_api.push_message(user_id, image_message)
                time_minutes = calculate_time(distance)
                output += f"車輛編號：{car['carNo']}\n"
                output += f"兩點之間距離：{distance:.3f} 公里\n"
                output += f"預計行駛時間（30 km/h）：{time_minutes:.2f} 分鐘\n\n"

        return output

    except Exception as e:
        return f"發生錯誤：{str(e)}"


