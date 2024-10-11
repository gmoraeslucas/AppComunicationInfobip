from tkinter import messagebox, IntVar, scrolledtext, Toplevel
import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledFrame
from ttkbootstrap.constants import *
from concurrent.futures import ThreadPoolExecutor, as_completed
from main import get_crisis_from_key, get_tags, get_numbers_by_tags, get_emails_by_tags, enviar_alerta_whatsapp_com_template, enviar_email_com_template_infobip, escolher_templates, process_issue_data, verificar_placeholders, format_template, format_template_html
from PIL import Image, ImageTk
import logging
import threading

logging.basicConfig(filename='application_logs.json', level=logging.DEBUG, format='%(asctime)s %(message)s')

tema_atual = "flatly"
def main():
    def create_tag_checkboxes():
        tags = get_tags()
        tags_to_activate = ["Command_Center", "Governança de TI", "Crises - TIVIT", "Infraestrutura - CSC", "Infraestrutura - TI"]
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
        if tema_atual == "flatly":
            root.style.theme_use("darkly")
            tema_atual = "darkly"
        else:
            root.style.theme_use("flatly")
            tema_atual = "flatly"

    def send_message():

        global destinatarios_tecnico, destinatarios_negocios, emails_tecnico, emails_negocios
        
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
            
        tipo_alerta = tipo_alerta_var.get().lower()
        status_alerta = status_alerta_var.get().lower()
        
        number_key = number_key_entry.get()
        issue_data = get_crisis_from_key(number_key)
        
        if issue_data:
            global issue_checkpoint
            global issue_impacto_normalizado
            process_issue_data(issue_data)
            issue_checkpoint = checkpoint_date_entry.get()
            issue_impacto_normalizado = impacto_normalizado_entry.get()

            templates = escolher_templates(tipo_alerta, status_alerta, issue_checkpoint, issue_impacto_normalizado)
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

        message_preview_tecnico = scrolledtext.ScrolledText(confirmation_window, wrap=ttk.WORD, height=10, width=70)
        message_preview_tecnico.pack(pady=10)

        message_preview_negocios = scrolledtext.ScrolledText(confirmation_window, wrap=ttk.WORD, height=10, width=70)
        message_preview_negocios.pack(pady=10)

        def load_preview():
            preview_text_tecnico = ""
            preview_text_negocios = ""

            for template_name, _ in templates:
                formatted_message = format_template(template_name, status_alerta_var.get(), issue_impacto_normalizado, issue_checkpoint)
                if "tecnico" in template_name:
                    preview_text_tecnico += formatted_message + "\n\n"
                if "negocios" in template_name:
                    preview_text_negocios += formatted_message + "\n\n"

            message_preview_tecnico.insert(1.0, preview_text_tecnico)
            message_preview_negocios.insert(1.0, preview_text_negocios)

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
                            formatted_message = format_template(template_name, status_alerta_var.get(), issue_impacto_normalizado, issue_checkpoint)
                            futures.append(executor.submit(enviar_alerta_whatsapp_com_template, destinatario, template_name, params))
                            logging.info(f"Enviando mensagem WhatsApp para {destinatario}.")
                    if "negocios" in template_name:
                        for destinatario in destinatarios_negocios:
                            formatted_message = format_template(template_name, status_alerta_var.get(), issue_impacto_normalizado, issue_checkpoint)
                            futures.append(executor.submit(enviar_alerta_whatsapp_com_template, destinatario, template_name, params))
                            logging.info(f"Enviando mensagem WhatsApp para {destinatario}.")

                for template_name, params in templates:
                    if "tecnico" in template_name:
                        for destinatario in emails_tecnico:
                            formatted_message_html = format_template_html(format_template(template_name, status_alerta_var.get(), issue_impacto_normalizado, issue_checkpoint))
                            futures.append(executor.submit(enviar_email_com_template_infobip, destinatario, tipo_alerta_var.get(), formatted_message_html))
                            logging.info(f"Enviando email para {destinatario}.")
                    if "negocios" in template_name:
                        for destinatario in emails_negocios:
                            formatted_message_html = format_template_html(format_template(template_name, status_alerta_var.get(), issue_impacto_normalizado, issue_checkpoint))
                            futures.append(executor.submit(enviar_email_com_template_infobip, destinatario, tipo_alerta_var.get(), formatted_message_html))
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


    global status_alerta_var
    root = ttk.Window(themename="flatly")
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

    tipo_alerta_frame = ttk.Frame(border_frame)
    tipo_alerta_frame.pack(pady=10)
    tipo_alerta_var = ttk.StringVar()
    ttk.Radiobutton(tipo_alerta_frame, text="Crise", variable=tipo_alerta_var, value="Crise").pack(side='left', padx=5)
    ttk.Radiobutton(tipo_alerta_frame, text="Inc. Crítico", variable=tipo_alerta_var, value="Inc. Crítico").pack(side='left', padx=5)

    ttk.Label(border_frame, text="Status:", font=("Arial", 10)).pack(pady=10)
    status_alerta_frame = ttk.Frame(border_frame)
    status_alerta_frame.pack(pady=10)
    status_alerta_var = ttk.StringVar()
    ttk.Radiobutton(status_alerta_frame, text="Início", variable=status_alerta_var, value="Início", command=toggle_checkpoint_date).pack(side='left', padx=5)
    ttk.Radiobutton(status_alerta_frame, text="Equipes seguem atuando", variable=status_alerta_var, value="Equipes seguem atuando", command=toggle_checkpoint_date).pack(side='left', padx=5)
    ttk.Radiobutton(status_alerta_frame, text="Em validação", variable=status_alerta_var, value="Em validação", command=toggle_checkpoint_date).pack(side='left', padx=5)
    ttk.Radiobutton(status_alerta_frame, text="Normalizado", variable=status_alerta_var, value="Normalizado", command=toggle_checkpoint_date).pack(side='left', padx=5)

    checkpoint_date_label = ttk.Label(border_frame, text="Data do Checkpoint:", font=("Arial", 10))
    checkpoint_date_entry = ttk.Entry(border_frame, font=("Arial", 10))

    impacto_normalizado_label = ttk.Label(border_frame, text="Mensagem de normalização:", font=("Arial", 10))
    impacto_normalizado_entry = ttk.Entry(border_frame, font=("Arial", 10))

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
    create_tag_checkboxes()

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
