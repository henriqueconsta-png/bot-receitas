"""Geração da receita (texto) e da foto do prato (imagem)."""
import base64
import json
import os
import time

import requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


def _gemini(model: str, body: dict) -> dict:
    """Chama a API do Gemini com até 3 tentativas (limite de uso / instabilidade)."""
    headers = {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}
    for tentativa in range(3):
        r = requests.post(GEMINI_URL.format(model=model), headers=headers, json=body, timeout=180)
        if r.status_code in (429, 500, 503) and tentativa < 2:
            time.sleep(30 * (tentativa + 1))
            continue
        if not r.ok:
            raise RuntimeError(f"Gemini ({model}) erro {r.status_code}: {r.text[:500]}")
        return r.json()
    raise RuntimeError("Gemini não respondeu")


PROMPT_RECEITA = """Você escreve posts de receitas para uma página brasileira do Facebook
cujo público é principalmente de pessoas com mais de 45 anos.

Regras:
- Receita REAL, tradicional e testada, que funciona de verdade. Nada inventado ou exótico.
- Simples, barata, com ingredientes de mercado comum. Medidas caseiras (xícara, colher, copo).
- Linguagem calorosa e simples, como uma avó explicando. Sem gírias de internet.
- Máximo de 10 ingredientes e 8 passos curtos.
- Não prometa benefícios de saúde nem cura de doenças.
{ideia}
Não repita nenhuma destas receitas já publicadas: {evitar}

Responda SOMENTE com JSON neste formato:
{{
  "titulo": "nome curto da receita (máx. 6 palavras)",
  "chamada": "uma frase curta e afetiva para abrir o post",
  "ingredientes": ["..."],
  "modo_preparo": ["..."],
  "tempo": "ex.: 40 minutos",
  "rendimento": "ex.: 8 porções",
  "prompt_imagem": "descrição EM INGLÊS só da aparência do prato pronto (ingredientes visíveis, cor, textura, recipiente)"
}}"""


def gerar_receita(ideia: str | None, evitar: list[str]) -> dict:
    texto_ideia = f"- A receita de hoje deve ser: {ideia}\n" if ideia else "- Escolha você uma receita caseira brasileira querida.\n"
    prompt = PROMPT_RECEITA.format(ideia=texto_ideia, evitar=", ".join(evitar) or "nenhuma")
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseMimeType": "application/json", "temperature": 0.9},
    }
    resp = _gemini(os.environ.get("GEMINI_TEXT_MODEL") or "gemini-2.5-flash", body)
    partes = resp["candidates"][0]["content"]["parts"]
    texto = "".join(p.get("text", "") for p in partes).strip()
    texto = texto.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    receita = json.loads(texto)
    for campo in ("titulo", "chamada", "ingredientes", "modo_preparo", "prompt_imagem"):
        if not receita.get(campo):
            raise ValueError(f"Resposta do Gemini sem o campo '{campo}': {texto[:300]}")
    return receita


ESTILO_FOTO = (
    "Homemade food photo taken with a smartphone, {prato}. "
    "Served in a simple everyday ceramic dish on a rustic wooden kitchen table, "
    "soft natural daylight from a window, late morning, realistic and appetizing, "
    "slightly imperfect homemade look, shallow depth of field, vertical framing, "
    "no text, no letters, no watermark, no people, no hands."
)


def gerar_imagem(prompt_prato: str) -> bytes:
    prompt = ESTILO_FOTO.format(prato=prompt_prato)
    provedor = (os.environ.get("IMAGE_PROVIDER") or "gemini").lower()
    if provedor == "cloudflare":
        return _imagem_cloudflare(prompt)
    return _imagem_gemini(prompt)


def _imagem_gemini(prompt: str) -> bytes:
    body = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"responseModalities": ["IMAGE"], "imageConfig": {"aspectRatio": "4:5"}},
    }
    resp = _gemini(os.environ.get("GEMINI_IMAGE_MODEL") or "gemini-2.5-flash-image", body)
    for parte in resp["candidates"][0]["content"]["parts"]:
        dados = parte.get("inlineData") or parte.get("inline_data")
        if dados:
            return base64.b64decode(dados["data"])
    raise RuntimeError("O Gemini não devolveu imagem.")


def _imagem_cloudflare(prompt: str) -> bytes:
    conta = os.environ["CF_ACCOUNT_ID"]
    url = f"https://api.cloudflare.com/client/v4/accounts/{conta}/ai/run/@cf/black-forest-labs/flux-1-schnell"
    headers = {"Authorization": f"Bearer {os.environ['CF_API_TOKEN']}"}
    r = requests.post(url, headers=headers, json={"prompt": prompt, "steps": 8}, timeout=180)
    if not r.ok:
        raise RuntimeError(f"Cloudflare erro {r.status_code}: {r.text[:500]}")
    return base64.b64decode(r.json()["result"]["image"])
