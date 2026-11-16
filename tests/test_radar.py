"""Testes offline: parsers dos sites (com HTML/JSON de amostra) e regras da nota.
Rodar: python -m pytest -q  (ou python tests/test_radar.py)"""
import sys
from pathlib import Path
from types import SimpleNamespace

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import yaml

from radar.coletores import gupy, linkedin, vagas_com
from radar.score import avaliar

PERFIL = yaml.safe_load((Path(__file__).resolve().parents[1] / "config/perfil.yaml").read_text())

LI_HTML = """<li><div class="base-card" data-entity-urn="urn:li:jobPosting:4012345678">
<a class="base-card__full-link" href="https://br.linkedin.com/jobs/view/faturista-4012345678?trk=x"></a>
<h3 class="base-search-card__title"> Faturista Hospitalar </h3>
<h4 class="base-search-card__subtitle"><a>Hospital X</a></h4>
<span class="job-search-card__location">Porto Alegre, RS</span>
<time datetime="2026-11-15">1 dia</time></div></li>"""

VC_HTML = """<ul><li class="vaga"><h2><a class="link-detalhes-vaga" title="Faturista" href="/vagas/v123/faturista">Faturista</a></h2>
<span class="emprVaga">Clínica Y</span><span class="nivelVaga">Pleno</span>
<div class="detalhes">Faturamento de convênios e glosas.</div>
<span class="vaga-local">Porto Alegre / RS</span><span class="data-publicacao">Hoje</span></li></ul>"""

GUPY_JSON = {"data": [{"name": "Analista de Faturamento", "careerPageName": "Hospital Z",
                       "city": "Porto Alegre", "state": "Rio Grande do Sul",
                       "jobUrl": "https://hz.gupy.io/jobs/1", "publishedDate": "2026-11-16T10:00:00.000Z",
                       "description": "<p>Contas de internação, <b>Tasy</b>, glosas</p>",
                       "isRemoteWork": False, "type": "vacancy_type_effective"}]}


def _fake(texto=None, js=None):
    return lambda *a, **k: SimpleNamespace(text=texto or "", json=lambda: js)


def test_linkedin(monkeypatch):
    monkeypatch.setattr(linkedin, "get", _fake(LI_HTML))
    v = linkedin.coletar("faturista", paginas=1, com_descricao=False)[0]
    assert v.titulo == "Faturista Hospitalar" and v.empresa == "Hospital X"
    assert v.url.endswith("4012345678") and v.publicada_em.startswith("2026-11-15")


def test_vagas_com(monkeypatch):
    monkeypatch.setattr(vagas_com, "get", _fake(VC_HTML))
    v = vagas_com.coletar("faturista")[0]
    assert v.empresa == "Clínica Y" and v.url.startswith("https://www.vagas.com.br/vagas/v123")
    assert v.publicada_em


def test_gupy(monkeypatch):
    monkeypatch.setattr(gupy, "get", _fake(js=GUPY_JSON))
    v = gupy.coletar("faturamento")[0]
    assert v.local == "Porto Alegre, Rio Grande do Sul" and "Tasy" in v.descricao and "<" not in v.descricao


def test_nota_ordem():
    base = dict(fonte="Gupy", empresa="X", url="", remoto=False, tipo="", termo_busca="", extra={},
                publicada_em="")
    boa = avaliar({**base, "titulo": "Faturista", "local": "Porto Alegre",
                   "descricao": "contas de internação, glosas, Tasy, OPME, honorários"}, PERFIL)
    ruim = avaliar({**base, "titulo": "Coordenador de Faturamento", "local": "Porto Alegre",
                    "descricao": "superior completo, liderança, enfermeiro"}, PERFIL)
    assert boa["nota"] > ruim["nota"] + 25
    assert avaliar({**base, "titulo": "Estágio em faturamento", "local": "", "descricao": ""}, PERFIL) is None


if __name__ == "__main__":
    import pytest
    sys.exit(pytest.main([__file__, "-q"]))
