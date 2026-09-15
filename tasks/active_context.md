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
  foto e personagem. Título continua editável (confirmado pelo usuário em 15/09).
- v2 publicada em 15/09/2026 (commit eef466c): https://vigattibla.github.io/gerador-artes-village/

- 15/09: interface refeita em passo a passo (escolhido pelo usuário): 1 arte, 2 valores e datas,
  3 título e contato, 4 foto e personagem + Baixar/Enviar. Arte sempre visível; tocar na arte leva ao
  campo; o trecho editado fica aceso; telefone formatado; parcelas com −/+. Base: NN/g (wizards),
  GOV.UK (uma coisa por vez), Canva (modelo travado), Baymard (campos no celular).

- 15/09: interface passo a passo publicada (commit fac1297); usuário enviou pra aprovação.
- 15/09: menu no topo (casinha Início, Criar arte, Minhas excursões; saiu "Gerador de artes"), site abre na
  tela Início. Minhas excursões já funciona salvando no aparelho (localStorage `village.excursoes`):
  cada arte vira excursão com salvamento automático e miniatura; abas Acontecendo/Próximas/Encerradas
  pelas datas; abrir, duplicar, excluir. Ainda não publicado. Troca o armazenamento pelo Supabase na fase de contas.

## Próximos passos
1. Contas e biblioteca (PRD itens 8–11) em planilha Google + Apps Script (`apps-script/Codigo.gs`,
   `docs/spec-contas.md`). Usuário cria a planilha, cola o script, roda `configurar` (anota o código de
   instalação), implanta e passa a URL `/exec`; depois: criar master / entrar / criar senha, biblioteca na
   planilha, dados da excursão, painel e contas. Papel "chefe" virou "master" (15/09).
- 15/09: usuário criou a planilha, rodou `configurar` e implantou. App da Web:
  https://script.google.com/macros/s/AKfycbyq6BPUme8ez58eYseXBpRAk1xLaAlwHith0EH952rB9Apm-bS2Bb2jMz8hFcHbqawD/exec
  Testado: status → precisaMaster true; entrar inválido e ação desconhecida → erro certo. Latência 2–6 s,
  picos 12–40 s → site local-first com sincronização. Master ainda não criada (código fica com o usuário).
- 15/09: site ligado à planilha (ainda não publicado): Entrar / Criar conta master / Crie sua senha; caixa de
  espera explícita com contador em toda chamada lenta (pedido do usuário); excursões no aparelho + envio em
  segundo plano com nova tentativa; passo "Dados da excursão"; Painel e Contas da master. Testado de ponta a
  ponta com `tests/mock_planilha.py` (master, vendedora, provisória, senha, sincronização, painel, desativar).
- 15/09: versão com contas publicada (commit 28d0f05). Falta o usuário criar a master no site com o código.
- 15/09 (só localhost, não publicado): logo Village Resort em vetor no topo (tirado de `01 Marca/00 - Logos.ai`, branco
  e amarelo). No localhost o site usa o servidor falso (`tests/mock_planilha.py`) e a tela Entrar tem botões
  "Entrar como master/adsign/vendedor" sem senha. Conta nova **adsign** (cria e edita campanhas, não mexe em contas).
- 15/09 (só localhost): aba **Campanhas** (`docs/spec-campanhas.md`): vitrine com abas, ficha completa (datas e valor
  vêm da arte, embarque, roteiro, inclui, pagamento, crianças, documentos, cancelamento, materiais com copiar),
  formulário em seções, arte da campanha no mesmo editor (passos 2–5, rascunho no aparelho até "Salvar na campanha"),
  vendedor "Fazer minha arte" (só passo de contato, só telefone editável), informar venda (valida vagas, prazo e
  situação), master confirma/cancela e vê ranking. Testado no localhost com master, adsign e vendedor.
  Falta: ações de campanha no `apps-script/Codigo.gs` (abas Campanhas, Vendas, Participantes) antes de publicar.
- 15/09: usuário pediu subir "sem banco de dados" pra outras pessoas verem e opinarem → modo `?demo` no mesmo site
  (servidor simulado no navegador, dados de exemplo, faixa "Demonstração" com Recomeçar). No link normal as campanhas
  ficam escondidas.
2. Decidir posição do "7x de".
3. Site definitivo.

## Limites conhecidos
- Título da arte 1 aproxima a distorção do Illustrator (a letra em si não deforma).
- Contorno do título fecha vãos entre letras com "pontes" na altura das maiúsculas.
- Banco ocupa ~51 MB no repositório.
