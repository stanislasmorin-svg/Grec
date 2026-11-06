"""Build the static site, one sub-site per language (see LANGS).
Usage (from repo root): python3 tools/build.py
lessons.json (grec, dossier grec/) / lessons_it.json (italien, dossier it/):
list of {date, title, title_fr, title_en, source{name,url}, paragraphs[], paragraphs_en[], fr{}, lemma{}, examples?}
paragraphs_en: English translation of each paragraph (bouton « Traduire le texte en anglais »).
lemma: {"<mot>": "<infinitif / forme du dictionnaire>"} for verbs only.
Each paragraph marks translated words as **mot** (English translation).
fr: {"<mot exactement comme dans **mot**>": "<traduction française>"} (pour le lexique mots.html)
examples (optional): {"<mot>": [["phrase grecque", "English translation", "traduction française"], ...]}
"""
import json, re, html, os, hashlib

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LANGS = {
    "el": dict(file="lessons.json", out="grec/", title="Grec du jour", eyebrow="Ελληνικά κάθε μέρα", name="grec", col="Ελληνικά", short="ΕΛ",
               tagline="Chaque matin, une actualité d'Athènes en grec simple, avec les mots difficiles traduits et l'audio.",
               voice="el-GR-AthinaNeural", gtts="el", other=("it", "Italien du jour →"), legacy=True),
    "it": dict(file="lessons_it.json", out="it/", title="Italien du jour", eyebrow="Italiano ogni giorno", name="italien", col="Italiano", short="IT",
               tagline="Chaque matin, une actualité italienne en italien simple, avec les mots difficiles traduits et l'audio.",
               voice="it-IT-ElsaNeural", gtts="it", other=("el", "Grec du jour →")),
}

