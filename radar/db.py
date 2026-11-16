"""Histórico em SQLite: guarda cada vaga uma vez, sabe o que é novo e o status dela."""
import json
import sqlite3
from pathlib import Path

from .coletores.base import agora_iso

ESQUEMA = """
CREATE TABLE IF NOT EXISTS vagas (
    id TEXT PRIMARY KEY,
    fonte TEXT, fontes TEXT, titulo TEXT, empresa TEXT, local TEXT, url TEXT,
    publicada_em TEXT, descricao TEXT, remoto INTEGER, tipo TEXT,
    nota INTEGER, avaliacao TEXT,
    primeira_vez TEXT, ultima_vez TEXT,
    notificada INTEGER DEFAULT 0,
    status TEXT DEFAULT 'nova'          -- nova, candidatou, descartada
);
CREATE TABLE IF NOT EXISTS execucoes (
    quando TEXT, fonte TEXT, termo TEXT, qtd INTEGER, erro TEXT
);
"""


class Banco:
    def __init__(self, caminho="dados/radar.db"):
        Path(caminho).parent.mkdir(parents=True, exist_ok=True)
        self.c = sqlite3.connect(caminho)
        self.c.row_factory = sqlite3.Row
        self.c.executescript(ESQUEMA)

    def log(self, fonte, termo, qtd, erro=""):
        self.c.execute("INSERT INTO execucoes VALUES (?,?,?,?,?)",
                       (agora_iso(), fonte, termo, qtd, erro))

    def salvar(self, v: dict, aval: dict) -> bool:
        """Grava a vaga. Retorna True se é nova."""
        agora = agora_iso()
        atual = self.c.execute("SELECT fontes, descricao FROM vagas WHERE id=?", (v["id"],)).fetchone()
        if atual:
            fontes = set(json.loads(atual["fontes"])) | {v["fonte"]}
            # fica com a descrição mais completa entre os sites
            desc = v["descricao"] if len(v["descricao"]) > len(atual["descricao"] or "") else atual["descricao"]
            self.c.execute(
                "UPDATE vagas SET fontes=?, ultima_vez=?, descricao=?, nota=MAX(nota, ?), "
                "avaliacao=CASE WHEN ? > nota THEN ? ELSE avaliacao END WHERE id=?",
                (json.dumps(sorted(fontes)), agora, desc, aval["nota"],
                 aval["nota"], json.dumps(aval, ensure_ascii=False), v["id"]))
            return False
        self.c.execute(
            "INSERT INTO vagas (id, fonte, fontes, titulo, empresa, local, url, publicada_em, "
            "descricao, remoto, tipo, nota, avaliacao, primeira_vez, ultima_vez) "
            "VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)",
            (v["id"], v["fonte"], json.dumps([v["fonte"]]), v["titulo"], v["empresa"],
             v["local"], v["url"], v["publicada_em"], v["descricao"], int(v["remoto"]),
             v["tipo"], aval["nota"], json.dumps(aval, ensure_ascii=False), agora, agora))
        return True

    def pendentes_alerta(self, nota_min):
        return [dict(r) for r in self.c.execute(
            "SELECT * FROM vagas WHERE notificada=0 AND nota>=? ORDER BY nota DESC", (nota_min,))]

    def marcar_notificadas(self, ids):
        self.c.executemany("UPDATE vagas SET notificada=1 WHERE id=?", [(i,) for i in ids])

    def todas(self, dias=45):
        return [dict(r) for r in self.c.execute(
            "SELECT * FROM vagas WHERE ultima_vez >= datetime('now', ?) ORDER BY nota DESC",
            (f"-{dias} days",))]

    def resumo_execucoes(self, n=60):
        return [dict(r) for r in self.c.execute(
            "SELECT * FROM execucoes ORDER BY quando DESC LIMIT ?", (n,))]

    def commit(self):
        self.c.commit()
