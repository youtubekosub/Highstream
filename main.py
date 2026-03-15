import requests
import uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# インスタンスリストを増やし、信頼性の高いものを優先
INSTANCES = [
    "https://invidious.lunar.icu",
    "https://yewtu.be",
    "https://invidious.projectsegfau.lt",
    "https://inv.tux.pizza",
    "https://invidious.asir.dev",
    "https://iv.ggtyler.dev"
]

def get_video_data(video_id):
    # 1. Invidious インスタンスを順番に試行
    for instance in INSTANCES:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            res = requests.get(api_url, timeout=3)
            
            if res.status_code == 200:
                data = res.json()
                
                # DASH URLを探す
                dash_url = data.get("dashMpegUrl")
                
                # DASHがない場合、adaptiveFormatsから探す
                if not dash_url and "adaptiveFormats" in data:
                    video_streams = [f for f in data["adaptiveFormats"] if "video" in f.get("type", "")]
                    if video_streams:
                        dash_url = video_streams[0].get("url")

                if not dash_url:
                    continue
                
                if dash_url.startswith("/"):
                    dash_url = instance + dash_url
                
                return {
                    "title": data.get("title"),
                    "dash_url": dash_url,
                    "author": data.get("author"),
                    "description": data.get("descriptionHtml", ""),
                    "instance": instance
                }
        except:
            continue

    # 2. すべてのインスタンスが失敗した場合の最終手段 (yudlp へのフォールバック)
    try:
        # yudlpなどの外部APIは直接ストリームURLを返すため、簡易的な情報を構成
        # 注: yudlpが直接動画ファイルを返す仕様を想定しています
        fallback_url = f"https://yudlp.vercel.app/stream/{video_id}"
        
        # 簡易チェック（リンクが生きているか）
        check = requests.head(fallback_url, timeout=3)
        if check.status_code < 400:
            return {
                "title": f"Video {video_id} (Fallback Mode)",
                "dash_url": fallback_url,
                "author": "System Fallback",
                "description": "Invidious APIが制限されているため、代替サーバーから配信しています。",
                "instance": "https://yudlp.vercel.app"
            }
    except:
        pass

    return None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/player", response_class=HTMLResponse)
async def player(request: Request, video_url: str = Form(...)):
    video_id = video_url
    if "v=" in video_url:
        video_id = video_url.split("v=")[1].split("&")[0]
    elif "youtu.be/" in video_url:
        video_id = video_url.split("/")[-1].split("?")[0]
    
    data = get_video_data(video_id)
    
    if not data:
        return HTMLResponse("""
            <div style="background:#121212; color:white; padding:50px; font-family:sans-serif; text-align:center; height:100vh;">
                <h2>現在、すべてのサーバーおよびバックアップAPIでストリームが制限されています。</h2>
                <p>YouTube側の規制が厳しくなっています。数分待ってから再試行してください。</p>
                <a href="/" style="color:#ff0000; text-decoration:none; font-weight:bold;">[ トップへ戻る ]</a>
            </div>
        """)

    return templates.TemplateResponse("player.html", {"request": request, "data": data})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
