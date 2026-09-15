# Especificação – Contas e biblioteca de excursões (planilha Google)

Pedido do usuário em 15/09/2026. Escolha: grátis, com o que já tem → **planilha Google + Apps Script**.
Requisitos no PRD (itens 8–11).

## Objetivo
Cada pessoa entra com e-mail e senha. A **conta master** (chefe da área) cria as outras contas,
desativa, troca senha e vê todas as excursões. **Vendedor** vê e mexe só nas próprias.

## Planilha (conta Google do resort) – criada por `configurar()` do `apps-script/Codigo.gs`
**Vendedores:** Email · Nome · Papel (`vendedor`/`master`) · Ativo (`SIM`/`NÃO`) · Senha provisória ·
Senha (oculta, só hash) · Criado em.

**Excursoes:** ID · Vendedor (e-mail) · Nome · Observações · Ida · Volta · Vagas · Vendidas ·
Responsável do grupo · Telefone do grupo · Atualizada em · Arte (oculta, JSON) · Miniatura (oculta).

## Fluxos
- **Criar conta master (uma vez):** o site mostra "Criar conta master" enquanto não existe master ativa.
  A pessoa escolhe nome, e-mail e senha e digita o **código de instalação**, que só aparece no
  registro do Apps Script ao rodar `configurar` (ninguém de fora cria a master antes). Depois some.
- **Master cria conta:** nome + e-mail → o site mostra uma **senha provisória** de 6 dígitos para
  passar à pessoa (também fica na coluna "Senha provisória" até ser usada).
- **Entrar:** e-mail + senha. Com a senha provisória, o site pede para criar a senha própria
  (mín. 8, diferente da provisória) e já entra. Sessão assinada vale 30 dias.
- **Esqueceu a senha:** master usa "Nova senha provisória" (site) ou escreve uma na coluna. A senha
  antiga e as sessões abertas param de valer.
- **Desativar:** Ativo = NÃO (site ou planilha). A sessão cai na próxima ação.
- **Recuperar a master:** Ativo da master = NÃO na planilha + rodar `configurar` → código novo.

## Telas do site
1. Criar conta master (só enquanto não existe) · Entrar · Criar sua senha.
2. Início (atalhos + continuar de onde parou).
3. Minhas excursões – abas Acontecendo / Próximas / Encerradas (pelas datas); abrir, duplicar, excluir.
4. Editor – passo a passo atual + passo "Dados da excursão" (nome, observações, vagas, vendidas,
   responsável e telefone do grupo). Salva sozinho na planilha ("Salvando…" / "Salvo").
5. Painel (master) – todas as excursões com a pessoa; filtro por pessoa e situação; total de vagas.
6. Contas (master) – adicionar, ativar/desativar, nova senha provisória.

## Servidor (Apps Script, App da Web)
POST com JSON em texto (sem pré-verificação de CORS). Resposta `{ ok, ...dados }` ou `{ ok: false, erro }`.

| Ação | Quem | Faz |
|---|---|---|
| `status` | todos | `{ precisaMaster }` |
| `criarMaster` {nome, email, senha, codigoInstalacao} | todos, só sem master | cria master e entra |
| `entrar` {email, senha} | todos | token + usuário, ou `{ precisaNovaSenha }` com a provisória |
| `criarSenha` {email, provisoria, senha} | todos | troca provisória pela senha própria e entra |
| `eu` {token} | logado | confere sessão |
| `listar` {token} | logado | vendedor: as próprias; master: todas (+ nome da pessoa) |
| `salvar` {token, excursao} | logado | cria ou atualiza (só o dono) |
| `excluir` {token, id} | logado | só o dono |
| `contas` {token} | master | lista contas |
| `salvarConta` {token, email, nome?, ativo?, novaProvisoria?} | master | cria/altera vendedor; devolve provisória |

## Segurança e limites
- Login feito à mão (não é um serviço de autenticação pronto). Senha: HMAC com segredo do script +
  sal por pessoa + 500 rodadas de SHA-256; nunca em texto na planilha (a provisória fica até ser usada).
- Token assinado com o segredo; conta desativada ou com provisória nova perde a sessão.
- 5 erros seguidos bloqueiam 10 minutos (por e-mail; criação da master tem o próprio limite).
- Códigos de 6 dígitos gerados a partir de UUID (aleatório seguro).
- Textos começando com `= + - @` entram como texto (sem virar fórmula na planilha).
- Quem tiver acesso de edição à planilha vê e altera tudo: deixar só com a master.
- Lentidão medida em 15/09/2026 (App da Web implantado): 2–6 s por chamada, picos de ~12 s e uma acima
  de 30 s, inclusive em chamada que nem abre a planilha (é do Google, não do script). Às vezes volta uma
  página HTML no lugar do JSON. Por isso o site é **local-first**: salva no aparelho na hora e sincroniza
  com a planilha em segundo plano, com nova tentativa; só o login espera o servidor.

## Passos do usuário (não automatizáveis por mim)
1. Criar uma planilha nova na conta Google do resort (ex.: "Village – Excursões").
2. Extensões → Apps Script → colar `apps-script/Codigo.gs` → Salvar.
3. Selecionar `configurar` → Executar → autorizar ("app não verificado": Avançado → acessar).
   Anotar o **código de instalação** que aparece no registro de execução.
4. Implantar → Nova implantação → App da Web → Executar como: Eu; Quem pode acessar: Qualquer pessoa.
5. Me passar a URL do App da Web (termina em `/exec`). O código de instalação fica com vocês.
6. Depois que eu ligar o site: "Criar conta master" com nome, e-mail, senha e o código.

## Construção
1. Cliente do servidor no site + Criar master / Entrar / Criar sua senha + sessão.
2. Minhas excursões lendo/gravando na planilha (as salvas no aparelho podem ser enviadas uma vez).
3. Passo "Dados da excursão".
4. Painel e Contas da master.
5. Verificação: vendedor não vê/altera de outro (chamando o servidor direto), master não pode ser
   criada de novo, desativado cai, provisória nova derruba sessão, arte reabre igual, celular.
