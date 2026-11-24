import os, smtplib, ssl
from email.message import EmailMessage

def enviar(para, asunto, texto):
    """Envía un correo por SMTP. Sin SMTP_HOST solo muestra el mensaje en la consola, y únicamente en modo local."""
    host = os.getenv("SMTP_HOST")
    if not host:
        if os.getenv("COOKIE_SECURE", "0") != "1":
            print(f"\n[CORREO NO CONFIGURADO, MODO LOCAL]\nPara: {para}\nAsunto: {asunto}\n{texto}\n")
        else:
            print("ADVERTENCIA: falta configurar SMTP_HOST, no se pudo enviar el correo de recuperación.")
        return False
    usuario, clave = os.getenv("SMTP_USER", ""), os.getenv("SMTP_PASS", "")
    msg = EmailMessage()
    msg["From"] = os.getenv("SMTP_FROM") or usuario
    msg["To"] = para; msg["Subject"] = asunto; msg.set_content(texto)
    puerto = int(os.getenv("SMTP_PORT", "587")); ctx = ssl.create_default_context()
    if puerto == 465:
        with smtplib.SMTP_SSL(host, puerto, context=ctx, timeout=20) as s:
            if usuario: s.login(usuario, clave)
            s.send_message(msg)
    else:
        with smtplib.SMTP(host, puerto, timeout=20) as s:
            s.starttls(context=ctx)
            if usuario: s.login(usuario, clave)
            s.send_message(msg)
    return True
