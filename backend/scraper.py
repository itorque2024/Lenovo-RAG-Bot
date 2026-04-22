import os
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md
from urllib.parse import urlparse

# Categories and their targeted URLs
TARGETS = {
    "products": [
        "https://www.lenovo.com/us/en/p/laptops/thinkpad/thinkpadx1/thinkpad-x1-carbon-gen-12/len101t0083",
        "https://www.lenovo.com/us/en/p/laptops/yoga/yoga-2-in-1-series/yoga-7i-gen-9-14-inch-intel/len101y0043"
    ],
    "support": [
        "https://support.lenovo.com/us/en/solutions/ht101564",  # How to find serial number
        "https://support.lenovo.com/us/en/solutions/ht505031"   # Battery FAQ
    ],
    "policies": [
        "https://www.lenovo.com/us/en/shopping-faq/",
        "https://www.lenovo.com/us/en/privacy/"
    ]
}

def scrape_to_markdown(url, category):
    print(f"Scraping: {url}...")
    try:
        headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'}
        response = requests.get(url, headers=headers, timeout=15)
        response.raise_for_status()
        
        soup = BeautifulSoup(response.text, 'html.parser')
        
        # Remove script and style elements
        for script in soup(["script", "style"]):
            script.decompose()

        # Target main content area (heuristics)
        main_content = soup.find('main') or soup.find('article') or soup.find('div', {'id': 'content'}) or soup.body
        
        markdown_text = md(str(main_content), heading_style="ATX")
        
        # Generate a clean filename
        parsed_url = urlparse(url)
        filename = parsed_url.path.strip('/').replace('/', '_') or "index"
        if not filename.endswith('.md'):
            filename += '.md'
            
        output_dir = f"data/{category}"
        os.makedirs(output_dir, exist_ok=True)
        
        filepath = os.path.join(output_dir, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(f"# Source: {url}\n\n")
            f.write(markdown_text)
            
        print(f"Saved to {filepath}")
        
    except Exception as e:
        print(f"Error scraping {url}: {e}")

if __name__ == "__main__":
    for category, urls in TARGETS.items():
        for url in urls:
            scrape_to_markdown(url, category)
