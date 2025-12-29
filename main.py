import requests, random, os, subprocess, time

# API Keys & Config
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')
FREESOUND_API_KEY = os.getenv('FREESOUND_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MAKE_WEBHOOK_URL = os.getenv('MAKE_WEBHOOK_URL')

HISTORY_FILE = "posted_history.txt"
FIXED_HASHTAGS = "#nature #wildlife #serenity #earth #landscape #adventure #explore #scenery"

# 18 Unique Topics (Duplicates removed)
STRICT_TOPICS = [
    "Tropical Beach Waves", "Amazon Rainforest Rain", "Himalayan Snow Peaks",
    "Autumn Forest Creek", "Sahara Desert Dunes", "Deep Ocean Blue",
    "Thunderstorm in Woods", "Crystal Waterfall", "Bamboo Forest Wind",
    "Sunrise Mountain Mist", "Pine Forest Snow", "Coral Reef Underwater"
    "Tropical Beach Waves", "Amazon Rainforest Rain", "Himalayan Snow Peaks",
    "Autumn Forest Creek", "Sahara Desert Dunes", "Deep Ocean Blue",
    "Thunderstorm in Woods", "Crystal Waterfall", "Bamboo Forest Wind",
    "Sunrise Mountain Mist", "Pine Forest Snow", "Coral Reef Underwater",
    "Wildflower Meadow", "Volcanic Lava Flow", "Icelandic Glaciers",
    "Northern Lights Aurora", "Spring Garden Birds", "Rocky Canyon River"
]

def get_history():
    if not os.path.exists(HISTORY_FILE): return []
    with open(HISTORY_FILE, "r") as f: return f.read().splitlines()

def save_to_history(v_id, a_id):
    with open(HISTORY_FILE, "a") as f: f.write(f"{v_id}\n{a_id}\n")

def get_unique_music(history):
    """NoneType safety check for Freesound"""
    try:
        r_page = random.randint(1, 60)
        url = f"https://freesound.org/apiv2/search/text/?query=nature+ambient&token={FREESOUND_API_KEY}&filter=duration:[10 TO 25]&fields=id,previews&page={r_page}"
        resp = requests.get(url, timeout=10).json()
        results = resp.get('results', [])
        if not results: return None, None
        random.shuffle(results)
        for track in results:
            t_id = str(track['id'])
            if t_id not in history:
                m_url = track['previews']['preview-hq-mp3']
                r = requests.get(m_url, timeout=15)
                with open("m.mp3", "wb") as f: f.write(r.content)
                return "m.mp3", t_id
    except: pass
    return None, None

def run_automation():
    start_time = time.time()
    history = get_history()
    topic = random.choice(STRICT_TOPICS)
    
    # Title & Caption limit: 50 characters
    title = f"{random.choice(['Pure', 'Calm', 'Wild'])} {topic} Magic".strip()[:50]
    short_caption = f"Relaxing {topic} vibes for you.".strip()[:50]
    
    # Pexels Video-Only Search API
    v_resp = requests.get(f"https://api.pexels.com/videos/search?query={topic}&per_page=15&orientation=portrait", 
                          headers={"Authorization": PEXELS_API_KEY}, timeout=10).json()
    
    for vid in v_resp.get('videos', []):
        v_id = str(vid['id'])
        # Video length check (10-25s) and History check
        if v_id not in history and 10 <= vid.get('duration', 0) <= 25:
            # Sirf wohi files uthayega jinka mime_type 'video/mp4' hai
            v_link = next((f['link'] for f in vid['video_files'] if f['width'] >= 1080 and 'video' in f.get('file_type', 'video')), None)
            
            if not v_link: continue # Agar HD video nahi mila toh next try karein

            music_file, a_id = get_unique_music(history)
            if not music_file: continue 
            
            # Fast Merge using FFmpeg
            cmd = ['ffmpeg', '-y', '-i', v_link, '-i', music_file, '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', '-shortest', '-preset', 'ultrafast', 'final.mp4']
            subprocess.run(cmd, check=True, timeout=30)
            
            if os.path.exists("final.mp4"):
                with open("final.mp4", 'rb') as f:
                    up = requests.post('https://catbox.moe/user/api.php', data={'reqtype': 'fileupload'}, files={'fileToUpload': f}, timeout=30)
                    merged_url = up.text.strip()
                
                if merged_url.startswith('http'):
                    full_post_text = f"{title}\n\n{short_caption}\n\n{FIXED_HASHTAGS}"
                    
                    # Telegram Direct
                    requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo", 
                                  data={"chat_id": TELEGRAM_CHAT_ID, "caption": full_post_text}, files={"video": open("final.mp4", 'rb')})
                    
                    # Webhook Redirect to Make.com
                    if MAKE_WEBHOOK_URL:
                        requests.post(MAKE_WEBHOOK_URL, json={
                            "video_url": merged_url, 
                            "title": title, 
                            "caption": short_caption,
                            "hashtags": FIXED_HASHTAGS
                        })
                    
                    save_to_history(v_id, a_id)
                    print(f"Success! {title}")
                    return

if __name__ == "__main__":
    run_automation()
                       
