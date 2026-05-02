from flask import Flask, render_template
import os
from supabase import create_client

# LACRE DE DIRETÓRIO: Garante que o Flask encontre a pasta static no Render
app = Flask(__name__, static_folder='static', template_folder='templates')

# CONFIGURAÇÃO DE CONEXÃO
url = "SUA_URL_DO_SUPABASE_AQUI"
key = "SUA_ANON_KEY_DO_SUPABASE_AQUI"
supabase = create_client(url, key)

@app.route('/')
def index():
    try:
        response = supabase.table('produtos').select("*").execute()
        produtos = response.data
        return render_template('index.html', produtos=produtos)
    except Exception as e:
        return f"Erro de conexão: {e}", 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
