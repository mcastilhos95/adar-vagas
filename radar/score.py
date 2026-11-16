"""Nota de compatibilidade (0 a 100) entre a vaga e o perfil, mais radar de competências."""
import re
from datetime import datetime, timezone
from functools import lru_cache

from .coletores.base import normalizar


@lru_cache(maxsize=4096)
def _rx(termo: str):
    return re.compile(r"(?<![a-z0-9])" + re.escape(termo) + r"(?![a-z0-9])")


def _tem(texto: str, termo: str) -> bool:
    return bool(_rx(normalizar(termo)).search(texto))


def _uniq(termos):
    vistos, out = set(), []
    for t in termos:
        n = normalizar(t)
        if n not in vistos:
            vistos.add(n)
            out.append(n)
    return out


def _dias(iso: str):
    if not iso:
        return None
    try:
        d = datetime.fromisoformat(iso.replace("Z", "+00:00"))
        if d.tzinfo is None:
            d = d.replace(tzinfo=timezone.utc)
        return max(0, (datetime.now(timezone.utc) - d).days)
    except ValueError:
        return None


def _nota_recencia(dias):
    if dias is None:
        return 50
    for limite, nota in [(1, 100), (3, 85), (7, 65), (15, 40), (30, 20)]:
        if dias <= limite:
            return nota
    return 5


def _nota_local(vaga, perfil):
    loc = normalizar(vaga.get("local", ""))
    cfg = perfil["locais"]
    if vaga.get("remoto") and cfg.get("remoto_ok"):
        return 90, "Remoto"
    if any(_tem(loc, c) for c in cfg["ideal"]):
        return 100, "Porto Alegre"
    if any(_tem(loc, c) for c in cfg["aceito"]):
        return 75, "Região metropolitana"
    if not loc:
        return 50, "Local não informado"
    if "rs" in loc.split() or "rio grande do sul" in loc:
        return 30, "Outra cidade do RS"
    return 0, "Fora do RS"


def avaliar(vaga: dict, perfil: dict) -> dict | None:
    titulo = normalizar(vaga.get("titulo", ""))
    texto = normalizar(f"{vaga.get('titulo', '')} {vaga.get('descricao', '')}")

    if any(_tem(titulo, t) for t in perfil.get("ignorar_titulo", [])):
        return None

    # 1) Título
    alvo = any(_tem(titulo, t) for t in perfil["titulos"]["alvo"])
    sec = any(_tem(titulo, t) for t in perfil["titulos"]["secundario"])
    if alvo:
        n_titulo, trilha = 100, "Faturamento"
    elif sec:
        n_titulo, trilha = 45, "Administrativo/RH"
    elif any(_tem(texto, t) for t in perfil["titulos"]["alvo"]):
        n_titulo, trilha = 35, "Faturamento (na descrição)"
    else:
        n_titulo, trilha = 0, "Fora do foco"

    # 2) Competências e radar
    radar, pedidos_total, atendidos_total, ajuste = [], 0, 0, []
    fortes, lacunas = [], []
    for nome, d in perfil["dimensoes"].items():
        termos = _uniq(d["termos"])
        tem = set(_uniq(d["tem"]))
        pedidos = [t for t in termos if _tem(texto, t)]
        atendidos = [t for t in pedidos if t in tem]
        faltam = [t for t in pedidos if t not in tem]
        demanda = 0 if not pedidos else min(5, 1 + len(pedidos))
        radar.append({"dimensao": nome, "vaga": demanda, "deisi": d["nivel"]})
        pedidos_total += len(pedidos)
        atendidos_total += len(atendidos)
        if demanda:
            ajuste.append(min(1.0, d["nivel"] / demanda))
        fortes += atendidos
        lacunas += faltam

    if pedidos_total:
        cobertura = atendidos_total / pedidos_total
        n_comp = 100 * (0.7 * cobertura + 0.3 * (sum(ajuste) / len(ajuste)))
        # pouca evidência na descrição: puxa a nota para o meio
        conf = min(1.0, pedidos_total / 4)
        n_comp = conf * n_comp + (1 - conf) * 55
    else:
        cobertura, n_comp = None, 45  # vaga sem descrição: neutro

    # 3) Local e 4) recência
    n_local, local_txt = _nota_local(vaga, perfil)
    dias = _dias(vaga.get("publicada_em", ""))
    n_rec = _nota_recencia(dias)

    p = perfil["pesos"]
    nota = (n_titulo * p["titulo"] + n_comp * p["competencias"]
            + n_local * p["local"] + n_rec * p["recencia"]) / 100

    bonus = []
    # benefício "plano de saúde" não conta; olha título, empresa e descrição
    txt_saude = normalizar(f"{vaga.get('empresa', '')} {texto}").replace("plano de saude", "")
    saude = any(_tem(txt_saude, t) for t in perfil.get("contexto_saude", []))
    if trilha == "Faturamento" and not saude:
        trilha = "Faturamento (fora da saúde)"
        nota -= 12
        alertas_ctx = ["Faturamento comercial/fiscal, não hospitalar"]
    else:
        alertas_ctx = []
    alertas = list(alertas_ctx)
    for a in perfil.get("alertas", []):
        alvo_txt = titulo if a.get("so_titulo") else texto
        if any(_tem(alvo_txt, t) for t in a["termos"]):
            nota -= a["peso"]
            alertas.append(a["aviso"])
    for b in perfil.get("bonus", []):
        if any(_tem(texto, t) for t in b["termos"]):
            nota += b["peso"]
            bonus.append(b["motivo"])

    # Tetos: o foco é faturamento hospitalar, o resto nunca passa na frente
    tetos = {"Fora do foco": 40, "Faturamento (na descrição)": 58,
             "Administrativo/RH": 74 if saude else 64, "Faturamento (fora da saúde)": 70}
    if trilha == "Administrativo/RH" and saude:
        bonus.append("Administrativo na área da saúde")
    if trilha in tetos:
        nota = min(nota, tetos[trilha])
    nota = round(max(0, min(100, nota)))

    faixa = ("Excelente" if nota >= 75 else "Boa" if nota >= 60
             else "Possível" if nota >= 45 else "Baixa")

    return {
        "nota": nota,
        "faixa": faixa,
        "trilha": trilha,
        "componentes": {"titulo": round(n_titulo), "competencias": round(n_comp),
                        "local": n_local, "recencia": n_rec},
        "cobertura": None if cobertura is None else round(100 * cobertura),
        "local_tipo": local_txt,
        "dias": dias,
        "radar": radar,
        "fortes": sorted(set(fortes)),
        "lacunas": sorted(set(lacunas)),
        "alertas": alertas,
        "bonus": bonus,
    }
