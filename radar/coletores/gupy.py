"""Gupy: API pública do portal de vagas (portal.gupy.io)."""
import re
from html import unescape

from .base import Vaga, get

API = "https://portal.api.gupy.io/api/job"


def _limpar_html(html: str) -> str:
    return re.sub(r"\s+", " ", unescape(re.sub(r"<[^>]+>", " ", html or ""))).strip()


def coletar(termo: str, limite: int = 100) -> list[Vaga]:
    r = get(API, params={"name": termo, "offset": 0, "limit": limite})
    dados = r.json().get("data", []) if r else []
    vagas = []
    for j in dados:
        cidade = j.get("city") or ""
        estado = j.get("state") or ""
        remoto = bool(j.get("isRemoteWork")) or (j.get("workplaceType") == "remote")
        vagas.append(Vaga(
            fonte="Gupy",
            titulo=j.get("name", "").strip(),
            empresa=(j.get("careerPageName") or "").strip(),
            local=", ".join(p for p in [cidade, estado] if p) or ("Remoto" if remoto else ""),
            url=j.get("jobUrl") or j.get("careerPageUrl") or "",
            publicada_em=j.get("publishedDate") or "",
            descricao=_limpar_html(j.get("description", "")),
            remoto=remoto,
            tipo=j.get("type", "") or "",
            termo_busca=termo,
            extra={"prazo": j.get("applicationDeadline"),
                   "modelo": j.get("workplaceType"),
                   "pcd": j.get("disabilities")},
        ))
    return vagas
