"""Estado do bot salvo em arquivos dentro do próprio repositório.

O GitHub Actions não guarda nada entre execuções, então o bot salva aqui os posts
pendentes de aprovação, o histórico de receitas e os horários já ocupados, e o
workflow faz commit dessas mudanças.
"""
import json
import os
import time
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

RAIZ = os.path.join(os.path.dirname(__file__), "..")
PASTA = os.path.join(RAIZ, "estado")
PENDENTES = os.path.join(PASTA, "pendentes")
HISTORICO = os.path.join(PASTA, "historico.json")
IDEIAS = os.path.join(RAIZ, "ideias.txt")
FUSO = ZoneInfo("America/Sao_Paulo")


def carregar_historico() -> dict:
    if os.path.exists(HISTORICO):
        with open(HISTORICO, encoding="utf-8") as f:
            hist = json.load(f)
    else:
        hist = {}
    hist.setdefault("titulos", [])
    hist.setdefault("ideias_usadas", [])
    hist.setdefault("agendados", [])
    hist.setdefault("telegram_offset", 0)
    return hist


def salvar_historico(hist: dict) -> None:
    os.makedirs(PASTA, exist_ok=True)
    hist["titulos"] = hist["titulos"][-300:]
    with open(HISTORICO, "w", encoding="utf-8") as f:
        json.dump(hist, f, ensure_ascii=False, indent=2)


def proxima_ideia(hist: dict) -> str | None:
    """Próxima linha do ideias.txt que ainda não foi usada (ou None)."""
    if not os.path.exists(IDEIAS):
        return None
    with open(IDEIAS, encoding="utf-8") as f:
        for linha in f:
            ideia = linha.strip()
            if ideia and not ideia.startswith("#") and ideia not in hist["ideias_usadas"]:
                return ideia
    return None


def salvar_pendente(post: dict, imagem: bytes) -> None:
    os.makedirs(PENDENTES, exist_ok=True)
    with open(os.path.join(PENDENTES, f"{post['id']}.json"), "w", encoding="utf-8") as f:
        json.dump(post, f, ensure_ascii=False, indent=2)
    with open(os.path.join(PENDENTES, f"{post['id']}.jpg"), "wb") as f:
        f.write(imagem)


def carregar_pendente(post_id: str) -> tuple[dict, bytes] | None:
    base = os.path.join(PENDENTES, post_id)
    if not os.path.exists(base + ".json"):
        return None
    with open(base + ".json", encoding="utf-8") as f:
        post = json.load(f)
    with open(base + ".jpg", "rb") as f:
        return post, f.read()


def remover_pendente(post_id: str) -> None:
    for ext in (".json", ".jpg"):
        caminho = os.path.join(PENDENTES, post_id + ext)
        if os.path.exists(caminho):
            os.remove(caminho)


def proximo_horario(hist: dict) -> int | None:
    """Próximo horário livre da lista HORARIOS (ex.: "11:30,18:00,20:30").

    Retorna timestamp Unix, ou None se HORARIOS estiver vazio (publicar na hora).
    """
    horarios = [h.strip() for h in (os.environ.get("HORARIOS") or "").split(",") if h.strip()]
    if not horarios:
        return None
    agora = time.time()
    hist["agendados"] = [t for t in hist["agendados"] if t > agora]
    ocupados = set(hist["agendados"])
    hoje = datetime.now(FUSO).date()
    for dia in range(29):
        data = hoje + timedelta(days=dia)
        for h in sorted(horarios):
            hora, minuto = map(int, h.split(":"))
            t = int(datetime(data.year, data.month, data.day, hora, minuto, tzinfo=FUSO).timestamp())
            if t > agora + 20 * 60 and t not in ocupados:
                return t
    raise RuntimeError("Todos os horários dos próximos 29 dias já estão ocupados.")


def formatar_horario(ts: int) -> str:
    return datetime.fromtimestamp(ts, FUSO).strftime("%d/%m às %H:%M")
