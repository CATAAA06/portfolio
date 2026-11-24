# Portfolio · Francesco, fotografia automotive (Modena)

Sito statico (HTML, CSS, JavaScript), senza build e senza dipendenze. Font e foto sono nel repo.

## Pubblicare su GitHub Pages
1. Crea un repo pubblico chiamato `portfolio` e carica tutti i file di questa cartella nella root.
2. Su GitHub: **Settings → Pages → Build and deployment → Deploy from a branch → `main` / `/ (root)`**.
3. Dopo circa un minuto il sito è su `https://cataaa06.github.io/portfolio/`.

Se il repo ha un altro nome, aggiorna l'indirizzo in `index.html` (tag `canonical`, `og:url`, `og:image`).

## Cosa modificare
- **Contatti:** sezione `#contatti` in `index.html` (Instagram, WhatsApp, email) e blocco JSON-LD nell'`<head>`.
- **Nuova foto:** salva due WebP in `assets/img/` (`NN-800.webp` larga 800 px e `NN-1600.webp` larga 1600 px, targhe coperte) e copia un blocco `<a class="shot">` dentro `#wall`. `data-cat` può essere `pista`, `museo` o `dettagli`.
- **Colori e font:** variabili `:root` in `assets/css/style.css`.

## Struttura
```
index.html
assets/css/style.css
assets/js/main.js        filtri galleria e lightbox (tasti ← → Esc, swipe)
assets/fonts/            Big Shoulders Display, Hanken Grotesk (self-hosted)
assets/img/              foto WebP, 800 px e 1600 px
assets/og.jpg            anteprima per i social (1200×630)
favicon.svg, robots.txt, .nojekyll
```
