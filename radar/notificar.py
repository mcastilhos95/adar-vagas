"""Alertas por Telegram e/ou e-mail. Configure por variáveis de ambiente."""
import os
import smtplib
from email.mime.text import MIMEText

import requests


def _linha(v, aval):
    emoji = "🟢" if aval["nota"] >= 75 else "🟡" if aval["nota"] >= 60 else "🟠"
    alertas = f"\n   ⚠️ {'; '.join(aval['alertas'])}" if aval["alertas"] else ""
    return (f"{emoji} <b>{aval['nota']}</b> | {v['titulo']}\n"
            f"   {v['empresa']} | {v['local']} | {v['fonte']}{alertas}\n"
            f"   {v['url']}")


def montar_mensagem(itens, link_painel=""):
    topo = f"🔎 <b>Radar de Vagas</b>: {len(itens)} vaga(s) nova(s) compatível(is)\n\n"
    corpo = "\n\n".join(_linha(v, a) for v, a in itens[:15])
    rodape = f"\n\n📊 Painel completo: {link_painel}" if link_painel else ""
    return topo + corpo + rodape


def telegram(texto):
    token, chat = os.getenv("TELEGRAM_TOKEN"), os.getenv("TELEGRAM_CHAT_ID")
    if not (token and chat):
        return False
    for chat_id in chat.split(","):
        requests.post(f"https://api.telegram.org/bot{token}/sendMessage",
                      json={"chat_id": chat_id.strip(), "text": texto, "parse_mode": "HTML",
                            "disable_web_page_preview": True}, timeout=20).raise_for_status()
    return True


def email(texto):
    host, user, pwd, dest = (os.getenv(k) for k in ("SMTP_HOST", "SMTP_USER", "SMTP_PASS", "EMAIL_PARA"))
    if not all([host, user, pwd, dest]):
        return False
    html = texto.replace("\n", "<br>")
    msg = MIMEText(html, "html", "utf-8")
    msg["Subject"], msg["From"], msg["To"] = "Radar de Vagas: novas vagas", user, dest
    with smtplib.SMTP_SSL(host, int(os.getenv("SMTP_PORT", "465"))) as s:
        s.login(user, pwd)
        s.sendmail(user, dest.split(","), msg.as_string())
    return True
