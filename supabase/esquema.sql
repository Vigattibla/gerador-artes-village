-- Gerador de Artes – contas e biblioteca de excursões
-- Rodar inteiro no SQL Editor do Supabase (pode rodar de novo: é idempotente).

create schema if not exists privado;  -- fora da API: funções de checagem das regras
grant usage on schema privado to authenticated;

-- ---------------------------------------------------------------- tabelas
create table if not exists public.perfis (
  id           uuid primary key references auth.users (id) on delete cascade,
  nome         text not null,
  papel        text not null default 'vendedor' check (papel in ('chefe', 'vendedor')),
  ativo        boolean not null default true,
  trocar_senha boolean not null default true,
  criado_em    timestamptz not null default now()
);

create table if not exists public.excursoes (
  id                uuid primary key default gen_random_uuid(),
  vendedor_id       uuid not null default auth.uid() references public.perfis (id) on delete cascade,
  nome              text not null default 'Nova excursão',
  observacoes       text not null default '',
  arte              jsonb not null default '{}'::jsonb,  -- estado do editor: arte, campos, foto, ajuste, personagem
  ida               date,
  volta             date,
  vagas_total       integer check (vagas_total >= 0),
  vagas_vendidas    integer not null default 0 check (vagas_vendidas >= 0),
  grupo_responsavel text not null default '',
  grupo_telefone    text not null default '',
  criada_em         timestamptz not null default now(),
  atualizada_em     timestamptz not null default now(),
  constraint volta_depois_da_ida check (ida is null or volta is null or volta >= ida),
  constraint vendidas_ate_o_total check (vagas_total is null or vagas_vendidas <= vagas_total)
);
create index if not exists excursoes_vendedor_idx on public.excursoes (vendedor_id);
create index if not exists excursoes_datas_idx on public.excursoes (ida, volta);

-- ---------------------------------------------------------------- funções de apoio
create or replace function privado.eh_chefe() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.perfis p where p.id = (select auth.uid()) and p.papel = 'chefe' and p.ativo);
$$;

create or replace function privado.esta_ativo() returns boolean
language sql stable security definer set search_path = '' as $$
  select exists (select 1 from public.perfis p where p.id = (select auth.uid()) and p.ativo);
$$;

revoke all on function privado.eh_chefe(), privado.esta_ativo() from public;
grant execute on function privado.eh_chefe(), privado.esta_ativo() to authenticated;

create or replace function privado.tocar_atualizada() returns trigger
language plpgsql set search_path = '' as $$
begin
  new.atualizada_em := now();
  return new;
end $$;

drop trigger if exists excursoes_atualizada on public.excursoes;
create trigger excursoes_atualizada before update on public.excursoes
  for each row execute function privado.tocar_atualizada();

-- o vendedor só consegue desligar o próprio aviso de "trocar senha" (não mexe em papel nem ativo)
create or replace function public.senha_trocada() returns void
language sql security definer set search_path = '' as $$
  update public.perfis set trocar_senha = false where id = (select auth.uid());
$$;
revoke all on function public.senha_trocada() from public, anon;
grant execute on function public.senha_trocada() to authenticated;

-- ---------------------------------------------------------------- regras de acesso (RLS)
alter table public.perfis enable row level security;
alter table public.excursoes enable row level security;

drop policy if exists "perfil: o próprio ou chefe" on public.perfis;
create policy "perfil: o próprio ou chefe" on public.perfis
  for select to authenticated
  using (id = (select auth.uid()) or (select privado.eh_chefe()));
-- sem insert/update/delete em perfis pela API: só a Edge Function (chave de serviço) altera

drop policy if exists "excursão: ler" on public.excursoes;
create policy "excursão: ler" on public.excursoes
  for select to authenticated
  using ((vendedor_id = (select auth.uid()) and (select privado.esta_ativo())) or (select privado.eh_chefe()));

drop policy if exists "excursão: criar" on public.excursoes;
create policy "excursão: criar" on public.excursoes
  for insert to authenticated
  with check (vendedor_id = (select auth.uid()) and (select privado.esta_ativo()));

drop policy if exists "excursão: editar" on public.excursoes;
create policy "excursão: editar" on public.excursoes
  for update to authenticated
  using (vendedor_id = (select auth.uid()) and (select privado.esta_ativo()))
  with check (vendedor_id = (select auth.uid()));

drop policy if exists "excursão: excluir" on public.excursoes;
create policy "excursão: excluir" on public.excursoes
  for delete to authenticated
  using (vendedor_id = (select auth.uid()) and (select privado.esta_ativo()));

revoke all on public.perfis, public.excursoes from anon;

-- ---------------------------------------------------------------- primeiro chefe
-- 1) Authentication > Users > Add user (e-mail e senha do chefe, marcar "Auto Confirm User")
-- 2) Troque o e-mail e o nome abaixo e rode só este trecho:
--
-- insert into public.perfis (id, nome, papel, trocar_senha)
-- select id, 'Nome do chefe', 'chefe', false from auth.users where email = 'chefe@exemplo.com'
-- on conflict (id) do update set papel = 'chefe', ativo = true;
