import requests, random, os, subprocess, time, concurrent.futures

# API Keys & Config
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')
FREESOUND_API_KEY = os.getenv('FREESOUND_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MAKE_WEBHOOK_URL = os.getenv('MAKE_WEBHOOK_URL')

STRICT_TOPICS = [
    "Deep Turquoise Ocean", "Crashing Blue Waves", "Crystal Clear Waterfall",
    "Gently Flowing Creek", "Mist Over Lake", "Bubbling Mountain Spring",
    "Sunlight Through Trees", "Ancient Mossy Oaks", "Wildflower Meadow",
    "Lush Fern Valley", "Tropical Palm Grove", "Fiery Sunset Sky",
    "Snowy Mountain Peaks", "Rolling Green Hills", "Heavy Tropical Rain"
]

def get_unique_music():
    """Freesound se music fetch karna - Timeout 5s for speed"""
    try:
        url = f"https://freesound.org/apiv2/search/text/?query=nature+ambient&token={FREESOUND_API_KEY}&filter=duration:[10 TO 30]&fields=previews&page_size=10"
        resp = requests.get(url, timeout=5).json()
        m_url = random.choice(resp['results'])['previews']['preview-hq-mp3']
        r = requests.get(m_url, timeout=5)
        with open("m.mp3", "wb") as f: f.write(r.content)
        return "m.mp3"
    except: return None

def run_automation():
    start_time = time.time()
    topic = random.choice(STRICT_TOPICS)
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        music_future = executor.submit(get_unique_music)
        video_future = executor.submit(requests.get, 
            f"https://api.pexels.com/videos/search?query={topic}&per_page=5&orientation=portrait", 
            headers={"Authorization": PEXELS_API_KEY}, timeout=5)
        
        music_file = music_future.result()
        v_resp = video_future.result().json()

    # --- 100% VIDEO FILTERING (SUDHAAR) ---
    v_link = None
    if v_resp.get('videos'):
        for video in v_resp['videos']:
            # Yahan hum pakka kar rahe hain ki sirf 'video/mp4' hi select ho
            files = [f for f in video['video_files'] if f.get('file_type') == 'video/mp4' or '.mp4' in f.get('link', '')]
            if files:
                # Sabse pehla valid mp4 link uthayega
                v_link = files[0]['link']
                break
    
    if not v_link or not music_file:
        print("Video ya Music link nahi mila.")
        return

    # --- FFmpeg: Video + Music Merge (As per your Rule) ---
    # '-preset ultrafast' isse process 10 second mein khatam hoga
    cmd = [
        'ffmpeg', '-y', '-i', v_link, '-i', music_file, 
        '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', 
        '-shortest', '-preset', 'ultrafast', 'final.mp4'
    ]
    subprocess.run(cmd, check=True, timeout=15)

    # --- Catbox.moe Upload & Webhook ---
    def upload_to_catbox():
        with open("final.mp4", 'rb') as f:
            # Catbox hamesha merged video ka direct link deta hai
            r = requests.post('https://catbox.moe/user/api.php', 
                            data={'reqtype': 'fileupload'}, 
                            files={'fileToUpload': f}, timeout=20)
            return r.text.strip()

    def send_to_tg():
        with open("final.mp4", 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo", 
                          data={"chat_id": TELEGRAM_CHAT_ID, "caption": f"✅ {topic}"}, 
                          files={"video": f}, timeout=15)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        catbox_future = executor.submit(upload_to_catbox)
        executor.submit(send_to_tg)
        
        merged_url = catbox_future.result()
        
        if MAKE_WEBHOOK_URL and merged_url.startswith('http'):
            # Merged link hi Webhook ko bhej raha hai (Fixed)
            executor.submit(requests.post, MAKE_WEBHOOK_URL, json={"video_url": merged_url}, timeout=10)

    print(f"Total Time: {time.time() - start_time:.2f}s | Merged URL: {merged_url}")

if __name__ == "__main__":
    run_automation()
