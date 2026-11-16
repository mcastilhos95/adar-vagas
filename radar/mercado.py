"""Análise do que as vagas estão pedindo, comparado com o que a Deisi tem."""
import json
import re
import statistics
from collections import Counter

from .coletores.base import normalizar
from .score import _tem

STOP = set("""a o as os um uma uns umas de da do das dos em na no nas nos para por com sem
e ou que se ao aos à às sua seu suas seus ser ter como mais muito bem nao não sim
area área vaga vagas empresa empresas trabalho atuar atuacao atuação atividades atividade
experiencia experiência conhecimento conhecimentos desejavel desejável requisitos requisito
responsabilidades beneficios benefícios local horario horário segunda sexta feira das
voce você nossa nosso nossos nossas time equipe junte buscamos procuramos oportunidade
anos ano sobre todos todas cada entre ate até pelo pela pelos pelas este esta isso
informacoes informações adicionais qualificacoes qualificações mil colaboradores fazer faca
faça parte pessoas somos busca profissional profissionais porto alegre assistencia assistência
medica médica odontologica odontológica faixa salarial atuacoes atuações anteriores podem indicar
afinidade ensino medio médio completo completa funcao função funcoes funções considerados tambem
também serao serão local candidatos candidato candidata venha estamos grande nosso crescimento
vale refeicao refeição alimentacao alimentação transporte plano saude saúde odontologico
odontológico seguro vida auxilio auxílio gympass wellhub dia dias salario salário
""".split())


def _nivel_termo(perfil):
    """termo normalizado -> 'tem' ou 'nocoes' conforme o perfil."""
    out = {}
    for d in perfil["dimensoes"].values():
        status = "nocoes" if d["nivel"] <= 2 else "tem"
        for t in d["tem"]:
            out[normalizar(t)] = status
    return out


def _status(termo_norm, niveis):
    """Tem se o termo é igual a algo do currículo ou contém (ex.: 'atendimento ao cliente')."""
    if termo_norm in niveis:
        return niveis[termo_norm]
    for t, st in niveis.items():
        if _tem(termo_norm, t):
            return st
    return "nao"


def _uniq_norm(lista):
    """Junta 'recepcao' e 'recepção' num termo só e mostra a forma com acento."""
    melhor = {}
    for t in lista:
        n = normalizar(t)
        if n not in melhor or (t != n and melhor[n] == n):
            melhor[n] = t
    return [(t, n) for n, t in melhor.items()]


def _contar(textos, termos):
    c = Counter()
    for orig, n in _uniq_norm(termos):
        c[orig] = sum(1 for t in textos if _tem(t, n))
    return c


def _contar_grupos(textos, grupos):
    return {nome: sum(1 for t in textos if any(_tem(t, x) for x in ts)) for nome, ts in grupos.items()}


def analisar(vagas_db: list[dict], perfil: dict) -> dict:
    vagas = []
    for v in vagas_db:
        av = json.loads(v["avaliacao"])
        foco = av["trilha"].startswith("Faturamento") or (
            av["trilha"] == "Administrativo/RH" and "Administrativo na área da saúde" in av["bonus"])
        vagas.append({**v, "av": av, "foco": foco,
                      "txt": normalizar(f"{v['titulo']} {v['descricao'] or ''}")})

    foco = [v for v in vagas if v["foco"] and len(v["txt"]) > 80]
    base = foco if len(foco) >= 5 else [v for v in vagas if len(v["txt"]) > 80]
    textos = [v["txt"] for v in base]
    n = max(1, len(textos))
    niveis = _nivel_termo(perfil)
    m = perfil["mercado"]

    # Conhecimentos: o mesmo conceito com e sem acento conta uma vez
    conhec = []
    vistos = set()
    for orig, nn in _uniq_norm(m["conhecimentos"]):
        if nn in vistos:
            continue
        vistos.add(nn)
        qtd = sum(1 for t in textos if _tem(t, nn))
        if qtd:
            conhec.append({"termo": orig, "qtd": qtd, "pct": round(100 * qtd / n),
                           "status": _status(nn, niveis)})
    conhec.sort(key=lambda x: -x["qtd"])

    sistemas = []
    for orig, nn in _uniq_norm(m["sistemas"]):
        qtd = sum(1 for t in textos if _tem(t, nn))
        if qtd:
            sistemas.append({"termo": orig, "qtd": qtd, "pct": round(100 * qtd / n),
                             "status": _status(nn, niveis)})
    sistemas.sort(key=lambda x: -x["qtd"])

    # Experiência pedida: "2 anos de experiência", "experiência em X"
    anos = Counter()
    frases = Counter()
    for t in textos:
        for a in re.findall(r"(\d{1,2})\s*(?:\(\w+\)\s*)?anos? de experiencia", t):
            anos[f"{a} ano(s)"] += 1
        for f in re.findall(r"experiencia (?:previa |comprovada |anterior )?(?:na|no|em|com) "
                            r"((?:[a-z]+ ){0,4}[a-z]+)", t):
            ws = []
            for w in f.split()[:3]:
                if w in STOP:
                    break
                ws.append(w)
            if ws and len(" ".join(ws)) > 4:
                frases[" ".join(ws)] += 1

    # Salário citado no texto
    sal = []
    for v in base:
        for s in re.findall(r"r\$\s?(\d{1,2}\.?\d{3})(?:,\d{2})?", v["txt"]):
            val = float(s.replace(".", ""))
            if 1200 <= val <= 15000:
                sal.append(val)
    salario = ({"qtd": len(sal), "min": min(sal), "mediana": statistics.median(sal), "max": max(sal)}
               if sal else None)

    # Termos frequentes que o dicionário não conhece (descoberta automática)
    conhecidos = {nn for _, nn in _uniq_norm(m["conhecimentos"] + m["sistemas"])}
    for d in perfil["dimensoes"].values():
        conhecidos |= {normalizar(x) for x in d["termos"]}
    bigr = Counter()
    for t in textos:
        pal = [p for p in re.findall(r"[a-z]{3,}", t)]
        vistos_doc = set()
        for i in range(len(pal) - 1):
            a, b = pal[i], pal[i + 1]
            if a in STOP or b in STOP:
                continue
            g = f"{a} {b}"
            if g not in vistos_doc and not any(k in g or g in k for k in conhecidos):
                vistos_doc.add(g)
                bigr[g] += 1
    descobertos = [{"termo": g, "qtd": q} for g, q in bigr.most_common(40) if q >= 2][:18]

    empresas = Counter(v["empresa"] for v in base if v["empresa"]).most_common(10)

    falta = [c for c in conhec + sistemas if c["status"] == "nao"][:10]
    nocoes = [c for c in conhec + sistemas if c["status"] == "nocoes"][:8]
    fortes = [c for c in conhec + sistemas if c["status"] == "tem"][:10]

    return {
        "total_vagas": len(vagas), "base": len(base),
        "base_descricao": "vagas de faturamento e administrativo na saúde" if base is foco
                          else "todas as vagas com descrição (poucas vagas do foco ainda)",
        "conhecimentos": conhec[:25], "sistemas": sistemas[:12],
        "escolaridade": _contar_grupos(textos, m["escolaridade"]),
        "jornada": _contar_grupos(textos, m["jornada"]),
        "regime": _contar_grupos(textos, m["regime"]),
        "anos": anos.most_common(6), "frases_experiencia": frases.most_common(10),
        "salario": salario, "descobertos": descobertos, "empresas": empresas,
        "falta": falta, "nocoes": nocoes, "fortes": fortes,
    }
