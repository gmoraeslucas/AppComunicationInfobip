import requests
from requests.auth import HTTPBasicAuth
from datetime import datetime
import json
from dotenv import load_dotenv
import os
from concurrent.futures import ThreadPoolExecutor
import logging
from tkinter import messagebox
import re
from tkinter import IntVar

load_dotenv()

logging.basicConfig(filename='application_logs.json', level=logging.DEBUG, format='%(asctime)s %(message)s')

API_KEY_INFOBIP = os.getenv('API_KEY_INFOBIP')
JIRA_SERVER = os.getenv('JIRA_SERVER')
JIRA_USER = os.getenv('JIRA_USER')
JIRA_API_TOKEN = os.getenv('JIRA_API_TOKEN')
AUTH_CLIENT_ID = os.getenv("AUTH_CLIENT_ID")
AUTH_CLIENT_SECRET = os.getenv("AUTH_CLIENT_SECRET")
SMS_TEMPLATE_ID = os.getenv("SMS_TEMPLATE_ID")
MODO_SMS = False 

def set_modo_sms(value: bool):
    global MODO_SMS
    MODO_SMS = bool(value)

def is_modo_sms() -> bool:
    return MODO_SMS

def get_jira_from_key(number_key, tipo_alerta_var):
    url = f"{JIRA_SERVER}/rest/api/3/search/jql"
    auth = HTTPBasicAuth(JIRA_USER, JIRA_API_TOKEN)
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json"
    }

    jql = f"key = {number_key}"
    payload = {
        "jql": jql,
        "maxResults": 1,
        "fields": [
            "issuetype",
            "customfield_10010",  # Tipo de GMUD
            "customfield_10273",  # Sistema
            "customfield_10371",  # Prioridade
            "customfield_11335",  # Impacto (ADF)
            "customfield_11735",  # Meet crise
            "customfield_10231",  # Início Crise
            "customfield_10753",  # Término Crise
            "customfield_10774",  # Início GMUD
            "customfield_10775"   # Término GMUD
        ]
    }

    logging.info(f"Buscando crise com chave: {number_key} (enhanced search)")
    response = requests.post(url, headers=headers, auth=auth, data=json.dumps(payload), timeout=20)

    if response.status_code == 200:
        issues = response.json().get('issues', [])
        if not issues:
            logging.error(f"Nenhum item encontrado com a chave {number_key}")
            return None

        issue_data = issues[0]

        Tipo_Issue_GMUD = issue_data['fields'].get('customfield_10010')
        if Tipo_Issue_GMUD:
            issue_tipo_gmud = Tipo_Issue_GMUD.get('requestType', {}).get('name', 'Não especificado')
        else:
            issue_tipo_gmud = 'Não especificado'

        Tipo_Issue_Crise = issue_data['fields'].get('issuetype', {}) or {}
        issue_tipo_crise = Tipo_Issue_Crise.get('name', 'Não especificado')

        logging.info(f"Issue_type selecionado: {issue_tipo_gmud}")

        if (issue_tipo_crise == "Crise" and tipo_alerta_var == "GMUD"):
            logging.error(f"Essa GV se trata de uma {issue_tipo_crise}")
            messagebox.showerror("Erro", f"A chave {number_key} se trata de uma {issue_tipo_crise}.")
            return
        elif ((issue_tipo_gmud in {"Pré Aprovada","Programada","Emergencial"}) and tipo_alerta_var == "Crise"):
            logging.error(f"Essa GV se trata de uma {issue_tipo_gmud}")
            messagebox.showerror("Erro", f"A chave {number_key} se trata de uma GMUD {issue_tipo_gmud}.")
            return
        else:
            logging.info(f"Conexão com Jira bem-sucedida para chave {number_key}.")
            return issue_data

    else:
        try:
            err = response.json()
        except Exception:
            err = {"text": response.text}
        logging.error(f"Erro ao acessar o Jira: {response.status_code} - {err}")


def extract_text_from_Impacto(Impacto):
    text = ""
    if isinstance(Impacto, dict):
        content = Impacto.get('content', [])
        for item in content:
            if isinstance(item, dict):
                paragraph_content = item.get('content', [])
                for paragraph in paragraph_content:
                    if isinstance(paragraph, dict):
                        text += paragraph.get('text', '') + " "
    return text.strip()

