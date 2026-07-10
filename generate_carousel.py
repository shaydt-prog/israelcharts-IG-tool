#!/usr/bin/env python3
"""
IsraeliCharts — Daily Instagram CAROUSEL Generator
Slide 1: "Guess what was #1?" teaser
Slides 2-6: up to 5 facts, each with real album artwork (iTunes API)

Usage: python generate_carousel.py [MM-DD]
Outputs: output/slide_1.jpg ... slide_N.jpg + caption.txt
"""
import json, os, sys, io, re
import urllib.request, urllib.parse
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont, ImageFilter

W, H = 1080, 1350
NAVY, NAVY2 = (13, 20, 40), (23, 33, 60)
RED, GOLD, WHITE, GREY, BLUE = (204,0,0), (255,184,0), (255,255,255), (150,160,180), (120,190,255)
SITE, HANDLE = "israelcharts.com", "@israelmusiccharts"

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
def font(size, bold=False):
    return ImageFont.truetype(os.path.join(FONT_DIR,
        "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"), size)

def fit(d, text, max_w, size, bold=True, min_size=26):
    while size > min_size:
        f = font(size, bold)
        if d.textlength(text, font=f) <= max_w: return f
        size -= 2
    return font(min_size, bold)

def wrap_text(d, text, f, max_w):
    words, lines, cur = text.split(), [], ""
    for w_ in words:
        t = (cur + " " + w_).strip()
        if d.textlength(t, font=f) <= max_w: cur = t
        else: lines.append(cur); cur = w_
    if cur: lines.append(cur)
    return lines

def gradient_bg(img):
    d = ImageDraw.Draw(img)
    for y in range(H):
        b = y / H
        d.line([(0,y),(W,y)], fill=(
            int(NAVY[0]+(NAVY2[0]-NAVY[0])*b),
            int(NAVY[1]+(NAVY2[1]-NAVY[1])*b),
            int(NAVY[2]+(NAVY2[2]-NAVY[2])*b)))
    return d

# ── Album art fetch (iTunes API, no key needed) ─────────────
def clean_title(t):
    """Strip parentheticals for better search hits."""
    return re.sub(r'\s*[\(\[].*?[\)\]]', '', t).strip()

def get_artwork(artist, title):
    for query in (f"{artist} {title}", f"{artist} {clean_title(title)}", f"{clean_title(title)} {artist}"):
        try:
            q = urllib.parse.quote(query)
            url = f"https://itunes.apple.com/search?term={q}&entity=song&limit=1"
            with urllib.request.urlopen(url, timeout=10) as r:
                data = json.loads(r.read().decode())
            if data["resultCount"] > 0:
                art_url = data["results"][0]["artworkUrl100"].replace("100x100", "600x600")
                with urllib.request.urlopen(art_url, timeout=15) as r:
                    return Image.open(io.BytesIO(r.read())).convert("RGB")
        except Exception:
            continue
    return None

