import hashlib
import re
import time
import unicodedata
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone

import requests

HEADERS = {
    "User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                   "(KHTML, like Gecko) Chrome/124.0 Safari/537.36"),
    "Accept-Language": "pt-BR,pt;q=0.9",
}


def normalizar(txt: str) -> str:
    txt = unicodedata.normalize("NFKD", txt or "")
    txt = "".join(c for c in txt if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", txt.lower()).strip()


@dataclass
class Vaga:
    fonte: str
    titulo: str
    empresa: str
    local: str
    url: str
    publicada_em: str = ""          # ISO 8601
    descricao: str = ""
    remoto: bool = False
    tipo: str = ""                  # CLT, PJ, efetivo...
    termo_busca: str = ""
    extra: dict = field(default_factory=dict)

    @property
    def id(self) -> str:
        # Mesma vaga em sites diferentes vira um id só (titulo + empresa)
        chave = normalizar(f"{self.titulo}|{self.empresa}")
        return hashlib.sha1(chave.encode()).hexdigest()[:16]

    def to_dict(self):
        d = asdict(self)
        d["id"] = self.id
        return d


def get(url, params=None, tentativas=3, pausa=2.0, **kw):
    for i in range(tentativas):
        try:
            r = requests.get(url, params=params, headers=HEADERS, timeout=25, **kw)
            if r.status_code == 429:
                time.sleep(pausa * (i + 2))
                continue
            r.raise_for_status()
            return r
        except requests.RequestException:
            if i == tentativas - 1:
                raise
            time.sleep(pausa * (i + 1))
    return None


def agora_iso():
    return datetime.now(timezone.utc).isoformat()
