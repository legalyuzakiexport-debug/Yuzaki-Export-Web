from flask import Flask, render_template, request, redirect, url_for, session, flash, abort
import os
import secrets
from datetime import datetime, timedelta, date
from flask_mail import Mail
from werkzeug.security import generate_password_hash, check_password_hash
import random
from flask_mail import Mail, Message
from database import DB_Ligar
from utils import (enviar_email_sistema, enviar_recibo, 
                   enviar_contacto_suporte, enviar_recuperacao_senha, enviar_notificacao_amizade)

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'yuzaki_export_key_2024')

# --- CONFIGURAÇÕES DO SISTEMA ---
ADMIN_EMAIL = "yuzakisama2007@gmail.com"
UPLOAD_FOLDER = os.path.join('static', 'uploads', 'games')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

# CONFIGURAÇÃO DE E-MAIL
app.config.update(
    MAIL_SERVER='smtp.gmail.com',
    MAIL_PORT=587,
    MAIL_USE_TLS=True,
    MAIL_USERNAME='yuzakisama2007@gmail.com',
    MAIL_PASSWORD='jgjttjeowqbjiqwx', 
    MAIL_DEFAULT_SENDER='yuzakisama2007@gmail.com'
)
mail = Mail(app)

def calcular_preco_atual(jogo):
    hoje = date.today()
    if jogo.get('desconto_percentual') and jogo.get('promo_inicio') and jogo.get('promo_fim'):
        # Garantir que as datas são comparáveis
        if jogo['promo_inicio'] <= hoje <= jogo['promo_fim']:
            desconto = jogo['desconto_percentual']
            preco_original = float(jogo['preco'])
            return round(preco_original * (1 - (desconto / 100)), 2)
    return float(jogo.get('preco', 0))

@app.context_processor
def utility_processor():
    return dict(calcular_preco_atual=calcular_preco_atual)

# ---------------------------------------------------------
# 1. AUTENTICAÇÃO E ACESSO
# ---------------------------------------------------------

# 1. INICIAL
@app.route('/')
def Inicial():
    return redirect(url_for('Entrar'))

# 2. ENTRAR (Com interrupção para 2FA)
@app.route('/entrar', methods=['GET', 'POST'])
def Entrar():
    if request.method == 'POST':
        email = request.form.get('email')
        senha = request.form.get('password')

        conn = DB_Ligar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT * FROM utilizadores WHERE email = %s", (email,))
        user = cursor.fetchone()
        conn.close()

        if user and check_password_hash(user['palavra_passe'], senha):
            # 1. Gerar código aleatório de 6 dígitos
            codigo_2fa = str(random.randint(100000, 999999))
            
            # 2. Guardar dados na SESSION temporária (não logado ainda)
            session['temp_user'] = {
                'id': user['id'],
                'nome': user['nome_utilizador'],
                'email': user['email'],
                'codigo': codigo_2fa
            }
            
            # 3. Enviar o email estilizado
            try:
                msg = Message('Yuzaki Export — Código de Verificação',
                              recipients=[email])
                
                msg.html = render_template('emails/codigo_2fa.html', 
                                           nome=user['nome_utilizador'], 
                                           codigo=codigo_2fa)
                # mail.send(msg)
                
                flash("Enviámos um código de segurança para o teu e-mail.", "info")
                return redirect(url_for('Verificar2FA'))
                
            except Exception as e:
                print(f"Erro ao enviar e-mail: {e}")
                flash("Houve um problema ao enviar o código. Tenta novamente.", "error")
                return redirect(url_for('Entrar'))
        
        flash("Email ou Senha incorretos!", "error")
        
    return render_template('entrar.html')


# 2.1 VERIFICAR 2FA
@app.route('/verificar-2fa', methods=['GET', 'POST'])
def Verificar2FA():
    # Segurança: Se não houver processo de login a decorrer, bloqueia o acesso
    if 'temp_user' not in session:
        return redirect(url_for('Entrar'))

    if request.method == 'POST':
        codigo_inserido = request.form.get('codigo')
        temp_data = session['temp_user']

        # Compara o que o user digitou com o que guardámos na session
        if codigo_inserido == temp_data['codigo']:
            # SUCESSO: Ativa a sessão oficial do utilizador
            session['user_id'] = temp_data['id']
            session['user_name'] = temp_data['nome']
            session['user_email'] = temp_data['email']
            
            # Limpa o "lixo" temporário da sessão
            session.pop('temp_user', None)
            
            flash(f"Login concluído! Bem-vindo {session['user_name']}.", "success")
            return redirect(url_for('Index'))
        else:
            flash("Código de verificação incorreto!", "error")

    return render_template('verificar_2fa.html')

# 3. REGISTAR
@app.route('/registar', methods=['GET', 'POST'])
def Registar():
    if request.method == 'POST':
        nome = request.form.get('username')
        email = request.form.get('email')
        senha_hash = generate_password_hash(request.form.get('password'))
        agora = datetime.now()

        try:
            conn = DB_Ligar()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO utilizadores (nome_utilizador, email, palavra_passe, data_registo, hora_registo)
                VALUES (%s, %s, %s, %s, %s)
            """, (nome, email, senha_hash, agora.date(), agora.time()))
            conn.commit()
            
            # enviar_email_sistema(mail, "Bem-vindo ao Yuzaki Export!", email, 'emails/boas_vindas.html', nome=nome)
            flash("Conta criada com sucesso!", "success")
            return redirect(url_for('Entrar'))
        except Exception as e:
            flash(f"Erro ao registar: {e}", "error")
        finally:
            conn.close()
    return render_template('registar.html')

# 4. SAIR
@app.route('/sair')
def Sair():
    session.clear()
    return redirect(url_for('Entrar'))

# 5. ESQUECI A SENHA
@app.route('/esqueci-senha', methods=['GET', 'POST'])
def EsqueciSenha():
    if request.method == 'POST':
        email = request.form.get('email')
        conn = DB_Ligar()
        cursor = conn.cursor(dictionary=True)
        cursor.execute("SELECT id, nome_utilizador FROM utilizadores WHERE email = %s", (email,))
        user = cursor.fetchone()
        
        if user:
            token = secrets.token_urlsafe(32)
            validade = datetime.now() + timedelta(hours=1)
            cursor.execute("DELETE FROM tokens_recuperacao WHERE utilizador_id = %s", (user['id'],))
            cursor.execute("""
                INSERT INTO tokens_recuperacao (utilizador_id, token, data_expiracao) 
                VALUES (%s, %s, %s)
            """, (user['id'], token, validade))
            conn.commit()
            
            link = url_for('RedefinirSenha', token=token, _external=True)
            enviar_recuperacao_senha(mail, email, user['nome_utilizador'], link)
            
        flash("Se o e-mail estiver correto, receberás instruções.", "success")
        conn.close()
        return redirect(url_for('Entrar'))
    return render_template('esqueceu_senha.html')

# 6. REDEFINIR A SENHA (TOKEN)
@app.route('/redefinir-senha/<token>', methods=['GET', 'POST'])
def RedefinirSenha(token):
    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT utilizador_id FROM tokens_recuperacao 
        WHERE token = %s AND usado = 0 AND data_expiracao > %s
    """, (token, datetime.now()))
    res = cursor.fetchone()
    
    if not res:
        flash("Link inválido ou expirado.", "error")
        return redirect(url_for('EsqueciSenha'))

    if request.method == 'POST':
        nova_senha = generate_password_hash(request.form.get('password'))
        cursor.execute("UPDATE utilizadores SET palavra_passe = %s WHERE id = %s", (nova_senha, res['utilizador_id']))
        cursor.execute("UPDATE tokens_recuperacao SET usado = 1 WHERE token = %s", (token,))
        conn.commit()
        conn.close()
        flash("Senha alterada com sucesso!", "success")
        return redirect(url_for('Entrar'))
    
    conn.close()
    return render_template('nova_senha.html', token=token)

