# -*- coding: utf-8 -*-
"""Registra nas planilhas uma otimização já aplicada (fecha a etapa 1.1.2.6).

Lê otimizador/trabalho/<slug>/aplicado.json (gravado pelo aplicar.py) e
feito.md (resumo do que foi feito, escrito junto com a otimização), e:
- Log: Data da otimização, O que foi feito, Backup (com o comando de reverter);
- Inventário: Última atualização, Total de otimizações, Última otimização, Status.

Uso:
    python scripts/otimizador/registrar.py <slug> <ciclo>
"""
import json
import sys
from datetime import datetime

from google_api import SKILL_DIR
from planilhas import Planilhas

SITE = "https://metakosmos.com.br/blog/"


def main():
    slug, ciclo = sys.argv[1], sys.argv[2]
    pasta = SKILL_DIR / "otimizador" / "trabalho" / slug
    aplicado = json.loads((pasta / "aplicado.json").read_text(encoding="utf-8"))
    feito = (pasta / "feito.md").read_text(encoding="utf-8").strip()
    quando = datetime.fromisoformat(aplicado["quando"]).date().isoformat()
    pid = json.loads((pasta / "seo.json").read_text(encoding="utf-8"))["id"]
    url = SITE + slug

    plan = Planilhas()
    ok_log = plan.atualizar_log(url, ciclo, {
        "Data da otimização": quando,
        "O que foi feito": feito,
        "Backup (para reverter)": f"python scripts/restore_post.py {aplicado['backup']} {pid}",
    })
    feitas = [l for l in plan.ler_log() if l["URL do artigo"] == url and l.get("O que foi feito", "").strip()
              and l.get("Balde") != "Controle"]
    ok_inv = plan.atualizar_inventario(url, {
        "Última atualização": quando,
        "Total de otimizações": len(feitas),
        "Última otimização": quando,
        "Status": "Em observação (otimizado há < 28 dias)",
    })
    if not (ok_log and ok_inv):
        raise SystemExit(f"[X] linha não encontrada: Log={ok_log} Inventário={ok_inv}")
    print(f"[OK] {slug} registrado no Log ({ciclo}) e no Inventário")


if __name__ == "__main__":
    main()
