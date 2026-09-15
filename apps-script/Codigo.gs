/**
 * Village Resort – contas e excursões dos vendedores numa planilha Google.
 *
 * Instalação (uma vez, na conta Google do resort):
 * 1. Crie uma planilha nova. Extensões > Apps Script. Apague o que tiver e cole este arquivo. Salve.
 * 2. Escolha a função "configurar" e clique em Executar (autorize o acesso à planilha).
 *    O registro de execução mostra o CÓDIGO DE INSTALAÇÃO da conta master.
 * 3. Implantar > Nova implantação > tipo "App da Web" > Executar como: Eu > Quem pode acessar: Qualquer pessoa.
 * 4. Copie a URL do App da Web (termina em /exec) e coloque no site.
 * 5. No site: "Criar conta master" com nome, e-mail, senha e o código de instalação.
 *
 * Perdeu o acesso da master? Na aba Vendedores troque o Ativo dela para NÃO e rode "configurar" de novo:
 * sai um código novo para criar outra master.
 * Toda vez que mudar este arquivo: Implantar > Gerenciar implantações > editar > Nova versão.
 */

const ABA_VENDEDORES = 'Vendedores';
const ABA_EXCURSOES = 'Excursoes';
const COLUNAS_VENDEDORES = ['Email', 'Nome', 'Papel', 'Ativo', 'Senha provisória', 'Senha (não mexer)', 'Criado em'];
const COLUNAS_EXCURSOES = ['ID', 'Vendedor', 'Nome', 'Observações', 'Ida', 'Volta', 'Vagas', 'Vendidas',
  'Responsável do grupo', 'Telefone do grupo', 'Atualizada em', 'Arte (não mexer)', 'Miniatura (não mexer)'];
const DIAS_SESSAO = 30;
const LIMITE_CELULA = 45000; // a planilha aceita até 50 mil caracteres por célula
const TENTATIVAS = 5;        // erros seguidos antes de bloquear por 10 minutos

// ---------------------------------------------------------------- instalação
function configurar() {
  const ss = SpreadsheetApp.getActive();
  const vendedores = criarAba_(ss, ABA_VENDEDORES, COLUNAS_VENDEDORES);
  const excursoes = criarAba_(ss, ABA_EXCURSOES, COLUNAS_EXCURSOES);
  vendedores.getRange('C2:C').setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(['vendedor', 'master']).build());
  vendedores.getRange('D2:D').setDataValidation(
    SpreadsheetApp.newDataValidation().requireValueInList(['SIM', 'NÃO']).build());
  vendedores.hideColumns(6);    // senha (hash)
  excursoes.hideColumns(12, 2); // arte e miniatura
  const props = PropertiesService.getScriptProperties();
  if (!props.getProperty('SEGREDO')) props.setProperty('SEGREDO', Utilities.getUuid() + Utilities.getUuid());
  if (existeMaster_()) {
    props.deleteProperty('CODIGO_INSTALACAO');
    console.log('Já existe conta master ativa. Nenhum código de instalação gerado.');
  } else {
    const codigo = codigo_();
    props.setProperty('CODIGO_INSTALACAO', codigo);
    console.log('Código de instalação da conta master: ' + codigo);
  }
}

function criarAba_(ss, nome, colunas) {
  const aba = ss.getSheetByName(nome) || ss.insertSheet(nome);
  if (aba.getLastRow() === 0) {
    aba.appendRow(colunas);
    aba.setFrozenRows(1);
    aba.getRange(1, 1, 1, colunas.length).setFontWeight('bold');
  }
  return aba;
}

// ---------------------------------------------------------------- entrada
function doGet() {
  return saida_({ ok: true, servico: 'village-excursoes' });
}

function doPost(e) {
  try {
    const pedido = JSON.parse(e.postData.contents);
    const acao = ACOES[pedido.acao];
    if (!acao) throw aviso_('Ação desconhecida.');
    return saida_(Object.assign({ ok: true }, acao(pedido)));
  } catch (err) {
    if (!err.publico) console.error(err);
    return saida_({ ok: false, erro: err.publico ? err.message : 'Algo deu errado. Tente de novo.' });
  }
}

function saida_(obj) {
  return ContentService.createTextOutput(JSON.stringify(obj)).setMimeType(ContentService.MimeType.JSON);
}

function aviso_(mensagem) { // erro que pode ser mostrado ao usuário
  const e = new Error(mensagem);
  e.publico = true;
  return e;
}

