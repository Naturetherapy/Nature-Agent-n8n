import requests, random, os, subprocess, time, concurrent.futures

# API Keys & Config
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')
FREESOUND_API_KEY = os.getenv('FREESOUND_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MAKE_WEBHOOK_URL = os.getenv('MAKE_WEBHOOK_URL')

STRICT_TOPICS = [
    # --- Water & Oceans ---
    "Deep Turquoise Ocean", "Crashing Blue Waves", "Crystal Clear Waterfall",
    "Gently Flowing Creek", "Mist Over Lake", "Bubbling Mountain Spring",
    "Golden Sunlit Pond", "Hidden Forest Stream", "Rippling River Water",

    # --- Forest & Flora ---
    "Dense Green Rainforest", "Autumn Gold Leaves", "Misty Pine Forest",
    "Sunlight Through Trees", "Ancient Mossy Oaks", "Wildflower Meadow",
    "Blooming Flower Garden", "Bamboo Leaf Canopy", "Tall Grass Prairie",
    "Lush Fern Valley", "Tropical Palm Grove", "Blooming Lavender Field",

    # --- Sky & Atmosphere ---
    "Fiery Sunset Sky", "Pastel Morning Clouds", "Midnight Starry Galaxy",
    "Dark Thunderstorm Clouds", "Double Rainbow Arch", "Soft Moonlight Glow",
    "Swirling Northern Lights", "Purple Twilight Haze", "Bright Blue Sky",

    # --- Terrain & Earth ---
    "Snowy Mountain Peaks", "Sand Dune Ripples", "Steep Rocky Cliffs",
    "Rolling Green Hills", "Canyon Stone Layers", "Volcanic Ash Ground",
    "Glacier Ice Texture", "Moist Soil and Sprout", "Cave Stalactites",

    # --- Weather & Effects ---
    "Heavy Tropical Rain", "Falling White Snow", "Morning Dew Drops",
    "Swirling Winter Blizzard", "Golden Hour Sunbeams", "Dense White Fog",
    "Dry Desert Heatwaves", "Frosty Window Patterns", "Falling Autumn Leaves"
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
    
    with concurrent.futures.ThreadPoolExecutor() as executor:
        music_future = executor.submit(get_unique_music)
        # /videos/search endpoint image result nahi bhejta, lekin hum safe side rahenge
        video_future = executor.submit(requests.get, 
            f"https://api.pexels.com/videos/search?query={topic}&per_page=3&orientation=portrait", 
            headers={"Authorization": PEXELS_API_KEY}, timeout=7)
        
        music_file = music_future.result()
        v_resp = video_future.result().json()

    if not music_file or not v_resp.get('videos'): 
        print("Data not found.")
        return

    # --- STRICT VIDEO FILTERING ---
    v_link = None
    for video in v_resp['videos']:
        for file in video['video_files']:
            # 'video/mp4' check karega taaki koi jpg ya link na aaye
            if 'video' in file.get('file_type', ''):
                v_link = file['link']
                break
        if v_link: break
    
    if not v_link:
        print("No pure video file found.")
        return
    # ------------------------------

    # FFmpeg command: Music merge ho raha hai (as per your request)
    cmd = ['ffmpeg', '-y', '-i', v_link, '-i', music_file, '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', '-shortest', '-preset', 'ultrafast', 'final.mp4']
    subprocess.run(cmd, check=True, timeout=20)

    # Upload and Send
    with open("final.mp4", 'rb') as f:
        up = requests.post('https://catbox.moe/user/api.php', 
                         data={'reqtype': 'fileupload'}, 
                         files={'fileToUpload': f}, 
                         timeout=25)
        merged_url = up.text.strip()

    if merged_url.startswith('http'):
        def send_tg():
            requests.post(f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo", 
                          data={"chat_id": TELEGRAM_CHAT_ID, "caption": f"{topic} #nature"}, 
                          files={"video": open("final.mp4", 'rb')}, timeout=15)

        with concurrent.futures.ThreadPoolExecutor() as executor:
            executor.submit(send_tg)
            if MAKE_WEBHOOK_URL:
                executor.submit(requests.post, MAKE_WEBHOOK_URL, json={"video_url": merged_url}, timeout=15)
        
        print(f"Done: {topic}")

if __name__ == "__main__":
    run_automation()
