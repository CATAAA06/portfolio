#!/usr/bin/env python3
"""Genera immagini (AVIF + WebP) e blocchi HTML del portfolio da tools/photos.json.

Uso (dalla radice del repo):
    python tools/build.py                 # immagini + HTML
    python tools/build.py --html-only     # solo HTML (immagini gia generate)
    python tools/build.py --source "C:\\altra\\cartella"

Richiede Pillow con supporto AVIF e WebP. Gli originali non finiscono nel repo.
I blocchi in index.html tra <!-- nome:start --> e <!-- nome:end --> sono generati:
non modificarli a mano, cambia photos.json e rilancia.

Le foto della galleria prendono l'id dalla posizione (01, 02, ...); le due foto della
hero (fuori galleria) si chiamano "ha" e "hb".
"""
import argparse, glob, html, json, os, re, sys
from urllib.parse import quote

from PIL import Image, ImageDraw, ImageFilter, ImageOps, ImageStat

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
IMG = os.path.join(ROOT, "assets", "img")
THUMBS = (480, 900)            # larghezze delle miniature
FULL_LONG_SIDE = 2400          # lato lungo massimo della versione grande
AVIF_Q, WEBP_Q = (58, 62), (80, 86)   # (miniature, grande)

GALLERY_SIZES = "(max-width: 1000px) 50vw, 33vw"
HERO_SIZES = "(max-width: 560px) 88vw, (max-width: 1000px) 460px, 520px"
INSET_SIZES = "(max-width: 1000px) 212px, 240px"


def esc(s):
    return html.escape(s, quote=True)


