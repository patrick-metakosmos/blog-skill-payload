Rode o ciclo quinzenal do Otimizador do blog mK de ponta a ponta, sozinho, sem me perguntar nada. Não há ninguém no terminal: esta execução vem da tarefa agendada "Blog mK - otimizador quinzenal". Siga o processo 1.1.2 e a skill blog-mk-payload (modo Reescrever). O Patrick já autorizou o ciclo automático: os artigos vão AO VIVO, com backup, auditoria e relatório.

Pasta de trabalho: a raiz da skill (blog mK Payload). O Mega Brain fica na pasta irmã Mega_Brain (só leitura).

Passo 0. A trava do ciclo JÁ foi pega pelo script que te chamou (estado "running"): NÃO rode `ciclo_guarda.py --check` de novo, ele diria que está rodando (é você). Descubra o ciclo com `python scripts/otimizador/ciclo_guarda.py --show` (ex.: 2026-S47; é a semana ISO de hoje). No fim, feche com `--finish`.

Passo 1. Medir o ciclo anterior (regra do ritual: primeiro medir, depois otimizar). `python scripts/otimizador/medir.py`. Se sair com código 3 (login do GSC expirado), siga assim mesmo e registre no relatório. Guarde o resultado: ele entra no relatório e decide o que fazer mais.

Passo 2. Coleta, nesta ordem: `python scripts/otimizador/inventario.py`, `python scripts/otimizador/coleta_gsc.py`, `python scripts/otimizador/coleta_ga4.py`. Depois `python scripts/otimizador/baldes.py` (grava a seleção por baldes do ciclo e o Log).

Este ciclo é SOMENTE de SEO (posição, impressões e cliques no Google). Não otimize nada para IA/GEO nem para YouTube (definição para citação, tabelas comparativas para IA, presença em fontes de terceiros): GEO tem rodada própria. Se vir algo de GEO, ignore.

Passo 3. Briefing com TODOS os dados do Mega Brain: `python scripts/otimizador/briefing_megabrain.py` (puxa o retrato do dia do Mega Brain: Top 3 SEO com as 50 keywords, plano aprovado, mKases, recomendações, o que já deu resultado). Leia o `.md` que ele grava em `otimizador/ciclos/<ciclo>-megabrain.md` por inteiro. Escolha os artigos na ordem do ranking, no máximo 25 (teto ampliado em 24/11/2026), pulando:
- os artigos da seção "Grupo de comparação: NÃO MEXER": o briefing já os gravou no Log como Balde "Controle". Nunca otimize, nunca use como reserva, nunca insira link neles neste ciclo. Eles medem quanto do ganho é da reescrita.
- artigo cuja ação aprovada é consolidar com 301 em OUTRO POST DO BLOG: faça você mesmo, no Passo 4b (abaixo).
- artigo cuja ação é 301 para página de produto ou mexer em página de produto: tarefa do TIME (/mkfashion, /mkbeauty, /mk3d, /mklabs). Liste no relatório, com o motivo.
- artigo que a auditoria bloquear duas vezes: pule e use a reserva.
Se o briefing sair com poucos artigos, trabalhe só com o que há. Artigo bom vale mais do que teto cumprido por obrigação.

