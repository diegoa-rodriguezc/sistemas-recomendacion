import sys
import pandas as pd
import argparse
from sqlalchemy.orm import Session
from db.database import engine
from db.session import get_db
from db.models import User as DBUser, Business as DBBusiness, Review as DBReview, Tip as DBTip, Checkin as DBCheckin
from db.loadtables import create_user

def main():
    # Usar argparse para obtener los parámetros de la línea de comandos
    parser = argparse.ArgumentParser(description="Carga datos en la base de datos")
    parser.add_argument('user_file', help="Ruta al archivo CSV de usuarios")
    #parser.add_argument('business_file', help="Ruta al archivo CSV de negocios")
    #parser.add_argument('review_file', help="Ruta al archivo CSV de reseñas")
    #parser.add_argument('tip_file', help="Ruta al archivo CSV de recomendaciones")
    #parser.add_argument('checkin_file', help="Ruta al archivo CSV de check-ins")
    
    args = parser.parse_args()

    # Crear una sesión de base de datos
    db = next(get_db())

    # Cargar los datos desde los archivos CSV proporcionados por línea de comandos
    #user_df = pd.read_csv(args.user_file)
    user_data = pd.read_json(args.user_file, lines=True)
    #business_df = pd.read_csv(args.business_file)
    #review_df = pd.read_csv(args.review_file)
    #tip_df = pd.read_csv(args.tip_file)
    #checkin_df = pd.read_csv(args.checkin_file)

    # Convertir DataFrames a listas de diccionarios (o tuplas)
    #user_data = user_df.to_records(index=False).tolist()
    #business_data = business_df.to_records(index=False).tolist()
    #review_data = review_df.to_records(index=False).tolist()
    #tip_data = tip_df.to_records(index=False).tolist()
    #checkin_data = checkin_df.to_records(index=False).tolist()

    # Llamar a la función que carga los datos
    #create_data(db, user_data, business_data, review_data, tip_data, checkin_data)
    create_user(db, user_data)
    print("Datos cargados exitosamente!")

if __name__ == "__main__":
    main()