# ── Slide 1: Teaser ─────────────────────────────────────────
def make_teaser(md_label, n_facts, first_year, last_year):
    img = Image.new("RGB", (W, H), NAVY)
    d = gradient_bg(img)
    d.rectangle([0,0,W,14], fill=RED)

    # Big vinyl record graphic
    cx, cy, r = W//2, 430, 240
    for ring in range(r, 60, -18):
        shade = 18 + (r-ring)//6
        d.ellipse([cx-ring, cy-ring, cx+ring, cy+ring], outline=(shade,shade+6,shade+18), width=5)
    d.ellipse([cx-70, cy-70, cx+70, cy+70], fill=RED)
    d.ellipse([cx-12, cy-12, cx+12, cy+12], fill=NAVY)
    d.text((cx, cy-100+35), "#1", font=font(58, True), fill=WHITE, anchor="mm")

    d.text((W//2, 105), "🎵 POP QUIZ", font=font(40, True), fill=GOLD, anchor="mm")

    y = 740
    d.text((W//2, y), "GUESS WHAT WAS", font=font(58, True), fill=WHITE, anchor="mm")
    d.text((W//2, y+80), "#1 IN ISRAEL", font=font(84, True), fill=RED, anchor="mm")
    d.text((W//2, y+175), f"ON {md_label.upper()}?", font=font(58, True), fill=WHITE, anchor="mm")

    d.text((W//2, y+290), f"{n_facts} answers from {first_year}–{last_year} inside", font=font(32), fill=GREY, anchor="mm")
    d.text((W//2, y+360), "SWIPE →", font=font(44, True), fill=GOLD, anchor="mm")

    d.rectangle([0, H-90, W, H], fill=RED)
    d.text((70, H-45), SITE, font=font(34, True), fill=WHITE, anchor="lm")
    d.text((W-70, H-45), HANDLE, font=font(30), fill=WHITE, anchor="rm")
    return img

# ── Fact slide with album art ───────────────────────────────
def make_fact_slide(fact, md_label, slide_no, total):
    n1 = fact["n1"]
    art = get_artwork(n1["a"], n1["t"])

    img = Image.new("RGB", (W, H), NAVY)

    if art:
        # Blurred art as background
        bg = art.resize((W, W)).filter(ImageFilter.GaussianBlur(40))
        bg_full = Image.new("RGB", (W, H), NAVY)
        bg_full.paste(bg, (0, (H-W)//2))
        # Dark overlay
        overlay = Image.new("RGB", (W, H), NAVY)
        img = Image.blend(bg_full, overlay, 0.72)

    d = ImageDraw.Draw(img)
    d.rectangle([0,0,W,14], fill=RED)

    # Header
    header = "THIS WEEK" if fact.get("approx") else "ON THIS DAY"
    d.text((70, 60), f"{header} · {md_label.upper()}", font=font(30, True), fill=GOLD)
    d.text((W-70, 60), f"{slide_no}/{total}", font=font(30, True), fill=GREY, anchor="ra")

    # Album art centered
    art_size = 560
    ax, ay = (W-art_size)//2, 150
    if art:
        art_sq = art.resize((art_size, art_size))
        # subtle border
        d.rectangle([ax-6, ay-6, ax+art_size+6, ay+art_size+6], fill=WHITE)
        img.paste(art_sq, (ax, ay))
        d = ImageDraw.Draw(img)
    else:
        # Fallback: vinyl placeholder
        d.rounded_rectangle([ax, ay, ax+art_size, ay+art_size], radius=20, fill=NAVY2, outline=(60,70,100), width=3)
        cx, cy = ax+art_size//2, ay+art_size//2
        for ring in range(220, 40, -22):
            d.ellipse([cx-ring, cy-ring, cx+ring, cy+ring], outline=(40,48,72), width=4)
        d.ellipse([cx-55, cy-55, cx+55, cy+55], fill=RED)

    y = ay + art_size + 55

    # Year badge + "#1 IN ISRAEL"
    d.rounded_rectangle([W//2-210, y, W//2-30, y+64], radius=14, fill=RED)
    d.text((W//2-120, y+32), str(fact["year"]), font=font(42, True), fill=WHITE, anchor="mm")
    d.text((W//2-10, y+32), "WAS #1 IN ISRAEL", font=font(30, True), fill=GOLD, anchor="lm")

    y += 105
    # Song title (wrapped, centered)
    tf = fit(d, n1["t"], W-160, 54)
    for line in wrap_text(d, n1["t"], tf, W-160)[:2]:
        d.text((W//2, y), line, font=tf, fill=WHITE, anchor="mm")
        y += tf.size + 12

    # Artist
    af = fit(d, n1["a"], W-160, 38, bold=False)
    d.text((W//2, y+8), n1["a"], font=af, fill=BLUE, anchor="mm")
    y += af.size + 40

    # Fact line
    fact_txt = f"{fact['ago']} years ago " + ("this week" if fact.get("approx") else "today")
    hne = fact.get("hne")
    d.text((W//2, y), fact_txt, font=font(28), fill=GREY, anchor="mm")
    if hne and y < H-190:
        y += 44
        new_txt = f"🆕 New that week: \"{hne['t'][:34]}\" — {hne['a'][:26]} (#{hne['pos']})"
        nf = fit(d, new_txt, W-140, 26, bold=False, min_size=20)
        d.text((W//2, y), new_txt, font=nf, fill=(180,190,210), anchor="mm")

    d.rectangle([0, H-90, W, H], fill=RED)
    d.text((70, H-45), SITE, font=font(34, True), fill=WHITE, anchor="lm")
    d.text((W-70, H-45), HANDLE, font=font(30), fill=WHITE, anchor="rm")
    return img

# ── Main ────────────────────────────────────────────────────
def generate(md=None):
    tz = ZoneInfo("Asia/Jerusalem")
    now = datetime.now(tz)
    if md is None: md = now.strftime("%m-%d")

    with open(os.path.join(os.path.dirname(__file__), "today_facts.json"), encoding="utf-8") as f:
        TF = json.load(f)

    facts = TF.get(md, [])
    if not facts:
        keys = sorted(TF.keys())
        md = min(keys, key=lambda k: abs(int(k[:2])*31+int(k[3:]) - (int(md[:2])*31+int(md[3:]))))
        facts = TF[md]

    # Pad thin dates from neighboring days: charts were weekly, so a #1
    # from a day or two away was still #1 on this date. Mark those facts
    # so slides say "this week" instead of "today".
    if len(facts) < 5:
        base_dt = datetime.strptime(f"2000-{md}", "%Y-%m-%d")  # leap year keeps 02-29 valid
        used_years = {f["year"] for f in facts}
        for off in (1, -1, 2, -2, 3, -3):
            if len(facts) >= 5: break
            key = (base_dt + timedelta(days=off)).strftime("%m-%d")
            for f in TF.get(key, []):
                if len(facts) >= 5: break
                if f["year"] in used_years: continue
                f = dict(f, approx=True)
                facts.append(f); used_years.add(f["year"])

    facts = sorted(facts, key=lambda f: -f["year"])[:5]   # up to 5, recent first
    try:
        md_label = datetime.strptime(md, "%m-%d").strftime("%B %-d")
    except ValueError:
        md_label = datetime.strptime(md, "%m-%d").strftime("%B %d").replace(" 0", " ")

    outdir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(outdir, exist_ok=True)
    # Clean old slides
    for f_ in os.listdir(outdir):
        if f_.startswith("slide_"): os.remove(os.path.join(outdir, f_))

    paths = []

    # Slide 1: teaser
    years = [f["year"] for f in facts]
    teaser = make_teaser(md_label, len(facts), min(years), max(years))
    p = os.path.join(outdir, "slide_1.jpg")
    teaser.save(p, "JPEG", quality=92); paths.append(p)
    print(f"✅ slide_1.jpg (teaser)")

    # Slides 2..N: facts with album art
    total = len(facts)
    for i, fact in enumerate(facts):
        slide = make_fact_slide(fact, md_label, i+1, total)
        p = os.path.join(outdir, f"slide_{i+2}.jpg")
        slide.save(p, "JPEG", quality=92); paths.append(p)
        art_status = "with art" 
        print(f"✅ slide_{i+2}.jpg — {fact['year']}: {fact['n1']['t'][:40]}")

    # Caption
    lines = [f"🎵 GUESS WHAT WAS #1 IN ISRAEL — {md_label}? Swipe to find out! 👉\n"]
    for fact in facts:
        n1 = fact["n1"]
        when = f"{fact['ago']} years ago" + (" this week" if fact.get("approx") else "")
        lines.append(f"🏆 {fact['year']}: \"{n1['t']}\" — {n1['a']} ({when})")
    lines.append(f"\n🔎 Explore the full archive: 1,548 weekly charts, 1961–1997 → {SITE}")
    lines.append("\n#IsraeliCharts #OnThisDay #MusicHistory #ChartHistory #Israel #מצעד #רשתגימל "
                 "#80smusic #90smusic #70smusic #retromusic #nostalgia #musicfacts #numberone #vinyl #popmusic")
    with open(os.path.join(outdir, "caption.txt"), "w", encoding="utf-8") as f:
        f.write("\n".join(lines))
    print(f"✅ caption.txt")
    return paths

if __name__ == "__main__":
    generate(sys.argv[1] if len(sys.argv) > 1 else None)
