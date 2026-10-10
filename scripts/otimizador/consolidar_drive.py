# -*- coding: utf-8 -*-
"""Consolida os decks de performance lidos do Drive (otimizador/dados/drive_decks/*.json).

Gera references/numeros-drive-interno.json: a lista de números de apresentações INTERNAS, usada pelo
auditor para avisar quando um artigo repete um número que ainda não foi aprovado para uso público.
Os valores em R$ (receita, investimento, fee) ficam marcados como 'sensivel' e nunca vão para o blog.

Uso:
    python scripts/otimizador/consolidar_drive.py
"""
import json
import re
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))
from payload_publish import SKILL_DIR  # noqa: E402

PASTA = SKILL_DIR / "otimizador" / "dados" / "drive_decks"
SAIDA = SKILL_DIR / "references" / "numeros-drive-interno.json"


def carregar():
    decks = []
    for arq in sorted(PASTA.glob("*.json")):
        d = json.loads(arq.read_text(encoding="utf-8"))
        d["_arquivo"] = arq.name
        decks.append(d)
    return decks


def relevante_para_auditor(valor):
    """Só números 'identificáveis' entram no aviso do auditor: com 4+ algarismos ou com decimal.
    '50%' ou '3x' seriam falsos positivos o tempo todo."""
    digitos = re.sub(r"\D", "", valor)
    return len(digitos) >= 4 or bool(re.search(r"\d,\d", valor))


def main():
    decks = carregar()
    numeros = []
    resumo = []
    for d in decks:
        mets = d.get("metricas", [])
        for m in mets:
            if relevante_para_auditor(m["valor"]):
                numeros.append({"valor": m["valor"], "cliente": d["cliente"], "produto": d.get("produto", ""),
                                "periodo": d.get("periodo", ""), "nome": m["nome"], "sensibilidade": m["sensibilidade"],
                                "deck_id": d["deck_id"]})
        resumo.append({"cliente": d["cliente"], "produto": d.get("produto", ""), "periodo": d.get("periodo", ""),
                       "status_deck": d.get("status_deck", ""), "deck_id": d["deck_id"], "titulo": d.get("titulo", ""),
                       "n_metricas": len(mets),
                       "n_sensiveis": sum(1 for m in mets if m["sensibilidade"] == "sensivel")})
    saida = {
        "_leia": ("Números extraídos de apresentações INTERNAS de performance (Google Drive da mK), em " + date.today().isoformat() +
                  ". NÃO são públicos: cada cliente precisa autorizar o uso, e valores em R$ (receita, investimento, fee) são 'sensivel' e nunca vão para o blog. "
                  "O auditor avisa quando um artigo repete um desses números. Para liberar um cliente, o Patrick registra a autorização e o número passa para references/numeros-oficiais.json com a fonte."),
        "decks": resumo,
        "numeros": numeros,
    }
    SAIDA.write_text(json.dumps(saida, ensure_ascii=False, indent=1), encoding="utf-8")
    print(f"[OK] {len(decks)} decks, {len(numeros)} números identificáveis ({sum(1 for n in numeros if n['sensibilidade'] == 'sensivel')} sensíveis) -> {SAIDA}")
    for r in resumo:
        print(f"  {r['cliente']:<18} {r['produto']:<12} {r['periodo']:<28} {r['n_metricas']:>3} métricas  ({r['status_deck'][:30]})")


if __name__ == "__main__":
    main()
