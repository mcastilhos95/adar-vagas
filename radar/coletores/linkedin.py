"""LinkedIn: endpoint público de vagas (sem login). Pega até 50 vagas da última semana."""
import time
from datetime import datetime, timezone

from bs4 import BeautifulSoup

from .base import Vaga, get

LISTA = "https://www.linkedin.com/jobs-guest/jobs/api/seeMoreJobPostings/search"
DETALHE = "https://www.linkedin.com/jobs-guest/jobs/api/jobPosting/{id}"


def _descricao(job_id: str) -> str:
    try:
        r = get(DETALHE.format(id=job_id), tentativas=2)
        s = BeautifulSoup(r.text, "html.parser")
        d = s.select_one(".show-more-less-html__markup") or s.select_one(".description__text")
        return d.get_text(" ", strip=True) if d else ""
    except Exception:
        return ""


def coletar(termo: str, local: str = "Porto Alegre, Rio Grande do Sul, Brasil",
            paginas: int = 2, com_descricao: bool = True) -> list[Vaga]:
    vagas = []
    for p in range(paginas):
        r = get(LISTA, params={"keywords": termo, "location": local,
                               "f_TPR": "r604800", "start": p * 25})
        if not r or not r.text.strip():
            break
        s = BeautifulSoup(r.text, "html.parser")
        cards = s.select("li")
        if not cards:
            break
        for c in cards:
            t = c.select_one(".base-search-card__title")
            if not t:
                continue
            link = c.select_one("a.base-card__full-link") or c.select_one("a")
            url = (link["href"].split("?")[0] if link and link.has_attr("href") else "")
            urn = c.select_one("[data-entity-urn]")
            job_id = urn["data-entity-urn"].split(":")[-1] if urn else url.rstrip("/").split("-")[-1]
            quando = c.select_one("time")
            data = quando["datetime"] if quando and quando.has_attr("datetime") else ""
            if data:
                data = datetime.fromisoformat(data).replace(tzinfo=timezone.utc).isoformat()
            emp = c.select_one(".base-search-card__subtitle")
            loc = c.select_one(".job-search-card__location")
            v = Vaga(
                fonte="LinkedIn",
                titulo=t.get_text(strip=True),
                empresa=emp.get_text(strip=True) if emp else "",
                local=loc.get_text(strip=True) if loc else "",
                url=url,
                publicada_em=data,
                termo_busca=termo,
            )
            v.remoto = "remot" in v.local.lower()
            if com_descricao and job_id.isdigit():
                v.descricao = _descricao(job_id)
                time.sleep(0.8)
            vagas.append(v)
        time.sleep(1.5)
    return vagas
