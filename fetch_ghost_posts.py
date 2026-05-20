import os
import re
from datetime import datetime
import requests
from markdownify import markdownify as md

# Configuration
GHOST_URL = os.environ.get("GHOST_URL", "https://www.caseciter.com")
GHOST_API_KEY = os.environ.get("GHOST_API_KEY", "a8cb21b63d79d87a2c3e748550")

# Filters (Date format: YYYY-MM-DD)
START_DATE = os.environ.get("START_DATE", "2026-05-19")  
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
    """Compiles all matched posts into a single Markdown document with a TOC."""
    if not posts:
        print("No posts matched your filtering criteria.")
        return

    # Sort posts chronologically by publication date (oldest to newest)
    posts.sort(key=lambda x: x.get('published_at', ''))

    # Generate a unique dynamic filename matching current execution filters
    timestamp = datetime.now().strftime("%Y%m%d-%H%M%H")
    filename = f"backups/compiled_posts_{timestamp}.md"
    
    # Ensure backups directory exists
    os.makedirs("backups", exist_ok=True)

    # 1. Start Building the Document Header
    document_body = f"# Compiled Blog Posts Export\n"
    document_body += f"*Generated on {datetime.now().strftime('%Y-%m-%d %H:%M')}*\n\n"
    
    # 2. Generate Clickable Table of Contents
    document_body += "## Table of Contents\n"
    for idx, post in enumerate(posts, 1):
        title = post.get('title', 'Untitled')
        # Create a basic Markdown anchor slug for cross-linking
        anchor = re.sub(r'[^\w\s-]', '', title.lower()).replace(' ', '-')
        document_body += f"{idx}. [{title}](#{anchor})\n"
    
    document_body += "\n---\n\n"

    # 3. Append Each Post Body
    for post in posts:
        title = post.get('title', 'Untitled')
        published_at = post.get('published_at', '')
        date_short = published_at[:10] if published_at else "Unknown Date"
        html_content = post.get('html', '')
        
        # Extract tags array
        tags = [tag['name'] for tag in post.get('tags', [])]
        tags_str = ", ".join(tags) if tags else "None"
        
        # Convert HTML body to clean Markdown formatting
        markdown_body = md(html_content, heading_style="ATX")
        
        # Append single post structure
        document_body += f"## {title}\n"
        document_body += f"**Published Date:** {date_short} | **Tags:** `{tags_str}`\n\n"
        document_body += f"{markdown_body}\n\n"
        document_body += "---\n\n" # Visual divider between different items

    # Save to disk
    with open(filename, "w", encoding="utf-8") as f:
        f.write(document_body)
        
    print(f"Success! Compiled {len(posts)} posts into a single file: {filename}")

def main():
    print("Initializing compiled Ghost blog sync...")
    all_posts = fetch_all_posts()
    print(f"Retrieved {len(all_posts)} total posts from API.")
    
    matched_posts = [post for post in all_posts if matches_filters(post)]
    create_compiled_markdown(matched_posts)

if __name__ == "__main__":
    main()
