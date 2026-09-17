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
# prancheta do .ai -> arte do gerador; a 3ª prancheta (story antigo do designer) fica de fora
PRANCHETAS = [(0, '1 pacote'), (1, '2 pacotes'), (3, 'Story'), (4, 'Feed'), (6, 'Últimas vagas'), (5, 'Carrossel')]
TITULO_FIXO = {3, 4, 5, 6}  # título reto em desenho: fica na camada de base, sem edição
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
    tam_real, ordem = {}, {}  # texttrace dá o tamanho horizontal (rawdict o vertical) e a ordem de desenho
    for t in p.get_texttrace():
        for c in t['chars']:
            tam_real[(round(c[2][0], 1), round(c[2][1], 1))] = t['size']
            ordem[(round(c[2][0], 1), round(c[2][1], 1))] = t['seqno']
    linhas, vistos = [], set()
    for bi, b in enumerate(p.get_text('rawdict')['blocks']):
        if b['type']:
            continue
        for s in (s for l in b['lines'] for s in l['spans']):
            chars = list(s['chars'])
            while chars and chars[-1]['c'].isspace():
                chars.pop()
            while chars and chars[0]['c'].isspace():  # " Village Resort, MG" logo depois do rótulo
                chars.pop(0)
            txt = ''.join(c['c'] for c in chars)
            chave = (txt, round(chars[0]['origin'][0]) if chars else 0, round(s['origin'][1]))
            if not chars or chave in vistos:  # o .ai tem cópias do mesmo texto no mesmo lugar
                continue
            vistos.add(chave)
            # "7x de 750": parcelas e preço riscado vêm no mesmo texto; cada um vira um campo
            m = re.fullmatch(r'(\d+x de)\s+(\S+)', txt)
            for cs in ([chars[:len(m.group(1))], chars[m.start(2):]] if m else [chars]):
                nome = s['font']
                tam = tam_real.get((round(cs[0]['origin'][0], 1), round(cs[0]['origin'][1], 1)), s['size'])
                F = fonte(nome)
                difs = [cs[i + 1]['origin'][0] - cs[i]['origin'][0] - F.adv(cs[i]['c']) * tam
                        for i in range(len(cs) - 1)]
                ls = round(statistics.median(difs), 2) if difs else 0
                linhas.append(dict(
                    txt=''.join(c['c'] for c in cs), bloco=bi, fonte=nome, peso=PESOS[nome.split('-')[1]],
                    x=cs[0]['origin'][0], y=s['origin'][1], x1=cs[-1]['bbox'][2], tam=tam,
                    vscale=round(s['size'] / tam, 3) if s['size'] / tam > 1.01 else 1,
                    cor='#%06x' % s['color'], ls=ls if abs(ls) >= 0.3 else 0,
                    seqno=ordem.get((round(cs[0]['origin'][0], 1), round(cs[0]['origin'][1], 1)), 0),
                    bbox=fitz.Rect(cs[0]['bbox'][0], s['bbox'][1], cs[-1]['bbox'][2], s['bbox'][3])))
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


