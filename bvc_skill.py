# ============================================================
# SKILL BVC - Cotações da Bolsa de Valores de Cabo Verde
# Publica diretamente no WordPress.com com tabela, logos, setas,
# categoria "NOTÍCIAS & ATUALIZAÇÕES" e tags "bvc", "cotação"
# ============================================================

import collections
import collections.abc
import sys
import os
import requests
from bs4 import BeautifulSoup
import re
from datetime import datetime
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import NewPost
from getpass import getpass

# Correção para Python 3.12+
if not hasattr(collections, 'Iterable'):
    collections.Iterable = collections.abc.Iterable

# -------------------------------
# CONFIGURAÇÃO DAS EMPRESAS
# -------------------------------
empresas_info = {
    "BCA": {
        "sigla_exibida": "BCA",
        "logo_url": "https://play-lh.googleusercontent.com/i9B1fsSj1ALd_QYbku6rG3xyCZpMFlOgXcaaBc2DWaRhtAEup-Oxi2mhH2RmRL9Z76c"
    },
    "CAIXA": {
        "sigla_exibida": "CAIXA",
        "logo_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSNcR0HAOVJ6szqOcu1ewBmcjpi2zirnR5Drw&s"
    },
    "ENA": {
        "sigla_exibida": "ENACOL",
        "logo_url": "https://www.bcv.cv/SiteCollectionImages/Logotipos%20AGMVM/Empresas/Logo%20Enacol%202019.png"
    },
    "SCT": {
        "sigla_exibida": "SCT",
        "logo_url": "https://www.kantusta.cv/stocks/sct.png"
    }
}

# -------------------------------
# EXTRAÇÃO DAS COTAÇÕES
# -------------------------------
def obter_cotacoes():
    url = "https://bvc.cv/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    response = requests.get(url, headers=headers, timeout=15)
    response.raise_for_status()
    soup = BeautifulSoup(response.text, "html.parser")
    
    tabela = None
    for table in soup.find_all("table"):
        if table.find(string=re.compile("Título", re.I)) and table.find(string=re.compile("Data", re.I)):
            tabela = table
            break
    if not tabela:
        div_mercado = soup.find("div", string=re.compile("Actividades de Mercado", re.I))
        if div_mercado:
            tabela = div_mercado.find_next("table")
    if not tabela:
        raise Exception("Não foi possível encontrar a tabela de cotações.")
    
    linhas = tabela.find_all("tr")
    cabecalho_idx = 0
    for i, linha in enumerate(linhas):
        textos = [c.get_text(strip=True) for c in linha.find_all(["th", "td"])]
        if "Título" in textos and "Data" in textos:
            cabecalho_idx = i
            break
    
    cotacoes = []
    for linha in linhas[cabecalho_idx+1:]:
        cols = linha.find_all("td")
        if len(cols) >= 4:
            sigla = cols[0].get_text(strip=True)
            data = cols[1].get_text(strip=True)
            cotacao_raw = cols[2].get_text(strip=True).replace(',', '.')
            variacao = cols[3].get_text(strip=True)
            if sigla:
                cotacoes.append((sigla, data, cotacao_raw, variacao))
    return cotacoes

