import os
import re
from datetime import datetime
import requests
from markdownify import markdownify as md

# Configuration - Loaded from environment variables for security in GitHub Actions
GHOST_URL = os.environ.get("GHOST_URL", "https://www.caseciter.com")
GHOST_API_KEY = os.environ.get("GHOST_API_KEY", "a8cb21b63d79d87a2c3e748550")

# Filters (Can be left empty if no filtering is needed)
# Date format: YYYY-MM-DD
START_DATE = os.environ.get("START_DATE", "2026-01-01")  
END_DATE = os.environ.get("END_DATE", "2026-12-31")      
KEYWORD_FILTER = os.environ.get("KEYWORD_FILTER", "")   # e.g., "judgment" or "Kerala"

def slugify(text):
    """Saves filenames safely by removing special characters."""
    text = text.lower()
    text = re.sub(r'[^\w\s-]', '', text)
    return re.sub(r'[-\s]+', '-', text).strip('-')

def fetch_all_posts():
    """Fetches all posts from the Ghost Content API using pagination."""
    posts = []
    page = 1
    limit = 15  # Default ghost api limit per page
    
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
            
            # Check pagination meta to see if we reached the end
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
    # 1. Parse Published Date
    pub_date_str = post.get('published_at')
    if not pub_date_str:
        return False
    
    # Ghost API returns ISO 8601 strings (e.g., 2026-05-20T14:59:00.000Z)
    post_date = datetime.fromisoformat(pub_date_str.replace('Z', '+00:00')).date()
    
    if START_DATE:
        start = datetime.strptime(START_DATE, "%Y-%m-%d").date()
        if post_date < start:
            return False
            
    if END_DATE:
        end = datetime.strptime(END_DATE, "%Y-%m-%d").date()
        if post_date > end:
            return False
            
    # 2. Keyword Filtering (Searches Title and Content)
    if KEYWORD_FILTER:
        keyword = KEYWORD_FILTER.lower()
        title = post.get('title', '').lower()
        html_content = post.get('html', '').lower()
        
        if keyword not in title and keyword not in html_content:
            return False
            
    return True

def save_to_markdown(post):
    """Converts post HTML content to Markdown and writes it to a file."""
    title = post.get('title', 'Untitled')
    published_at = post.get('published_at', '')
    html_content = post.get('html', '')
    slug = post.get('slug', slugify(title))
    
    # Convert HTML body to Markdown
    markdown_content = md(html_content, heading_style="ATX")
    
    # Extract tags
    tags = [tag['name'] for tag in post.get('tags', [])]
    tags_str = ", ".join(tags)
    
    # Build Hugo/Jekyll style Front Matter header
    front_matter = f"---\n"
    front_matter += f"title: \"{title}\"\n"
    front_matter += f"date: {published_at}\n"
    front_matter += f"slug: {slug}\n"
    front_matter += f"tags: [{tags_str}]\n"
    front_matter += f"---\n\n"
    
    full_output = front_matter + markdown_content
    
    # Ensure delivery folder exists
    os.makedirs("backups", exist_ok=True)
    
    # Create filename prefix matching date for cleaner directory sorting
    date_prefix = published_at[:10] if published_at else "unknown-date"
    filename = f"backups/{date_prefix}-{slug}.md"
    
    with open(filename, "w", encoding="utf-8") as f:
        f.write(full_output)
        
    print(f" Saved: {filename}")

def main():
    print("Initializing Ghost blog backup sync...")
    all_posts = fetch_all_posts()
    print(f"Retrieved {len(all_posts)} total posts from API.")
    
    saved_count = 0
    for post in all_posts:
        if matches_filters(post):
            save_to_markdown(post)
            saved_count += 1
            
    print(f"\nTask Complete! Successfully exported {saved_count} posts matching filters.")

if __name__ == "__main__":
    main()
