from flask import Flask, render_template
import os
from supabase import create_client

app = Flask(__name__)

# CONFIGURAÇÃO DE CONEXÃO - COLOQUE SUAS CHAVES AQUI
# Pegue no Supabase: Settings -> API
url = "SUA_URL_DO_SUPABASE_AQUI"
key = "SUA_ANON_KEY_DO_SUPABASE_AQUI"
supabase = create_client(url, key)

@app.route('/')
def index():
    try:
        # Busca os serviços da Barbearia, Salão e Manicure de uma vez
        # O filtro de visualização será feito pelo HTML
        response = supabase.table('produtos').select("*").execute()
        produtos = response.data
        return render_template('index.html', produtos=produtos)
    except Exception as e:
        print(f"Erro de conexão: {e}")
        return "Erro ao carregar o banco de dados.", 500

if __name__ == '__main__':
    # Porta padrão para rodar no Render
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
