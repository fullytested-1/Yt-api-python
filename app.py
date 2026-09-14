import os
import random
import requests
import yt_dlp
from flask import Flask, request, jsonify

app = Flask(__name__)

# ProxyScrape API Endpoint
PROXY_API_URL = "https://api.proxyscrape.com/v4/free-proxy-list/get?request=display_proxies&proxy_format=protocolipport&format=json"

PROXY_POOL = []

def fetch_and_rank_proxies():
    """Fetches proxy list from ProxyScrape and selects working HTTP/HTTPS proxies."""
    global PROXY_POOL
    print("[*] Fetching proxies from ProxyScrape API...")
    try:
        response = requests.get(PROXY_API_URL, timeout=10)
        if response.status_code == 200:
            data = response.json()
            proxies_data = data.get("proxies", [])
            
            valid_proxies = []
            for item in proxies_data:
                protocol = item.get("protocol", "http")
                ip = item.get("ip")
                port = item.get("port")
                
                if ip and port and protocol in ["http", "https"]:
                    proxy_url = f"{protocol}://{ip}:{port}"
                    valid_proxies.append(proxy_url)
            
            # Keep up to 30 proxies to rotate through
            PROXY_POOL = valid_proxies[:30]
            print(f"[+] Loaded {len(PROXY_POOL)} working proxies into the pool.")
        else:
            print("[-] Failed to fetch proxies from API.")
    except Exception as e:
        print(f"[-] Error loading proxies: {str(e)}")

# Initialize the proxy list on app startup
fetch_and_rank_proxies()

def get_random_proxy():
    """Returns a random proxy from the available pool."""
    if PROXY_POOL:
        return random.choice(PROXY_POOL)
    return None

@app.route('/', methods=['GET'])
def home():
    return jsonify({
        "status": "online",
        "proxies_loaded": len(PROXY_POOL),
        "usage": "/download?url=YOUR_MEDIA_URL"
    })

@app.route('/download', methods=['GET'])
def get_video_info():
    url = request.args.get('url')
    if not url:
        return jsonify({"error": "Missing 'url' parameter"}), 400

    cookie_path = os.path.join(os.path.dirname(__file__), 'cookies.txt')

    # Try up to 3 different proxies if one fails
    max_retries = 3
    for attempt in range(max_retries):
        selected_proxy = get_random_proxy()
        
        ydl_opts = {
            'quiet': True,
            'no_warnings': True,
            'format': 'best',
            'user_agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
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
                    "proxy_used": selected_proxy if selected_proxy else "Direct IP",
                    "title": info.get('title'),
                    "thumbnail": info.get('thumbnail'),
                    "duration": info.get('duration'),
                    "download_url": info.get('url'),
                    "uploader": info.get('uploader'),
                    "ext": info.get('ext')
                })
                
        except Exception as e:
            print(f"[!] Attempt {attempt + 1} with proxy {selected_proxy} failed: {str(e)}")
            # If the proxy pool gets exhausted or errors out, refresh the pool on final attempt
            if attempt == max_retries - 1:
                return jsonify({
                    "status": "error",
                    "message": f"Failed after {max_retries} proxy retries. Details: {str(e)}"
                }), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 8000))
    app.run(host='0.0.0.0', port=port)
