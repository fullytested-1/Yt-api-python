import os
import random
import socket
import requests
import yt_dlp
from flask import Flask, request, jsonify

# Set global timeout for socket connections so slow proxies don't freeze Gunicorn
socket.setdefaulttimeout(5)

app = Flask(__name__)

PROXY_API_URL = "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=json"
PROXY_POOL = []

def fetch_proxies():
    """Fetches proxy list from ProxyScrape."""
    global PROXY_POOL
    try:
        response = requests.get(PROXY_API_URL, timeout=5)
        if response.status_code == 200:
            data = response.json()
            proxies_data = data.get("proxies", [])
            valid_proxies = []
            for item in proxies_data:
                protocol = item.get("protocol", "http")
                ip = item.get("ip")
                port = item.get("port")
                if ip and port and protocol in ["http", "https"]:
                    valid_proxies.append(f"{protocol}://{ip}:{port}")
            
            PROXY_POOL = valid_proxies[:30]
            print(f"[+] Loaded {len(PROXY_POOL)} proxies.")
    except Exception as e:
        print(f"[-] Proxy fetch failed: {e}")

fetch_proxies()

def get_proxy():
    return random.choice(PROXY_POOL) if PROXY_POOL else None

@app.route('/', methods=['GET'])
def home():
    return jsonify({"status": "online", "proxies_loaded": len(PROXY_POOL)})

@app.route('/download', methods=['GET'])
def get_video_info():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    cookie_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')

    # Try with up to 3 proxies before falling back
    max_retries = 3
    last_error = ""

    for attempt in range(max_retries):
        selected_proxy = get_proxy()

        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best',
            'socket_timeout': 5,  # Prevents hanging on slow connections
            # Bypass YouTube bot detection by posing as iOS client
            'extractor_args': {
                'youtube': {
                    'player_client': ['ios', 'android']
                }
            },
            'user_agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 16_6 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Mobile/15E148 Safari/604.1',
        }

        if selected_proxy:
            ydl_opts['proxy'] = selected_proxy

        if os.path.exists(cookie_path):
            ydl_opts['cookiefile'] = cookie_path

        try:
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(url, download=False)
                return jsonify({
                    "status": "success",
                    "proxy_used": selected_proxy or "Direct IP",
                    "title": info.get('title'),
                    "thumbnail": info.get('thumbnail'),
                    "duration": info.get('duration'),
                    "download_url": info.get('url'),
                    "uploader": info.get('uploader'),
                    "ext": info.get('ext')
                })
        except Exception as e:
            last_error = str(e)
            print(f"[!] Proxy {selected_proxy} failed: {last_error}")

    return jsonify({
        "status": "error",
        "message": f"All retries failed. Last error: {last_error}"
    }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
