# -*- coding: utf-8 -*-
"""Cria, lista e apaga redirects na coleção `redirects` do Payload (metakosmos.com.br).

Testado em 09/11/2026: POST /api/redirects {from, to, ativo}; o site responde 308 em segundos.
Cada redirect criado é gravado em otimizador/redirects.json (id, data, motivo), para conferir
depois e para desfazer.

    python scripts/otimizador/redirect_payload.py criar <de> <para> --motivo "texto"
    python scripts/otimizador/redirect_payload.py consolidar <slug-antigo> <slug-dono> --motivo "texto"
    python scripts/otimizador/redirect_payload.py listar
    python scripts/otimizador/redirect_payload.py apagar <id>
"""
import argparse, datetime, json, os, sys, time, urllib.error, urllib.request

BASE = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
REG = os.path.join(BASE, 'otimizador', 'redirects.json')
SITE = 'https://metakosmos.com.br'


def env():
    d = {}
    with open(os.path.join(BASE, '.env'), encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                d[k.strip()] = v.strip().strip('"').strip("'")
    return d


E = env()
API = E.get('PAYLOAD_API_URL', SITE).rstrip('/')


def req(path, data=None, tok=None, method=None):
    h = {'Content-Type': 'application/json'}
    if tok:
        h['Authorization'] = 'JWT ' + tok
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(API + path, data=body, headers=h,
                               method=method or ('POST' if data is not None else 'GET'))
    try:
        with urllib.request.urlopen(r, timeout=60) as resp:
            return resp.status, json.loads(resp.read().decode() or '{}')
    except urllib.error.HTTPError as e:
        return e.code, e.read().decode()[:500]


def login():
    s, d = req('/api/users/login', {'email': E['PAYLOAD_EMAIL'], 'password': E['PAYLOAD_PASSWORD']})
    return d['token']


class NoFollow(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *a, **k):
        return None


def sonda(path):
    op = urllib.request.build_opener(NoFollow)
    try:
        r = op.open(urllib.request.Request(SITE + path, method='HEAD'), timeout=30)
        return r.status, r.headers.get('Location')
    except urllib.error.HTTPError as e:
        return e.code, e.headers.get('Location')


def reg_ler():
    if os.path.exists(REG):
        return json.load(open(REG, encoding='utf-8'))
    return []


def reg_gravar(x):
    json.dump(x, open(REG, 'w', encoding='utf-8'), ensure_ascii=False, indent=1)


def post_por_slug(tok, slug):
    s, d = req('/api/posts?where[slug][equals]=%s&depth=0&limit=1&draft=false' % slug, tok=tok)
    docs = d.get('docs', []) if s == 200 else []
    return docs[0] if docs else None


def consolidar(tok, antigo, dono, motivo):
    """Consolidação SÓ entre posts do blog (24/11/2026, autorizado pelo Patrick):
    backup do post antigo -> despublica -> redirect 308 /blog/antigo -> /blog/dono -> confere.
    O redirect só pega com o post antigo despublicado (aprendido em 09/11). Se não pegar,
    apaga o redirect e republica o post: o site volta a ser o que era."""
    antigo, dono = antigo.strip('/').split('/')[-1], dono.strip('/').split('/')[-1]
    if antigo == dono:
        sys.exit('[X] antigo e dono são o mesmo post')
    de, para = '/blog/' + antigo, '/blog/' + dono
    if sonda(para)[0] != 200:
        sys.exit('[X] o dono %s não responde 200: nada feito' % para)
    post = post_por_slug(tok, antigo)
    if not post:
        sys.exit('[X] post %s não encontrado no Payload' % antigo)
    pasta = os.path.join(BASE, 'backups', 'consolidar_%s_post%s' % (
        datetime.datetime.now().strftime('%Y%m%d_%H%M'), post['id']))
    os.makedirs(pasta, exist_ok=True)
    json.dump(post, open(os.path.join(pasta, 'post.json'), 'w', encoding='utf-8'), ensure_ascii=False, indent=1)
    s, _ = req('/api/posts/%s' % post['id'], {'_status': 'draft'}, tok, method='PATCH')
    if s != 200:
        sys.exit('[X] não consegui despublicar o post %s (HTTP %s): nada feito' % (post['id'], s))
    s, d = req('/api/redirects', {'from': de, 'to': para, 'ativo': True}, tok)
    rid = d.get('doc', {}).get('id') if s in (200, 201) else None
    depois = (None, None)
    for _ in range(10):
        time.sleep(6)
        depois = sonda(de)
        if depois[0] in (301, 302, 307, 308):
            break
    ok = rid and depois[0] in (301, 308) and (depois[1] or '').rstrip('/').endswith(para)
    reg = reg_ler()
    reg.append({'id': rid, 'de': de, 'para': para, 'criado_em': datetime.date.today().isoformat(),
                'post_despublicado': post['id'], 'backup': pasta, 'motivo': motivo,
                'antes': 200, 'depois': depois[0], 'ok': bool(ok)})
    reg_gravar(reg)
    if ok:
        print('[OK] %s -> %s (308); post %s despublicado; backup em %s' % (de, para, post['id'], pasta))
        return
    print('[X] redirect não pegou (%s): desfazendo' % (depois,))
    if rid:
        req('/api/redirects/%s' % rid, tok=tok, method='DELETE')
    req('/api/posts/%s' % post['id'], {'_status': 'published'}, tok, method='PATCH')
    print('[i] post %s republicado; %s responde %s' % (post['id'], de, sonda(de)[0]))
    sys.exit(2)


def main():
    ap = argparse.ArgumentParser()
    sp = ap.add_subparsers(dest='cmd', required=True)
    c = sp.add_parser('criar'); c.add_argument('de'); c.add_argument('para'); c.add_argument('--motivo', default='')
    k = sp.add_parser('consolidar', help='só post do blog para post do blog')
    k.add_argument('antigo'); k.add_argument('dono'); k.add_argument('--motivo', default='')
    sp.add_parser('listar')
    a = sp.add_parser('apagar'); a.add_argument('id')
    args = ap.parse_args()
    tok = login()

    if args.cmd == 'consolidar':
        consolidar(tok, args.antigo, args.dono, args.motivo)
    elif args.cmd == 'listar':
        s, d = req('/api/redirects?limit=100&depth=0', tok=tok)
        for x in d.get('docs', []):
            print(x['id'], x['from'], '->', x['to'], 'ativo' if x.get('ativo') else 'inativo')
        print('total:', d.get('totalDocs'))
    elif args.cmd == 'apagar':
        s, d = req('/api/redirects/%s' % args.id, tok=tok, method='DELETE')
        print('apagar', args.id, '->', s)
        reg = reg_ler()
        for r in reg:
            if str(r.get('id')) == str(args.id):
                r['apagado_em'] = datetime.date.today().isoformat()
        reg_gravar(reg)
    else:
        antes = sonda(args.de)
        s, d = req('/api/redirects', {'from': args.de, 'to': args.para, 'ativo': True}, tok)
        print('criar', args.de, '->', args.para, ':', s)
        if s not in (200, 201):
            print(d); sys.exit(1)
        rid = d['doc']['id']
        depois = None
        for i in range(8):
            time.sleep(6)
            depois = sonda(args.de)
            if depois[0] in (301, 302, 307, 308):
                break
        ok = depois[0] in (301, 308) and (depois[1] or '').rstrip('/').endswith(args.para.rstrip('/'))
        print('antes:', antes, '| depois:', depois, '|', 'OK' if ok else 'NAO FUNCIONOU')
        reg = reg_ler()
        reg.append({'id': rid, 'de': args.de, 'para': args.para, 'criado_em': datetime.date.today().isoformat(),
                    'motivo': args.motivo, 'antes': antes[0], 'depois': depois[0], 'ok': ok})
        reg_gravar(reg)
        if not ok:
            print('Redirect nao pegou: apagando para nao deixar lixo.')
            req('/api/redirects/%s' % rid, tok=tok, method='DELETE')
            sys.exit(2)


if __name__ == '__main__':
    main()