def ex_audio_name(lang, text):
    """File name (in audio/ex/ of the language folder) of the MP3 of an example sentence."""
    return hashlib.md5((lang + "|" + text.strip()).encode("utf-8")).hexdigest()[:16] + ".mp3"
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
.text p{margin:0;border-radius:8px}.text[hidden]{display:none}
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
.card .exf2,.vocab .fr2{color:var(--gloss);font-size:14px}
.card .speak{font-size:12px;color:var(--accent);margin-top:4px}
@media (prefers-reduced-motion:reduce){.card{transition:none}}
.vocab .gr{font-family:var(--text);font-size:17px;font-weight:600}.vocab .fr{color:var(--muted);font-size:14px}
.lem{font-weight:400;color:var(--muted);font-size:.85em}
#enBtn[aria-pressed=true]{background:#1e8e3e;border-color:#1e8e3e;color:#fff}
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
  var LANG = document.documentElement.dataset.learn || 'el';
  var a = document.getElementById('voice');
  document.querySelectorAll('[data-rate]').forEach(function(b){
    b.addEventListener('click', function(){
      if (a) a.playbackRate = +b.dataset.rate;
      document.querySelectorAll('[data-rate]').forEach(function(x){ x.setAttribute('aria-pressed', x === b); });
    });
  });
  document.addEventListener('click', function(e){ var w = e.target.closest('.w'); if (w) w.classList.toggle('open'); });
  var tts = null, re = new RegExp('^' + LANG, 'i');
  function pickVoice(){ if (!window.speechSynthesis) return; tts = speechSynthesis.getVoices().filter(function(v){ return re.test(v.lang); })[0] || null; }
  pickVoice(); if (window.speechSynthesis) speechSynthesis.onvoiceschanged = pickVoice;
  var player = null, timer = null;
  function stopAll(){ if (player) { player.pause(); player = null; } clearTimeout(timer); if (window.speechSynthesis) speechSynthesis.cancel(); }
  function say(text, url){
    stopAll();
    if (url) { player = new Audio(url); player.play().catch(function(){ fallback(text); }); return; }
    fallback(text);
  }
  function fallback(text){
    if (!tts) return;
    // 1 s de silence avant la phrase pour ne pas perdre le début
    timer = setTimeout(function(){ var u = new SpeechSynthesisUtterance(text); u.voice = tts; u.lang = tts.lang; u.rate = 0.9; speechSynthesis.speak(u); }, 1000);
  }
  function esc(t){ var d = document.createElement('div'); d.textContent = t; return d.innerHTML; }
  document.querySelectorAll('.card').forEach(function(c){
    var ex = JSON.parse(c.dataset.ex || '[]'), i = -1;
    if (!ex.length) return;
    var head = '<span class="gr">' + esc(c.dataset.gr) + (c.dataset.lem ? ' <span class="lem">(' + esc(c.dataset.lem) + ')</span>' : '') + '</span>';
    c.addEventListener('click', function(){
      if (a && !a.paused) a.pause();
      i = (i + 1) % (ex.length + 1);
      c.classList.add('spin');
      setTimeout(function(){
        var li = c.parentNode;
        if (i === ex.length) { i = -1; li.classList.remove('on'); stopAll();
          c.innerHTML = head + '<span class="fr">' + esc(c.dataset.tr) + '</span>' + (c.dataset.fr ? '<span class="fr2">' + esc(c.dataset.fr) + '</span>' : '') + '<span class="hint">' + ex.length + ' phrase' + (ex.length > 1 ? 's' : '') + ' ↻</span>';
        } else { li.classList.add('on');
          c.innerHTML = '<span class="exg">' + esc(ex[i][0]) + '</span><span class="exf">' + esc(ex[i][1]) + '</span>' + (ex[i][2] ? '<span class="exf2">' + esc(ex[i][2]) + '</span>' : '') + '<span class="hint">' + esc(c.dataset.gr) + ' · ' + (i + 1) + '/' + ex.length + ' — touche pour la suite ↻</span>';
          say(ex[i][0], ex[i][3]);
        }
        c.classList.remove('spin');
      }, 160);
    });
  });
  var gb = document.getElementById('glossBtn'), eb = document.getElementById('enBtn'), text = document.getElementById('text'), en = document.getElementById('textEn');
  gb.addEventListener('click', function(){
    var show = gb.getAttribute('aria-pressed') !== 'true';
    gb.setAttribute('aria-pressed', show); gb.textContent = show ? 'Traductions visibles' : 'Traductions cachées';
    text.classList.toggle('hide', !show);
  });
  if (eb) eb.addEventListener('click', function(){
    var on = eb.getAttribute('aria-pressed') !== 'true';
    eb.setAttribute('aria-pressed', on);
    text.hidden = on; en.hidden = !on;
  });
})();
"""

def lesson_page(s, prev, nxt, lang, L, outdir):
    words, paras_html, plain = [], [], []
    frm = s.get("fr", {})
    for p in s["paragraphs"]:
        out, last = "", 0
        for m in RX.finditer(p):
            out += html.escape(p[last:m.start()])
            f = frm.get(m.group(1), "")
            words.append((m.group(1), m.group(2), f))
            gl = m.group(2) + (f" · {f}" if f else "")
            out += f'<span class="w">{html.escape(m.group(1))}</span><span class="g"> ({html.escape(gl)})</span>'
            last = m.end()
        out += html.escape(p[last:])
        paras_html.append(f"<p>{out}</p>")
        plain.append(RX.sub(r"\1", p))
    chunks = [s["title"] + "."] + plain
    gt = f"https://translate.google.com/?sl={lang}&tl=en&op=translate&text=" + __import__("urllib.parse").parse.quote("\n\n".join(chunks))
    mp3 = os.path.join(outdir, "audio", s["date"] + ".mp3")
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
    lem = s.get("lemma", {})
    def with_audio(p):
        p = list(p[:3]) + [""] * (3 - len(p[:3]))
        n = ex_audio_name(lang, p[0])
        f = os.path.join(outdir, "audio", "ex", n)
        if os.path.exists(f):
            ver = __import__("hashlib").md5(open(f, "rb").read()).hexdigest()[:8]
            p.append("../audio/ex/" + n + "?v=" + ver)
        return p
    def card(a, b, f=""):
        pairs = [with_audio(p) for p in ex.get(a, []) if len(p) >= 2]
        lm = lem.get(a, "")
        lm_html = f' <span class="lem">({html.escape(lm)})</span>' if lm else ""
        data = html.escape(json.dumps(pairs, ensure_ascii=False), quote=True)
        hint = f'<span class="hint">{len(pairs)} phrase{"s" if len(pairs) > 1 else ""} ↻</span>' if pairs else ""
        return (f'<li><button class="card" type="button" data-ex="{data}" data-gr="{html.escape(a)}" data-tr="{html.escape(b)}" data-fr="{html.escape(f)}" data-lem="{html.escape(lm)}"'
                f'{"" if pairs else " disabled"}><span class="gr">{html.escape(a)}{lm_html}</span><span class="fr">{html.escape(b)}</span>{f'<span class="fr2">{html.escape(f)}</span>' if f else ""}{hint}</button></li>')
    vocab = "".join(card(a, b, f) for a, b, f in words)
    nav = []
    if prev: nav.append(f'<a href="{prev["date"]}.html">← Cours précédent</a>')
    nav.append('<a href="../index.html">Tous les cours</a>')
    nav.append('<a href="../mots.html">Tous les mots</a>')
    en_html = "".join(f"<p>{html.escape(p)}</p>" for p in s.get("paragraphs_en", []))
    if nxt: nav.append(f'<a href="{nxt["date"]}.html">Cours suivant →</a>')
    src = s.get("source")
    src_html = f'<p class="note">Source : <a href="{html.escape(src["url"])}" target="_blank" rel="noopener">{html.escape(src["name"])}</a></p>' if src else ""
    return f"""<!doctype html><html lang="fr" data-learn="{lang}"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{html.escape(s["title"])} · {L["title"]}</title>{FONTS}<style>{CSS}</style></head><body><div class="wrap">
