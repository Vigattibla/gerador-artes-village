# PRD – Gerador de Artes para Vendedores

## Objetivo
Vendedores do Village Resort geram, sozinhos e sem Illustrator, as artes de divulgação da
excursão "All Fun Inclusive" com os dados da venda deles. Simples e funcional acima de tudo.

## Usuários
Vendedores / agentes de viagem. Não são designers. Usam pelo link do site, inclusive no celular.

## Fonte da arte
`Layout - Agentes de viagem.ai` — 2 artes 1080×1350 (feed Instagram):
1. **1 pacote** – card de preço + lista "Tudo Incluso" + personagem (menino)
2. **2 pacotes** – dois cards de preço + personagem (cachorro)

## Requisitos
1. Editável pelo vendedor (marcação do usuário, 15/09/2026): valor, parcelas, ida/volta e local
   (card de preço) e telefone.
2. Título editável (pedido de 14/09/2026).
3. Travado, sempre igual ao `.ai`: quadro "Tudo Incluso + Lazer" e lista, logo, site, aviso legal e os
   rótulos do card ("A partir de", "para o casal", "por dia"). Site definitivo entra direto no `.ai`.
4. Foto: escolher de um **banco fechado** (`08 Fotos/Fotos Boas`, categorias pelas subpastas).
   Vendedor não envia foto própria.
5. Personagem: ligar/desligar.
6. Baixar PNG e copiar imagem.
7. Posição e estilo idênticos ao `.ai`; ajustes do designer entram rodando a extração.

## Contas e biblioteca (pedido de 15/09/2026)
8. Login por e-mail e senha. Contas e excursões numa **planilha Google do resort**, servida por
   Apps Script (escolha do usuário em 15/09/2026: grátis, com o que já tem). Site continua no GitHub Pages.
9. Papéis: **conta master** (chefe da área; a própria pessoa cria a master no site escolhendo a senha;
   cria as outras contas, desativa, troca senha; vê o painel geral com as excursões de todos) e
   **vendedor** (vê e mexe só nas próprias excursões). Conta nova recebe senha provisória da master e
   a pessoa cria a própria senha ao entrar (pedido de 15/09/2026).
10. Biblioteca do vendedor: cada excursão guarda a arte pronta (tudo que foi preenchido), nome interno,
    observações, vagas (total e vendidas) e contato do responsável pelo grupo. Dá pra abrir, editar,
    baixar de novo e duplicar.
11. Situação calculada pelas datas: próxima (ida depois de hoje), acontecendo (entre ida e volta),
    encerrada (volta antes de hoje).

## Campanhas (pedido de 15/09/2026)
12. Aba Campanhas tipo painel (detalhes em `docs/spec-campanhas.md`). A master publica (o tipo de conta adsign foi removido
    em 17/09/2026) a campanha com arte, informações
    da excursão, vagas totais e materiais; pesquisa em CRMs e portais de parceiros para completar os campos.
13. Vendedor pega a campanha e faz a arte trocando **só o telefone** (datas, valor, título e foto travados).
14. Vagas somadas: cada venda informada desconta do total da campanha; master confirma ou cancela vendas.
15. Novas artes (layouts) vêm do `.ai` pelo `extrair.py`, rodado com o Claude (o site não lê Illustrator).

16. Futuro (16/09/2026): vendedor escolher o personagem. O `.ai` já tem, fora das pranchetas, o bebê e a menina
    além do menino e do cachorro; a extração hoje só pega o personagem de cada prancheta.

## Fora de escopo / decisões
- Preço com 4 dígitos (não existe).
- Posição do "7x de" sobre o preço: decidir depois.
- Arte "Comparativo" foi removida (14/09/2026).
- Fotos do banco ficam públicas no GitHub Pages (aceito pelo usuário).
