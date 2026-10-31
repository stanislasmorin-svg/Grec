"""Build the static site from lessons.json.
Usage (from repo root): python3 tools/build.py
lessons.json: list of {date, title, title_fr, title_en, source{name,url}, paragraphs[], fr{}, examples?}
Each paragraph marks translated words as **mot** (English translation).
fr: {"<mot exactement comme dans **mot**>": "<traduction française>"} (pour le lexique mots.html)
examples (optional): {"<mot>": [["phrase grecque", "English translation"], ...]}
"""
import json, re, html, os

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
RX = re.compile(r"\*\*(.+?)\*\*\s*\((.+?)\)")
MONTHS = ["janvier","février","mars","avril","mai","juin","juillet","août","septembre","octobre","novembre","décembre"]
DAYS = ["lundi","mardi","mercredi","jeudi","vendredi","samedi","dimanche"]

def fr_date(iso):
    import datetime
    d = datetime.date.fromisoformat(iso)
    return f"{DAYS[d.weekday()]} {d.day} {MONTHS[d.month-1]} {d.year}"

CSS = """
:root{--bg:#f6f7f3;--surface:#fff;--fg:#1d221c;--muted:#5d665a;--line:#dde2d8;--accent:#4f6b2f;--soft:#e6edda;--gloss:#8a5a14;
--text:"Literata","Noto Serif",Georgia,serif;--ui:"Commissioner","Noto Sans",system-ui,sans-serif}
@media (prefers-color-scheme:dark){:root{--bg:#141712;--surface:#1c2019;--fg:#e8ebe3;--muted:#a2ab9c;--line:#2f362b;--accent:#a9c97d;--soft:#2a3420;--gloss:#e3b469;color-scheme:dark}}
*{box-sizing:border-box}
body{margin:0;background:var(--bg);color:var(--fg);font-family:var(--ui);font-size:15px;line-height:1.5}
.wrap{max-width:680px;margin:0 auto;padding-inline:18px;padding-block:20px 48px;display:flex;flex-direction:column;gap:22px}
a{color:var(--accent)}
.eyebrow{font-size:12px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--accent)}
h1{font-family:var(--text);font-weight:600;font-size:clamp(26px,7vw,36px);line-height:1.15;margin:4px 0;text-wrap:balance}
.sub{color:var(--muted);margin:0}
.player{position:sticky;top:0;z-index:2;background:var(--surface);border:1px solid var(--line);border-radius:14px;padding:12px;display:flex;flex-direction:column;gap:10px}
.row{display:flex;flex-wrap:wrap;gap:8px;align-items:center}
.play{font:inherit;font-size:16px;font-weight:600;padding:10px 20px;border-radius:999px;border:0;background:var(--accent);color:var(--bg);cursor:pointer;text-decoration:none}
.chip{font:inherit;font-size:13px;font-weight:500;padding:6px 12px;border-radius:999px;border:1px solid var(--line);background:transparent;color:var(--fg);cursor:pointer}
.chip[aria-pressed=true]{background:var(--accent);border-color:var(--accent);color:var(--bg)}
.label,.note{font-size:13px;color:var(--muted);margin:0}
.text{font-family:var(--text);font-size:20px;line-height:1.75;display:flex;flex-direction:column;gap:14px}
.text p{margin:0;border-radius:8px}
audio{width:100%}
.w{color:var(--accent);font-weight:600;cursor:pointer}
.g{font-family:var(--ui);font-size:.72em;font-weight:500;color:var(--gloss);white-space:nowrap}
.hide .g{display:none}.hide .w.open+.g{display:inline}
h2{font-size:13px;font-weight:600;letter-spacing:.08em;text-transform:uppercase;color:var(--muted);margin:0 0 10px}
.vocab{display:grid;grid-template-columns:repeat(auto-fill,minmax(150px,1fr));gap:0 18px;margin:0;padding:0;list-style:none}
.vocab li{border-bottom:1px solid var(--line);min-width:0;perspective:600px}
.vocab li.on{grid-column:1/-1}
.card{all:unset;box-sizing:border-box;width:100%;display:flex;flex-direction:column;padding:8px 0;cursor:pointer;border-radius:8px;transition:transform .25s ease,background-color .2s}
.card:disabled{cursor:default}
.card:focus-visible{outline:2px solid var(--accent);outline-offset:2px}
.card.spin{transform:rotateX(90deg)}
.on .card{background:var(--soft);padding:10px 12px}
.card .hint{font-size:11px;color:var(--accent);margin-top:2px}
.card .exg{font-family:var(--text);font-size:18px;font-weight:600;line-height:1.4}
.card .exf{color:var(--muted);font-size:14px}
.card .speak{font-size:12px;color:var(--accent);margin-top:4px}
@media (prefers-reduced-motion:reduce){.card{transition:none}}
.vocab .gr{font-family:var(--text);font-size:17px;font-weight:600}.vocab .fr{color:var(--muted);font-size:14px}
.list{list-style:none;margin:0;padding:0}
.list li{border-bottom:1px solid var(--line)}
.list a{display:flex;gap:12px;align-items:baseline;padding:12px 0;text-decoration:none;color:var(--fg)}
.list .d{font-variant-numeric:tabular-nums;color:var(--muted);font-size:13px;min-width:82px}
.list .t{font-family:var(--text);font-size:17px}
.list .f{color:var(--muted);font-size:13px;display:block}
"""
FONTS = '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Commissioner:wght@400;500;600&family=Literata:opsz,wght@7..72,400;7..72,600&display=swap">'

