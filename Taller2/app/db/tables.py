# python -m db.tables

from db.database import engine
from db.models import Base

"""
Crea tablas en la base de datos
"""
Base.metadata.create_all(bind=engine)