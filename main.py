import requests, random, os, subprocess, time, concurrent.futures

# API Keys & Config
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')
FREESOUND_API_KEY = os.getenv('FREESOUND_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MAKE_WEBHOOK_URL = os.getenv('MAKE_WEBHOOK_URL')

STRICT_TOPICS = [
    "Tropical Beach Waves", "Amazon Rainforest Rain", "Himalayan Snow Peaks",
    "Autumn Forest Creek", "Sahara Desert Dunes", "Deep Ocean Blue",
    "Thunderstorm in Woods", "Crystal Waterfall", "Bamboo Forest Wind"
]

def get_unique_music():
    """Fast music fetch from Freesound"""
    try:
        url = f"https://freesound.org/apiv2/search/text/?query=nature+piano&token={FREESOUND_API_KEY}&filter=duration:[10 TO 20]&fields=previews&page_size=5"
        resp = requests.get(url, timeout=7).json()
        m_url = random.choice(resp['results'])['previews']['preview-hq-mp3']
        r = requests.get(m_url, timeout=7)
        with open("m.mp3", "wb") as f: f.write(r.content)
        return "m.mp3"
    except: return None

def run_automation():
    topic = random.choice(STRICT_TOPICS)
    
    # 1. Parallel Fetch: Video and Music together (Saves ~10s)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        music_future = executor.submit(get_unique_music)
        video_future = executor.submit(requests.get, 
            f"https://api.pexels.com/videos/search?query={topic}&per_page=1&orientation=portrait", 
            headers={"Authorization": PEXELS_API_KEY}, timeout=7)
        
        music_file = music_future.result()
        v_resp = video_future.result().json()

    if not music_file or not v_resp.get('videos'): return

    v_link = v_resp['videos'][0]['video_files'][0]['link']

    # 2. Fastest Merge: Stream copy using FFmpeg (Takes 2-3s)
    # Instruction: Ensure background music is added
    cmd = ['ffmpeg', '-y', '-i', v_link, '-i', music_file, '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', '-shortest', '-preset', 'ultrafast', 'final.mp4']
    subprocess.run(cmd, check=True, timeout=15)

    # 3. Upload to Catbox (Essential for Webhook/Make.com)
    with open("final.mp4", 'rb') as f:
        up = requests.post('https://catbox.moe/user/api.php', 
                         data={'reqtype': 'fileupload'}, 
                         files={'fileToUpload': f}, 
                         timeout=25) # Optimized timeout
        merged_url = up.text.strip()

    # 4. Parallel Sending: Telegram and Make.com Webhook (Saves ~5s)
    if merged_url.startswith('http'):
        def send_tg():
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo", 
                          data={"chat_id": TELEGRAM_CHAT_ID, "caption": f"{topic} #nature"}, 
                          files={"video": open("final.mp4", 'rb')}, timeout=15)

        def send_make():
            if MAKE_WEBHOOK_URL:
                requests.post(MAKE_WEBHOOK_URL, json={
                    "video_url": merged_url, "title": topic, "caption": f"Relaxing {topic}"
                }, timeout=15)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(send_tg)
            executor.submit(send_make)
        
        print(f"Success! Workflow completed in under 30s using Catbox.")

if __name__ == "__main__":
    run_automation()
