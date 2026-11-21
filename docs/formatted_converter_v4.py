import os
import requests

# Dictionary of high-quality, open-access clean contract files 
CLEAN_REPOS = {
    "NDA": [
        "https://commonpaper.com",
        "https://github.com",
        "https://github.com"
    ],
    "MSA": [
        "https://commonpaper.com",
        "https://commonpaper.com",
        "https://github.com"
    ],
    "SOW": [
        "https://commonpaper.com",
        "https://github.com"
    ],
    "ORDER_FORM": [
        "https://commonpaper.com",
        "https://commonpaper.com"
    ]
}

def fetch_clean_templates():
    output_dir = "Pristine_Contracts"
    print(f"[*] Creating document directory: {output_dir}/")
    os.makedirs(output_dir, exist_ok=True)
    
    headers = {
        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
    }

    for category, urls in CLEAN_REPOS.items():
        category_path = os.path.join(output_dir, category)
        os.makedirs(category_path, exist_ok=True)
        
        for index, url in enumerate(urls, start=1):
            filename = f"{category}_Clean_Template_{index}.docx"
            filepath = os.path.join(category_path, filename)
            
            print(f"[~] Fetching clean structural {category} ({index}/{len(urls)})...")
            try:
                response = requests.get(url, headers=headers, timeout=15)
                if response.status_code == 200:
                    with open(filepath, 'wb') as f:
                        f.write(response.content)
                    print(f" [✔] Saved beautifully formatted file: {filepath}")
                else:
                    # Fallback notice if an individual file fails
                    print(f" [!] Could not download via link (Status {response.status_code})")
            except Exception as e:
                print(f" [!] Connection error for {category} index {index}: {e}")

if __name__ == "__main__":
    fetch_clean_templates()
    print("\n[✔] Finished! Check the 'Pristine_Contracts' directory for layout-perfect documents.")

