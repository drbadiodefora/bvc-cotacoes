# arme_fuel_prices.py
import os
import re
import requests
import base64
from datetime import datetime
from wordpress_xmlrpc import Client, WordPressPost
from wordpress_xmlrpc.methods.posts import NewPost
from PIL import Image
from io import BytesIO
import pytesseract

# ============================================================
# CONFIGURAÇÕES (variáveis de ambiente)
# ============================================================
IMAGE_URL = os.environ.get("ARME_IMAGE_URL")                # Tabela de preços (obrigatório)
ILLUSTRATIVE_IMAGE_URL = os.environ.get("ARME_ILLUSTRATIVE_IMAGE_URL")  # Imagem ilustrativa (opcional)
WP_USER = os.environ.get("WP_USERNAME")
WP_PASS = os.environ.get("WP_PASSWORD")

# ============================================================
# FUNÇÕES AUXILIARES
# ============================================================
def download_image_from_url(url, description="Imagem"):
    """Descarrega uma imagem a partir de um URL (link direto ou Google Drive)."""
    if not url:
        print(f"⚠️ {description} não fornecida.")
        return None
    # Se for URL do Google Drive (com /d/.../view), converte para download direto
    if "drive.google.com" in url:
        # Tenta extrair o file ID
        match = re.search(r'/d/([a-zA-Z0-9_-]+)', url)
        if match:
            file_id = match.group(1)
            download_url = f"https://drive.google.com/uc?export=download&id={file_id}"
        else:
            download_url = url
    else:
        download_url = url

    try:
        headers = {'User-Agent': 'Mozilla/5.0'}
        resp = requests.get(download_url, headers=headers, stream=True, timeout=30)
        resp.raise_for_status()
        return Image.open(BytesIO(resp.content))
    except Exception as e:
        print(f"❌ Erro ao descarregar {description}: {e}")
        return None

def image_to_base64(img):
    """Converte imagem PIL para string base64 (embed HTML)."""
    if img is None:
        return ""
    buffer = BytesIO()
    img.save(buffer, format="JPEG")
    img_b64 = base64.b64encode(buffer.getvalue()).decode()
    return f"data:image/jpeg;base64,{img_b64}"

def ocr_image(image):
    """Extrai texto da imagem usando Tesseract (português)."""
    return pytesseract.image_to_string(image, lang='por')

def parse_fuel_table(text):
    """Extrai dados da tabela principal (produto, preço, variação, diferença)."""
    produtos = [
        "Gasolina", "Gasóleo Normal", "Petróleo", "Butano \\(Gás\\)",
        "Gasóleo Eletricidade", "Gasóleo Marinha", "Fuel 380", "Fuel 180"
    ]
    pattern = re.compile(
        r'(' + '|'.join(produtos) + r')\s+([\d.,]+)\s*\/?[A-Za-z]*\s*([+-]?\d+%)\s*([+-]?[\d.,]+)',
        re.IGNORECASE
    )
    matches = pattern.findall(text)
    data = []
    for m in matches:
        produto = m[0].strip()
        preco = m[1].replace(',', '.')
        variacao = m[2]
        diferenca = m[3].replace(',', '.')
        data.append((produto, preco, variacao, diferenca))
    return data

def parse_butane_prices(text):
    """Extrai preços do gás butano por embalagem."""
    pattern = re.compile(r'Garrafa de\s+([\d.,]+)\s*Kg:\s*([\d.,]+)\s*ECV', re.IGNORECASE)
    matches = pattern.findall(text)
    butane = [(kg.replace(',', '.'), valor.replace(',', '.')) for kg, valor in matches]
    # Gás a Granel
    granel = re.search(r'Gás a Granel\s*\(Kg\):\s*([\d.,]+)\s*ECV', text, re.IGNORECASE)
    if granel:
        butane.append(("a Granel", granel.group(1).replace(',', '.')))
    return butane

def get_month_year_from_url(url):
    """Tenta extrair mês/ano do nome do ficheiro (ex: ARME_Precos_202502.jpg)."""
    if url:
        match = re.search(r'(\d{4})(\d{2})', url)
        if match:
            year = match.group(1)
            month_num = int(match.group(2))
            months = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
                      "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
            return f"{months[month_num-1]} {year}"
    # Fallback: mês actual
    now = datetime.now()
    months = ["Janeiro", "Fevereiro", "Março", "Abril", "Maio", "Junho",
              "Julho", "Agosto", "Setembro", "Outubro", "Novembro", "Dezembro"]
    return f"{months[now.month-1]} {now.year}"

