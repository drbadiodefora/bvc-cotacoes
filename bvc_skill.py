# bvc_skill.py
import os
import requests
from bs4 import BeautifulSoup
import re
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
# Configuração das empresas (logótipos, siglas)
# ============================================================
empresas_info = {
    "BCA": {"sigla_exibida": "BCA",
            "logo_url": "https://play-lh.googleusercontent.com/i9B1fsSj1ALd_QYbku6rG3xyCZpMFlOgXcaaBc2DWaRhtAEup-Oxi2mhH2RmRL9Z76c"},
    "CAIXA": {"sigla_exibida": "CAIXA",
              "logo_url": "https://encrypted-tbn0.gstatic.com/images?q=tbn:ANd9GcSNcR0HAOVJ6szqOcu1ewBmcjpi2zirnR5Drw&s"},
    "ENA": {"sigla_exibida": "ENACOL",
            "logo_url": "https://www.bcv.cv/SiteCollectionImages/Logotipos%20AGMVM/Empresas/Logo%20Enacol%202019.png"},
    "SCT": {"sigla_exibida": "SCT",
            "logo_url": "https://www.kantusta.cv/stocks/sct.png"}
}

# ============================================================
# Funções
# ============================================================
def obter_cotacoes():
    url = "https://bvc.cv/"
    headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"}
    resp = requests.get(url, headers=headers, timeout=15)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.text, "html.parser")
    
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
        raise Exception("Tabela de cotações não encontrada")
    
    linhas = tabela.find_all("tr")
    idx_cabecalho = 0
    for i, linha in enumerate(linhas):
        textos = [c.get_text(strip=True) for c in linha.find_all(["th","td"])]
        if "Título" in textos and "Data" in textos:
            idx_cabecalho = i
            break
    
    cotacoes = []
    for linha in linhas[idx_cabecalho+1:]:
        cols = linha.find_all("td")
        if len(cols) >= 4:
            sigla = cols[0].get_text(strip=True)
            data_bruta = cols[1].get_text(strip=True)
            cotacao = cols[2].get_text(strip=True).replace(',', '.')
            variacao = cols[3].get_text(strip=True)
            if sigla:
                cotacoes.append((sigla, data_bruta, cotacao, variacao))
    return cotacoes

def formatar_html(cotacoes):
    if not cotacoes:
        return "<p>⚠️ Nenhuma cotação disponível hoje.</p>"
    
    data_hoje = datetime.now().strftime("%d/%m/%Y")
    
    html = f'<p>Bom dia seguidor/a.</p>\n'
    html += f'<p>Seguem abaixo as cotações das empresas no mercado de Cabo Verde, para o dia {data_hoje}:</p>\n\n'
    
    html += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse; width:100%;">\n'
    html += "<tr><th>Empresa</th><th style=\"text-align:right\">Data</th><th style=\"text-align:right\">Preço CVE</th><th style=\"text-align:right\">Variação</th></tr>\n"
    
    for sigla, data_bruta, cot, var in cotacoes:
        # LIMPEZA DA DATA: Pega apenas a parte antes do espaço (remove HH:MM:SS)
        data_limpa = data_bruta.split(' ')[0]
        
        info = empresas_info.get(sigla, {"sigla_exibida": sigla, "logo_url": ""})
        sigla_exib = info["sigla_exibida"]
        logo = info.get("logo_url", "")
        
        if logo:
            celula_empresa = f'<div style="white-space: nowrap;"><img src="{logo}" alt="{sigla_exib}" style="height:24px; vertical-align:middle; margin-right:4px;">{sigla_exib}</div>'
        else:
            celula_empresa = sigla_exib
        
        # Formatação da variação
        var_num = re.sub(r'[^0-9\-+.]', '', var)
        try:
            num = float(var_num)
            if num > 0:
                seta, cor = "⬆️", "green"
            elif num < 0:
                seta, cor = "⬇️", "red"
            else:
                seta, cor = "➡️", "gray"
        except:
            seta, cor = "➡️", "gray"
        
        variacao_html = f'<div style="text-align: right;"><font color="{cor}">{seta} {var}</font></div>'
        data_html = f'<div style="text-align: right;">{data_limpa}</div>'
        cot_html = f'<div style="text-align: right;">{cot}</div>'
        
        html += f"<tr>\n"
        html += f"<td>{celula_empresa}</td>\n"
        html += f"<td>{data_html}</td>\n"
        html += f"<td>{cot_html}</td>\n"
        html += f"<td>{variacao_html}</td>\n"
        html += f"</tr>\n"
    
    html += "</table>\n"
    html += '<p>📌 <em>Fonte: <a href="https://bvc.cv/">Bolsa de Valores de Cabo Verde</a></em></p>'
    return html

def publicar_no_wordpress(titulo, conteudo):
    client = Client("https://fiscocaboverde.com/xmlrpc.php", WP_USER, WP_PASS)
    post = WordPressPost()
    post.title = titulo
    post.content = conteudo
    post.post_status = 'publish'  # Alterado para publicação automática
    post.terms_names = {
        'category': ['NOTÍCIAS & ATUALIZAÇÕES'],
        'post_tag': ['bvc', 'cotação']
    }
    return client.call(NewPost(post))

def main():
    print("🔍 Obtendo cotações da BVC...")
    try:
        cotacoes = obter_cotacoes()
        if not cotacoes:
            print("⚠️ Nenhuma cotação encontrada.")
            return
        
        print(f"✅ {len(cotacoes)} empresas encontradas.")
        conteudo = formatar_html(cotacoes)
        
        # Título com data formatada d/m/Y
        titulo = f"Cotações BVC - {datetime.now().strftime('%d/%m/%Y')}"
        
        print("🚀 Publicando no WordPress...")
        post_id = publicar_no_wordpress(titulo, conteudo)
        print(f"✅ Publicado com sucesso! ID: {post_id}")
        print(f"🔗 Ver post: https://fiscocaboverde.com/?p={post_id}")
        
    except Exception as e:
        print(f"❌ Erro: {e}")

if __name__ == "__main__":
    main()
