"""Radar de Vagas: coleta, dá nota, guarda, avisa e gera o painel.

Uso:
  python main.py                 # rodada completa
  python main.py --sem-alerta    # coleta e painel, sem mandar mensagem
  python main.py --demo          # usa vagas de exemplo (sem internet), para testar
"""
import argparse
import json
import os
import sys
from pathlib import Path

import yaml

from radar import notificar, painel
from radar.coletores import gupy, linkedin, vagas_com
from radar.coletores.base import Vaga
from radar.db import Banco
from radar.score import avaliar

RAIZ = Path(__file__).parent


def coletar_tudo(perfil, banco, rapido=False):
    termos = perfil["buscas"]["principais"] + ([] if rapido else perfil["buscas"]["secundarias"])
    fontes = {
        "Gupy": lambda t: gupy.coletar(t),
        "LinkedIn": lambda t: linkedin.coletar(t, paginas=1 if rapido else 2),
        "Vagas.com": lambda t: vagas_com.coletar(t),
    }
    for nome, fn in fontes.items():
        for termo in termos:
            try:
                achadas = fn(termo)
                banco.log(nome, termo, len(achadas))
                print(f"  {nome:10} {termo:35} {len(achadas):3} vagas")
                yield from achadas
            except Exception as e:  # um site fora do ar não derruba os outros
                banco.log(nome, termo, 0, str(e)[:200])
                print(f"  {nome:10} {termo:35} ERRO: {e}", file=sys.stderr)


def vagas_demo():
    for d in json.loads((RAIZ / "exemplo" / "vagas_exemplo.json").read_text(encoding="utf-8")):
        yield Vaga(**d)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--demo", action="store_true")
    ap.add_argument("--sem-alerta", action="store_true")
    ap.add_argument("--rapido", action="store_true", help="só termos principais")
    ap.add_argument("--db", default=str(RAIZ / "dados" / "radar.db"))
    ap.add_argument("--saida", default=str(RAIZ / "site" / "index.html"))
    a = ap.parse_args()

    perfil = yaml.safe_load((RAIZ / "config" / "perfil.yaml").read_text(encoding="utf-8"))
    banco = Banco(a.db)
    fonte = vagas_demo() if a.demo else coletar_tudo(perfil, banco, a.rapido)

    novas, total, ignoradas = [], 0, 0
    for vaga in fonte:
        aval = avaliar(vaga.to_dict(), perfil)
        if aval is None:
            ignoradas += 1
            continue
        total += 1
        if banco.salvar(vaga.to_dict(), aval):
            novas.append((vaga.to_dict(), aval))
    banco.commit()
    print(f"\n{total} vagas avaliadas, {len(novas)} novas, {ignoradas} ignoradas pelo título")

    destino = painel.gerar(banco.todas(), perfil["nome"], a.saida)
    print(f"Painel: {destino}")

    if not a.sem_alerta:
        pend = banco.pendentes_alerta(perfil["nota_minima_alerta"])
        if pend:
            itens = [(v, json.loads(v["avaliacao"])) for v in pend]
            msg = notificar.montar_mensagem(itens, os.getenv("LINK_PAINEL", ""))
            enviado = False
            for canal in (notificar.telegram, notificar.email):
                try:
                    enviado |= canal(msg)
                except Exception as e:
                    print(f"Falha no alerta {canal.__name__}: {e}", file=sys.stderr)
            if enviado:
                banco.marcar_notificadas([v["id"] for v in pend])
                banco.commit()
                print(f"Alerta enviado com {len(pend)} vaga(s)")
            else:
                print("Nenhum canal de alerta configurado (veja README)")


if __name__ == "__main__":
    main()