# ---------------------------------------------------------
# 2. NAVEGAÇÃO E LOJA
# ---------------------------------------------------------

# 7. INDEX (HOME)
@app.route('/')
@app.route('/home')
def Index():

    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Busca os jogos gratuitos
    cursor.execute("SELECT * FROM jogos WHERE preco = 0 OR preco IS NULL ORDER BY id DESC")
    jogos = cursor.fetchall()
    
    meus_downloads = []
    if 'user_id' in session:
        cursor.execute("SELECT jogo_id FROM downloads WHERE utilizador_id = %s", (session['user_id'],))
        meus_downloads = [row['jogo_id'] for row in cursor.fetchall()]
    
    conn.close()
    
    return render_template('index.html', jogos=jogos, meus_downloads=meus_downloads)

# 8. LOJA
@app.route('/loja')
def Loja():
    busca = request.args.get('search', '').strip()
    ordem = request.args.get('sort', 'recentes')
    categoria_id = request.args.get('categoria', 'todas')
    
    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Construção da Query Base com JOIN para as Categorias
    # Usamos GROUP_CONCAT para o caso de um jogo ter mais que uma categoria
    sql_base = """
        SELECT j.*, GROUP_CONCAT(c.nome SEPARATOR ', ') as categoria_nome 
        FROM jogos j
        LEFT JOIN jogos_categorias jc ON j.id = jc.jogo_id
        LEFT JOIN categorias c ON jc.categoria_id = c.id
    """
    
    params = []
    condicoes = []

    # Filtro de Busca
    if busca:
        condicoes.append("j.titulo LIKE %s")
        params.append(f"%{busca}%")

    # Filtro de Categoria (Via tabela intermédia)
    if categoria_id != 'todas':
        condicoes.append("j.id IN (SELECT jogo_id FROM jogos_categorias WHERE categoria_id = %s)")
        params.append(categoria_id)

    if condicoes:
        sql_base += " WHERE " + " AND ".join(condicoes)

    # Agrupamento necessário por causa do GROUP_CONCAT
    sql_base += " GROUP BY j.id"

    # 2. Lógica de Ordenação
    if ordem == 'vendas':
        sql_base += " ORDER BY j.vendas_count DESC"
    elif ordem == 'downloads':
        # Subquery para contar downloads mantendo os nomes das categorias
        sql_base = f"""
            SELECT res.*, (SELECT COUNT(*) FROM downloads d WHERE d.jogo_id = res.id) as total_dl 
            FROM ({sql_base}) as res 
            ORDER BY total_dl DESC
        """
    elif ordem == 'preco_baixo':
        sql_base += " ORDER BY j.preco ASC"
    elif ordem == 'preco_alto':
        sql_base += " ORDER BY j.preco DESC"
    else:
        sql_base += " ORDER BY j.id DESC"

    cursor.execute(sql_base, tuple(params))
    jogos = cursor.fetchall()

    # 3. Injetar Comentários (O teu código original estava bom, mantemos aqui)
    for jogo in jogos:
        cursor.execute("""
            SELECT a.comentario, u.nome_utilizador 
            FROM avaliacoes a 
            JOIN utilizadores u ON a.utilizador_id = u.id 
            WHERE a.jogo_id = %s 
            ORDER BY a.data_avaliacao DESC LIMIT 2
        """, (jogo['id'],))
        jogo['comentarios'] = cursor.fetchall()

    # 4. Buscar Categorias para o Dropdown
    cursor.execute("SELECT * FROM categorias ORDER BY nome ASC")
    categorias = cursor.fetchall()

    # 5. Verificar jogos adquiridos
    meus_downloads = []
    if 'user_id' in session:
        cursor.execute("SELECT jogo_id FROM downloads WHERE utilizador_id = %s", (session['user_id'],))
        meus_downloads = [d['jogo_id'] for d in cursor.fetchall()]
    
    conn.close()
    
    return render_template('loja.html', 
                           jogos=jogos, 
                           busca=busca, 
                           categorias=categorias, 
                           meus_downloads=meus_downloads)
