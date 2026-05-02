import os
from flask import Flask, render_template, send_from_directory
from supabase import create_client, Client

# Lacre PJ Studio Design - Configuração de Pastas
app = Flask(__name__, static_folder='static', template_folder='templates')

# Conexão com Supabase via variáveis do Render
SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

@app.route('/')
def index():
    try:
        # Busca os produtos no banco (agora com a coluna 'imagem' que você criou)
        response = supabase.table('produtos').select("*").execute()
        return render_template('index.html', produtos=response.data)
    except Exception as e:
        return f"Erro Crítico: {str(e)}", 500

# ROTA DE SEGURANÇA: Garante que o Render entregue as fotos da subpasta barbearia
@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
