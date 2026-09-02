# -*- coding: utf-8 -*-
"""Cruza o BACKLOG-EDITORIAL.md com o que existe de fato no Payload.

Regenera o backlog com uma coluna Status preenchida automaticamente e exporta
um CSV para colaboracao humana (Google Sheets). Ninguem marca nada a mao.

    python scripts/status_backlog.py            # atualiza o .md e gera o .csv
    python scripts/status_backlog.py --dry-run  # so mostra o placar, nao escreve
"""
import csv, json, os, re, sys, unicodedata, urllib.request, urllib.parse

BASE = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
PASTA = os.path.join(BASE, 'Pautas e Palavras Cahve')
MD = os.path.join(PASTA, 'BACKLOG-EDITORIAL.md')
CSV_OUT = os.path.join(PASTA, 'backlog.csv')

STOP = r'(?:de|do|da|dos|das|no|na|nos|nas|em|com|para|por|e|o|a|os|as|um|uma|que)'


def norm(s):
    s = unicodedata.normalize('NFD', (s or '').lower())
    s = ''.join(c for c in s if unicodedata.category(c) != 'Mn')
    s = s.replace('-', ' ').replace('/', ' ')
    s = re.sub(r'[^a-z0-9 ]', ' ', s)
    return re.sub(r'\s+', ' ', s).strip()


def env():
    d = {}
    with open(os.path.join(BASE, '.env'), encoding='utf-8-sig') as f:
        for line in f:
            line = line.strip()
            if line and not line.startswith('#') and '=' in line:
                k, v = line.split('=', 1)
                d[k.strip()] = v.strip().strip('"').strip("'")
    return d


def req(url, data=None, token=None):
    hdr = {'Content-Type': 'application/json'}
    if token:
        hdr['Authorization'] = 'JWT ' + token
    body = json.dumps(data).encode() if data is not None else None
    r = urllib.request.Request(url, data=body, headers=hdr,
                               method='POST' if data else 'GET')
    with urllib.request.urlopen(r, timeout=90) as resp:
        return json.loads(resp.read().decode())


def puxar_posts():
    e = env()
    api = e.get('PAYLOAD_API_URL', 'https://metakosmos.com.br').rstrip('/')
    tok = req(api + '/api/users/login',
              {'email': e['PAYLOAD_EMAIL'], 'password': e['PAYLOAD_PASSWORD']})['token']
    posts, page = [], 1
    while True:
        q = urllib.parse.urlencode({'limit': 100, 'page': page, 'depth': 0, 'draft': 'true'})
        d = req(api + '/api/posts?' + q, token=tok)
        posts.extend(d.get('docs', []))
        if not d.get('hasNextPage'):
            break
        page += 1
    return posts


def casa(kw, titulo, post):
    """Classifica a relacao entre a linha do backlog e um post existente.

    'forte' -> o post JA E este artigo (keyword abre o titulo do post, ou o slug bate).
    'fraca' -> a keyword aparece no post, mas ele e outro artigo: risco de canibalizacao.
    None    -> sem relacao.
    """
    alvo = norm(post.get('title'))
    slug = norm(post.get('slug'))
    k = norm(kw)
    if not k or not alvo:
        return None
    # FORTE: a keyword abre o titulo do post (com stopwords intercaladas permitidas)
    toks = k.split()
    sep = r'\s+(?:' + STOP + r'\s+)*'
    if re.match(r'^' + sep.join(map(re.escape, toks)) + r'\b', alvo):
        return 'forte'
    # FORTE: slug do post contem a keyword inteira (>= 3 tokens significativos)
    sig = [t for t in toks if len(t) > 2]
    if len(sig) >= 3 and ' '.join(toks) in slug:
        return 'forte'
    # FRACA: aparece no meio do titulo -> outro artigo ja ocupa o termo
    if k in alvo:
        return 'fraca'
    return None


LINHA = re.compile(r'^\|\s*(\d+)\s*\|([^|]*)\|([^|]*)\|([^|]*)\|(.*?)\|([^|]*)\|\s*`([^`]*)`\s*\|(.*)$')


