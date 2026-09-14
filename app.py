import os
import yt_dlp
from flask import Flask, request, jsonify

app = Flask(__name__)

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "message": "Fast yt-dlp API active",
        "usage": "/download?url=YOUR_MEDIA_URL"
    })

@app.route('/download', methods=['GET'])
def get_video_info():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    cookie_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')

    # Ultra-fast configuration options
    ydl_opts = {
        'quiet': True,
        'no_warnings': True,
        'format': 'best[ext=mp4]/best', # Fetch single best stream without merging
        'skip_download': True,
        'socket_timeout': 5, # Max 5-second socket connection wait
        'concurrent_fragment_downloads': 5,
        
        # Bypass YouTube bot checks directly via Mobile API clients (No slow proxies needed)
        'extractor_args': {
            'youtube': {
                'player_client': ['ios', 'android', 'mweb'],
                'skip': ['dash', 'hls'] # Skip parsing complex streams to speed up response
            }
        },
        'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 17_0 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.0 Mobile/15E148 Safari/604.1',
    }

    # Use cookies if available for extra speed & stability
    if os.path.exists(cookie_path):
        ydl_opts['cookiefile'] = cookie_path

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            # extract_info with process=True but minimal extraction format
            info = ydl.extract_info(url, download=False)
            
            return jsonify({
                "status": "success",
                "title": info.get('title'),
                "thumbnail": info.get('thumbnail'),
                "duration": info.get('duration'),
                "download_url": info.get('url'),
                "uploader": info.get('uploader'),
                "ext": info.get('ext', 'mp4')
            })

    except Exception as e:
        return jsonify({
            "status": "error",
            "message": str(e)
        }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
