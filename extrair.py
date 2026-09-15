# Extrai do .ai tudo que o gerador precisa: camadas (base, máscara da foto, personagem),
# textos com posição/estilo exatos e o banco de fotos.
# Rodar de novo sempre que o .ai ou as fotos mudarem:   python extrair.py
# (fotos já convertidas são puladas; apague banco/ para refazer)
import collections, io, json, pathlib, re, statistics, unicodedata
import numpy as np
import pymupdf as fitz
import pymupdf.mupdf as mupdf
from fontTools.ttLib import TTFont
from PIL import Image, ImageOps

AQUI = pathlib.Path(__file__).parent
SRC = AQUI.parent / 'Layout - Agentes de viagem.ai'
BANCO_SRC = pathlib.Path(r'D:\Design\Village Resort\08 Fotos\Fotos Boas')
NOMES = ['1 pacote', '2 pacotes']
DPI = 144                          # canvas trabalha em 2x (1 pt = 2 px)
FOTO_LADO, MINI_LADO = 2400, 400
PESOS = {'Medium': 500, 'SemiBold': 600, 'Bold': 700, 'ExtraBold': 800, 'Black': 900}
PLANAS = set('EFHIKLMNTVWXYZ')     # letras sem overshoot: base e altura confiáveis


class Fonte:
    def __init__(self, nome):
        f = TTFont(AQUI / 'fonts' / f'{nome}.ttf')
        self.upm, self.cmap, self.hmtx, self.glyf = f['head'].unitsPerEm, f.getBestCmap(), f['hmtx'], f['glyf']
        self.cap = f['OS/2'].sCapHeight / self.upm

    def adv(self, s):
        return sum(self.hmtx[self.cmap[ord(c)]][0] for c in s) / self.upm

    def tinta(self, c):
        g = self.glyf[self.cmap[ord(c)]]
        return g.xMin / self.upm, g.xMax / self.upm


_fontes = {}
def fonte(nome):
    return _fontes.setdefault(nome, Fonte(nome))


def cor(c):
    return '#%02x%02x%02x' % tuple(round(v * 255) for v in c)


def slug(t):
    t = unicodedata.normalize('NFKD', t).encode('ascii', 'ignore').decode().lower()
    return re.sub(r'[^a-z0-9]+', '-', t).strip('-')[:40]


def ret(r):
    return [round(v, 2) for v in r]


TRACO = (mupdf.FZ_CULL_PATH_STROKE, mupdf.FZ_CULL_PATH_FILL_STROKE)
PREENCHE = (mupdf.FZ_CULL_PATH_FILL, mupdf.FZ_CULL_PATH_FILL_STROKE)


def filtrar(p, decidir, atualizar):
    """Passa o conteúdo pelo filtro do MuPDF; decidir(i, tipo, caixa_pdf) -> True descarta o objeto i."""
    cont = [0]

    class Opcoes(mupdf.PdfSanitizeFilterOptions2):
        def __init__(self):
            super().__init__()
            self.use_virtual_culler()

        def culler(self, ctx, bbox, tipo):
            r = bbox if hasattr(bbox, 'x0') else mupdf.FzRect(bbox)
            cont[0] += 1
            return int(bool(decidir(cont[0] - 1, tipo, (r.x0, r.y0, r.x1, r.y1))))

    opcoes = Opcoes()
    pp = fitz._as_pdf_page(p.this)
    mupdf.pdf_filter_page_contents(pp.doc(), pp, fitz._make_PdfFilterOptions(
        recurse=1, instance_forms=1, no_update=0 if atualizar else 1, sanitize=1, sopts=opcoes))


def subcaminhos(d):
    """Caixa de cada subcaminho do desenho (começa um novo quando o segmento não continua o anterior)."""
    grupos, atual, fim = [], [], None
    for it in d['items']:
        if it[0] in ('re', 'qu'):
            grupos.append(list(fitz.Rect(it[1]).quad if it[0] == 're' else it[1]))
            fim = None
            continue
        pts = list(it[1:])
        if fim is None or abs(pts[0].x - fim.x) > 0.01 or abs(pts[0].y - fim.y) > 0.01:
            if atual:
                grupos.append(atual)
            atual = []
        atual += pts
        fim = pts[-1]
    if atual:
        grupos.append(atual)
    return [fitz.Rect(min(q.x for q in g), min(q.y for q in g), max(q.x for q in g), max(q.y for q in g))
            for g in grupos]