JS = r"""
(function(){
  var a = document.getElementById('voice');
  document.querySelectorAll('[data-rate]').forEach(function(b){
    b.addEventListener('click', function(){
      if (a) a.playbackRate = +b.dataset.rate;
      document.querySelectorAll('[data-rate]').forEach(function(x){ x.setAttribute('aria-pressed', x === b); });
    });
  });
  document.addEventListener('click', function(e){ var w = e.target.closest('.w'); if (w) w.classList.toggle('open'); });
  var greek = null;
  function pickVoice(){ if (!window.speechSynthesis) return; greek = speechSynthesis.getVoices().filter(function(v){ return /^el/i.test(v.lang); })[0] || null; }
  pickVoice(); if (window.speechSynthesis) speechSynthesis.onvoiceschanged = pickVoice;
  function esc(t){ var d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
  document.querySelectorAll('.card').forEach(function(c){
    var ex = JSON.parse(c.dataset.ex || '[]'), i = -1;
    if (!ex.length) return;
    c.addEventListener('click', function(){
      if (a && !a.paused) a.pause();
      i = (i + 1) % (ex.length + 1);
      c.classList.add('spin');
      setTimeout(function(){
        var li = c.parentNode;
        if (i === ex.length) { i = -1; li.classList.remove('on');
          c.innerHTML = '<span class="gr">' + esc(c.dataset.gr) + '</span><span class="fr">' + esc(c.dataset.tr) + '</span><span class="hint">' + ex.length + ' phrase' + (ex.length > 1 ? 's' : '') + ' ↻</span>';
        } else { li.classList.add('on');
          c.innerHTML = '<span class="exg">' + esc(ex[i][0]) + '</span><span class="exf">' + esc(ex[i][1]) + '</span><span class="hint">' + esc(c.dataset.gr) + ' · ' + (i + 1) + '/' + ex.length + ' — touche pour la suite ↻</span>';
          if (greek) { speechSynthesis.cancel(); var u = new SpeechSynthesisUtterance(ex[i][0]); u.voice = greek; u.lang = greek.lang; u.rate = 0.9; speechSynthesis.speak(u); }
        }
        c.classList.remove('spin');
      }, 160);
    });
  });
  var gb = document.getElementById('glossBtn'), text = document.getElementById('text');
  gb.addEventListener('click', function(){
    var show = gb.getAttribute('aria-pressed') !== 'true';
    gb.setAttribute('aria-pressed', show); gb.textContent = show ? 'Traductions visibles' : 'Traductions cachées';
    text.classList.toggle('hide', !show);
  });
})();
"""

