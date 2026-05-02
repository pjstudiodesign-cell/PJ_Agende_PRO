import os
from flask import Flask, render_template, jsonify
from supabase import create_client, Client

app = Flask(__name__)

# Configurações do Supabase - Buscando do ambiente para segurança
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def index():
    # Rota principal para carregar o seu index.html já lacrado
    return render_template('index.html')

@app.route('/api/produtos')
def get_produtos():
    # Busca os dados da tabela produtos que você já criou
    try:
        response = supabase.table('produtos').select("*").execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

if __name__ == '__main__':
    # Configuração cirúrgica para o Render
    port = int(os.environ.get("PORT", 5000))
    # Host 0.0.0.0 é obrigatório para o deploy não falhar
    app.run(host='0.0.0.0', port=port)