def remover_desenhos(p, desenhos):
    """Tira do PDF exatamente estes desenhos. A remoção por área do PyMuPDF não pega caminhos
    dentro de grupo com recorte (o título do .ai), então casa um a um pela caixa que o MuPDF vê."""
    H = p.rect.height
    vistos = []
    filtrar(p, lambda i, t, c: vistos.append((i, t, c)), atualizar=False)
    pares = []
    for a, d in enumerate(desenhos):
        e = (d.get('width') or 0) / 2 if d['type'] == 's' else 0  # traço: caixa do caminho + meia espessura
        tipos = TRACO if d['type'] == 's' else PREENCHE
        # o PyMuPDF junta objetos seguidos de mesmo estilo num desenho só ("Ã" = letra + til, "d" = bojo + haste):
        # além da caixa inteira, cada subcaminho vira candidato (folga 3: cópias do contorno ficam a 2pt)
        subs = subcaminhos(d)
        caixas = [(d['rect'], max(2, 2 * e))] + ([(r, 3) for r in subs] if len(subs) > 1 else [])
        for k, (r, tol) in enumerate(caixas):
            alvo = (r.x0 - e, H - r.y1 - e, r.x1 + e, H - r.y0 + e)  # PDF tem y pra cima
            pares += [(dist, (a, k), i) for i, t, c in vistos if t in tipos
                      and (dist := max(abs(x - y) for x, y in zip(c, alvo))) <= tol]
    usadas, cortar, casados = set(), set(), set()
    for dist, ak, i in sorted(pares):  # mais próximos primeiro; cada caixa e cada objeto uma vez só
        if ak not in usadas and i not in cortar:
            usadas.add(ak)
            cortar.add(i)
            casados.add(ak[0])
    # 2ª passada: descartar muda a sequência de chamadas, então casa por tipo + caixa, não por posição
    restantes = collections.Counter((t, tuple(round(v, 2) for v in c)) for i, t, c in vistos if i in cortar)

    def decidir(i, t, c):
        k = (t, tuple(round(v, 2) for v in c))
        if restantes[k] > 0:
            restantes[k] -= 1
            return True
        return False

    filtrar(p, decidir, atualizar=True)
    return len(desenhos) - len(casados)


def sem_texto(p, vetores=fitz.PDF_REDACT_LINE_ART_NONE):
    p.add_redact_annot(p.rect, fill=False)
    p.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE, graphics=vetores, text=fitz.PDF_REDACT_TEXT_REMOVE)


# ---------------------------------------------------------------- textos
def ler_linhas(p):
    tam_real = {}  # texttrace dá o tamanho horizontal; rawdict o vertical (escala vertical)
    for t in p.get_texttrace():
        for c in t['chars']:
            tam_real[(round(c[2][0], 1), round(c[2][1], 1))] = t['size']
    linhas = []
    for bi, b in enumerate(p.get_text('rawdict')['blocks']):
        if b['type']:
            continue
        for s in (s for l in b['lines'] for s in l['spans']):
            chars = list(s['chars'])
            while chars and chars[-1]['c'].isspace():
                chars.pop()
            if not chars:
                continue
            nome = s['font']
            tam = tam_real.get((round(s['origin'][0], 1), round(s['origin'][1], 1)), s['size'])
            F = fonte(nome)
            difs = [chars[i + 1]['origin'][0] - chars[i]['origin'][0] - F.adv(chars[i]['c']) * tam
                    for i in range(len(chars) - 1)]
            ls = round(statistics.median(difs), 2) if difs else 0
            linhas.append(dict(
                txt=''.join(c['c'] for c in chars), bloco=bi, fonte=nome, peso=PESOS[nome.split('-')[1]],
                x=s['origin'][0], y=s['origin'][1], x1=chars[-1]['bbox'][2], tam=tam,
                vscale=round(s['size'] / tam, 3) if s['size'] / tam > 1.01 else 1,
                cor='#%06x' % s['color'], ls=ls if abs(ls) >= 0.3 else 0, bbox=fitz.Rect(s['bbox'])))
    return linhas


