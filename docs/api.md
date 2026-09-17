# API do servidor — contrato para migrar o banco de dados

> 17/09/2026: o gerador ficou **só com a geração de arte**. Campanhas, vendas, vagas, passageiros e contas são do
> sistema do resort. Das ações abaixo o site usa hoje: `status`, `criarMaster`, `entrar`, `criarSenha`, `eu`,
> `listar`, `salvar`, `excluir`, `campanhas`, `salvarCampanha` (cria ou atualiza: `nome, status, layouts, motions,
> arquivos, arte, mini`) e `excluirCampanha`. Falta no servidor: guardar os arquivos da campanha. As demais seguem no
> `Codigo.gs`, mas o site não chama mais.

O site (`index.html`, estático no GitHub Pages) conversa com **um único endereço**. Hoje é o App da Web do
Google Apps Script (`apps-script/Codigo.gs`) gravando numa planilha Google. Para trocar o banco basta
um servidor que responda igual a este documento e trocar a constante `API` no `index.html`.

Hoje (17/09/2026) o site publicado roda **sem servidor**: usa o `demoApi()` e guarda tudo no navegador.
Para usar o servidor, abra o site com `?planilha` (ou troque a constante `DEMO` no `index.html`).

Implementações de referência (mesmas regras):
- `apps-script/Codigo.gs` — a de produção (planilha).
- `tests/mock_planilha.py` — servidor falso em memória (localhost:8766).
- `demoApi()` no `index.html` — versão no navegador usada no link `?demo`.
- `tests/teste_apps_script.js` — roda o Codigo.gs com planilha falsa e confere o fluxo (`node tests/teste_apps_script.js`).

## Transporte
- `POST <API>` com corpo **texto** contendo JSON: `{"acao": "<nome>", ...campos}`.
  O site manda `Content-Type: text/plain` de propósito (sem preflight de CORS). O novo servidor precisa
  aceitar isso e responder com `Access-Control-Allow-Origin` para o domínio do site.
- Resposta sempre JSON, HTTP 200:
  - sucesso: `{"ok": true, ...dados}`
  - erro para mostrar ao usuário: `{"ok": false, "erro": "mensagem em português"}`
- O site tenta de novo (0 s, 1,5 s, 4 s; 45 s por tentativa) quando a resposta não é JSON ou a rede falha.
  Erro com `ok:false` não é repetido.
- Mensagens que derrubam a sessão no site (ele volta para o login): texto contendo "entre de novo",
  "sessão expirou" ou "acesso mudou".

## Sessão e papéis
- `token`: string opaca devolvida no login; vale 30 dias. Hoje é `base64url(JSON{e: email, x: expira_ms}) + "." + HMAC`.
  Todas as ações, menos `status`, `criarMaster`, `entrar` e `criarSenha`, recebem `token`.
- A cada chamada o servidor confere se a conta continua ativa e sem senha provisória pendente; senão responde
  "Seu acesso mudou. Entre de novo ou fale com a conta master."
- Papéis: `master` (uma conta, criada com o código de instalação; cria contas, vê tudo, cria campanhas,
  confirma vendas) e `vendedor`. **Não existe mais o papel adsign** (removido em 17/09/2026).
- Senha: guardada com sal + HMAC + 500 rodadas de SHA-256. Senha provisória: 6 dígitos, vale só para chegar
  em `criarSenha`. Depois de 5 erros seguidos, bloqueia por 10 minutos (por e-mail).

## Objetos
```
usuario  = { email, nome, papel: "master"|"vendedor" }
excursao = { id, vendedor, vendedorNome?, nome, ida, volta,          // arte salva do agente; datas "AAAA-MM-DD"
             atualizada (ms), arte: {atual, layouts: [n], anim: 'cascata'|'zoom'|'desliza',
                                    foto, personagem, ajuste, campos, campanha?}, mini: dataURL JPEG }
             (`layouts` = as artes da pasta; `anim` = o movimento dos vídeos dela)
// personagem: id da pasta personagens/, "arte" (o do .ai) ou "" (nenhum); antes de 17/09 era true/false
// campos.logo = "1" mostra a logo do agente (a imagem fica só no aparelho dele, não vai ao servidor)
campanha = { id, nome, status: "rascunho"|"ativa",   // montada no construtor do gerador pelo criador (17/09/2026)
             layouts: [índices de LAYOUTS], motions: ["story"|"vagas"|"feed"], arquivos: [{id, nome, tamanho, tipo}],
             // arquivos: na demonstração o conteúdo fica no IndexedDB do navegador; no servidor precisa de upload/download por id
             // campos antigos abaixo não são mais usados pelo gerador:
             limite_venda "AAAA-MM-DD"|"",
             vagas_total (número ou null), criada_por, atualizada (ms), mini,
             resumo, embarques, retorno, sinal, quitar_ate, pagamento: [texto], comissao, criancas, roteiro,
             inclui, nao_inclui, documentos, cancelamento, regras, contato_guia, textos, links,
             arte: {atual, foto, personagem, ajuste, campos},
             // calculados na resposta:
             vendidas (soma das pessoas das vendas não canceladas), peguei (o usuário pegou a campanha) }
venda    = { id, campanha, vendedor, vendedorNome?, cliente, telefone, pessoas, embarque, pagamento,
             sinal_pago (bool), obs, status: "pendente"|"confirmada"|"cancelada", criada (ms) }
```
`arte` e `mini` são guardados como vieram (o site monta e lê). Limite atual: 45 mil caracteres por campo.

