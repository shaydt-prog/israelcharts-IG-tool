#!/usr/bin/env python3
"""
IsraeliCharts — Instagram CAROUSEL Poster (Graph API)
Publishes output/slide_*.jpg as a carousel with caption.txt

Env vars:
  IG_USER_ID, IG_ACCESS_TOKEN
  IMAGE_BASE_URL — public base URL where slide_N.jpg files are reachable
                   e.g. https://raw.githubusercontent.com/USER/REPO/main/output
"""
import os, time, json, glob
import urllib.request, urllib.parse

GRAPH = "https://graph.facebook.com/v21.0"

def api(path, params, method="POST"):
    if method == "GET":
        url = f"{GRAPH}/{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
    else:
        req = urllib.request.Request(f"{GRAPH}/{path}",
              data=urllib.parse.urlencode(params).encode(), method="POST")
    with urllib.request.urlopen(req, timeout=60) as r:
        return json.loads(r.read().decode())

def wait_finished(cid, token, tries=20):
    for _ in range(tries):
        s = api(cid, {"fields": "status_code", "access_token": token}, "GET")
        if s.get("status_code") == "FINISHED": return True
        time.sleep(3)
    return False

def main():
    ig_user = os.environ["IG_USER_ID"]
    token   = os.environ["IG_ACCESS_TOKEN"]
    base    = os.environ["IMAGE_BASE_URL"].rstrip("/")

    outdir = os.path.join(os.path.dirname(__file__), "output")
    slides = sorted(glob.glob(os.path.join(outdir, "slide_*.jpg")),
                    key=lambda p: int(p.split("_")[-1].split(".")[0]))
    with open(os.path.join(outdir, "caption.txt"), encoding="utf-8") as f:
        caption = f.read()

    print(f"Publishing carousel: {len(slides)} slides")

    # 1. Create item containers
    children = []
    for p in slides:
        fname = os.path.basename(p)
        c = api(f"{ig_user}/media", {
            "image_url": f"{base}/{fname}",
            "is_carousel_item": "true",
            "access_token": token,
        })
        children.append(c["id"])
        print(f"  ✅ container for {fname}: {c['id']}")

    # 2. Wait for all items
    for cid in children:
        wait_finished(cid, token)

    # 3. Create carousel container
    carousel = api(f"{ig_user}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
        "access_token": token,
    })
    wait_finished(carousel["id"], token)

    # 4. Publish
    result = api(f"{ig_user}/media_publish", {
        "creation_id": carousel["id"],
        "access_token": token,
    })
    print(f"🎉 Carousel published! Media ID: {result['id']}")

if __name__ == "__main__":
    main()
