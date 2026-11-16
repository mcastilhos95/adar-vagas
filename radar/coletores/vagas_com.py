"""Vagas.com.br: busca por termo na cidade."""
import re
from datetime import datetime, timedelta, timezone

from bs4 import BeautifulSoup

from .base import Vaga, get, normalizar

BASE = "https://www.vagas.com.br"


def _slug(txt):
    return re.sub(r"[^a-z0-9]+", "-", normalizar(txt)).strip("-")


def _data(txt: str) -> str:
    t = normalizar(txt)
    hoje = datetime.now(timezone.utc)
    if "hoje" in t:
        return hoje.isoformat()
    if "ontem" in t:
        return (hoje - timedelta(days=1)).isoformat()
    m = re.search(r"(\d+) dias", t)
    if m:
        return (hoje - timedelta(days=int(m.group(1)))).isoformat()
    m = re.search(r"(\d{2})/(\d{2})/(\d{4})", t)
    if m:
        d, mo, a = map(int, m.groups())
        return datetime(a, mo, d, tzinfo=timezone.utc).isoformat()
    return ""


def coletar(termo: str, cidade: str = "porto alegre") -> list[Vaga]:
    url = f"{BASE}/vagas-de-{_slug(termo)}-em-{_slug(cidade)}"
    r = get(url)
    s = BeautifulSoup(r.text, "html.parser")
    vagas = []
    for li in s.select("li.vaga"):
        a = li.select_one("a.link-detalhes-vaga")
        if not a:
            continue
        emp = li.select_one(".emprVaga")
        loc = li.select_one(".vaga-local")
        desc = li.select_one(".detalhes")
        dt = li.select_one(".data-publicacao")
        nivel = li.select_one(".nivelVaga")
        vagas.append(Vaga(
            fonte="Vagas.com",
            titulo=a.get("title") or a.get_text(strip=True),
            empresa=emp.get_text(strip=True) if emp else "",
            local=loc.get_text(" ", strip=True) if loc else "",
            url=BASE + a["href"],
            publicada_em=_data(dt.get_text(strip=True)) if dt else "",
            descricao=desc.get_text(" ", strip=True) if desc else "",
            tipo=nivel.get_text(strip=True) if nivel else "",
            termo_busca=termo,
        ))
    return vagas