// ---------------------------------------------------------------- ações do site
const ACOES = {
  // o site pergunta se ainda falta criar a conta master
  status: function () {
    return { precisaMaster: !existeMaster_() };
  },

  criarMaster: function (p) {
    const falhou = tentativa_('instalacao');
    return trava_(function () {
      const props = PropertiesService.getScriptProperties();
      if (existeMaster_()) throw aviso_('A conta master já foi criada. Entre com e-mail e senha.');
      const instalacao = props.getProperty('CODIGO_INSTALACAO');
      if (!instalacao || String(p.codigoInstalacao || '').trim() !== instalacao) {
        falhou();
        throw aviso_('Código de instalação incorreto. Ele aparece no registro ao rodar "configurar" no Apps Script.');
      }
      const email = email_(p.email);
      const nome = texto_(p.nome, 100);
      const senha = String(p.senha || '');
      if (!nome) throw aviso_('Digite seu nome.');
      if (!emailValido_(email)) throw aviso_('Digite um e-mail válido.');
      if (senha.length < 8) throw aviso_('A senha precisa ter pelo menos 8 caracteres.');
      if (vendedor_(email)) throw aviso_('Esse e-mail já tem conta na planilha.');
      const sal = Utilities.getUuid();
      aba_(ABA_VENDEDORES).appendRow([email, nome, 'master', 'SIM', '', sal + '$' + hash_(senha, sal), new Date()]);
      props.deleteProperty('CODIGO_INSTALACAO');
      return sessao_({ email: email, nome: nome, papel: 'master' });
    });
  },

  // senha provisória (criada pela master) vale só para chegar na tela de criar a senha própria
  entrar: function (p) {
    const email = email_(p.email);
    const falhou = tentativa_(email);
    const v = vendedor_(email);
    const senha = String(p.senha || '');
    if (!v || !v.ativo) { falhou(); throw aviso_('E-mail ou senha incorretos.'); }
    if (v.provisoria) {
      if (senha.trim() === v.provisoria) return { precisaNovaSenha: true };
      falhou();
      throw aviso_('E-mail ou senha incorretos.');
    }
    const partes = v.senha.split('$');
    if (partes.length !== 2 || hash_(senha, partes[0]) !== partes[1]) {
      falhou();
      throw aviso_('E-mail ou senha incorretos.');
    }
    return sessao_(v);
  },

  criarSenha: function (p) {
    const email = email_(p.email);
    const falhou = tentativa_(email);
    const v = vendedor_(email);
    if (!v || !v.ativo || !v.provisoria || String(p.provisoria || '').trim() !== v.provisoria) {
      falhou();
      throw aviso_('E-mail ou senha provisória incorretos.');
    }
    const senha = String(p.senha || '');
    if (senha.length < 8) throw aviso_('A senha precisa ter pelo menos 8 caracteres.');
    if (senha.trim() === v.provisoria) throw aviso_('Escolha uma senha diferente da provisória.');
    const sal = Utilities.getUuid();
    trava_(function () {
      aba_(ABA_VENDEDORES).getRange(v.linha, 5, 1, 2).setValues([['', sal + '$' + hash_(senha, sal)]]);
    });
    v.provisoria = '';
    return sessao_(v);
  },

  eu: function (p) {
    return { usuario: publico_(usuario_(p.token)) };
  },

  listar: function (p) {
    const u = usuario_(p.token);
    const nomes = {};
    vendedores_().forEach(function (v) { nomes[v.email] = v.nome; });
    const lista = excursoes_()
      .filter(function (x) { return u.papel === 'master' || x.vendedor === u.email; })
      .map(function (x) { delete x.linha; x.vendedorNome = nomes[x.vendedor] || x.vendedor; return x; });
    return { excursoes: lista };
  },

  salvar: function (p) {
    const u = usuario_(p.token);
    const x = p.excursao || {};
    const arte = JSON.stringify(x.arte || {});
    if (arte.length > LIMITE_CELULA) throw aviso_('A arte ficou grande demais para salvar.');
    const mini = String(x.mini || '').length <= LIMITE_CELULA ? String(x.mini || '') : '';
    return trava_(function () {
      const aba = aba_(ABA_EXCURSOES);
      const atual = x.id ? excursoes_().filter(function (e) { return e.id === x.id; })[0] : null;
      if (atual && atual.vendedor !== u.email) throw aviso_('Essa excursão é de outra pessoa.');
      const id = atual ? atual.id : Utilities.getUuid();
      const agora = new Date();
      const linha = [id, u.email, texto_(x.nome, 200), texto_(x.observacoes, 5000), data_(x.ida), data_(x.volta),
        numero_(x.vagas_total), numero_(x.vagas_vendidas) || 0, texto_(x.grupo_responsavel, 200),
        texto_(x.grupo_telefone, 40), agora, arte, mini];
      if (atual) aba.getRange(atual.linha, 1, 1, linha.length).setValues([linha]);
      else aba.appendRow(linha);
      return { excursao: { id: id, atualizada: agora.getTime() } };
    });
  },

  excluir: function (p) {
    const u = usuario_(p.token);
    return trava_(function () {
      const atual = excursoes_().filter(function (e) { return e.id === p.id; })[0];
      if (!atual) return {};
      if (atual.vendedor !== u.email) throw aviso_('Essa excursão é de outra pessoa.');
      aba_(ABA_EXCURSOES).deleteRow(atual.linha);
      return {};
    });
  },

  contas: function (p) {
    master_(p.token);
    const lista = vendedores_().map(function (v) {
      return { email: v.email, nome: v.nome, papel: v.papel, ativo: v.ativo, aguardandoSenha: !!v.provisoria };
    });
    lista.sort(function (a, b) { return a.nome.localeCompare(b.nome); });
    return { contas: lista };
  },

  // master cria conta de vendedor ou muda nome/ativo; "novaProvisoria" troca a senha por uma provisória
  salvarConta: function (p) {
    const u = master_(p.token);
    const email = email_(p.email);
    if (!emailValido_(email)) throw aviso_('Digite um e-mail válido.');
    return trava_(function () {
      const aba = aba_(ABA_VENDEDORES);
      const v = vendedor_(email);
      if (v && v.papel === 'master' && v.email !== u.email) throw aviso_('Outra conta master só se altera pela planilha.');
      if (v && v.email === u.email && (p.ativo === false || p.novaProvisoria)) throw aviso_('Isso não vale para a sua própria conta.');
      const provisoria = (!v || p.novaProvisoria) ? codigo_() : '';
      if (!v) {
        const nome = texto_(p.nome, 100);
        if (!nome) throw aviso_('Digite o nome da pessoa.');
        aba.appendRow([email, nome, 'vendedor', p.ativo === false ? 'NÃO' : 'SIM', provisoria, '', new Date()]);
      } else {
        if (p.nome) aba.getRange(v.linha, 2).setValue(texto_(p.nome, 100));
        if (typeof p.ativo === 'boolean') aba.getRange(v.linha, 4).setValue(p.ativo ? 'SIM' : 'NÃO');
        if (provisoria) aba.getRange(v.linha, 5).setValue(provisoria);
      }
      return { provisoria: provisoria }; // o site mostra para a master passar à pessoa
    });
  },
};

