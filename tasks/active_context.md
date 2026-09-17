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
- 15/09 (19h): usuário mudou o `.ai`: card de preço com "7x de" + preço antigo riscado (vermelho), etiquetas
  Crédito/Débito/Pix embaixo das datas, local saiu do card e virou caixa "Excursão: Village Resort, MG", site saiu.
  `extrair.py` agora separa "7x de 750" em `parcelas_N` + `preco_de_N` (acompanha o fim das parcelas, risco
  redesenhado), lê a fileira de etiquetas como `pag_N` (tipo `pagamentos`, liga/desliga, centraliza as ligadas),
  ignora textos duplicados e acha `local` depois de rótulo com ":". Editor: por pacote valor, valor antigo, parcelas
  (−/+) e formas de pagamento. Excursões antigas com `parcelas` único viram `parcelas_1/2`. Não publicado.
- 17/09: propostas de layout (pasta `Agentes de viagem/Propostas de layout`, `fonte/gerar.py` monta PDF e .ai nativo)
  aprovadas e coladas pelo usuário no `.ai` (pranchetas 4–7). Gerador agora tem 6 artes: 1 pacote, 2 pacotes, Story,
  Feed, Últimas vagas, Carrossel (tela da oferta). Editor aceita 1080×1920, campo "Vagas restantes". Arte 1 sem o menino
  (usuário tirou). Testado: diferença ≤1% contra o .ai nas artes novas, editor no desktop e celular. Não publicado.
2. Decidir posição do "7x de".
3. Site definitivo.

## Limites conhecidos
- Título da arte 1 aproxima a distorção do Illustrator (a letra em si não deforma).
- Contorno do título fecha vãos entre letras com "pontes" na altura das maiúsculas.
- Banco ocupa ~51 MB no repositório.
- 17/09 (tarde): usuário salvou o .ai com Story/Últimas trocados, cachorro no carrossel e ícones na lista da arte 1;
  extração rodada. Adsign removido (site, servidor falso, demonstração, Codigo.gs). Campanhas implementadas no
  `Codigo.gs` (abas Campanhas, Vendas, Participantes; `configurar` cria) e liberadas no site de produção.
  `tests/teste_apps_script.js` roda o Codigo.gs com planilha falsa (passou). `docs/api.md` para o TI que vai migrar o banco.
  Falta: usuário colar o Codigo.gs novo no Apps Script, rodar `configurar`, nova versão da implantação; publicar o site.
- 17/09: usuário decidiu que o site publicado fica só local (demonstração, sem planilha) até o TI migrar o banco;
  `DEMO` é o padrão fora do localhost e `?planilha` liga o Apps Script.
- 17/09: editor começa pela escolha da arte (Escolha a arte → Dados da excursão → Valores → Título e contato → Foto).
- 17/09: personagem atrás do que o .ai desenha depois dele (`camadas/arteN-frente.png`, ordem pelo `get_bboxlog`).
  Aba **Agenda** (calendário do mês: minhas excursões, campanhas, e para a master as dos vendedores) e tela
  **Passageiros** por excursão (planilha editável, colar do Excel, baixar CSV que abre no Excel). Passageiros ficam
  em `arte.passageiros` (sem mudança no servidor). Testado no `?demo` (desktop e celular). Não publicado.
- 17/09 (noite): **foco só em gerar arte** (conversa do usuário com o TI): campanhas/gestão vão para o sistema do
  resort, que manda as campanhas por API. Saíram agenda, passageiros, painel, contas, ficha/vendas/formulário de
  campanha e o passo "Dados da excursão" (menu: Início, Criar arte, Minhas artes, Campanhas). Entraram: título só
  para o criador (conta master) com letra que diminui para caber; calculadora de desconto pelo preço do pacote;
  logo do agente (aparelho, caixa ao lado do telefone, lugar medido pelo `extrair.py` → `LAYOUTS[].logo`);
  escolha de personagem (`personagens/*.png` → `PERSONAGENS`; hoje menino e 2 cachorros provisórios; faltam
  bebê e menina, que não estão mais no .ai). Testado no `?demo` (criador e agente, desktop e celular). Não publicado.
  Ideia do usuário: kit com impressos e vídeo/GIF (pesquisa: MP4 via WebCodecs + Mediabunny no navegador; PDF A5/A4).
