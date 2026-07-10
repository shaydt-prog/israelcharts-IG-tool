#!/usr/bin/env python3
"""
IsraeliCharts — Instagram Auto-Poster
Posts output/post.jpg + caption.txt to Instagram via the official Graph API.

Requirements (one-time setup — see README):
  IG_USER_ID      — Instagram Business account ID
  IG_ACCESS_TOKEN — Long-lived Page access token with instagram_content_publish
  IMAGE_URL       — public URL of the image (set automatically in GitHub Actions)

The Graph API can't accept file uploads directly — the image must be at a
public URL. In GitHub Actions we commit the image to the repo and use the
raw.githubusercontent.com URL.
"""
import os, sys, time, json
import urllib.request, urllib.parse

GRAPH = "https://graph.facebook.com/v21.0"

def api(path, params, method="POST"):
    url = f"{GRAPH}/{path}"
    data = urllib.parse.urlencode(params).encode()
    req = urllib.request.Request(url, data=data if method == "POST" else None,
                                 method=method)
    if method == "GET":
        url = f"{url}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def main():
    ig_user  = os.environ["IG_USER_ID"]
    token    = os.environ["IG_ACCESS_TOKEN"]
    img_url  = os.environ["IMAGE_URL"]

    cap_path = os.path.join(os.path.dirname(__file__), "output", "caption.txt")
    with open(cap_path, encoding="utf-8") as f:
        caption = f.read()

    print(f"1/3 Creating media container…")
    container = api(f"{ig_user}/media", {
        "image_url": img_url,
        "caption": caption,
        "access_token": token,
    })
    creation_id = container["id"]
    print(f"    container id: {creation_id}")

    # Wait for processing
    print("2/3 Waiting for processing…")
    for _ in range(20):
        status = api(creation_id, {"fields": "status_code", "access_token": token}, method="GET")
        if status.get("status_code") == "FINISHED":
            break
        time.sleep(3)

    print("3/3 Publishing…")
    result = api(f"{ig_user}/media_publish", {
        "creation_id": creation_id,
        "access_token": token,
    })
    print(f"✅ Published! Media ID: {result['id']}")

if __name__ == "__main__":
    main()