// ---------------------------------------------------------------- sessão e senha
function segredo_() {
  const s = PropertiesService.getScriptProperties().getProperty('SEGREDO');
  if (!s) throw new Error('Rode a função "configurar" antes de usar.');
  return s;
}

function hash_(senha, sal) {
  let h = Utilities.computeHmacSha256Signature(sal + ':' + senha, segredo_());
  const salBytes = Utilities.newBlob(sal).getBytes();
  for (let i = 0; i < 500; i++) h = Utilities.computeDigest(Utilities.DigestAlgorithm.SHA_256, h.concat(salBytes));
  return Utilities.base64Encode(h);
}

function codigo_() { // 6 dígitos a partir de um UUID (aleatório seguro do Google)
  return String(parseInt(Utilities.getUuid().replace(/-/g, '').slice(0, 12), 16) % 900000 + 100000);
}

function sessao_(v) {
  const dados = Utilities.base64EncodeWebSafe(JSON.stringify({ e: v.email, x: Date.now() + DIAS_SESSAO * 864e5 }));
  const assinatura = Utilities.base64EncodeWebSafe(Utilities.computeHmacSha256Signature(dados, segredo_()));
  return { token: dados + '.' + assinatura, usuario: publico_(v) };
}

function usuario_(token) {
  const partes = String(token || '').split('.');
  const conferida = partes.length === 2 &&
    Utilities.base64EncodeWebSafe(Utilities.computeHmacSha256Signature(partes[0], segredo_())) === partes[1];
  if (!conferida) throw aviso_('Entre de novo para continuar.');
  const dados = JSON.parse(Utilities.newBlob(Utilities.base64DecodeWebSafe(partes[0])).getDataAsString());
  if (Date.now() > dados.x) throw aviso_('Sua sessão expirou. Entre de novo.');
  const v = vendedor_(dados.e);
  // conta desativada ou com senha provisória nova derruba a sessão na hora
  if (!v || !v.ativo || v.provisoria || !v.senha) throw aviso_('Seu acesso mudou. Entre de novo ou fale com a conta master.');
  return v;
}

