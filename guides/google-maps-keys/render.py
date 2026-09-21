#!/usr/bin/env python3
"""Render the customer "Setting up your Google Maps keys" PDF.

usage: python3 render.py values.json out.pdf

values.json keys (all strings):
  AGENT_NAME   full trading name, e.g. "Carvels Lettings"
  AGENT_SHORT  short name used in the key names, e.g. "Carvels"
  DOMAIN       bare domain, no www, e.g. "carvels.co.uk"
  SERVER_IP    IP the site's server-side Places calls come from (OVH Live UK: 51.89.218.35)
  REPLY_EMAIL  where the customer sends the keys, e.g. "dave@agenthelp.uk"
  PHONE        phone number for "give me a call"
  BRAND        customer brand colour, e.g. "#a03058"
  BRAND_TINT   pale tint of it for the boxes, e.g. "#f4e3e9"
  NO_PLACES    optional "1" to drop Key 2 (site has no nearby schools/transport)

Assets (template.html + 4 PNGs) are read from the folder this script sits in,
or fetched from the pwdp-assets repo on jsDelivr when missing.
Needs Pillow. PDF via Playwright if installed, else headless Chrome/Edge.
"""
import json, os, re, shutil, subprocess, sys, tempfile, urllib.request

CDN = "https://cdn.jsdelivr.net/gh/rcdc69/pwdp-assets@main/guides/google-maps-keys/"
ASSETS = ["template.html", "websites-restriction.png", "api-maps-javascript.png",
          "api-places-new.png", "ip-restrictions-blank.png"]
REQUIRED = ["AGENT_NAME", "AGENT_SHORT", "DOMAIN", "SERVER_IP", "REPLY_EMAIL", "PHONE", "BRAND", "BRAND_TINT"]


def fetch_assets(work):
    here = os.path.dirname(os.path.abspath(__file__))
    for a in ASSETS:
        src = os.path.join(here, a)
        if os.path.exists(src):
            shutil.copy(src, os.path.join(work, a))
        else:
            urllib.request.urlretrieve(CDN + a, os.path.join(work, a))


def draw_ip(work, ip):
    # The screenshot is Dave's own Google Cloud console (dark theme) with the IP
    # cell blanked; the IP is drawn back in the console's text colour and size.
    from PIL import Image, ImageDraw, ImageFont
    im = Image.open(os.path.join(work, "ip-restrictions-blank.png")).convert("RGB")
    font = None
    for f in ["/usr/share/fonts/truetype/liberation/LiberationSans-Regular.ttf",
              "/System/Library/Fonts/Supplemental/Arial.ttf", "/Library/Fonts/Arial.ttf",
              "C:/Windows/Fonts/arial.ttf"]:
        if os.path.exists(f):
            font = ImageFont.truetype(f, 14); break
    ImageDraw.Draw(im).text((75, 516), ip, font=font or ImageFont.load_default(), fill=(189, 193, 198))
    im.save(os.path.join(work, "ip-restrictions.png"))


def fill(work, v):
    s = open(os.path.join(work, "template.html"), encoding="utf-8").read()
    if v.get("NO_PLACES") == "1":
        s = re.sub(r"<h2>Part 4\..*?(?=<h2>Part 5\.)", "", s, flags=re.S)
        s = s.replace("<li>Create Key 2 (for schools and transport) and lock it to our server</li>", "")
        s = s.replace("<li>Switch on the two Google services the website uses</li>", "<li>Switch on the Google service the website uses</li>")
        s = s.replace(", and the schools and transport lookups have their own free allowance. A website of your size stays well inside both",
                      ". A website of your size stays well inside that")
        s = re.sub(r"<li>Go back to the Library and search for.*?</li>\s*<li>Click <b>Enable</b>.*?</li>", "", s, flags=re.S)
        s = re.sub(r"<li>Do the same for <b>.*? website server</b>.*?</li>", "", s, flags=re.S)
        s = s.replace("The map on the property listings and the nearby schools and transport on each property page are provided by Google.", "The map on the property listings is provided by Google.")
        s = s.replace("Part 2. Switch on the two services", "Part 2. Switch on the service")
        s = s.replace("We set both keys up properly in Parts 3 and 4.", "We set the key up properly in Part 3.")
        s = s.replace("you will now see both keys listed by the names you gave them", "you will now see the key listed by the name you gave it")
        s = s.replace("You will be asked to do four things:", "You will be asked to do three things:")
        s = s.replace("Create Key 1 (for the map)", "Create the key (for the map)").replace("Part 3. Key 1: the map", "Part 3. The map key")
        s = s.replace("Send me the two keys", "Send me the key").replace("email me the two keys", "email me the key")
        s = s.replace("need two \"keys\"", "need a \"key\"").replace("Once you send them to me", "Once you send it to me")
        s = s.replace("Key 1 only works on your website and Key 2 only works from our server, so they are no use", "the key only works on your website, so it is no use")
    for k, val in v.items():
        s = s.replace("{{" + k + "}}", val)
    left = sorted(set(re.findall(r"{{[A-Z_]+}}", s)))
    if left:
        sys.exit(f"unfilled placeholders: {left}")
    out = os.path.join(work, "guide.html")
    open(out, "w", encoding="utf-8").write(s)
    return out


def to_pdf(html, pdf):
    try:
        from playwright.sync_api import sync_playwright
        with sync_playwright() as p:
            b = p.chromium.launch(); pg = b.new_page()
            pg.goto("file://" + os.path.abspath(html)); pg.wait_for_timeout(500)
            pg.pdf(path=pdf, format="A4", print_background=True,
                   margin={"top": "16mm", "bottom": "18mm", "left": "16mm", "right": "16mm"})
            b.close()
        return
    except ImportError:
        pass
    for exe in ["/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
                "C:/Program Files/Google/Chrome/Application/chrome.exe",
                "C:/Program Files (x86)/Microsoft/Edge/Application/msedge.exe",
                "C:/Program Files/Microsoft/Edge/Application/msedge.exe",
                shutil.which("google-chrome") or "", shutil.which("chromium") or ""]:
        if exe and os.path.exists(exe):
            subprocess.run([exe, "--headless=new", "--disable-gpu", "--no-pdf-header-footer",
                            f"--print-to-pdf={os.path.abspath(pdf)}", "file:///" + os.path.abspath(html).replace("\\", "/")],
                           check=True)
            return
    sys.exit("no Playwright and no Chrome/Edge found to print the PDF")


def main():
    vals = json.load(open(sys.argv[1], encoding="utf-8"))
    missing = [k for k in REQUIRED if not vals.get(k)]
    if missing:
        sys.exit(f"missing values: {missing}")
    work = tempfile.mkdtemp(prefix="gmk-")
    fetch_assets(work)
    if vals.get("NO_PLACES") != "1":
        draw_ip(work, vals["SERVER_IP"])
    to_pdf(fill(work, vals), sys.argv[2])
    print("written", sys.argv[2])


if __name__ == "__main__":
    main()
