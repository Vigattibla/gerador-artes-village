# Gera os fundos (arte sem texto) a partir do .ai. Rodar de novo se o .ai mudar.
import base64, json, pathlib
import pymupdf as fitz

SRC = r'D:\Design\Village Resort\Agentes de viagem\Layout - Agentes de viagem.ai'
OUT = pathlib.Path(__file__).parent

fundos = []
for i, p in enumerate(fitz.open(SRC)):
    # contorno azul do "7x de" é vetor separado: some aqui e o gerador redesenha
    for t in p.get_texttrace():
        if 'x de' in ''.join(chr(c[0]) for c in t['chars']):
            p.add_redact_annot(fitz.Rect(t['bbox']) + (-8, -8, 8, 8), fill=False)
    p.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                       graphics=fitz.PDF_REDACT_LINE_ART_REMOVE_IF_COVERED,
                       text=fitz.PDF_REDACT_TEXT_REMOVE)
    p.add_redact_annot(p.rect, fill=False)
    p.apply_redactions(images=fitz.PDF_REDACT_IMAGE_NONE,
                       graphics=fitz.PDF_REDACT_LINE_ART_NONE,
                       text=fitz.PDF_REDACT_TEXT_REMOVE)
    jpg = p.get_pixmap(dpi=144).tobytes('jpg', jpg_quality=90)  # 2160x2700
    (OUT / f'fundo-{i + 1}.jpg').write_bytes(jpg)
    fundos.append('data:image/jpeg;base64,' + base64.b64encode(jpg).decode())

# data URI via <script> para o canvas não ficar "tainted" abrindo por file://
(OUT / 'fundos.js').write_text('const FUNDOS = ' + json.dumps(fundos) + ';\n')
print('ok', [len(f) // 1024 for f in fundos], 'KB')
