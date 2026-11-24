# Portfolio · Francesco, fotografia automotive (Modena)

Sito statico (HTML, CSS, JavaScript), senza build per il sito e senza dipendenze. Le foto e i font sono nel repo.
Online: https://cataaa06.github.io/portfolio/

## Pubblicare su GitHub Pages
1. Repo pubblico `portfolio`, branch `main`, tutti i file nella root.
2. **Settings → Pages → Deploy from a branch → `main` / `/ (root)`**.
3. Dopo circa un minuto il sito è online. GitHub tiene la pagina in cache fino a 10 minuti: per vedere subito una modifica usa Ctrl+F5 o aggiungi `?v=numero` all'indirizzo.

Se il repo cambia nome, aggiorna l'indirizzo in `index.html` (`canonical`, `og:*`, `twitter:*`), in `tools/photos.json` (`siteUrl`), in `tools/check.py` (`SITE`), in `robots.txt` e `sitemap.xml`.

## Struttura
```
index.html               pagina unica (i blocchi tra <!-- nome:start/end --> sono generati)
assets/css/style.css     stili, variabili in :root
assets/js/main.js        galleria (ordine di lettura, filtri), lightbox, menu mobile
assets/js/motion.js      extra di movimento (si spegne con prefers-reduced-motion)
assets/fonts/            Big Shoulders Display, Hanken Grotesk (self-hosted)
assets/img/              foto generate: NN-480, NN-900, NN-full in AVIF e WebP (ha/hb = le due foto della hero)
assets/og.jpg            anteprima per i social (1200×630)
tools/photos.json        elenco foto: file, titolo, didascalia, alt, targhe da coprire
tools/build.py           genera immagini e blocchi HTML da photos.json
tools/check.py           controlli statici (file, alt, JSON-LD, peso, subpath)
404.html, robots.txt, sitemap.xml, favicon.svg, apple-touch-icon.png
```

## Aggiungere o cambiare una foto
1. Metti il JPEG originale nella cartella indicata in `tools/photos.json` (`sourceDir`) o passa `--source`.
2. Aggiungi una voce in `photos` (`file`, `cat` tra `pista`, `dettagli`, `museo`, `title`, `sub`, `cap`, `alt`). L'ordine nell'elenco è l'ordine in galleria e fissa l'id (01, 02, ...): le prime foto sono quelle che si vedono per prime. Se si vede una targa, aggiungi `plates`: `[[x0, y0, x1, y1]]` in pixel dell'originale, viene sostituita da una targa vuota.
3. Le due foto della hero sono in `hero` e **non** devono comparire anche in galleria (`tools/check.py` lo controlla).
4. Lancia `python tools/build.py` (serve Pillow con AVIF e WebP). Rigenera le immagini e la galleria, i filtri con i conteggi, il preload della foto principale, i contatti precompilati e i dati strutturati.
5. Lancia `python tools/check.py`: deve finire con `OK`.
6. Alza il numero di versione di CSS e JS in `index.html` (`?v=`) se li hai toccati, poi commit e push.

`python tools/build.py --html-only` rigenera solo l'HTML senza ricreare le immagini.

## Dati di scatto
Spenti per ora (`"showExif": false` in `tools/photos.json`). Con `true` il lightbox mostra fotocamera, diaframma, tempo e ISO letti dall'EXIF dell'originale (mai la posizione). Conviene riattivarli quando le foto sono fatte con la Sony.

## Cosa modificare a mano
- **Contatti e messaggi precompilati** (WhatsApp per categoria, email): blocco `contact` in `tools/photos.json`, poi `python tools/build.py --html-only`. Numero, email e Instagram stanno solo lì.
- **Testi:** direttamente in `index.html`, fuori dai blocchi generati.
- **Colori e font:** variabili `:root` in `assets/css/style.css`.
- **Anteprima social:** `assets/og.jpg`; dopo averla cambiata aggiorna `?v=` in `og:image` e `twitter:image`.