def main():
    dry = '--dry-run' in sys.argv
    posts = puxar_posts()
    print('Posts no Payload: %d' % len(posts))

    linhas = open(MD, encoding='utf-8').read().split('\n')
    saida, csv_rows = [], []
    placar = {'publicado': 0, 'rascunho': 0, 'a fazer': 0, 'sobreposicao': 0}
    cab_feito = False

    for ln in linhas:
        m = LINHA.match(ln)
        if not m:
            # injeta a coluna Status no cabecalho da tabela do calendario.
            # Corta tudo depois de "| Funil |" antes de escrever: sem isso o
            # script ACRESCENTA um trio Status/Publicado/Slug a cada execucao,
            # e a tabela cresce 3 colunas por rodada (bug ate 02/09/2026).
            if not cab_feito and ln.startswith('| # | Data | Pilar | Origem |'):
                corte = ln.index('| Funil |') + len('| Funil |')
                saida.append(ln[:corte] + ' Status | Publicado em | Slug |')
                n_colunas = saida[-1].count('|') - 1
                cab_feito = True
                continue
            # separador reconstruido a partir da largura real do cabecalho
            if cab_feito and re.match(r'^\|[-\s|]+\|$', ln) and '---' in ln:
                saida.append('|' + '---|' * n_colunas)
                continue
            saida.append(ln)
            continue

        num, data, pilar, origem, titulo, car, kw, resto = m.groups()
        titulo_limpo = re.sub(r'<br>.*$', '', titulo).strip()

        achado, status, vizinho = None, 'a fazer', None
        for p in posts:
            rel = casa(kw, titulo_limpo, p)
            if rel == 'forte':
                achado = p
                status = 'publicado' if p.get('_status') == 'published' else 'rascunho'
                break
            if rel == 'fraca' and vizinho is None:
                vizinho = p
        if status == 'a fazer' and vizinho is not None:
            status = 'sobreposicao'
            achado = vizinho
        placar[status] += 1

        pub = (achado.get('publishedAt') or '')[:10] if achado else ''
        slug = achado.get('slug', '') if achado else ''
        marca = {'publicado': '✅ publicado', 'rascunho': '🟡 rascunho',
                 'a fazer': '⬜ a fazer',
                 'sobreposicao': '⚠️ termo já citado em outro post'}[status]
        # Reconstroi a linha a partir das 10 colunas de origem (ate Funil) e
        # descarta qualquer trio Status/Publicado/Slug de rodadas anteriores.
        # `resto` traz Vol | KD | Funil e, num arquivo ja poluido, os trios
        # antigos depois deles.
        campos = resto.split('|')
        vol, kd, funil = (campos + ['', '', ''])[:3]
        linha_base = '| %s |%s|%s|%s|%s|%s| `%s` |%s|%s|%s|' % (
            num, data, pilar, origem, titulo, car, kw, vol, kd, funil)
        saida.append(linha_base + ' %s | %s | %s |' % (marca, pub or '—', slug or '—'))

        csv_rows.append({
            'n': num.strip(), 'data_prevista': data.strip(), 'pilar': pilar.strip(),
            'origem': origem.strip(), 'titulo': titulo_limpo, 'keyword': kw.strip(),
            'status': status, 'publicado_em': pub, 'slug': slug,
            'responsavel': '', 'observacoes': '',
        })

    total = sum(placar.values())
    print('publicado: %d | rascunho: %d | sobreposicao: %d | a fazer: %d | total: %d'
          % (placar['publicado'], placar['rascunho'], placar['sobreposicao'],
             placar['a fazer'], total))
    print('  sobreposicao = a keyword ja aparece no titulo de outro post. Nao conta como feito:')
    print('  e aviso de canibalizacao, para decidir angulo diferente ou fundir os dois.')
    if total:
        print('progresso: %.1f%%' % (100.0 * placar['publicado'] / total))

    if dry:
        print('(--dry-run: nada foi escrito)')
        return

    with open(MD, 'w', encoding='utf-8') as f:
        f.write('\n'.join(saida))
    with open(CSV_OUT, 'w', encoding='utf-8-sig', newline='') as f:
        wr = csv.DictWriter(f, fieldnames=list(csv_rows[0].keys()))
        wr.writeheader()
        wr.writerows(csv_rows)
    print('atualizado ->', MD)
    print('exportado  ->', CSV_OUT)
    print('\nAs colunas "responsavel" e "observacoes" do CSV sao suas: o script nunca as sobrescreve')
    print('porque as regenera vazias. Se for usar no Sheets, mantenha o Sheets como copia de trabalho')
    print('e o .md como fonte de verdade do que escrever.')


if __name__ == '__main__':
    main()
