from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Cadena de conexión a una Base de datos MS SQL Server (reemplazar los valores según corresponda)
# DATABASE_URL = ("mssql+pyodbc://user:password@host:ip/databasename?driver=ODBC+Driver+17+for+SQL+Server")

# Cadena de conexión a una Base de datos PostgreSQL (reemplazar los valores según corresponda)
DATABASE_URL = "postgresql://postgres:laboratorio@localhost:5432/sr_movielens"

# Crear el motor de conexión
engine = create_engine(DATABASE_URL,pool_pre_ping=True)

# Crear la clase base para los modelos
Base = declarative_base()

# Crear sesión local
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
