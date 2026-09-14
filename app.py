import os
import asyncio
from fastapi import FastAPI, HTTPException, Query
import yt_dlp

app = FastAPI(title="Fast YT-DLP API")

@app.get("/")
async def root():
    return {"status": "online", "message": "API is running fast & smooth!"}

async def extract_yt_info(url: str):
    loop = asyncio.get_event_loop()
    
    def _extract():
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best[ext=mp4]/best',
            'skip_download': True,
            'socket_timeout': 10,
            # Pass bot protection through embedded TV/Android client spoofing
            'extractor_args': {
                'youtube': {
                    'player_client': ['tv_embedded', 'android', 'ios'],
                    'skip': ['dash', 'hls']
                }
            },
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15',
        }
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            return ydl.extract_info(url, download=False)

    return await loop.run_in_executor(None, _extract)

@app.get("/download")
async def download(url: str = Query(..., description="YouTube Video URL")):
    try:
        info = await extract_yt_info(url)
        return {
            "status": "success",
            "title": info.get("title"),
            "thumbnail": info.get("thumbnail"),
            "duration": info.get("duration"),
            "download_url": info.get("url"),
            "uploader": info.get("uploader"),
            "ext": info.get("ext", "mp4")
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    uvicorn.run(app, host="0.0.0.0", port=port)