# 9. DETALHES DO JOGO
@app.route('/jogo/<int:id>')
def DetalhesJogo(id):
    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT j.*, u.nome_utilizador as criador 
        FROM jogos j LEFT JOIN utilizadores u ON j.utilizador_id = u.id 
        WHERE j.id = %s
    """, (id,))
    jogo = cursor.fetchone()

    if not jogo:
        conn.close()
        flash("Jogo não encontrado!", "error")
        return redirect(url_for('Loja'))

    # Carregar comentários para o template
    cursor.execute("""
        SELECT a.*, u.nome_utilizador FROM avaliacoes a 
        JOIN utilizadores u ON a.utilizador_id = u.id 
        WHERE a.jogo_id = %s ORDER BY a.data_avaliacao DESC
    """, (id,))
    jogo['comentarios'] = cursor.fetchall()
    conn.close()
    return render_template('jogo_detalhes.html', jogo=jogo)

# 10. AVALIAR JOGO (COMENTÁRIOS)
@app.route('/avaliar/<int:id_jogo>', methods=['POST'])
def Avaliar(id_jogo):
    if 'user_id' not in session: return redirect(url_for('Entrar'))
    comentario = request.form.get('comentario', '').strip()
    
    if comentario:
        try:
            conn = DB_Ligar()
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO avaliacoes (utilizador_id, jogo_id, comentario, data_avaliacao)
                VALUES (%s, %s, %s, NOW())
            """, (session['user_id'], id_jogo, comentario))
            conn.commit()
            flash("Obrigado pela tua avaliação!", "success")
        except Exception as e:
            flash(f"Erro ao avaliar: {e}", "error")
        finally:
            conn.close()
    else:
        flash("O comentário não pode estar vazio.", "warning")
        
    return redirect(url_for('DetalhesJogo', id=id_jogo))

# ---------------------------------------------------------
# 3. CARRINHO E BIBLIOTECA
# ---------------------------------------------------------

# 11. VER O CARRINHO
@app.route('/carrinho')
def VerCarrinho():
    carrinho = session.get('carrinho', [])
    jogos_no_carrinho = []
    
    # Inicializamos os 3 acumuladores
    total_final = 0
    total_base_acumulado = 0
    total_iva_acumulado = 0
    
    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)
    
    for id_jogo in carrinho:
        cursor.execute("SELECT * FROM jogos WHERE id = %s", (id_jogo,))
        jogo = cursor.fetchone()
        
        if jogo:
            # Preço que o utilizador realmente vai pagar (já com desconto aplicado)
            preco_pago = calcular_preco_atual(jogo)
            
            # Cálculos individuais para a linha da tabela
            base_un = preco_pago / 1.23
            iva_un = preco_pago - base_un
            
            # Dados para as colunas da tabela
            jogo['preco_base_sem_desconto'] = float(jogo['preco']) / 1.23
            jogo['base_unitario'] = base_un
            jogo['iva_unitario'] = iva_un
            jogo['total_unitario'] = preco_pago
            
            jogos_no_carrinho.append(jogo)
            
            # Somar aos acumuladores globais
            total_final += preco_pago
            total_base_acumulado += base_un
            total_iva_acumulado += iva_un
            
    conn.close()
    
    # Enviamos as 3 variáveis para o HTML
    return render_template('carrinho.html', 
                           jogos=jogos_no_carrinho, 
                           total=total_final, 
                           total_base=total_base_acumulado, 
                           total_iva=total_iva_acumulado)

# 12. ADICIONAR AO CARRINHO
@app.route('/carrinho/adicionar/<int:id_jogo>', methods=['GET', 'POST'])
def AdicionarCarrinho(id_jogo):
    # Inicializa o carrinho se não existir
    if 'carrinho' not in session:
        session['carrinho'] = []
    
    # Criamos uma cópia da lista para garantir que o Flask deteta a mudança
    carrinho = list(session['carrinho'])
    
    if id_jogo not in carrinho:
        carrinho.append(id_jogo)
        session['carrinho'] = carrinho
        session.modified = True 
        flash("Jogo adicionado ao carrinho com sucesso!", "success")
    else:
        flash("Esse jogo já está no teu carrinho.", "info")
    
    return redirect(request.referrer or url_for('Loja'))

# 13. REMOVER DO CARRINHO
@app.route('/carrinho/remover/<int:id_jogo>')
def RemoverDoCarrinho(id_jogo):
    carrinho = session.get('carrinho', [])
    if id_jogo in carrinho:
        carrinho.remove(id_jogo)
        session['carrinho'] = carrinho
        flash("Jogo removido do carrinho.", "info")
    return redirect(url_for('VerCarrinho'))

# 14. FINALIZAR A COMPRA
@app.route('/finalizar-compra', methods=['GET', 'POST'])
def FinalizarCompra():
    if 'user_id' not in session or not session.get('carrinho'):
        return redirect(url_for('Loja'))

    user_id = session['user_id']
    ids_carrinho = session.get('carrinho')
    
    try:
        conn = DB_Ligar()
        cursor = conn.cursor(dictionary=True)
        
        # --- BUSCAR DETALHES COMPLETOS (Incluindo dados de promoção) ---
        format_strings = ','.join(['%s'] * len(ids_carrinho))
        # Adicionei os campos: desconto_percentual, promo_inicio, promo_fim
        cursor.execute(f"""
            SELECT id, titulo, preco, desconto_percentual, promo_inicio, promo_fim 
            FROM jogos 
            WHERE id IN ({format_strings})
        """, tuple(ids_carrinho))
        lista_jogos_recibo = cursor.fetchall()

        agora = datetime.now()
        
        # 1. Registar a Compra Principal
        cursor.execute("""
            INSERT INTO compras (utilizador_id, data_pagamento, hora_pagamento) 
            VALUES (%s, %s, %s)
        """, (user_id, agora.date(), agora.time()))
        compra_id = cursor.lastrowid

        # 2. Registar cada item e libertar para download
        for jogo in lista_jogos_recibo:
            jogo_id = jogo['id']
            cursor.execute("INSERT INTO itens_compra (compra_id, jogo_id) VALUES (%s, %s)", (compra_id, jogo_id))
            cursor.execute("UPDATE jogos SET vendas_count = vendas_count + 1 WHERE id = %s", (jogo_id,))
            cursor.execute("""
                INSERT INTO downloads (utilizador_id, jogo_id, data_download, hora_download) 
                VALUES (%s, %s, %s, %s)
            """, (user_id, jogo_id, agora.date(), agora.time()))

        conn.commit()
        
        # --- CHAMADA DA FUNÇÃO DE EMAIL (Passando a lista completa) ---
        # Certifica-te que 'user_email' está na session!
        enviar_recibo(mail, session.get('user_email'), session.get('user_name'), lista_jogos_recibo, fatura_id=compra_id)
        
        conn.close()
        
        session.pop('carrinho', None)
        flash("Pagamento confirmado! O recibo foi enviado para o teu e-mail.", "success")
        return redirect(url_for('Biblioteca'))

    except Exception as e:
        print(f"Erro ao finalizar: {e}")
        flash("Ocorreu um erro ao processar a compra.", "danger")
        return redirect(url_for('VerCarrinho'))

