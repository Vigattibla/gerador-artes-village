# Servidor falso da planilha: mesmas ações e regras do apps-script/Codigo.gs, com os dados em memória.
# Serve pra testar o site sem criar conta nem mexer na planilha real.
#   python tests/mock_planilha.py            -> http://localhost:8766
#   site de teste: http://localhost:8765/?api=http://localhost:8766
#   GET /controle?atraso=2&falha=0.3         -> lentidão (s) e chance de devolver página HTML no lugar do JSON
#   GET /controle?resetar=1                  -> apaga contas e excursões
import hashlib
import json
import random
import time
import uuid
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from urllib.parse import parse_qs, urlparse

CONF = {'atraso': 0.3, 'falha': 0.0}
INSTALACAO = '111222'
CONTAS, EXCURSOES, TOKENS = {}, {}, {}


class Aviso(Exception):
    pass


def hash_(senha):
    return hashlib.sha256(senha.encode()).hexdigest()


def publico(c):
    return {'email': c['email'], 'nome': c['nome'], 'papel': c['papel']}


def sessao(c):
    token = uuid.uuid4().hex
    TOKENS[token] = c['email']
    return {'token': token, 'usuario': publico(c)}


def usuario(p):
    c = CONTAS.get(TOKENS.get(p.get('token') or ''))
    if not c:
        raise Aviso('Entre de novo para continuar.')
    if not c['ativo'] or c['provisoria'] or not c['senha']:
        raise Aviso('Seu acesso mudou. Entre de novo ou fale com a conta master.')
    return c


def master(p):
    c = usuario(p)
    if c['papel'] != 'master':
        raise Aviso('Só a conta master pode fazer isso.')
    return c


def existe_master():
    return any(c['papel'] == 'master' and c['ativo'] and c['senha'] for c in CONTAS.values())


def numero(v):
    try:
        return max(0, int(float(v)))
    except (TypeError, ValueError):
        return None


