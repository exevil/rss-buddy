#!/usr/bin/env python3
import os
import json
import xml.etree.ElementTree as ET
from datetime import datetime
import shutil
import html

def generate_pages(input_dir='processed_feeds', output_dir='docs'):
    """Generate GitHub Pages from processed RSS feeds.
    
    Args:
        input_dir: Directory containing the processed XML feeds
        output_dir: Directory to output the GitHub Pages files
    """
    # Ensure output directory exists
    os.makedirs(output_dir, exist_ok=True)
    
    # Copy state file if it exists
    state_file = os.path.join(input_dir, 'processed_state.json')
    if os.path.exists(state_file):
        shutil.copy2(state_file, os.path.join(output_dir, 'processed_state.json'))
        print(f"State file copied to {output_dir}/processed_state.json")
    else:
        print("Warning: State file not found")
    
    # Copy feed files if they exist
    feed_count = 0
    if os.path.exists(input_dir):
        for file in os.listdir(input_dir):
            if file.endswith('.xml'):
                # Create a copy in the output directory
                src_path = os.path.join(input_dir, file)
                dst_path = os.path.join(output_dir, file)
                with open(src_path, 'rb') as src:
                    with open(dst_path, 'wb') as dst:
                        dst.write(src.read())
                feed_count += 1
                print(f"Copied feed: {file}")
    
    print(f"Total feeds copied: {feed_count}")
    
    # Create a metadata file with information about when the feeds were last processed
    metadata = {
        "last_processed": datetime.now().isoformat(),
        "feed_count": feed_count
    }
    
    with open(os.path.join(output_dir, 'metadata.json'), 'w') as f:
        json.dump(metadata, f, indent=2)
    
    feeds_list = []
    
    # Create HTML start
    html_content = '''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>rss-buddy processed feeds</title>
    <style>
        body {
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }
        h1 { border-bottom: 1px solid #eee; padding-bottom: 10px; }
        h2 { margin-top: 20px; font-size: 1.3em; }
        ul { list-style-type: none; padding: 0; }
        li {
            margin: 10px 0;
            padding: 10px;
            background-color: #f5f5f5;
            border-radius: 5px;
        }
        .digest {
            background-color: #e6f7ff;
            border-left: 4px solid #1890ff;
        }
        a { color: #0366d6; text-decoration: none; }
        a:hover { text-decoration: underline; }
        .feed-description {
            font-size: 0.9rem;
            color: #666;
            margin-top: 5px;
        }
        .updated {
            font-size: 0.8rem;
            color: #888;
            margin-top: 5px;
        }
        .state-info {
            margin-top: 20px;
            padding: 10px;
            background-color: #f0f0f0;
            border-radius: 5px;
            font-size: 0.9rem;
        }
        .explanation {
            margin: 20px 0;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 5px;
            border-left: 4px solid #4caf50;
        }
        .article-links {
            margin-top: 15px;
            padding: 10px;
            background-color: #f0f8ff;
            border-radius: 5px;
        }
    </style>
</head>
<body>
    <h1>rss-buddy Processed Feeds</h1>
    
    <div class="explanation">
        <p>These feeds are processed with AI to prioritize content:</p>
        <ul style="list-style-type: disc; padding-left: 20px;">
            <li><strong>Important articles</strong> are shown individually in full</li>
            <li><strong>Other articles</strong> are consolidated into a single digest item (highlighted in blue)</li>
        </ul>
    </div>
    
    <p>Below are the processed RSS feeds with AI-enhanced organization:</p>
    <ul>
'''
    
    if os.path.exists(input_dir) and os.path.isdir(input_dir):
        for file in os.listdir(input_dir):
            if file.endswith('.xml'):
                try:
                    feed_path = os.path.join(input_dir, file)
                    tree = ET.parse(feed_path)
                    root = tree.getroot()
                    
                    # Get feed title
                    title = root.find('.//title')
                    if title is not None:
                        title_text = title.text
                    else:
                        title_text = file.replace('.xml', '')
                    
                    # Get feed description
                    description = root.find('.//description')
                    description_text = description.text if description is not None else ''
                    
                    # Get feed link
                    link = root.find('.//link')
                    link_text = link.text if link is not None else '#'
                    
                    # Get feed items
                    items = root.findall('.//item')
                    
                    html_content += f'''
                    <li>
                        <a href="{html.escape(link_text)}">{html.escape(title_text)}</a>
                        <div class="feed-description">{html.escape(description_text)}</div>
                        <div class="updated">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
                    </li>
                    '''
                    
                    # Create detailed HTML feed page
                    feed_html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{html.escape(title_text)}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, Helvetica, Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
        }}
        h1 {{ border-bottom: 1px solid #eee; padding-bottom: 10px; }}
        h2 {{ margin-top: 30px; color: #333; }}
        h3 {{ margin-top: 20px; color: #555; }}
        a {{ color: #0366d6; text-decoration: none; }}
        a:hover {{ text-decoration: underline; }}
        .article {{
            margin: 20px 0;
            padding: 15px;
            background-color: #f9f9f9;
            border-radius: 5px;
        }}
        .digest {{
            margin: 30px 0;
            padding: 20px;
            background-color: #e6f7ff;
            border-left: 4px solid #1890ff;
            border-radius: 5px;
        }}
        .article-meta {{
            font-size: 0.8rem;
            color: #666;
            margin-bottom: 10px;
        }}
        .back-link {{
            display: inline-block;
            margin-bottom: 20px;
            padding: 5px 10px;
            background-color: #f0f0f0;
            border-radius: 3px;
        }}
    </style>
</head>
<body>
    <a href="index.html" class="back-link">← Back to all feeds</a>
    <h1>{html.escape(title_text)}</h1>
    <p>{html.escape(description_text)}</p>
    <p><small>Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</small></p>
    
    <div>
'''
                    
                    for item in items:
                        try:
                            item_title = item.find('title')
                            item_link = item.find('link')
                            item_description = item.find('description')
                            
                            if item_title is not None and item_link is not None:
                                title_text = item_title.text or ''
                                link_text = item_link.text or '#'
                                description_text = item_description.text if item_description is not None else ''
                                
                                # Check if this is a digest item
                                is_digest = 'digest' in title_text.lower()
                                
                                if is_digest:
                                    html_content += f'''
        <div class="digest">
            <h2><a href="{html.escape(link_text)}">{html.escape(title_text)}</a></h2>
            <div class="article-meta">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            <div>{html.escape(description_text)}</div>
'''
                                else:
                                    html_content += f'''
        <div class="article">
            <h2><a href="{html.escape(link_text)}">{html.escape(title_text)}</a></h2>
            <div class="article-meta">{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
            <div>{html.escape(description_text)}</div>
        </div>
'''
                        except Exception as e:
                            print(f"Error processing item in {file}: {e}")
                            continue
                    
                    feed_html += '''
    </div>
</body>
</html>
'''
                    
                    # Write feed HTML file
                    feed_html_file = os.path.join(output_dir, os.path.splitext(file)[0] + '.html')
                    with open(feed_html_file, 'w', encoding='utf-8') as f:
                        f.write(feed_html)
                    
                    feeds_list.append({
                        'title': title_text,
                        'link': link_text,
                        'description': description_text,
                        'item_count': len(items)
                    })
                    
                    html_content += f'''        <li>
            <a href="{os.path.splitext(file)[0] + '.html'}">{html.escape(title_text)}</a>
            <div class="feed-description">{html.escape(description_text)}</div>
            <div class="updated">Last updated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</div>
        </li>
'''
                except Exception as e:
                    print(f"Error processing {file}: {e}")
    
    # Add state information if available
    if os.path.exists(state_file):
        try:
            with open(state_file, 'r') as f:
                state_data = json.load(f)
                last_updated = state_data.get('last_updated', 'Unknown')
                feed_count = len(state_data.get('feeds', {}))
                
                html_content += f'''    </ul>
    <div class="state-info">
        <strong>State Information:</strong>
        <div>Last state update: {html.escape(last_updated)}</div>
        <div>Tracking {feed_count} feeds</div>
    </div>
'''
        except Exception as e:
            print(f"Error reading state file: {e}")
            html_content += '''    </ul>'''
    else:
        html_content += '''    </ul>'''
    
    # Finish HTML
    html_content += '''</body>
</html>'''
    
    # Write HTML file
    with open(os.path.join(output_dir, 'index.html'), 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    # Write JSON file
    with open(os.path.join(output_dir, 'feeds.json'), 'w', encoding='utf-8') as f:
        json.dump(feeds_list, f, indent=2)
    
    print(f"Generated GitHub Pages with {len(feeds_list)} feeds")
    return len(feeds_list)

if __name__ == "__main__":
    import sys
    
    input_dir = 'processed_feeds'
    output_dir = 'docs'
    
    # Allow override from command line
    if len(sys.argv) > 1:
        input_dir = sys.argv[1]
    if len(sys.argv) > 2:
        output_dir = sys.argv[2]
    
    generate_pages(input_dir, output_dir) 