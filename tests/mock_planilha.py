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
PAPEIS = ('master', 'adsign', 'vendedor')
CONTAS, EXCURSOES, TOKENS = {}, {}, {}
CAMPANHAS, VENDAS, PARTICIPANTES = {}, {}, set()
CAMPOS_CAMPANHA = ('nome', 'resumo', 'status', 'limite_venda', 'vagas_total', 'embarques', 'retorno', 'sinal', 'quitar_ate',
                   'pagamento', 'comissao', 'criancas', 'roteiro', 'inclui', 'nao_inclui', 'documentos', 'cancelamento',
                   'regras', 'contato_guia', 'textos', 'links', 'arte', 'mini')
STATUS_CAMPANHA = ('rascunho', 'ativa', 'pausada', 'encerrada')


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


def gestor(p):
    c = usuario(p)
    if c['papel'] not in ('master', 'adsign'):
        raise Aviso('Só a conta master ou adsign pode fazer isso.')
    return c


def vendidas(cid, sem=''):
    return sum(v['pessoas'] for v in VENDAS.values() if v['campanha'] == cid and v['status'] != 'cancelada' and v['id'] != sem)


def campanha_para(c, u):
    return dict(c, vendidas=vendidas(c['id']), participantes=len({e for i, e in PARTICIPANTES if i == c['id']}),
                peguei=(c['id'], u['email']) in PARTICIPANTES)