- 17/09 (noite, 2): **construtor de campanha** do criador: "+ Nova campanha", passo 1 marca as artes da campanha,
  passo 3 com nome, passo 5 "Materiais" (vídeos animados Story/Últimas vagas/Feed com prévia, arquivos no IndexedDB,
  publicar). Agente: escolhe só entre as artes da campanha e baixa vídeo MP4 (MediaRecorder, 8 s, testado: MP4
  1080×1920) e arquivos. Logo do agente no selo igual ao do Village. Usuário pediu manter só local por enquanto.
- 17/09: agente informa a comissão (%) na arte de campanha; preço e valor riscado da arte sobem junto (`campos.comissao`).
- 17/09: vídeo anima as peças da arte, não só o texto: `extrair.py` separa as peças (manchas da imagem sem o fundo
  grande) em `camadas/arteN-pecaK.png` + `arteN-fundo.png` (formas grandes redesenhadas; tirar desenho do PDF falha
  nos contornos empilhados). No canvas: rodapé sobe, peças da borda deslizam, as outras "pulam" com leve passo além,
  texto entra junto com a peça, personagem sobe, preço pulsa, foto se afasta. Arte parada continua na base.
  Botão "Finalizar" no fim das próprias artes (salva e volta para Minhas artes). .ai salvo com o cachorro no Carrossel.

17/09 (2): quem cria a excursão continua sendo o master (preço, título, pacote, layouts), mas o
ônibus e a saída costumam ser do agente — então, na arte de campanha, o agente agora edita a data
de ida, a de volta e as vagas restantes. O passo "Datas e vagas" aparece para ele com o bloco de
preço/parcelas escondido (`#pacotes.so-datas`). No vídeo, as peças coladas na borda entram sem o
"passo além" (usavam `volta`, agora `suave`), senão o corte reto delas aparecia dentro da arte.

17/09 (3): a campanha guarda `datas: 'agente' | 'master'` — o criador marca no passo dos valores quem
põe a data da saída e as vagas. Em 'master', o agente nem vê o passo "Datas e vagas". Em "Minhas artes",
selo "Campanha do Village" ou "Arte sua" para separar o que veio pronto do que é do próprio agente.
Pendente do usuário: letra miúda das artes (aviso legal em 12,5 px num 1080 = ~4,5 px no celular).

17/09 (4): quem cria a campanha também baixa o MP4 (botão "Baixar vídeo" ao lado de "Incluir"; mesmo
`gravarVideo` do agente). Subido para o GitHub Pages.

17/09 (5): letra miúda do rodapé maior. `subir_miudo` no extrair.py sobe o bloco até 18 px mantendo a
base no lugar e para antes de encostar na linha das pílulas: 18 no Story/Feed/Vagas/Carrossel,
17 em "2 pacotes" e 15,5 em "1 pacote" (caixa estreita).

17/09 (6): "Baixar vídeo" também nas artes próprias do agente (último passo, ao lado de "Baixar imagem");
usa o mesmo `gravarVideo` do motion da campanha, com a arte que estiver aberta.

17/09 (7): pasta por excursão (`#/pasta/<id>`): a excursão guarda `layouts` (as artes dela) e `anim`
(o movimento dos vídeos). A tela lista cada criativo com imagem/vídeo/editar, os arquivos da campanha
e os três movimentos com preview rodando (cascata, zoom, deslizar). `paraServidor`/`deServidor` levam
`layouts` e `anim`; o hash aceita `#/arte/<id>?layout=&passo=`.
