# PRD – Gerador de Artes para Agentes de Viagem

## Objetivo
Agentes de viagem do Village Resort geram, sozinhos e sem Illustrator, as artes de divulgação das
excursões com o contato e a logo deles. Simples e funcional acima de tudo.

**Escopo (TI, 17/09/2026): o gerador só gera arte.** Criação e gestão de campanhas, vendas, vagas,
passageiros e contas ficam em outro sistema do resort, que manda as campanhas para cá por API.

## Usuários
Vendedores / agentes de viagem. Não são designers. Usam pelo link do site, inclusive no celular.

## Fonte da arte
`Layout - Agentes de viagem.ai` — 2 artes 1080×1350 (feed Instagram):
1. **1 pacote** – card de preço + lista "Tudo Incluso" + personagem (menino)
2. **2 pacotes** – dois cards de preço + personagem (cachorro)

## Requisitos
1. Editável pelo vendedor (marcação do usuário, 15/09/2026): valor, parcelas, ida/volta e local
   (card de preço) e telefone.
2. Título: só quem cria a campanha muda (TI, 17/09/2026). Frase maior que a do `.ai` diminui a letra para caber.
3. Travado, sempre igual ao `.ai`: quadro "Tudo Incluso + Lazer" e lista, logo, site, aviso legal e os
   rótulos do card ("A partir de", "para o casal", "por dia"). Site definitivo entra direto no `.ai`.
4. Foto: escolher de um **banco fechado** (`08 Fotos/Fotos Boas`, categorias pelas subpastas).
   Vendedor não envia foto própria.
5. Personagem: o agente escolhe entre as opções (`personagens/*.png`) ou nenhum, nas artes que têm lugar de personagem.
   Pedido de 17/09/2026: 4 opções (menino, cachorro, bebê, menina); faltam os PNGs do designer.
5b. Logo do agente (17/09/2026): o agente envia a logo uma vez (fica no aparelho) e ela entra numa caixa branca à
   direita da pílula do telefone; liga/desliga por arte.
5c. Calculadora de desconto (17/09/2026): preço do pacote sem e com desconto → divide pelas parcelas e preenche o
   valor e o valor antigo; o selo de % OFF acompanha.
6. Baixar PNG e copiar imagem.
7. Posição e estilo idênticos ao `.ai`; ajustes do designer entram rodando a extração.

## Contas, biblioteca e campanhas
8. Login continua (hoje planilha Google/Apps Script ou demonstração); o TI vai ligar o sistema dele (`docs/api.md`).
9. Papéis: **criador de campanha** (conta master: monta a arte da campanha, muda título e valores) e **agente**.
10. Minhas artes: cada arte salva (abrir, duplicar, excluir), separada por datas.
11a. Construtor de campanha (17/09/2026, pedido do usuário: começar pelo criador; o do agente fica mais simples
    depois, dentro do sistema do resort): nome, valores e datas, título, foto e personagem, **quais artes entram**,
    **vídeos animados** (liga/desliga cada um, com prévia) e **arquivos** para os agentes baixarem; publicar ou rascunho.
    Agente baixa a arte (só entre as da campanha), os vídeos (MP4 gravado no navegador com o contato e a logo dele)
    e os arquivos. Quem cria a excursão é sempre o master (produto, preço, título, layouts); o **ônibus e a saída
    costumam ser do agente**, então na arte de campanha ele edita data de ida, data de volta e vagas restantes
    (passo "Datas e vagas", com o bloco de preço escondido). O agente não digita preço: informa a **comissão (%)**
    e o preço da arte = preço da campanha × (1 + %),
    inclusive o valor riscado. Logo do agente no mesmo selo do "Village Resort" (borda, base e fundo medidos no .ai).
11. Campanhas: vêm do sistema do resort. O criador monta/edita a arte; o agente faz a dele trocando telefone, logo e
    personagem (datas, valor, título e foto travados).
12. Novas artes (layouts) vêm do `.ai` pelo `extrair.py`, rodado com o Claude (o site não lê Illustrator).
13. Removido em 17/09/2026 (vai para o sistema do resort): agenda, planilha de passageiros, painel, contas,
    ficha/vendas/formulário de campanha e o passo "Dados da excursão".
13a. Pasta (17/09/2026): cada excursão é uma pasta com vários criativos. No passo "Escolha a arte" o agente
    marca quais artes ficam na pasta; a tela `#/pasta/<id>` mostra cada criativo com "Baixar imagem",
    "Baixar vídeo" e "Editar", os arquivos da campanha e os três movimentos de vídeo (cascata, zoom,
    deslizar) com preview. O movimento escolhido vale para os vídeos daquela pasta.
14. Próximo (ideia do usuário, 17/09/2026): kit por campanha com outros formatos — impressos (PDF A5/A4) e
    vídeo/GIF animado para Reels/Status.

## Fora de escopo / decisões
- Preço com 4 dígitos (não existe).
- Posição do "7x de" sobre o preço: decidir depois.
- Arte "Comparativo" foi removida (14/09/2026).
- Fotos do banco ficam públicas no GitHub Pages (aceito pelo usuário).
