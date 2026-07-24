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


class GraphAPIError(RuntimeError):
    """A non-2xx response from the Graph API, carrying the parsed error fields."""
    def __init__(self, message, http_status=None, code=None, subcode=None):
        super().__init__(message)
        self.http_status = http_status
        self.code = code
        self.subcode = subcode


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
        code = subcode = None
        try:
            err = json.loads(body).get("error", {})
            code, subcode = err.get("code"), err.get("error_subcode")
            detail = (f"code={code} subcode={subcode} "
                      f"type={err.get('type')} message={err.get('message')!r} "
                      f"fbtrace_id={err.get('fbtrace_id')}")
        except json.JSONDecodeError:
            detail = body
        raise GraphAPIError(f"Graph API {method} {path} -> HTTP {e.code}: {detail}",
                            http_status=e.code, code=code, subcode=subcode) from None


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


def latest_media_id(ig_user, token):
    """Return the id of the account's most recent media, or None if unreadable."""
    try:
        r = api(f"{ig_user}/media",
                {"fields": "id", "limit": "1", "access_token": token}, "GET")
        data = r.get("data", [])
        return data[0]["id"] if data else None
    except GraphAPIError as e:
        print(f"  ⚠️  could not read latest media: {e}")
        return None


def publish_carousel(ig_user, creation_id, token, attempts=3):
    """Publish the carousel container.

    media_publish is NOT idempotent, and the Graph API can publish server-side
    while still returning an error to the caller. So on any error we verify
    whether the post actually went live (by watching the account's most-recent
    media id) before deciding to retry — this prevents duplicate posts. We also
    refuse to retry on rate-limit errors, which would only burn more quota.
    """
    before = latest_media_id(ig_user, token)
    delay = 15
    for attempt in range(1, attempts + 1):
        try:
            result = api(f"{ig_user}/media_publish",
                         {"creation_id": creation_id, "access_token": token})
            return result["id"]
        except GraphAPIError as e:
            print(f"  ⚠️  media_publish failed (attempt {attempt}/{attempts}): {e}")

            # Give Instagram a moment, then check whether it published anyway.
            time.sleep(min(delay, 15))
            after = latest_media_id(ig_user, token)
            if before is not None and after is not None and after != before:
                print(f"  ✅ media actually published despite the error: {after}")
                return after

            # If we couldn't establish a baseline, we can't safely retry without
            # risking a duplicate. Bail out and let a human check the account.
            if before is None:
                sys.exit("❌ media_publish failed and the account's media list "
                         "was unreadable, so publish success can't be verified. "
                         "Not retrying to avoid a duplicate post — check the "
                         "account manually.")

            # Rate limited: retrying shortly will just fail again and consume
            # more quota. The container stays valid; the next scheduled run can
            # publish a fresh one. Abort cleanly.
            if e.code == 4:
                sys.exit(f"❌ Rate limited by the Graph API (code 4: application "
                         f"request limit reached). Not retrying to avoid burning "
                         f"more quota. creation_id={creation_id}")

            if attempt == attempts:
                raise
            delay *= 2


def main():
    ig_user = os.environ["IG_USER_ID"]
    token   = os.environ["IG_ACCESS_TOKEN"]
    base    = os.environ["IMAGE_BASE_URL"].rstrip("/")

    # Cache-buster appended to every image URL. The slide files always live at
    # the same paths (slide_1.jpg …), and Instagram caches images by URL — as
    # does the raw.githubusercontent.com CDN — so without this the Graph API can
    # ingest a *previous day's* cached bytes and post stale images. A unique
    # per-run token forces a fresh fetch of the just-committed slides.
    bust = os.environ.get("CACHE_BUST") or str(int(time.time()))

    outdir = os.path.join(os.path.dirname(__file__), "output")
    slides = sorted(glob.glob(os.path.join(outdir, "slide_*.jpg")),
                    key=lambda p: int(p.split("_")[-1].split(".")[0]))
    with open(os.path.join(outdir, "caption.txt"), encoding="utf-8") as f:
        caption = f.read()

    print(f"Publishing carousel: {len(slides)} slides (cache-bust v={bust})")

    # 1. Create item containers
    children = []
    for p in slides:
        fname = os.path.basename(p)
        c = api(f"{ig_user}/media", {
            "image_url": f"{base}/{fname}?v={bust}",
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

    # 5. Publish (idempotency-safe — see publish_carousel).
    media_id = publish_carousel(ig_user, carousel["id"], token)
    print(f"🎉 Carousel published! Media ID: {media_id}")


if __name__ == "__main__":
    main()
