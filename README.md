# Radar de Vagas da Deisi

Robô que procura vagas de faturamento hospitalar (e plano B administrativo/RH) em Porto Alegre e região, dá uma nota de 0 a 100 para cada vaga com base no currículo dela, desenha o radar de competências e manda alerta no Telegram quando aparece vaga boa.

## O que ele faz

| Etapa | Detalhe |
|---|---|
| Coleta | Gupy (API pública do portal), LinkedIn (vagas públicas da última semana, com descrição), Vagas.com.br. 9 termos principais + 5 secundários |
| Junta duplicadas | Mesma vaga em 2 sites vira 1 só (título + empresa), guardando a descrição mais completa |
| Nota | Título 35% + competências 35% + local 15% + recência 15%, com bônus (Tasy, vivência hospitalar, Santa Casa) e alertas (superior completo, exige enfermeira, cargo de liderança, MV) |
| Radar | 6 dimensões: Faturamento, Glosas/Auditoria, Tabelas, Sistemas, Clínico, Administrativo. Mostra "Deisi tem" x "vaga pede" |
| Lacunas | Lista o que as vagas boas pedem e ela não tem. Vira lista de estudo e preparação de entrevista |
| Histórico | SQLite em `dados/radar.db`: quando apareceu, em quais sites, se já avisou |
| Alerta | Telegram (e/ou e-mail) só com vagas novas de nota 55+ |
| Painel | `site/index.html`, funciona no celular: filtros, "NOVA", botão Candidatei / Descartar (fica salvo no aparelho) |

## Rodar no seu computador (5 min)

```bash
pip install -r requirements.txt
python main.py --demo --sem-alerta   # teste sem internet, com vagas de exemplo
rm dados/radar.db                    # apaga o teste
python main.py --sem-alerta          # coleta de verdade
# abra site/index.html no navegador
```

## Deixar rodando sozinho, de graça (GitHub Actions)

1. Crie um repositório **privado** no GitHub e suba esta pasta.
2. **Settings > Pages > Source: GitHub Actions.**
   Atenção: em repositório privado, Pages exige plano pago. Alternativas: deixe o repositório público (o painel só tem vagas públicas, sem dados pessoais além do nome) ou baixe o painel em Actions > execução > artifacts.
3. Telegram:
   - No Telegram, fale com **@BotFather**, `/newbot`, copie o token.
   - Mande um "oi" para o seu bot (e peça para sua mãe mandar também).
   - Abra `https://api.telegram.org/bot<TOKEN>/getUpdates` e copie o `chat.id` de cada um.
4. **Settings > Secrets and variables > Actions**, crie:
   - `TELEGRAM_TOKEN`
   - `TELEGRAM_CHAT_ID` (pode ser dois separados por vírgula: o seu e o dela)
   - opcional e-mail: `SMTP_HOST` (smtp.gmail.com), `SMTP_USER`, `SMTP_PASS` (senha de app), `EMAIL_PARA`
5. **Actions > Radar de Vagas > Run workflow** para rodar a primeira vez. Depois ele roda sozinho às 7h, 12h e 18h.

## Ajustar

Tudo fica em `config/perfil.yaml`:
- `buscas`: termos pesquisados em cada site
- `locais`: cidades aceitas
- `dimensoes`: nível dela (0 a 5) e termos que ela tem. **Se ela aprender algo novo (ex.: TISS, MV), coloque em `tem` e suba o nível.**
- `alertas` e `bonus`: o que tira ou soma pontos
- `nota_minima_alerta`: abaixe para receber mais vagas

Para usar com outra pessoa (ex.: vagas de dados), basta copiar o projeto e trocar o `perfil.yaml`.

## Testes

```bash
python -m pytest -q tests
```

## Limites honestos

- Sites mudam o HTML sem avisar. Se um coletor parar, os outros continuam e o erro fica registrado na tabela `execucoes`. LinkedIn às vezes devolve 429 (muitas requisições) em IPs do GitHub; o robô tenta de novo e segue.
- Indeed e Catho bloqueiam robôs; ficaram de fora de propósito.
- A nota mede aderência ao texto da vaga, não garante chamada. Vaga sem descrição recebe nota neutra em competências.
- Respeite os termos de uso dos sites: frequência baixa (3x ao dia), sem login, só vagas públicas.
