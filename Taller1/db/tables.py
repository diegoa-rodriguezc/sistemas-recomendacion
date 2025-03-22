# python tables.py

from database import engine
from models import Base

"""
Crea tablas en la base de datos
"""
Base.metadata.create_all(bind=engine)