def ler_arte(p, titulo_fixo=False):
    desenhos = p.get_drawings()
    # texto coberto por um fundo desenhado depois dele não aparece no .ai (ex.: caixa antiga atrás da nova)
    elems = [e for e in agrupar(ler_linhas(p))
             if not any('f' in d['type'] and d['seqno'] > e['seqno'] and d['rect'].contains(e['bbox']) for d in desenhos)]
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
            c = min((c for c in elems if re.fullmatch(r',\d{2}', c['txt']) and abs(c['y'] - e['y']) < 25 and c['x'] > e['x']),
                    key=lambda c: abs(c['x'] - e['x']) + abs(c['y'] - e['y']))  # centavos podem descer um pouco (arte nova)
            precos.append((e, c))
            usados |= {id(e), id(c)}
    precos.sort(key=lambda pc: pc[0]['y'])
    for n, (e, c) in enumerate(precos, 1):
        arte['textos'].append(dict(tipo='preco', key=f'preco_{n}', x=e['x'], y=e['y'], peso=e['peso'], tam=e['tam'],
                                   tamCents=c['tam'], cor=e['cor'], larg=round(c['x1'] - e['x'], 2),
                                   dyCents=round(c['y'] - e['y'], 2)))
        arte['valores'][f'preco_{n}'] = e['txt'] + c['txt']

    perto = lambda y: min(range(len(precos)), key=lambda i: abs(precos[i][0]['y'] - y)) + 1  # pacote mais próximo
    # arte nova: "13/11 a 16/11/2026" e "4 dias e 3 noites" saem das datas de ida e volta do pacote
    for e in elems:
        m = re.fullmatch(r'(\d{2})/(\d{2}) a (\d{2})/(\d{2})/(\d{4})', e['txt'])
        d = re.fullmatch(r'\d+ dias? e \d+ noites?', e['txt'])
        if not (m or d) or id(e) in usados:
            continue
        n = perto(e['y'])
        arte['textos'].append(dict(tipo='texto', key=f"{'periodo' if m else 'duracao'}_{n}", formato='periodo' if m else 'duracao',
                                   de=f'ida_{n}', campos=[f'ida_{n}', f'volta_{n}'], x=e['x'], y=e['y'], peso=e['peso'],
                                   tam=e['tam'], cor=e['cor'], ls=e['ls'], maxW=round((e['x1'] - e['x']) * 1.3, 1)))
        if m:
            arte['valores'][f'ida_{n}'] = f'{m[5]}-{m[2]}-{m[1]}'
            arte['valores'][f'volta_{n}'] = f'{m[5]}-{m[4]}-{m[3]}'
        usados.add(id(e))

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
    grossos = [] if titulo_fixo else [d for d in soltos if d['width'] >= 20]
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

    acima_do_preco = lambda y: min((pe['y'] - y, n) for n, (pe, _) in enumerate(precos, 1) if pe['y'] > y)[1]
    abaixo_do_preco = lambda y: max(n for n, (pe, _) in enumerate(precos, 1) if pe['y'] < y)

    # formas de pagamento: fileira de etiquetas iguais (fundo arredondado + texto); o vendedor liga e desliga cada uma
    etiquetas = collections.defaultdict(list)
    for e in elems:
        if id(e) in usados or len(e['linhas']) > 1:
            continue
        centro = fitz.Point((e['bbox'].x0 + e['bbox'].x1) / 2, e['y'] - e['tam'] * .35)
        caixa = min((d for d in desenhos if d['type'] == 'f' and d['rect'].height < 45 and d['rect'].width < 150
                     and d['rect'].contains(centro) and d['rect'].width > e['bbox'].width), key=lambda d: d['rect'].get_area(), default=None)
        if caixa:
            r = caixa['rect']
            etiquetas[(round(r.y0), round(r.width), round(r.height))].append((e, caixa))
    for (y0, *_), fila in etiquetas.items():
        if len(fila) < 2:
            continue
        fila.sort(key=lambda ed: ed[1]['rect'].x0)
        r0, e0 = fila[0][1]['rect'], fila[0][0]
        canto = next(it for it in fila[0][1]['items'] if it[0] == 'c')
        key = f'pag_{abaixo_do_preco(y0)}'
        arte['textos'].append(dict(tipo='pagamentos', key=key, itens=[e['txt'] for e, _ in fila],
                                   cx=round((r0.x0 + fila[-1][1]['rect'].x1) / 2, 2), y0=round(r0.y0, 2), w=round(r0.width, 2),
                                   h=round(r0.height, 2), gap=round(fila[1][1]['rect'].x0 - r0.x1, 2),
                                   raio=round(max(abs(canto[4].x - canto[1].x), abs(canto[4].y - canto[1].y)), 2),
                                   fundo=cor(fila[0][1]['fill']), base=round(e0['y'], 2), peso=e0['peso'], tam=e0['tam'],
                                   cor=e0['cor'], ls=e0['ls']))
        arte['valores'][key] = ','.join(e['txt'] for e, _ in fila)
        arte['remover'] += [d for _, d in fila]
        usados |= {id(e) for e, _ in fila}

    riscos = [d for d in desenhos if d['type'] == 's' and d['rect'].height < 1 and d['rect'].width > 10]
    # fundo chapado da página inteira (vem das propostas montadas por script): sai da base, senão tapa a foto
    arte['remover'] += [d for d in desenhos if 'f' in d['type'] and d['rect'].contains(p.rect + (1, 1, -1, -1))]
    for e in elems:
        if id(e) in usados:
            continue
        t = e['txt']
        esq = max((o for o in elems if o is not e and abs(o['y'] - e['y']) < 1 and o['x1'] <= e['x'] + 1),
                  key=lambda o: o['x1'], default=None)  # texto logo à esquerda, na mesma linha
        abaixo_das_datas = any(0 < e['y'] - d['y'] < 80 and abs(e['x'] - d['x']) < 40 for d in datas)  # local, com alfinete
        risco = next((d for d in riscos if d['rect'].x0 < e['x1'] and d['rect'].x1 > e['x']
                      and e['bbox'].y0 < d['rect'].y0 < e['bbox'].y1), None)
        apos_parcelas = bool(esq and re.fullmatch(r'\d+x de', esq['txt']))
        formato = None
        if re.fullmatch(r'\d+X', t):  # "10X" da arte nova
            key, formato = f'parcelasx_{perto(e["y"])}', 'parcelasX'
            arte['valores'].setdefault(f'parcelas_{perto(e["y"])}', f'{t[:-1]}x de')
        elif re.fullmatch(r'\d+% OFF', t):
            key, formato = f'desconto_{perto(e["y"])}', 'desconto'
        elif re.fullmatch(r'Restam só \d+ vagas?', t):
            key, formato = 'restam', 'restam'
            arte['valores']['restam'] = re.search(r'\d+', t)[0]
        elif risco and not apos_parcelas and re.fullmatch(r'(R\$\s*)?[\d.,]+', t):
            key = f'preco_de_{perto(e["y"])}'  # "R$ 750" riscado da arte nova
        elif re.fullmatch(r'\d+x de', t):
            key = f'parcelas_{acima_do_preco(e["y"])}'
        elif esq and re.fullmatch(r'\d+x de', esq['txt']) and re.fullmatch(r'[\d.,]+', t):
            key = f'preco_de_{acima_do_preco(e["y"])}'
        elif esq and esq['txt'].endswith(':') or abaixo_das_datas:  # "Excursão: Village Resort, MG"
            key = 'local'
        else:
            key = ('telefone' if re.search(r'\(\d{2}\)\s*\d', t) else 'site' if re.search(r'\.com|www\.', t, re.I) else slug(t))
        el = dict(tipo='texto', key=key, x=e['x'], y=e['y'], peso=e['peso'], tam=e['tam'], cor=e['cor'], ls=e['ls'])
        if formato:
            n = key.split('_')[1] if '_' in key else ''
            el.update(formato=formato, de={'parcelasX': f'parcelas_{n}', 'desconto': f'preco_de_{n}', 'restam': 'restam'}[formato])
        if key.startswith('preco_de_') and not apos_parcelas:
            if t.startswith('R$'):
                el['prefixo'] = 'R$ '
                t = t[2:].strip()
            if risco:
                el['riscado'] = dict(cor=cor(risco['color']), larg=risco['width'], dy=round(risco['rect'].y0 - e['y'], 2),
                                     antes=round(e['x'] - risco['rect'].x0, 2), depois=round(risco['rect'].x1 - e['x1'], 2))
                arte['remover'].append(risco)
        elif key.startswith('preco_de_'):  # vem logo depois das parcelas: acompanha a largura delas; risco redesenhado
            el.update(apos=f'parcelas_{key.rsplit("_", 1)[1]}', gap=round(e['x'] - esq['x1'], 2))
            r = next((d for d in riscos if d['rect'].x0 < e['x1'] and d['rect'].x1 > e['x']
                      and e['bbox'].y0 < d['rect'].y0 < e['bbox'].y1), None)
            if r:
                el['riscado'] = dict(cor=cor(r['color']), larg=r['width'], dy=round(r['rect'].y0 - e['y'], 2),
                                     antes=round(e['x'] - r['rect'].x0, 2), depois=round(r['rect'].x1 - e['x1'], 2))
                arte['remover'].append(r)
        if e['vscale'] != 1:
            el['vscale'] = e['vscale']
        if len(e['linhas']) > 1:
            el['lh'] = round(e['linhas'][1]['y'] - e['linhas'][0]['y'], 2)
            el['quebra'] = largura_quebra(e)
        else:
            el['maxW'] = round((e['x1'] - e['x']) * 1.3, 1)
            if key == 'local':  # usa a largura toda da caixa em volta (a de cima, se houver outra atrás)
                centro = fitz.Point((e['bbox'].x0 + e['bbox'].x1) / 2, e['y'] - e['tam'] * .35)
                caixa = max((d for d in desenhos if 'f' in d['type'] and d['rect'].contains(centro)
                             and d['rect'].width > e['bbox'].width + 10 and d['rect'].height < 120), key=lambda d: d['seqno'], default=None)
                if caixa:
                    el['maxW'] = round(caixa['rect'].x1 - 14 - e['x'], 1)
        if e['tracos']:
            el['traco'] = estilo_traco(e['tracos'], sum(1 for ch in t if not ch.isspace()))
        arte['textos'].append(el)
        if not formato:
            arte['valores'].setdefault(key, t)
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
def render_sem(pno, remover, manter_fotos=()):
    """Página sem textos, sem imagens (menos as pedidas) e sem os desenhos de `remover`, com fundo transparente."""
    doc = fitz.open(SRC)
    p = doc[pno]
    if remover:
        faltam = remover_desenhos(p, remover)
        if faltam:
            print(f'  aviso: {faltam} de {len(remover)} desenhos não achados no PDF')
        p = doc.reload_page(p)
    sem_texto(p)
    for im in {im['xref'] for im in p.get_image_info(xrefs=True)} - set(manter_fotos):
        p.delete_image(im)
    return p.get_pixmap(dpi=DPI, alpha=True)


