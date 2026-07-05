import sib_api_v3_sdk
from sib_api_v3_sdk.rest import ApiException
from flask import render_template
import os
from datetime import datetime, date

# --- CONFIGURAÇÃO CENTRAL DA API ---
def get_api_instance():
    configuration = sib_api_v3_sdk.Configuration()
    # Usa a variável de ambiente (garante que está configurada no Render)
    configuration.api_key['api-key'] = os.environ.get('BREVO_API_KEY') 
    return sib_api_v3_sdk.TransactionalEmailsApi(sib_api_v3_sdk.ApiClient(configuration))

# --- FUNÇÃO MESTRE UNIFICADA (API) ---
def enviar_email_api(destinatario, assunto, template_html, **kwargs):
    api_instance = get_api_instance()
    # Renderiza o conteúdo do template Flask
    conteudo = render_template(template_html, **kwargs)
    
    send_smtp_email = sib_api_v3_sdk.SendSmtpEmail(
        to=[{"email": destinatario}],
        sender={"email": "yuzakisama2007@gmail.com", "name": "Yuzaki Export"},
        subject=assunto,
        html_content=conteudo
    )
    
    try:
        # MÉTODO CORRETO PARA A API BREVO
        api_instance.send_transac_email(send_smtp_email)
        print(f"✅ Email enviado via API para {destinatario}")
        return True
    except ApiException as e:
        print(f"❌ ERRO API BREVO: {e}")
        return False

# --- FUNÇÕES ESPECÍFICAS (Agora todas usam a API) ---

def enviar_recuperacao_senha(email_destino, nome_user, link):
    return enviar_email_api(email_destino, "Recuperação de Acesso", 'emails/recuperar_senha.html', nome=nome_user, link=link)

def enviar_notificacao_amizade(email_destino, nome_requisitante):
    return enviar_email_api(email_destino, f"Pedido de Amizade de {nome_requisitante}", 'emails/pedido_amizade.html', nome_remetente=nome_requisitante)

def enviar_contacto_suporte(user_nome, user_email, assunto_msg, mensagem_corpo):
    return enviar_email_api("yuzakisama2007@gmail.com", f"📩 [{assunto_msg}] Feedback de {user_nome}", 'emails/contacto_admin.html', nome=user_nome, email=user_email, assunto=assunto_msg, mensagem=mensagem_corpo)

def enviar_recibo(email_cliente, nome_cliente, lista_jogos, fatura_id=None):
    try:
        total_geral, total_base, total_iva = 0, 0, 0
        jogos_processados = []  
        hoje = date.today()

        for jogo in lista_jogos:
            preco_original = float(jogo.get('preco', 0) or 0)
            desconto = jogo.get('desconto_percentual', 0) or 0
            ini, fim = jogo.get('promo_inicio'), jogo.get('promo_fim')
            preco_pago = preco_original

            if desconto > 0 and ini and fim:
                if isinstance(ini, str): ini = datetime.strptime(ini, '%Y-%m-%d').date()
                if isinstance(fim, str): fim = datetime.strptime(fim, '%Y-%m-%d').date()
                if ini <= hoje <= fim:
                    preco_pago = preco_original * (1 - (desconto / 100))

            base_jogo = preco_pago / 1.23
            total_geral += preco_pago
            total_base += base_jogo
            total_iva += (preco_pago - base_jogo)

            jogos_processados.append({'titulo': jogo['titulo'], 'preco_pago': preco_pago, 'foi_promo': preco_pago < preco_original})

        return enviar_email_api(
            email_cliente, "Recibo de Aquisição | Yuzaki Export", 'emails/recibo.html',
            nome_cliente=nome_cliente, lista_jogos=jogos_processados,
            num_fatura=fatura_id or datetime.now().strftime('%Y%m%d%H%M'),
            data_atual=datetime.now().strftime('%d/%m/%Y %H:%M'),
            total_geral=round(total_geral, 2), total_base=round(total_base, 2), total_iva=round(total_iva, 2)
        )
    except Exception as e:
        print(f"❌ ERRO NO ENVIO DO RECIBO: {e}")
        return False
