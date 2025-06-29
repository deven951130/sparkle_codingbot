from keep_alive import keep_alive  
import os
import discord
from discord.ext import tasks, commands
from googleapiclient.discovery import build
from google.oauth2 import service_account
from datetime import datetime
from dotenv import load_dotenv
from io import BytesIO
from googleapiclient.http import MediaIoBaseDownload
from flask import Flask
from threading import Thread

# ====== 啟動 keep_alive Server ======
app = Flask('')

@app.route('/')
def home():
    return "Bot is alive!"

def run():
    app.run(host='0.0.0.0', port=8080)

def keep_alive():
    t = Thread(target=run)
    t.start()

# ====== 載入 .env 變數 =======
load_dotenv()
DISCORD_TOKEN="MTM4ODQ1NDk2MTUxNTQ2MjY2Ng.GvpHSA.YRRlIxjggn3mLCTvrRTSfjuTFuEP3bY6EiTSxA"
CHANNEL_ID = int(os.getenv('CHANNEL_ID'))
USER_ID = int(os.getenv('USER_ID'))
DRIVE_FOLDER_ID = os.getenv('DRIVE_FOLDER_ID')
SERVICE_ACCOUNT_FILE = 'credentials.json'

# ====== 初始化 Discord Bot =======
intents = discord.Intents.default()
intents.message_content = True
intents.members = True
bot = commands.Bot(command_prefix="!", intents=intents)

# ====== Google Drive 題目讀取邏輯 =======
def get_today_question():
    try:
        creds = service_account.Credentials.from_service_account_file(
            SERVICE_ACCOUNT_FILE, scopes=['https://www.googleapis.com/auth/drive.readonly'])
        service = build('drive', 'v3', credentials=creds)

        today_str = datetime.now().strftime('%Y-%m-%d')

        results = service.files().list(
            q=f"'{DRIVE_FOLDER_ID}' in parents and name contains '{today_str}'",
            pageSize=1, fields="files(id, name)").execute()
        files = results.get('files', [])

        if not files:
            return f"今天 ({today_str}) 沒有找到題目喔～是你忘記放還是我放錯資料夾？"

        file_id = files[0]['id']
        request = service.files().get_media(fileId=file_id)
        fh = BytesIO()
        downloader = MediaIoBaseDownload(fh, request)
        done = False
        while not done:
            status, done = downloader.next_chunk()

        fh.seek(0)
        content = fh.read().decode('utf-8', errors='replace')  # 防止編碼錯誤炸掉
        return content
    except Exception as e:
        return f"取得題目時出錯啦～錯誤訊息：{e}"

# ====== 當 Bot 啟動時 =======
@bot.event
async def on_ready():
    await bot.wait_until_ready()
    print(f'{bot.user} 已啟動')
    send_question.start()

# ====== 每分鐘檢查一次時間，早上 9:00 發送題目 =======
already_sent_today = False

@tasks.loop(minutes=1)
async def send_question():
    global already_sent_today
    now = datetime.now()

    if now.hour == 9 and now.minute == 0:
        if not already_sent_today:
            channel = bot.get_channel(CHANNEL_ID)
            user_mention = f'<@{USER_ID}>'
            question = get_today_question()
            msg = f"{user_mention} 起床啦！今天的題目來了：\n```{question}```"
            await channel.send(msg)
            already_sent_today = True
    else:
        already_sent_today = False  # 新的一天可以重發

# ====== 測試用指令 =======
@bot.command()
async def 測試題目(ctx):
    question = get_today_question()
    await ctx.send(f"測試：```{question}```")

# ====== 開始表演！ =======
keep_alive()
bot.run(DISCORD_TOKEN)
