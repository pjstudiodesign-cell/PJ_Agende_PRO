import os
from flask import Flask, render_template, send_from_directory, request, jsonify
from supabase import create_client, Client
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='static', template_folder='templates')

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================
# DURAÇÃO EM MINUTOS DE CADA SERVIÇO
# =====================================================
DURACOES = {
    # BARBEARIA
    'Corte Moderno':          45,
    'Barba Premium':          30,
    'Cavanhaque Top':         30,
    'Corte Artístico':        60,
    # SALÃO
    'Corte Feminino':         60,
    'Escova Progressiva':    120,
    'Hidratação':             60,
    # MANICURE
    'Pé e Mão':               60,
    'Unhas em Gel':           90,
    'Esmaltação':             30,
    # TATUAGEM
    'Tatuagem Pequena':       60,
    'Tatuagem Média':        120,
    'Tatuagem Grande':       240,
    'Tatuagem Colorida':     180,
    # ESTÉTICA
    'Limpeza de Pele':        60,
    'Design de Sobrancelha':  30,
    'Depilação':              45,
    'Massagem Relaxante':     60,
}
DURACAO_PADRAO = 60


def get_slots_bloqueados(horario_inicio_str, duracao_minutos):
    """Retorna todos os slots de 30 min ocupados por um serviço."""
    fmt = "%H:%M"
    inicio = datetime.strptime(horario_inicio_str, fmt)
    slots = []
    elapsed = 0
    while elapsed < duracao_minutos:
        slots.append(inicio.strftime(fmt))
        inicio += timedelta(minutes=30)
        elapsed += 30
    return slots


@app.route('/')
def index():
    try:
        response = supabase.table('produtos').select("*").execute()
        return render_template('index.html', produtos=response.data, duracoes=DURACOES)
    except Exception as e:
        return f"Erro Crítico: {str(e)}", 500


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)


@app.route('/horarios-ocupados', methods=['GET'])
def horarios_ocupados():
    data     = request.args.get('data')
    servicos = request.args.getlist('servico')

    if not data or not servicos:
        return jsonify({'error': 'data e servico são obrigatórios'}), 400

    try:
        todos_bloqueados = set()

        for servico in servicos:
            response = supabase.table('agendamentos') \
                .select('horario') \
                .eq('data', data) \
                .eq('servico', servico) \
                .execute()

            duracao = DURACOES.get(servico, DURACAO_PADRAO)

            for row in response.data:
                hora_str = row['horario'][:5]
                slots = get_slots_bloqueados(hora_str, duracao)
                todos_bloqueados.update(slots)

        return jsonify({'ocupados': sorted(list(todos_bloqueados))})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/agendar', methods=['POST'])
def agendar():
    dados    = request.get_json()
    cliente  = dados.get('cliente')
    servicos = dados.get('servicos')
    data     = dados.get('data')
    horario  = dados.get('horario')
    total    = dados.get('total')

    if not all([cliente, servicos, data, horario]):
        return jsonify({'error': 'Campos obrigatórios faltando'}), 400

    try:
        for servico in servicos:
            duracao     = DURACOES.get(servico, DURACAO_PADRAO)
            slots_novos = get_slots_bloqueados(horario, duracao)

            existing = supabase.table('agendamentos') \
                .select('horario') \
                .eq('data', data) \
                .eq('servico', servico) \
                .execute()

            for row in existing.data:
                hora_existente     = row['horario'][:5]
                duracao_existente  = DURACOES.get(servico, DURACAO_PADRAO)
                slots_existentes   = get_slots_bloqueados(hora_existente, duracao_existente)

                if set(slots_novos) & set(slots_existentes):
                    return jsonify({
                        'error': f'Horário indisponível para "{servico}". '
                                 f'Já existe agendamento às {hora_existente} '
                                 f'que ocupa esse período.'
                    }), 409

        for servico in servicos:
            supabase.table('agendamentos').insert({
                'cliente': cliente,
                'servico': servico,
                'data':    data,
                'horario': horario,
                'total':   float(total)
            }).execute()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