# ---------- targhe: al posto del testo una targa vuota, nel colore reale della targa ----------
def blank_plate(im, box):
    x0, y0, x1, y1 = box
    w, h = x1 - x0, y1 - y0
    med = tuple(int(v) for v in ImageStat.Stat(im.crop(box)).median[:3])
    bright = sum(med) / 3 > 120
    if bright:
        # targa chiara: tolgo la dominante rosa della luce e la porto verso il bianco (niente rettangolo colorato)
        med = tuple(int(0.35 * c + 0.65 * 236) for c in med)
    patch = Image.new("RGB", (w, h))
    px = patch.load()
    for y in range(h):
        f = 1.04 - 0.10 * (y / max(1, h - 1))          # lieve gradiente di luce dall'alto
        row = tuple(min(255, int(c * f)) for c in med)
        for x in range(w):
            px[x, y] = row
    radius = max(4, h // 7)
    d = ImageDraw.Draw(patch)
    if bright:                                          # fascia blu europea, senza stelle né lettere
        d.rounded_rectangle((0, 0, int(w * 0.115), h - 1), radius=radius, fill=(34, 62, 140))
        d.rectangle((radius, 0, int(w * 0.115), h - 1), fill=(34, 62, 140))
    d.rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, outline=tuple(int(c * 0.62) for c in med), width=max(2, h // 26))
    patch = patch.filter(ImageFilter.GaussianBlur(max(1.0, h / 38)))
    mask = Image.new("L", (w, h), 0)
    ImageDraw.Draw(mask).rounded_rectangle((0, 0, w - 1, h - 1), radius=radius, fill=255)
    im.paste(patch, (x0, y0), mask.filter(ImageFilter.GaussianBlur(1.2)))


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


# ---------- elenco foto con id ----------
def items_of(cfg):
    gallery = []
    for i, p in enumerate(cfg["photos"], 1):
        q = dict(p); q["id"] = "%02d" % i
        gallery.append(q)
    hero = {"ha": dict(cfg["hero"]["main"], id="ha"), "hb": dict(cfg["hero"]["inset"], id="hb")}
    return gallery, hero


# ---------- immagini ----------
def save_both(im, stem, q_avif, q_webp):
    im.save(stem + ".avif", "AVIF", quality=q_avif, speed=6)
    im.save(stem + ".webp", "WEBP", quality=q_webp, method=6)


def build_images(items, source):
    for old in glob.glob(os.path.join(IMG, "*.avif")) + glob.glob(os.path.join(IMG, "*.webp")):
        os.remove(old)
    for p in items:
        im = ImageOps.exif_transpose(Image.open(os.path.join(source, p["file"]))).convert("RGB")
        for box in p.get("plates", []):
            blank_plate(im, tuple(box))
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


def block_gallery(gallery, dims, exifs):
    out = []
    for p in gallery:
        pid = p["id"]
        out.append(
            '      <a class="shot" data-cat="%s" data-n="%s" data-title="%s" data-cap="%s" data-exif="%s"'
            ' href="assets/img/%s-full.webp" data-avif="assets/img/%s-full.avif" aria-haspopup="dialog">\n%s\n'
            '        <span class="roundel" aria-hidden="true">%s</span>'
            '<span class="cap" aria-hidden="true"><b>%s</b>%s</span>\n      </a>'
            % (p["cat"], pid, esc(p["title"]), esc(p["cap"]), esc(exifs.get(pid, "")), pid, pid,
               picture(p, dims, GALLERY_SIZES, ' loading="lazy" decoding="async"'),
               pid, esc(p["title"]), esc(p["sub"])))
    return "\n".join(out)


def block_hero(hero, dims):
    return (picture(hero["ha"], dims, HERO_SIZES, ' class="a" fetchpriority="high" decoding="async"', True, "      ") + "\n" +
            picture(hero["hb"], dims, INSET_SIZES, ' class="b" decoding="async"', False, "      "))


def block_chips(cfg, gallery):
    counts = {k: sum(1 for p in gallery if k == "all" or p["cat"] == k) for k, _ in cfg["categories"]}
    return "\n".join(
        '        <button class="chip" type="button" data-f="%s" aria-pressed="%s">%s <small>%d</small></button>'
        % (k, "true" if k == "all" else "false", esc(label), counts[k]) for k, label in cfg["categories"])


def block_meta(gallery):
    return '        <p class="sec-meta">%d scatti · targhe sempre coperte</p>' % len(gallery)


def block_preload(hero, dims):
    d = dims["ha"]
    return ('<link rel="preload" as="image" type="image/avif" href="assets/img/ha-900.avif"\n'
            '      imagesrcset="%s" imagesizes="%s" fetchpriority="high">'
            % (srcset("ha", "avif", d, True), HERO_SIZES))


def wa(contact, text):
    return "https://wa.me/%s?text=%s" % (contact["phone"], quote(text, safe=""))


def block_contact(cfg):
    c = cfg["contact"]
    pills = "\n".join('      <a class="wa" href="%s" rel="noopener">%s</a>' % (esc(wa(c, m["text"])), esc(m["label"]))
                      for m in c["messages"])
    mailto = "mailto:%s?subject=%s&body=%s" % (c["email"], quote(c["emailSubject"], safe=""), quote(c["emailBody"], safe=""))
    return (
        '    <p class="lead small">Dimmi di cosa ti occupi: si apre WhatsApp con il messaggio già scritto, completi i vuoti e invii.</p>\n'
        '    <div class="wa-row" role="group" aria-label="Scrivimi su WhatsApp come">\n%s\n    </div>\n'
        '    <div class="cards">\n'
        '      <a class="card" href="https://instagram.com/%s" rel="noopener"><small>Instagram</small><span>@%s</span></a>\n'
        '      <a class="card" href="%s" rel="noopener"><small>WhatsApp</small><span>%s</span></a>\n'
        '      <a class="card" href="%s"><small>Email</small><span>%s</span></a>\n'
        '    </div>'
    ) % (pills, c["instagram"], c["instagram"], esc(wa(c, c["whatsappGeneric"])), esc(c["phoneLabel"]), esc(mailto), esc(c["email"]))


def block_ld(cfg, gallery):
    site = cfg["siteUrl"]
    me = site + "#francesco"
    c = cfg["contact"]
    graph = [
        {"@type": "Person", "@id": me, "name": "Francesco", "jobTitle": "Fotografo automotive", "url": site,
         "description": "Fotografo auto a Modena, nella Motor Valley.",
         "address": {"@type": "PostalAddress", "addressLocality": "Modena", "addressCountry": "IT"},
         "email": c["email"], "sameAs": ["https://instagram.com/" + c["instagram"]]},
        {"@type": "ImageGallery", "@id": site + "#scatti", "name": "Quello che vedo io", "url": site + "#scatti",
         "inLanguage": "it", "creator": {"@id": me},
         "image": [{"@type": "ImageObject", "contentUrl": site + "assets/img/%s-full.webp" % p["id"],
                    "name": p["title"], "caption": p["cap"], "description": p["alt"], "creator": {"@id": me}}
                   for p in gallery]},
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
    gallery, hero = items_of(cfg)

    if not args.html_only:
        build_images(gallery + list(hero.values()), source)
    dims = {p["id"]: dims_of(p["id"]) for p in gallery + list(hero.values())}
    exifs = {p["id"]: exif_line(os.path.join(source, p["file"])) for p in gallery} if cfg.get("showExif") else {}

    path = os.path.join(ROOT, "index.html")
    with open(path, encoding="utf-8", newline="") as f:
        text = f.read()
    text = replace_block(text, "preload", block_preload(hero, dims))
    text = replace_block(text, "ld", block_ld(cfg, gallery))
    text = replace_block(text, "hero", block_hero(hero, dims))
    text = replace_block(text, "chips", block_chips(cfg, gallery))
    text = replace_block(text, "meta", block_meta(gallery))
    text = replace_block(text, "gallery", block_gallery(gallery, dims, exifs))
    text = replace_block(text, "contact", block_contact(cfg))
    with open(path, "w", encoding="utf-8", newline="") as f:
        f.write(text)
    print("dati di scatto nel lightbox:", "si" if exifs else "no")
    total = sum(os.path.getsize(x) for x in glob.glob(os.path.join(IMG, "*")))
    print("assets/img: %.1f MB" % (total / 1048576))


if __name__ == "__main__":
    main()
