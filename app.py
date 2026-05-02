import os
from flask import Flask, render_template, jsonify, send_from_directory
from supabase import create_client, Client

# Inicialização com o caminho fixo para os arquivos estáticos
app = Flask(__name__, static_folder='static', template_folder='templates')

# Configurações do Supabase
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def index():
    return render_template('index.html')

# ROTA CRÍTICA: Garante que as imagens da barbearia sejam entregues pelo servidor
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/api/produtos')
def get_produtos():
    try:
        # Busca os dados da Barbearia que você populou
        response = supabase.table('produtos').select("*").execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
