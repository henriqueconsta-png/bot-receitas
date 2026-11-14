"""Gera posts de receita e manda para aprovação no Telegram.

Uso: python gerar.py            (gera QTD_POR_DIA posts, padrão 3)
     python gerar.py 1          (gera 1 post)
"""
import os
import sys
import time
import uuid
from datetime import datetime

from src import arte, estado, ia, telegram_api


def montar_legenda(r: dict) -> str:
    ingredientes = "\n".join(f"• {i}" for i in r["ingredientes"])
    passos = "\n".join(f"{n}. {p}" for n, p in enumerate(r["modo_preparo"], 1))
    extras = " | ".join(x for x in (
        f"⏱ {r['tempo']}" if r.get("tempo") else "",
        f"🍽 Rende {r['rendimento']}" if r.get("rendimento") else "",
    ) if x)
    return (
        f"{r['titulo']} 😋\n\n"
        f"{r['chamada']}\n\n"
        f"🛒 INGREDIENTES\n{ingredientes}\n\n"
        f"👩‍🍳 MODO DE PREPARO\n{passos}\n\n"
        + (f"{extras}\n\n" if extras else "")
        + "Salve essa receita para não perder! ❤️"
    )


def criar_post(hist: dict) -> str:
    ideia = estado.proxima_ideia(hist)
    receita = ia.gerar_receita(ideia, evitar=hist["titulos"][-80:])
    foto = ia.gerar_imagem(receita["prompt_imagem"])
    imagem = arte.aplicar_titulo(foto, receita["titulo"])
    legenda = montar_legenda(receita)

    post_id = datetime.now(estado.FUSO).strftime("%Y%m%d-%H%M") + "-" + uuid.uuid4().hex[:4]
    post = {"id": post_id, "receita": receita, "legenda": legenda, "ideia": ideia}

    telegram_api.enviar_foto(imagem, f"📝 Prévia: {receita['titulo']}")
    post["msg_id"] = telegram_api.enviar_texto(legenda, telegram_api.botoes(post_id))
    estado.salvar_pendente(post, imagem)

    hist["titulos"].append(receita["titulo"])
    if ideia:
        hist["ideias_usadas"].append(ideia)
    print(f"Post {post_id} criado: {receita['titulo']}")
    return post_id


def main():
    qtd = int(sys.argv[1]) if len(sys.argv) > 1 else int(os.environ.get("QTD_POR_DIA") or 3)
    hist = estado.carregar_historico()
    erros = 0
    for n in range(qtd):
        try:
            criar_post(hist)
        except Exception as e:  # um erro não deve impedir os outros posts
            erros += 1
            print(f"Erro ao gerar post: {e}")
            try:
                telegram_api.enviar_texto(f"⚠️ Erro ao gerar receita:\n{e}")
            except Exception:
                pass
        estado.salvar_historico(hist)
        if n < qtd - 1:
            time.sleep(15)  # respeita o limite por minuto do plano gratuito
    if erros == qtd:
        sys.exit(1)


if __name__ == "__main__":
    main()