def camadas(pno, remover, n):
    info = fitz.open(SRC)[pno].get_image_info(xrefs=True)
    foto = max(info, key=lambda im: im['width'] * im['height'])
    outras = sorted({im['xref'] for im in info if im['xref'] != foto['xref']})
    k = 72 / DPI

    # personagem: a imagem que sobra (a última visível)
    personagem = None
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
        personagem = (x, dict(src=f'camadas/arte{n}-personagem.png', rect=ret([v * k for v in caixa])))

    # o que o designer pôs NA FRENTE do personagem (rodapé, faixa...) vai numa camada à parte, desenhada depois dele
    frente, pg = [], fitz.open(SRC)[pno]
    if personagem:
        bb = fitz.Rect(next(im['bbox'] for im in pg.get_image_info(xrefs=True) if im['xref'] == personagem[0]))
        seq = max(i for i, (t, r) in enumerate(pg.get_bboxlog())
                  if 'image' in t and abs(fitz.Rect(r).x0 - bb.x0) < 2 and abs(fitz.Rect(r).y0 - bb.y0) < 2)
        tirar = {d['seqno'] for d in remover}
        desenhos = [d for d in pg.get_drawings() if d['seqno'] not in tirar]
        frente = [d for d in desenhos if d['seqno'] > seq]
        tras = [d for d in desenhos if d['seqno'] < seq]

    base = render_sem(pno, list(remover) + frente)
    base.save(AQUI / f'camadas/arte{n}-base.png')
    base_a = np.frombuffer(base.samples, np.uint8).reshape(base.height, base.width, 4)[..., 3]
    if frente:
        render_sem(pno, list(remover) + tras).save(AQUI / f'camadas/arte{n}-frente.png')
        print(f'  {len(frente)} desenhos na frente do personagem')

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
    spec = dict(mascara=f'camadas/arte{n}-mascara.png', base=f'camadas/arte{n}-base.png', padrao=None,
                frente=f'camadas/arte{n}-frente.png' if frente else None,
                box=ret([xs.min() * k, ys.min() * k, (xs.max() + 1) * k, (ys.max() + 1) * k]),
                visivel=ret([vx.min() * k, vy.min() * k, (vx.max() + 1) * k, (vy.max() + 1) * k]),
                original=ret(foto['bbox']), personagem=personagem[1] if personagem else None)
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


