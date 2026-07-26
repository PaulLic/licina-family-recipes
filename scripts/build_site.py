#!/usr/bin/env python3
"""Rebuild index.html (the interactive online book) from recipes/*.md and library/*.json.
Run from the repo root: python3 scripts/build_site.py"""
import json, re, pathlib, html, datetime

ROOT = pathlib.Path(__file__).resolve().parent.parent

def parse_recipe(path):
    text = path.read_text(encoding='utf-8')
    m = re.match(r'---\n(.*?)\n---\n(.*)', text, re.S)
    front, body = m.group(1), m.group(2)
    meta = {}
    for line in front.splitlines():
        k, _, v = line.partition(':')
        v = v.strip()
        if v.startswith('"') and v.endswith('"'):
            v = json.loads(v)
        meta[k.strip()] = v
    sections = {}
    for name, content in re.findall(r'## (\w[\w &]*)\n\n(.*?)(?=\n## |\Z)', body, re.S):
        sections[name.lower()] = content.strip()
    meta['ingredients'] = sections.get('ingredients', '')
    meta['method'] = sections.get('method', '')
    return meta

def md_inline(s):
    s = html.escape(s)
    s = re.sub(r'\*([^*]+)\*', r'<em>\1</em>', s)
    return s

def render_list(md):
    items = [md_inline(l[2:]) for l in md.splitlines() if l.startswith('- ')]
    return '<ul>' + ''.join(f'<li>{i}</li>' for i in items) + '</ul>'

def render_paras(md):
    return ''.join(f'<p>{md_inline(p.strip())}</p>' for p in md.split('\n\n') if p.strip())

recipes = [parse_recipe(p) for p in sorted((ROOT/'recipes').glob('*.md'))]
for r in recipes:
    r['ingredients_html'] = render_list(r['ingredients'])
    r['method_html'] = render_paras(r['method'])
    r['search'] = ' '.join([r.get('title',''), r.get('alt_title',''), r.get('cuisine',''),
                            r.get('course',''), r.get('tag',''), r.get('ingredients','')]).lower()

library = []
for p in sorted((ROOT/'library').glob('*.json')):
    d = json.loads(p.read_text(encoding='utf-8'))
    if p.name.startswith('_'):
        for b in d.get('books', []):
            library.append({'book': b['title'], 'author': b.get('author',''),
                            'cuisine': b.get('cuisine',''), 'recipes': [], 'indexed': b.get('indexed', False)})
    else:
        library.append({'book': d.get('title',''), 'author': d.get('author',''),
                        'cuisine': d.get('cuisine',''), 'recipes': d.get('recipes', []),
                        'indexed': True, 'source': d.get('source','')})

data = json.dumps({'recipes': recipes, 'library': library}, ensure_ascii=False)
updated = datetime.date.today().strftime('%d %B %Y')
n_final = sum(1 for r in recipes if r.get('status') == 'final')

