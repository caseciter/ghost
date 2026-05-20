import os
import re
from datetime import datetime
import requests
from markdownify import markdownify as md

# Configuration
GHOST_URL = os.environ.get("GHOST_URL", "https://www.caseciter.com")
GHOST_API_KEY = os.environ.get("GHOST_API_KEY", "a8cb21b63d79d87a2c3e748550")

# Filters (Date format: YYYY-MM-DD)
START_DATE = os.environ.get("START_DATE", "2026-01-01")  
END_DATE = os.environ.get("END_DATE", "2026-12-31")      
KEYWORD_FILTER = os.environ.get("KEYWORD_FILTER", "")   

def fetch_all_posts():
    """Fetches all posts from the Ghost Content API using pagination."""
    posts = []
    page = 1
    limit = 15
    endpoint = f"{GHOST_URL}/ghost/api/content/posts/"
    
    while True:
        params = {
            'key': GHOST_API_KEY,
            'limit': limit,
            'page': page,
            'formats': 'html',
            'include': 'tags,authors'
        }
        try:
            response = requests.get(endpoint, params=params)
            response.raise_for_status()
            data = response.json()
            
            page_posts = data.get('posts', [])
            if not page_posts:
                break
                
            posts.extend(page_posts)
            meta = data.get('meta', {}).get('pagination', {})
            if page >= meta.get('pages', 1):
                break
            page += 1
        except Exception as e:
            print(f"Error fetching data from Ghost API: {e}")
            break
            
    return posts

def matches_filters(post):
    """Applies date and keyword filtering to a post."""
    pub_date_str = post.get('published_at')
    if not pub_date_str:
        return False
    
    post_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00')).date()
    
    if START_DATE:
        start = datetime.strptime(START_DATE, "%Y-%m-%d").date()
        if post_date < start:
            return False
            
    if END_DATE:
        end = datetime.strptime(END_DATE, "%Y-%m-%d").date()
        if post_date > end:
            return False
            
    if KEYWORD_FILTER:
        keyword = KEYWORD_FILTER.lower()
        title = post.get('title', '').lower()
        html_content = post.get('html', '').lower()
        if keyword not in title and keyword not in html_content:
            return False
            
    return True

def create_compiled_markdown(posts):
    """Compiles all matched posts into a single clean Markdown document."""
    if not posts:
        print("No posts matched your filtering criteria.")
        return

    # Sort posts chronologically (oldest to newest)
    posts.sort(key=lambda x: x.get('published_at', ''))

    # Saving as a static unified filename for continuous replacement or tracking
    filename = "backups/compiled_posts.md"
    os.makedirs("backups", exist_ok=True)

    document_body = ""

    for post in posts:
        title = post.get('title', 'Untitled')
        url = post.get('url', GHOST_URL)
        html_content = post.get('html', '')
        
        # Strip out any native Ghost toggle/accordion blocks wrapper elements if they exist 
        # while keeping the inner raw structural text content intact
        markdown_content = md(html_content, heading_style="ATX", strip=['details', 'summary'])
        
        # Clean up double vertical spacing gaps
        markdown_content = re.sub(r'\n{3,}', '\n\n', markdown_content).strip()
        
        # Format layout precisely: Title heading, Content body text, and Resource URL footprint
        document_body += f"# {title}\n\n"
        document_body += f"{markdown_content}\n\n"
        document_body += f"**Original Post URL:** [{url}]({url})\n\n"
        document_body += "---\n\n"

    with open(filename, "w", encoding="utf-8") as f:
        f.write(document_body.strip())
        
    print(f"Success! Clean compiled document generated at: {filename}")

def main():
    all_posts = fetch_all_posts()
    matched_posts = [post for post in all_posts if matches_filters(post)]
    create_compiled_markdown(matched_posts)

if __name__ == "__main__":
    main()
