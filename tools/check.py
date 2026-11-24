#!/usr/bin/env python3
"""Controlli statici del portfolio (solo libreria standard). Esce con 1 se qualcosa non va.

    python tools/check.py

Verifica: file referenziati esistenti, <img> con alt/width/height, ancore valide, un solo h1,
JSON-LD valido e coerente con la galleria, canonical/og coerenti, nessun percorso assoluto
(il sito vive in /portfolio/), budget di peso del primo caricamento e delle singole foto.
"""
import json, os, re, sys
from html.parser import HTMLParser

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
SITE = "https://cataaa06.github.io/portfolio/"
BUDGET_FIRST_LOAD_KB = 450      # html + css + js + font critici + foto hero (AVIF 900)
BUDGET_THUMB_KB = 200           # AVIF 900
BUDGET_FULL_KB = 600            # AVIF full

fails, warns = [], []


def fail(msg): fails.append(msg)
def warn(msg): warns.append(msg)
def size_kb(rel): return os.path.getsize(os.path.join(ROOT, rel)) / 1024


class Page(HTMLParser):
    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.imgs, self.refs, self.ids, self.anchors, self.h1, self.meta, self.links = [], [], [], [], 0, {}, []
        self.ld, self._in_ld, self._buf, self.title, self._in_title = [], False, [], "", False

    def handle_starttag(self, tag, attrs):
        a = dict(attrs)
        if "id" in a: self.ids.append(a["id"])
        if tag == "h1": self.h1 += 1
        if tag == "img": self.imgs.append(a)
        if tag == "meta":
            key = a.get("property") or a.get("name")
            if key: self.meta[key] = a.get("content", "")
        if tag == "link": self.links.append(a)
        for k in ("src", "href"):
            if k in a and tag in ("img", "source", "script", "link", "a"):
                if tag == "a" and a[k].startswith("#"): self.anchors.append(a[k][1:])
                else: self.refs.append((tag, a[k]))
        for k in ("srcset", "imagesrcset", "data-avif"):
            if k in a:
                for part in a[k].split(","):
                    u = part.strip().split(" ")[0]
                    if u: self.refs.append((tag, u))
        if tag == "script" and a.get("type") == "application/ld+json":
            self._in_ld, self._buf = True, []
        if tag == "title": self._in_title = True

    def handle_endtag(self, tag):
        if tag == "script" and self._in_ld:
            self.ld.append("".join(self._buf)); self._in_ld = False
        if tag == "title": self._in_title = False

    def handle_data(self, data):
        if self._in_ld: self._buf.append(data)
        if self._in_title: self.title += data


def local(url):
    if re.match(r"^(https?:|mailto:|tel:|data:)", url): return None
    return url.split("#")[0].split("?")[0]


