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
8. Login por e-mail e senha (Supabase; o site continua no GitHub Pages).
9. Papéis: **chefe da área** (login próprio; autoriza, cria e desativa contas de vendedores; vê o
   painel geral com as excursões de todos) e **vendedor** (vê e mexe só nas próprias excursões).
10. Biblioteca do vendedor: cada excursão guarda a arte pronta (tudo que foi preenchido), nome interno,
    observações, vagas (total e vendidas) e contato do responsável pelo grupo. Dá pra abrir, editar,
    baixar de novo e duplicar.
11. Situação calculada pelas datas: próxima (ida depois de hoje), acontecendo (entre ida e volta),
    encerrada (volta antes de hoje).

## Fora de escopo / decisões
- Preço com 4 dígitos (não existe).
- Posição do "7x de" sobre o preço: decidir depois.
- Arte "Comparativo" foi removida (14/09/2026).
- Fotos do banco ficam públicas no GitHub Pages (aceito pelo usuário).
