"""Crea el primer administrador. Uso: python crear_usuario.py"""
import getpass
from app.main import crear_usuario, reg
u = input("Usuario: ").strip()
correo = input("Correo para recuperar la contraseña: ").strip()
c1 = getpass.getpass("Contraseña de mínimo 10 caracteres: ")
c2 = getpass.getpass("Repite la contraseña: ")
if c1 != c2: raise SystemExit("Las contraseñas no coinciden. No se creó el usuario.")
try: crear_usuario(u, c1, "admin", correo)
except ValueError as e: raise SystemExit("No se creó el usuario: " + str(e))
reg(None, "consola", "administrador_creado", u.lower())
print("Administrador creado:", u.lower())
