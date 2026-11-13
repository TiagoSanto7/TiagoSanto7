"""Gera os cards de estatísticas do README (assets/readme/stats-{dark,light}.svg).

Roda no GitHub Actions (.github/workflows/stats.yml) com o GITHUB_TOKEN do próprio
workflow, então não depende de nenhum serviço externo.

Uso local: pip install fonttools && GITHUB_TOKEN=... python3 scripts/gerar-stats.py TiagoSanto7 assets/readme
Sem token, STATS_MOCK=1 gera com números de exemplo (só para testar o visual).
"""
import datetime, json, os, sys, urllib.request
from fontTools.ttLib import TTFont
from fontTools.pens.svgPathPen import SVGPathPen
from fontTools.pens.transformPen import TransformPen

AQUI = os.path.dirname(os.path.abspath(__file__))
F = os.path.join(AQUI, 'fontes') + '/'
AZUL, TINTA, CAMPO, PAPEL, BRANCO = '#1C33FF', '#0E0F14', '#04060F', '#EEEDE7', '#FAFAF7'
TONS = ['#1C33FF', '#5C6CFF', '#9AA4FF', '#C9CEFF', '#7A7D88']  # do azul para o neutro


class Font:
    def __init__(self, path):
        f = TTFont(path)
        self.gs, self.cmap = f.getGlyphSet(), f.getBestCmap()
        self.upm, self.hmtx = f['head'].unitsPerEm, f['hmtx']

    def _g(self, c):
        return self.cmap.get(ord(c), self.cmap[ord('?')])

    def width(self, text, size, ls=0):
        s = size / self.upm
        return sum(self.hmtx[self._g(c)][0] * s + ls for c in text) - ls

    def path(self, text, x, y, size, ls=0):
        s = size / self.upm
        pen, cx = SVGPathPen(self.gs), x
        for c in text:
            g = self._g(c)
            self.gs[g].draw(TransformPen(pen, (s, 0, 0, -s, cx, y)))
            cx += self.hmtx[g][0] * s + ls
        return pen.getCommands()


ANTON, SG, MONO = Font(F + 'Anton.ttf'), Font(F + 'SG.ttf'), Font(F + 'JBM.ttf')


def txt(font, text, x, y, size, fill, ls=0, anchor='start'):
    if anchor == 'end':
        x -= font.width(text, size, ls)
    d = font.path(text, x, y, size, ls)
    return f'<path fill="{fill}" d="{d}"/>' if d else ''


QUERY = """
query($login: String!, $after: String) {
  user(login: $login) {
    pullRequests { totalCount }
    followers { totalCount }
    contributionsCollection { contributionCalendar { totalContributions } }
    repositories(ownerAffiliations: OWNER, privacy: PUBLIC, isFork: false, first: 100, after: $after) {
      totalCount
      pageInfo { hasNextPage endCursor }
      nodes {
        stargazerCount
        languages(first: 10, orderBy: {field: SIZE, direction: DESC}) { edges { size node { name } } }
      }
    }
  }
}"""


def buscar(login, token):
    stats = {'repos': 0, 'stars': 0, 'langs': {}}
    after = None
    while True:
        body = json.dumps({'query': QUERY, 'variables': {'login': login, 'after': after}}).encode()
        req = urllib.request.Request('https://api.github.com/graphql', data=body, headers={
            'Authorization': f'bearer {token}', 'Content-Type': 'application/json', 'User-Agent': 'readme-stats'})
        data = json.load(urllib.request.urlopen(req, timeout=30))
        if data.get('errors'):
            raise SystemExit(f'Erro da API do GitHub: {data["errors"]}')
        u = data['data']['user']
        r = u['repositories']
        stats['repos'] = r['totalCount']
        stats['prs'] = u['pullRequests']['totalCount']
        stats['followers'] = u['followers']['totalCount']
        stats['contrib'] = u['contributionsCollection']['contributionCalendar']['totalContributions']
        for n in r['nodes']:
            stats['stars'] += n['stargazerCount']
            for e in n['languages']['edges']:
                stats['langs'][e['node']['name']] = stats['langs'].get(e['node']['name'], 0) + e['size']
        if not r['pageInfo']['hasNextPage']:
            return stats
        after = r['pageInfo']['endCursor']


def fmt(n):
    return f'{n/1000:.1f}K'.replace('.0K', 'K') if n >= 1000 else str(n)