def lesson_page(s, prev, nxt):
    words, paras_html, plain = [], [], []
    for p in s["paragraphs"]:
        out, last = "", 0
        for m in RX.finditer(p):
            out += html.escape(p[last:m.start()])
            words.append((m.group(1), m.group(2)))
            out += f'<span class="w">{html.escape(m.group(1))}</span> <span class="g">({html.escape(m.group(2))})</span>'
            last = m.end()
        out += html.escape(p[last:])
        paras_html.append(f"<p>{out}</p>")
        plain.append(RX.sub(r"\1", p))
    chunks = [s["title"] + "."] + plain
    gt = "https://translate.google.com/?sl=el&tl=en&op=translate&text=" + __import__("urllib.parse").parse.quote("\n\n".join(chunks))
    mp3 = os.path.join(ROOT, "audio", s["date"] + ".mp3")
    if os.path.exists(mp3):
        ver = __import__("hashlib").md5(open(mp3, "rb").read()).hexdigest()[:8]
        player = (f'<audio id="voice" controls preload="metadata" src="../audio/{s["date"]}.mp3?v={ver}"></audio>'
                  '<div class="row"><span class="label">Vitesse</span>'
                  '<button class="chip" data-rate="0.85" aria-pressed="false">0,85×</button>'
                  '<button class="chip" data-rate="1" aria-pressed="true">1×</button></div>')
    else:
        player = (f'<p class="note">L\'audio est en préparation (quelques minutes). En attendant : '
                  f'<a href="{html.escape(gt)}" target="_blank" rel="noopener">écouter dans Google Traduction</a>.</p>')
    ex = s.get("examples", {})
    def card(a, b):
        pairs = [p for p in ex.get(a, []) if len(p) == 2]
        data = html.escape(json.dumps(pairs, ensure_ascii=False), quote=True)
        hint = f'<span class="hint">{len(pairs)} phrase{"s" if len(pairs) > 1 else ""} ↻</span>' if pairs else ""
        return (f'<li><button class="card" type="button" data-ex="{data}" data-gr="{html.escape(a)}" data-tr="{html.escape(b)}"'
                f'{"" if pairs else " disabled"}><span class="gr">{html.escape(a)}</span><span class="fr">{html.escape(b)}</span>{hint}</button></li>')
    vocab = "".join(card(a, b) for a, b in words)
    nav = []
    if prev: nav.append(f'<a href="{prev["date"]}.html">← Cours précédent</a>')
    nav.append('<a href="../index.html">Tous les cours</a>')
    nav.append('<a href="../mots.html">Tous les mots</a>')
    if nxt: nav.append(f'<a href="{nxt["date"]}.html">Cours suivant →</a>')
    src = s.get("source")
    src_html = f'<p class="note">Source : <a href="{html.escape(src["url"])}" target="_blank" rel="noopener">{html.escape(src["name"])}</a></p>' if src else ""
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(s["title"])} · Grec du jour</title>{FONTS}<style>{CSS}</style></head><body><div class="wrap">
<header><span class="eyebrow">{fr_date(s["date"])}</span><h1>{html.escape(s["title"])}</h1><p class="sub">{html.escape(s.get("title_en") or s.get("title_fr",""))}</p></header>
<section class="player">
  {player}
</section>
<section><h2>Les {len(words)} mots</h2>{'<p class="note" style="margin:-4px 0 10px">Touche un mot pour voir des exemples en grec et en anglais.</p>' if ex else ""}<ul class="vocab">{vocab}</ul></section>
<section><h2>Le texte</h2><div class="text" id="text">{"".join(paras_html)}</div></section>
<div class="row"><button class="chip" id="glossBtn" aria-pressed="true">Traductions visibles</button></div>
{src_html}
<nav class="row">{" · ".join(nav)}</nav>
</div><script>{JS}</script></body></html>"""

def index_page(lessons):
    items = "".join(f'<li><a href="cours/{s["date"]}.html"><span class="d">{s["date"][8:10]}/{s["date"][5:7]}/{s["date"][:4]}</span><span><span class="t">{html.escape(s["title"])}</span><span class="f">{html.escape(s.get("title_en") or s.get("title_fr",""))}</span></span></a></li>' for s in lessons)
    latest = lessons[0]
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Grec du jour</title>{FONTS}<style>{CSS}</style></head><body><div class="wrap">
<header><span class="eyebrow">Ελληνικά κάθε μέρα</span><h1>Grec du jour</h1><p class="sub">Chaque matin, une actualité d'Athènes en grec simple, avec les mots difficiles traduits et l'audio.</p></header>
<p class="row"><a class="play" href="cours/{latest["date"]}.html">Lire le cours du jour →</a> <a href="mots.html">Tous les mots (FR · EN · ΕΛ)</a></p>
<section><h2>Tous les cours</h2><ul class="list">{items}</ul></section>
</div></body></html>"""

ARTICLES = re.compile(r"^(?:l'|l’|d'|d’|le |la |les |un |une |des |du |de la |de l'|de l’|de |à |au |aux |se |s'|a |ont |est |sont |va |vont |va |s’)", re.I)

