"""Lê os cliques nos botões do Telegram e age: agenda no Facebook, descarta ou gera outra.

Também aceita o comando /gerar no chat do bot para criar mais um post na hora.
"""
from gerar import criar_post
from src import estado, facebook_api, telegram_api


def tratar_botao(cb: dict, hist: dict) -> None:
    acao, _, post_id = cb.get("data", "").partition("|")
    pendente = estado.carregar_pendente(post_id)
    if not pendente:
        telegram_api.responder_botao(cb["id"], "Esse post já foi resolvido.")
        return
    post, imagem = pendente
    msg_id = post.get("msg_id") or cb["message"]["message_id"]
    titulo = post["receita"]["titulo"]

    if acao == "ok":
        try:
            quando = estado.proximo_horario(hist)
            facebook_api.publicar_foto(imagem, post["legenda"], quando)
        except Exception as e:
            # Mantém o post pendente e os botões, para tentar de novo depois
            telegram_api.responder_botao(cb["id"], "Erro ao publicar")
            telegram_api.enviar_texto(f"⚠️ Não consegui publicar '{titulo}':\n{e}")
            return
        if quando:
            hist["agendados"].append(quando)
            status = f"✅ Agendado para {estado.formatar_horario(quando)}"
        else:
            status = "✅ Publicado agora"
        estado.remover_pendente(post_id)
        telegram_api.responder_botao(cb["id"], status)
        telegram_api.editar_texto(msg_id, f"{status}: {titulo}")

    elif acao == "no":
        estado.remover_pendente(post_id)
        telegram_api.responder_botao(cb["id"], "Descartado")
        telegram_api.editar_texto(msg_id, f"❌ Descartado: {titulo}")

    elif acao == "new":
        estado.remover_pendente(post_id)
        telegram_api.responder_botao(cb["id"], "Gerando outra receita...")
        telegram_api.editar_texto(msg_id, f"🔄 Substituído: {titulo}")
        criar_post(hist)


def main():
    hist = estado.carregar_historico()
    meu_chat = telegram_api.chat_id()
    atualizacoes = telegram_api.buscar_atualizacoes(hist["telegram_offset"])

    for upd in atualizacoes:
        hist["telegram_offset"] = upd["update_id"] + 1
        try:
            if "callback_query" in upd:
                cb = upd["callback_query"]
                if str(cb["message"]["chat"]["id"]) == meu_chat:
                    tratar_botao(cb, hist)
            elif "message" in upd:
                msg = upd["message"]
                if str(msg["chat"]["id"]) == meu_chat and msg.get("text", "").startswith("/gerar"):
                    telegram_api.enviar_texto("🍳 Gerando uma receita nova...")
                    criar_post(hist)
        except Exception as e:
            print(f"Erro ao tratar atualização {upd.get('update_id')}: {e}")
            try:
                telegram_api.enviar_texto(f"⚠️ Erro: {e}")
            except Exception:
                pass
        estado.salvar_historico(hist)  # salva a cada passo para não repetir ações

    estado.salvar_historico(hist)
    print(f"{len(atualizacoes)} atualização(ões) processada(s).")


if __name__ == "__main__":
    main()