def card(s, theme, hoje):
    W, H, M = 1200, 440, 56
    dark = theme == 'dark'
    bg, fg = (CAMPO, BRANCO) if dark else (PAPEL, TINTA)
    mute = '#8A8D99' if dark else '#6B6A66'
    rule = '#262938' if dark else '#C9C8C2'
    b = []
    if dark:
        b.append('<defs><pattern id="sl" width="4" height="4" patternUnits="userSpaceOnUse">'
                 '<rect width="4" height="1.2" fill="#FFFFFF" opacity="0.035"/></pattern></defs>')
        b.append(f'<rect width="{W}" height="{H}" fill="{bg}"/><rect width="{W}" height="{H}" fill="url(#sl)"/>')
    else:
        b.append(f'<rect width="{W}" height="{H}" fill="{bg}"/>')
        for x, y in ((22, 22), (W - 22, 22), (22, H - 22), (W - 22, H - 22)):
            b.append(f'<path d="M{x-10} {y}H{x+10}M{x} {y-10}V{y+10}" stroke="{TINTA}" stroke-width="1.2"/>')

    # topo
    b.append(f'<path d="M{M} 52 L{M+14} 60 L{M} 68 Z" fill="{fg}"/>')
    b.append(txt(MONO, 'GITHUB / ' + s['login'].upper(), M + 26, 66, 15, fg, 1.5))
    b.append(txt(MONO, 'UPDATED ' + hoje, W - M, 66, 15, mute, 1.5, 'end'))
    b.append(f'<rect x="{M}" y="88" width="{W-2*M}" height="1.5" fill="{rule}"/>')

    # números (2 x 2)
    itens = [('CONTRIBUTIONS', 'LAST 12 MONTHS', s['contrib']), ('PUBLIC REPOS', 'OWNED', s['repos']),
             ('PULL REQUESTS', 'ALL TIME', s['prs']), ('STARS', 'EARNED', s['stars'])]
    cw = 250
    for k, (rot, sub, val) in enumerate(itens):
        x = M + (k % 2) * cw
        y = 200 + (k // 2) * 140
        num = fmt(val)
        if k == 0:  # destaque em bloco azul, como no guia
            w = ANTON.width(num, 74, 1)
            b.append(f'<rect x="{x-6}" y="{y-68}" width="{w+20:.0f}" height="80" fill="{AZUL}"/>')
            if dark:
                b.append(f'<rect x="{x-6}" y="{y-68}" width="{w+20:.0f}" height="80" fill="url(#sl)"/>')
            b.append(txt(ANTON, num, x + 4, y, 74, BRANCO, 1))
        else:
            b.append(txt(ANTON, num, x, y, 74, fg, 1))
        b.append(txt(MONO, '+ ' + rot, x, y + 30, 13, fg, 1.2))
        b.append(txt(MONO, sub, x + 18, y + 48, 11, mute, 1.2))

    # linguagens
    lx, lw = 640, W - M - 640
    b.append(f'<rect x="{lx-40}" y="120" width="1.5" height="{H-160}" fill="{rule}"/>')
    b.append(txt(MONO, '+ TOP LANGUAGES', lx, 134, 13, fg, 1.2))
    langs = sorted(s['langs'].items(), key=lambda kv: -kv[1])
    total = sum(v for _, v in langs) or 1
    top = langs[:4]
    resto = total - sum(v for _, v in top)
    if resto > 0:
        top.append(('Other', resto))
    if not top:
        b.append(txt(SG, 'No public code yet.', lx, 200, 20, mute))
    x = lx
    for i, (nome, v) in enumerate(top):
        w = lw * v / total
        b.append(f'<rect x="{x:.1f}" y="158" width="{max(w-3, 1):.1f}" height="22" fill="{TONS[i]}"/>')
        x += w
    for i, (nome, v) in enumerate(top):
        y = 230 + i * 34
        b.append(f'<rect x="{lx}" y="{y-13}" width="14" height="14" fill="{TONS[i]}"/>')
        b.append(txt(SG, nome, lx + 26, y, 20, fg))
        b.append(txt(MONO, f'{100*v/total:.1f}%', W - M, y, 15, mute, 1, 'end'))

    titulo = f'GitHub stats for {s["login"]}'
    return (f'<svg xmlns="http://www.w3.org/2000/svg" width="{W}" height="{H}" viewBox="0 0 {W} {H}" '
            f'role="img" aria-label="{titulo}"><title>{titulo}</title>{"".join(b)}</svg>\n')


def main():
    login, out = sys.argv[1], sys.argv[2]
    if os.environ.get('STATS_MOCK'):
        s = {'repos': 12, 'stars': 34, 'prs': 27, 'followers': 8, 'contrib': 486,
             'langs': {'Python': 620000, 'JavaScript': 180000, 'HTML': 90000, 'C++': 60000, 'Shell': 20000, 'CSS': 9000}}
    else:
        s = buscar(login, os.environ['GITHUB_TOKEN'])
    s['login'] = login
    hoje = datetime.date.today().isoformat()
    os.makedirs(out, exist_ok=True)
    for t in ('dark', 'light'):
        with open(os.path.join(out, f'stats-{t}.svg'), 'w') as f:
            f.write(card(s, t, hoje))
    print(json.dumps({k: v for k, v in s.items() if k != 'langs'}))


if __name__ == '__main__':
    main()
