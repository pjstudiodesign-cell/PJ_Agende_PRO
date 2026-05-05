import os
from flask import Flask, render_template, send_from_directory, request, jsonify, session, redirect, url_for
from supabase import create_client, Client
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get("SECRET_KEY", "pjstudio_secret_2024")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================
# DURAÇÃO EM MINUTOS DE CADA SERVIÇO
# =====================================================
DURACOES = {
    'Corte Moderno':          45,
    'Barba Premium':          30,
    'Cavanhaque Top':         30,
    'Corte Artístico':        60,
    'Corte Feminino':         60,
    'Escova Progressiva':    120,
    'Hidratação':             60,
    'Pé e Mão':               60,
    'Unhas em Gel':           90,
    'Esmaltação':             30,
    'Tatuagem Pequena':       60,
    'Tatuagem Média':        120,
    'Tatuagem Grande':       240,
    'Tatuagem Colorida':     180,
    'Limpeza de Pele':        60,
    'Design de Sobrancelha':  30,
    'Depilação':              45,
    'Massagem Relaxante':     60,
}
DURACAO_PADRAO = 60


def get_slots_bloqueados(horario_inicio_str, duracao_minutos):
    fmt = "%H:%M"
    inicio = datetime.strptime(horario_inicio_str, fmt)
    slots = []
    elapsed = 0
    while elapsed < duracao_minutos:
        slots.append(inicio.strftime(fmt))
        inicio += timedelta(minutes=30)
        elapsed += 30
    return slots


def login_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not session.get('admin_logado'):
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated


# =====================================================
# ROTAS PÚBLICAS
# =====================================================

@app.route('/')
def index():
    try:
        produtos = supabase.table('produtos').select("*").execute()
        return render_template('index.html', produtos=produtos.data, duracoes=DURACOES)
    except Exception as e:
        return f"Erro Crítico: {str(e)}", 500


@app.route('/static/<path:filename>')
def serve_static(filename):
    return send_from_directory(app.static_folder, filename)


