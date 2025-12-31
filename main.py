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
    "Dense Green Rainforest", "Autumn Gold Leaves", "Misty Pine Forest",
    "Sunlight Through Trees", "Ancient Mossy Oaks", "Wildflower Meadow",
    "Lush Fern Valley", "Tropical Palm Grove", "Blooming Lavender Field",
    "Fiery Sunset Sky", "Pastel Morning Clouds", "Midnight Starry Galaxy",
    "Dark Thunderstorm Clouds", "Double Rainbow Arch", "Soft Moonlight Glow"
]

def get_unique_music():
    try:
        url = f"https://freesound.org/apiv2/search/text/?query=nature+ambient&token={FREESOUND_API_KEY}&filter=duration:[10 TO 30]&fields=previews&page_size=10"
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
        # Search specifically for videos
        video_future = executor.submit(requests.get, 
            f"https://api.pexels.com/videos/search?query={topic}&per_page=10&orientation=portrait", 
            headers={"Authorization": PEXELS_API_KEY}, timeout=7)
        
        music_file = music_future.result()
        v_resp = video_future.result().json()

    # --- 100% STRICT VIDEO-ONLY LOGIC ---
    v_link = None
    title, desc, hashtags, final_caption = "", "", "", ""

    if v_resp.get('videos'):
        for video in v_resp['videos']:
            # Metadata generation
            raw_name = video.get('url', "").split('/')[-2].replace('-', ' ').title()
            title = f"Pure {raw_name}"[:50]
            desc = f"Nature vibes: {topic}"[:50]
            tags = [f"#{topic.replace(' ', '')}", "#nature", "#viral", "#reels", "#peace", "#view", "#4k", "#relax"]
            hashtags = " ".join(tags[:8])
            final_caption = f"{title}\n\n{desc}\n\n{hashtags}"

            # DOUBLE-LOCK FILTER
            for file in video['video_files']:
                link = file.get('link', '')
                f_type = file.get('file_type', '')
                
                # Check 1: File type must be video/mp4
                # Check 2: Link must end with .mp4 (removes jpg/png previews)
                if 'video/mp4' in f_type and ('.mp4' in link.lower()):
                    v_link = link
                    break
            if v_link: break # Agar video mil gayi toh loop stop karein
    
    if not v_link or not music_file:
        print("Video/Music file missing.")
        return

    # --- MERGING (final.mp4) ---
    cmd = ['ffmpeg', '-y', '-i', v_link, '-i', music_file, '-c:v', 'copy', '-c:a', 'aac', '-map', '0:v:0', '-map', '1:a:0', '-shortest', '-preset', 'ultrafast', 'final.mp4']
    subprocess.run(cmd, check=True, timeout=25)

    # --- CATBOX UPLOAD (MERGED LINK ONLY) ---
    def upload_to_catbox():
        with open("final.mp4", 'rb') as f:
            r = requests.post('https://catbox.moe/user/api.php', 
                            data={'reqtype': 'fileupload'}, 
                            files={'fileToUpload': f}, timeout=30)
            return r.text.strip()

    with concurrent.futures.ThreadPoolExecutor() as executor:
        catbox_future = executor.submit(upload_to_catbox)
        
        # Telegram notification
        with open("final.mp4", 'rb') as f:
            executor.submit(requests.post, f"https://api.telegram.org/bot{TELEGRAM_BOT_TOKEN}/sendVideo", 
                            data={"chat_id": TELEGRAM_CHAT_ID, "caption": final_caption}, files={"video": f})
        
        merged_url = catbox_future.result()
        
        # FINAL WEBHOOK OUTPUT (Catbox Link)
        if MAKE_WEBHOOK_URL and merged_url.startswith('http'):
            executor.submit(requests.post, MAKE_WEBHOOK_URL, json={
                "video_url": merged_url, # Always Catbox Merged Link
                "title": title,
                "description": desc,
                "caption": final_caption,
                "hashtags": hashtags,
                "status": "success"
            }, timeout=15)

    print(f"Total Time: {time.time() - start_time:.2f}s | Output: {merged_url}")

if __name__ == "__main__":
    run_automation()
