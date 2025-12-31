import requests, random, os, subprocess, time, concurrent.futures

# API Keys & Config
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')
FREESOUND_API_KEY = os.getenv('FREESOUND_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MAKE_WEBHOOK_URL = os.getenv('MAKE_WEBHOOK_URL')

HISTORY_FILE = "posted_history.txt"
FIXED_HASHTAGS = "#nature #wildlife #serenity #earth #landscape #adventure #explore #scenery"

# Saare 18 Unique Topics (Vapas add kar diye gaye hain)
STRICT_TOPICS = [
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
    """Speed: 5-7 seconds"""
    try:
        r_page = random.randint(1, 50)
        url = f"https://freesound.org/apiv2/search/text/?query=nature+piano&token={FREESOUND_API_KEY}&filter=duration:[10 TO 25]&fields=id,previews&page={r_page}"
        resp = requests.get(url, timeout=10).json()
        results = resp.get('results', [])
        random.shuffle(results)
        for track in results:
            t_id = str(track['id'])
            if t_id not in history:
                r = requests.get(track['previews']['preview-hq-mp3'], timeout=10)
                with open("m.mp3", "wb") as f: f.write(r.content)
                return "m.mp3", t_id
    except: pass
    return None, None

def parallel_delivery(merged_url, title, caption, hashtags):
    """Telegram aur Webhook ko ek saath bhejta hai (Parallel)"""
    def send_tg():
        full_text = f"{title}\n\n{caption}\n\n{hashtags}"
        requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo", 
                      data={"chat_id": TELEGRAM_CHAT_ID, "caption": full_text}, 
                      files={"video": open("final.mp4", 'rb')}, timeout=20)

    def send_webhook():
        if MAKE_WEBHOOK_URL:
            requests.post(MAKE_WEBHOOK_URL, json={
                "video_url": merged_url, # Catbox ka merged link
                "title": title, 
                "caption": caption,
                "hashtags": hashtags
            }, timeout=20)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        executor.submit(send_tg)
        executor.submit(send_webhook)

def run_automation():
    history = get_history()
    topic = random.choice(STRICT_TOPICS)
    
    title = f"{random.choice(['Pure', 'Calm', 'Wild'])} {topic} Magic".strip()[:50]
    short_caption = f"Relaxing {topic} vibes for you.".strip()[:50]
    
    # 1. Parallel Fetch Video & Music
    with concurrent.futures.ThreadPoolExecutor() as executor:
        music_future = executor.submit(get_unique_music, history)
        video_future = executor.submit(requests.get, 
            f"https://api.pexels.com/videos/search?query={topic}&per_page=10&orientation=portrait", 
            headers={"Authorization": PEXELS_API_KEY}, timeout=10)
        
        music_file, a_id = music_future.result()
        v_resp = video_future.result().json()

    if not music_file or not v_resp.get('videos'): return

    # 2. Image Blocker & Video Processing
    for vid in v_resp['videos']:
        v_id = str(vid['id'])
        if v_id not in history:
            # Check for Video content only (Block images)
            v_link = next((f['link'] for f in vid['video_files'] if 'video' in f.get('file_type', 'video') and f.get('width', 0) >= 720), None)
            if not v_link: continue

            # FAST MERGE (c:v copy use karke ~2 seconds)
            # Music added as per instruction
            cmd = ['ffmpeg', '-y', '-i', v_link, '-i', music_file, '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', '-shortest', '-preset', 'ultrafast', 'final.mp4']
            subprocess.run(cmd, check=True, timeout=20)

            # 3. Catbox Upload (Merged File)
            with open("final.mp4", 'rb') as f:
                up = requests.post('https://catbox.moe/user/api.php', data={'reqtype': 'fileupload'}, files={'fileToUpload': f}, timeout=40)
                merged_url = up.text.strip()

            if merged_url.startswith('http'):
                # 4. Final Parallel Delivery
                parallel_delivery(merged_url, title, short_caption, FIXED_HASHTAGS)
                save_to_history(v_id, a_id)
                print(f"Success! {title} sent in under 30s")
                return

if __name__ == "__main__":
    run_automation()
