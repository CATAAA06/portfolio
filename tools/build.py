#!/usr/bin/env python3
"""Genera immagini (AVIF + WebP) e blocchi HTML del portfolio da tools/photos.json.

Uso (dalla radice del repo):
    python tools/build.py                 # immagini + HTML
    python tools/build.py --html-only     # solo HTML (immagini gia generate)
    python tools/build.py --source "C:\\altra\\cartella"

Richiede Pillow con supporto AVIF e WebP. Gli originali non finiscono nel repo.
I blocchi in index.html tra <!-- nome:start --> e <!-- nome:end --> sono generati:
non modificarli a mano, cambia photos.json e rilancia.
"""
import argparse, glob, html, json, os, re, sys
from fractions import Fraction

from PIL import Image, ImageDraw, ImageFilter, ImageOps

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "img")
THUMBS = (480, 900)            # larghezze delle miniature
FULL_LONG_SIDE = 2400          # lato lungo massimo della versione grande
AVIF_Q, WEBP_Q = (58, 62), (80, 86)   # (miniature, grande)

GALLERY_SIZES = "(max-width: 1000px) 50vw, 33vw"
HERO_SIZES = "(max-width: 560px) 88vw, (max-width: 1000px) 460px, 520px"
INSET_SIZES = "(max-width: 1000px) 212px, 240px"
BAND_SIZES = "(max-width: 560px) 100vw, 520px"


def esc(s):
    return html.escape(s, quote=True)


def cover_plate(im, box):
    """Copre una targa con sfocatura forte e scurimento (bordi sfumati)."""
    x0, y0, x1, y1 = box
    region = im.crop(box).filter(ImageFilter.GaussianBlur(40))
    region = Image.eval(region, lambda v: int(v * 0.55))
    mask = Image.new("L", (x1 - x0, y1 - y0), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, x1 - x0 - 1, y1 - y0 - 1), radius=18, fill=255)
    im.paste(region, (x0, y0), mask.filter(ImageFilter.GaussianBlur(6)))


# ---------- EXIF (solo dati realmente presenti nel file) ----------
def _fmt_num(x):
    return ("%.1f" % x).rstrip("0").rstrip(".").replace(".", ",")


def exif_line(path):
    try:
        ex = Image.open(path).getexif()
        sub = ex.get_ifd(0x8769)
    except Exception:
        return ""
    make, model = (ex.get(271) or "").strip(), (ex.get(272) or "").strip()
    if not model:
        return ""
    if make.lower() == "sony":
        dev = "Sony " + model.replace("ILCE-", "a")
    elif model.lower().startswith(make.lower()):
        dev = model
    else:
        dev = (make.capitalize() + " " + model).strip()
    parts = [dev]
    focal = sub.get(37386)
    if make.lower() == "sony" and focal:     # sul telefono la focale fisica non e significativa
        parts.append("%s mm" % _fmt_num(float(focal)).replace(",0", ""))
    f = sub.get(33437)
    if f:
        parts.append("f/" + _fmt_num(float(f)))
    t = sub.get(33434)
    if t:
        t = float(t)
        parts.append("1/%d s" % round(1 / t) if t < 1 else "%s s" % _fmt_num(t))
    iso = sub.get(34855)
    if iso:
        parts.append("ISO %d" % (iso[0] if isinstance(iso, (tuple, list)) else iso))
    return " · ".join(parts)


# ---------- immagini ----------
def save_both(im, stem, q_avif, q_webp):
    im.save(stem + ".avif", "AVIF", quality=q_avif, speed=6)
    im.save(stem + ".webp", "WEBP", quality=q_webp, method=6)


def build_images(cfg, source):
    for old in glob.glob(os.path.join(IMG, "*.avif")) + glob.glob(os.path.join(IMG, "*.webp")):
        os.remove(old)
    for p in cfg["photos"]:
        im = ImageOps.exif_transpose(Image.open(os.path.join(source, p["file"]))).convert("RGB")
        for box in p.get("plates", []):
            cover_plate(im, tuple(box))
        big = im.copy()
        big.thumbnail((FULL_LONG_SIDE, FULL_LONG_SIDE), Image.LANCZOS)
        save_both(big, os.path.join(IMG, p["id"] + "-full"), AVIF_Q[1], WEBP_Q[1])
        for w in THUMBS:
            small = im.resize((w, round(im.height * w / im.width)), Image.LANCZOS)
            save_both(small, os.path.join(IMG, "%s-%d" % (p["id"], w)), AVIF_Q[0], WEBP_Q[0])
        print("img", p["id"], p["file"], big.size)


def dims_of(pid):
    out = {}
    for key in list(THUMBS) + ["full"]:
        with Image.open(os.path.join(IMG, "%s-%s.webp" % (pid, key))) as im:
            out[key] = im.size
    return out


# ---------- markup ----------
def srcset(pid, ext, dims, with_full=False):
    items = ["assets/img/%s-%d.%s %dw" % (pid, w, ext, dims[w][0]) for w in THUMBS]
    if with_full:
        items.append("assets/img/%s-full.%s %dw" % (pid, ext, dims["full"][0]))
    return ", ".join(items)


