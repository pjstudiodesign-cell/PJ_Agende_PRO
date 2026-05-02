import os
from flask import Flask, render_template, send_from_directory, request, jsonify
from supabase import create_client, Client

app = Flask(__name__, static_folder='static', template_folder='templates')

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# Duração em minutos de cada serviço
DURACOES = {
    'Corte Moderno': 45,
    'Barba Premium': 30,
    'Cavanhaque Top': 30,
    'Corte Artístico': 60,
    'Corte Feminino': 60,
    'Escova Progressiva': 120,
    'Hidratação': 60,
    'Pé e Mão': 60,
    'Unhas em Gel': 90,
    'Esmaltação': 30,
}

DURACAO_PADRAO = 60  # minutos

@app.route('/')
def index():
    try:
        response = supabase.table('produtos').select("*").execute()
        return render_template('index.html', produtos=response.data)
    except Exception as e:
        return f"Erro Crítico: {str(e)}", 500

@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)

@app.route('/horarios-ocupados', methods=['GET'])
def horarios_ocupados():
    """Retorna horários já ocupados para uma data e serviço específicos."""
    data = request.args.get('data')
    servico = request.args.get('servico')

    if not data or not servico:
        return jsonify({'error': 'data e servico são obrigatórios'}), 400

    try:
        response = supabase.table('agendamentos') \
            .select('horario, servico') \
            .eq('data', data) \
            .eq('servico', servico) \
            .execute()

        ocupados = [row['horario'][:5] for row in response.data]  # formato HH:MM
        return jsonify({'ocupados': ocupados})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/agendar', methods=['POST'])
def agendar():
    """Salva um novo agendamento no banco."""
    dados = request.get_json()

    cliente  = dados.get('cliente')
    servicos = dados.get('servicos')   # lista de nomes
    data     = dados.get('data')
    horario  = dados.get('horario')
    total    = dados.get('total')

    if not all([cliente, servicos, data, horario]):
        return jsonify({'error': 'Campos obrigatórios faltando'}), 400

    try:
        # Verifica conflito para cada serviço selecionado
        for servico in servicos:
            check = supabase.table('agendamentos') \
                .select('id') \
                .eq('data', data) \
                .eq('servico', servico) \
                .eq('horario', horario) \
                .execute()

            if check.data:
                return jsonify({
                    'error': f'Horário {horario} já está ocupado para {servico}. Escolha outro horário.'
                }), 409

        # Salva cada serviço como um registro
        for servico in servicos:
            supabase.table('agendamentos').insert({
                'cliente': cliente,
                'servico': servico,
                'data': data,
                'horario': horario,
                'total': float(total)
            }).execute()

        return jsonify({'success': True, 'message': 'Agendamento confirmado!'})

    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
