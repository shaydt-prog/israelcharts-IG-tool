#!/usr/bin/env python3
"""
IsraeliCharts — Instagram CAROUSEL Poster (Graph API)
Publishes output/slide_*.jpg as a carousel with caption.txt

Env vars:
  IG_USER_ID, IG_ACCESS_TOKEN
  IMAGE_BASE_URL — public base URL where slide_N.jpg files are reachable
                   e.g. https://raw.githubusercontent.com/USER/REPO/main/output
"""
import os, sys, time, json, glob
import urllib.request, urllib.parse, urllib.error

GRAPH = "https://graph.facebook.com/v21.0"

def api(path, params, method="POST"):
    if method == "GET":
        url = f"{GRAPH}/{path}?{urllib.parse.urlencode(params)}"
        req = urllib.request.Request(url)
    else:
        req = urllib.request.Request(f"{GRAPH}/{path}",
              data=urllib.parse.urlencode(params).encode(), method="POST")
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            return json.loads(r.read().decode())
    except urllib.error.HTTPError as e:
        # The Graph API returns a JSON body describing the error even on 4xx/5xx
        # responses. urllib raises before we can see it, so surface it here.
        body = e.read().decode("utf-8", "replace")
        try:
            err = json.loads(body).get("error", {})
            detail = (f"code={err.get('code')} subcode={err.get('error_subcode')} "
                      f"type={err.get('type')} message={err.get('message')!r} "
                      f"fbtrace_id={err.get('fbtrace_id')}")
        except json.JSONDecodeError:
            detail = body
        raise RuntimeError(f"Graph API {method} {path} -> HTTP {e.code}: {detail}") from None

def wait_finished(cid, token, tries=30):
    """Poll a container until status_code == FINISHED. Return True on success."""
    for _ in range(tries):
        s = api(cid, {"fields": "status_code,status", "access_token": token}, "GET")
        code = s.get("status_code")
        if code == "FINISHED":
            return True
        if code == "ERROR":
            print(f"  ⚠️  container {cid} entered ERROR state: {s.get('status')}")
            return False
        time.sleep(3)
    print(f"  ⚠️  container {cid} not FINISHED after {tries} polls")
    return False

def api_with_retry(path, params, method="POST", attempts=4):
    """Call api() with exponential backoff for transient failures (e.g. the
    eventual-consistency 403 the Graph API can return right after a container
    reports FINISHED)."""
    delay = 3
    for attempt in range(1, attempts + 1):
        try:
            return api(path, params, method)
        except RuntimeError as e:
            if attempt == attempts:
                raise
            print(f"  ⚠️  {path} failed (attempt {attempt}/{attempts}): {e}")
            print(f"      retrying in {delay}s...")
            time.sleep(delay)
            delay *= 2

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

    # 2. Wait for all items to finish processing before building the carousel.
    for cid, p in zip(children, slides):
        if not wait_finished(cid, token):
            sys.exit(f"❌ Item container {cid} ({os.path.basename(p)}) "
                     f"never reached FINISHED — aborting before publish.")

    # 3. Create carousel container
    carousel = api(f"{ig_user}/media", {
        "media_type": "CAROUSEL",
        "children": ",".join(children),
        "caption": caption,
        "access_token": token,
    })
    print(f"  ✅ carousel container: {carousel['id']}")

    # 4. Ensure the carousel container is fully processed. Publishing an
    #    unfinished container is a common cause of media_publish failures.
    if not wait_finished(carousel["id"], token):
        sys.exit(f"❌ Carousel container {carousel['id']} never reached "
                 f"FINISHED — aborting before publish.")

    # 5. Publish (with retry — media_publish can transiently 403 right after
    #    the container reports FINISHED).
    result = api_with_retry(f"{ig_user}/media_publish", {
        "creation_id": carousel["id"],
        "access_token": token,
    })
    print(f"🎉 Carousel published! Media ID: {result['id']}")

if __name__ == "__main__":
    main()
