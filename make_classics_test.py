import os
import requests
import shutil
from PIL import Image, ImageOps

# CONFIG
TEST_ROOT = "/app/TEST_LAB/CLASSICS_TEST"
GOLD_DIR = os.path.join(TEST_ROOT, "GOLD_MUSEUM")
TARGET_DIR = os.path.join(TEST_ROOT, "TARGET_INBOX")

ARTIFACTS = {
    "Michelangelo_David.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/8/80/Michelangelo%27s_David_-_63_grijze_achtergrond.jpg/480px-Michelangelo%27s_David_-_63_grijze_achtergrond.jpg",
    "Botticelli_Venus.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/0/0b/Sandro_Botticelli_-_La_nascita_di_Venere_-_Google_Art_Project_-_edited.jpg/540px-Sandro_Botticelli_-_La_nascita_di_Venere_-_Google_Art_Project_-_edited.jpg",
    "DaVinci_Study.jpg": "https://upload.wikimedia.org/wikipedia/commons/thumb/4/4b/%C3%89tude_pour_la_L%C3%A9da_-_L%C3%A9onard_de_Vinci_-_Chatsworth_Devonshire_Collection.jpg/445px-%C3%89tude_pour_la_L%C3%A9da_-_L%C3%A9onard_de_Vinci_-_Chatsworth_Devonshire_Collection.jpg"
}

def download_image(url, save_path):
    print(f"⬇️  Acquiring Artifact: {os.path.basename(save_path)}...")
    try:
        # FAKE A BROWSER to avoid being blocked
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        
        response = requests.get(url, headers=headers, timeout=15)
        
        if response.status_code == 200:
            with open(save_path, 'wb') as f:
                f.write(response.content)
            print(f"   ✅ Saved {len(response.content)} bytes.")
            return True
        else:
            print(f"   ⚠️ Failed: HTTP {response.status_code}") 
    except Exception as e:
        print(f"❌ Error: {e}")
    return False

def create_variants(original_path, target_dir):
    try:
        base_name = os.path.basename(original_path)
        img = Image.open(original_path)
        
        # 1. B&W Variant
        bw_path = os.path.join(target_dir, f"{os.path.splitext(base_name)[0]}_BW_Study.jpg")
        ImageOps.grayscale(img).save(bw_path)
        print("   🎨 Created Variant: B&W Sketch")
        
        # 2. Thumbnail Variant
        thumb_path = os.path.join(target_dir, f"thumb_{base_name}")
        img.resize((100, 100)).save(thumb_path)
        print("   🎨 Created Variant: Catalog Thumbnail")
        
        # 3. Direct Copy
        copy_path = os.path.join(target_dir, f"Copy of {base_name}")
        shutil.copy(original_path, copy_path)
        print("   🎨 Created Variant: Archive Copy")
        
    except Exception as e:
        print(f"   ❌ Variant Error: {e}")

def main():
    # Setup Dirs
    if os.path.exists(TEST_ROOT): shutil.rmtree(TEST_ROOT)
    os.makedirs(GOLD_DIR, exist_ok=True)
    os.makedirs(TARGET_DIR, exist_ok=True)
    print(f"✅ Created Museum: {TEST_ROOT}")
    
    # Download & Generate
    for name, url in ARTIFACTS.items():
        # Save Original to Target (as if it was just imported)
        save_path = os.path.join(TARGET_DIR, name)
        if download_image(url, save_path):
            if "David" in name: # Only make edits for David for this test
                create_variants(save_path, TARGET_DIR)

    print("\n" + "="*50)
    print("🏛️  CLASSICAL ART LAB READY")
    print("="*50)

if __name__ == "__main__":
    main()
