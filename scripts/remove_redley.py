# -*- coding: utf-8 -*-
"""Remove mencoes a Redley do BLOG (colecao posts).

Escopo: SO a colecao `posts`. Nao toca em `mkases`, nem em `media`, nem nos
arquivos de referencia locais.

    python scripts/remove_redley.py --dry-run        # mostra o que mudaria
    python scripts/remove_redley.py --only <slug>    # aplica em 1 post
    python scripts/remove_redley.py --all            # aplica em todos
"""
import json, os, re, sys, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LINK_REDLEY = '/mkases/redley'

OREAL = "L'Oréal"

# por slug: subs = [(texto exato do no, novo texto)], drop_heading = blocos a remover
REGRAS = {
 'provador-virtual-ia-generativa-ecommerce': {'subs': [
    ('Marcas como a ', 'Marcas de moda'),
    (', Coca-Cola, UFC, Ambev, Redley, Osklen, Grendene e TV Globo.',
     ', Coca-Cola, UFC, Ambev, Osklen, Grendene e TV Globo.')]},

 'videos-publicitarios-com-ia-guia-completo-para-marcas': {'subs': [
    (' e a ', ''),
    (", entre elas GM, " + OREAL + ", Natura, Avon, Decathlon, Flexform, Coca-Cola, Redley, Osklen e ",
     ", entre elas GM, " + OREAL + ", Natura, Avon, Decathlon, Flexform, Coca-Cola, Osklen e ")]},

 'ai-shooting-moda-ia': {'subs': [(' e a ', '')]},

 'marketing-imersivo-varejo-moda': {'subs': [
    (' na ', ' em uma marca de moda'),
    ('Redley (Grupo S2):', 'Marca de moda:'),
    (' (Redley), ', ' em moda, '),
    (': Gregory (mK Fashion+ em todos os lançamentos), Redley (+56% de conversão), '
     'Fuel Eyewear (26 modelos com RA) e Osklen (Shop The Look). No total, ',
     ': Gregory (mK Fashion+ em todos os lançamentos), '
     'Fuel Eyewear (26 modelos com RA) e Osklen (Shop The Look). No total, ')]},

 'videos-fooh-ia-generativa-viralizar-campanhas': {'subs': [
    (" a dar os primeiros passos em soluções imersivas, entre elas GM, " + OREAL
     + ", Natura, Coca-Cola, UFC, ",
     " a dar os primeiros passos em soluções imersivas, entre elas GM, " + OREAL
     + ", Natura, Coca-Cola, UFC")]},

 'provador-virtual-ecommerce-guia-completo': {
    'drop_heading': ['mKase: Redley (Grupo S2)'],
    'subs': [
    (' com mais de 200 plataformas integradas e clientes como Boca Rosa, Bio Extratus, Redley, '
     'Gregory, Oscar Calçados e Osklen.',
     ' com mais de 200 plataformas integradas e clientes como Boca Rosa, Bio Extratus, '
     'Gregory, Oscar Calçados e Osklen.'),
    (' registrou ', ''),
    ('+56% de conversão', ''),
    (', a ', ''),
    (' na Redley após integração do mK Fashion+.',
     ' em moda após integração do mK Fashion+.'),
    ('No caso da Redley, o dashboard mostrou ', 'O dashboard de um cliente de moda mostrou '),
    ('Redley, Gregory, Osklen e Oscar Calçados', 'Gregory, Osklen e Oscar Calçados'),
    (' (Redley), ', ', '),
    ('Redley, Gregory, Osklen, Oscar Calçados', 'Gregory, Osklen, Oscar Calçados')]},

 'provador-virtual-e-realidade-aumentada-o-futuro-do-varejo': {'subs_parciais': [
    ('Coca-Cola, UFC, Redley, Osklen,', 'Coca-Cola, UFC, Osklen,')]},

 'visualizador-3d-realidade-aumentada': {'subs': [
    (" como GM, " + OREAL + ", Avon, Boca Rosa, Redley, Osklen, Grendene, Flexform e Decathlon.",
     " como GM, " + OREAL + ", Avon, Boca Rosa, Osklen, Grendene, Flexform e Decathlon."),
    (' e a ', '')]},

 'videos-ia-campanhas-publicitarias': {'subs': [(' e a ', '')]},

 'videos-com-ia-nova-fronteira-storytelling-marcas': {'subs_parciais': [
    ('Avon, Redley, Osklen,', 'Avon, Osklen,')]},

 'implementacao-visualizador-3d-ecommerce': {'subs': [
    (', Coca-Cola, Redley e TV Globo.', ', Coca-Cola e TV Globo.')]},

 'realidade-aumentada-no-e-commerce': {'subs': [
    (" a dar os primeiros passos em soluções imersivas, entre elas GM, " + OREAL
     + ", Natura, Avon, ",
     " a dar os primeiros passos em soluções imersivas, entre elas GM, " + OREAL
     + ", Natura, Avon")]},
}