function master_(token) {
  const u = usuario_(token);
  if (u.papel !== 'master') throw aviso_('Só a conta master pode fazer isso.');
  return u;
}

function existeMaster_() {
  return vendedores_().some(function (v) { return v.papel === 'master' && v.ativo && v.senha; });
}

function tentativa_(chave) { // bloqueia depois de muitos erros; devolve a função que conta um erro
  const cache = CacheService.getScriptCache();
  const k = 'falhas:' + chave;
  const falhas = Number(cache.get(k) || 0);
  if (falhas >= TENTATIVAS) throw aviso_('Muitas tentativas. Espere 10 minutos e tente de novo.');
  return function () { cache.put(k, String(falhas + 1), 600); };
}

function publico_(v) {
  return { email: v.email, nome: v.nome, papel: v.papel };
}

// ---------------------------------------------------------------- planilha
function aba_(nome) {
  const aba = SpreadsheetApp.getActive().getSheetByName(nome);
  if (!aba) throw new Error('Rode a função "configurar" antes de usar.');
  return aba;
}

function trava_(fn) { // uma gravação por vez
  const trava = LockService.getScriptLock();
  trava.waitLock(15000);
  try { return fn(); } finally { trava.releaseLock(); }
}

function vendedores_() {
  return aba_(ABA_VENDEDORES).getDataRange().getValues().slice(1).map(function (l, i) {
    return {
      linha: i + 2,
      email: email_(l[0]),
      nome: String(l[1]).trim(),
      papel: String(l[2]).trim().toLowerCase() === 'master' ? 'master' : 'vendedor',
      ativo: String(l[3]).trim().toUpperCase() === 'SIM',
      provisoria: String(l[4]).trim(),
      senha: String(l[5]).trim(),
    };
  }).filter(function (v) { return v.email; });
}

function vendedor_(email) {
  return vendedores_().filter(function (v) { return v.email === email; })[0] || null;
}

function excursoes_() {
  const fuso = Session.getScriptTimeZone();
  return aba_(ABA_EXCURSOES).getDataRange().getValues().slice(1).map(function (l, i) {
    let arte = {};
    try { arte = JSON.parse(l[11] || '{}'); } catch (e) {}
    return {
      linha: i + 2,
      id: String(l[0]),
      vendedor: email_(l[1]),
      nome: String(l[2]),
      observacoes: String(l[3]),
      ida: l[4] instanceof Date ? Utilities.formatDate(l[4], fuso, 'yyyy-MM-dd') : String(l[4] || ''),
      volta: l[5] instanceof Date ? Utilities.formatDate(l[5], fuso, 'yyyy-MM-dd') : String(l[5] || ''),
      vagas_total: l[6] === '' ? null : Number(l[6]),
      vagas_vendidas: Number(l[7] || 0),
      grupo_responsavel: String(l[8]),
      grupo_telefone: String(l[9]),
      atualizada: l[10] instanceof Date ? l[10].getTime() : 0,
      arte: arte,
      mini: String(l[12] || ''),
    };
  }).filter(function (x) { return x.id; });
}

// ---------------------------------------------------------------- limpeza do que chega do site
function email_(v) {
  return String(v || '').trim().toLowerCase();
}

function emailValido_(email) {
  return /^[^@\s]+@[^@\s]+\.[^@\s]+$/.test(email);
}

function texto_(v, max) { // começa com = + - @: a planilha trataria como fórmula
  const s = String(v == null ? '' : v).trim().slice(0, max);
  return /^[=+\-@]/.test(s) ? "'" + s : s;
}

function data_(v) {
  return /^\d{4}-\d{2}-\d{2}$/.test(String(v || '')) ? new Date(v + 'T12:00:00') : '';
}

function numero_(v) {
  return v === '' || v == null || isNaN(Number(v)) ? '' : Math.max(0, Math.floor(Number(v)));
}
