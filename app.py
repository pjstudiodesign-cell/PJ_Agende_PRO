import os
from flask import Flask, render_template, jsonify, send_from_directory
from supabase import create_client, Client

# Inicialização com mapeamento fixo das pastas static e templates
app = Flask(__name__, static_folder='static', template_folder='templates')

# Conexão com Supabase via variáveis de ambiente do Render
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def index():
    try:
        # Busca os dados da tabela produtos para alimentar o HTML
        # O lacre aqui é enviar exatamente a variável 'produtos' que o seu index.html espera
        response = supabase.table('produtos').select("*").execute()
        return render_template('index.html', produtos=response.data)
    except Exception as e:
        # Retorno de erro técnico caso a conexão falhe
        return f"Erro de Conexão: {str(e)}", 500

@app.route('/api/produtos')
def get_produtos():
    try:
        response = supabase.table('produtos').select("*").execute()
        return jsonify(response.data)
    except Exception as e:
        return jsonify({"error": str(e)}), 500

# ROTA DE ENTREGA DE IMAGENS: Mantida para garantir acesso à subpasta barbearia
# Sem esta rota, o servidor Render bloqueia o acesso aos arquivos servico1.jpg, etc.
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    # Porta dinâmica obrigatória para o ambiente Render
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