@app.route('/profissionais', methods=['GET'])
def get_profissionais():
    categoria = request.args.get('categoria')
    if not categoria:
        return jsonify({'error': 'categoria obrigatória'}), 400
    try:
        resp = supabase.table('profissionais') \
            .select('id, nome') \
            .eq('categoria', categoria) \
            .eq('ativo', True) \
            .execute()
        return jsonify({'profissionais': resp.data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/horarios-ocupados', methods=['GET'])
def horarios_ocupados():
    data            = request.args.get('data')
    profissional_id = request.args.get('profissional_id')
    servicos        = request.args.getlist('servico')

    if not data or not profissional_id:
        return jsonify({'error': 'data e profissional_id são obrigatórios'}), 400

    try:
        resp = supabase.table('agendamentos') \
            .select('horario, servico') \
            .eq('data', data) \
            .eq('profissional_id', profissional_id) \
            .execute()

        todos_bloqueados = set()
        for row in resp.data:
            hora_str = row['horario'][:5]
            servico  = row['servico']
            duracao  = DURACOES.get(servico, DURACAO_PADRAO)
            slots    = get_slots_bloqueados(hora_str, duracao)
            todos_bloqueados.update(slots)

        return jsonify({'ocupados': sorted(list(todos_bloqueados))})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/agendar', methods=['POST'])
def agendar():
    dados             = request.get_json()
    cliente           = dados.get('cliente')
    servicos          = dados.get('servicos')
    data              = dados.get('data')
    horario           = dados.get('horario')
    total             = dados.get('total')
    profissional_id   = dados.get('profissional_id')
    profissional_nome = dados.get('profissional_nome')

    if not all([cliente, servicos, data, horario, profissional_id]):
        return jsonify({'error': 'Campos obrigatórios faltando'}), 400

    try:
        existing = supabase.table('agendamentos') \
            .select('horario, servico') \
            .eq('data', data) \
            .eq('profissional_id', profissional_id) \
            .execute()

        duracao_total = sum(DURACOES.get(s, DURACAO_PADRAO) for s in servicos)
        slots_novos   = get_slots_bloqueados(horario, duracao_total)

        for row in existing.data:
            hora_existente    = row['horario'][:5]
            duracao_existente = DURACOES.get(row['servico'], DURACAO_PADRAO)
            slots_existentes  = get_slots_bloqueados(hora_existente, duracao_existente)

            if set(slots_novos) & set(slots_existentes):
                return jsonify({
                    'error': f'Profissional indisponível nesse horário. '
                             f'Já existe agendamento às {hora_existente}. '
                             f'Escolha outro horário ou profissional.'
                }), 409

        for servico in servicos:
            supabase.table('agendamentos').insert({
                'cliente':           cliente,
                'servico':           servico,
                'data':              data,
                'horario':           horario,
                'total':             float(total),
                'profissional_id':   int(profissional_id),
                'profissional_nome': profissional_nome
            }).execute()

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =====================================================
# ROTAS DO PAINEL ADMIN
# =====================================================

@app.route('/admin', methods=['GET'])
def admin_login():
    if session.get('admin_logado'):
        return redirect(url_for('admin_painel'))
    return render_template('admin.html', pagina='login')


@app.route('/admin/login', methods=['GET', 'POST'])
def admin_fazer_login():
    if request.method == 'GET':
        return redirect(url_for('admin_login'))

    dados   = request.get_json()
    usuario = dados.get('usuario')
    senha   = dados.get('senha')

    try:
        resp = supabase.table('admins') \
            .select('id') \
            .eq('usuario', usuario) \
            .eq('senha', senha) \
            .execute()

        if resp.data:
            session['admin_logado']  = True
            session['admin_usuario'] = usuario
            return jsonify({'success': True})
        else:
            return jsonify({'error': 'Usuário ou senha incorretos'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/logout', methods=['GET'])
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


@app.route('/admin/painel', methods=['GET'])
@login_required
def admin_painel():
    return render_template('admin.html', pagina='painel')


@app.route('/admin/agendamentos', methods=['GET'])
@login_required
def admin_agendamentos():
    data_filtro = request.args.get('data')
    try:
        query = supabase.table('agendamentos').select("*").order('data').order('horario')
        if data_filtro:
            query = query.eq('data', data_filtro)
        resp = query.execute()
        return jsonify({'agendamentos': resp.data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/agendamentos/<int:id>', methods=['DELETE'])
@login_required
def admin_cancelar_agendamento(id):
    try:
        supabase.table('agendamentos').delete().eq('id', id).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/servicos', methods=['GET'])
@login_required
def admin_get_servicos():
    try:
        resp = supabase.table('produtos').select("*").order('categoria').execute()
        return jsonify({'servicos': resp.data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/servicos/<int:id>', methods=['PUT'])
@login_required
def admin_editar_servico(id):
    dados = request.get_json()
    try:
        update = {}
        if 'nome'  in dados: update['nome']  = dados['nome']
        if 'preco' in dados: update['preco'] = float(dados['preco'])
        supabase.table('produtos').update(update).eq('id', id).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/profissionais', methods=['GET'])
@login_required
def admin_get_profissionais():
    try:
        resp = supabase.table('profissionais').select("*").order('categoria').execute()
        return jsonify({'profissionais': resp.data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/profissionais', methods=['POST'])
@login_required
def admin_add_profissional():
    dados = request.get_json()
    try:
        supabase.table('profissionais').insert({
            'nome':      dados['nome'],
            'categoria': dados['categoria'],
            'ativo':     True
        }).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/profissionais/<int:id>', methods=['PUT'])
@login_required
def admin_editar_profissional(id):
    dados = request.get_json()
    try:
        update = {}
        if 'nome'      in dados: update['nome']      = dados['nome']
        if 'ativo'     in dados: update['ativo']     = dados['ativo']
        if 'categoria' in dados: update['categoria'] = dados['categoria']
        supabase.table('profissionais').update(update).eq('id', id).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/profissionais/<int:id>', methods=['DELETE'])
@login_required
def admin_deletar_profissional(id):
    try:
        supabase.table('profissionais').delete().eq('id', id).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
