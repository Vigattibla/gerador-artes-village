// Roda o apps-script/Codigo.gs no Node com uma planilha falsa e confere o fluxo de contas, campanhas e vendas.
//   node tests/teste_apps_script.js
const fs = require('fs');
const path = require('path');
const crypto = require('crypto');
const assert = require('assert');

// ---------- serviços do Google, só o que o Codigo.gs usa ----------
class Faixa {
  constructor(aba, l, c, nl = 1, nc = 1) { Object.assign(this, { aba, l, c, nl, nc }); }
  getValues() { return this.aba.linhas.slice(this.l - 1, this.l - 1 + this.nl).map(r => Array.from({ length: this.nc }, (_, i) => r[this.c - 1 + i] ?? '')); }
  setValues(v) { v.forEach((r, i) => r.forEach((x, j) => { (this.aba.linhas[this.l - 1 + i] ??= [])[this.c - 1 + j] = x; })); }
  setValue(x) { this.setValues([[x]]); }
  setDataValidation() {}
  setFontWeight() {}
}
class Aba {
  constructor() { this.linhas = []; }
  appendRow(r) { this.linhas.push([...r]); }
  getLastRow() { return this.linhas.length; }
  getDataRange() { return new Faixa(this, 1, 1, this.linhas.length, Math.max(1, ...this.linhas.map(r => r.length))); }
  getRange(l, c, nl, nc) { return typeof l === 'string' ? new Faixa(this, 1, 1) : new Faixa(this, l, c, nl, nc); }
  deleteRow(l) { this.linhas.splice(l - 1, 1); }
  hideColumns() {}
  setFrozenRows() {}
}
const abas = {};
const props = {}, cache = {};
const bytes = s => Array.from(Buffer.from(s));
global.SpreadsheetApp = {
  getActive: () => ({ getSheetByName: n => abas[n] || null, insertSheet: n => (abas[n] = new Aba()) }),
  newDataValidation: () => ({ requireValueInList() { return this; }, build() { return {}; } }),
};
global.PropertiesService = { getScriptProperties: () => ({ getProperty: k => props[k] ?? null, setProperty: (k, v) => { props[k] = v; }, deleteProperty: k => { delete props[k]; } }) };
global.CacheService = { getScriptCache: () => ({ get: k => cache[k] ?? null, put: (k, v) => { cache[k] = v; } }) };
global.LockService = { getScriptLock: () => ({ waitLock() {}, releaseLock() {} }) };
global.Session = { getScriptTimeZone: () => 'America/Sao_Paulo' };
global.ContentService = { MimeType: { JSON: 'json' }, createTextOutput: s => ({ setMimeType() { return s; } }) };
global.console = console;
global.Utilities = {
  DigestAlgorithm: { SHA_256: 'sha256' },
  getUuid: () => crypto.randomUUID(),
  computeHmacSha256Signature: (dados, chave) => bytes(crypto.createHmac('sha256', chave).update(Buffer.from(typeof dados === 'string' ? dados : dados)).digest()),
  computeDigest: (alg, dados) => bytes(crypto.createHash('sha256').update(Buffer.from(dados.map(b => b & 255))).digest()),
  base64Encode: b => Buffer.from(b.map(x => x & 255)).toString('base64'),
  base64EncodeWebSafe: b => Buffer.from(typeof b === 'string' ? b : b.map(x => x & 255)).toString('base64url'),
  base64DecodeWebSafe: s => bytes(Buffer.from(s, 'base64url')),
  newBlob: x => ({ getBytes: () => bytes(x), getDataAsString: () => Buffer.from(x).toString() }),
  formatDate: (d, fuso, fmt) => d.toISOString().slice(0, 10),
};

const codigo = fs.readFileSync(path.join(__dirname, '..', 'apps-script', 'Codigo.gs'), 'utf8');
const { configurar, doPost } = new Function(codigo + '\nreturn { configurar, doPost };')();

const logs = [];
const log0 = console.log;
console.log = m => logs.push(m);
configurar();
console.log = log0;
const instalacao = /(\d{6})/.exec(logs.join(' '))[1];