def format_date(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%Y-%m-%dT%H:%M:%S.%f%z")
        formatted_date = date_obj.strftime("%d/%m - %H:%M")
        return formatted_date
    except ValueError as e:
        logging.error(f"Erro ao formatar a data: {e}")
        return "Data inválida"

def get_tags():
    URL = 'https://dm62yg.api.infobip.com/people/2/tags'
    headers = {
        'Authorization': f'App {API_KEY_INFOBIP}',
        'Accept': 'application/json'
    }
    logging.info("Obtendo tags da API Infobip.")
    response = requests.get(URL, headers=headers)

    if response.status_code == 200:
        tags = response.json()
        return [tag['name'] for tag in tags.get('tags', [])]
    else:
        logging.error(f"Erro ao obter tags: {response.status_code} - {response.json()}")
        return []
    
import requests
import json

def fetch_contacts_for_tag(tag_name):
    base_url = 'https://dm62yg.api.infobip.com/people/2/persons'
    headers = {
        'Authorization': f'App {API_KEY_INFOBIP}',
        'Accept': 'application/json'
    }

    contacts = []
    filter_criteria = {
        "#and": [
            {"#contains": {"tags": tag_name}}
        ]
    }
    
    more_results = True
    page_number = 0
    limit = 1000

    while more_results:
        params = {
            'filter': json.dumps(filter_criteria),
            'limit': limit,
            'pageNumber': page_number
        }
        response = requests.get(base_url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            persons = data.get('persons', [])
            for person in persons:
                contact_info = person.get('contactInformation', {})
                phones = contact_info.get('phone', [])
                for phone in phones:
                    number = phone.get('number')
                    if number and number not in contacts:
                        contacts.append(number)
            
            more_results = len(persons) == limit
            page_number += 1
        else:
            logging.error(f"Erro ao obter contatos para a tag {tag_name}: {response.status_code} - {response.json()}")
            more_results = False

    return contacts

def get_numbers_by_tags(tag_names):
    all_contacts = []

    logging.info(f"Obtendo números de telefone para as tags: {tag_names}")
    with ThreadPoolExecutor(max_workers=5) as executor: #Não alterar o "max_workers=5", pois a API de GET persons só aceita 5 requisições por segundo
        futures = {executor.submit(fetch_contacts_for_tag, tag_name): tag_name for tag_name in tag_names}
        
        for future in futures:
            try:
                contacts = future.result()
                all_contacts.extend(contacts)
            except Exception as exc:
                tag_name = futures[future]
                logging.error(f"Erro ao processar a tag {tag_name}: {exc}")

    return list(set(all_contacts))

def fetch_emails_for_tag(tag_name):
    base_url = 'https://dm62yg.api.infobip.com/people/2/persons'
    headers = {
        'Authorization': f'App {API_KEY_INFOBIP}',
        'Accept': 'application/json'
    }

    emails = []
    filter_criteria = {
        "#and": [
            {"#contains": {"tags": tag_name}}
        ]
    }
    
    more_results = True
    page_number = 0
    limit = 1000

    while more_results:
        params = {
            'filter': json.dumps(filter_criteria),
            'limit': limit,
            'pageNumber': page_number
        }
        response = requests.get(base_url, headers=headers, params=params)

        if response.status_code == 200:
            data = response.json()
            persons = data.get('persons', [])
            for person in persons:
                contact_info = person.get('contactInformation', {})
                email_addresses = contact_info.get('email', [])
                for email in email_addresses:
                    address = email.get('address')
                    if address and address not in emails:
                        emails.append(address)
            
            more_results = len(persons) == limit
            page_number += 1
        else:
            logging.error(f"Erro ao obter emails para a tag {tag_name}: {response.status_code} - {response.json()}")
            more_results = False

    return emails

def get_emails_by_tags(tag_names):
    all_emails = []

    with ThreadPoolExecutor(max_workers=5) as executor: #Não alterar o "max_workers=5", pois a API de GET persons só aceita 5 requisições por segundo
        futures = {executor.submit(fetch_emails_for_tag, tag_name): tag_name for tag_name in tag_names}
        
        for future in futures:
            try:
                emails = future.result()
                all_emails.extend(emails)
            except Exception as exc:
                tag_name = futures[future]
                logging.error(f"Erro ao processar a tag {tag_name}: {exc}")

    return list(set(all_emails))

def obter_token_sms():
    """
    Chama a API de autenticação para obter token de acesso.
    Retorna o token como string ou None em caso de erro.
    """
    AUTH_URL = "https://rhsso-internal.segurosunimed.com.br/auth/realms/unimed-internos/protocol/openid-connect/token"
    headers = {"Content-Type": "application/x-www-form-urlencoded"}
    data = {
        "client_id": AUTH_CLIENT_ID,
        "client_secret": AUTH_CLIENT_SECRET,
        "grant_type": "client_credentials"
    }
    try:
        resp = requests.post(AUTH_URL, headers=headers, data=data, timeout=10)
        if resp.status_code == 200:
            token = resp.json().get("access_token")
            if token:
                logging.info("Token SMS obtido com sucesso.")
                return token
            else:
                logging.error("Resposta sem 'access_token': %s", resp.text)
        else:
            logging.error(f"Falha ao obter token ({resp.status_code}): {resp.text}")
    except Exception as e:
        logging.exception("Erro na requisição de token SMS")
    return None

def enviar_sms_interno(destinatario, token, formatted_message):
    """
    Envia SMS via API interna, obtendo token antes.
    """
    
    SMS_URL = "https://unicom-api.digital-segurosunimed.com/channels/SMS/messages"

    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json; charset=UTF-8",
        "User-Agent": "gov-communication-api"
    }
    payload = {
        "recipients": [{
            "name": "Seguros Unimed",
            "number": str(destinatario)
        }],
        "templateId": SMS_TEMPLATE_ID,
        "templateAttributes": {
            "message": formatted_message or {}
        }
    }

    try:
        resp = requests.post(SMS_URL, headers=headers, json=payload, timeout=30)
        if 200 <= resp.status_code < 300:
            logging.info(f"SMS enviado com sucesso para {destinatario}.")
        else:
            logging.error(f"Falha ao enviar SMS ({resp.status_code}): {resp.text}")
            messagebox.showerror("Erro SMS", f"Falha ao enviar SMS ({resp.status_code}).")
    except Exception as e:
        logging.exception("Erro ao enviar SMS")
        messagebox.showerror("Erro SMS", f"Exceção ao enviar SMS: {e}")

def enviar_alerta_whatsapp_com_template(destinatario, template_name, parametros, token, formatted_message, language_code='pt_BR'):
    if is_modo_sms():
        return enviar_sms_interno(destinatario, token, formatted_message)
    URL = 'https://api.infobip.com/whatsapp/1/message/template'
    headers = {
        'Authorization': f'App {API_KEY_INFOBIP}',
        'Content-Type': 'application/json',
        'Accept': 'application/json'
    }

    payload = {
        "messages": [
            {
                "from": "5511934543628",
                "to": destinatario,
                "content": {
                    "templateName": template_name,
                    "templateData": {
                        "body": {
                            "placeholders": parametros
                        }
                    },
                    "language": language_code
                }
            }
        ]
    }

    try:
        response = requests.post(URL, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        error_message = f"Erro ao enviar mensagem para {destinatario}: {e}"
        logging.error(error_message)
        raise Exception(error_message)

    logging.info(f'Mensagem enviada com sucesso para {destinatario}!')

def enviar_email_com_template_infobip(destinatario, assunto, corpo_email_html):
    base_url = 'dm62yg.api.infobip.com'
    url = f'https://{base_url}/email/3/send'
    headers = {
        'Authorization': f'App {API_KEY_INFOBIP}'
    }

    with open('images/unnamed.png', 'rb') as img:
        files = {'inlineImage': ('unnamed.png', img)}

        html_content = f"""
        <html>
        <body style="background-color: #f0f0f0; text-align: center; font-family: Arial, sans-serif;">
            <div style="padding: 20px;">
                <div style="display: block; margin: 0 auto;">
                    <img src="cid:unnamed.png" alt="Governança de TI" style="width: 100%; max-width: 640px; height: auto; max-height: 220px; margin-bottom: 20px;"/>
                </div>
                <div style="background-color: white; padding: 20px; border-radius: 10px; display: block; margin: 0 auto; max-width: 600px; text-align: left;">
                    {corpo_email_html}
                </div>
            </div>
        </body>
        </html>
        """

        data = {
            'from': 'Governança de TI <ti-governanca@segurosunimed.com.br>',
            'to': [destinatario],
            'subject': assunto,
            'html': html_content,
        }

        try:
            response = requests.post(url, headers=headers, data=data, files=files)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            error_message = f"Erro ao enviar email para {destinatario}: {e}"
            logging.error(error_message)
            raise Exception(error_message)

    logging.info(f'Email enviado com sucesso para {destinatario}!')

def escolher_templates(tipo_alerta, status, issue_checkpoint, issue_impacto_normalizado):

    templates_crise = {
        'início': [
            ('inicio_crise_negocios', [issue_sistema, 'Início', issue_impacto, issue_inicio]),
            ('inicio_crise_tecnico', [issue_sistema, issue_prioridade, issue_ticket, 'Início', issue_impacto, issue_inicio, issue_meet])
        ],
        'equipes seguem atuando': [
            ('check_crise_negocios', [issue_sistema, 'Equipes seguem atuando', issue_impacto, issue_inicio]),
            ('check_crise_tecnico', [issue_sistema, issue_prioridade, issue_ticket, 'Equipes seguem atuando', issue_impacto, issue_checkpoint, issue_inicio, issue_meet])
        ],
        'em validação': [
            ('check_crise_negocios', [issue_sistema, 'Em validação', issue_impacto_normalizado, issue_inicio]),
            ('check_crise_tecnico', [issue_sistema, issue_prioridade, issue_ticket, 'Em validação', issue_impacto_normalizado, issue_checkpoint, issue_inicio, issue_meet])
        ],
        'normalizado': [
            ('encerramento_crise_negocios', [issue_sistema, 'Normalizado', issue_impacto_normalizado, issue_inicio, issue_termino]),
            ('encerramento_crise_tecnico', [issue_sistema, issue_prioridade, issue_ticket, 'Normalizado', issue_impacto_normalizado, issue_inicio, issue_termino])
        ]
    }

    templates_critico = {
        'início': [
            ('inicio_critico_negocios', [issue_sistema, 'Início', issue_impacto, issue_inicio]),
            ('inicio_critico_tecnico', [issue_sistema, issue_prioridade, issue_ticket, 'Início', issue_impacto, issue_inicio, issue_meet])
        ],
        'equipes seguem atuando': [
            ('check_critico_negocios', [issue_sistema, 'Equipes seguem atuando', issue_impacto, issue_inicio]),
            ('check_critico_tecnico', [issue_sistema, issue_prioridade, issue_ticket, 'Equipes seguem atuando', issue_impacto, issue_checkpoint, issue_inicio, issue_meet])
        ],
        'em validação': [
            ('check_critico_negocios', [issue_sistema, 'Em validação', issue_impacto_normalizado, issue_inicio]),
            ('check_critico_tecnico', [issue_sistema, issue_prioridade, issue_ticket, 'Em validação', issue_impacto_normalizado, issue_checkpoint, issue_inicio, issue_meet])
        ],
        'normalizado': [
            ('encerramento_critico_negocios', [issue_sistema, 'Normalizado', issue_impacto_normalizado, issue_inicio, issue_termino]),
            ('encerramento_critico_tecnico', [issue_sistema, issue_prioridade, issue_ticket, 'Normalizado', issue_impacto_normalizado, issue_inicio, issue_termino])
        ]
    }

    if tipo_alerta == 'crise':
        return templates_crise.get(status.lower(), [])
    elif tipo_alerta == 'inc. crítico':
        return templates_critico.get(status.lower(), [])
    else:
        return []
    
def escolher_templates_gmud(tipo_alerta_var, issue_atividade_tecnica, issue_atividade_negocio, issue_meet_gmud):
    templates_gmud = {
        'gmud': [
            ('gmud_negocio_v2', [issue_sistema, issue_tipo, issue_ambiente, issue_atividade_negocio, issue_inicio, issue_termino]),
            ('gmud_tecnico_v4', [issue_sistema, issue_tipo, issue_ticket, issue_ambiente, issue_atividade_tecnica, issue_meet_gmud, issue_inicio, issue_termino])
        ]
    }
    if tipo_alerta_var == "GMUD":
        return templates_gmud.get("gmud", [])
    else:
        return []

def verificar_placeholders(templates):
    for template_name, params in templates:
        missing_placeholders = [param for param in params if param == '']
        if missing_placeholders:
            logging.info(f"Erro: Template '{template_name}' contém placeholders vazios: {missing_placeholders}")
            return False
    return True

def format_checkpoint_date(date_str):
    try:
        date_obj = datetime.strptime(date_str, "%d/%m %H:%M")
        formatted_date = date_obj.strftime("%d/%m - %H:%M")
        return formatted_date
    except ValueError as e:
        logging.error(f"Erro ao formatar a data do checkpoint: {e}")
        return "Data inválida"
    
def process_issue_data(issue_data):
    global issue_ticket, issue_sistema, issue_prioridade, issue_impacto, issue_inicio, issue_termino, issue_meet
    
    issue_ticket = issue_data['key']

    Sistema = issue_data['fields'].get('customfield_10273', {})
    issue_sistema = Sistema.get('value', 'Não especificado')

    Prioridade = issue_data['fields'].get('customfield_10371', {})
    issue_prioridade = Prioridade.get('value', 'Não especificado')

    Impacto = issue_data['fields'].get('customfield_11335', {})
    issue_impacto = extract_text_from_Impacto(Impacto)

    issue_meet = issue_data['fields'].get('customfield_11735')

    Inicio = issue_data['fields'].get('customfield_10231', None)
    issue_inicio = format_date(Inicio)

    Termino = issue_data['fields'].get('customfield_10753', None)
    issue_termino = format_date(Termino) if Termino else ""

    return {
        'ticket': issue_ticket,
        'sistema': issue_sistema,
        'impacto': issue_impacto,
        'inicio': issue_inicio,
        'termino': issue_termino,
        'meet': issue_meet,
    }

def process_issue_data_gmud(issue_data):
    global issue_ticket, issue_sistema, issue_tipo, issue_inicio, issue_termino, issue_ambiente
    
    issue_ticket = issue_data['key']
    
    Sistema = issue_data['fields'].get('customfield_10273', {})
    issue_sistema = Sistema.get('value', 'Não especificado')
    
    issue_ambiente = "Produção"

    Tipo = issue_data['fields'].get('customfield_10010', {})
    issue_tipo = Tipo.get('requestType', {}).get('name', 'Não especificado')

    Inicio = issue_data['fields'].get('customfield_10774', None)
    issue_inicio = format_date(Inicio)
    
    Termino = issue_data['fields'].get('customfield_10775', None)
    issue_termino = format_date(Termino) if Termino else ""

    return {
        'ticket': issue_ticket,
        'sistema': issue_sistema,
        'inicio': issue_inicio,
        'termino': issue_termino
    }, issue_tipo

def load_templates():
    with open('templates.json', 'r', encoding='utf-8') as file:
        return json.load(file)

TEMPLATES = load_templates()

def format_template(template_name, issue_status, issue_impacto_normalizado, issue_checkpoint, tipo_alerta_var, issue_atividade_tecnica, issue_atividade_negocio, issue_meet_gmud):
    template = TEMPLATES.get(template_name, "")
    if template:
        if ((issue_status == "Normalizado" or issue_status == "Em validação") and tipo_alerta_var != "GMUD"):
            formatted_text = template.format(
                issue_sistema=issue_sistema,
                issue_prioridade=issue_prioridade,
                issue_ticket=issue_ticket,
                issue_status=issue_status,
                issue_inicio=issue_inicio,
                issue_impacto=issue_impacto_normalizado,
                issue_meet=issue_meet,
                issue_checkpoint=issue_checkpoint,
                issue_termino=issue_termino
            )
        elif ((issue_status == "Início" or issue_status == "Equipes seguem atuando") and tipo_alerta_var != "GMUD"):
            formatted_text = template.format(
                issue_sistema=issue_sistema,
                issue_prioridade=issue_prioridade,
                issue_ticket=issue_ticket,
                issue_status=issue_status,
                issue_inicio=issue_inicio,
                issue_impacto=issue_impacto,
                issue_meet=issue_meet,
                issue_checkpoint=issue_checkpoint,
                issue_termino=issue_termino
            )
        elif (tipo_alerta_var == "GMUD"):
            formatted_text = template.format(
                issue_sistema=issue_sistema,
                issue_tipo=issue_tipo,
                issue_ticket=issue_ticket,
                issue_ambiente=issue_ambiente,
                issue_atividade_tecnica=issue_atividade_tecnica,
                issue_atividade_negocio=issue_atividade_negocio,
                issue_meet_gmud=issue_meet_gmud,
                issue_inicio=issue_inicio,
                issue_termino=issue_termino
            )
        else:
            formatted_text = ""
        return formatted_text
    return ""

def format_template_html(formatted_text):

    formatted_html = re.sub(r'\*(.*?)\*', r'<strong>\1</strong>', formatted_text)
    formatted_html = formatted_html.replace("\n", "<br>")
    formatted_html = re.sub(r'_(.*?)_', r'<em>\1</em>', formatted_html)
    
    return formatted_html

def format_template_sms(formatted_html):

    formatted_html = formatted_html.replace("*", "")
    
    return formatted_html