def acao(p):
    a = p.get('acao')
    email = str(p.get('email') or '').strip().lower()
    senha = str(p.get('senha') or '')

    if a == 'status':
        return {'precisaMaster': not existe_master()}

    if a == 'criarMaster':
        if existe_master():
            raise Aviso('A conta master já foi criada. Entre com e-mail e senha.')
        if str(p.get('codigoInstalacao') or '').strip() != INSTALACAO:
            raise Aviso('Código de instalação incorreto. Ele aparece no registro ao rodar "configurar" no Apps Script.')
        nome = str(p.get('nome') or '').strip()
        if not nome:
            raise Aviso('Digite seu nome.')
        if '@' not in email:
            raise Aviso('Digite um e-mail válido.')
        if len(senha) < 8:
            raise Aviso('A senha precisa ter pelo menos 8 caracteres.')
        c = CONTAS[email] = {'email': email, 'nome': nome, 'papel': 'master', 'ativo': True, 'provisoria': '', 'senha': hash_(senha)}
        return sessao(c)

    if a == 'entrar':
        c = CONTAS.get(email)
        if not c or not c['ativo']:
            raise Aviso('E-mail ou senha incorretos.')
        if c['provisoria']:
            if senha.strip() == c['provisoria']:
                return {'precisaNovaSenha': True}
            raise Aviso('E-mail ou senha incorretos.')
        if hash_(senha) != c['senha']:
            raise Aviso('E-mail ou senha incorretos.')
        return sessao(c)

    if a == 'criarSenha':
        c = CONTAS.get(email)
        if not c or not c['ativo'] or not c['provisoria'] or str(p.get('provisoria') or '').strip() != c['provisoria']:
            raise Aviso('E-mail ou senha provisória incorretos.')
        if len(senha) < 8:
            raise Aviso('A senha precisa ter pelo menos 8 caracteres.')
        if senha.strip() == c['provisoria']:
            raise Aviso('Escolha uma senha diferente da provisória.')
        c['provisoria'], c['senha'] = '', hash_(senha)
        return sessao(c)

    if a == 'eu':
        return {'usuario': publico(usuario(p))}

    if a == 'listar':
        u = usuario(p)
        return {'excursoes': [dict(x, vendedorNome=CONTAS.get(x['vendedor'], {}).get('nome', x['vendedor']))
                              for x in EXCURSOES.values() if u['papel'] == 'master' or x['vendedor'] == u['email']]}

    if a == 'salvar':
        u = usuario(p)
        x = p.get('excursao') or {}
        atual = EXCURSOES.get(x.get('id') or '')
        if atual and atual['vendedor'] != u['email']:
            raise Aviso('Essa excursão é de outra pessoa.')
        i = atual['id'] if atual else str(uuid.uuid4())
        agora = int(time.time() * 1000)
        EXCURSOES[i] = {
            'id': i, 'vendedor': u['email'], 'nome': x.get('nome', ''), 'observacoes': x.get('observacoes', ''),
            'ida': x.get('ida', ''), 'volta': x.get('volta', ''), 'vagas_total': numero(x.get('vagas_total')),
            'vagas_vendidas': numero(x.get('vagas_vendidas')) or 0, 'grupo_responsavel': x.get('grupo_responsavel', ''),
            'grupo_telefone': x.get('grupo_telefone', ''), 'atualizada': agora, 'arte': x.get('arte') or {}, 'mini': x.get('mini', ''),
        }
        return {'excursao': {'id': i, 'atualizada': agora}}

    if a == 'excluir':
        u = usuario(p)
        atual = EXCURSOES.get(p.get('id') or '')
        if atual:
            if atual['vendedor'] != u['email']:
                raise Aviso('Essa excursão é de outra pessoa.')
            del EXCURSOES[atual['id']]
        return {}

    if a == 'contas':
        master(p)
        return {'contas': sorted([{'email': c['email'], 'nome': c['nome'], 'papel': c['papel'], 'ativo': c['ativo'],
                                   'aguardandoSenha': bool(c['provisoria'])} for c in CONTAS.values()], key=lambda c: c['nome'])}

    if a == 'salvarConta':
        u = master(p)
        if '@' not in email:
            raise Aviso('Digite um e-mail válido.')
        c = CONTAS.get(email)
        if c and c['papel'] == 'master' and c['email'] != u['email']:
            raise Aviso('Outra conta master só se altera pela planilha.')
        if c and c['email'] == u['email'] and (p.get('ativo') is False or p.get('novaProvisoria')):
            raise Aviso('Isso não vale para a sua própria conta.')
        provisoria = str(random.randint(100000, 999999)) if (not c or p.get('novaProvisoria')) else ''
        if not c:
            nome = str(p.get('nome') or '').strip()
            if not nome:
                raise Aviso('Digite o nome da pessoa.')
            CONTAS[email] = {'email': email, 'nome': nome, 'papel': 'vendedor', 'ativo': p.get('ativo') is not False,
                             'provisoria': provisoria, 'senha': ''}
        else:
            if p.get('nome'):
                c['nome'] = p['nome']
            if isinstance(p.get('ativo'), bool):
                c['ativo'] = p['ativo']
            if provisoria:
                c['provisoria'] = provisoria
        return {'provisoria': provisoria}

    raise Aviso('Ação desconhecida.')


class Handler(BaseHTTPRequestHandler):
    def enviar(self, corpo, tipo):
        dados = corpo.encode()
        self.send_response(200)
        self.send_header('Content-Type', tipo)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Content-Length', str(len(dados)))
        self.end_headers()
        self.wfile.write(dados)

    def do_GET(self):
        url = urlparse(self.path)
        if url.path == '/controle':
            params = parse_qs(url.query)
            if 'resetar' in params:
                CONTAS.clear(); EXCURSOES.clear(); TOKENS.clear()
            for k in ('atraso', 'falha'):
                if k in params:
                    CONF[k] = float(params[k][0])
            estado = {'conf': CONF, 'contas': {e: {k: v for k, v in c.items() if k != 'senha'} for e, c in CONTAS.items()},
                      'excursoes': [{k: v for k, v in x.items() if k not in ('mini', 'arte')} for x in EXCURSOES.values()]}
            return self.enviar(json.dumps(estado), 'application/json')
        self.enviar(json.dumps({'ok': True, 'servico': 'village-excursoes (falso)'}), 'application/json')

    def do_POST(self):
        time.sleep(CONF['atraso'])
        try:
            p = json.loads(self.rfile.read(int(self.headers.get('Content-Length') or 0)) or b'{}')
        except ValueError:
            p = {}
        if random.random() < CONF['falha']:
            return self.enviar('<!DOCTYPE html><html><body>Página do Google</body></html>', 'text/html')
        try:
            saida = {'ok': True, **acao(p)}
        except Aviso as e:
            saida = {'ok': False, 'erro': str(e)}
        self.enviar(json.dumps(saida), 'application/json')

    def log_message(self, *args):
        pass


if __name__ == '__main__':
    ThreadingHTTPServer(('127.0.0.1', 8766), Handler).serve_forever()
