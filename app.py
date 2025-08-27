from flask import Flask, jsonify
import requests
import urllib3

# 關閉 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

app = Flask(__name__)

@app.route("/")
def home():
    return "🚛 Garbage Truck Relay API is running!"

@app.route("/garbage")
def garbage():
    url = "https://7966.hccg.gov.tw/WEB/_IMP/API/CleanWeb/getCarLocation"
    payload = "rId=all"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    try:
        res = requests.post(url, headers=headers, data=payload, timeout=10, verify=False)
        return jsonify(res.json())
    except Exception as e:
        return jsonify({"error": str(e)})

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000)