"""Publicação de foto com legenda na página do Facebook (Graph API)."""
import os

import requests


def publicar_foto(imagem: bytes, legenda: str, agendar_para: int | None = None) -> str:
    """Publica agora ou agenda (timestamp Unix, entre 10 min e 30 dias à frente)."""
    versao = os.environ.get("FB_API_VERSION") or "v21.0"
    url = f"https://graph.facebook.com/{versao}/{os.environ['FB_PAGE_ID']}/photos"
    dados = {"message": legenda, "access_token": os.environ["FB_PAGE_TOKEN"]}
    if agendar_para:
        dados["published"] = "false"
        dados["scheduled_publish_time"] = str(int(agendar_para))
    r = requests.post(url, data=dados, files={"source": ("post.jpg", imagem, "image/jpeg")}, timeout=120)
    resp = r.json()
    if "error" in resp:
        erro = resp["error"]
        raise RuntimeError(f"Facebook: {erro.get('message')} (código {erro.get('code')})")
    return resp.get("post_id") or resp.get("id", "")