# 15. BIBLIOTECA
@app.route('/biblioteca')
def Biblioteca():
    if 'user_id' not in session: 
        return redirect(url_for('Entrar'))
    
    busca = request.args.get('search', '')
    
    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)
    
    # Query com JOIN para buscar nomes das categorias concatenados
    sql = """
        SELECT j.*, 
               MAX(d.data_download) as data_download,
               GROUP_CONCAT(DISTINCT c.nome SEPARATOR ', ') as categoria_nome
        FROM jogos j 
        INNER JOIN downloads d ON j.id = d.jogo_id 
        LEFT JOIN jogos_categorias jc ON j.id = jc.jogo_id
        LEFT JOIN categorias c ON jc.categoria_id = c.id
        WHERE d.utilizador_id = %s
    """
    params = [session['user_id']]
    
    if busca:
        sql += " AND j.titulo LIKE %s"
        params.append(f"%{busca}%")
        
    sql += " GROUP BY j.id ORDER BY data_download DESC"
    
    cursor.execute(sql, tuple(params))
    meus_jogos = cursor.fetchall()
    
    for jogo in meus_jogos:
        # Verifica se o utilizador já avaliou este jogo
        cursor.execute("SELECT * FROM avaliacoes WHERE utilizador_id = %s AND jogo_id = %s", 
                       (session['user_id'], jogo['id']))
        jogo['minha_avaliacao'] = cursor.fetchone()
        
    conn.close()
    
    return render_template('biblioteca.html', jogos=meus_jogos, busca=busca)

# 16. REMOVER DA BIBLIOTECA
@app.route('/biblioteca/remover/<int:id_jogo>')
def RemoverDaBiblioteca(id_jogo):
    if 'user_id' not in session: return redirect(url_for('Entrar'))
    try:
        conn = DB_Ligar()
        cursor = conn.cursor()
        cursor.execute("DELETE FROM downloads WHERE utilizador_id = %s AND jogo_id = %s", 
                       (session['user_id'], id_jogo))
        conn.commit()
        flash("Jogo removido da biblioteca.", "info")
    except Exception as e:
        flash(f"Erro: {e}", "error")
    finally:
        conn.close()
    return redirect(url_for('Biblioteca'))

# ---------------------------------------------------------
# 4. PERFIL E CONFIGURAÇÕES
# ---------------------------------------------------------

@app.context_processor
def inject_notifications():
    if session.get('user_id'):
        conn = DB_Ligar()
        cursor = conn.cursor(dictionary=True)
        # Conta apenas as não lidas para o badge
        cursor.execute("SELECT COUNT(*) as total FROM notificacoes WHERE utilizador_id = %s AND lida = FALSE", (session['user_id'],))
        count = cursor.fetchone()['total']
        conn.close()
        return dict(notificacoes_count=count)
    return dict(notificacoes_count=0)

# ROTA PARA VER A LISTA DE NOTIFICAÇÕES
@app.route('/notificacoes')
def VerNotificacoes():
    uid = session.get('user_id')
    if not uid: return redirect(url_for('Entrar'))

    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)
    
    cursor.execute("SELECT * FROM notificacoes WHERE utilizador_id = %s ORDER BY data_envio DESC", (uid,))
    notificacoes_db = cursor.fetchall()
    conn.close()

    lista_final = notificacoes_db if notificacoes_db is not None else []

    return render_template('notificacoes.html', notificacoes=lista_final)

# ROTA PARA MARCAR COMO LIDA INDIVIDUALMENTE
@app.route('/notificacao/lida/<int:id>')
def MarcarLida(id):
    if not session.get('user_id'): return redirect(url_for('Entrar'))
    
    conn = DB_Ligar()
    cursor = conn.cursor()
    cursor.execute("UPDATE notificacoes SET lida = TRUE WHERE id = %s AND utilizador_id = %s", (id, session['user_id']))
    conn.commit()
    conn.close()
    return redirect(url_for('VerNotificacoes'))

# ROTA PARA ENVIAR RESPOSTA À ADMINISTRAÇÃO
@app.route('/notificacao/responder', methods=['POST'])
def ResponderNotificacao():
    if not session.get('user_id'): return redirect(url_for('Entrar'))

    msg_user = request.form.get('mensagem_resposta')
    notif_id = request.form.get('notificacao_id')
    user_nome = session.get('user_name')
    user_email = session.get('user_email')

    try:
        msg = Message(f"RESPOSTA APOIO: Notificação #{notif_id}", 
                      sender=app.config['MAIL_USERNAME'],
                      recipients=[ADMIN_EMAIL])
        
        msg.body = f"O utilizador {user_nome} ({user_email}) respondeu à notificação #{notif_id}:\n\n{msg_user}"
        mail.send(msg)
        
        flash("A tua resposta foi enviada com sucesso para a equipa de administração!", "success")
    except Exception as e:
        flash(f"Erro ao enviar resposta: {e}", "error")

    return redirect(url_for('VerNotificacoes'))

# --- SISTEMA SOCIAL E AMIZADES ---

# 1. ROTA PRINCIPAL SOCIAL
@app.route('/social')
def Social():
    if not session.get('user_id'): return redirect(url_for('Entrar'))
    uid = session['user_id']
    
    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)
    
    # Buscar Amigos Aceites
    cursor.execute("""
        SELECT u.id, u.nome_utilizador, u.data_registo FROM utilizadores u
        JOIN amizades a ON (u.id = a.id_requisitante OR u.id = a.id_aceitante)
        WHERE (a.id_requisitante = %s OR a.id_aceitante = %s) 
        AND a.estado = 'aceite' AND u.id != %s
    """, (uid, uid, uid))
    amigos = cursor.fetchall()
    
    # Buscar Pedidos Pendentes
    cursor.execute("""
        SELECT a.id as id_amizade, u.nome_utilizador FROM amizades a
        JOIN utilizadores u ON a.id_requisitante = u.id
        WHERE a.id_aceitante = %s AND a.estado = 'pendente'
    """, (uid,))
    pendentes = cursor.fetchall()
    
    conn.close()
    return render_template('social.html', amigos=amigos, pendentes=pendentes)

