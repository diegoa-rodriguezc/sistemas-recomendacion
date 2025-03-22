from sqlalchemy.orm import Session
from database import SessionLocal

# Función para obtener una sesión de base de datos
def get_db():
    """
    Devuelve una sesión de base de datos.

    Returns:
        Session: Una instancia de sesión de base de datos.
    """
    db = SessionLocal()
    try:
        yield db
    except Exception as error:
        print('ERROR', error)
        raise
    finally:
        db.close()
