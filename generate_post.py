#!/usr/bin/env python3
"""
IsraeliCharts — Daily Instagram Post Generator
Creates a branded 1080x1350 "On This Day" image + caption from today_facts.json
Usage: python generate_post.py [MM-DD]   (defaults to today, Israel time)
Outputs: post.jpg + caption.txt in ./output/
"""
import json, os, sys, textwrap
from datetime import datetime
from zoneinfo import ZoneInfo
from PIL import Image, ImageDraw, ImageFont

# ── CONFIG ──────────────────────────────────────────────────
W, H = 1080, 1350                    # IG portrait 4:5 (max feed real estate)
NAVY   = (13, 20, 40)
NAVY2  = (23, 33, 60)
RED    = (204, 0, 0)
GOLD   = (255, 184, 0)
WHITE  = (255, 255, 255)
GREY   = (150, 160, 180)
SITE   = "israelicharts.com"
HANDLE = "@israelicharts"            # change to your IG handle

FONT_DIR = "/usr/share/fonts/truetype/dejavu"
def font(size, bold=False):
    name = "DejaVuSans-Bold.ttf" if bold else "DejaVuSans.ttf"
    return ImageFont.truetype(os.path.join(FONT_DIR, name), size)

def fit_text(draw, text, max_width, size, bold=True, min_size=28):
    """Shrink font until text fits max_width."""
    while size > min_size:
        f = font(size, bold)
        if draw.textlength(text, font=f) <= max_width:
            return f, size
        size -= 2
    return font(min_size, bold), min_size

def generate(md=None):
    tz = ZoneInfo("Asia/Jerusalem")
    now = datetime.now(tz)
    if md is None:
        md = now.strftime("%m-%d")

    with open(os.path.join(os.path.dirname(__file__), "today_facts.json"), encoding="utf-8") as f:
        TF = json.load(f)

    facts = TF.get(md, [])
    if not facts:
        # No chart aired on this exact calendar day — use nearest available day
        keys = sorted(TF.keys())
        md = min(keys, key=lambda k: abs(int(k[:2])*31+int(k[3:]) - (int(md[:2])*31+int(md[3:]))))
        facts = TF[md]

    # Pick up to 4 facts, most recent years first (more recognizable)
    facts = sorted(facts, key=lambda f: -f["year"])[:4]

    # ── CANVAS ──────────────────────────────────────────────
    img = Image.new("RGB", (W, H), NAVY)
    d = ImageDraw.Draw(img)

    # Background gradient stripes
    for y in range(H):
        blend = y / H
        r = int(NAVY[0] + (NAVY2[0]-NAVY[0]) * blend)
        g = int(NAVY[1] + (NAVY2[1]-NAVY[1]) * blend)
        b = int(NAVY[2] + (NAVY2[2]-NAVY[2]) * blend)
        d.line([(0, y), (W, y)], fill=(r, g, b))

    # Top red bar
    d.rectangle([0, 0, W, 14], fill=RED)

    # Header
    month_name = datetime.strptime(md, "%m-%d").strftime("%B %-d") if os.name != 'nt' else datetime.strptime(md, "%m-%d").strftime("%B %d")
    d.text((70, 70),  "ON THIS DAY", font=font(38, True), fill=RED)
    d.text((70, 125), month_name.upper(), font=font(86, True), fill=WHITE)
    d.text((70, 235), "IN ISRAELI CHART HISTORY", font=font(30, True), fill=GREY)

    # Flag emoji substitute: red/white/blue square accent
    d.rectangle([W-170, 70, W-70, 170], outline=RED, width=4)
    d.text((W-152, 88), "🇮🇱" if False else "IL", font=font(52, True), fill=WHITE)

    # ── FACT CARDS ──────────────────────────────────────────
    y = 330
    card_h = (H - y - 160) // len(facts) - 24

    for fact in facts:
        n1 = fact["n1"]
        yr, ago = fact["year"], fact["ago"]

        # Card background
        d.rounded_rectangle([50, y, W-50, y+card_h], radius=22, fill=(255,255,255,10), outline=(255,255,255,30))
        d.rounded_rectangle([50, y, W-50, y+card_h], radius=22, outline=(60,70,100), width=2)

        # Year badge
        d.rounded_rectangle([80, y+24, 260, y+82], radius=14, fill=RED)
        d.text((170, y+53), str(yr), font=font(40, True), fill=WHITE, anchor="mm")

        # "#1 SONG" label + years ago
        d.text((285, y+34), "WAS #1 IN ISRAEL", font=font(24, True), fill=GOLD)
        d.text((W-90, y+34), f"{ago} years ago", font=font(22), fill=GREY, anchor="ra")

        # Song title — auto-fit
        title = n1["t"]
        tf_, _ = fit_text(d, title, W-200, 46, bold=True)
        d.text((80, y+card_h//2 + 8), title, font=tf_, fill=WHITE, anchor="lm")

        # Artist
        af_, _ = fit_text(d, n1["a"], W-200, 32, bold=False)
        d.text((80, y+card_h - 34), n1["a"], font=af_, fill=(120, 190, 255), anchor="lm")

        y += card_h + 24

    # ── FOOTER ──────────────────────────────────────────────
    d.rectangle([0, H-90, W, H], fill=RED)
    d.text((70, H-45), SITE, font=font(34, True), fill=WHITE, anchor="lm")
    d.text((W-70, H-45), HANDLE, font=font(30), fill=WHITE, anchor="rm")

    # ── SAVE ────────────────────────────────────────────────
    outdir = os.path.join(os.path.dirname(__file__), "output")
    os.makedirs(outdir, exist_ok=True)
    img_path = os.path.join(outdir, "post.jpg")
    img.save(img_path, "JPEG", quality=92)

    # ── CAPTION ─────────────────────────────────────────────
    lines = [f"📻 ON THIS DAY in Israeli chart history — {month_name}\n"]
    for fact in facts:
        n1 = fact["n1"]
        lines.append(f"🏆 {fact['year']}: \"{n1['t']}\" by {n1['a']} was the #1 song in Israel ({fact['ago']} years ago)")
        hne = fact.get("hne")
        if hne:
            lines.append(f"   🆕 New that week: \"{hne['t']}\" by {hne['a']} (#{hne['pos']})")
    lines.append(f"\n🔎 Explore 36 years of Israeli chart history (1961–1997) → {SITE}")
    lines.append("\n#IsraeliCharts #OnThisDay #MusicHistory #ChartHistory #Israel #מצעד #רשתגימל "
                 "#80smusic #90smusic #retromusic #nostalgia #musicfacts #numberone #popmusic")
    caption = "\n".join(lines)

    cap_path = os.path.join(outdir, "caption.txt")
    with open(cap_path, "w", encoding="utf-8") as f:
        f.write(caption)

    print(f"✅ Generated: {img_path}")
    print(f"✅ Caption:   {cap_path}")
    return img_path, cap_path

if __name__ == "__main__":
    md = sys.argv[1] if len(sys.argv) > 1 else None
    generate(md)
