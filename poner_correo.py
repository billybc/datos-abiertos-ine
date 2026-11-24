"""Pone o cambia el correo de un usuario que ya existe. Uso: python poner_correo.py"""
from sqlalchemy import select
from app.main import engine, U, EMAIL, reg
u = input("Usuario: ").strip().lower(); correo = input("Correo: ").strip().lower()
if not EMAIL.match(correo): raise SystemExit("Correo no válido.")
with engine.begin() as c:
    if c.execute(select(U.c.id).where(U.c.correo == correo, U.c.usuario != u)).first(): raise SystemExit("Ese correo ya lo usa otro usuario.")
    n = c.execute(U.update().where(U.c.usuario == u).values(correo=correo)).rowcount
if not n: raise SystemExit("Ese usuario no existe.")
reg(None, "consola", "correo_actualizado", u); print("Correo guardado para", u)