## Ações

| ação | quem | entrada | resposta |
|---|---|---|---|
| `status` | todos | — | `{precisaMaster}` |
| `criarMaster` | todos | `nome, email, senha, codigoInstalacao` | `{token, usuario}` |
| `entrar` | todos | `email, senha` | `{token, usuario}` ou `{precisaNovaSenha: true}` se a senha é a provisória |
| `criarSenha` | todos | `email, provisoria, senha` (≥ 8) | `{token, usuario}` |
| `eu` | logado | — | `{usuario}` |
| `listar` | logado | — | `{excursoes}` — master recebe de todos (com `vendedorNome`), vendedor só as dele |
| `salvar` | logado | `excursao` (sem `id` = nova) | `{excursao: {id, atualizada}}`; só o dono altera |
| `excluir` | logado | `id` | `{}`; só o dono |
| `contas` | master | — | `{contas: [{email, nome, papel, ativo, aguardandoSenha}]}` |
| `salvarConta` | master | `email` + `nome` (conta nova) / `ativo` (bool) / `novaProvisoria: true` | `{provisoria}` ("" se não gerou) — conta nova é sempre `vendedor`; a master não desativa nem troca a própria senha |
| `campanhas` | logado | — | `{campanhas}` ordenadas pela mais recente; vendedor não recebe rascunhos |
| `salvarCampanha` | master | `campanha` com `id` para editar; só os campos enviados mudam | `{campanha}`; nome obrigatório; `vagas_total` não pode ficar menor que as vendidas |
| `excluirCampanha` | master | `id` | `{}`; recusa se já houver vendas ("mude para Encerrada") |
| `pegarCampanha` | logado | `id` | `{}`; registra que o usuário vende a campanha (não vale para rascunho) |
| `vendas` | logado | `campanha?` | `{vendas}` — master vê de todos (com `vendedorNome`), os outros só as próprias |
| `salvarVenda` | logado | venda nova: `venda {campanha, cliente, pessoas, telefone, embarque, pagamento, sinal_pago, obs}` | `{venda}` com `status: "pendente"`; exige campanha `ativa`, dentro do `limite_venda`, cliente e pessoas ≥ 1, e pessoas ≤ vagas restantes; também registra o vendedor na campanha |
| `salvarVenda` | master (ou o dono, só para cancelar pendente) | `venda {id, status}` | `{venda}`; reativar venda cancelada confere se ainda há vagas |

Mensagens de erro usadas pelo site: ver os `aviso_('...')` no `Codigo.gs` (o site só as mostra).

## Onde fica cada coisa hoje (planilha)
- **Vendedores**: Email, Nome, Papel, Ativo (SIM/NÃO), Senha provisória, Senha (hash, oculta), Criado em.
- **Excursoes**: ID, Vendedor, Nome, Observações, Ida, Volta, Vagas, Vendidas, Responsável do grupo,
  Telefone do grupo, Atualizada em, Arte (JSON, oculta), Miniatura (oculta).
- **Campanhas**: ID, Nome, Situação, Vende até, Vagas, Criada por, Atualizada em, Dados (JSON com o resto
  da campanha, oculta), Miniatura (oculta).
- **Vendas**: ID, Campanha, Vendedor, Cliente, Telefone, Pessoas, Embarque, Pagamento, Sinal pago, Observação,
  Situação, Criada em.
- **Participantes**: Campanha, Vendedor, Desde.
- Propriedades do script: `SEGREDO` (assina tokens e senhas; ao migrar, as senhas atuais só continuam
  válidas se o novo servidor usar o mesmo segredo e o mesmo cálculo de hash) e `CODIGO_INSTALACAO`.

## Comportamento do site que o servidor precisa aguentar
- Local-first: excursões são salvas no aparelho e enviadas depois (`salvar` pode chegar repetido; o `id`
  devolvido é guardado e usado nas próximas).
- O Apps Script grátis responde em 2–12 s; o site mostra caixa de espera. Um banco novo mais rápido não
  exige mudança no site.