# -------------------------------
# FORMATAÇÃO HTML (TABELA + LOGOS + SETAS COLORIDAS)
# -------------------------------
def formatar_html(cotacoes):
    if not cotacoes:
        return "<p>⚠️ Nenhuma cotação disponível hoje.</p>"
    
    html = '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width:100%;">\n'
    html += "<tr><th>Empresa</th><th>Data da Cotação</th><th>Preço</th><th>Variação</th></tr>\n"
    
    for sigla, data, cot_raw, var in cotacoes:
        info = empresas_info.get(sigla, {"sigla_exibida": sigla, "logo_url": ""})
        sigla_exibida = info["sigla_exibida"]
        logo_url = info.get("logo_url", "")
        
        if logo_url:
            celula_empresa = f'<img src="{logo_url}" alt="{sigla_exibida}" style="height:24px; width:auto; vertical-align:middle; margin-right:8px;"> {sigla_exibida}'
        else:
            celula_empresa = sigla_exibida
        
        # Formatar valor com separador de milhar e unidade CVE
        try:
            valor_num = float(cot_raw)
            if valor_num.is_integer():
                valor_formatado = f"{int(valor_num):,}".replace(",", ".")
            else:
                valor_formatado = f"{valor_num:,.2f}".replace(",", ".")
            cot_cell = f"{valor_formatado} CVE"
        except:
            cot_cell = f"{cot_raw} CVE"
        
        # Variação com seta e cor
        var_clean = var.replace('%', '').strip()
        is_positive = False
        is_negative = False
        try:
            num = float(var_clean)
            if num > 0:
                is_positive = True
            elif num < 0:
                is_negative = True
        except:
            if var_clean.startswith('+'):
                is_positive = True
            elif var_clean.startswith('-'):
                is_negative = True
        
        if is_positive:
            seta = "⬆️"
            cor = "green"
        elif is_negative:
            seta = "⬇️"
            cor = "red"
        else:
            seta = "➡️"
            cor = "gray"
        
        variacao_html = f'<font color="{cor}">{seta} {var}</font>'
        
        html += f"<tr>\n"
        html += f"<td>{celula_empresa}</td>\n"
        html += f"<td>{data}</td>\n"
        html += f"<td>{cot_cell}</td>\n"
        html += f"<td>{variacao_html}</td>\n"
        html += f"</tr>\n"
    
    html += "</table>\n"
    html += '<p>📌 <em>Fonte: <a href="https://bvc.cv/" target="_blank">Bolsa de Valores de Cabo Verde</a></em></p>'
    return html

# -------------------------------
# PUBLICAR POST DIRETAMENTE (NÃO RASCUNHO)
# -------------------------------
def publicar_post(usuario, senha_app, titulo, conteudo):
    client = Client("https://fiscocaboverde.com/xmlrpc.php", usuario, senha_app)
    post = WordPressPost()
    post.title = titulo
    post.content = conteudo
    post.post_status = 'publish'   # Publica imediatamente
    post.terms_names = {
        'category': ['NOTÍCIAS & ATUALIZAÇÕES'],
        'post_tag': ['bvc', 'cotação']
    }
    return client.call(NewPost(post))

# -------------------------------
# EXECUÇÃO PRINCIPAL
# -------------------------------
def main():
    print("🔍 A obter cotações da BVC...")
    cotacoes = obter_cotacoes()
    
    if not cotacoes:
        print("⚠️ Nenhuma cotação encontrada.")
        return
    
    print(f"✅ {len(cotacoes)} empresa(s) encontrada(s):")
    for sigla, data, cot, var in cotacoes:
        sigla_exib = empresas_info.get(sigla, {}).get("sigla_exibida", sigla)
        print(f"   {sigla_exib}: {cot} CVE ({var}) em {data}")
    
    usuario = os.environ.get("WP_USERNAME")
    senha_app = os.environ.get("WP_PASSWORD")
    
    if not usuario or not senha_app:
        print("\n🔐 Credenciais do WordPress não encontradas nas variáveis de ambiente.")
        usuario = input("Utilizador (email ou username): ")
        senha_app = getpass("Application Password (16 caracteres): ")
    
    conteudo_html = formatar_html(cotacoes)
    titulo_post = f"Cotações BVC - {datetime.now().strftime('%d/%m/%Y')}"
    
    print("📝 A publicar post no WordPress...")
    post_id = publicar_post(usuario, senha_app, titulo_post, conteudo_html)
    print(f"\n✅ Post publicado com sucesso!")
    print(f"📄 ID do post: {post_id}")
    print(f"🔗 Ver post: https://fiscocaboverde.com/?p={post_id}")

# -------------------------------
# PONTO DE ENTRADA COM TRATAMENTO DE EXCEÇÕES
# -------------------------------
if __name__ == "__main__":
    try:
        main()
    except Exception as e:
        print(f"FATAL: {e}")
        sys.exit(1)