<header><span class="eyebrow">{fr_date(s["date"])}</span><h1>{html.escape(s["title"])}</h1><p class="sub">{html.escape(s.get("title_en") or s.get("title_fr",""))}</p></header>
<section class="player">
  {player}
</section>
<section><h2>Les {len(words)} mots</h2>{'<p class="note" style="margin:-4px 0 10px">Touche un mot pour voir des exemples en ' + L["name"] + ', en anglais et en français.</p>' if ex else ""}<ul class="vocab">{vocab}</ul></section>
<section><h2>Le texte</h2><div class="text hide" id="text">{"".join(paras_html)}</div><div class="text" id="textEn" lang="en" hidden>{en_html}</div></section>
<div class="row"><button class="chip" id="glossBtn" aria-pressed="false">Traductions cachées</button>{'<button class="chip" id="enBtn" aria-pressed="false">Traduire le texte en anglais</button>' if en_html else ""}</div>
{src_html}
<nav class="row">{" · ".join(nav)}</nav>
</div><script>{JS}</script></body></html>"""

def index_page(lessons, lang, L):
    items = "".join(f'<li><a href="cours/{s["date"]}.html"><span class="d">{s["date"][8:10]}/{s["date"][5:7]}/{s["date"][:4]}</span><span><span class="t">{html.escape(s["title"])}</span><span class="f">{html.escape(s.get("title_en") or s.get("title_fr",""))}</span></span></a></li>' for s in lessons)
    o = LANGS[L["other"][0]]
    other = "../" + o["out"]
    head = f'<a class="play" href="cours/{lessons[0]["date"]}.html">Lire le cours du jour →</a> ' if lessons else ""
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>{L["title"]}</title>{FONTS}<style>{CSS}</style></head><body><div class="wrap">
<header><span class="eyebrow">{L["eyebrow"]}</span><h1>{L["title"]}</h1><p class="sub">{L["tagline"]}</p></header>
<p class="row">{head}<a href="mots.html">Tous les mots (FR · EN · {L["short"]})</a> · <a href="{other}index.html">{L["other"][1]}</a> · <a href="../index.html">Toutes les langues</a></p>
<section><h2>Tous les cours</h2><ul class="list">{items or '<li class="note">Le premier cours arrive bientôt.</li>'}</ul></section>
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

def gloss_page(lessons, lang, L):
    seen, rows = set(), []
    for s in sorted(lessons, key=lambda s: s["date"]):
        fr = s.get("fr", {}); lem = s.get("lemma", {})
        for p in s["paragraphs"]:
            for m in RX.finditer(p):
                gr, en = m.group(1), m.group(2)
                if lem.get(gr): gr = f"{gr} ({lem[gr]})"
                f = fr.get(gr, "")
                k = (f.lower(), en.lower(), gr.lower())
                if k in seen: continue
                seen.add(k); rows.append((f, en, gr, s["date"]))
    rows.sort(key=lambda r: (fr_key(r[0]), r[1].lower()))
    out, cur = [], None
    for f, en, gr, d in rows:
        ch = (fr_key(f)[0][:1] or "#").upper()
        if ch != cur:
            cur = ch; out.append(f'<tr class="letter"><td colspan="3">{html.escape(ch)}</td></tr>')
        out.append(f'<tr data-s="{html.escape((f+" "+en+" "+gr).lower(), quote=True)}"><td>{html.escape(f)}</td><td>{html.escape(en)}</td>'
                   f'<td><a href="cours/{d}.html" title="Cours du {d}">{html.escape(gr)}</a></td></tr>')
    js = """(function(){var q=document.getElementById('q');q.addEventListener('input',function(){var v=q.value.trim().toLowerCase();
document.querySelectorAll('.lex tr[data-s]').forEach(function(r){r.hidden=v&&r.dataset.s.indexOf(v)<0;});
document.querySelectorAll('.lex tr.letter').forEach(function(r){r.hidden=!!v;});});})();"""
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Tous les mots · {L["title"]}</title>{FONTS}<style>{CSS}{GLOSS_CSS}</style></head><body><div class="wrap">
<header><span class="eyebrow">{L["col"]}</span><h1>Tous les mots</h1><p class="sub">{len(rows)} mots vus dans les cours, par ordre alphabétique français. Touche un mot en {L["name"]} pour ouvrir son cours.</p></header>
<input class="search" id="q" type="search" placeholder="Chercher (français, anglais ou {L["name"]})…" autocomplete="off">
<table class="lex"><thead><tr><th>Français</th><th>English</th><th>{L["col"]}</th></tr></thead><tbody>{"".join(out)}</tbody></table>
<nav class="row"><a href="index.html">Tous les cours</a></nav>
</div><script>{js}</script></body></html>"""