page = """<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>The Licina Family Recipe Collection</title>
<style>
:root{--cream:#f5efe6;--paper:#fdfaf5;--brown:#3e2723;--mid:#6d4c41;--accent:#8d6e63;--line:#d7ccc0}
*{box-sizing:border-box;margin:0}
body{font-family:Georgia,'Times New Roman',serif;background:var(--cream);color:var(--brown);line-height:1.6}
.wrap{max-width:1000px;margin:0 auto;padding:0 20px}
header.cover{text-align:center;padding:70px 20px 50px;background:var(--brown);color:var(--cream)}
header.cover .the{letter-spacing:.5em;font-size:.9rem;color:#d7ccc0}
header.cover h1{font-size:clamp(1.6rem,5vw,3rem);letter-spacing:.12em;margin:.4em 0 .2em;font-weight:normal}
header.cover .tagline{font-style:italic;color:#d7ccc0;max-width:620px;margin:1em auto 0;font-size:1.05rem}
.rule{width:120px;border:none;border-top:1px solid var(--accent);margin:1.4em auto}
nav.tabs{display:flex;justify-content:center;gap:0;background:var(--brown);padding-bottom:0}
nav.tabs button{font-family:inherit;font-size:1rem;padding:12px 26px;border:none;cursor:pointer;background:transparent;color:#d7ccc0;border-bottom:3px solid transparent}
nav.tabs button.on{color:#fff;border-bottom-color:var(--accent)}
.about{background:var(--paper);border:1px solid var(--line);padding:28px 32px;margin:36px auto;max-width:760px;font-size:1.02rem}
.about h2{font-size:1.1rem;letter-spacing:.15em;margin-bottom:.6em}
.toolbar{display:flex;flex-wrap:wrap;gap:10px;align-items:center;margin:26px 0 18px}
.toolbar input{flex:1 1 240px;font-family:inherit;font-size:1rem;padding:10px 14px;border:1px solid var(--line);background:var(--paper);color:var(--brown)}
.chips{display:flex;flex-wrap:wrap;gap:8px}
.chip{font-family:inherit;font-size:.85rem;padding:6px 14px;border:1px solid var(--accent);border-radius:999px;background:transparent;color:var(--mid);cursor:pointer}
.chip.on{background:var(--brown);color:var(--cream);border-color:var(--brown)}
.grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(270px,1fr));gap:22px;padding-bottom:60px}
.card{background:var(--paper);border:1px solid var(--line);cursor:pointer;transition:box-shadow .15s}
.card:hover{box-shadow:0 4px 18px rgba(62,39,35,.18)}
.card img{width:100%;aspect-ratio:4/3;object-fit:cover;display:block}
.card .pad{padding:14px 16px 16px}
.card h3{font-size:1.08rem;font-weight:normal}
.card .alt{font-style:italic;color:var(--mid);font-size:.9rem}
.badge{display:inline-block;font-size:.72rem;letter-spacing:.08em;text-transform:uppercase;color:var(--accent);margin-top:6px}
.badge.wip{color:#a3552e}
.overlay{position:fixed;inset:0;background:rgba(40,26,22,.55);display:none;align-items:flex-start;justify-content:center;overflow-y:auto;padding:30px 12px;z-index:10}
.overlay.open{display:flex}
.sheet{background:var(--paper);max-width:720px;width:100%;padding:36px 40px 44px;position:relative}
.sheet .x{position:absolute;top:10px;right:16px;font-size:1.6rem;background:none;border:none;color:var(--mid);cursor:pointer}
.sheet img{width:100%;max-height:420px;object-fit:cover;margin:18px 0}
.sheet h2{font-weight:normal;font-size:1.7rem;line-height:1.25}
.sheet .credit{font-style:italic;color:var(--mid);margin-top:4px}
.sheet h4{letter-spacing:.15em;font-size:.85rem;text-transform:uppercase;color:var(--accent);margin:22px 0 8px}
.sheet ul{padding-left:20px}
.libnote{font-size:.92rem;color:var(--mid);font-style:italic;margin:8px 0 20px}
table.lib{width:100%;border-collapse:collapse;background:var(--paper);margin-bottom:60px}
table.lib td,table.lib th{border:1px solid var(--line);padding:9px 12px;text-align:left;font-size:.95rem}
table.lib th{background:var(--brown);color:var(--cream);font-weight:normal;letter-spacing:.08em}
.dl{display:inline-block;margin-top:1.2em;padding:10px 22px;border:1px solid var(--accent);color:var(--cream);text-decoration:none;font-size:.95rem}
.dl:hover{background:var(--accent)}
footer{text-align:center;color:var(--mid);font-size:.85rem;padding:30px 0 40px;font-style:italic}
@media(max-width:600px){.sheet{padding:26px 20px 34px}}
</style>
</head>
<body>
<header class="cover">
  <div class="the">THE</div>
  <h1>LICINA<br>FAMILY RECIPE COLLECTION</h1>
  <hr class="rule">
  <div class="tagline">Recipes gathered with love, from Tatjana&rsquo;s kitchen &mdash; to the kitchens of future generations of Licinas</div>
  <a class="dl" href="book/Licina-Family-Recipe-Book.pdf">Download the printable book (PDF)</a>
</header>
<nav class="tabs">
  <button class="on" data-tab="recipes">Recipes</button>
  <button data-tab="library">Tanya&rsquo;s Library</button>
</nav>
<div class="wrap">
  <section id="tab-recipes">
    <div class="about">
      <h2>ABOUT THIS COLLECTION</h2>
      <p>My love of cooking is a creative outlet and a break from the administrative demands of my career in HR management &mdash; a space for relaxation, self-expression, and showing love to my family. Cooking and dining also help me organise and maintain social connections, from family dinners to events built around fine food and wine.</p>
      <p style="margin-top:.8em">This collection gathers the dishes Natasha and Bianca grew up on, alongside my own creations and favourites drawn from my personal cookbook library.</p>
    </div>
    <div class="toolbar">
      <input id="q" type="search" placeholder="Search recipes or ingredients&hellip;">
      <div class="chips" id="chips"></div>
    </div>
    <div class="grid" id="grid"></div>
  </section>
  <section id="tab-library" style="display:none">
    <div class="about">
      <h2>TANYA&rsquo;S COOKBOOK LIBRARY</h2>
      <p>A growing index of the cookbook collection. Search by dish or ingredient to find which book a recipe lives in &mdash; books marked &ldquo;indexed&rdquo; have their full recipe lists searchable.</p>
    </div>
    <div class="toolbar"><input id="lq" type="search" placeholder="e.g. french chicken with mushrooms and mustard&hellip;"></div>
    <div class="libnote" id="libcount"></div>
    <table class="lib"><thead><tr><th>Match</th><th>Book</th><th>Author</th><th>Page</th></tr></thead><tbody id="librows"></tbody></table>
  </section>
</div>
<div class="overlay" id="ov"><div class="sheet" id="sheet"></div></div>
<footer>Last updated __UPDATED__ &middot; __COUNT__ recipes and counting</footer>
<script>
const DATA = __DATA__;
const TAGS = ["All","Family Favourite","Tanya's Collection","Tanya's Original"];
let tag = "All";
const $ = id => document.getElementById(id);
function chips(){ $('chips').innerHTML = TAGS.map(t=>`<button class="chip ${t===tag?'on':''}" onclick="tag='${t.replace(/'/g,"\\\\'")}';chips();draw()">${t}</button>`).join(''); }
function draw(){
  const q = $('q').value.toLowerCase();
  $('grid').innerHTML = DATA.recipes
    .filter(r => (tag==='All'||r.tag===tag) && (!q || r.search.includes(q)))
    .map((r,i) => `<div class="card" onclick="open_(${DATA.recipes.indexOf(r)})">
      <img src="${r.image}" alt="" loading="lazy">
      <div class="pad"><h3>${r.title}</h3>${r.alt_title?`<div class="alt">${r.alt_title}</div>`:''}
      <span class="badge">${r.tag}</span>${r.status==='in-progress'?'<span class="badge wip"> &middot; in progress</span>':''}</div></div>`).join('')
    || '<p style="grid-column:1/-1;text-align:center;color:var(--mid);font-style:italic">No recipes match &mdash; yet.</p>';
}
function open_(i){
  const r = DATA.recipes[i];
  $('sheet').innerHTML = `<button class="x" onclick="$('ov').classList.remove('open')">&times;</button>
    <h2>${r.title}</h2>${r.alt_title?`<div class="credit">${r.alt_title}</div>`:''}
    <div class="credit">${r.tag}${r.credit?' — '+r.credit:''}</div>
    <img src="${r.image}" alt="${r.title}">
    ${r.status==='in-progress'?'<p class="libnote">This one is still in progress.</p>':''}
    <h4>Ingredients</h4>${r.ingredients_html}<h4>Method</h4>${r.method_html}`;
  $('ov').classList.add('open'); window.scrollTo(0,0);
}
$('ov').addEventListener('click', e => { if(e.target===$('ov')) $('ov').classList.remove('open'); });
function libdraw(){
  const q = $('lq').value.toLowerCase().split(/\\s+/).filter(Boolean);
  let rows = [];
  DATA.library.forEach(b => {
    (b.recipes||[]).forEach(rc => {
      const hay = (rc.title+' '+(rc.tags||[]).join(' ')+' '+b.cuisine).toLowerCase();
      const score = q.filter(w=>hay.includes(w)).length;
      if(!q.length || score) rows.push({s:score, m:rc.title, b:b.book, a:b.author, p:rc.page||'—'});
    });
    if(q.length){
      const bh = (b.book+' '+b.author+' '+b.cuisine).toLowerCase();
      const bs = q.filter(w=>bh.includes(w)).length;
      if(bs && !(b.recipes||[]).length) rows.push({s:bs*0.5, m:'<em>'+(b.indexed?'':'not yet indexed — ')+b.cuisine+'</em>', b:b.book, a:b.author, p:'—'});
    }
  });
  if(!q.length) DATA.library.forEach(b => { if(!(b.recipes||[]).length) rows.push({s:0, m:'<em>'+b.cuisine+(b.indexed?'':' — not yet indexed')+'</em>', b:b.book, a:b.author, p:'—'}); });
  rows.sort((x,y)=>y.s-x.s);
  $('librows').innerHTML = rows.slice(0,80).map(r=>`<tr><td>${r.m}</td><td>${r.b}</td><td>${r.a}</td><td>${r.p}</td></tr>`).join('');
  const ni = DATA.library.filter(b=>b.indexed).length;
  $('libcount').textContent = `${DATA.library.length} books on the shelf · ${ni} fully indexed`;
}
document.querySelectorAll('nav.tabs button').forEach(b=>b.addEventListener('click',()=>{
  document.querySelectorAll('nav.tabs button').forEach(x=>x.classList.remove('on')); b.classList.add('on');
  $('tab-recipes').style.display = b.dataset.tab==='recipes'?'':'none';
  $('tab-library').style.display = b.dataset.tab==='library'?'':'none';
}));
$('q').addEventListener('input',draw); $('lq').addEventListener('input',libdraw);
chips(); draw(); libdraw();
</script>
</body>
</html>"""

page = page.replace('__DATA__', data).replace('__UPDATED__', updated).replace('__COUNT__', str(n_final))
(ROOT/'index.html').write_text(page, encoding='utf-8')
print(f'index.html written: {len(page)} bytes, {len(recipes)} recipes, {len(library)} library books')