# 2. ROTA DE PESQUISA 
@app.route('/social/procurar')
def ProcurarAmigos():
    query = request.args.get('query', '')
    uid_sessao = session.get('user_id')
    
    if not query:
        return redirect(url_for('Social'))

    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT u.id, u.nome_utilizador, u.data_registo, 
               a.estado as estado_amizade, a.id_requisitante
        FROM utilizadores u
        LEFT JOIN amizades a ON (
            (a.id_requisitante = %s AND a.id_aceitante = u.id) OR 
            (a.id_aceitante = %s AND a.id_requisitante = u.id)
        )
        WHERE u.nome_utilizador LIKE %s AND u.id != %s
    """, (uid_sessao, uid_sessao, f"%{query}%", uid_sessao))
    
    resultados = cursor.fetchall()
    conn.close()

    return render_template('procurar_social.html', users=resultados, query=query)

# --- FUNÇÃO DE ENVIO DE EMAIL (Social) ---
@app.route('/social/adicionar/<int:id_alvo>')
def AdicionarAmigo(id_alvo):
    uid_envia = session.get('user_id')
    if not uid_envia: return redirect(url_for('Entrar'))
    
    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)
    
    try:
        cursor.execute("SELECT nome_utilizador FROM utilizadores WHERE id = %s", (uid_envia,))
        user_remetente = cursor.fetchone()
        
        if not user_remetente:
            return redirect(url_for('Social'))
            
        nome_real = user_remetente['nome_utilizador']

        # 2. INSERIR AMIZADE
        cursor.execute("INSERT IGNORE INTO amizades (id_requisitante, id_aceitante, estado) VALUES (%s, %s, 'pendente')", (uid_envia, id_alvo))
        
        if cursor.rowcount > 0:
            # 3. INSERIR NOTIFICAÇÃO 
            cursor.execute("""
                INSERT INTO notificacoes (utilizador_id, titulo, mensagem, lida) 
                VALUES (%s, 'Amizade', %s, FALSE)
            """, (id_alvo, f"{nome_real} enviou-te um pedido!"))

            # 4. ENVIAR EMAIL
            cursor.execute("SELECT email FROM utilizadores WHERE id = %s", (id_alvo,))
            alvo = cursor.fetchone()
            
            if alvo and alvo['email']:
                enviar_notificacao_amizade(mail, alvo['email'], nome_real)
            
            conn.commit()
            flash(f"Pedido enviado para o utilizador!", "success")
            
    except Exception as e:
        print(f"Erro ao processar: {e}")
    finally:
        conn.close()
    return redirect(url_for('Social'))
# 4. GERIR PEDIDOS (ACEITAR/RECUSAR)
@app.route('/social/gerir/<int:id>/<acao>')
def GerirAmizade(id, acao):
    if not session.get('user_id'): return redirect(url_for('Entrar'))
    
    conn = DB_Ligar()
    cursor = conn.cursor()
    
    if acao == 'aceitar':
        cursor.execute("UPDATE amizades SET estado = 'aceite' WHERE id = %s", (id,))
        flash("Amizade aceite! Agora são amigos.", "success")
    else:
        cursor.execute("DELETE FROM amizades WHERE id = %s", (id,))
        flash("Pedido removido.", "info")
        
    conn.commit()
    conn.close()
    return redirect(url_for('Social'))

@app.context_processor
def inject_social_info():
    if session.get('user_id'):
        conn = DB_Ligar()
        cursor = conn.cursor()
        # Conta pedidos de amizade onde o user é o aceitante e está pendente
        cursor.execute("""
            SELECT COUNT(*) FROM amizades 
            WHERE id_aceitante = %s AND estado = 'pendente'
        """, (session['user_id'],))
        total_pedidos = cursor.fetchone()[0]
        conn.close()
        return dict(total_pedidos_pendentes=total_pedidos)
    return dict(total_pedidos_pendentes=0)

# Rota social
@app.route('/social/chat/<int:amigo_id>')
def ChatAmigo(amigo_id):
    if not session.get('user_id'): return redirect(url_for('Entrar'))
    uid = session['user_id']

    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)

    # Buscar dados do amigo para o cabeçalho
    cursor.execute("SELECT id, nome_utilizador FROM utilizadores WHERE id = %s", (amigo_id,))
    amigo = cursor.fetchone()

    # Buscar o histórico de mensagens entre os dois
    cursor.execute("""
        SELECT * FROM mensagens 
        WHERE (id_remetente = %s AND id_recetor = %s) 
           OR (id_remetente = %s AND id_recetor = %s)
        ORDER BY data_envio ASC
    """, (uid, amigo_id, amigo_id, uid))
    historico = cursor.fetchall()
    
    conn.close()
    return render_template('chat.html', amigo=amigo, historico=historico)

# Rota para enviar mensagem (via AJAX/Form)
@app.route('/social/enviar_mensagem', methods=['POST'])
def EnviarMensagem():
    uid = session.get('user_id')
    amigo_id = request.form.get('amigo_id')
    texto = request.form.get('mensagem')

    if uid and texto:
        conn = DB_Ligar()
        cursor = conn.cursor()
        cursor.execute("INSERT INTO mensagens (id_remetente, id_recetor, mensagem) VALUES (%s, %s, %s)", 
                       (uid, amigo_id, texto))
        conn.commit()
        conn.close()
    
    return redirect(url_for('ChatAmigo', amigo_id=amigo_id))
# 17. PERFIL
@app.route('/perfil')
def Perfil():
    if 'user_id' not in session: return redirect(url_for('Entrar'))
    
    user_id = session['user_id']
    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)
    
    # 1. Dados do Utilizador
    cursor.execute("SELECT * FROM utilizadores WHERE id = %s", (user_id,))
    user = cursor.fetchone()
    
    # 2. Conta quantos jogos únicos este utilizador tem na tabela downloads
    # Se um jogo for removido da tabela downloads, este número desce automaticamente.
    cursor.execute("SELECT COUNT(id) as total FROM downloads WHERE utilizador_id = %s", (user_id,))
    res_contagem = cursor.fetchone()
    num_jogos = res_contagem['total'] if res_contagem else 0
    
    # 3. Investimento total (Soma apenas os jogos que foram comprados e estão no histórico)
    cursor.execute("""
        SELECT SUM(j.preco) as total FROM jogos j
        INNER JOIN itens_compra ic ON j.id = ic.jogo_id
        INNER JOIN compras c ON ic.compra_id = c.id
        WHERE c.utilizador_id = %s
    """, (user_id,))
    res_inv = cursor.fetchone()
    investimento = res_inv['total'] if res_inv and res_inv['total'] else 0.0
    
    # 4. Histórico de compras
    cursor.execute("""
        SELECT j.titulo, j.preco, c.data_pagamento FROM jogos j
        INNER JOIN itens_compra ic ON j.id = ic.jogo_id
        INNER JOIN compras c ON ic.compra_id = c.id
        WHERE c.utilizador_id = %s ORDER BY c.data_pagamento DESC
    """, (user_id,))
    historico = cursor.fetchall()
    
    conn.close()

    return render_template('perfil.html', 
                           user=user, 
                           num_jogos=num_jogos,
                           investimento=investimento, 
                           historico=historico)

# 18. ALTERAR NOME
@app.route('/perfil/alterar-nome', methods=['POST'])
def AlterarNome():
    if 'user_id' not in session: return redirect(url_for('Entrar'))
    
    novo_nome = request.form.get('novo_nome') 
    email_user = session.get('user_email')
    user_id = session.get('user_id')

    if novo_nome and len(novo_nome.strip()) >= 3:
        try:
            conn = DB_Ligar()
            cursor = conn.cursor()
            cursor.execute("UPDATE utilizadores SET nome_utilizador = %s WHERE id = %s", (novo_nome, user_id))
            conn.commit()
            conn.close()

            session['user_name'] = novo_nome
            
            # Envio do email (dentro de um try para não travar se o SMTP falhar)
            try:
                enviar_email_sistema(
                    mail, 
                    "Segurança: Nome de Utilizador Alterado", 
                    email_user, 
                    'emails/notificacao_perfil.html', 
                    nome=novo_nome,
                    data_alteracao=datetime.now().strftime('%d/%m/%Y %H:%M')
                )
            except Exception as e_mail:
                print(f"Erro ao enviar email: {e_mail}")

            flash("Nome atualizado com sucesso!", "success")
        except Exception as e:
            print(f"Erro na BD: {e}")
            flash("Erro ao atualizar na base de dados.", "error")
    else:
        flash("O nome deve ter pelo menos 3 caracteres.", "warning")
            
    return redirect(url_for('Perfil'))

# 19. ALTERAR SENHA (PERFIL)
@app.route('/perfil/alterar-senha', methods=['POST'])
def AlterarSenha():
    if 'user_id' not in session: return redirect(url_for('Entrar'))
    nova_senha = request.form.get('nova_senha')
    if nova_senha:
        senha_hash = generate_password_hash(nova_senha)
        conn = DB_Ligar()
        cursor = conn.cursor()
        cursor.execute("UPDATE utilizadores SET palavra_passe = %s WHERE id = %s", (senha_hash, session['user_id']))
        conn.commit()
        conn.close()
        enviar_email_sistema(mail, "Senha Alterada", session['user_email'], 'emails/senha_alterada.html', nome=session['user_name'])
        flash("Senha atualizada!", "success")
    return redirect(url_for('Perfil'))

# 20. ELIMINAR CONTA
@app.route('/perfil/eliminar-conta', methods=['POST'])
def EliminarConta():
    if 'user_id' not in session: return redirect(url_for('Entrar'))
    conn = DB_Ligar()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM utilizadores WHERE id = %s", (session['user_id'],))
    conn.commit()
    conn.close()
    session.clear()
    flash("Conta eliminada permanentemente.", "info")
    return redirect(url_for('Registar'))

# ---------------------------------------------------------
# 5. ADMINISTRAÇÃO E SUPORTE
# ---------------------------------------------------------

# 21. ADMIN PANEL (Atualizado com JOIN para o Nick)
@app.route('/admin')
def Admin():
    if session.get('user_email') != ADMIN_EMAIL:
        abort(403)
    
    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)

    cursor.execute("""
        SELECT j.*, u.nome_utilizador 
        FROM jogos j
        JOIN utilizadores u ON j.utilizador_id = u.id
        ORDER BY j.id DESC
    """)
    jogos = cursor.fetchall()

    cursor.execute("SELECT id, nome_utilizador, email, data_registo FROM utilizadores")
    users = cursor.fetchall()
    conn.close()
    
    return render_template('admin.html', jogos=jogos, users=users)

# 22. ADMIN — PÁGINA DE DECISÃO
@app.route('/admin/decisao-jogo/<int:id>')
def AdminApagarJogo(id): 
    if session.get('user_email') != ADMIN_EMAIL: abort(403)
    
    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("""
        SELECT j.*, u.email as email_dono 
        FROM jogos j 
        JOIN utilizadores u ON j.utilizador_id = u.id 
        WHERE j.id = %s
    """, (id,))
    jogo = cursor.fetchone()
    conn.close()
    
    if not jogo:
        flash("Jogo não encontrado.", "error")
        return redirect(url_for('Admin'))
        
    return render_template('admin_decisao.html', jogo=jogo)

# 22.1 ADMIN — PROCESSAR ELIMINAÇÃO E EMAIL
@app.route('/admin/confirmar-acao/<int:id>', methods=['POST'])
def AdminConfirmarAcao(id):
    if session.get('user_email') != ADMIN_EMAIL:
        abort(403)

    acao_escolhida = request.form.get('motivo')
    observacao_admin = request.form.get('detalhes') 
    email_dono = request.form.get('email_dono')
    titulo_jogo = request.form.get('titulo_jogo')

    try:
        conn = DB_Ligar()
        cursor = conn.cursor(dictionary=True)

        cursor.execute("SELECT utilizador_id FROM jogos WHERE id = %s", (id,))
        resultado_autor = cursor.fetchone()
        id_autor = resultado_autor['utilizador_id'] if resultado_autor else None

        # 2. Lógica de Moderação/Eliminação
        if acao_escolhida in ['eliminado', 'banido']:
            cursor.execute("DELETE FROM downloads WHERE jogo_id = %s", (id,))
            cursor.execute("DELETE FROM itens_compra WHERE jogo_id = %s", (id,))
            cursor.execute("DELETE FROM avaliacoes WHERE jogo_id = %s", (id,))
            cursor.execute("DELETE FROM jogos_categorias WHERE jogo_id = %s", (id,))
            cursor.execute("DELETE FROM jogos WHERE id = %s", (id,))
            msg_status = "Removido Permanentemente"
        else:
            cursor.execute("UPDATE jogos SET estado = %s WHERE id = %s", (acao_escolhida, id))
            msg_status = acao_escolhida.capitalize()

        # 3. ENVIO DO EMAIL
        msg = Message(f"Yuzaki Export - Notificação: {titulo_jogo}", recipients=[email_dono])
        msg.html = render_template('emails/notificacao_admin.html', 
                                   titulo_jogo=titulo_jogo, 
                                   motivo=msg_status, 
                                   detalhes=observacao_admin)
        mail.send(msg)

        # 4. CRIAR NOTIFICAÇÃO NO SITE
        if id_autor:
            cursor.execute("""
                INSERT INTO notificacoes (utilizador_id, titulo, mensagem) 
                VALUES (%s, %s, %s)
            """, (id_autor, f"Moderação: {titulo_jogo}", f"O seu jogo foi marcado como {msg_status}. Motivo: {observacao_admin}"))

        conn.commit()
        flash("Ação executada, e-mail enviado e notificação registada!", "success")

    except Exception as e:
        flash(f"Erro: {e}", "error")
    finally:
        conn.close()

    return redirect(url_for('Admin'))

# ROTA 1: Carregar página de decisão do utilizador
@app.route('/admin/decisao-utilizador/<int:id>')
def AdminDecisaoUser(id):
    if session.get('user_email') != ADMIN_EMAIL: abort(403)
    
    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)
    cursor.execute("SELECT id, nome_utilizador, email FROM utilizadores WHERE id = %s", (id,))
    u = cursor.fetchone()
    conn.close()
    
    return render_template('admin_decisao_user.html', u=u)

# ROTA 2: Processar a ação (Banir ou Suspender)
@app.route('/admin/confirmar-acao-user/<int:id>', methods=['POST'])
def AdminConfirmarAcaoUser(id):
    if session.get('user_email') != ADMIN_EMAIL: abort(403)

    acao = request.form.get('motivo')
    detalhes = request.form.get('detalhes')
    email_user = request.form.get('email_user')
    nome_user = request.form.get('nome_user')

    try:
        conn = DB_Ligar()
        cursor = conn.cursor()

        if acao == 'banido':
            cursor.execute("DELETE FROM jogos WHERE utilizador_id = %s", (id,))
            cursor.execute("DELETE FROM notificacoes WHERE utilizador_id = %s", (id,))
            cursor.execute("DELETE FROM utilizadores WHERE id = %s", (id,))
            msg_flash = f"Utilizador {nome_user} banido com sucesso."
        else:
            cursor.execute("UPDATE utilizadores SET estado = %s WHERE id = %s", (acao, id))
            cursor.execute("""
                INSERT INTO notificacoes (utilizador_id, titulo, mensagem) 
                VALUES (%s, %s, %s)
            """, (id, "Ação Disciplinar na Conta", f"A sua conta foi marcada como: {acao}. Motivo: {detalhes}"))
            msg_flash = f"Estado do utilizador {nome_user} atualizado para {acao}."

        conn.commit()

        msg = Message(f"Yuzaki Export — Atualização de Conta", recipients=[email_user])
        msg.html = render_template('emails/notificacao_admin.html', 
                                   titulo_jogo="Sua Conta", 
                                   motivo=acao.upper(), 
                                   detalhes=detalhes)
        mail.send(msg)
        
        flash(msg_flash, "success")
    except Exception as e:
        flash(f"Erro: {e}", "error")
    finally:
        conn.close()

    return redirect(url_for('Admin'))

@app.route('/publicar', methods=['GET', 'POST'])
def Publicar():
    if 'user_id' not in session: 
        flash("Precisas de ter conta para publicar projetos.", "warning")
        return redirect(url_for('Entrar'))

    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)

    if request.method == 'POST':
        titulo = request.form.get('titulo', '').strip()
        descricao = request.form.get('descricao', '').strip()
        preco = request.form.get('preco', 0.00)
        categoria_id = request.form.get('categoria_id')
        ficheiro = request.files.get('arquivo')

        if not titulo or not ficheiro or not categoria_id:
            flash("Erro: Título, Ficheiro e Categoria são obrigatórios!", "danger")
            return redirect(url_for('Publicar'))

        try:
            extensao = os.path.splitext(ficheiro.filename)[1].lower()
            nome_seguro = f"YE_{secrets.token_hex(8)}{extensao}"
            
            if not os.path.exists(app.config['UPLOAD_FOLDER']):
                os.makedirs(app.config['UPLOAD_FOLDER'])
                
            caminho_completo = os.path.join(app.config['UPLOAD_FOLDER'], nome_seguro)
            ficheiro.save(caminho_completo)

            sql_jogo = """
                INSERT INTO jogos (
                    titulo, descricao, preco, imagem_url, 
                    utilizador_id, data_lancamento, data_criacao, hora_criacao
                ) VALUES (%s, %s, %s, %s, %s, CURDATE(), CURDATE(), CURTIME())
            """
            cursor.execute(sql_jogo, (titulo, descricao, preco, nome_seguro, session['user_id']))
            
            novo_jogo_id = cursor.lastrowid

            sql_cat = "INSERT INTO jogos_categorias (jogo_id, categoria_id) VALUES (%s, %s)"
            cursor.execute(sql_cat, (novo_jogo_id, categoria_id))

            conn.commit()
            
            flash(f"🚀 '{titulo}' foi lançado com sucesso no Mercado Yuzaki!", "success")
            return redirect(url_for('Loja'))

        except Exception as e:
            if conn: conn.rollback()
            print(f"ERRO DE PUBLICAÇÃO: {e}") # Log para o terminal do dev
            flash("Ocorreu um erro técnico ao processar o teu ficheiro.", "error")
            return redirect(url_for('Publicar'))
        finally:
            if conn: conn.close()

    # --- LÓGICA DO MÉTODO GET (Exibir a página) ---
    try:
        cursor.execute("SELECT * FROM categorias ORDER BY nome ASC")
        lista_categorias = cursor.fetchall()
        return render_template('publicar.html', categorias=lista_categorias)
    except Exception as e:
        flash("Erro ao carregar sistema de categorias.", "error")
        return redirect(url_for('Index'))
    finally:
        if conn: conn.close()

# 25. CONTACTO SUPORTE
@app.route('/contacto', methods=['GET', 'POST'])
def Contacto():
    if 'user_id' not in session: return redirect(url_for('Entrar'))
    if request.method == 'POST':
        if enviar_contacto_suporte(mail, session.get('user_name'), session.get('user_email'), 
                                    request.form.get('assunto'), request.form.get('mensagem')):
            flash("Mensagem enviada com sucesso!", "success")
        return redirect(url_for('Contacto'))
    return render_template('contacto.html')

# 26. Painel de Desenvolvedor
@app.route('/painel-desenvolvedor')
def DeveloperPanel():
    # 1. Bloqueio de segurança
    if 'user_id' not in session:
        return redirect(url_for('Entrar'))
    
    user_id = session['user_id']
    
    try:
        conn = DB_Ligar()
        cursor = conn.cursor(dictionary=True)

        # 2. Buscar dados do utilizador (Perfil)
        cursor.execute("SELECT * FROM utilizadores WHERE id = %s", (user_id,))
        user = cursor.fetchone()

        sql_jogos = """
            SELECT j.*, GROUP_CONCAT(c.nome SEPARATOR ', ') as categoria_nome
            FROM jogos j
            LEFT JOIN jogos_categorias jc ON j.id = jc.jogo_id
            LEFT JOIN categorias c ON jc.categoria_id = c.id
            WHERE j.utilizador_id = %s
            GROUP BY j.id
            ORDER BY j.id DESC
        """
        cursor.execute(sql_jogos, (user_id,))
        jogos_criados = cursor.fetchall()

        # 4. Cálculos Financeiros
        total_vendas_count = 0
        receita_bruta_total = 0.0

        for jogo in jogos_criados:
            vendas = jogo.get('vendas_count') or 0
            preco = float(jogo.get('preco') or 0.0)
            
            total_vendas_count += vendas
            receita_bruta_total += (vendas * preco)

        # Divisão 80/20 da Yuzaki Export
        saldo_dev = receita_bruta_total * 0.80
        taxa_yuzaki = receita_bruta_total * 0.20

        conn.close()

        return render_template('desenvolvedor_painel.html', 
                               user=user,
                               jogos=jogos_criados,
                               total_vendas=total_vendas_count,
                               saldo_dev=saldo_dev,
                               taxa_yuzaki=taxa_yuzaki)

    except Exception as e:
        print(f"ERRO CRÍTICO NO PAINEL: {e}")
        try: conn.close()
        except: pass
        
        flash(f"Erro ao carregar o painel: {e}", "error")
        return redirect(url_for('Perfil'))
    
# Rota para Gerir o Jogo (Edição, Promoção e Eliminação)
@app.route('/dev-acao/<int:id>', methods=['GET', 'POST'])
def DevAcao(id):
    if 'user_id' not in session:
        return redirect(url_for('Entrar'))
    
    user_id = session['user_id']
    conn = DB_Ligar()
    cursor = conn.cursor(dictionary=True)

    sql_jogo = """
        SELECT j.*, jc.categoria_id 
        FROM jogos j 
        LEFT JOIN jogos_categorias jc ON j.id = jc.jogo_id 
        WHERE j.id = %s AND j.utilizador_id = %s
    """
    cursor.execute(sql_jogo, (id, user_id))
    jogo = cursor.fetchone()

    if not jogo:
        conn.close()
        flash("Jogo não encontrado ou acesso negado.", "error")
        return redirect(url_for('DeveloperPanel'))

    if request.method == 'POST':
        # CASO 1: Eliminar o Jogo
        if 'confirmar_eliminar' in request.form:
            try:
                cursor.execute("DELETE FROM avaliacoes WHERE jogo_id = %s", (id,))
                cursor.execute("DELETE FROM jogos_categorias WHERE jogo_id = %s", (id,))
                cursor.execute("DELETE FROM jogos WHERE id = %s", (id,))
                conn.commit()
                flash("O jogo foi removido permanentemente.", "info")
                return redirect(url_for('DeveloperPanel'))
            except Exception as e:
                flash(f"Erro ao eliminar: {e}", "error")

        # CASO 2: Editar/Promover
        titulo = request.form.get('titulo')
        descricao = request.form.get('descricao')
        preco = request.form.get('preco')
        desconto = request.form.get('desconto', 0)
        data_ini = request.form.get('promo_inicio') or None
        data_fim = request.form.get('promo_fim') or None
        categoria_id = request.form.get('categoria_id')

        try:
            sql_update = """
                UPDATE jogos 
                SET titulo=%s, descricao=%s, preco=%s, 
                    desconto_percentual=%s, promo_inicio=%s, promo_fim=%s 
                WHERE id=%s
            """
            cursor.execute(sql_update, (titulo, descricao, preco, desconto, data_ini, data_fim, id))
    
            if categoria_id:
                cursor.execute("DELETE FROM jogos_categorias WHERE jogo_id = %s", (id,))
                cursor.execute("INSERT INTO jogos_categorias (jogo_id, categoria_id) VALUES (%s, %s)", (id, categoria_id))

            conn.commit()
            flash("Atualizações guardadas com sucesso!", "success")
            return redirect(url_for('DeveloperPanel'))
        except Exception as e:
            conn.rollback()
            flash(f"Erro ao atualizar dados: {e}", "error")

    cursor.execute("SELECT * FROM categorias ORDER BY nome ASC")
    categorias_lista = cursor.fetchall()

    conn.close()
    return render_template('dev_acao.html', jogo=jogo, categorias=categorias_lista)

# ---------------------------------------------------------
# 6. PÁGINAS GERAIS E ERROS
# ---------------------------------------------------------

# 26. AGRADECIMENTOS
@app.route('/agradecimentos')
def Agradecimentos():
    return render_template('agradecimentos.html')

# 27. PRIVACIDADE
@app.route('/privacidade')
def Privacidade():
    return render_template('privacity.html')

# 28. ERRO 404
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404

#29. ERRO 403
@app.errorhandler(403)
def access_forbidden(e):
    return render_template('403.html'), 403

@app.route('/teste-500')
def teste_500():
    return render_template('500.html'), 500

#30. ERRO 500
@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500



if __name__ == '__main__':
    app.run(debug=True)

