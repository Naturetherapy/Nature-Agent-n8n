import requests, random, os, subprocess, time, concurrent.futures

# API Keys & Config
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')
FREESOUND_API_KEY = os.getenv('FREESOUND_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MAKE_WEBHOOK_URL = os.getenv('MAKE_WEBHOOK_URL')

# --- AAPKI POORI LIST WAPAS DAAL DI HAI ---
STRICT_TOPICS = [
    "Deep Turquoise Ocean", "Crashing Blue Waves", "Crystal Clear Waterfall",
    "Gently Flowing Creek", "Mist Over Lake", "Bubbling Mountain Spring",
    "Golden Sunlit Pond", "Hidden Forest Stream", "Rippling River Water",
    "Dense Green Rainforest", "Autumn Gold Leaves", "Misty Pine Forest",
    "Sunlight Through Trees", "Ancient Mossy Oaks", "Wildflower Meadow",
    "Blooming Flower Garden", "Bamboo Leaf Canopy", "Tall Grass Prairie",
    "Lush Fern Valley", "Tropical Palm Grove", "Blooming Lavender Field",
    "Fiery Sunset Sky", "Pastel Morning Clouds", "Midnight Starry Galaxy",
    "Dark Thunderstorm Clouds", "Double Rainbow Arch", "Soft Moonlight Glow",
    "Swirling Northern Lights", "Purple Twilight Haze", "Bright Blue Sky",
    "Snowy Mountain Peaks", "Sand Dune Ripples", "Steep Rocky Cliffs",
    "Rolling Green Hills", "Canyon Stone Layers", "Volcanic Ash Ground",
    "Glacier Ice Texture", "Moist Soil and Sprout", "Cave Stalactites",
    "Heavy Tropical Rain", "Falling White Snow", "Morning Dew Drops",
    "Swirling Winter Blizzard", "Golden Hour Sunbeams", "Dense White Fog",
    "Dry Desert Heatwaves", "Frosty Window Patterns", "Falling Autumn Leaves"
]

def get_unique_music():
    """Fast music fetch - 5 seconds timeout"""
    try:
        url = f"https://freesound.org/apiv2/search/text/?query=nature+piano&token={FREESOUND_API_KEY}&filter=duration:[10 TO 20]&fields=previews&page_size=10"
        resp = requests.get(url, timeout=5).json()
        m_url = random.choice(resp['results'])['previews']['preview-hq-mp3']
        r = requests.get(m_url, timeout=5)
        with open("m.mp3", "wb") as f: f.write(r.content)
        return "m.mp3"
    except: return None

def run_automation():
    start_time = time.time()
    topic = random.choice(STRICT_TOPICS)
    
    # Parallel Fetching for Speed (Saves 5-10 seconds)
    with concurrent.futures.ThreadPoolExecutor() as executor:
        music_future = executor.submit(get_unique_music)
        video_future = executor.submit(requests.get, 
            f"https://api.pexels.com/videos/search?query={topic}&per_page=5&orientation=portrait", 
            headers={"Authorization": PEXELS_API_KEY}, timeout=5)
        
        music_file = music_future.result()
        v_resp = video_future.result().json()

    # --- 100% VIDEO PICKUP LOGIC (No Images) ---
    v_link = None
    if v_resp.get('videos'):
        for video in v_resp['videos']:
            # Sirf mp4 link filter kar rahe hain
            files = [f for f in video['video_files'] if 'video/mp4' in f.get('file_type', '') or '.mp4' in f.get('link', '')]
            if files:
                v_link = files[0]['link']
                break
    
    if not v_link or not music_file:
        print("Required data missing.")
        return

    # --- ULTRAFAST FFMEPG MERGE (Max 10s) ---
    # Aapka background music rule yahan apply ho raha hai
    cmd = [
        'ffmpeg', '-y', '-i', v_link, '-i', music_file, 
        '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', 
        '-shortest', '-preset', 'ultrafast', 'final.mp4'
    ]
    subprocess.run(cmd, check=True, timeout=15)

    # --- UPLOAD & NOTIFY (Parallel) ---
    def upload_final():
        with open("final.mp4", 'rb') as f:
            r = requests.post('https://catbox.moe/user/api.php', 
                            data={'reqtype': 'fileupload'}, 
                            files={'fileToUpload': f}, timeout=15)
            return r.text.strip()

    def send_to_telegram():
        with open("final.mp4", 'rb') as f:
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo", 
                          data={"chat_id": TELEGRAM_CHAT_ID, "caption": f"🎬 {topic}"}, 
                          files={"video": f}, timeout=15)

    with concurrent.futures.ThreadPoolExecutor() as executor:
        up_future = executor.submit(upload_final)
        executor.submit(send_to_telegram)
        
        merged_url = up_future.result()
        if MAKE_WEBHOOK_URL and merged_url.startswith('http'):
            # Webhook ko merged video URL 10 second ke andar bhejna
            executor.submit(requests.post, MAKE_WEBHOOK_URL, json={"video_url": merged_url}, timeout=10)

    print(f"Total Time: {time.time() - start_time:.2f}s | Topic: {topic}")

if __name__ == "__main__":
    run_automation()
