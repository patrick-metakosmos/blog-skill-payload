# -*- coding: utf-8 -*-
"""Leitura e escrita das duas planilhas do processo 1.1.2 (Drive da mK,
pasta "Otimizador do Blog"). O robô é editor das duas.

- Inventário de Artigos: reescrito inteiro a cada ciclo (é foto do momento).
- Log de Otimizações: só recebe linhas novas ou completa os campos "depois";
  nunca apaga o que já está lá (é o histórico, e pode ter anotação manual).
"""
import urllib.parse

from google_api import checar, sessao

API = "https://sheets.googleapis.com/v4/spreadsheets"
ABA_INVENTARIO = "Inventário"
ABA_LOG = "Log"

COLUNAS_LOG = [
    "URL do artigo", "Data da otimização", "Ciclo", "Balde",
    "Posição média (antes)", "Cliques (antes)", "CTR (antes)", "Impressões (antes)",
    "Diagnóstico", "O que foi feito",
    "Posição média (depois)", "Cliques (depois)", "CTR (depois)", "Impressões (depois)",
    "Resultado", "Próximo passo", "Aprendizado", "Backup (para reverter)",
]


class Planilhas:
    def __init__(self):
        self.s, env = sessao()
        self.id_inv = env["SHEET_INVENTARIO"]
        self.id_log = env["SHEET_LOG"]
        self.aba_inv = self._garantir_aba(self.id_inv, ABA_INVENTARIO)
        self.aba_log = self._garantir_aba(self.id_log, ABA_LOG)

    def _garantir_aba(self, planilha, nome):
        """A planilha nasceu de um CSV, com a aba 'Untitled'; renomeia uma vez."""
        meta = checar(self.s.get(f"{API}/{planilha}?fields=sheets.properties"), "sheets meta")
        aba = meta["sheets"][0]["properties"]
        if aba["title"] != nome:
            corpo = {"requests": [{"updateSheetProperties": {
                "properties": {"sheetId": aba["sheetId"], "title": nome}, "fields": "title"}}]}
            checar(self.s.post(f"{API}/{planilha}:batchUpdate", json=corpo), "renomear aba")
        return aba["sheetId"]

    def _formatar(self, planilha, aba_id, colunas, nomes_pct):
        """Congela o cabeçalho e põe as colunas de CTR em percentual."""
        reqs = [{"updateSheetProperties": {"properties": {"sheetId": aba_id, "gridProperties": {"frozenRowCount": 1}},
                                           "fields": "gridProperties.frozenRowCount"}}]
        for nome in nomes_pct:
            i = colunas.index(nome)
            reqs.append({"repeatCell": {
                "range": {"sheetId": aba_id, "startRowIndex": 1, "startColumnIndex": i, "endColumnIndex": i + 1},
                "cell": {"userEnteredFormat": {"numberFormat": {"type": "PERCENT", "pattern": "0.0%"}}},
                "fields": "userEnteredFormat.numberFormat"}})
        checar(self.s.post(f"{API}/{planilha}:batchUpdate", json={"requests": reqs}), "formatar")

    def _ler(self, planilha, aba):
        intervalo = urllib.parse.quote(f"'{aba}'!A1:Z", safe="")
        valores = checar(self.s.get(f"{API}/{planilha}/values/{intervalo}"), f"ler {aba}").get("values", [])
        if not valores:
            return [], []
        cab = valores[0]
        return cab, [dict(zip(cab, linha + [""] * (len(cab) - len(linha)))) for linha in valores[1:]]

    def ler_log(self):
        return self._ler(self.id_log, ABA_LOG)[1]

    def escrever_inventario(self, colunas, linhas):
        intervalo = urllib.parse.quote(f"'{ABA_INVENTARIO}'!A1:Z", safe="")
        checar(self.s.post(f"{API}/{self.id_inv}/values/{intervalo}:clear", json={}), "limpar inventário")
        corpo = {"values": [colunas] + [[l.get(c, "") for c in colunas] for l in linhas]}
        checar(self.s.put(f"{API}/{self.id_inv}/values/{urllib.parse.quote(ABA_INVENTARIO + '!A1', safe='')}"
                          "?valueInputOption=RAW", json=corpo), "escrever inventário")
        self._formatar(self.id_inv, self.aba_inv, colunas, ["CTR atual"])

    def remover_pendentes(self, ciclo):
        """Re-rodar a seleção de um ciclo substitui as linhas dele que ainda não
        foram executadas ('O que foi feito' vazio). Linha executada nunca sai."""
        _, linhas = self._ler(self.id_log, ABA_LOG)
        alvos = [i for i, l in enumerate(linhas, start=1)
                 if l["Ciclo"] == ciclo and not l.get("O que foi feito", "").strip()]
        if not alvos:
            return 0
        reqs = [{"deleteDimension": {"range": {"sheetId": self.aba_log, "dimension": "ROWS",
                                               "startIndex": i, "endIndex": i + 1}}}
                for i in sorted(alvos, reverse=True)]
        checar(self.s.post(f"{API}/{self.id_log}:batchUpdate", json={"requests": reqs}), "remover pendentes")
        return len(alvos)

    def anexar_log(self, linhas):
        """Anexa linhas novas, pulando (URL, Ciclo) que já existam: rodar o mesmo
        ciclo duas vezes não duplica o registro."""
        existentes = {(l["URL do artigo"], l["Ciclo"]) for l in self.ler_log()}
        novas = [l for l in linhas if (l["URL do artigo"], l["Ciclo"]) not in existentes]
        if not novas:
            return 0
        corpo = {"values": [[l.get(c, "") for c in COLUNAS_LOG] for l in novas]}
        intervalo = urllib.parse.quote(f"'{ABA_LOG}'!A1", safe="")
        checar(self.s.post(f"{API}/{self.id_log}/values/{intervalo}:append"
                           "?valueInputOption=RAW&insertDataOption=INSERT_ROWS", json=corpo),
               "anexar log")
        self._formatar(self.id_log, self.aba_log, COLUNAS_LOG, ["CTR (antes)", "CTR (depois)"])
        return len(novas)

    def atualizar_inventario(self, url, campos):
        """Atualiza campos da linha do artigo no Inventário (localizada pela URL)."""
        return self._atualizar_linha(self.id_inv, ABA_INVENTARIO, campos,
                                     lambda l: l.get("Slug/URL") == url)

    def _atualizar_linha(self, planilha, aba, campos, achar):
        cab, linhas = self._ler(planilha, aba)
        for i, l in enumerate(linhas, start=2):
            if achar(l):
                dados = [{"range": f"'{aba}'!{chr(ord('A') + cab.index(nome))}{i}", "values": [[valor]]}
                         for nome, valor in campos.items()]
                checar(self.s.post(f"{API}/{planilha}/values:batchUpdate",
                                   json={"valueInputOption": "RAW", "data": dados}), f"atualizar {aba}")
                return True
        return False

    def atualizar_log(self, url, ciclo, campos):
        """Preenche campos de uma linha do Log (ex.: 'O que foi feito', os 'depois')."""
        return self._atualizar_linha(self.id_log, ABA_LOG, campos,
                                     lambda l: l["URL do artigo"] == url and l["Ciclo"] == ciclo)
