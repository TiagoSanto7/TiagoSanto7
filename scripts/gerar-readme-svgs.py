"""Gera os SVGs do README de perfil (texto convertido em curvas, sem fontes externas).

Uso: pip install fonttools && FONTES=caminho/das/fontes/ python3 scripts/gerar-readme-svgs.py assets/readme
"""
import math, os, sys
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

F = os.environ.get('FONTES', 'fontes/')  # pasta com Anton.ttf, SG.ttf (Space Grotesk 400) e JBM.ttf (JetBrains Mono)
OUT = sys.argv[1]
os.makedirs(OUT, exist_ok=True)

AZUL, TINTA, CAMPO, PAPEL, BRANCO = '#1C33FF', '#0E0F14', '#04060F', '#EEEDE7', '#FAFAF7'

class Font:
    def __init__(self, path):
        self.f = TTFont(path)
        self.gs = self.f.getGlyphSet()
        self.cmap = self.f.getBestCmap()
        self.upm = self.f['head'].unitsPerEm
        self.hmtx = self.f['hmtx']
    def width(self, text, size, ls=0):
        s = size / self.upm
        return sum(self.hmtx[self.cmap.get(ord(c), self.cmap[ord('?')])][0] * s + ls for c in text) - ls
    def path(self, text, x, y, size, ls=0):
        s = size / self.upm
        pen = SVGPathPen(self.gs)
        cx = x
        for c in text:
            g = self.cmap.get(ord(c), self.cmap[ord('?')])
            tp = TransformPen(pen, (s, 0, 0, -s, cx, y))
            self.gs[g].draw(tp)
            cx += self.hmtx[g][0] * s + ls
        return pen.getCommands()

ANTON, SG, SG5, MONO = Font(F+'Anton.ttf'), Font(F+'SG.ttf'), None, Font(F+'JBM.ttf')

def txt(font, text, x, y, size, fill, ls=0, anchor='start'):
    if anchor == 'end':
        x -= font.width(text, size, ls)
    return f'<path fill="{fill}" d="{font.path(text, x, y, size, ls)}"/>'

# ---------- os quatro elementos ----------
def orbita(cx, cy, r, c, bg=None):
    o = []
    for a in (-22, 22):
        o.append(f'<ellipse cx="{cx}" cy="{cy}" rx="{r}" ry="{r*0.36:.1f}" transform="rotate({a} {cx} {cy})" fill="none" stroke="{c}" stroke-width="{r*0.035:.2f}"/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r*0.62:.1f}" fill="none" stroke="{c}" stroke-width="{r*0.035:.2f}" stroke-dasharray="{r*0.02:.2f} {r*0.07:.2f}" stroke-linecap="round"/>')
    o.append(f'<circle cx="{cx}" cy="{cy}" r="{r*0.09:.1f}" fill="{c}"/>')
    for a, rr in ((200, 0.06), (25, 0.05)):
        t = math.radians(a)
        px, py = r*math.cos(t), r*0.36*math.sin(t)
        rot = math.radians(-22 if a == 200 else 22)
        x = cx + px*math.cos(rot) - py*math.sin(rot)
        y = cy + px*math.sin(rot) + py*math.cos(rot)
        o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{r*rr:.1f}" fill="{c}"/>')
    return ''.join(o)

def mira(cx, cy, r, c):
    w = r*0.035
    ox = cx - r*0.06
    return (f'<line x1="{ox}" y1="{cy-r*0.85}" x2="{ox}" y2="{cy+r*0.85}" stroke="{c}" stroke-width="{w:.2f}"/>'
            f'<line x1="{cx-r*0.9}" y1="{cy}" x2="{cx+r*0.9}" y2="{cy}" stroke="{c}" stroke-width="{w:.2f}"/>'
            f'<path d="M{ox+r*0.42:.1f} {cy:.1f} A{r*0.42:.1f} {r*0.42:.1f} 0 1 1 {ox:.1f} {cy-r*0.42:.1f}" fill="none" stroke="{c}" stroke-width="{w:.2f}"/>')

def reticula(cx, cy, r, c):
    o, n = [], 11
    step = 2*r*0.8/(n-1)
    for i in range(n):
        for j in range(n):
            x = cx - r*0.8 + i*step
            y = cy - r*0.8 + j*step
            d = math.hypot(x-cx, (y-cy)*1.25)/(r*0.85)
            if d > 1: continue
            rad = step*0.46*(1-d)**0.9
            if rad < 0.7: continue
            o.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.2f}" fill="{c}"/>')
    return ''.join(o)

PIX = ["...X...",
       "..XXX..",
       "..X.X..",
       ".XXXXX.",
       ".XX.XX.",
       "XX...XX",
       "XXXXXXX"]
def pixel(cx, cy, r, c, scan=None):
    o, n = [], len(PIX)
    s = 2*r*0.72/n
    x0, y0 = cx - s*n/2, cy - s*n/2
    for j, row in enumerate(PIX):
        for i, ch in enumerate(row):
            if ch == 'X':
                o.append(f'<rect x="{x0+i*s:.1f}" y="{y0+j*s:.1f}" width="{s+0.3:.1f}" height="{s+0.3:.1f}" fill="{c}"/>')
    return ''.join(o)

ELEMENTOS = [orbita, mira, reticula, pixel]

def scanlines(id_, color, op):
    return (f'<pattern id="{id_}" width="4" height="4" patternUnits="userSpaceOnUse">'
            f'<rect width="4" height="1.2" fill="{color}" opacity="{op}"/></pattern>')

