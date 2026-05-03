name: ARME - Preços combustíveis (rascunho)

on:
  # schedule:                     # <--- descomentar quando quiser automatizar
  #   - cron: '0 6 1 * *'        # 1º dia do mês às 6h Cabo Verde
  #     timezone: "Atlantic/Cape_Verde"
  workflow_dispatch:              # execução manual

jobs:
  run-script:
    runs-on: ubuntu-latest
    steps:
      - uses: actions/checkout@v4
      - uses: actions/setup-python@v5
        with:
          python-version: '3.10'
      - name: Instalar Tesseract
        run: |
          sudo apt-get update
          sudo apt-get install -y tesseract-ocr tesseract-ocr-por
      - run: pip install requests pytesseract Pillow python-wordpress-xmlrpc
      - name: Executar skill ARME
        env:
          ARME_IMAGE_URL: ${{ secrets.ARME_IMAGE_URL }}
          ARME_ILLUSTRATIVE_IMAGE_URL: ${{ secrets.ARME_ILLUSTRATIVE_IMAGE_URL }}
          WP_USERNAME: ${{ secrets.WP_USERNAME }}
          WP_PASSWORD: ${{ secrets.WP_PASSWORD }}
        run: python arme_fuel_prices.py
