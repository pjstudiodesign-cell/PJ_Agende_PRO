import os
from flask import Flask, render_template, jsonify, send_from_directory
from supabase import create_client, Client

# Inicialização com mapeamento fixo das pastas que você criou
app = Flask(__name__, static_folder='static', template_folder='templates')

# Conexão com Supabase via variáveis de ambiente do Render
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def index():
    try:
        # Busca os dados da tabela produtos para alimentar o HTML
        response = supabase.table('produtos').select("*").execute()
        # Envia a variável 'produtos' para o Jinja2 no index.html
        return render_template('index.html', produtos=response.data)
    except Exception as e:
        return f"Erro de Conexão: {str(e)}", 500

@app.route('/api/produtos')
def get_produtos():
    try:
        response = supabase.table('produtos').select("*").execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ROTA DE ENTREGA DE IMAGENS: Garante acesso à subpasta barbearia
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    # Porta obrigatória para o deploy no Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
