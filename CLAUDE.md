# Gerador de Artes – Agentes de Viagem

Sistema estático (HTML + canvas) para vendedores gerarem as artes da excursão a partir do
`../Layout - Agentes de viagem.ai`. Publicado no GitHub Pages (repo público
Vigattibla/gerador-artes-village).

## Memory bank
- Requisitos: `docs/product_requirement_docs.md`
- Estado atual e próximos passos: `tasks/active_context.md`
- Nota no Obsidian: `D:\Obsidian\Github\Gerador Artes Agentes.md`

## Arquivos
- `extrair.py` — lê o `.ai` e o banco de fotos; gera `dados.js`, `camadas/` e `banco/`. Rodar: `python extrair.py`
- `index.html` — o sistema (formulário + canvas). Tudo que é da arte vem do `dados.js`.
- `dados.js`, `camadas/`, `banco/` — gerados, não editar.
- `fonts/` — Montserrat + `MontserratTab` (dígitos tabulares, gerada com fontTools).
- `gerador.html` — só redireciona o link antigo para a raiz.
- `tests/mock_planilha.py` — servidor falso da planilha (mesmas ações do Apps Script) pra testar o site sem
  mexer na planilha real: servidor `mock-planilha` (porta 8766) + `http://localhost:8765/?api=http://localhost:8766`.
  `?api=` só vale em localhost (em produção mandaria senhas pra outro servidor).
- O site é local-first: grava as excursões no aparelho na hora e sincroniza com a planilha em segundo plano
  (o Apps Script grátis leva 2–12 s e às vezes devolve página HTML; `api()` tenta de novo).
- `docs/spec-contas.md` — especificação de contas, biblioteca e painel do chefe (próxima fase).
- `apps-script/Codigo.gs` — servidor das contas: planilha Google + Apps Script publicado como App da Web.
  O segredo das sessões fica nas propriedades do script; no site vai só a URL `/exec`.
  Mudou o arquivo → nova versão da implantação no Apps Script.

## Regras
- O `.ai` é a fonte da verdade. Posições, fontes, tamanhos e cores saem do script de extração,
  nunca de número digitado à mão. Designer mexeu no `.ai` → rodar a extração de novo.
- Arquivos gerados pela extração não se editam à mão.
- Canvas desenha em 2x (2160×2700) sobre prancheta de 1080×1350 pt.
- Preço e datas usam `MontserratTab` (dígitos tabulares). Preço nunca tem 4 dígitos.
- Toda mudança visual: conferir contra o `.ai` renderizado (diff por pixel no Chrome headless).
- Testar por http (servidor `gerador-agentes`, porta 8765), não por file://: imagens soltas
  "sujam" o canvas em file:// e o download falha.

## Gotchas
- `img.decode()` trava no Chrome headless → usar `onload`.
- `--timeout` do Chrome corta o load; usar `--virtual-time-budget`.
- CSS `display` em elemento sobrescreve `[hidden]` → manter `[hidden]{display:none!important}`.
- Push e publicação: confirmar com o usuário antes.
