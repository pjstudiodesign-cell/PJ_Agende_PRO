import os
from flask import Flask, render_template
from supabase import create_client, Client

app = Flask(__name__)

# --- BLOCO DE CONEXÃO BLINDADA ---
# As chaves são buscadas diretamente do ambiente do Render para segurança total
url: str = os.environ.get("SUPABASE_URL")
key: str = os.environ.get("SUPABASE_KEY")

# Inicialização do cliente Supabase com verificação de existência das chaves
if url and key:
    supabase: Client = create_client(url, key)
else:
    supabase = None

@app.route('/')
def index():
    """
    Rota principal: Busca serviços e produtos do banco de dados real.
    Mantém o nome da variável 'produtos' para garantir compatibilidade 
    com o seu template index.html atual.
    """
    lista_final = []
    
    if supabase:
        try:
            # Busca na tabela de serviços criada no SQL Editor
            response_servicos = supabase.table("servicos").select("*").execute()
            if response_servicos.data:
                lista_final.extend(response_servicos.data)
                
            # Busca na tabela de produtos (caso existam itens de venda)
            response_produtos = supabase.table("produtos").select("*").execute()
            if response_produtos.data:
                lista_final.extend(response_produtos.data)
                
        except Exception as e:
            # Em caso de erro técnico, o erro é logado mas o site não cai
            print(f"Erro na busca de dados: {e}")
    
    # Renderização integral enviando os dados do banco para o HTML
    return render_template('index.html', produtos=lista_final)

if __name__ == '__main__':
    # Configuração de porta dinâmica para o ambiente do Render
    port = int(os.environ.get("PORT", 10000))
    app.run(host='0.0.0.0', port=port, debug=False)
