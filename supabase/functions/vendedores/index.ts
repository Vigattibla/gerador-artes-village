// Edge Function "vendedores": só o chefe da área cria, desativa/reativa e define senha de vendedor.
// A chave de serviço (SUPABASE_SERVICE_ROLE_KEY) já existe no ambiente da função e nunca vai pro site.
import { createClient } from 'npm:@supabase/supabase-js@2';

const ORIGENS = ['https://vigattibla.github.io', 'http://localhost:8765'];

function cabecalhos(req: Request) {
  const origem = req.headers.get('Origin') ?? '';
  return {
    'Access-Control-Allow-Origin': ORIGENS.includes(origem) ? origem : ORIGENS[0],
    'Access-Control-Allow-Headers': 'authorization, x-client-info, apikey, content-type',
    'Access-Control-Allow-Methods': 'POST, OPTIONS',
    'Content-Type': 'application/json',
  };
}

Deno.serve(async (req) => {
  const h = cabecalhos(req);
  const responder = (corpo: unknown, status = 200) => new Response(JSON.stringify(corpo), { status, headers: h });
  if (req.method === 'OPTIONS') return new Response('ok', { headers: h });
  if (req.method !== 'POST') return responder({ erro: 'Use POST.' }, 405);

  const admin = createClient(Deno.env.get('SUPABASE_URL')!, Deno.env.get('SUPABASE_SERVICE_ROLE_KEY')!, {
    auth: { persistSession: false, autoRefreshToken: false },
  });

  // quem chamou precisa estar logado e ser chefe ativo
  const token = (req.headers.get('Authorization') ?? '').replace(/^Bearer\s+/i, '');
  const { data: quem, error: erroQuem } = await admin.auth.getUser(token);
  if (erroQuem || !quem.user) return responder({ erro: 'Entre de novo para continuar.' }, 401);
  const { data: chefe } = await admin.from('perfis').select('papel, ativo').eq('id', quem.user.id).maybeSingle();
  if (chefe?.papel !== 'chefe' || !chefe.ativo) return responder({ erro: 'Só o chefe da área pode fazer isso.' }, 403);

  let corpo: Record<string, unknown>;
  try {
    corpo = await req.json();
  } catch {
    return responder({ erro: 'Pedido inválido.' }, 400);
  }
  const senha = String(corpo.senha ?? '');

  if (corpo.acao === 'criar') {
    const nome = String(corpo.nome ?? '').trim();
    const email = String(corpo.email ?? '').trim().toLowerCase();
    if (!nome || !/^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email)) return responder({ erro: 'Preencha o nome e um e-mail válido.' }, 400);
    if (senha.length < 8) return responder({ erro: 'A senha provisória precisa ter pelo menos 8 caracteres.' }, 400);
    const { data, error } = await admin.auth.admin.createUser({ email, password: senha, email_confirm: true, user_metadata: { nome } });
    if (error || !data.user) {
      const existe = /already|registered|exists/i.test(error?.message ?? '');
      return responder({ erro: existe ? 'Já existe uma conta com esse e-mail.' : 'Não deu pra criar a conta.' }, 400);
    }
    const { error: erroPerfil } = await admin.from('perfis').insert({ id: data.user.id, nome, papel: 'vendedor' });
    if (erroPerfil) {
      await admin.auth.admin.deleteUser(data.user.id); // não deixa login sem perfil
      return responder({ erro: 'Não deu pra criar a conta.' }, 500);
    }
    return responder({ id: data.user.id });
  }

  // as outras ações mexem num vendedor existente (nunca em outro chefe)
  const id = String(corpo.id ?? '');
  const { data: alvo } = await admin.from('perfis').select('papel').eq('id', id).maybeSingle();
  if (alvo?.papel !== 'vendedor') return responder({ erro: 'Vendedor não encontrado.' }, 404);

  if (corpo.acao === 'desativar' || corpo.acao === 'ativar') {
    const ativo = corpo.acao === 'ativar';
    const { error } = await admin.auth.admin.updateUserById(id, { ban_duration: ativo ? 'none' : '876000h' });
    if (error) return responder({ erro: 'Não deu pra mudar o acesso.' }, 400);
    await admin.from('perfis').update({ ativo }).eq('id', id);
    return responder({ ok: true });
  }

  if (corpo.acao === 'nova_senha') {
    if (senha.length < 8) return responder({ erro: 'A senha provisória precisa ter pelo menos 8 caracteres.' }, 400);
    const { error } = await admin.auth.admin.updateUserById(id, { password: senha });
    if (error) return responder({ erro: 'Não deu pra definir a senha.' }, 400);
    await admin.from('perfis').update({ trocar_senha: true }).eq('id', id);
    return responder({ ok: true });
  }

  return responder({ erro: 'Ação desconhecida.' }, 400);
});
