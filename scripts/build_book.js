#!/usr/bin/env node
/* Rebuild the printable book from recipes/*.md.
   Duplex layout: p1 cover (recto) · p2 spacer · p3 About (recto) · then per FINAL recipe:
   text on a left-hand (even) page, photo on the facing right-hand (odd) page.
   Run from repo root: node scripts/build_book.js  → book/Licina-Family-Recipe-Book.docx */
const fs = require('fs'), path = require('path');
const { Document, Packer, Paragraph, TextRun, ImageRun, PageBreak, AlignmentType,
        LevelFormat, convertMillimetersToTwip } = require('docx');

const ROOT = path.resolve(__dirname, '..');
const BROWN = "3E2723", MID = "6D4C41", ACCENT = "8D6E63";
const FONT = "Georgia";

function parseRecipe(file) {
  const text = fs.readFileSync(file, 'utf8');
  const m = text.match(/^---\n([\s\S]*?)\n---\n([\s\S]*)$/);
  const meta = {};
  for (const line of m[1].split('\n')) {
    const i = line.indexOf(':');
    let v = line.slice(i + 1).trim();
    if (v.startsWith('"') && v.endsWith('"')) v = JSON.parse(v);
    meta[line.slice(0, i).trim()] = v;
  }
  const sec = {};
  for (const s of m[2].split(/\n## /).slice(0)) {
    const name = s.replace(/^## /, '').split('\n')[0].trim().toLowerCase();
    sec[name] = s.split('\n').slice(1).join('\n').trim();
  }
  meta.ingredients = (sec['ingredients'] || '').split('\n').filter(l => l.startsWith('- ')).map(l => l.slice(2).replace(/\*/g, ''));
  meta.method = (sec['method'] || '').split('\n\n').map(p => p.replace(/\n/g, ' ').replace(/\*/g, '').trim()).filter(Boolean);
  return meta;
}

const recipes = fs.readdirSync(path.join(ROOT, 'recipes')).sort()
  .map(f => parseRecipe(path.join(ROOT, 'recipes', f)))
  .filter(r => r.status === 'final');

const P = (opts) => new Paragraph(opts);
const T = (text, o = {}) => new TextRun({ text, font: FONT, ...o });
const spacer = (n) => Array.from({ length: n }, () => P({ children: [] }));
const brk = () => P({ children: [new PageBreak()] });

/* Pixel dimensions straight from the file header, so portrait and landscape
   photos both keep their true proportions instead of being stretched. */
function pixelSize(buf, ext) {
  if (ext === 'png') return { w: buf.readUInt32BE(16), h: buf.readUInt32BE(20) };
  let i = 2;
  while (i < buf.length - 9) {
    if (buf[i] !== 0xFF) { i++; continue; }
    const marker = buf[i + 1];
    if (marker >= 0xC0 && marker <= 0xCF && ![0xC4, 0xC8, 0xCC].includes(marker))
      return { h: buf.readUInt16BE(i + 5), w: buf.readUInt16BE(i + 7) };
    const len = buf.readUInt16BE(i + 2);
    if (len < 2) break;
    i += 2 + len;
  }
  return null;
}

function img(rel, maxWMM, maxHMM) {
  const ext = rel.toLowerCase().endsWith('.png') ? 'png' : 'jpg';
  const data = fs.readFileSync(path.join(ROOT, rel));
  const px = pixelSize(data, ext);
  let wMM = maxWMM, hMM = maxHMM;
  if (px && px.w > 0 && px.h > 0) {
    const scale = Math.min(maxWMM / px.w, maxHMM / px.h);
    wMM = px.w * scale; hMM = px.h * scale;
  }
  return new ImageRun({
    type: ext, data,
    transformation: { width: wMM * 3.7795, height: hMM * 3.7795 }
  });
}

const children = [];

// ---- p1 Cover
children.push(...spacer(6));
children.push(P({ alignment: AlignmentType.CENTER, children: [T("THE", { size: 28, color: MID, characterSpacing: 60 })] }));
children.push(...spacer(1));
children.push(P({ alignment: AlignmentType.CENTER, children: [T("LICINA", { size: 72, bold: true, color: BROWN })] }));
children.push(P({ alignment: AlignmentType.CENTER, children: [T("FAMILY RECIPE COLLECTION", { size: 48, bold: true, color: BROWN })] }));
children.push(...spacer(2));
const coverFile = fs.readdirSync(path.join(ROOT,'images')).find(f => f.startsWith('cover.'));
children.push(P({ alignment: AlignmentType.CENTER, children: [img('images/' + coverFile, 100, 133)] }));
children.push(...spacer(2));
children.push(P({ alignment: AlignmentType.CENTER, children: [T("Recipes gathered with love, from Tatjana’s kitchen — to the kitchens of future generations of Licinas", { italics: true, size: 24, color: MID })] }));
children.push(brk());

// ---- p2 spacer (back of cover)
children.push(P({ children: [T("")] }));
children.push(brk());

// ---- p3 About (recto)
children.push(...spacer(3));
children.push(P({ alignment: AlignmentType.CENTER, children: [T("About This Collection", { size: 40, bold: true, color: BROWN })] }));
children.push(...spacer(1));
for (const para of [
  "My beautiful daughters Natasha and Bianca asked me to write a recipe book of all their favourite meals they enjoyed as children and continue to enjoy as young adults. This collection includes those recipes and a collection of my own favourites from talented chefs and my own creations.",
  "For me, cooking has always been an expression of my creativity and my kitchen a space for relaxation. Preparing and serving food for my family and friends is how I stay socially connected and show love. My husband motivates and encourages my passion for cooking; often joining me in designing menus, sourcing ingredients and preparing dinners for social occasions with our friends and family.",
]) children.push(P({ spacing: { after: 240 }, children: [T(para, { size: 24 })] }));
children.push(...spacer(1));
children.push(P({ children: [T("How Recipes Are Tagged", { size: 28, bold: true, color: BROWN })] }));
for (const tag of [
  "Family Favourite — dishes from Natasha and Bianca’s childhood",
  "Tanya’s Collection — recipes gathered from my cookbook library, credited to the original author",
  "Tanya’s Original — my own creations",
]) children.push(P({ numbering: { reference: "bullets", level: 0 }, children: [T(tag, { size: 24 })] }));
children.push(brk());

// ---- Recipes: text on verso (even), image on recto (odd)
recipes.forEach((r, i) => {
  children.push(P({ children: [T(`RECIPE ${r.number}`, { size: 20, color: ACCENT, characterSpacing: 40 })] }));
  children.push(P({ spacing: { after: 60 }, children: [T(r.title, { size: 40, bold: true, color: BROWN })] }));
  if (r.alt_title) children.push(P({ children: [T(r.alt_title, { italics: true, size: 24, color: MID })] }));
  children.push(P({ spacing: { after: 240 }, children: [T(`${r.tag}${r.credit ? " — " + r.credit : ""}`, { italics: true, size: 22, color: MID })] }));
  children.push(P({ spacing: { after: 120 }, children: [T("Ingredients", { size: 26, bold: true, color: BROWN })] }));
  for (const ing of r.ingredients) children.push(P({ numbering: { reference: "bullets", level: 0 }, children: [T(ing, { size: 22 })] }));
  children.push(P({ spacing: { before: 240, after: 120 }, children: [T("Method", { size: 26, bold: true, color: BROWN })] }));
  for (const para of r.method) children.push(P({ spacing: { after: 180 }, children: [T(para, { size: 22 })] }));
  children.push(brk());
  // facing image page — fits inside this box, portrait or landscape
  children.push(...spacer(3));
  children.push(P({ alignment: AlignmentType.CENTER, children: [img(r.image, 150, 195)] }));
  if (r.image_status === 'placeholder')
    children.push(P({ alignment: AlignmentType.CENTER, spacing: { before: 120 }, children: [T("(placeholder — awaiting Tanya’s photograph)", { italics: true, size: 18, color: ACCENT })] }));
  if (i < recipes.length - 1) children.push(brk());
});

const doc = new Document({
  numbering: { config: [{ reference: "bullets", levels: [{ level: 0, format: LevelFormat.BULLET, text: "•", style: { paragraph: { indent: { left: 360, hanging: 200 } } } }] }] },
  sections: [{
    properties: { page: { margin: { top: convertMillimetersToTwip(22), bottom: convertMillimetersToTwip(22), left: convertMillimetersToTwip(24), right: convertMillimetersToTwip(24) } } },
    children
  }]
});

Packer.toBuffer(doc).then(buf => {
  fs.mkdirSync(path.join(ROOT, 'book'), { recursive: true });
  fs.writeFileSync(path.join(ROOT, 'book', 'Licina-Family-Recipe-Book.docx'), buf);
  console.log('book docx written,', recipes.length, 'recipes');
});
