import os
import requests
from flask import Flask, render_template, send_from_directory, request, jsonify, redirect, url_for
from supabase import create_client, Client
from datetime import datetime, timedelta
from functools import wraps

app = Flask(__name__, static_folder='static', template_folder='templates')

SUPABASE_URL      = os.environ.get("SUPABASE_URL")
SUPABASE_KEY      = os.environ.get("SUPABASE_KEY")
ADMIN_TOKEN       = os.environ.get("ADMIN_TOKEN", "pjstudio2024token")
ULTRAMSG_INSTANCE = os.environ.get("ULTRAMSG_INSTANCE", "instance174522")
ULTRAMSG_TOKEN    = os.environ.get("ULTRAMSG_TOKEN", "y969oc7m8365o8nn")
WHATSAPP_DONO     = os.environ.get("WHATSAPP_DONO", "5524981196037")

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


def enviar_whatsapp(numero, mensagem):
    """Envia mensagem automática via UltraMsg."""
    try:
        url  = f"https://api.ultramsg.com/{ULTRAMSG_INSTANCE}/messages/chat"
        payload = {
            "token":   ULTRAMSG_TOKEN,
            "to":      numero,
            "body":    mensagem,
            "priority": 1
        }
        resp = requests.post(url, data=payload, timeout=10)
        return resp.status_code == 200
    except Exception as e:
        print(f"Erro UltraMsg: {e}")
        return False


def token_valido():
    token = request.headers.get('X-Admin-Token') or request.args.get('token')
    return token == ADMIN_TOKEN


def admin_required(f):
    @wraps(f)
    def decorated(*args, **kwargs):
        if not token_valido():
            return jsonify({'error': 'Não autorizado'}), 401
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
    dados             = request.get_json(force=True, silent=True) or {}
    cliente           = dados.get('cliente')
    servicos          = dados.get('servicos')
    data              = dados.get('data')
    horario           = dados.get('horario')
    total             = dados.get('total')
    profissional_id   = dados.get('profissional_id')
    profissional_nome = dados.get('profissional_nome')
    telefone_cliente  = dados.get('telefone', '')

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

        # Salva agendamentos
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

        # Salva notificação no banco
        servicos_str = ', '.join(servicos)
        supabase.table('notificacoes').insert({
            'cliente':      cliente,
            'profissional': profissional_nome,
            'data':         data,
            'horario':      horario,
            'servicos':     servicos_str,
            'total':        float(total)
        }).execute()

        # Monta e envia mensagem automática para o dono
        partes = data.split('-')
        data_fmt = f"{partes[2]}/{partes[1]}/{partes[0]}" if len(partes) == 3 else data
        servicos_lista = '\n'.join([f"  • {s}" for s in servicos])

        mensagem = (
            f"🗓️ *NOVO AGENDAMENTO - PJ STUDIO*\n\n"
            f"👤 *Cliente:* {cliente}\n"
            f"💼 *Profissional:* {profissional_nome}\n"
            f"📅 *Data:* {data_fmt}\n"
            f"🕐 *Horário:* {horario[:5]}\n\n"
            f"✨ *Serviços:*\n{servicos_lista}\n\n"
            f"💰 *Total:* R$ {float(total):.2f}\n\n"
            f"_Agendamento confirmado pelo PJ Agende Pro_ ⭐"
        )

        enviar_whatsapp(WHATSAPP_DONO, mensagem)

        # Envia confirmação automática para o cliente
        if telefone_cliente:
            numero_cliente = '55' + telefone_cliente if not telefone_cliente.startswith('55') else telefone_cliente
            confirmacao = (
                f"✅ *AGENDAMENTO CONFIRMADO!*\n\n"
                f"Olá {cliente}! Seu agendamento foi recebido com sucesso!\n\n"
                f"📅 *Data:* {data_fmt}\n"
                f"🕐 *Horário:* {horario[:5]}\n"
                f"💼 *Profissional:* {profissional_nome}\n"
                f"✨ *Serviços:* {servicos_str}\n\n"
                f"💰 *Total:* R$ {float(total):.2f}\n\n"
                f"Em breve entraremos em contato se necessário.\n"
                f"_PJ Studio — Obrigado pela preferência!_ ⭐"
            )
            enviar_whatsapp(numero_cliente, confirmacao)

        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


