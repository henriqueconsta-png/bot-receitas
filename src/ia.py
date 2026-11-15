"""Geração da receita (texto) e da foto do prato (imagem)."""
import base64
import json
import os
import time

import requests

GEMINI_URL = "https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"


MODELOS_TEXTO_PADRAO = "gemini-3.8-flash,gemini-3.7-flash,gemini-3.6-flash"


def _gemini(model: str, body: dict, tentativas: int = 3) -> dict:
    """Chama a API do Gemini, repetindo em caso de sobrecarga ou demora."""
    headers = {"x-goog-api-key": os.environ["GEMINI_API_KEY"]}
    for tentativa in range(tentativas):
        ultima = tentativa == tentativas - 1
        try:
            r = requests.post(GEMINI_URL.format(model=model), headers=headers, json=body, timeout=120)
        except (requests.exceptions.Timeout, requests.exceptions.ConnectionError):
            if not ultima:
                time.sleep(15)
                continue
            raise RuntimeError(f"Gemini ({model}) não respondeu a tempo")
        if r.status_code in (429, 500, 503) and not ultima:
            time.sleep(20 * (tentativa + 1))
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
  "prompt_imagem": "descrição EM INGLÊS, de 40 a 70 palavras, do prato pronto exatamente como ele é servido numa casa brasileira"
}}

Como escrever o prompt_imagem (ele vai para uma IA de imagem que não conhece pratos brasileiros):
- Comece com o nome do prato em inglês e o nome em português entre parênteses.
- Descreva o FORMATO real (ex.: round bundt cake with a hole in the center; flat rectangular slices; small round golden balls).
- Diga o RECIPIENTE certo para esse prato (ex.: aluminum baking pan, glass baking dish, shallow white plate, clay pot).
- Diga as CORES e TEXTURAS reais, e como fica por dentro se for servido cortado.
- Cite SOMENTE ingredientes que estão na receita. Não invente guarnições, enfeites ou acompanhamentos."""


def gerar_receita(ideia: str | None, evitar: list[str]) -> dict:
    texto_ideia = f"- A receita de hoje deve ser: {ideia}\n" if ideia else "- Escolha você uma receita caseira brasileira querida.\n"
    prompt = PROMPT_RECEITA.format(ideia=texto_ideia, evitar=", ".join(evitar) or "nenhuma")
    lista = os.environ.get("GEMINI_TEXT_MODEL") or MODELOS_TEXTO_PADRAO
    modelos = [m.strip() for m in lista.split(",") if m.strip()]
    erros = []
    for modelo in modelos:  # se um modelo estiver fora do ar ou sobrecarregado, tenta o próximo
        config = {"responseMimeType": "application/json"}
        if modelo.startswith("gemini-3"):
            config["thinkingConfig"] = {"thinkingLevel": "low"}  # receita não precisa de raciocínio longo
        body = {"contents": [{"parts": [{"text": prompt}]}], "generationConfig": config}
        try:
            resp = _gemini(modelo, body, tentativas=2)
            break
        except Exception as e:
            erros.append(str(e)[:300])
    else:
        raise RuntimeError("Nenhum modelo do Gemini respondeu:\n" + "\n".join(erros))
    partes = resp["candidates"][0]["content"]["parts"]
    texto = "".join(p.get("text", "") for p in partes).strip()
    texto = texto.removeprefix("```json").removeprefix("```").removesuffix("```").strip()
    receita = json.loads(texto)
    for campo in ("titulo", "chamada", "ingredientes", "modo_preparo", "prompt_imagem"):
        if not receita.get(campo):
            raise ValueError(f"Resposta do Gemini sem o campo '{campo}': {texto[:300]}")
    return receita


ESTILO_FOTO = (
    "{prato}. "
    "Realistic close-up food photo taken with a smartphone in a Brazilian home kitchen. "
    "The dish is the single main subject and fills most of the frame, 45-degree angle, "
    "simple kitchen table, soft natural daylight from a window, late morning, appetizing, "
    "slightly imperfect homemade look, vertical framing. "
    "No text, no letters, no watermark, no people, no hands, no other dishes."
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