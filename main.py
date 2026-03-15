import requests
import uvicorn
from fastapi import FastAPI, Request, Form
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
import os

app = FastAPI()
templates = Jinja2Templates(directory="templates")

# 信頼性の高いInvidiousインスタンス
INSTANCES = [
    "https://invidious.lunar.icu",
    "https://yewtu.be",
    "https://invidious.projectsegfau.lt",
    "https://inv.vern.cc"
]

def get_video_data(video_id):
    for instance in INSTANCES:
        try:
            api_url = f"{instance}/api/v1/videos/{video_id}"
            res = requests.get(api_url, timeout=5)
            if res.status_code == 200:
                data = res.json()
                # DASHマニフェストURLを取得
                dash_url = data.get("dashMpegUrl")
                if not dash_url:
                    continue
                
                # 相対パスを絶対パスに変換
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
    return None

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    return templates.TemplateResponse("index.html", {"request": request})

@app.post("/player", response_class=HTMLResponse)
async def player(request: Request, video_url: str = Form(...)):
    # IDの抽出 (URLでもID単体でも可)
    video_id = video_url.split("v=")[-1].split("&")[0].split("/")[-1]
    
    data = get_video_data(video_id)
    if not data:
        return HTMLResponse("<h2>エラー: 高画質ストリームが見つかりませんでした。別の動画を試してください。</h2><a href='/'>戻る</a>")

    return templates.TemplateResponse("player.html", {"request": request, "data": data})

if __name__ == "__main__":
    # Render環境のポートに対応
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