def banco(doc, fotos_artes):
    itens = []
    for nome, xref in fotos_artes:  # foto que o designer pôs em cada arte ("layout" é a da primeira)
        pix = fitz.Pixmap(doc, xref)
        if pix.n - pix.alpha != 3:
            pix = fitz.Pixmap(fitz.csRGB, pix)
        salvar_foto(Image.open(io.BytesIO(pix.tobytes('png'))), nome, 'Foto da arte', itens)
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
    assert doc.page_count > max(p for p, _ in PRANCHETAS), f'o .ai tem {doc.page_count} pranchetas; ajuste PRANCHETAS em extrair.py'
    artes = [ler_arte(doc[pno], pno in TITULO_FIXO) for pno, _ in PRANCHETAS]
    valores = {}
    for a in artes:
        for k, v in a['valores'].items():
            valores.setdefault(k, v)
    ref = next(a['titulo'] for a in artes if a['titulo'])
    layouts, fotos = [], {}
    for n, ((pno, nome), a) in enumerate(zip(PRANCHETAS, artes), 1):
        print(f'arte {n}: {nome} (prancheta {pno + 1})')
        if a.get('titulo_desenho'):
            a['titulo'] = ajustar_titulo_desenho(a['titulo_desenho'], ref, valores)
        foto, xref = camadas(pno, a['remover'], n)
        foto['padrao'] = fotos.setdefault(xref, 'layout' if not fotos else f'layout-{n}')
        textos = sorted(a['textos'], key=lambda t: t['tipo'] != 'preco')  # preço embaixo do "7x de"
        r = doc[pno].rect
        layouts.append(dict(nome=nome, w=round(r.width), h=round(r.height), foto=foto,
                            textos=textos + ([a['titulo']] if a['titulo'] else [])))
        print(f'  {len(textos)} textos, personagem: {"sim" if foto["personagem"] else "não"}, foto: {foto["padrao"]}')
    itens = banco(doc, [(nome, xref) for xref, nome in fotos.items()])
    print(f'banco: {len(itens)} fotos')
    js = ('// gerado por extrair.py – não editar à mão\n'
          f'const LAYOUTS = {json.dumps(layouts, ensure_ascii=False)};\n'
          f'const VALORES = {json.dumps(valores, ensure_ascii=False)};\n'
          f'const BANCO = {json.dumps(itens, ensure_ascii=False)};\n')
    (AQUI / 'dados.js').write_text(js, encoding='utf-8')


if __name__ == '__main__':
    main()
