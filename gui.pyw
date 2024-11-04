from tkinter import messagebox, IntVar, scrolledtext, Toplevel
import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledFrame
from ttkbootstrap.constants import *
from concurrent.futures import ThreadPoolExecutor, as_completed
from main import escolher_templates_gmud, get_jira_from_key, get_tags, get_numbers_by_tags, get_emails_by_tags, enviar_alerta_whatsapp_com_template, enviar_email_com_template_infobip, escolher_templates, process_issue_data, verificar_placeholders, format_template, format_template_html, process_issue_data_gmud
from PIL import Image, ImageTk
import logging
import threading
import json

logging.basicConfig(filename='application_logs.json', level=logging.DEBUG, format='%(asctime)s %(message)s')

tema_atual = "simplex"
def main():
    tags = get_tags()
    def active_tag_checkboxes():
        if tipo_alerta_var.get() == "Crise":
            tags_to_activate = ["Command_Center", "Governança de TI", "Crises - TIVIT", "Infraestrutura - CSC", "Infraestrutura - TI"]
        elif tipo_alerta_var.get() == "GMUD":
            tags_to_activate = ["Command_Center", "Governança de TI", "Mudanças - TIVIT", "Infraestrutura - CSC", "Infraestrutura - TI"]

        for widget in tags_frame_tecnico.winfo_children():
            widget.destroy()

        for tag in tags:
            var = IntVar()
            if tag in tags_to_activate:
                var.set(1)
            checkbox = ttk.Checkbutton(tags_frame_tecnico, text=tag, variable=var)
            checkbox.pack(anchor='w')
            tags_vars_tecnico[tag] = var
    
    def populate_negocios_tags():
        tags_to_activate = ["Command_Center", "Negócios", "Governança de TI"]
        for tag in tags_to_activate:
            var = IntVar()
            var.set(1)
            checkbox = ttk.Checkbutton(tags_frame_negocios, text=tag, variable=var)
            checkbox.pack(anchor='w')
            tags_vars_negocios[tag] = var

    def toggle_checkpoint_date():
        if status_alerta_var.get() == "Equipes seguem atuando":
            checkpoint_date_label.pack(pady=10, after=number_key_entry)
            checkpoint_date_entry.pack(pady=10, after=checkpoint_date_label)
            impacto_normalizado_label.pack_forget()
            impacto_normalizado_entry.pack_forget()
        elif status_alerta_var.get() == "Em validação":
            checkpoint_date_label.pack(pady=10, after=number_key_entry)
            checkpoint_date_entry.pack(pady=10, after=checkpoint_date_label)
            impacto_normalizado_label.pack(pady=10, after=number_key_entry)
            impacto_normalizado_entry.pack(pady=10, after=impacto_normalizado_label)
        elif status_alerta_var.get() == "Normalizado":
            impacto_normalizado_label.pack(pady=10, after=number_key_entry)
            impacto_normalizado_entry.pack(pady=10, after=impacto_normalizado_label)
            checkpoint_date_label.pack_forget()
            checkpoint_date_entry.pack_forget()
        else:
            checkpoint_date_label.pack_forget()
            checkpoint_date_entry.pack_forget()
            impacto_normalizado_label.pack_forget()
            impacto_normalizado_entry.pack_forget()

    def choose_theme():
        global tema_atual
        available_themes = root.style.theme_names()
        
        theme_cycle = ["simplex", "solar", "darkly"]
        
        if tema_atual in theme_cycle:
            current_index = theme_cycle.index(tema_atual)
            next_index = (current_index + 1) % len(theme_cycle)
            new_theme = theme_cycle[next_index]
        else:
            new_theme = "simplex"  # Se o tema atual não for reconhecido, será iniciado como "simplex"

        if new_theme in available_themes:
            root.style.theme_use(new_theme)
            tema_atual = new_theme

        logging.info(f"Theme changed to: {tema_atual}")

    def send_message():

        global destinatarios_tecnico, destinatarios_negocios, emails_tecnico, emails_negocios, tipo_alerta_email
        
        selected_tags_tecnico = [tag for tag, var in tags_vars_tecnico.items() if var.get() == 1]
        destinatarios_tecnico = get_numbers_by_tags(selected_tags_tecnico)
        logging.info(f"Técnico: {len(destinatarios_tecnico)} destinatários encontrados.")
        emails_tecnico = get_emails_by_tags(selected_tags_tecnico)
        logging.info(f"Técnico Emails: {len(emails_tecnico)} encontrados.")

        if not destinatarios_tecnico:
            messagebox.showerror("Erro", "Nenhum destinatário encontrado para as tags técnicas.")
            return

        selected_tags_negocios = [tag for tag, var in tags_vars_negocios.items() if var.get() == 1]
        destinatarios_negocios = get_numbers_by_tags(selected_tags_negocios)
        logging.info(f"Negócios: {len(destinatarios_negocios)} destinatários encontrados.")
        emails_negocios = get_emails_by_tags(selected_tags_negocios)
        logging.info(f"Negócios Emails: {len(emails_negocios)} encontrados.")
        
        if not destinatarios_negocios:
            messagebox.showerror("Erro", "Nenhum destinatário encontrado para as tags de negócios.")
            return
        
        tipo_alerta = ""
        tipo_alerta_email = ""
        status_alerta = status_alerta_var.get().lower()
        
        number_key = number_key_entry.get()
        issue_data = get_jira_from_key(number_key, tipo_alerta_var.get())
            
        if issue_data:
            global issue_checkpoint
            global issue_impacto_normalizado
            global issue_atividade_tecnica
            global issue_atividade_negocio
            global issue_meet_gmud
            if tipo_alerta_var.get() == "Crise":
                process_issue_data(issue_data)
                Prioridade = issue_data['fields'].get('customfield_10371', {})
                issue_prioridade = Prioridade.get('value', 'Não especificado')

                if issue_prioridade == "P1" or issue_prioridade == "P0":
                    tipo_alerta = "crise"
                    tipo_alerta_email = "Crise"

                elif issue_prioridade == "P2" or issue_prioridade == "P3":
                    tipo_alerta = "inc. crítico"
                    tipo_alerta_email = "Inc. Crítico"

            elif tipo_alerta_var.get() == "GMUD":
                Tipo = issue_data['fields'].get('customfield_10010', None)
                if Tipo:
                    issue_tipo = Tipo.get('requestType', {}).get('name', 'Não especificado')
                else:
                    issue_tipo = 'Não especificado'
                process_issue_data_gmud(issue_data)
                tipo_alerta_email = f"Mudança {issue_tipo}"
                
            issue_checkpoint = checkpoint_date_entry.get()
            issue_impacto_normalizado = impacto_normalizado_entry.get()
            issue_atividade_tecnica = atividade_tecnica_entry.get()
            issue_atividade_negocio = atividade_negocio_entry.get()
            issue_meet_gmud = meet_gmud_entry.get()
            

            if tipo_alerta_var.get() == "Crise":
                templates = escolher_templates(tipo_alerta, status_alerta, issue_checkpoint, issue_impacto_normalizado)
            elif tipo_alerta_var.get() == "GMUD":
                templates = escolher_templates_gmud(tipo_alerta_var.get(), issue_atividade_tecnica, issue_atividade_negocio, issue_meet_gmud)

            if templates:
                if not verificar_placeholders(templates):
                    messagebox.showerror("Erro", "Um ou mais placeholders estão vazios.")
                    return

                show_confirmation(templates)
            else:
                messagebox.showerror("Erro", "Opção inválida!")
        else:
            messagebox.showerror("Erro", "Erro ao recuperar os dados da crise!")
    

    def show_confirmation(templates):
        confirmation_window = Toplevel(root)
        confirmation_window.title("Confirmação de Envio")
        window_width = 850
        window_height = 700
        position_right = int(confirmation_window.winfo_screenwidth() / 2 - window_width / 2)
        position_top = int(confirmation_window.winfo_screenheight() / 2 - window_height / 1.8)
        confirmation_window.geometry(f"{window_width}x{window_height}+{position_right}+{position_top}")

        ttk.Label(confirmation_window, text="Confirme as Mensagens a Serem Enviadas:", font=("Arial", 10)).pack(pady=10)

        message_preview_tecnico = None
        message_preview_negocios = None
        message_preview_gmud_tecnico = None
        message_preview_gmud_negocio = None


        if tipo_alerta_var.get() == "Crise":
            message_preview_tecnico = scrolledtext.ScrolledText(confirmation_window, wrap=ttk.WORD, height=10, width=70)
            message_preview_tecnico.pack(pady=10)
        
            message_preview_negocios = scrolledtext.ScrolledText(confirmation_window, wrap=ttk.WORD, height=10, width=70)
            message_preview_negocios.pack(pady=10)

        elif tipo_alerta_var.get() == "GMUD":
            message_preview_gmud_tecnico = scrolledtext.ScrolledText(confirmation_window, wrap=ttk.WORD, height=10, width=70)
            message_preview_gmud_tecnico.pack(pady=10)

            message_preview_gmud_negocio = scrolledtext.ScrolledText(confirmation_window, wrap=ttk.WORD, height=10, width=70)
            message_preview_gmud_negocio.pack(pady=10)

        def load_preview():
            preview_text_tecnico = ""
            preview_text_negocios = ""
            preview_text_gmud_tecnico = ""
            preview_text_gmud_negocio = ""

            for template_name, _ in templates:
                formatted_message = format_template(template_name, status_alerta_var.get(), issue_impacto_normalizado, issue_checkpoint, tipo_alerta_var.get(), issue_atividade_tecnica, issue_atividade_negocio, issue_meet_gmud)
                if "tecnico" in template_name:
                    preview_text_tecnico += formatted_message + "\n\n"
                if "negocios" in template_name:
                    preview_text_negocios += formatted_message + "\n\n"
                if "gmud_tecnico" in template_name:
                    preview_text_gmud_tecnico += formatted_message + "\n\n"
                if "gmud_negocio" in template_name:
                    preview_text_gmud_negocio += formatted_message + "\n\n"

            if message_preview_tecnico is not None:
                message_preview_tecnico.insert(1.0, preview_text_tecnico)
            if message_preview_negocios is not None:
                message_preview_negocios.insert(1.0, preview_text_negocios)
            if message_preview_gmud_tecnico is not None:
                message_preview_gmud_tecnico.insert(1.0, preview_text_gmud_tecnico)
            if message_preview_gmud_negocio is not None:
                message_preview_gmud_negocio.insert(1.0, preview_text_gmud_negocio)

        threading.Thread(target=load_preview).start()

        ttk.Button(confirmation_window, text="Confirmar Envio", command=lambda: confirm_send(confirmation_window, templates)).pack(pady=10)

    def confirm_send(confirmation_window, templates):
        confirmation_window.destroy()

        def send_messages():
            with ThreadPoolExecutor(max_workers=10) as executor:
                futures = []
                
                for template_name, params in templates:
                    
                    if "tecnico" in template_name:
                        for destinatario in destinatarios_tecnico:
                            formatted_message = format_template(template_name, status_alerta_var.get(), issue_impacto_normalizado, issue_checkpoint, tipo_alerta_var.get(), issue_atividade_tecnica, issue_atividade_negocio, issue_meet_gmud)
                            futures.append(executor.submit(enviar_alerta_whatsapp_com_template, destinatario, template_name, params))
                            logging.info(f"Enviando mensagem WhatsApp para {destinatario}.")
                    if "negocio" in template_name:
                        for destinatario in destinatarios_negocios:
                            formatted_message = format_template(template_name, status_alerta_var.get(), issue_impacto_normalizado, issue_checkpoint, tipo_alerta_var.get(), issue_atividade_tecnica, issue_atividade_negocio, issue_meet_gmud)
                            futures.append(executor.submit(enviar_alerta_whatsapp_com_template, destinatario, template_name, params))
                            logging.info(f"Enviando mensagem WhatsApp para {destinatario}.")

                for template_name, params in templates:
                    if "tecnico" in template_name:
                        for destinatario in emails_tecnico:
                            formatted_message_html = format_template_html(format_template(template_name, status_alerta_var.get(), issue_impacto_normalizado, issue_checkpoint, tipo_alerta_var.get(), issue_atividade_tecnica, issue_atividade_negocio, issue_meet_gmud))
                            futures.append(executor.submit(enviar_email_com_template_infobip, destinatario, tipo_alerta_email, formatted_message_html))
                            logging.info(f"Enviando email para {destinatario}.")
                    if "negocio" in template_name:
                        for destinatario in emails_negocios:
                            formatted_message_html = format_template_html(format_template(template_name, status_alerta_var.get(), issue_impacto_normalizado, issue_checkpoint, tipo_alerta_var.get(), issue_atividade_tecnica, issue_atividade_negocio, issue_meet_gmud))
                            futures.append(executor.submit(enviar_email_com_template_infobip, destinatario, tipo_alerta_email, formatted_message_html))
                            logging.info(f"Enviando email para {destinatario}.")

                for future in as_completed(futures):
                    try:
                        future.result()
                    except Exception as e:
                        logging.error(f"Erro ao enviar para um destinatário: {e}")
                        messagebox.showerror("Erro", f"Erro ao enviar mensagem ou email: {e}")
                        return

            logging.info("Mensagens e emails enviados com sucesso.")
            messagebox.showinfo("Sucesso", "Mensagens e emails enviados com sucesso!")

        threading.Thread(target=send_messages).start()


    global status_alerta_var, tipo_alerta_var
    root = ttk.Window(themename=tema_atual)
    root.title("Envio de Alertas")
    window_width = 730
    window_height = 960
    position_right = int(root.winfo_screenwidth() / 2 - window_width / 2)
    position_top = int(root.winfo_screenheight() / 2 - window_height / 1.75)
    root.geometry(f"{window_width}x{window_height}+{position_right}+{position_top}")

    global tags_vars_tecnico, tags_vars_negocios
    tags_vars_tecnico = {}
    tags_vars_negocios = {}

    scrolled_frame = ScrolledFrame(root, width=window_width, height=window_height, autohide=True)
    scrolled_frame.pack(pady=10, padx=10, fill='both', expand=True)

    border_frame = ttk.Labelframe(scrolled_frame, text="Envio de Comunicação de Crise", padding=(10, 10, 5, 10))
    border_frame.pack(pady=10, padx=10, fill='both', expand=True)

    def toggle_fields():
        active_tag_checkboxes() #Para ser ativado no mesmo botão com a variavél tipo_alerta_var.
        checkpoint_date_label.pack_forget()
        checkpoint_date_entry.pack_forget()
        impacto_normalizado_label.pack_forget()
        impacto_normalizado_entry.pack_forget()
        if tipo_alerta_var.get() == "Crise":
            status_gmud_frame.pack_forget()
            atividade_tecnica_label.pack_forget()
            atividade_tecnica_entry.pack_forget()
            atividade_negocio_label.pack_forget()
            atividade_negocio_entry.pack_forget()
            meet_gmud_label.pack_forget()
            meet_gmud_entry.pack_forget()
            status_alerta_frame.pack(pady=10, after=tipo_alerta_frame)
        elif tipo_alerta_var.get() == "GMUD":
            status_alerta_frame.pack_forget()
            status_gmud_frame.pack(pady=10, after=tipo_alerta_frame)
            atividade_tecnica_label.pack(pady=10, after=number_key_entry)
            atividade_tecnica_entry.pack(pady=10, after=atividade_tecnica_label)
            atividade_negocio_label.pack(pady=10, after=number_key_entry)
            atividade_negocio_entry.pack(pady=10, after=atividade_negocio_label)
            meet_gmud_label.pack(pady=10, after=number_key_entry)
            meet_gmud_entry.pack(pady=10, after=meet_gmud_label)

    tipo_alerta_frame = ttk.Frame(border_frame)
    tipo_alerta_frame.pack(pady=10)
    tipo_alerta_var = ttk.StringVar(value="Crise")
    ttk.Radiobutton(tipo_alerta_frame, text="Crise", variable=tipo_alerta_var, value="Crise", command=toggle_fields).pack(side='left', padx=5)
    ttk.Radiobutton(tipo_alerta_frame, text="GMUD", variable=tipo_alerta_var, value="GMUD", command=toggle_fields).pack(side='left', padx=5)

    status_alerta_frame = ttk.Frame(border_frame)
    status_alerta_frame.pack(pady=10)
    status_alerta_var = ttk.StringVar()
    ttk.Radiobutton(status_alerta_frame, text="Início", variable=status_alerta_var, value="Início", command=toggle_checkpoint_date).pack(side='left', padx=5)
    ttk.Radiobutton(status_alerta_frame, text="Equipes seguem atuando", variable=status_alerta_var, value="Equipes seguem atuando", command=toggle_checkpoint_date).pack(side='left', padx=5)
    ttk.Radiobutton(status_alerta_frame, text="Em validação", variable=status_alerta_var, value="Em validação", command=toggle_checkpoint_date).pack(side='left', padx=5)
    ttk.Radiobutton(status_alerta_frame, text="Normalizado", variable=status_alerta_var, value="Normalizado", command=toggle_checkpoint_date).pack(side='left', padx=5)
    
    status_gmud_frame = ttk.Frame(border_frame)
    status_gmud_frame.pack(pady=10)
    
    checkpoint_date_label = ttk.Label(border_frame, text="Data do Checkpoint:", font=("Arial", 10))
    checkpoint_date_entry = ttk.Entry(border_frame, font=("Arial", 10))

    impacto_normalizado_label = ttk.Label(border_frame, text="Mensagem de normalização:", font=("Arial", 10))
    impacto_normalizado_entry = ttk.Entry(border_frame, font=("Arial", 10), width=40)

    atividade_tecnica_label = ttk.Label(border_frame, text="Atividade Técnica:", font=("Arial", 10))
    atividade_tecnica_entry = ttk.Entry(border_frame, font=("Arial", 10), width=40)

    atividade_negocio_label = ttk.Label(border_frame, text="Atividade Negócio:", font=("Arial", 10))
    atividade_negocio_entry =  ttk.Entry(border_frame, font=("Arial", 10), width=40)

    meet_gmud_label = ttk.Label(border_frame, text="Link do Meet:", font=("Arial", 10))
    meet_gmud_entry = ttk.Entry(border_frame, font=("Arial", 10))

    number_key_label = ttk.Label(border_frame, text="Número da GV:", font=("Helvetica", 10))
    number_key_label.pack(pady=10)
    number_key_entry = ttk.Entry(border_frame, font=("Arial", 10))
    number_key_entry.pack(pady=10)
    
    tags_container_frame = ttk.Frame(border_frame)
    tags_container_frame.pack(pady=10, padx=10)

    tecnico_frame = ttk.Frame(tags_container_frame)
    tecnico_frame.pack(side='left', padx=10)

    ttk.Label(tecnico_frame, text="Escolha as Tags para Técnico:", font=("Arial", 10)).pack(pady=10)
    tags_border_frame_tecnico = ttk.Frame(tecnico_frame, padding=5, style="Custom.TFrame")
    tags_border_frame_tecnico.pack(pady=10)
    tags_border_frame_tecnico.configure(borderwidth=1, relief="solid")
    scrolled_frame_tecnico = ScrolledFrame(tags_border_frame_tecnico, width=300, height=300, autohide=True)
    scrolled_frame_tecnico.pack(pady=10, padx=10)
    tags_frame_tecnico = scrolled_frame_tecnico
    active_tag_checkboxes()

    toggle_fields()

    negocios_frame = ttk.Frame(tags_container_frame)
    negocios_frame.pack(side='left', padx=10)

    ttk.Label(negocios_frame, text="Tags para Negócios (Predefinidas):", font=("Arial", 10)).pack(pady=10)
    tags_border_frame_negocios = ttk.Frame(negocios_frame, padding=5, style="Custom.TFrame")
    tags_border_frame_negocios.pack(pady=10)
    tags_border_frame_negocios.configure(borderwidth=1, relief="solid")
    scrolled_frame_negocios = ScrolledFrame(tags_border_frame_negocios, width=300, height=300, autohide=True)
    scrolled_frame_negocios.pack(pady=10, padx=10)
    tags_frame_negocios = scrolled_frame_negocios
    populate_negocios_tags()

    ttk.Button(border_frame, text="Enviar mensagem", command=send_message).pack(pady=10)

    logos_frame = ttk.Frame(border_frame)
    logos_frame.pack(pady=10)

    logo1_img = Image.open("images/infobip.png")
    logo1_img = logo1_img.resize((140, 85), Image.Resampling.LANCZOS)
    logo1 = ImageTk.PhotoImage(logo1_img)

    logo2_img = Image.open("images/seguros-unimed.png")
    logo2_img = logo2_img.resize((120, 50), Image.Resampling.LANCZOS)
    logo2 = ImageTk.PhotoImage(logo2_img)

    logo1_label = ttk.Label(logos_frame, image=logo1)
    logo1_label.pack(side="left", padx=40)

    logo2_label = ttk.Label(logos_frame, image=logo2)
    logo2_label.pack(side="left", padx=40)

    ttk.Button(border_frame, text="Alternar Tema", command=choose_theme).pack(side='left', padx=5)

    root.mainloop()

if __name__ == "__main__":
    main()
