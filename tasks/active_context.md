# Contexto ativo

## Estado (14/09/2026)
- v2 local, ainda não publicada. `index.html` lê `dados.js`, gerado por `extrair.py` direto do `.ai`.
- Por arte, 3 camadas: base (sem textos, sem título, sem foto/personagem), máscara da foto e personagem.
  Composição foto → base → personagem → textos reproduz o `.ai` sem diferença de pixel.
- Textos: posição, fonte, tamanho, cor, tracking e escala vertical lidos do PDF; campos por papel
  (preço/ida/volta por pacote, parcelas, telefone, site, título) e o resto por texto.
- Título editável nas 2 artes. Arte 1: o PDF traz o título em curvas (efeito de distorção);
  a curva "bandeira" é medida nas letras e o canvas aplica cisalhamento por letra (erro ≤ ~2,5pt).
- Título e contornos saem da base pelo filtro do MuPDF (culler), casando objeto a objeto.
  A remoção por área do PyMuPDF não funciona nesse arquivo (grupo com recorte).
- Banco: 85 fotos (`08 Fotos/Fotos Boas` + foto da arte), 2400px + miniaturas.
- Foto: cobre a área, ancora pela base, centraliza na parte visível; zoom + arrastar.
- Preço e datas em `MontserratTab`.
- Campos travados (15/09): vendedor edita só valor, parcelas, ida/volta, local, telefone, título,
  foto e personagem. O site publicado ainda é a v1 (3 artes); a v2 espera confirmação de push.

## Próximos passos
1. Confirmar com o usuário e publicar (push) no GitHub Pages.
2. Decidir posição do "7x de".
3. Site definitivo.

## Limites conhecidos
- Título da arte 1 aproxima a distorção do Illustrator (a letra em si não deforma).
- Contorno do título fecha vãos entre letras com "pontes" na altura das maiúsculas.
- Banco ocupa ~51 MB no repositório.
