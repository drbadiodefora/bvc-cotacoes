# arme_fuel_prices_historical.py
# Publica preços ARME e calcula variações a partir de dados históricos (Abril, Março, ...)
import os
import re
import requests
from datetime import datetime
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import NewPost

# ============================================================
# Credenciais – lidas das variáveis de ambiente
# ============================================================
WP_USER = os.environ.get("WP_USERNAME", "")
WP_PASS = os.environ.get("WP_PASSWORD", "")

if not WP_USER or not WP_PASS:
    print("❌ Credenciais do WordPress não configuradas. Defina WP_USERNAME e WP_PASSWORD.")
    exit(1)

# ============================================================
# Base histórica de preços (fornecida pelo utilizador)
# ============================================================
PRECOS_HISTORICOS = {
    2026: {
        4: {  # Abril 2026
            "Gasolina": "139.89",
            "Gasóleo Normal": "117.52",
            "Gasóleo Eletricidade": "95.04",
            "Gasóleo Marinha": "86.32",
            "Petróleo": "148.66",
            "Fuel 380": "67.92",
            "Fuel 180": "70.99",
            "Butano Granel": "144.30"
        },
        3: {  # Março 2026
            "Gasolina": "129.50",
            "Gasóleo Normal": "108.80",
            "Gasóleo Eletricidade": "93.10",
            "Gasóleo Marinha": "82.20",
            "Petróleo": "137.70",
            "Fuel 380": "66.60",
            "Fuel 180": "69.60",
            "Butano Granel": "137.40"
        },
        2: {  # Fevereiro 2026
            "Gasolina": "121.40",
            "Gasóleo Normal": "103.90",
            "Gasóleo Eletricidade": "88.30",
            "Gasóleo Marinha": "78.00",
            "Petróleo": "132.20",
            "Fuel 380": "61.70",
            "Fuel 180": "64.60",
            "Butano Granel": "134.60"
        }
    }
}

# ============================================================
# Funções
# ============================================================
def obter_url_artigo(ano, mes):
    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    mes_nome = meses[mes-1]
    titulo = f"ARME atualiza preços máximos dos combustíveis para {mes_nome.lower()} {ano}"
    url_cat = "https://www.arme.cv/index.php?option=com_content&view=category&id=79&Itemid=878"
    try:
        resp = requests.get(url_cat, timeout=20)
        resp.raise_for_status()
        padrao = r'<a href="(index\.php\?option=com_content&amp;view=article&amp;id=\d+:[^"]+)".*?>(.*?)</a>'
        for link, tit in re.findall(padrao, resp.text, re.IGNORECASE):
            if titulo.lower() in tit.lower():
                return "https://www.arme.cv/" + link.replace('&amp;', '&')
    except:
        pass
    # Fallback manual para Maio 2026
    if ano == 2026 and mes == 5:
        return "https://www.arme.cv/index.php?option=com_content&view=article&id=1355:arme-atualiza-precos-maximos-dos-combustiveis-para-maio-2026&catid=79&Itemid=8789"
    return None

def extrair_precos_da_web(html):
    texto = re.sub(r'\s+', ' ', html)
    precos = {}
    padroes = {
        "Gasolina": r"Gasolina passa a ser vendida a ([\d.,]+) ESC/L",
        "Gasóleo Normal": r"Gasóleo Normal, a ([\d.,]+) ESC/L",
        "Gasóleo Eletricidade": r"Gasóleo para Eletricidade, a ([\d.,]+) ESC/L",
        "Gasóleo Marinha": r"Gasóleo Marinha, a ([\d.,]+) ESC/L",
        "Petróleo": r"Petróleo, ([\d.,]+) ESC/L",
        "Fuel 380": r"Fuel\s+380[^0-9]*([\d.,]+)\s*ESC/Kg",
        "Fuel 180": r"Fuel\s+180[^0-9]*([\d.,]+)\s*ESC/Kg",
        "Butano Granel": r"Gás Butano (?:passa a custar|mantem-se) a granel ([\d.,]+) ESC/Kg"
    }
    for prod, regex in padroes.items():
        m = re.search(regex, texto, re.IGNORECASE)
        if m:
            precos[prod] = m.group(1).replace(',', '.')
        else:
            nome_curto = prod.split()[0]
            fb = re.search(rf"{nome_curto}[^0-9]*([\d.,]+)\s*ESC", texto, re.IGNORECASE)
            if fb:
                precos[prod] = fb.group(1).replace(',', '.')
    return precos

def obter_precos(ano, mes, usar_web=True):
    if usar_web:
        url = obter_url_artigo(ano, mes)
        if url:
            try:
                resp = requests.get(url, timeout=20)
                resp.raise_for_status()
                precos = extrair_precos_da_web(resp.text)
                if precos and len(precos) >= 5:
                    print(f"✅ Preços de {mes}/{ano} obtidos da web.")
                    return precos
            except Exception as e:
                print(f"⚠️ Falha web para {mes}/{ano}: {e}")
    # Fallback para histórico
    if ano in PRECOS_HISTORICOS and mes in PRECOS_HISTORICOS[ano]:
        print(f"📦 Usando dados históricos para {mes}/{ano}.")
        return PRECOS_HISTORICOS[ano][mes].copy()
    return None

def calcular_variacoes(atual, anterior):
    variacoes = {}
    for prod in atual:
        if prod in anterior:
            try:
                a = float(atual[prod])
                ant = float(anterior[prod])
                diff = a - ant
                perc = (diff / ant) * 100 if ant != 0 else 0
                variacoes[prod] = {
                    'perc': f"{perc:+.2f}%".replace('.', ','),
                    'diff': f"{diff:+.2f}".replace('.', ',')
                }
                print(f"Variação {prod}: {perc:+.2f}% / {diff:+.2f}")
            except:
                variacoes[prod] = {'perc': '—', 'diff': '—'}
        else:
            variacoes[prod] = {'perc': '—', 'diff': '—'}
    return variacoes

