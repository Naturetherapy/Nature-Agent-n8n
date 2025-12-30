import requests, random, os, subprocess, time, concurrent.futures

# API Keys & Config
PEXELS_API_KEY = os.getenv('PEXELS_API_KEY')
FREESOUND_API_KEY = os.getenv('FREESOUND_API_KEY')
TELEGRAM_BOT_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
TELEGRAM_CHAT_ID = os.getenv('TELEGRAM_CHAT_ID')
MAKE_WEBHOOK_URL = os.getenv('MAKE_WEBHOOK_URL')

# --- AAPKI POORI ORIGINAL LIST (As it was) ---
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
    """Music fetch from Freesound [Rule: Every video must have music]"""
    try:
        url = f"https://freesound.org/apiv2/search/text/?query=nature+piano&token={FREESOUND_API_KEY}&filter=duration:[10 TO 30]&fields=previews&page_size=10"
        resp = requests.get(url, timeout=7).json()
        m_url = random.choice(resp['results'])['previews']['preview-hq-mp3']
        r = requests.get(m_url, timeout=7)
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
            headers={"Authorization": PEXELS_API_KEY}, timeout=7)
        
        music_file = music_future.result()
        v_resp = video_future.result().json()

    # --- 100% VIDEO FILTERING & DYNAMIC CAPTION ---
    v_link = None
    title, description, hashtags, final_caption = "", "", "", ""
    
    if v_resp.get('videos'):
        video_data = random.choice(v_resp['videos'])
        
        # --- Dynamic Text Logic ---
        raw_name = video_data.get('url', "").split('/')[-2].replace('-', ' ').title()
        title = f"Pure {raw_name}"[:50]
        description = f"Nature view of {topic}."[:50]
        tags = [f"#{topic.replace(' ', '')}", "#nature", "#viral", "#reels", "#peace", "#view", "#beauty", "#relax"]
        hashtags = " ".join(tags[:8])
        final_caption = f"{title}\n\n{description}\n\n{hashtags}"

        # --- Fix: Image pickup problem solve ---
        for file in video_data['video_files']:
            if 'video' in file.get('file_type', ''):
                v_link = file['link']
                break
    
    if not v_link or not music_file: return

    # --- MERGE PROCESS (Max 10s) ---
    cmd = ['ffmpeg', '-y', '-i', v_link, '-i', music_file, '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', '-shortest', '-preset', 'ultrafast', 'final.mp4']
    subprocess.run(cmd, check=True, timeout=20)

    # --- CATBOX UPLOAD (Merged Link for Webhook) ---
    def upload_to_catbox():
        with open("final.mp4", 'rb') as f:
            r = requests.post('https://catbox.moe/user/api.php', data={'reqtype': 'fileupload'}, files={'fileToUpload': f}, timeout=25)
            return r.text.strip()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        catbox_future = executor.submit(upload_to_catbox)
        
        # Telegram Send
        with open("final.mp4", 'rb') as f:
            executor.submit(requests.post, f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo", 
                            data={"chat_id": TELEGRAM_CHAT_ID, "caption": final_caption}, files={"video": f})
        
        merged_url = catbox_future.result()
        
        # --- WEBHOOK DATA (All fields included) ---
        if MAKE_WEBHOOK_URL and merged_url.startswith('http'):
            executor.submit(requests.post, MAKE_WEBHOOK_URL, json={
                "video_url": merged_url, 
                "title": title,
                "description": description,
                "caption": final_caption,
                "hashtags": hashtags,
                "topic": topic
            }, timeout=15)

    print(f"Done! Process Time: {time.time() - start_time:.2f}s")

if __name__ == "__main__":
    run_automation()
