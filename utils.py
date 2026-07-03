from flask import render_template
from flask_mail import Message
from datetime import datetime, date

def enviar_email_sistema(mail, assunto, destinatario, template, **kwargs):
    try:
        msg = Message(assunto, recipients=[destinatario])
        msg.html = render_template(template, **kwargs)
        mail.send(msg)
    except Exception as e:
        print(f"Erro ao enviar email de sistema: {e}")

def enviar_recibo(mail, email_cliente, nome_cliente, lista_jogos, fatura_id=None):
    try:
        total_geral = 0
        total_base = 0
        total_iva = 0
        jogos_processados = []  

        hoje = date.today()

        for jogo in lista_jogos:
            # 1. Determinar o preço real pago (Considerando Promoção)
            preco_original = float(jogo.get('preco', 0) or 0)
            desconto = jogo.get('desconto_percentual', 0) or 0
            ini = jogo.get('promo_inicio')
            fim = jogo.get('promo_fim')

            preco_pago = preco_original

            # Verificar se a promo está ativa
            if desconto > 0 and ini and fim:
                # Converter para date se vierem como string da BD
                if isinstance(ini, str): ini = datetime.strptime(ini, '%Y-%m-%d').date()
                if isinstance(fim, str): fim = datetime.strptime(fim, '%Y-%m-%d').date()
                
                if ini <= hoje <= fim:
                    preco_pago = preco_original * (1 - (desconto / 100))

            # 2. Extrair o IVA (O preço pago JÁ inclui IVA)
            # Base = Total / 1.23 | IVA = Total - Base
            base_jogo = preco_pago / 1.23
            iva_jogo = preco_pago - base_jogo

            # 3. Acumular totais
            total_geral += preco_pago
            total_base += base_jogo
            total_iva += iva_jogo

            # Criamos uma lista nova para o template com os valores calculados
            jogos_processados.append({
                'titulo': jogo['titulo'],
                'preco_pago': preco_pago,
                'foi_promo': preco_pago < preco_original
            })

        num_fatura = fatura_id if fatura_id else datetime.now().strftime('%Y%m%d%H%M')
        data_atual = datetime.now().strftime('%d/%m/%Y %H:%M')

        msg = Message("Recibo de Aquisição | Yuzaki Export", recipients=[email_cliente])
        
        # Passamos os 'jogos_processados' e os totais arredondados a 2 casas decimais
        msg.html = render_template('emails/recibo.html', 
                                   nome_cliente=nome_cliente, 
                                   lista_jogos=jogos_processados, 
                                   num_fatura=num_fatura, 
                                   data_atual=data_atual, 
                                   total_geral=round(total_geral, 2), 
                                   total_base=round(total_base, 2), 
                                   total_iva=round(total_iva, 2))
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erro no envio do recibo: {e}")
        return False

def enviar_contacto_suporte(mail, user_nome, user_email, assunto_msg, mensagem_corpo):
    try:
        msg = Message(subject=f"📩 [{assunto_msg}] Feedback de {user_nome}",
                      sender=("Yuzaki Export Suporte", "yuzakisama2007@gmail.com"),
                      recipients=["yuzakisama2007@gmail.com"])
        msg.html = render_template('emails/contacto_admin.html', nome=user_nome, 
                                   email=user_email, assunto=assunto_msg, mensagem=mensagem_corpo)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erro suporte: {e}")
        return False

def enviar_recuperacao_senha(mail, email_destino, nome_user, link):
    try:
        msg = Message("Recuperação de Acesso | Yuzaki Export", recipients=[email_destino])
        msg.html = render_template('emails/recuperar_senha.html', nome=nome_user, link=link)
        mail.send(msg)
        return True
    except Exception as e:
        print(f"Erro recuperação: {e}")
        return False

def enviar_email_sistema(mail, assunto, destinatario, template, **kwargs):
    try:
        msg = Message(assunto, recipients=[destinatario])
        # O erro indica que o Flask falha aqui
        msg.html = render_template(template, **kwargs)
        mail.send(msg)
        print(f"✅ Email enviado para {destinatario}")
    except Exception as e:
        # Mudamos para imprimir o erro completo e entender se é falta de ficheiro
        print(f"❌ ERRO REAL: {e}")

def enviar_notificacao_amizade(mail, email_destino, nome_requisitante):
    # O quarto parâmetro é o nome do ficheiro que corrigiste: pedido_amizade.html
    return enviar_email_sistema(
        mail, 
        f"Pedido de Amizade de {nome_requisitante}", 
        email_destino, 
        'emails/pedido_amizade.html', 
        nome_remetente=nome_requisitante # Aqui é onde o HTML recebe o valor
    )