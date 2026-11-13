# Concorrentes que podem ser citados pelo nome

Decisão do Patrick em 09/11/2026:

1. Só pode ser citado quem está **pelo menos 10 posições abaixo da mK** no ranking de presença nas respostas das IAs (GEO_Plus, rodada de 08/11/2026). Nunca os que estão acima ou logo abaixo.
2. Mesmo esses **só podem aparecer em artigos comparativos**, do tipo "Melhores provadores virtuais de roupa" ou "Melhores provadores virtuais de maquiagem". Em qualquer outro artigo, nenhum concorrente é citado.

O auditor (`scripts/audit_artigo.py`) aplica as duas regras: um nome desta lista só passa se o H1 do artigo for comparativo (contém "melhores", "comparativo", "comparação" ou "alternativas"). Fora disso, reprova. Nomes de `references/concorrentes.md` que não estão aqui seguem proibidos em qualquer artigo.

Formato: uma linha por nome, `- Nome | segmento | observação`. O auditor lê só o que vem antes do primeiro `|`.

## Como a posição foi medida

Ranking "quem aparece" por segmento, rodada GEO de 08/11/2026 (planilha "Concorrentes · Mega Brain", aba GEO do Mega Brain). A mK está em **3º em moda (19%)** e **4º em beleza (25%)**. Entra quem está na 13ª posição ou abaixo em moda, ou na 14ª ou abaixo em beleza. A medição é de presença nas IAs; não mede autoridade de domínio nem posição no Google. Reavaliar a cada rodada: se a mK cair no ranking ou o concorrente subir, ele sai da lista.

## Permitidos (verificados no site oficial em 13/11/2026)

- Mirage AI | moda | mirageai.com.br: provador virtual para e-commerce, "Feito no Brasil", plug-in para Shopify, VTEX, WooCommerce e Nuvemshop; vestuário, calçado, óculos e maquiagem. 3% de presença, fora do top 15 de moda.
- Meu Vestir | moda | meuvestir.com.br: "Provador Virtual para Lojas de Moda". Só o título da página foi lido; conferir o resto do site ao escrever. 3% de presença.
- AnyTry | moda | anytry.app: provador de roupa com IA (foto de corpo inteiro + peça). ATENÇÃO: não é de maquiagem, como constava antes; movido de beleza para moda em 13/11/2026. 2% de presença.
- VTON (Splus Innovation) | moda | app "Provador Virtual" na loja de aplicativos da Nuvemshop, prova de roupa na página do produto. 1% de presença.
- Pixellabs | beleza | pixellabs.com.br: provador virtual B2B de maquiagem (Makeup Mirror), também roupa e cabelo, versão em português. 0% de presença.

## Em espera (NÃO citar; fora do formato da lista de propósito, o auditor não os libera)

| Nome | segmento | motivo |
|---|---|---|
| Dressy | moda | site fora do ar na verificação de 13/11 (dressy.ai vazio, dressy.com.br com erro 503). Voltar a conferir. |
| Yarvia | beleza | yarvia.app diz "launching soon" (pré-lançamento, fundada em 2026 pela VEAUTHY); não há produto no ar nem prova de que seja brasileiro. Reavaliar quando lançar. |
| Performa.AI | moda | provador é 1 de 10 ferramentas de uma plataforma de performance; só serve se o artigo falar de plataforma, não de provador. |
| Imediata, Mizui, Pryzmo | moda | as IAs erraram: Imediata é ERP, Mizui é plataforma de cupom e CRM, Pryzmo não tem site. Não são provadores. |
| Shade Studio (Cart Lab), MaIA/B4A, ARRASEI, Vitraun, MaqAI, Maisonlip, Outwow | beleza | sem site localizável na verificação de 13/11. Faltam nomes de beleza: hoje só 1 verificado. |

## Regras para citar

1. **Conferir no site oficial da empresa, na hora de escrever.** As descrições acima vêm do que as IAs disseram e não foram verificadas. Se não achar o site, ou se a empresa parecer inativa, não citar.
2. Só afirmar o que está no site da empresa. Sem preço, número de cliente ou resultado que não esteja lá, e sem julgamento negativo sobre a empresa.
3. Sem link para o site do concorrente (regra antiga mantida).
4. O artigo comparativo precisa incluir a mK com critério claro de comparação (recurso, integração, prazo, tipo de resultado), e não só uma lista de nomes.
5. Sizebay, Genlook, Provou, Provou Levou, Abcielli, Provei, Doris, Banuba, Perfect Corp, ModiFace e demais marcas acima ou logo abaixo da mK **não entram**.
