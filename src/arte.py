"""Escreve o nome da receita sobre a foto.

O texto é colocado pelo próprio código (e não pela IA de imagem), porque as IAs
costumam errar letras e acentos em português.
"""
import io
import os

from PIL import Image, ImageDraw, ImageFont

LARGURA, ALTURA = 1080, 1350  # 4:5, formato que ocupa mais espaço no feed

FONTES = [
    os.path.join(os.path.dirname(__file__), "..", "fontes", "titulo.ttf"),  # coloque aqui uma fonte sua, se quiser
    "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    "/usr/share/fonts/truetype/liberation/LiberationSans-Bold.ttf",
    "C:/Windows/Fonts/arialbd.ttf",
]


def _fonte(tamanho: int):
    for caminho in FONTES:
        if os.path.exists(caminho):
            return ImageFont.truetype(caminho, tamanho)
    return ImageFont.load_default(size=tamanho)


def _recortar(img: Image.Image) -> Image.Image:
    """Redimensiona preenchendo 1080x1350 (corta as sobras, sem distorcer)."""
    escala = max(LARGURA / img.width, ALTURA / img.height)
    img = img.resize((round(img.width * escala), round(img.height * escala)), Image.LANCZOS)
    x = (img.width - LARGURA) // 2
    y = (img.height - ALTURA) // 2
    return img.crop((x, y, x + LARGURA, y + ALTURA))


def _quebrar(draw, texto, fonte, largura_max):
    linhas, atual = [], ""
    for palavra in texto.split():
        teste = f"{atual} {palavra}".strip()
        if draw.textlength(teste, font=fonte) <= largura_max:
            atual = teste
        else:
            if atual:
                linhas.append(atual)
            atual = palavra
    if atual:
        linhas.append(atual)
    return linhas


def aplicar_titulo(imagem_bytes: bytes, titulo: str) -> bytes:
    img = _recortar(Image.open(io.BytesIO(imagem_bytes)).convert("RGB"))
    draw = ImageDraw.Draw(img)
    texto = titulo.upper()
    margem = 70

    # Diminui a fonte até caber em no máximo 3 linhas
    for tamanho in range(96, 40, -4):
        fonte = _fonte(tamanho)
        linhas = _quebrar(draw, texto, fonte, LARGURA - 2 * margem)
        if len(linhas) <= 3:
            break

    altura_linha = int(tamanho * 1.18)
    altura_bloco = altura_linha * len(linhas) + 2 * 45
    topo = ALTURA - altura_bloco - 60

    # Faixa escura semitransparente para dar leitura
    faixa = Image.new("RGBA", img.size, (0, 0, 0, 0))
    ImageDraw.Draw(faixa).rounded_rectangle(
        (40, topo, LARGURA - 40, topo + altura_bloco), radius=36, fill=(25, 18, 12, 185)
    )
    img = Image.alpha_composite(img.convert("RGBA"), faixa).convert("RGB")
    draw = ImageDraw.Draw(img)

    y = topo + 45
    for linha in linhas:
        w = draw.textlength(linha, font=fonte)
        draw.text(((LARGURA - w) / 2, y), linha, font=fonte, fill=(255, 244, 222))
        y += altura_linha

    saida = io.BytesIO()
    img.save(saida, "JPEG", quality=90)
    return saida.getvalue()