def picture(p, dims, sizes, img_attrs="", with_full=False, indent="        "):
    pid, d = p["id"], dims[p["id"]]
    w, h = d[900]
    return (
        '%s<picture>\n'
        '%s  <source type="image/avif" srcset="%s" sizes="%s">\n'
        '%s  <img src="assets/img/%s-900.webp" srcset="%s" sizes="%s" width="%d" height="%d" alt="%s"%s>\n'
        '%s</picture>'
    ) % (indent, indent, srcset(pid, "avif", d, with_full), sizes,
         indent, pid, srcset(pid, "webp", d, with_full), sizes, w, h, esc(p["alt"]), img_attrs, indent)


def block_gallery(cfg, dims, exifs):
    out = []
    for p in cfg["photos"]:
        pid = p["id"]
        ex = exifs.get(pid, "")
        out.append(
            '      <a class="shot" data-cat="%s" data-n="%s" data-title="%s" data-cap="%s" data-exif="%s"'
            ' href="assets/img/%s-full.webp" data-avif="assets/img/%s-full.avif">\n%s\n'
            '        <span class="roundel">%s</span><span class="cap"><b>%s</b>%s</span>\n      </a>'
            % (p["cat"], pid, esc(p["title"]), esc(p["cap"]), esc(ex), pid, pid,
               picture(p, dims, GALLERY_SIZES, ' loading="lazy" decoding="async"'),
               pid, esc(p["title"]), esc(p["sub"])))
    return "\n".join(out)


def by_id(cfg):
    return {p["id"]: p for p in cfg["photos"]}


def block_hero(cfg, dims):
    ph = by_id(cfg)
    a, b = ph[cfg["hero"]["main"]], ph[cfg["hero"]["inset"]]
    return (picture(a, dims, HERO_SIZES, ' class="a" fetchpriority="high" decoding="async"', True, "      ") + "\n" +
            picture(b, dims, INSET_SIZES, ' class="b" decoding="async"', False, "      "))


def block_band(cfg, dims):
    p = by_id(cfg)[cfg["band"]]
    return picture(p, dims, BAND_SIZES, ' loading="lazy" decoding="async"', False, "      ")


def block_chips(cfg):
    counts = {k: sum(1 for p in cfg["photos"] if k == "all" or p["cat"] == k) for k, _ in cfg["categories"]}
    return "\n".join(
        '        <button class="chip" type="button" data-f="%s" aria-pressed="%s">%s <small>%d</small></button>'
        % (k, "true" if k == "all" else "false", esc(label), counts[k]) for k, label in cfg["categories"])


def block_preload(cfg, dims):
    p = by_id(cfg)[cfg["hero"]["main"]]
    d = dims[p["id"]]
    return ('<link rel="preload" as="image" type="image/avif" href="assets/img/%s-900.avif"\n'
            '      imagesrcset="%s" imagesizes="%s" fetchpriority="high">'
            % (p["id"], srcset(p["id"], "avif", d, True), HERO_SIZES))


def block_ld(cfg):
    site = cfg["siteUrl"]
    me = site + "#francesco"
    graph = [
        {"@type": "Person", "@id": me, "name": "Francesco", "jobTitle": "Fotografo automotive", "url": site,
         "address": {"@type": "PostalAddress", "addressLocality": "Modena", "addressCountry": "IT"},
         "email": "fra.cata2006@gmail.com", "sameAs": ["https://instagram.com/fra_catalano27"]},
        {"@type": "ImageGallery", "@id": site + "#scatti", "name": "Quello che vedo io", "url": site + "#scatti",
         "inLanguage": "it", "creator": {"@id": me},
         "image": [{"@type": "ImageObject", "contentUrl": site + "assets/img/%s-full.webp" % p["id"],
                    "name": p["title"], "caption": p["cap"], "description": p["alt"], "creator": {"@id": me}}
                   for p in cfg["photos"]]},
    ]
    data = json.dumps({"@context": "https://schema.org", "@graph": graph}, ensure_ascii=False, separators=(",", ":"))
    return '<script type="application/ld+json">\n%s\n</script>' % data


def replace_block(text, name, content):
    pat = re.compile(r"(<!-- %s:start -->)(.*?)(<!-- %s:end -->)" % (name, name), re.S)
    if not pat.search(text):
        sys.exit("marcatori mancanti in index.html: " + name)
    return pat.sub(lambda m: "%s\n%s\n%s" % (m.group(1), content, m.group(3)), text, count=1)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--html-only", action="store_true")
    ap.add_argument("--source")
    args = ap.parse_args()
    with open(os.path.join(ROOT, "tools", "photos.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    source = args.source or cfg["sourceDir"]

    if not args.html_only:
        build_images(cfg, source)
    dims = {p["id"]: dims_of(p["id"]) for p in cfg["photos"]}
    exifs = {p["id"]: exif_line(os.path.join(source, p["file"])) for p in cfg["photos"]}

    path = os.path.join(ROOT, "index.html")
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    text = replace_block(text, "preload", block_preload(cfg, dims))
    text = replace_block(text, "ld", block_ld(cfg))
    text = replace_block(text, "hero", block_hero(cfg, dims))
    text = replace_block(text, "chips", block_chips(cfg))
    text = replace_block(text, "gallery", block_gallery(cfg, dims, exifs))
    text = replace_block(text, "band", block_band(cfg, dims))
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    for pid, line in exifs.items():
        print("exif", pid, line or "(nessuno)")
    total = sum(os.path.getsize(x) for x in glob.glob(os.path.join(IMG, "*")))
    print("assets/img: %.1f MB" % (total / 1048576))


if __name__ == "__main__":
    main()