def generate_html(fuel_data, butane_data, month_year, illustrative_img_b64):
    """Gera o HTML do post seguindo o template."""
    # Imagem ilustrativa no topo
    html = ""
    if illustrative_img_b64:
        html += f'<div style="text-align: center;"><img src="{illustrative_img_b64}" alt="Preços combustíveis ARME" style="max-width: 100%; height: auto;"></div>\n\n'

    html += f'<p>A Agência Reguladora Multissetorial da Economia (ARME) atualizou os preços máximos de venda dos combustíveis que vigoram entre 1 e 31 de {month_year}.</p>\n'
    html += '<p>De acordo com a nova tabela, regista-se uma tendência de aumento nos preços da maioria dos produtos petrolíferos em comparação com o mês passado, com exceção do Gás Butano, que mantém o seu valor inalterado.</p>\n'
    html += '<h3>Tabela de Preços ao Consumidor (Maio 2026)</h3>\n'  # Pode ajustar o mês
    html += '<p>Abaixo apresentamos os valores fixados para a venda a retalho, bem como a variação percentual e nominal em relação ao período de abril.</p>\n'
    html += '<table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">\n'
    html += "<tr><th>Produto</th><th>Preço Máximo (ECV/Unid.)</th><th>Variação (%)</th><th>Diferença (ECV)</th></tr>\n"
    for prod, preco, var, diff in fuel_data:
        html += f"<tr><td>{prod}</td><td>{preco}</td><td>{var}</td><td>{diff}</td></tr>\n"
    html += "</table>\n"

    if butane_data:
        html += '<h3>Preços do Gás Butano por Embalagem</h3>\n'
        html += '<p>Para as famílias e empresas que utilizam gás butano, os preços das garrafas (já com IVA incluído) permanecem os mesmos que vigoraram em abril:</p>\n'
        html += '<ul>\n'
        for kg, valor in butane_data:
            if kg == "a Granel":
                html += f'<li>Gás a Granel (Kg): {valor} ECV</li>\n'
            else:
                html += f'<li>Garrafa de {kg} Kg: {valor} ECV</li>\n'
        html += '</ul>\n'

    html += '<h3>Estrutura de Custos</h3>\n'
    html += '<p>O preço final de venda ao público é composto por diversos fatores regulados pela ARME, incluindo os Custos de Importação (CP), Custos de Logística (CU GSL), Custos de Distribuição (MMUD), além do IVA e outras taxas específicas aplicáveis ao setor.</p>\n'
    html += '<p><em>Fonte: Agência Reguladora Multissetorial da Economia (ARME) – Tabela de Novos Preços Máximos de 1 a 31 de ' + month_year + '</em></p>\n'
    return html

def create_draft(title, content):
    """Cria um rascunho no WordPress (status draft)."""
    client = Client("https://fiscocaboverde.com/xmlrpc.php", WP_USER, WP_PASS)
    post = WordPressPost()
    post.title = title
    post.content = content
    post.post_status = 'draft'   # <---- rascunho
    # post.post_status = 'publish' # <---- alterar para publicação direta após testes
    post.terms_names = {
        'category': ['NOTÍCIAS & ATUALIZAÇÕES'],
        'post_tag': ['combustíveis', 'ARME', 'preços']
    }
    return client.call(NewPost(post))

def main():
    print("🔍 A descarregar imagem da tabela de preços...")
    img_tabela = download_image_from_url(IMAGE_URL, "Tabela de preços")
    if not img_tabela:
        raise Exception("Não foi possível obter a imagem da tabela.")
    
    print("📄 A aplicar OCR...")
    texto = ocr_image(img_tabela)
    # Guarda para debug (opcional)
    with open("ocr_arme_output.txt", "w", encoding="utf-8") as f:
        f.write(texto)

    print("🛠️ Extraindo dados da tabela de combustíveis...")
    fuel_data = parse_fuel_table(texto)
    if not fuel_data:
        raise Exception("Não foi possível extrair os preços da tabela. Verifique o OCR.")
    
    print("🛠️ Extraindo preços do gás butano...")
    butane_data = parse_butane_prices(texto)
    
    print("🖼️ A descarregar imagem ilustrativa (opcional)...")
    img_illus = download_image_from_url(ILLUSTRATIVE_IMAGE_URL, "Imagem ilustrativa")
    illus_b64 = image_to_base64(img_illus) if img_illus else ""
    
    month_year = get_month_year_from_url(IMAGE_URL)
    print(f"📅 Período: {month_year}")
    
    html_content = generate_html(fuel_data, butane_data, month_year, illus_b64)
    post_title = f"ARME atualiza preços dos combustíveis – {month_year}"
    
    print("📝 A criar rascunho no WordPress...")
    post_id = create_draft(post_title, html_content)
    print(f"✅ Rascunho criado! ID: {post_id}")
    print(f"🔗 Editar: https://fiscocaboverde.com/wp-admin/post.php?post={post_id}&action=edit")

if __name__ == "__main__":
    main()
