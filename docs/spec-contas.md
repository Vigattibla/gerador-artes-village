# Especificação – Contas e biblioteca de excursões

Pedido do usuário em 15/09/2026. Requisitos no PRD (itens 8–11).

## Objetivo
Cada vendedor entra com e-mail e senha e tem a própria biblioteca de excursões: cria, edita, duplica,
baixa a arte de novo e acompanha vagas. O chefe da área cria e controla os acessos e vê tudo.

## Papéis
| Papel | Pode |
|---|---|
| Chefe da área | Entrar; criar vendedor (nome, e-mail, senha provisória); desativar/reativar; definir nova senha provisória; ver painel com as excursões de todos; ter as próprias excursões |
| Vendedor | Entrar; trocar a senha provisória no 1º acesso; criar, editar, duplicar e excluir **só as próprias** excursões |

Não existe cadastro aberto: o "sign up" do Supabase fica desligado.

## Telas
1. **Entrar** – e-mail, senha, "Entrar". Erro claro ("E-mail ou senha incorretos."). Conta desativada não entra.
2. **Trocar senha** – aparece só no 1º acesso (ou depois que o chefe define uma senha nova).
3. **Minhas excursões** – abas *Acontecendo*, *Próximas*, *Encerradas*; cartão com nome, datas, vagas
   (vendidas/total) e miniatura da arte; ações: Abrir, Duplicar, Excluir (com confirmação).
   Botão principal: "Nova excursão". Lista vazia vira convite pra criar a primeira.
4. **Editor** – o passo a passo atual com um passo novo no começo, *Dados da excursão*:
   nome, observações, vagas (total e vendidas), responsável do grupo (nome e telefone).
   Salva sozinho a cada alteração ("Salvo" discreto). Baixar/Enviar continuam no último passo.
5. **Painel do chefe** – todas as excursões com vendedor, datas, situação e vagas; filtro por vendedor
   e por situação; totais de vagas vendidas.
6. **Vendedores** (só chefe) – lista com situação da conta; "Adicionar vendedor"; desativar/reativar;
   "Definir nova senha".

Situação calculada pelas datas do pacote (menor ida e maior volta entre os pacotes da arte):
*Próxima* (ida > hoje) · *Acontecendo* (ida ≤ hoje ≤ volta) · *Encerrada* (volta < hoje).

## Dados (Supabase / Postgres) – `supabase/esquema.sql`
- `perfis`: id (= usuário do Auth), nome, papel (`chefe`|`vendedor`), ativo, trocar_senha.
- `excursoes`: vendedor_id, nome, observacoes, arte (jsonb com o estado do editor: arte escolhida,
  campos, foto, ajuste, personagem), ida, volta, vagas_total, vagas_vendidas, grupo_responsavel,
  grupo_telefone, criada_em, atualizada_em.

## Segurança
- Row Level Security em todas as tabelas. Vendedor ativo lê/grava só `vendedor_id = auth.uid()`;
  chefe lê tudo. Checagem de papel em função `privado.eh_chefe()` (security definer,
  `search_path = ''`, schema fora da API) pra não entrar em recursão.
- Criar/desativar/trocar senha de vendedor só pela Edge Function `vendedores`, que confere que quem
  chamou é chefe ativo antes de usar a chave de serviço. A chave de serviço nunca vai pro site.
- No site só vão a URL do projeto e a chave pública (anon/publishable), feitas pra ficar no navegador.
- Conta desativada: `ban_duration` no Auth (não entra) + `perfis.ativo = false` (RLS bloqueia dados).
- Sem e-mail automático: o envio embutido do Supabase só manda 2 por hora. O chefe passa a senha
  provisória ao vendedor; recuperação de senha também passa pelo chefe.

## Riscos e decisões pendentes
- **Plano grátis pausa o projeto após 1 semana sem uso.** Com vendedores usando toda semana não pausa;
  se pausar, o login para até alguém retomar no painel do Supabase. Alternativa: plano Pro (US$ 25/mês).
- Fotos continuam no GitHub Pages (públicas); só os dados das excursões ficam no Supabase.

## Passos do usuário (não automatizáveis por mim)
1. Criar conta em supabase.com e um projeto (região São Paulo). Guardar a senha do banco no gerenciador de senhas.
2. SQL Editor → colar e rodar `supabase/esquema.sql`.
3. Authentication → Sign In / Providers → desligar "Allow new users to sign up".
4. Authentication → Users → "Add user" com o e-mail e senha do chefe → rodar o trecho "primeiro chefe" do fim do `esquema.sql`.
5. Edge Functions → criar a função `vendedores` com o conteúdo de `supabase/functions/vendedores/index.ts`.
6. Me passar a **Project URL** e a **chave pública (anon/publishable)**. Nunca a service_role/secret.

## Construção (depois dos passos acima)
1. Cliente Supabase no site + tela Entrar/Trocar senha.
2. Minhas excursões (lista, abas, duplicar, excluir).
3. Editor: passo "Dados da excursão" + salvar sozinho + abrir excursão existente.
4. Painel do chefe + Vendedores.
5. Verificação: vendedor A não vê dados de B (teste direto na API), conta desativada não entra,
   chefe vê tudo, arte reabre igual ao que foi salvo, celular.