def semear():  # campanha de exemplo pra ver a tela cheia no teste
    i = str(uuid.uuid4())
    CAMPANHAS[i] = {
        'id': i, 'criada_por': 'master@teste.local', 'atualizada': int(time.time() * 1000), 'status': 'ativa',
        'nome': 'All Fun Inclusive – Feriado de Novembro', 'resumo': 'Pacote completo com tudo incluso para casais e famílias.',
        'limite_venda': '2026-11-05', 'vagas_total': 40, 'embarques': 'Praça da Estação, Belo Horizonte – 6h\nBig Shopping, Contagem – 6h40',
        'retorno': 'Domingo, saída do resort às 16h', 'sinal': 'R$ 200 no Pix', 'quitar_ate': '2026-11-10',
        'pagamento': ['Pix', 'Cartão de crédito'], 'comissao': '10% por venda confirmada',
        'criancas': 'Até 5 anos no colo não paga.\n6 a 10 anos paga meia.', 'roteiro': 'Sexta: chegada e jantar.\nSábado: parque aquático e festa.\nDomingo: café e retorno.',
        'inclui': 'Transporte, hospedagem, todas as refeições e bebidas, lazer completo.', 'nao_inclui': 'Passeios fora do resort.',
        'documentos': 'RG ou CNH com foto. Menores com certidão ou autorização.', 'cancelamento': 'Até 30 dias antes: devolve 90%.\nDe 29 a 15 dias: 50%.\nMenos de 15 dias: sem devolução.',
        'regras': 'Uma mala e uma bolsa de mão por pessoa.', 'contato_guia': 'Marcos – (31) 98888-7777',
        'textos': 'Feriado de Novembro no Village Resort! Tudo incluso, transporte saindo de BH. Garanta sua vaga comigo 👇\n\nÚltimas vagas pro feriado! Chama no WhatsApp.',
        'links': 'Roteiro em PDF – https://example.com/roteiro.pdf',
        'arte': {'atual': 0, 'foto': 'layout', 'personagem': True, 'ajuste': {},
                 'campos': {'preco_1': '416,57', 'ida_1': '2026-11-13', 'volta_1': '2026-11-16', 'parcelas': '7'}},
        'mini': '',
    }


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

    if a == 'dev':  # só no servidor falso: entra sem senha com uma conta de teste de cada tipo
        papel = p.get('papel') if p.get('papel') in PAPEIS else 'vendedor'
        nome = {'master': 'Chefe (teste)', 'adsign': 'Adsign (teste)', 'vendedor': 'Vendedora (teste)'}[papel]
        c = CONTAS.setdefault(f'{papel}@teste.local', {'email': f'{papel}@teste.local', 'nome': nome, 'papel': papel,
                                                       'ativo': True, 'provisoria': '', 'senha': hash_('teste1234')})
        if not CAMPANHAS:
            semear()
        return sessao(c)

    if a == 'campanhas':
        u = usuario(p)
        tudo = u['papel'] in ('master', 'adsign')
        return {'campanhas': [campanha_para(c, u) for c in sorted(CAMPANHAS.values(), key=lambda c: -c['atualizada'])
                              if tudo or c['status'] != 'rascunho']}

    if a == 'salvarCampanha':
        u = gestor(p)
        x = p.get('campanha') or {}
        atual = CAMPANHAS.get(x.get('id') or '')
        if x.get('id') and not atual:
            raise Aviso('Essa campanha não existe mais.')
        c = dict(atual) if atual else {'id': str(uuid.uuid4()), 'criada_por': u['email'], 'status': 'rascunho', 'nome': ''}
        for k in CAMPOS_CAMPANHA:
            if k in x:
                c[k] = x[k]
        if c['status'] not in STATUS_CAMPANHA:
            c['status'] = 'rascunho'
        if 'vagas_total' in x:
            c['vagas_total'] = numero(x['vagas_total'])
        if not str(c.get('nome') or '').strip():
            raise Aviso('Dê um nome para a campanha.')
        if c.get('vagas_total') is not None and c['vagas_total'] < vendidas(c['id']):
            raise Aviso(f'Já foram vendidas {vendidas(c["id"])} vagas. O total não pode ser menor que isso.')
        c['atualizada'] = int(time.time() * 1000)
        CAMPANHAS[c['id']] = c
        return {'campanha': campanha_para(c, u)}

    if a == 'excluirCampanha':
        gestor(p)
        cid = p.get('id') or ''
        if any(v['campanha'] == cid for v in VENDAS.values()):
            raise Aviso('Essa campanha já tem vendas. Mude a situação para Encerrada em vez de excluir.')
        CAMPANHAS.pop(cid, None)
        return {}

    if a == 'pegarCampanha':
        u = usuario(p)
        c = CAMPANHAS.get(p.get('id') or '')
        if not c or c['status'] == 'rascunho':
            raise Aviso('Essa campanha não está disponível.')
        PARTICIPANTES.add((c['id'], u['email']))
        return {}

    if a == 'vendas':
        u = usuario(p)
        cid = p.get('campanha') or ''
        return {'vendas': [dict(v, vendedorNome=CONTAS.get(v['vendedor'], {}).get('nome', v['vendedor'])) for v in VENDAS.values()
                           if (not cid or v['campanha'] == cid) and (u['papel'] == 'master' or v['vendedor'] == u['email'])]}

    if a == 'salvarVenda':
        u = usuario(p)
        x = p.get('venda') or {}
        atual = VENDAS.get(x.get('id') or '')
        if atual:  # só muda a situação: master confirma/cancela; vendedor cancela a própria enquanto pendente
            status = x.get('status')
            if status not in ('pendente', 'confirmada', 'cancelada'):
                raise Aviso('Situação inválida.')
            if u['papel'] != 'master' and (atual['vendedor'] != u['email'] or status != 'cancelada' or atual['status'] != 'pendente'):
                raise Aviso('Só a conta master confirma ou muda uma venda.')
            c = CAMPANHAS.get(atual['campanha'])
            if atual['status'] == 'cancelada' and status != 'cancelada' and c and c.get('vagas_total') is not None \
                    and atual['pessoas'] > c['vagas_total'] - vendidas(c['id'], atual['id']):
                raise Aviso('Não há vagas para reativar essa venda.')
            atual['status'] = status
            return {'venda': atual}
        c = CAMPANHAS.get(x.get('campanha') or '')
        if not c or c['status'] != 'ativa':
            raise Aviso('Essa campanha não está aceitando vendas.')
        if c.get('limite_venda') and c['limite_venda'] < time.strftime('%Y-%m-%d'):
            raise Aviso('O prazo de venda dessa campanha acabou.')
        cliente = str(x.get('cliente') or '').strip()
        pessoas = numero(x.get('pessoas')) or 0
        if not cliente:
            raise Aviso('Digite o nome do cliente.')
        if pessoas < 1:
            raise Aviso('Digite quantas pessoas.')
        if c.get('vagas_total') is not None and pessoas > c['vagas_total'] - vendidas(c['id']):
            raise Aviso(f'Só restam {max(0, c["vagas_total"] - vendidas(c["id"]))} vagas nessa campanha.')
        i = str(uuid.uuid4())
        VENDAS[i] = {'id': i, 'campanha': c['id'], 'vendedor': u['email'], 'cliente': cliente, 'telefone': str(x.get('telefone') or ''),
                     'pessoas': pessoas, 'embarque': str(x.get('embarque') or ''), 'pagamento': str(x.get('pagamento') or ''),
                     'sinal_pago': bool(x.get('sinal_pago')), 'obs': str(x.get('obs') or ''), 'status': 'pendente',
                     'criada': int(time.time() * 1000)}
        PARTICIPANTES.add((c['id'], u['email']))
        return {'venda': VENDAS[i]}

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
            papel = p.get('papel') if p.get('papel') in ('vendedor', 'adsign') else 'vendedor'
            CONTAS[email] = {'email': email, 'nome': nome, 'papel': papel, 'ativo': p.get('ativo') is not False,
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
                CONTAS.clear(); EXCURSOES.clear(); TOKENS.clear(); CAMPANHAS.clear(); VENDAS.clear(); PARTICIPANTES.clear()
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