def gerar_html(precos, variacoes, mes, ano):
    meses = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
             "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    mes_nome = meses[mes-1]
    data_vigor = f"1 a 31 de {mes_nome} {ano}"
    ordem = ["Gasolina", "Gasóleo Normal", "Petróleo", "Butano Granel",
             "Gasóleo Eletricidade", "Gasóleo Marinha", "Fuel 380", "Fuel 180"]
    tabela = '<table border="1" cellpadding="5" style="border-collapse: collapse;">\n'
    tabela += "<tr><th>Produto</th><th>Preço (ECV/Unid.)</th><th>Variação (%)</th><th>Diferença (ECV)</th></tr>\n"
    for prod in ordem:
        if prod in precos:
            preco = precos[prod].replace('.', ',')
            var = variacoes.get(prod, {'perc': '—', 'diff': '—'})
            tabela += f"<tr>\n"
            tabela += f"<td>{prod}</td>\n"
            tabela += f"<td>{preco}</td>\n"
            tabela += f"<td>{var['perc']}</td>\n"
            tabela += f"<td>{var['diff']}</td>\n"
            tabela += f"</tr>\n"
        else:
            tabela += f"<tr>\n"
            tabela += f"<td>{prod}</td>\n"
            tabela += "<td>—</td>\n"
            tabela += "<td>—</td>\n"
            tabela += "<td>—</td>\n"
            tabela += f"<tr>\n"
    tabela += "</table>\n"
    butano_granel = precos.get('Butano Granel', '0').replace('.', ',')
    html = f"""
<p>A Agência Reguladora Multissetorial da Economia (ARME) atualizou os preços máximos de venda dos combustíveis que vigoram entre {data_vigor}.</p>

<p>De acordo com a nova tabela, regista-se uma tendência de aumento nos preços da maioria dos produtos petrolíferos em comparação com o mês passado, com exceção do Gás Butano, que mantém o seu valor inalterado.</p>

<h3>Tabela de Preços ao Consumidor</h3>
<p>Abaixo apresentamos os valores fixados para a venda a retalho, bem como a variação percentual e nominal em relação ao período anterior:</p>

{tabela}

<h3>Preços do Gás Butano por Embalagem</h3>
<p>Para as famílias e empresas que utilizam gás butano, os preços das garrafas (já com IVA incluído) permanecem os mesmos que vigoraram em abril:</p>
<ul>
    <li>Garrafa de 3 Kg: 411,00 ECV</li>
    <li>Garrafa de 6 Kg: 866,00 ECV</li>
    <li>Garrafa de 12,5 Kg: 1.804,00 ECV</li>
    <li>Garrafa de 55 Kg: 7.937,00 ECV</li>
    <li>Gás a Granel (Kg): {butano_granel} ECV</li>
</ul>

<h3>Estrutura de Custos</h3>
<p>O preço final de venda ao público é composto por diversos fatores regulados pela ARME, incluindo os Custos de Importação (CP), Custos de Logística (CU GSL), Custos de Distribuição (MMUD), além do IVA e outras taxas específicas aplicáveis ao setor.</p>

<p><em>Fonte: Agência Reguladora Multissetorial da Economia (ARME) – Tabela de Novos Preços Máximos de {data_vigor}</em></p>
"""
    return html

def publicar_rascunho(titulo, conteudo):
    client = Client("https://fiscocaboverde.com/xmlrpc.php", WP_USER, WP_PASS)
    post = WordPressPost()
    post.title = titulo
    post.content = conteudo
    post.post_status = 'draft'   # altere para 'publish' para publicação automática
    post.terms_names = {
        'category': ['NOTÍCIAS & ATUALIZAÇÕES'],
        'post_tag': ['combustíveis', 'ARME']
    }
    return client.call(NewPost(post))

def main():
    hoje = datetime.now()
    ano = hoje.year
    mes = hoje.month

    print(f"🔍 Obtendo preços do mês actual ({mes}/{ano})...")
    atuais = obter_precos(ano, mes, usar_web=True)
    if not atuais:
        print("❌ Não foi possível obter preços do mês actual.")
        return

    mes_ant = mes - 1 if mes > 1 else 12
    ano_ant = ano if mes > 1 else ano - 1
    print(f"🔍 Obtendo preços do mês anterior ({mes_ant}/{ano_ant})...")
    anteriores = obter_precos(ano_ant, mes_ant, usar_web=True)
    if not anteriores:
        print("⚠️ Preços anteriores não disponíveis. Variações ficarão '—'.")

    variacoes = calcular_variacoes(atuais, anteriores) if anteriores else {}

    meses_str = ["janeiro", "fevereiro", "março", "abril", "maio", "junho",
                 "julho", "agosto", "setembro", "outubro", "novembro", "dezembro"]
    titulo = f"ARME atualiza preços máximos dos combustíveis para {meses_str[mes-1]} {ano}"
    html_final = gerar_html(atuais, variacoes, mes, ano)

    print("\n📝 A criar rascunho no WordPress...")
    post_id = publicar_rascunho(titulo, html_final)
    print(f"✅ Rascunho criado! ID: {post_id}")
    print(f"🔗 Editar: https://fiscocaboverde.com/wp-admin/post.php?post={post_id}&action=edit")

if __name__ == "__main__":
    main()