def marks(w, h, c, m=22, L=10):
    o = []
    for x, y in ((m, m), (w-m, m), (m, h-m), (w-m, h-m)):
        o.append(f'<path d="M{x-L} {y}H{x+L}M{x} {y-L}V{y+L}" stroke="{c}" stroke-width="1.2"/>')
    return ''.join(o)

def svg(w, h, body, title):
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{title}">'
            f'<title>{title}</title>{body}</svg>\n')

# ---------- header ----------
def header(theme):
    W, H = 1200, 520
    dark = theme == 'dark'
    bg = CAMPO if dark else PAPEL
    fg = BRANCO if dark else TINTA
    mute = '#8A8D99' if dark else '#6B6A66'
    b = []
    if dark:
        b.append(f'<defs>{scanlines("sl", "#FFFFFF", 0.035)}</defs>')
        b.append(f'<rect width="{W}" height="{H}" fill="{bg}"/><rect width="{W}" height="{H}" fill="url(#sl)"/>')
    else:
        b.append(f'<defs><pattern id="gr" width="40" height="40" patternUnits="userSpaceOnUse"><path d="M40 0H0V40" fill="none" stroke="{AZUL}" stroke-opacity="0.07" stroke-width="1"/></pattern></defs>')
        b.append(f'<rect width="{W}" height="{H}" fill="{bg}"/><rect width="{W}" height="{H}" fill="url(#gr)"/>')
        b.append(marks(W, H, TINTA))
    M = 64
    # topo
    b.append(f'<path d="M{M} 58 L{M+16} 67 L{M} 76 Z" fill="{fg}"/>')
    b.append(txt(MONO, 'TIAGO SANTO', M+30, 73, 17, fg, 1.5))
    b.append(txt(MONO, 'GITHUB · V1', W-M, 73, 17, fg, 1.5, 'end'))
    # titulo
    y1, y2, size = 214, 340, 106
    b.append(txt(ANTON, 'BUILDING', M, y1, size, fg, 1))
    word = 'AI AGENTS.'
    ww = ANTON.width(word, size, 1)
    pad = 18
    b.append(f'<rect x="{M-6}" y="{y2-size*0.86:.0f}" width="{ww+pad*2-6:.0f}" height="{size*1.06:.0f}" fill="{AZUL}"/>')
    if dark:
        b.append(f'<rect x="{M-6}" y="{y2-size*0.86:.0f}" width="{ww+pad*2-6:.0f}" height="{size*1.06:.0f}" fill="url(#sl)"/>')
    b.append(txt(ANTON, word, M+pad-6, y2, size, BRANCO, 1))
    # subtitulo
    b.append(txt(SG, 'Brazilian developer. AI Engineering postgrad.', M, 412, 22, mute))
    b.append(txt(SG, 'I orchestrate AI agents and connect software and hardware.', M, 442, 22, mute))
    # rodape
    b.append(txt(MONO, '+ PYTHON / AI AGENTS / IoT', M, H-36, 14, fg, 1.5))
    b.append(txt(MONO, 'BRAZIL · 2026', W-M, H-36, 14, fg, 1.5, 'end'))
    # grade de elementos
    cs, gap = 150, 16
    gx, gy = W - M - 2*cs - gap, 120
    for k, fn in enumerate(ELEMENTOS):
        x = gx + (k % 2)*(cs+gap); y = gy + (k//2)*(cs+gap)
        if k == 0:
            b.append(f'<rect x="{x}" y="{y}" width="{cs}" height="{cs}" fill="{AZUL}"/>')
            if dark: b.append(f'<rect x="{x}" y="{y}" width="{cs}" height="{cs}" fill="url(#sl)"/>')
            col = BRANCO
        else:
            col = BRANCO if dark else AZUL
            if not dark: b.append(f'<rect x="{x}" y="{y}" width="{cs}" height="{cs}" fill="{BRANCO}"/>')
        b.append(f'<rect x="{x+1}" y="{y+1}" width="{cs-2}" height="{cs-2}" fill="none" stroke="{BRANCO if dark else TINTA}" stroke-width="2"/>')
        b.append(fn(x+cs/2, y+cs/2, cs*0.38, col))
    return svg(W, H, ''.join(b), 'Tiago Santo — building AI agents')

# ---------- titulos de secao (modo laboratorio) ----------
def secao(num, nome, theme):
    W, H = 1200, 84
    dark = theme == 'dark'
    fg = BRANCO if dark else TINTA
    rule = '#30333F' if dark else '#C9C8C2'
    b = [f'<rect x="0" y="6" width="{W}" height="1.5" fill="{rule}"/>']
    b.append(txt(MONO, num, 0, 66, 18, AZUL if not dark else '#5C6CFF', 1))
    b.append(txt(ANTON, nome, 42, 70, 40, fg, 0.5))
    return svg(W, H, ''.join(b), f'{num} {nome}')

SECOES = [('01', 'ABOUT'), ('02', 'WHAT I DO'), ('03', 'IN PROGRESS'), ('04', 'CONTACT'), ('05', 'STATS')]

for t in ('dark', 'light'):
    open(f'{OUT}/header-{t}.svg', 'w').write(header(t))
    for n, nome in SECOES:
        open(f'{OUT}/secao-{n}-{t}.svg', 'w').write(secao(n, nome, t))
print('ok')