def env():
    d = {}
    for line in open(os.path.join(BASE, '.env'), encoding='utf-8-sig'):
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            k, v = line.split('=', 1)
            d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def req(url, data=None, token=None, method=None):
    hdr = {'Content-Type': 'application/json'}
    if token:
        hdr['Authorization'] = 'JWT ' + token
    body = json.dumps(data).encode() if data is not None else None
    m = method or ('POST' if data else 'GET')
    r = urllib.request.Request(url, data=body, headers=hdr, method=m)
    with urllib.request.urlopen(r, timeout=120) as resp:
        return resp.status, json.loads(resp.read().decode())


def texto(n):
    if n.get('type') == 'text':
        return n.get('text', '')
    return ''.join(texto(c) for c in n.get('children') or [])


def limpa(node, regras, stats):
    """Descarta links de Redley e aplica as substituicoes, recursivamente."""
    filhos = node.get('children')
    if not filhos:
        return
    novos = []
    for c in filhos:
        if c.get('type') == 'link' and LINK_REDLEY in ((c.get('fields') or {}).get('url') or ''):
            stats['links'] += 1
            continue
        novos.append(c)
    node['children'] = novos
    for c in novos:
        if c.get('type') == 'text':
            # 1) substituicao do no inteiro (segura: so casa se o no for exatamente aquilo)
            for velho, novo in regras.get('subs', []):
                if c['text'] == velho:
                    c['text'] = novo
                    stats['subs'] += 1
                    break
            # 2) substituicao de trecho, quando a mencao esta no meio de um no maior
            for velho, novo in regras.get('subs_parciais', []):
                if velho in c['text']:
                    c['text'] = c['text'].replace(velho, novo)
                    stats['subs'] += 1
        limpa(c, regras, stats)


def processa(doc, regras, stats):
    root = doc['content']['root']
    fora = set(regras.get('drop_heading') or [])
    if fora:
        filhos, pular = [], False
        for n in root['children']:
            if n.get('type') == 'heading' and texto(n).strip() in fora:
                pular = True
                stats['blocos'] += 1
                continue
            if pular:
                pular = False
                if n.get('type') == 'paragraph':   # corpo do mKase, logo abaixo do H3
                    stats['blocos'] += 1
                    continue
            filhos.append(n)
        root['children'] = filhos
    limpa(root, regras, stats)
    return doc


def main():
    dry = '--dry-run' in sys.argv
    only = sys.argv[sys.argv.index('--only') + 1] if '--only' in sys.argv else None
    if not dry and not only and '--all' not in sys.argv:
        print('use --dry-run, --only <slug> ou --all')
        sys.exit(1)

    e = env()
    api = e['PAYLOAD_API_URL'].rstrip('/')
    tok = req(api + '/api/users/login',
              {'email': e['PAYLOAD_EMAIL'], 'password': e['PAYLOAD_PASSWORD']})[1]['token']

    for slug, regras in REGRAS.items():
        if only and slug != only:
            continue
        q = urllib.parse.urlencode({'where[slug][equals]': slug, 'depth': 0,
                                    'draft': 'true', 'limit': 1})
        doc = req(api + '/api/posts?' + q, token=tok)[1]['docs'][0]
        stats = {'links': 0, 'subs': 0, 'blocos': 0}
        processa(doc, regras, stats)
        restam = len(re.findall(r'redley', json.dumps(doc['content'], ensure_ascii=False), re.I))
        print('%-56s links:%d subs:%d blocos:%d | restam:%d %s'
              % (slug, stats['links'], stats['subs'], stats['blocos'], restam,
                 'OK' if restam == 0 else '<<< AINDA TEM'))
        if dry:
            continue
        draft_q = '' if doc['_status'] == 'published' else '&draft=true'
        code, _ = req(api + '/api/posts/%s?locale=pt-BR%s' % (doc['id'], draft_q),
                      {'content': doc['content'], '_status': doc['_status']},
                      token=tok, method='PATCH')
        print('   -> PATCH id=%s (%s) HTTP %s' % (doc['id'], doc['_status'], code))


if __name__ == '__main__':
    main()