def fr_key(w):
    import unicodedata
    w = w.strip()
    for _ in range(2):
        w = ARTICLES.sub("", w)
    w = unicodedata.normalize("NFD", w.lower())
    return "".join(c for c in w if not unicodedata.combining(c)), w

GLOSS_CSS = """
.search{font:inherit;font-size:16px;width:100%;padding:10px 14px;border-radius:10px;border:1px solid var(--line);background:var(--surface);color:var(--fg)}
.lex{width:100%;border-collapse:collapse}
.lex th{text-align:left;font-size:12px;font-weight:600;letter-spacing:.06em;text-transform:uppercase;color:var(--muted);padding:6px 8px 6px 0;border-bottom:1px solid var(--line)}
.lex td{padding:8px 8px 8px 0;border-bottom:1px solid var(--line);vertical-align:baseline}
.lex td:first-child{font-weight:500}.lex td:nth-child(2){color:var(--muted)}
.lex td:last-child a{font-family:var(--text);font-size:17px;font-weight:600;text-decoration:none}
.lex tr.letter td{border:0;padding:18px 0 4px;font-size:13px;font-weight:600;color:var(--accent)}
"""

def gloss_page(lessons):
    seen, rows = set(), []
    for s in sorted(lessons, key=lambda s: s["date"]):
        fr = s.get("fr", {})
        for p in s["paragraphs"]:
            for m in RX.finditer(p):
                gr, en = m.group(1), m.group(2)
                f = fr.get(gr, "")
                k = (f.lower(), en.lower(), gr.lower())
                if k in seen: continue
                seen.add(k); rows.append((f, en, gr, s["date"]))
    rows.sort(key=lambda r: (fr_key(r[0]), r[1].lower()))
    out, cur = [], None
    for f, en, gr, d in rows:
        L = (fr_key(f)[0][:1] or "#").upper()
        if L != cur:
            cur = L; out.append(f'<tr class="letter"><td colspan="3">{html.escape(L)}</td></tr>')
        out.append(f'<tr data-s="{html.escape((f+" "+en+" "+gr).lower(), quote=True)}"><td>{html.escape(f)}</td><td>{html.escape(en)}</td>'
                   f'<td><a href="cours/{d}.html" title="Cours du {d}">{html.escape(gr)}</a></td></tr>')
    js = """(function(){var q=document.getElementById('q');q.addEventListener('input',function(){var v=q.value.trim().toLowerCase();
document.querySelectorAll('.lex tr[data-s]').forEach(function(r){r.hidden=v&&r.dataset.s.indexOf(v)<0;});
document.querySelectorAll('.lex tr.letter').forEach(function(r){r.hidden=!!v;});});})();"""
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tous les mots · Grec du jour</title>{FONTS}<style>{CSS}{GLOSS_CSS}</style></head><body><div class="wrap">
<header><span class="eyebrow">Λεξιλόγιο</span><h1>Tous les mots</h1><p class="sub">{len(rows)} mots vus dans les cours, par ordre alphabétique français. Touche un mot grec pour ouvrir son cours.</p></header>
<input class="search" id="q" type="search" placeholder="Chercher (français, anglais ou grec)…" autocomplete="off">
<table class="lex"><thead><tr><th>Français</th><th>English</th><th>Ελληνικά</th></tr></thead><tbody>{"".join(out)}</tbody></table>
<nav class="row"><a href="index.html">Tous les cours</a></nav>
</div><script>{js}</script></body></html>"""

def main():
    lessons = json.load(open(os.path.join(ROOT, "lessons.json"), encoding="utf-8"))
    lessons.sort(key=lambda s: s["date"], reverse=True)
    os.makedirs(os.path.join(ROOT, "cours"), exist_ok=True)
    for i, s in enumerate(lessons):
        prev = lessons[i + 1] if i + 1 < len(lessons) else None
        nxt = lessons[i - 1] if i > 0 else None
        open(os.path.join(ROOT, "cours", s["date"] + ".html"), "w", encoding="utf-8").write(lesson_page(s, prev, nxt))
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(index_page(lessons))
    open(os.path.join(ROOT, "mots.html"), "w", encoding="utf-8").write(gloss_page(lessons))
    open(os.path.join(ROOT, ".nojekyll"), "w").close()
    print(f"built {len(lessons)} lesson(s)")

if __name__ == "__main__":
    main()