# =====================================================
# ROTAS DO PAINEL ADMIN
# =====================================================

@app.route('/admin', methods=['GET'])
def admin_login():
    return render_template('admin.html', pagina='login')


@app.route('/admin/login', methods=['POST'])
def admin_fazer_login():
    dados   = request.get_json(force=True, silent=True) or {}
    usuario = dados.get('usuario', '').strip()
    senha   = dados.get('senha', '').strip()

    if not usuario or not senha:
        return jsonify({'error': 'Preencha todos os campos'}), 400

    try:
        resp = supabase.table('admins') \
            .select('id') \
            .eq('usuario', usuario) \
            .eq('senha', senha) \
            .execute()

        if resp.data:
            return jsonify({'success': True, 'token': ADMIN_TOKEN})
        return jsonify({'error': 'Usuário ou senha incorretos'}), 401
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/painel', methods=['GET'])
def admin_painel():
    token = request.args.get('token', '')
    if token != ADMIN_TOKEN:
        return redirect(url_for('admin_login'))
    return render_template('admin.html', pagina='painel', token=token)


@app.route('/admin/checar-notificacao', methods=['GET'])
@admin_required
def admin_checar_notificacao():
    ultimo_id = int(request.args.get('ultimo_id', 0))
    try:
        resp = supabase.table('notificacoes') \
            .select('*') \
            .gt('id', ultimo_id) \
            .order('id') \
            .limit(1) \
            .execute()

        if resp.data:
            n = resp.data[0]
            return jsonify({
                'novo': True,
                'id':   n['id'],
                'dados': {
                    'cliente':      n['cliente'],
                    'profissional': n['profissional'],
                    'data':         str(n['data']),
                    'horario':      str(n['horario'])[:5],
                    'servicos':     n['servicos'],
                    'total':        float(n['total'] or 0)
                }
            })

        resp2 = supabase.table('notificacoes') \
            .select('id') \
            .order('id', desc=True) \
            .limit(1) \
            .execute()
        atual_id = resp2.data[0]['id'] if resp2.data else 0

        return jsonify({'novo': False, 'id': atual_id})
    except Exception as e:
        return jsonify({'novo': False, 'id': ultimo_id, 'error': str(e)})


@app.route('/admin/agendamentos', methods=['GET'])
@admin_required
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
@admin_required
def admin_cancelar_agendamento(id):
    try:
        supabase.table('agendamentos').delete().eq('id', id).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/servicos', methods=['GET'])
@admin_required
def admin_get_servicos():
    try:
        resp = supabase.table('produtos').select("*").order('categoria').execute()
        return jsonify({'servicos': resp.data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/servicos/<int:id>', methods=['PUT'])
@admin_required
def admin_editar_servico(id):
    dados = request.get_json(force=True, silent=True) or {}
    try:
        update = {}
        if 'nome'  in dados: update['nome']  = dados['nome']
        if 'preco' in dados: update['preco'] = float(dados['preco'])
        supabase.table('produtos').update(update).eq('id', id).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/profissionais', methods=['GET'])
@admin_required
def admin_get_profissionais():
    try:
        resp = supabase.table('profissionais').select("*").order('categoria').execute()
        return jsonify({'profissionais': resp.data})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/admin/profissionais', methods=['POST'])
@admin_required
def admin_add_profissional():
    dados = request.get_json(force=True, silent=True) or {}
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
@admin_required
def admin_editar_profissional(id):
    dados = request.get_json(force=True, silent=True) or {}
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
@admin_required
def admin_deletar_profissional(id):
    try:
        supabase.table('profissionais').delete().eq('id', id).execute()
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'error': str(e)}), 500


if __name__ == '__main__':
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)