def main():
    with open(os.path.join(ROOT, "index.html"), encoding="utf-8") as f:
        raw = f.read()
    p = Page(); p.feed(raw)

    # 1. file referenziati
    for tag, url in p.refs:
        rel = local(url)
        if rel is None or rel == "": continue
        if rel.startswith("/"): fail("percorso assoluto (rompe la subpath): " + url)
        elif not os.path.exists(os.path.join(ROOT, rel)): fail("file mancante: " + url)

    # 2. immagini
    for a in p.imgs:
        name = a.get("src", a.get("id", "?"))
        if "alt" not in a: fail("img senza alt: " + name)
        if a.get("id") == "lbImg": continue   # riempita dal lightbox
        if not a.get("alt"): fail("img con alt vuoto: " + name)
        if not (a.get("width") and a.get("height")): fail("img senza width/height (CLS): " + name)

    # 3. ancore, id, h1
    dup = {i for i in p.ids if p.ids.count(i) > 1}
    if dup: fail("id duplicati: %s" % sorted(dup))
    for t in p.anchors:
        if t and t not in p.ids: fail("ancora senza destinazione: #" + t)
    if p.h1 != 1: fail("servono esattamente un h1, trovati %d" % p.h1)

    # 4. JSON-LD
    shots = len(re.findall(r'class="shot"', raw))
    try:
        graph = json.loads(p.ld[0])["@graph"]
        types = [n["@type"] for n in graph]
        if "Person" not in types or "ImageGallery" not in types: fail("JSON-LD senza Person/ImageGallery")
        gal = next(n for n in graph if n["@type"] == "ImageGallery")
        if len(gal["image"]) != shots: fail("JSON-LD: %d immagini, galleria: %d" % (len(gal["image"]), shots))
    except Exception as e:
        fail("JSON-LD non valido: %s" % e)

    # 5. meta e link
    canon = next((l["href"] for l in p.links if l.get("rel") == "canonical"), "")
    if canon != SITE: fail("canonical diverso da " + SITE)
    if p.meta.get("og:url") != SITE: fail("og:url diverso da " + SITE)
    for k in ("og:image", "twitter:image"):
        if not p.meta.get(k, "").startswith(SITE + "assets/og.jpg"): fail(k + " non punta a og.jpg del sito")
    for k in ("og:image:alt", "twitter:image:alt", "og:title", "twitter:title", "description"):
        if not p.meta.get(k): fail("meta mancante: " + k)
    if len(p.meta.get("description", "")) > 175: warn("description lunga (%d car., Google ne mostra ~155-160)" % len(p.meta["description"]))
    if not p.title.strip(): fail("title vuoto")

    # 6. file di servizio
    for f in ("robots.txt", "sitemap.xml", "404.html", "favicon.svg", "apple-touch-icon.png", "assets/og.jpg", ".nojekyll"):
        if not os.path.exists(os.path.join(ROOT, f)): fail("manca " + f)

    # 6b. contenuto: nessuna foto ripetuta, filtri coerenti, contatti coerenti, dati di scatto
    with open(os.path.join(ROOT, "tools", "photos.json"), encoding="utf-8") as f:
        cfg = json.load(f)
    files = [p["file"] for p in cfg["photos"]] + [cfg["hero"]["main"]["file"], cfg["hero"]["inset"]["file"]]
    dupes = {x for x in files if files.count(x) > 1}
    if dupes: fail("stessa foto usata due volte (hero e galleria): %s" % sorted(dupes))
    cats = re.findall(r'class="shot" data-cat="(\w+)"', raw)
    for k, label in cfg["categories"]:
        n = len(cats) if k == "all" else cats.count(k)
        m = re.search(r'data-f="%s"[^>]*>[^<]*<small>(\d+)</small>' % k, raw)
        if not m or int(m.group(1)) != n: fail("filtro '%s': conteggio %s, foto reali %d" % (label, m.group(1) if m else "?", n))
    unknown = set(cats) - {k for k, _ in cfg["categories"]}
    if unknown: fail("categorie senza filtro: %s" % sorted(unknown))
    phone = cfg["contact"]["phone"]
    numbers = set(re.findall(r"wa\.me/(\d+)", raw))
    if numbers != {phone}: fail("numeri WhatsApp diversi nei link: %s (atteso %s)" % (sorted(numbers), phone))
    if re.sub(r"\D", "", cfg["contact"]["phoneLabel"]) != phone: fail("numero visibile diverso dal link WhatsApp")
    if cfg["contact"]["phoneLabel"] not in raw: fail("numero visibile assente dalla pagina")
    if not cfg.get("showExif") and re.search(r'data-exif="[^"]+"', raw): fail("dati di scatto presenti ma showExif e false")
    if cfg["contact"]["email"] not in raw: fail("email non presente nella pagina")
    for stale in ("Parto da Modena", "assets/img/%s" % "01-l.webp"):
        if stale in raw: fail("testo/file superato ancora presente: " + stale)
    from urllib.parse import unquote as _unq
    everything = _unq(raw).lower() + " " + json.dumps(cfg, ensure_ascii=False).lower()
    for banned in ("gratis", "gratuit", "prova"):
        if banned in everything: fail("la parola '%s' non deve comparire (pagina, meta, JSON-LD, messaggi precompilati)" % banned)

    # 6c. testo: niente parole incollate, niente frasi ripetute, messaggi precompilati leggibili
    glued = re.findall(r"</(?:b|small|strong)><(?:span|small|b)\b", raw)
    if glued: fail("elementi inline senza spazio (testo incollato quando manca il CSS): %d casi" % len(glued))
    plain = re.sub(r"<script.*?</script>|<[^>]+>", " ", raw, flags=re.S).lower()
    n_phrase = plain.count("tutto quello che si muove")
    if n_phrase != 1: fail("'tutto quello che si muove' deve comparire una sola volta nel testo (trovato %d)" % n_phrase)
    from urllib.parse import unquote
    for enc in re.findall(r'href="https://wa\.me/\d+\?text=([^"]+)"', raw):
        txt = unquote(enc)
        if "_" in txt: fail("segnaposto con underscore (WhatsApp li legge come corsivo): " + txt)
        if "[" not in txt and "]" not in txt: warn("messaggio WhatsApp senza segnaposto da completare: " + txt)
    mail = re.search(r'href="mailto:[^"?]+\?subject=([^&"]+)&amp;body=([^"]+)"', raw)
    if not mail: fail("mailto senza oggetto e testo")

    # 7. budget di peso
    first = size_kb("index.html") + size_kb("assets/css/style.css") + size_kb("assets/js/main.js") + size_kb("assets/js/motion.js")
    first += size_kb("assets/fonts/big-shoulders-display-latin-800-normal.woff2") + size_kb("assets/fonts/hanken-grotesk-latin-400-normal.woff2")
    m = re.search(r'<img src="assets/img/(\d\d)-900\.webp"[^>]*class="a"', raw) or re.search(r'class="a"[^>]*>', raw)
    hero = re.search(r'rel="preload" as="image"[^>]*href="(assets/img/[^"]+)"', raw)
    if hero: first += size_kb(hero.group(1))
    print("primo caricamento stimato: %.0f KB (budget %d)" % (first, BUDGET_FIRST_LOAD_KB))
    if first > BUDGET_FIRST_LOAD_KB: fail("primo caricamento %.0f KB > %d KB" % (first, BUDGET_FIRST_LOAD_KB))
    img_dir = os.path.join(ROOT, "assets", "img")
    for name in sorted(os.listdir(img_dir)):
        kb = size_kb("assets/img/" + name)
        if name.endswith("-900.avif") and kb > BUDGET_THUMB_KB: fail("%s pesa %.0f KB (> %d)" % (name, kb, BUDGET_THUMB_KB))
        if name.endswith("-full.avif") and kb > BUDGET_FULL_KB: fail("%s pesa %.0f KB (> %d)" % (name, kb, BUDGET_FULL_KB))

    print("img: %d elementi, %d foto in galleria, %d riferimenti locali controllati" % (len(p.imgs), shots, len(p.refs)))
    for w in warns: print("AVVISO:", w)
    for f in fails: print("ERRORE:", f)
    print("OK" if not fails else "FALLITO (%d errori)" % len(fails))
    sys.exit(1 if fails else 0)


if __name__ == "__main__":
    main()