def build(lang, L):
    path = os.path.join(ROOT, L["file"])
    lessons = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else []
    lessons.sort(key=lambda s: s["date"], reverse=True)
    outdir = os.path.join(ROOT, L["out"])
    os.makedirs(os.path.join(outdir, "cours"), exist_ok=True)
    for i, s in enumerate(lessons):
        prev = lessons[i + 1] if i + 1 < len(lessons) else None
        nxt = lessons[i - 1] if i > 0 else None
        open(os.path.join(outdir, "cours", s["date"] + ".html"), "w", encoding="utf-8").write(lesson_page(s, prev, nxt, lang, L, outdir))
    open(os.path.join(outdir, "index.html"), "w", encoding="utf-8").write(index_page(lessons, lang, L))
    open(os.path.join(outdir, "mots.html"), "w", encoding="utf-8").write(gloss_page(lessons, lang, L))
    print(f"{lang}: built {len(lessons)} lesson(s)")

def redirect(target):
    t = html.escape(target, quote=True)
    return (f'<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta http-equiv="refresh" content="0; url={t}">'
            f'<link rel="canonical" href="{t}"><title>Redirection</title></head><body><p><a href="{t}">Le cours a déménagé : cliquer ici</a></p>'
            f'<script>location.replace({json.dumps(target)} + location.hash)</script></body></html>')

def home_page():
    items = []
    for lang, L in LANGS.items():
        path = os.path.join(ROOT, L["file"])
        n = len(json.load(open(path, encoding="utf-8"))) if os.path.exists(path) else 0
        items.append(f'<li><a href="{L["out"]}index.html"><span class="d">{L["short"]}</span><span><span class="t">{L["title"]}</span>'
                     f'<span class="f">{html.escape(L["tagline"])} · {n} cours</span></span></a></li>')
    return f"""<!doctype html><html lang="fr"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>Langues du jour</title>{FONTS}<style>{CSS}</style></head><body><div class="wrap">
<header><span class="eyebrow">15 minutes par jour</span><h1>Langues du jour</h1><p class="sub">Chaque matin, une actualité en version simple, avec les mots difficiles traduits et l'audio. Choisis ta langue.</p></header>
<section><ul class="list">{"".join(items)}</ul></section>
</div></body></html>"""

def main():
    for lang, L in LANGS.items():
        build(lang, L)
    open(os.path.join(ROOT, "index.html"), "w", encoding="utf-8").write(home_page())
    # anciennes adresses du grec (avant le dossier grec/) → redirection
    for lang, L in LANGS.items():
        if not L.get("legacy"): continue
        os.makedirs(os.path.join(ROOT, "cours"), exist_ok=True)
        for s in json.load(open(os.path.join(ROOT, L["file"]), encoding="utf-8")):
            open(os.path.join(ROOT, "cours", s["date"] + ".html"), "w", encoding="utf-8").write(redirect(f'../{L["out"]}cours/{s["date"]}.html'))
        open(os.path.join(ROOT, "mots.html"), "w", encoding="utf-8").write(redirect(f'{L["out"]}mots.html'))
    open(os.path.join(ROOT, ".nojekyll"), "w").close()

if __name__ == "__main__":
    main()
