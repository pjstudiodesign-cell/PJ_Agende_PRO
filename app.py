import os
from flask import Flask, render_template, send_from_directory, request, jsonify, redirect, url_for, session
from supabase import create_client, Client
from datetime import datetime, timedelta

app = Flask(__name__, static_folder='static', template_folder='templates')
app.secret_key = os.environ.get("SECRET_KEY", "pj_agende_pro_secret")

SUPABASE_URL = os.environ.get("SUPABASE_URL")
SUPABASE_KEY = os.environ.get("SUPABASE_KEY")
supabase: Client = create_client(SUPABASE_URL, SUPABASE_KEY)

# =====================================================
# DURAÇÃO EM MINUTOS DE CADA SERVIÇO
# =====================================================
DURACOES = {
    # BARBEARIA
    'Corte Moderno': 45,
    'Barba Premium': 30,
    'Cavanhaque Top': 30,
    'Corte Artístico': 60,

    # SALÃO
    'Corte Feminino': 60,
    'Escova Progressiva': 120,
    'Hidratação': 60,

    # MANICURE
    'Pé e Mão': 60,
    'Unhas em Gel': 90,
    'Esmaltação': 30,

    # TATUAGEM
    'Tatuagem Pequena': 60,
    'Tatuagem Média': 120,
    'Tatuagem Grande': 240,
    'Tatuagem Colorida': 180,

    # ESTÉTICA
    'Limpeza de Pele': 60,
    'Design de Sobrancelha': 30,
    'Depilação': 45,
    'Massagem Relaxante': 60,
}

DURACAO_PADRAO = 60


def get_slots_bloqueados(horario_inicio_str, duracao_minutos):
    """Retorna todos os slots de 30min ocupados por um serviço."""
    fmt = "%H:%M"
    inicio = datetime.strptime(horario_inicio_str, fmt)
    slots = []
    elapsed = 0

    while elapsed < duracao_minutos:
        slots.append(inicio.strftime(fmt))
        inicio += timedelta(minutes=30)
        elapsed += 30

    return slots


# =====================================================
# FRONTEND CLIENTE (CORE LACRADO)
# =====================================================

@app.route('/')
def index():
    try:
        produtos = supabase.table('produtos').select("*").execute()
        return render_template(
            'index.html',
            produtos=produtos.data,
            duracoes=DURACOES
        )
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
    data = request.args.get('data')
    profissional_id = request.args.get('profissional_id')

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
            servico = row['servico']
            duracao = DURACOES.get(servico, DURACAO_PADRAO)
            slots = get_slots_bloqueados(hora_str, duracao)
            todos_bloqueados.update(slots)

        return jsonify({'ocupados': sorted(list(todos_bloqueados))})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/agendar', methods=['POST'])
def agendar():
    dados = request.get_json()

    cliente = dados.get('cliente')
    servicos = dados.get('servicos')
    data = dados.get('data')
    horario = dados.get('horario')
    total = dados.get('total')
    profissional_id = dados.get('profissional_id')
    profissional_nome = dados.get('profissional_nome')

    if not all([cliente, servicos, data, horario, profissional_id]):
        return jsonify({'error': 'Campos obrigatórios faltando'}), 400

    try:
        existing = supabase.table('agendamentos') \
            .select('horario, servico') \
            .eq('data', data) \
            .eq('profissional_id', profissional_id) \
            .execute()

        duracao_total = sum(
            DURACOES.get(s, DURACAO_PADRAO) for s in servicos
        )

        slots_novos = get_slots_bloqueados(
            horario,
            duracao_total
        )

        for row in existing.data:
            hora_existente = row['horario'][:5]
            duracao_existente = DURACOES.get(
                row['servico'],
                DURACAO_PADRAO
            )

            slots_existentes = get_slots_bloqueados(
                hora_existente,
                duracao_existente
            )

            if set(slots_novos) & set(slots_existentes):
                return jsonify({
                    'error': f'Profissional indisponível nesse horário.'
                }), 409

        for servico in servicos:
            supabase.table('agendamentos').insert({
                'cliente': cliente,
                'servico': servico,
                'data': data,
                'horario': horario,
                'total': float(total),
                'profissional_id': int(profissional_id),
                'profissional_nome': profissional_nome
            }).execute()

        return jsonify({'success': True})

    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =====================================================
# ADMIN LOGIN
# =====================================================

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        usuario = request.form.get('usuario')
        senha = request.form.get('senha')

        try:
            admin = supabase.table('admins') \
                .select('*') \
                .eq('usuario', usuario) \
                .eq('senha', senha) \
                .execute()

            if admin.data:
                session['admin_logado'] = True
                session['admin_usuario'] = usuario
                return redirect(url_for('admin_dashboard'))

            return render_template(
                'admin_login.html',
                erro='Usuário ou senha inválidos'
            )

        except Exception as e:
            return render_template(
                'admin_login.html',
                erro=str(e)
            )

    return render_template('admin_login.html')


# =====================================================
# DASHBOARD ADMIN
# =====================================================

@app.route('/admin/dashboard')
def admin_dashboard():
    if not session.get('admin_logado'):
        return redirect(url_for('admin_login'))

    try:
        agendamentos = supabase.table('agendamentos') \
            .select('*') \
            .order('data') \
            .execute()

        total_agendamentos = len(agendamentos.data)

        hoje = datetime.now().strftime('%Y-%m-%d')

        agendamentos_hoje = [
            a for a in agendamentos.data
            if a['data'] == hoje
        ]

        return render_template(
            'admin_dashboard.html',
            agendamentos=agendamentos.data,
            total_agendamentos=total_agendamentos,
            agendamentos_hoje=len(agendamentos_hoje)
        )

    except Exception as e:
        return f"Erro no dashboard: {str(e)}", 500


# =====================================================
# CANCELAR AGENDAMENTO
# =====================================================

@app.route('/admin/cancelar/<int:agendamento_id>', methods=['POST'])
def cancelar_agendamento(agendamento_id):
    if not session.get('admin_logado'):
        return redirect(url_for('admin_login'))

    try:
        supabase.table('agendamentos') \
            .delete() \
            .eq('id', agendamento_id) \
            .execute()

        return redirect(url_for('admin_dashboard'))

    except Exception as e:
        return f"Erro ao cancelar: {str(e)}", 500


# =====================================================
# LOGOUT ADMIN
# =====================================================

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    return redirect(url_for('admin_login'))


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
