🚛 Garbage Truck Relay API
這是一個中繼伺服器 (Relay)，用來繞過 PythonAnywhere 免費方案的外部網路限制。
它會呼叫新竹市環保局的垃圾車 API，然後把結果回傳。
部署方式
1. Fork 專案
把這個 repo fork 到你的 GitHub。
2. 部署到 Render (推薦)
1. 到 https://render.com 註冊帳號
2. 建立 New Web Service
3. 連結到這個 GitHub repo
4. 設定： 
Environment: Python 3
Build Command: pip install -r requirements.txt
Start Command: gunicorn app:app
