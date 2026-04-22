import os
import requests
from bs4 import BeautifulSoup
from markdownify import markdownify as md

# Targeted URLs and their specific local filenames
DOWNLOAD_LIST = [
    {
        "url": "https://www.lenovo.com/us/en/p/laptops/thinkpad/thinkpadx1/thinkpad-x1-carbon-gen-12/len101t0083",
        "folder": "product",
        "filename": "lenovo_product_catalog.txt"
    },
    {
        "url": "https://pcsupport.lenovo.com/us/en/contact-us", # Better contact/support entry
        "folder": "tech",
        "filename": "tech_support.txt"
    },
    {
        "url": "https://www.lenovo.com/us/en/legal/new-product-limited-warranty/", # Updated warranty link
        "folder": "policy",
        "filename": "warranty.txt"
    },
    {
        "url": "https://www.lenovo.com/us/en/shopping-faq/", # General FAQ covers delivery
        "folder": "policy",
        "filename": "delivery.txt"
    },
    {
        "url": "https://www.lenovo.com/us/en/shopping-faq/", # General FAQ covers returns
        "folder": "policy",
        "filename": "returns & refund.txt"
    }
]

def download_as_markdown_txt(item):
    url = item['url']
    folder = item['folder']
    filename = item['filename']
    
    print(f"Downloading {url} to {folder}/{filename}...")
    
    try:
        # Using a common browser user agent to avoid bot detection
        headers = {
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
            'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,image/apng,*/*;q=0.8',
            'Accept-Language': 'en-US,en;q=0.9',
        }
        
        # Increased timeout and added stream for large pages
        with requests.get(url, headers=headers, timeout=30, stream=True) as response:
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, 'html.parser')
            
            # Remove noise
            for tag in soup(['nav', 'footer', 'header', 'script', 'style']):
                tag.decompose()
                
            main_content = soup.find('main') or soup.find('article') or soup.find('div', id='content') or soup.body
            
            markdown_content = md(str(main_content), heading_style="ATX")
            
            os.makedirs(folder, exist_ok=True)
            filepath = os.path.join(folder, filename)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(f"--- SOURCE: {url} ---\n\n")
                f.write(markdown_content)
                
            print(f"Successfully saved to {filepath}")
        
    except Exception as e:
        print(f"Error downloading {url}: {e}")

if __name__ == "__main__":
    for item in DOWNLOAD_LIST:
        download_as_markdown_txt(item)