def agrupar(linhas):
    """Linhas seguidas do mesmo bloco e estilo viram um parágrafo."""
    elems = []
    for l in linhas:
        e = elems[-1] if elems else None
        if (e and e['bloco'] == l['bloco'] and (e['peso'], e['tam'], e['cor']) == (l['peso'], l['tam'], l['cor'])
                and abs(e['x'] - l['x']) < 0.5 and 0 < l['y'] - e['linhas'][-1]['y'] < 1.6 * l['tam']):
            e['linhas'].append(l)
            e['bbox'] |= l['bbox']
        else:
            elems.append(dict(l, linhas=[l], bbox=fitz.Rect(l['bbox']), tracos=[]))
    for e in elems:
        e['txt'] = ' '.join(l['txt'] for l in e['linhas'])
    return elems


def largura_quebra(e):
    ls = e['linhas']
    if len(ls) == 1:
        return None
    F, larg = fonte(e['fonte']), [l['x1'] - l['x'] for l in ls]
    limites = [larg[i] + (F.adv(' ' + ls[i + 1]['txt'].split(' ')[0])) * e['tam'] for i in range(len(ls) - 1)]
    lo, hi = max(larg), min(limites)
    return round((lo + hi) / 2, 1) if hi > lo else round(lo + 1, 1)


