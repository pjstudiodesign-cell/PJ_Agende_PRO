import os
from flask import Flask, render_template, jsonify, send_from_directory
from supabase import create_client, Client

app = Flask(__name__, static_folder='static')

# Credenciais do Ambiente
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/produtos')
def get_produtos():
    try:
        response = supabase.table('produtos').select("*").execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# SOLUÇÃO PARA IMAGENS: Mapeamento direto e obrigatório
@app.route('/static/<path:filename>')
def custom_static(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
