# Bot de Receitas para o Facebook

Todo dia o bot:

1. Cria receitas com o **Gemini** (texto grátis) e uma foto do prato com IA.
2. Escreve o nome da receita sobre a foto (feito pelo código, então nunca erra acento).
3. Manda a prévia no seu **Telegram** com 3 botões: ✅ Aprovar · 🔄 Outra · ❌ Descartar.
4. Quando você aprova, **agenda** o post na página do Facebook no próximo horário livre.

Tudo roda no **GitHub Actions**, sem precisar do seu PC ligado.

Comando extra: mande `/gerar` para o bot no Telegram e ele cria mais uma receita.

---

## Custos (sendo sincero)

| Parte | Custo |
|---|---|
| Texto (Gemini 2.5 Flash) | Grátis (limite de ~20 pedidos/dia no plano gratuito, sobra) |
| Foto com **Gemini** | **Pago**: cerca de US$ 0,04 por imagem → 3 posts/dia ≈ US$ 3,50/mês. Exige ativar faturamento no Google AI Studio. |
| Foto com **Cloudflare** (FLUX) | Grátis dentro do limite diário (dá para dezenas de imagens/dia). Qualidade um pouco menor. |
| GitHub Actions | Grátis em repositório **público**. Em repositório privado, mude o `verificar.yml` para `*/30` (para não passar das 2.000 min/mês). |

Recomendação: comece com **Cloudflare** (grátis). Se as fotos não agradarem, troque para Gemini mudando uma variável.

---

## Passo a passo

### 1. Criar o repositório
1. Crie um repositório novo no GitHub (ex.: `bot-receitas`) e envie todos estes arquivos.
2. Pode ser público: as chaves ficam em *Secrets*, que ninguém vê.

### 2. Chave do Gemini
1. Acesse https://aistudio.google.com/apikey e clique em **Create API key**.
2. Guarde a chave → vai virar o secret `GEMINI_API_KEY`.

### 3. Imagens (escolha uma)
**Cloudflare (grátis):**
1. Crie conta em https://dash.cloudflare.com
2. Copie o **Account ID** (aparece na página inicial, lado direito) → `CF_ACCOUNT_ID`.
3. Em *My Profile → API Tokens → Create Token*, use o modelo **Workers AI** → `CF_API_TOKEN`.
4. No GitHub, crie a variável `IMAGE_PROVIDER` = `cloudflare`.

**Gemini (pago):** ative o faturamento no AI Studio e deixe `IMAGE_PROVIDER` vazio ou `gemini`.

### 4. Bot do Telegram
1. No Telegram, fale com **@BotFather** → `/newbot` → escolha nome → ele te dá o **token** → `TELEGRAM_BOT_TOKEN`.
2. Mande qualquer mensagem para o seu bot novo.
3. Abra no navegador: `https://api.telegram.org/botSEU_TOKEN/getUpdates`
4. Procure `"chat":{"id":123456789` → esse número é o `TELEGRAM_CHAT_ID`.

### 5. Facebook (a parte burocrática, feita uma vez só)
1. Acesse https://developers.facebook.com → **Meus apps → Criar app** → tipo **Empresa/Outro**.
2. Adicione o produto **Facebook Login for Business** (ou apenas siga para o Graph API Explorer).
3. Abra o **Graph API Explorer**: https://developers.facebook.com/tools/explorer
   - Selecione seu app.
   - Em *Permissions*, adicione: `pages_show_list`, `pages_read_engagement`, `pages_manage_posts`.
   - Clique em **Generate Access Token** e autorize a sua página.
4. Transforme em token **de longa duração**:
   - Abra a **Ferramenta de depuração de token**: https://developers.facebook.com/tools/debug/accesstoken
   - Cole o token → **Extend Access Token** → copie o token novo.
5. Pegue o token **da página**: no Graph API Explorer, com o token longo, faça `GET me/accounts`.
   - Na resposta, ache sua página: o `id` é o `FB_PAGE_ID` e o `access_token` é o `FB_PAGE_TOKEN`.
   - Esse token de página gerado a partir de um token longo **não expira** (a menos que você troque a senha ou remova o app).

> Como você é o administrador do app e da página, **não precisa** passar pela revisão de app da Meta para postar na sua própria página.

### 6. Cadastrar tudo no GitHub
No repositório: **Settings → Secrets and variables → Actions**.

**Secrets** (aba *Secrets*):
| Nome | O que é |
|---|---|
| `GEMINI_API_KEY` | chave do passo 2 |
| `TELEGRAM_BOT_TOKEN` | token do BotFather |
| `TELEGRAM_CHAT_ID` | seu número do chat |
| `FB_PAGE_ID` | id da página |
| `FB_PAGE_TOKEN` | token da página |
| `CF_ACCOUNT_ID` / `CF_API_TOKEN` | só se usar Cloudflare |

**Variables** (aba *Variables*, todas opcionais):
| Nome | Exemplo | Para que serve |
|---|---|---|
| `IMAGE_PROVIDER` | `cloudflare` | `cloudflare` ou `gemini` (padrão) |
| `HORARIOS` | `11:30,18:00,20:30` | horários de Brasília em que os posts saem. Vazio = publica na hora em que você aprova |
| `QTD_POR_DIA` | `3` | quantas receitas gerar por dia (padrão 3) |
| `GEMINI_TEXT_MODEL` | `gemini-2.5-flash` | troque se o Google lançar outro modelo |
| `GEMINI_IMAGE_MODEL` | `gemini-2.5-flash-image` | idem |

### 7. Testar
1. Aba **Actions** → **Gerar receitas** → **Run workflow** (quantidade 1).
2. Em ~1 minuto a prévia chega no Telegram.
3. Aperte ✅. Depois rode **Verificar aprovações** → **Run workflow** (ou espere até 20 min).
4. Confira em *Meta Business Suite → Planejador* o post agendado.

---

## Como usar no dia a dia
- O bot gera as receitas todo dia às **07:17**. Você aprova quando puder; os posts entram na fila dos `HORARIOS`.
- Quer escolher as receitas? Escreva uma por linha no `ideias.txt`. Se a lista acabar, o Gemini escolhe sozinho sem repetir.
- **Sempre leia a receita antes de aprovar**: a IA às vezes erra medida ou tempo de forno.
- Para mudar o horário de geração, edite o `cron` em `.github/workflows/gerar.yml` (está em UTC: Brasília + 3h).

## Problemas comuns
- **Nada chega no Telegram**: veja o log na aba Actions. Erro `429` = limite do Gemini; erro de imagem com `limit: 0` = imagem do Gemini sem faturamento → use Cloudflare.
- **Erro do Facebook código 190**: token expirado → refaça o passo 5.
- **Erro do Facebook código 200**: falta permissão `pages_manage_posts` no token.
- **Cliquei e nada aconteceu**: normal esperar até 20 min (o GitHub às vezes atrasa o agendamento).
