"""Funções mínimas da API do Telegram (sem bibliotecas extras)."""
import json
import os

import requests


def _chamar(metodo: str, dados: dict | None = None, arquivos: dict | None = None) -> dict:
    url = f"https://api.telegram.org/bot{os.environ['TELEGRAM_BOT_TOKEN']}/{metodo}"
    r = requests.post(url, data=dados, files=arquivos, timeout=60)
    resp = r.json()
    if not resp.get("ok"):
        raise RuntimeError(f"Telegram {metodo}: {resp}")
    return resp["result"]


def chat_id() -> str:
    return str(os.environ["TELEGRAM_CHAT_ID"])


def enviar_foto(foto: bytes, legenda: str) -> int:
    res = _chamar("sendPhoto", {"chat_id": chat_id(), "caption": legenda[:1000]},
                  {"photo": ("post.jpg", foto, "image/jpeg")})
    return res["message_id"]


def botoes(post_id: str) -> str:
    return json.dumps({"inline_keyboard": [[
        {"text": "✅ Aprovar", "callback_data": f"ok|{post_id}"},
        {"text": "🔄 Outra", "callback_data": f"new|{post_id}"},
        {"text": "❌ Descartar", "callback_data": f"no|{post_id}"},
    ]]})


def enviar_texto(texto: str, teclado: str | None = None) -> int:
    dados = {"chat_id": chat_id(), "text": texto[:4000]}
    if teclado:
        dados["reply_markup"] = teclado
    return _chamar("sendMessage", dados)["message_id"]


def editar_texto(message_id: int, texto: str) -> None:
    try:
        _chamar("editMessageText", {"chat_id": chat_id(), "message_id": message_id, "text": texto[:4000]})
    except RuntimeError:
        pass  # mensagem antiga ou igual: não é crítico


def responder_botao(callback_id: str, texto: str) -> None:
    try:
        _chamar("answerCallbackQuery", {"callback_query_id": callback_id, "text": texto})
    except RuntimeError:
        pass  # botão clicado há muito tempo: o Telegram recusa a resposta, mas tudo bem


def buscar_atualizacoes(offset: int) -> list[dict]:
    return _chamar("getUpdates", {"offset": offset, "timeout": 0,
                                  "allowed_updates": json.dumps(["message", "callback_query"])})
