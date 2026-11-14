"""Faz todas as chamadas de internet do bot tentarem de novo quando a conexão cai.

Serviços gratuitos às vezes derrubam a conexão no meio ("Connection reset by peer").
O Facebook fica de fora para nunca correr o risco de publicar o mesmo post duas vezes.
"""
import time
from urllib.parse import urlparse

import requests

_post_original = requests.post


def _post_com_repeticao(url, *args, **kwargs):
    servidor = urlparse(url).hostname or url
    tentativas = 1 if "facebook.com" in servidor else 3
    for tentativa in range(tentativas):
        try:
            return _post_original(url, *args, **kwargs)
        except requests.exceptions.ConnectionError as e:
            if tentativa == tentativas - 1:
                raise RuntimeError(f"Falha de conexão com {servidor}: {e}") from e
            time.sleep(10 * (tentativa + 1))


if not getattr(requests.post, "_com_repeticao", False):  # evita embrulhar duas vezes
    _post_com_repeticao._com_repeticao = True
    requests.post = _post_com_repeticao