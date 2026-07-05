from flask import render_template
from flask_mail import Message
from datetime import datetime, date

# --- FUNÇÃO MESTRE PARA ENVIOS (UNIFICADA) ---
def enviar_email_sistema(mail, assunto, destinatario, template, **kwargs):
    try:
        msg = Message(assunto, recipients=[destinatario])
        msg.html = render_template(template, **kwargs)
        mail.send(msg)
        print(f"✅ Email enviado com sucesso para {destinatario}")
        return True
    except Exception as e:
        print(f"❌ ERRO CRÍTICO NO ENVIO DE EMAIL: {e}")
        return False

# --- FUNÇÕES ESPECÍFICAS ---

def enviar_recuperacao_senha(mail, email_destino, nome_user, link):
    return enviar_email_sistema(
        mail, 
        "Recuperação de Acesso | Yuzaki Export", 
        email_destino, 
        'emails/recuperar_senha.html', 
        nome=nome_user, link=link
    )

def enviar_notificacao_amizade(mail, email_destino, nome_requisitante):
    return enviar_email_sistema(
        mail, 
        f"Pedido de Amizade de {nome_requisitante}", 
        email_destino, 
        'emails/pedido_amizade.html', 
        nome_remetente=nome_requisitante
    )

def enviar_contacto_suporte(mail, user_nome, user_email, assunto_msg, mensagem_corpo):
    return enviar_email_sistema(
        mail,
        f"📩 [{assunto_msg}] Feedback de {user_nome}",
        "yuzakisama2007@gmail.com",
        'emails/contacto_admin.html',
        nome=user_nome, email=user_email, assunto=assunto_msg, mensagem=mensagem_corpo
    )

def enviar_recibo(mail, email_cliente, nome_cliente, lista_jogos, fatura_id=None):
    try:
        total_geral = 0
        total_base = 0
        total_iva = 0
        jogos_processados = []  
        hoje = date.today()

        for jogo in lista_jogos:
            preco_original = float(jogo.get('preco', 0) or 0)
            desconto = jogo.get('desconto_percentual', 0) or 0
            ini = jogo.get('promo_inicio')
            fim = jogo.get('promo_fim')
            preco_pago = preco_original

            if desconto > 0 and ini and fim:
                if isinstance(ini, str): ini = datetime.strptime(ini, '%Y-%m-%d').date()
                if isinstance(fim, str): fim = datetime.strptime(fim, '%Y-%m-%d').date()
                if ini <= hoje <= fim:
                    preco_pago = preco_original * (1 - (desconto / 100))

            base_jogo = preco_pago / 1.23
            iva_jogo = preco_pago - base_jogo
            total_geral += preco_pago
            total_base += base_jogo
            total_iva += iva_jogo

            jogos_processados.append({
                'titulo': jogo['titulo'],
                'preco_pago': preco_pago,
                'foi_promo': preco_pago < preco_original
            })

        num_fatura = fatura_id if fatura_id else datetime.now().strftime('%Y%m%d%H%M')
        data_atual = datetime.now().strftime('%d/%m/%Y %H:%M')

        return enviar_email_sistema(
            mail, "Recibo de Aquisição | Yuzaki Export", email_cliente,
            'emails/recibo.html',
            nome_cliente=nome_cliente, lista_jogos=jogos_processados,
            num_fatura=num_fatura, data_atual=data_atual,
            total_geral=round(total_geral, 2), total_base=round(total_base, 2),
            total_iva=round(total_iva, 2)
        )
    except Exception as e:
        print(f"❌ ERRO NO ENVIO DO RECIBO: {e}")
        return False
