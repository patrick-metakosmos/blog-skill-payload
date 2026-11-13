# Concorrentes que podem ser citados pelo nome

Decisão do Patrick em 09/11/2026:

1. Só pode ser citado quem está **muito abaixo da mK** no ranking de presença nas respostas das IAs (GEO_Plus, rodada de 08/11/2026). Nunca os que estão acima ou logo abaixo.
   (a) **Moda:** regra ajustada pelo Patrick em 13/11/2026: **presença de até 5% (cerca de um quarto da mK, que tem 19%)**. Ficam de fora Sizebay, Genlook, Provou Levou, Provou, Doris, Abcielli e Provei (7% a 33%). A regra original de 09/11 era 10 posições abaixo da mK.
   (b) **Beleza:** regra ajustada pelo Patrick em 13/11/2026. Em beleza o ranking é um degrau (depois do trio Perfect Corp, ModiFace e Banuba, quase todos ficam entre 2% e 4%), então vale a distância em percentual: **presença de até 5% (um quinto da mK, que tem 25%)**, fora do trio acima e de qualquer produto dele (TINT é da Banuba). Fornecedor de cliente da mK (PulpoAR, do Simple) também não entra.
2. Mesmo esses **só podem aparecer em artigos comparativos**, do tipo "Melhores provadores virtuais de roupa" ou "Melhores provadores virtuais de maquiagem". Em qualquer outro artigo, nenhum concorrente é citado.

O auditor (`scripts/audit_artigo.py`) aplica as duas regras: um nome desta lista só passa se o H1 do artigo for comparativo (contém "melhores", "comparativo", "comparação" ou "alternativas"). Fora disso, reprova. Nomes de `references/concorrentes.md` que não estão aqui seguem proibidos em qualquer artigo.

Formato: uma linha por nome, `- Nome | segmento | observação`. O auditor lê só o que vem antes do primeiro `|`.

## Como a posição foi medida

Ranking "quem aparece" por segmento, rodada GEO de 08/11/2026 (planilha "Concorrentes · Mega Brain", aba GEO do Mega Brain). A mK está em **3º em moda (19%)** e **4º em beleza (25%)**. Entra quem tem até 5% de presença, em moda e em beleza (ver regra 1). A medição é de presença nas IAs; não mede autoridade de domínio nem posição no Google. Reavaliar a cada rodada: se a mK cair no ranking ou o concorrente subir, ele sai da lista.

## Permitidos (verificados no site oficial em 13/11/2026)

- Mirage AI | moda | mirageai.com.br: provador virtual para e-commerce, "Feito no Brasil", plug-in para Shopify, VTEX, WooCommerce e Nuvemshop; vestuário, calçado, óculos e maquiagem. 3% de presença, fora do top 15 de moda.
- Meu Vestir | moda | meuvestir.com.br: "Provador Virtual para Lojas de Moda". Só o título da página foi lido; conferir o resto do site ao escrever. 3% de presença.
- AnyTry | moda | anytry.app: provador de roupa com IA (foto de corpo inteiro + peça). ATENÇÃO: não é de maquiagem, como constava antes; movido de beleza para moda em 13/11/2026. 2% de presença.
- VTON (Splus Innovation) | moda | app "Provador Virtual" na loja de aplicativos da Nuvemshop, prova de roupa na página do produto. 1% de presença.
- Clostech | moda | app "Provador virtual com IA" na loja de aplicativos da Nuvemshop: prova de roupa na foto do cliente e recomendação de tamanho, para lojas de roupa. Ativo em out/2026. Preço em dólar no listing (não citar). 5% de presença.
- FASHN | moda | fashn.ai: IA para e-commerce de moda (imagens de produto, modelos de IA, provador virtual, vídeos), B2B, site em inglês, sem cliente brasileiro citado. 4% de presença.
- Pixellabs | beleza | pixellabs.com.br: provador virtual B2B de maquiagem (Makeup Mirror), também roupa e cabelo, versão em português. 0% de presença.
- GlamAR | beleza | glamar.io: provador virtual de maquiagem (lábios, olhos, rosto) com busca de tom, SaaS B2B para marcas e varejo, site em inglês. 3% de presença.
- Revieve | beleza | revieve.com: conselho de maquiagem com IA, prova em AR e Foundation Finder, B2B para marcas e varejistas, site em inglês. 4% de presença.
- Arbelle | beleza | arbelle.ai: prova de maquiagem em AR e busca de base e corretivo, B2B, parte da Visage Technologies, site em inglês. 4% de presença.
- Orbo AI | beleza | orbo.ai: maquiagem virtual, busca de base e ferramentas de cabelo, para marcas, varejo e salões, com app para consumidor; site em inglês. 3% de presença.

## Em espera (NÃO citar; fora do formato da lista de propósito, o auditor não os libera)

| Nome | segmento | motivo |
|---|---|---|
| Dressy | moda | site fora do ar na verificação de 13/11 (dressy.ai vazio, dressy.com.br com erro 503). Voltar a conferir. |
| Yarvia | beleza | yarvia.app diz "launching soon" (pré-lançamento, fundada em 2026 pela VEAUTHY); não há produto no ar nem prova de que seja brasileiro. Reavaliar quando lançar. |
| Performa.AI | moda | provador é 1 de 10 ferramentas de uma plataforma de performance; só serve se o artigo falar de plataforma, não de provador. |
| Mira Estúdio | moda | é inteligência de mercado para moda; o provador está em prévia, limitado a 3 clientes em 2026. Reavaliar se virar produto aberto. |
| Veesual | moda | o site agora é de vídeo curto a partir de imagem de produto, sem provador. |
| Fits.me, Photta | moda | sites não abrem na verificação de 13/11. |
| Imediata, Mizui, Pryzmo | moda | as IAs erraram: Imediata é ERP, Mizui é plataforma de cupom e CRM, Pryzmo não tem site. Não são provadores. |
| Shade Studio (Cart Lab), MaIA/B4A, ARRASEI, Vitraun, MaqAI, Maisonlip, Outwow | beleza | sem site localizável na verificação de 13/11. Resolvido em 13/11 com o critério de até 5% (beleza fecha com 5 nomes). |

## Regras para citar

1. **Conferir no site oficial da empresa, na hora de escrever.** As descrições acima vêm do que as IAs disseram e não foram verificadas. Se não achar o site, ou se a empresa parecer inativa, não citar.
2. Só afirmar o que está no site da empresa. Sem preço, número de cliente ou resultado que não esteja lá, e sem julgamento negativo sobre a empresa.
3. Sem link para o site do concorrente (regra antiga mantida).
4. O artigo comparativo precisa incluir a mK com critério claro de comparação (recurso, integração, prazo, tipo de resultado), e não só uma lista de nomes.
5. Sizebay, Genlook, Provou, Provou Levou, Abcielli, Provei, Doris, Banuba, Perfect Corp, ModiFace e demais marcas acima ou logo abaixo da mK **não entram**.
