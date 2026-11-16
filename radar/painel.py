"""Gera o painel HTML (arquivo único) a partir do banco."""
import json
from datetime import datetime, timezone
from pathlib import Path

TEMPLATE = Path(__file__).with_name("painel_template.html")


def gerar(vagas_db: list[dict], nome: str, destino="site/index.html"):
    vagas = []
    for v in vagas_db:
        av = json.loads(v["avaliacao"])
        vagas.append({
            "id": v["id"], "titulo": v["titulo"], "empresa": v["empresa"], "local": v["local"],
            "url": v["url"], "fontes": json.loads(v["fontes"]), "descricao": (v["descricao"] or "")[:3000],
            "primeira_vez": v["primeira_vez"], "av": av,
        })
    dados = {"gerado_em": datetime.now(timezone.utc).isoformat(), "vagas": vagas}
    html = (TEMPLATE.read_text(encoding="utf-8")
            .replace("__NOME__", nome.split()[0])
            .replace("__DADOS__", json.dumps(dados, ensure_ascii=False).replace("</", "<\\/")))
    Path(destino).parent.mkdir(parents=True, exist_ok=True)
    Path(destino).write_text(html, encoding="utf-8")
    return destino
