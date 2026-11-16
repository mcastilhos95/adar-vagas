"""Gupy: API pública do portal de vagas (portal.gupy.io)."""
import re
import time
from html import unescape

from .base import Vaga, get

API = "https://portal.api.gupy.io/api/v1/jobs"


def _limpar_html(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html or ""))).strip()


def _buscar(termo, offset, estado):
    params = {"jobName": termo, "offset": offset, "limit": 50}
    if estado:
        params["state"] = estado
    try:
        return get(API, params=params).json()
    except Exception:
        if not estado:
            raise
        params.pop("state")          # se o filtro de estado não for aceito, busca sem ele
        return get(API, params=params).json()


def coletar(termo: str, paginas: int = 3, estado: str = "Rio Grande do Sul") -> list[Vaga]:
    vagas = []
    for p in range(paginas):
        js = _buscar(termo, p * 50, estado)
        dados = js.get("data") or js.get("results") or []
        for j in dados:
            cidade = j.get("city") or ""
            uf = j.get("state") or ""
            remoto = bool(j.get("isRemoteWork")) or (j.get("workplaceType") == "remote")
            vagas.append(Vaga(
                fonte="Gupy",
                titulo=(j.get("name") or "").strip(),
                empresa=(j.get("careerPageName") or "").strip(),
                local=", ".join(x for x in [cidade, uf] if x) or ("Remoto" if remoto else ""),
                url=j.get("jobUrl") or j.get("careerPageUrl") or "",
                publicada_em=j.get("publishedDate") or "",
                descricao=_limpar_html(j.get("description", "")),
                remoto=remoto,
                tipo=j.get("type", "") or "",
                termo_busca=termo,
                extra={"prazo": j.get("applicationDeadline"), "modelo": j.get("workplaceType")},
            ))
        if len(dados) < 50:
            break
        time.sleep(1)
    return vagas