function chamar(acao, dados = {}) {
  return JSON.parse(doPost({ postData: { contents: JSON.stringify({ acao, ...dados }) } }));
}
const ok = (r, msg) => { assert.ok(r.ok, `${msg}: ${r.erro}`); return r; };
const erro = (r, trecho) => assert.ok(!r.ok && r.erro.includes(trecho), `esperava erro "${trecho}", veio ${JSON.stringify(r)}`);

// contas
const m = ok(chamar('criarMaster', { nome: 'Chefe', email: 'chefe@x.com', senha: 'senha1234', codigoInstalacao: instalacao }), 'criar master');
const prov = ok(chamar('salvarConta', { token: m.token, nome: 'Ana', email: 'ana@x.com', papel: 'adsign' }), 'criar conta').provisoria;
assert.strictEqual(abas.Vendedores.linhas[2][2], 'vendedor', 'conta nova sempre é vendedor (não existe mais adsign)');
ok(chamar('entrar', { email: 'ana@x.com', senha: prov }), 'entrar com provisória');
const v = ok(chamar('criarSenha', { email: 'ana@x.com', provisoria: prov, senha: 'outra1234' }), 'criar senha');

// campanhas: só a master cria; vendedor não vê rascunho
erro(chamar('salvarCampanha', { token: v.token, campanha: { nome: 'X' } }), 'Só a conta master');
const c = ok(chamar('salvarCampanha', { token: m.token, campanha: { nome: 'Feriado', vagas_total: '10', limite_venda: '2099-01-01', status: 'rascunho', pagamento: ['Pix'], roteiro: 'Dia 1' } }), 'criar campanha').campanha;
assert.strictEqual(ok(chamar('campanhas', { token: v.token }), 'listar').campanhas.length, 0, 'vendedor não vê rascunho');
ok(chamar('salvarCampanha', { token: m.token, campanha: { id: c.id, status: 'ativa', arte: { atual: 0, campos: { preco_1: '416,57' } }, mini: 'data:x' } }), 'ativar');
const lista = ok(chamar('campanhas', { token: v.token }), 'listar').campanhas;
assert.strictEqual(lista.length, 1);
assert.deepStrictEqual([lista[0].status, lista[0].vagas_total, lista[0].roteiro, lista[0].arte.campos.preco_1, lista[0].pagamento[0]],
  ['ativa', 10, 'Dia 1', '416,57', 'Pix'], 'campos da campanha voltam da planilha');

// vendas
ok(chamar('pegarCampanha', { token: v.token, id: c.id }), 'pegar');
erro(chamar('salvarVenda', { token: v.token, venda: { campanha: c.id, cliente: 'Joana', pessoas: 11 } }), 'Só restam 10');
const venda = ok(chamar('salvarVenda', { token: v.token, venda: { campanha: c.id, cliente: 'Joana', pessoas: 4, sinal_pago: true } }), 'vender').venda;
const depois = ok(chamar('campanhas', { token: v.token }), 'listar').campanhas[0];
assert.deepStrictEqual([depois.vendidas, depois.peguei], [4, true]);
erro(chamar('salvarVenda', { token: v.token, venda: { id: venda.id, status: 'confirmada' } }), 'Só a conta master');
ok(chamar('salvarVenda', { token: m.token, venda: { id: venda.id, status: 'confirmada' } }), 'confirmar');
assert.strictEqual(ok(chamar('vendas', { token: m.token, campanha: c.id }), 'vendas').vendas[0].vendedorNome, 'Ana');
erro(chamar('salvarCampanha', { token: m.token, campanha: { id: c.id, vagas_total: 3 } }), 'Já foram vendidas 4');
erro(chamar('excluirCampanha', { token: m.token, id: c.id }), 'já tem vendas');
ok(chamar('salvarVenda', { token: m.token, venda: { id: venda.id, status: 'cancelada' } }), 'cancelar');
assert.strictEqual(ok(chamar('campanhas', { token: m.token }), 'listar').campanhas[0].vendidas, 0, 'cancelada devolve as vagas');

console.log('ok: contas, campanhas e vendas do Apps Script');
