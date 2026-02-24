import re
import sys

def analyze():
    path = r"AI_Employee_Vault\Logs\linkedin_posts\photo_button_not_found_20260223_010245.html"
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        print(f"Failed to read file: {e}")
        return

    print(f"File size: {len(content)} chars")

    # Search for modal markers
    modal_indicators = [
        'role="dialog"',
        'aria-modal="true"',
        'artdeco-modal',
        'Create a post',
        'Start a post'
    ]
    for mi in modal_indicators:
        if mi in content:
            print(f"FOUND modal indicator: {mi}")
            # print snippet
            idx = content.find(mi)
            print(f"  Snippet: {content[max(0, idx-50):idx+100]}")
        else:
            print(f"NOT FOUND: {mi}")

    # Search for media keywords
    media_keywords = ['photo', 'media', 'image', 'Photo', 'Media', 'Image', 'Add a photo']
    for kw in media_keywords:
        if kw in content:
            # Check if it's in a button-like tag
            indices = [m.start() for m in re.finditer(re.escape(kw), content)]
            print(f"FOUND keyword '{kw}' at {len(indices)} locations.")
            # Show first 3 snippet contexts
            for i in indices[:3]:
                snippet = content[max(0, i-100):i+100]
                print(f"  Context: {snippet}")
        else:
            pass # print(f"NOT FOUND: {kw}")

    # Search for post content
    post_content = "Sanity Check"
    if post_content in content:
        print(f"FOUND post content: {post_content}")
        idx = content.find(post_content)
        print(f"  Snippet: {content[max(0, idx-100):idx+200]}")
    else:
        print(f"NOT FOUND post content: {post_content}")

if __name__ == "__main__":
    analyze()