Passo 4. Para não estourar o seu contexto com 25 reescritas, rode CADA artigo num subagente (ferramenta Agent), um de cada vez, na ordem: passe a ele o slug, o id, o bloco do artigo no briefing e as etapas a) a g) abaixo; espere o resultado, confira que `registrar.py` rodou e só então passe ao próximo. O PRIMEIRO artigo (o teste) você faz no contexto principal. Etapas de cada artigo:
 a) `python scripts/otimizador/artigo_html.py <id>` (exporta o texto que está NO AR).
 b) `python scripts/otimizador/aplicar.py <slug> --comparar` (prova de ida e volta). Se falhar, pule o artigo.
 c) Reescreva `otimizador/trabalho/<slug>/artigo.html` e `seo.json` seguindo o padrão aprovado: reescrita COMPLETA nas regras da skill (modelo: `otimizador/trabalho/fooh-guia-completo-fake-out-of-home-viral/`). Pisos duros: 2000+ palavras de corpo, FAQ com 10+ perguntas, zero em dash, keyword exata abrindo o H1, citação do State of Immersive & Agentic Commerce 2026 conferida na linha de origem. Use o briefing: as keywords que o artigo serve (a keyword do Top 3 vai no title, no H1 ou no primeiro H2 conforme o plano), as buscas reais do Search Console, as ações aprovadas do plano, e os links internos sugeridos. Não disputar com a página dona da keyword: link para ela com a âncora exata. Preço só como "a partir de", conforme `Base-de-numeros-e-precos-do-blog.md`. Número sem fonte NÃO fica: remova e liste cada um em `feito.md` ("removido: ..."). Nenhuma imagem pode ser logo de marca. O estudo só é linkado por https://metakosmos.com.br/estudo.
 d) Escreva `otimizador/trabalho/<slug>/feito.md` (3 a 6 linhas: o que mudou, quais keywords/ações do plano foram atendidas, o que foi removido e por quê).
 e) `python scripts/audit_artigo.py otimizador/trabalho/<slug>/artigo.html` e só siga com ZERO falhas bloqueadoras. Corrija e rode de novo (até 2 vezes).
 f) `python scripts/otimizador/aplicar.py <slug> --dry-run`, confira o diff, depois `python scripts/otimizador/aplicar.py <slug>` (AO VIVO, com backup automático). Ele confere que o post continua publicado e responde 200. Se a página não responder 200, restaure na hora com `python scripts/restore_post.py` (o comando está em `aplicado.json`) e pule o artigo.
 g) `python scripts/otimizador/registrar.py <slug> <ciclo>`.
Passo 4b. Consolidações 301 ENTRE POSTS DO BLOG que o briefing aponte como ação aprovada (ex.: "id 9 vira 301 para id 12"): primeiro garanta que o post dono já recebeu o conteúdo exclusivo do antigo (se não, faça isso na reescrita do dono). Depois `python scripts/otimizador/redirect_payload.py consolidar <slug-antigo> <slug-dono> --motivo "<ação do plano>"`. O script faz backup, despublica o antigo, cria o redirect, confere o 308 e desfaz sozinho se não pegar. Nunca use para página de produto, case ou LP. No máximo 5 consolidações por ciclo; liste cada uma no resumo.

O PRIMEIRO artigo do ciclo é o teste: depois de aplicado, abra a URL pública (curl) e confira que o título, o H1 e o primeiro parágrafo são os novos. Só depois siga com os demais. Se o primeiro falhar em qualquer etapa, PARE o ciclo inteiro e feche como failed.

Passo 5. Fechamento (obrigatório, mesmo se algo falhar no caminho).
 - `python scripts/otimizador/painel.py` e `python scripts/otimizador/relatorio_ciclo.py` (geram o painel e o relatório visual; se falharem, siga).
 - Escreva `otimizador/ciclos/<ciclo>-resumo.md` com: resultado da medição do ciclo anterior (por artigo, qual melhorou/piorou), artigos otimizados (slug, balde, keywords atendidas), artigos pulados e por quê, números removidos por falta de fonte, consolidações 301 feitas (de, para), o grupo de comparação do ciclo, tarefas do TIME que o briefing apontou (redirects para páginas de produto, páginas de produto) e as keywords do CEO que ainda não aparecem no Google (candidatas a pauta nova do blog).
 - deu certo: `python scripts/otimizador/ciclo_guarda.py --finish done --nota "<N artigos: slugs>"`
 - não deu: `python scripts/otimizador/ciclo_guarda.py --finish failed --nota "<motivo em uma linha>"`
 - O Mega Brain lê o Log do otimizador na coleta das 07:40 do dia seguinte e o analista das 08:00 avisa no #only-marketing. Não poste no Slack daqui.

Regras que valem por cima de tudo:
- Nunca altere página de produto, case ou site: só posts do blog (`/blog/...`). Redirect só de post do blog para post do blog, pelo `redirect_payload.py consolidar`.
- Nunca rode alteração em mais de um artigo sem o anterior ter passado por aplicar + registrar.
- Se qualquer comando for recusado por falta de permissão, PARE na hora e feche a trava com `--finish failed --nota "sem permissao para executar comandos"`, dizendo isso na primeira linha da resposta.

Ao terminar, imprima o ciclo, os slugs otimizados, os pulados, o caminho do resumo e o resultado da auditoria de cada um.
