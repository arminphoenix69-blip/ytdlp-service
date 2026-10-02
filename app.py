"""
YouTube Audio Extractor Service
یه سرویس ساده با yt-dlp که لینک مستقیم صوتی ویدیوهای یوتیوب رو برمی‌گردونه.
برای استفاده توسط ربات تلگرام Aura music.
"""

from flask import Flask, request, jsonify
import yt_dlp
import re

app = Flask(__name__)

# برای امنیت: فقط ربات ما بتونه صدا بزنه (توکن رو عوض کن)
API_SECRET = "change-this-to-a-random-secret"

def extract_video_id(url_or_id):
    """از لینک یا ID، فقط videoId رو استخراج کن"""
    if re.match(r'^[A-Za-z0-9_-]{11}$', url_or_id):
        return url_or_id
    m = re.search(r'(?:v=|youtu\.be/|/shorts/)([A-Za-z0-9_-]{11})', url_or_id)
    return m.group(1) if m else None

@app.route('/audio', methods=['POST'])
def get_audio():
    # چک امنیتی
    auth = request.headers.get('X-API-Secret', '')
    if auth != API_SECRET:
        return jsonify({"error": "unauthorized"}), 403

    data = request.get_json(silent=True) or {}
    url_or_id = data.get('url', '') or data.get('videoId', '')

    video_id = extract_video_id(url_or_id)
    if not video_id:
        return jsonify({"error": "invalid url or video id"}), 400

    url = f"https://www.youtube.com/watch?v={video_id}"

    ydl_opts = {
        'format': 'bestaudio[ext=m4a]/bestaudio/best',
        'quiet': True,
        'no_warnings': True,
        'noplaylist': True,
        # فقط اطلاعات رو بگیر، دانلود نکن
        'skip_download': True,
    }

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=False)

            # بهترین فرمت صوتی رو پیدا کن
            audio_url = None
            for f in info.get('formats', []):
                # فقط فرمت‌های صوتی
                if f.get('acodec') != 'none' and f.get('vcodec') == 'none' and f.get('url'):
                    audio_url = f['url']
                    break

            # اگه پیدا نشد، از url اصلی استفاده کن
            if not audio_url:
                audio_url = info.get('url')

            if not audio_url:
                return jsonify({"error": "no audio stream found"}), 404

            return jsonify({
                "url": audio_url,
                "title": info.get('title', ''),
                "artist": info.get('uploader', '') or info.get('channel', ''),
                "duration": info.get('duration', 0),
                "videoId": video_id,
            })

    except yt_dlp.utils.DownloadError as e:
        return jsonify({"error": f"download error: {str(e)[:200]}"}), 404
    except Exception as e:
        return jsonify({"error": f"internal error: {str(e)[:200]}"}), 500

@app.route('/health', methods=['GET'])
def health():
    return jsonify({"status": "ok"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000)
