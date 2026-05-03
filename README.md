# Skills de automação para o blogue [Fisco Cabo Verde](https://fiscocaboverde.com)

Este repositório contém scripts e workflows para publicação automática de conteúdos no WordPress.

## 📌 Skill 1: Cotações da BVC (semanal)

- **Ficheiro:** `bvc_skill.py`
- **Workflow:** `.github/workflows/bvc_semanal.yml`
- **Execução:** todas as segundas‑feiras às 6h (hora Cabo Verde)
- **O que faz:** extrai cotações da Bolsa de Valores de Cabo Verde, formata tabela com logótipos, setas coloridas e publica no blogue.
- **Credenciais necessárias:** `WP_USERNAME`, `WP_PASSWORD`

## 📌 Skill 2: Preços combustíveis ARME (mensal)

- **Ficheiro:** `arme_fuel_prices.py`
- **Workflow:** `.github/workflows/arme_mensal.yml`
- **Execução:** primeiro dia de cada mês às 6h (hora Cabo Verde) – atualmente em modo **rascunho** para testes.
- **O que faz:** descarrega imagem do Google Drive (tabela de preços), aplica OCR, extrai dados, insere imagem ilustrativa e cria post.
- **Credenciais adicionais:** `ARME_IMAGE_URL`, `ARME_ILLUSTRATIVE_IMAGE_URL`

## 🔧 Configuração

Os segredos devem ser adicionados no GitHub: **Settings → Secrets and variables → Actions**

- `WP_USERNAME` – seu utilizador do WordPress.com
- `WP_PASSWORD` – Application Password gerada no WordPress
- `ARME_IMAGE_URL` – link direto da imagem da tabela (Google Drive)
- `ARME_ILLUSTRATIVE_IMAGE_URL` – link direto da imagem ilustrativa (opcional)

## 🧪 Testes

- Execute manualmente os workflows através da aba **Actions**.
- Verifique os rascunhos no WordPress antes de alterar para publicação direta.

## 📅 Agendamento

- A skill BVC já está programada para executar semanalmente.
- A skill ARME aguarda a alteração de `draft` para `publish` e o descomentário do `schedule` no workflow.

---

*Qualquer dúvida, consulte os logs das execuções no GitHub Actions.*