def estilo_traco(tracos, glifos):
    ts = sorted(tracos, key=lambda d: d['seqno'])
    n = max(1, round(len(ts) / glifos))
    grupos = [ts[i * len(ts) // n:(i + 1) * len(ts) // n] for i in range(n)]
    y0 = [min(d['rect'].y0 for d in g) for g in grupos]
    return dict(larg=round(statistics.median(d['width'] for d in ts), 1), cor=cor(ts[0]['color']),
                dys=[round(y - y0[-1], 1) for y in y0])


def ler_arte(p):
    elems = agrupar(ler_linhas(p))
    # contornos de texto (ex.: "7x de", título): traços pequenos em volta do texto
    tracos = [d for d in p.get_drawings() if d['type'] == 's' and (d.get('width') or 0) >= 5
              and d['rect'].width < 200 and d['rect'].height < 200]
    soltos = []
    for d in tracos:
        cands = [e for e in elems if (e['bbox'] + (-15, -15, 15, 15)).contains(d['rect'])]
        if cands:
            min(cands, key=lambda e: e['bbox'].get_area())['tracos'].append(d)
        else:
            soltos.append(d)

    arte = dict(textos=[], remover=[d for e in elems for d in e['tracos']], titulo=None, valores={})
    usados = set()

    # preço = número grande + centavos na mesma linha
    precos = []
    for e in elems:
        if len(e['linhas']) == 1 and e['txt'].isdigit() and e['tam'] > 80:
            c = next(c for c in elems if re.fullmatch(r',\d{2}', c['txt']) and abs(c['y'] - e['y']) < 1)
            precos.append((e, c))
            usados |= {id(e), id(c)}
    precos.sort(key=lambda pc: pc[0]['y'])
    for n, (e, c) in enumerate(precos, 1):
        arte['textos'].append(dict(tipo='preco', key=f'preco_{n}', x=e['x'], y=e['y'], peso=e['peso'], tam=e['tam'],
                                   tamCents=c['tam'], cor=e['cor'], larg=round(c['x1'] - e['x'], 2)))
        arte['valores'][f'preco_{n}'] = e['txt'] + c['txt']

    # datas: pertencem ao preço logo acima; esquerda = ida, direita = volta
    datas = [e for e in elems if re.fullmatch(r'\d{2}/\d{2}/\d{4}', e['txt'])]
    for e in datas:
        n = max(i for i, (pe, _) in enumerate(precos, 1) if pe['y'] < e['y'])
        par = sorted((d for d in datas if abs(d['y'] - e['y']) < 1), key=lambda d: d['x'])
        key = f"{'ida' if par.index(e) == 0 else 'volta'}_{n}"
        arte['textos'].append(dict(tipo='texto', key=key, x=e['x'], y=e['y'], peso=e['peso'], tam=e['tam'],
                                   cor=e['cor'], ls=0, tab=True))
        d, m, a = e['txt'].split('/')
        arte['valores'][key] = f'{a}-{m}-{d}'
        usados.add(id(e))

    # título com texto vivo: contorno grosso (>= 20pt)
    tit = [e for e in elems if e['tracos'] and statistics.median(d['width'] for d in e['tracos']) >= 20]
    if tit:
        tit.sort(key=lambda e: e['y'])
        glifos = sum(1 for e in tit for ch in e['txt'] if not ch.isspace())
        arte['titulo'] = dict(tipo='titulo', traco=estilo_traco([d for e in tit for d in e['tracos']], glifos),
                              linhas=[dict(key=f'titulo{i}', x=e['x'], y=e['y'], peso=e['peso'], fonte=e['fonte'],
                                           tam=e['tam'], cor=e['cor'], ls=e['ls']) for i, e in enumerate(tit, 1)])
        for i, e in enumerate(tit, 1):
            arte['valores'][f'titulo{i}'] = e['txt']
            usados.add(id(e))

    # título em desenho (efeito de distorção vira curva no PDF): ajustado depois, com o texto da outra arte
    grossos = [d for d in soltos if d['width'] >= 20]
    if grossos:
        area = fitz.Rect()
        for d in grossos:
            area |= d['rect']
        primeiro = min(d['seqno'] for d in grossos)  # letras vêm depois do contorno; enfeites do fundo, antes
        glifos = sorted((d for d in p.get_drawings() if d['type'] == 'f' and d['seqno'] > primeiro
                         and (area + (-5, -5, 5, 5)).contains(d['rect']) and d['rect'].height > 30),
                        key=lambda d: (d['rect'].y0 + d['rect'].y1) / 2)
        linhas, atual = [], [glifos[0]]
        for d in glifos[1:]:
            yc = lambda g: (g['rect'].y0 + g['rect'].y1) / 2
            if yc(d) - yc(atual[-1]) > 20:
                linhas.append(atual)
                atual = []
            atual.append(d)
        linhas.append(atual)
        arte['titulo_desenho'] = dict(linhas=[sorted(l, key=lambda d: d['rect'].x0) for l in linhas],
                                      traco=grossos)
        arte['remover'] += grossos + glifos

    for e in elems:
        if id(e) in usados:
            continue
        t = e['txt']
        abaixo_das_datas = any(0 < e['y'] - d['y'] < 80 and abs(e['x'] - d['x']) < 40 for d in datas)  # local, com alfinete
        key = ('parcelas' if re.fullmatch(r'\d+x de', t) else 'telefone' if re.search(r'\(\d{2}\)\s*\d', t)
               else 'site' if re.search(r'\.com|www\.', t, re.I) else 'local' if abaixo_das_datas else slug(t))
        el = dict(tipo='texto', key=key, x=e['x'], y=e['y'], peso=e['peso'], tam=e['tam'], cor=e['cor'], ls=e['ls'])
        if e['vscale'] != 1:
            el['vscale'] = e['vscale']
        if len(e['linhas']) > 1:
            el['lh'] = round(e['linhas'][1]['y'] - e['linhas'][0]['y'], 2)
            el['quebra'] = largura_quebra(e)
        else:
            el['maxW'] = round((e['x1'] - e['x']) * 1.3, 1)
        if e['tracos']:
            el['traco'] = estilo_traco(e['tracos'], sum(1 for ch in t if not ch.isspace()))
        arte['textos'].append(el)
        arte['valores'][key] = t
    return arte


def ajustar_titulo_desenho(td, ref, valores):
    """Mede a curva (distorção bandeira) e o espaçamento a partir das letras desenhadas."""
    F = fonte(ref['linhas'][0]['fonte'])
    linhas, pontos = [], []
    for li, (glifos, lr) in enumerate(zip(td['linhas'], ref['linhas'])):
        txt = valores[lr['key']]
        chars = [(j, c) for j, c in enumerate(txt) if not c.isspace()]
        assert len(chars) == len(glifos), f'título: {len(glifos)} letras desenhadas x "{txt}"'
        planas = [g['rect'].height for (j, c), g in zip(chars, glifos) if c in PLANAS]
        tam = statistics.median(planas) / F.cap
        A, b = [], []
        for (j, c), g in zip(chars, glifos):
            pen = F.adv(txt[:j]) * tam
            x0, x1 = F.tinta(c)
            A += [[1, j], [1, j]]
            b += [g['rect'].x0 - pen - x0 * tam, g['rect'].x1 - pen - x1 * tam]
            if c in PLANAS:
                pontos.append((li, (g['rect'].x0 + g['rect'].x1) / 2, g['rect'].y1))
        (x, ls), *_ = np.linalg.lstsq(np.array(A, float), np.array(b), rcond=None)
        linhas.append(dict(key=lr['key'], x=round(x, 2), peso=ref['linhas'][li]['peso'], fonte=ref['linhas'][li]['fonte'],
                           tam=round(tam, 2), cor=cor(glifos[0]['fill']), ls=round(ls, 2)))
    # base de cada linha: c_linha + a·u + b·u² + d·u³ (u = x/1000), mesma curva para as linhas
    nl = len(linhas)
    M = np.array([[1 if li == k else 0 for k in range(nl)] + [x / 1000, (x / 1000) ** 2, (x / 1000) ** 3]
                  for li, x, _ in pontos])
    coef, *_ = np.linalg.lstsq(M, np.array([y for *_, y in pontos]), rcond=None)
    resid = max(abs(M @ coef - np.array([y for *_, y in pontos])))
    xs = [x for _, x, _ in pontos]
    for li, l in enumerate(linhas):
        l['y'] = round(coef[li], 2)
        l['curva'] = dict(a=round(coef[nl], 4), b=round(coef[nl + 1], 4), d=round(coef[nl + 2], 4),
                          xmin=round(min(xs), 1), xmax=round(max(xs), 1))
    glifos = sum(len(g) for g in td['linhas'])
    print(f'  título em desenho: tamanho {linhas[0]["tam"]}, erro máx. da curva {resid:.2f}pt')
    return dict(tipo='titulo', traco=estilo_traco(td['traco'], glifos), linhas=linhas)


# ---------------------------------------------------------------- camadas
def camadas(pno, remover):
    n = pno + 1
    info = fitz.open(SRC)[pno].get_image_info(xrefs=True)
    foto = max(info, key=lambda im: im['width'] * im['height'])
    outras = sorted({im['xref'] for im in info if im['xref'] != foto['xref']})

    doc = fitz.open(SRC)
    p = doc[pno]
    if remover:  # contornos e título em desenho: o canvas redesenha
        faltam = remover_desenhos(p, remover)
        if faltam:
            print(f'  aviso: {faltam} de {len(remover)} desenhos de título/contorno não achados no PDF')
        p = doc.reload_page(p)
    sem_texto(p)
    for x in [foto['xref'], *outras]:
        p.delete_image(x)
    base = p.get_pixmap(dpi=DPI, alpha=True)
    base.save(AQUI / f'camadas/arte{n}-base.png')
    base_a = np.frombuffer(base.samples, np.uint8).reshape(base.height, base.width, 4)[..., 3]

    doc = fitz.open(SRC)
    p = doc[pno]
    sem_texto(p, fitz.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED)
    for x in outras:
        p.delete_image(x)
    pix = p.get_pixmap(dpi=DPI, alpha=True)
    alfa = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 4)[..., 3]
    zeros = np.zeros_like(alfa)
    Image.fromarray(np.dstack([zeros, zeros, zeros, alfa]), 'RGBA').save(AQUI / f'camadas/arte{n}-mascara.png')
    ys, xs = np.nonzero(alfa)
    vy, vx = np.nonzero((alfa > 0) & (base_a < 128))
    k = 72 / DPI
    spec = dict(mascara=f'camadas/arte{n}-mascara.png', base=f'camadas/arte{n}-base.png',
                box=[xs.min() * k, ys.min() * k, (xs.max() + 1) * k, (ys.max() + 1) * k],
                visivel=[vx.min() * k, vy.min() * k, (vx.max() + 1) * k, (vy.max() + 1) * k],
                original=ret(foto['bbox']), personagem=None)

    for x in outras:
        doc = fitz.open(SRC)
        p = doc[pno]
        sem_texto(p, fitz.PDF_REDACT_LINE_ART_REMOVE_IF_TOUCHED)
        for y in [foto['xref'], *[o for o in outras if o != x]]:
            p.delete_image(y)
        pix = p.get_pixmap(dpi=DPI, alpha=True)
        a = np.frombuffer(pix.samples, np.uint8).reshape(pix.height, pix.width, 4)[..., 3]
        ys, xs = np.nonzero(a)
        if not len(xs):
            continue  # imagem escondida
        caixa = (xs.min(), ys.min(), xs.max() + 1, ys.max() + 1)
        Image.open(io.BytesIO(pix.tobytes('png'))).crop(caixa).save(AQUI / f'camadas/arte{n}-personagem.png')
        spec['personagem'] = dict(src=f'camadas/arte{n}-personagem.png', rect=[v * k for v in caixa])
    spec['box'], spec['visivel'] = ret(spec['box']), ret(spec['visivel'])
    if spec['personagem']:
        spec['personagem']['rect'] = ret(spec['personagem']['rect'])
    return spec, foto['xref']


# ---------------------------------------------------------------- banco
def salvar_foto(img, nome, cat, itens):
    f, m = AQUI / f'banco/fotos/{nome}.jpg', AQUI / f'banco/mini/{nome}.jpg'
    if not f.exists():
        im = img.convert('RGB')
        im.thumbnail((FOTO_LADO, FOTO_LADO), Image.LANCZOS)
        im.save(f, quality=82)
        im.thumbnail((MINI_LADO, MINI_LADO), Image.LANCZOS)
        im.save(m, quality=75)
    itens.append(dict(id=nome, cat=cat, src=f'banco/fotos/{nome}.jpg', mini=f'banco/mini/{nome}.jpg'))


def banco(doc, xref_layout):
    itens = []
    pix = fitz.Pixmap(doc, xref_layout)
    if pix.n - pix.alpha != 3:
        pix = fitz.Pixmap(fitz.csRGB, pix)
    salvar_foto(Image.open(io.BytesIO(pix.tobytes('png'))), 'layout', 'Foto da arte', itens)
    arquivos = sorted(f for f in BANCO_SRC.rglob('*') if f.suffix.lower() in ('.jpg', '.jpeg', '.png'))
    for f in sorted(arquivos, key=lambda f: (f.parent == BANCO_SRC, f.parent.name, f.name)):
        cat = 'Gerais' if f.parent == BANCO_SRC else f.parent.name
        salvar_foto(ImageOps.exif_transpose(Image.open(f)), slug(f'{cat}-{f.stem}'), cat, itens)
    return itens


# ---------------------------------------------------------------- principal
def main():
    for d in ('camadas', 'banco/fotos', 'banco/mini'):
        (AQUI / d).mkdir(parents=True, exist_ok=True)
    doc = fitz.open(SRC)
    assert doc.page_count == len(NOMES), f'o .ai tem {doc.page_count} artes; ajuste NOMES em extrair.py'
    artes = [ler_arte(p) for p in doc]
    valores = {}
    for a in artes:
        for k, v in a['valores'].items():
            valores.setdefault(k, v)
    ref = next(a['titulo'] for a in artes if a['titulo'])
    layouts, xref = [], None
    for pno, a in enumerate(artes):
        print(f'arte {pno + 1}: {NOMES[pno]}')
        if a.get('titulo_desenho'):
            a['titulo'] = ajustar_titulo_desenho(a['titulo_desenho'], ref, valores)
        foto, xref = camadas(pno, a['remover'])
        textos = sorted(a['textos'], key=lambda t: t['tipo'] != 'preco')  # preço embaixo do "7x de"
        layouts.append(dict(nome=NOMES[pno], foto=foto, textos=textos + ([a['titulo']] if a['titulo'] else [])))
        print(f'  {len(textos)} textos, personagem: {"sim" if foto["personagem"] else "não"}')
    itens = banco(doc, xref)
    print(f'banco: {len(itens)} fotos')
    js = ('// gerado por extrair.py – não editar à mão\n'
          f'const LAYOUTS = {json.dumps(layouts, ensure_ascii=False)};\n'
          f'const VALORES = {json.dumps(valores, ensure_ascii=False)};\n'
          f'const BANCO = {json.dumps(itens, ensure_ascii=False)};\n')
    (AQUI / 'dados.js').write_text(js, encoding='utf-8')


if __name__ == '__main__':
    main()
