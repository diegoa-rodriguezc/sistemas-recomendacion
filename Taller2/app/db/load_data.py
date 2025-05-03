import sys
import pandas as pd
import argparse
from sqlalchemy.orm import Session
from db.database import engine
from db.session import get_db
from db.models import User as DBUser, Business as DBBusiness, Review as DBReview, Tip as DBTip, Checkin as DBCheckin
from db.loadtables import create_user

from tqdm import tqdm  # Importar tqdm para la barra de progreso


def main1():
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
    
    # Barra de progreso para la inserción de datos
    # Usamos tqdm para envolver el bucle de inserción de datos
    print("Cargando datos de usuarios...")
    for user in tqdm(user_data, desc="Usuarios", unit="registro"):
        db.add(DBUser(**user))
    
    # Confirmar los cambios en la base de datos
    db.commit()

    print("Datos cargados exitosamente!")

def clear_data(db: Session):
    """
    Elimina todos los registros de las tablas relevantes antes de insertar nuevos datos.
    """
    print("Eliminando datos existentes...")

    # Lista de tablas a limpiar
    #tables = [DBUser, DBBusiness, DBReview, DBTip, DBCheckin]
    #tables = [DBBusiness, DBReview]
    tables = [DBReview]

    # Usamos tqdm para mostrar una barra de progreso mientras limpiamos las tablas
    for table in tqdm(tables, desc="Eliminando datos", unit="tabla"):
        db.query(table).delete()
        db.commit()  # Confirmamos la eliminación de cada tabla
    print("Datos eliminados correctamente.")

def load_tip(db: Session, tip_data: pd.DataFrame):
    """
    Carga los datos de recomendaciones (tips) en la base de datos.
    """
    print("Cargando datos de tips...")

    # Usamos tqdm para mostrar el progreso mientras insertamos los datos
    """
    for tip in tqdm(tip_data.itertuples(index=False), desc="Cargando tips", unit="registro"):
        db.add(DBTip(
            text = tip.text,
            date = tip.date,
            compliment_count = tip.compliment_count,
            business_id = tip.business_id,
            user_id = tip.user_id
        ))
        """
    for tip in tqdm(tip_data.to_dict(orient="records"), desc="Tips", unit="registro"):
        db.add(DBTip(
        text = tip['text'],
        date = tip['date'],
        compliment_count = tip['compliment_count'],
        business_id = tip['business_id'],
        user_id = tip['user_id'])
        )

    # Confirmar los cambios en la base de datos
    db.commit()
    print("Datos cargados exitosamente!")

def load_checkin(db: Session, checkin_data: pd.DataFrame):
    """
    Carga los datos de recomendaciones (checkin) en la base de datos.
    """
    print("Cargando datos de checkin...")

    # Usamos tqdm para mostrar el progreso mientras insertamos los datos
    for checkin in tqdm(checkin_data.to_dict(orient="records"), desc="Checkin", unit="registro"):
        db.add(DBCheckin(
            business_id = checkin['business_id'],
            date = checkin['date']
            )
        )

    # Confirmar los cambios en la base de datos
    db.commit()
    print("Datos cargados exitosamente!")

def load_user(db: Session, user_data: pd.DataFrame):
    """
    Carga los datos de recomendaciones (user) en la base de datos.
    """
    print("Cargando datos de user...")

    # Usamos tqdm para mostrar el progreso mientras insertamos los datos
    for user in tqdm(user_data.to_dict(orient="records"), desc="User", unit="registro"):
        db.add(DBUser(
            user_id = user['user_id'],
            name = user['name'],
            review_count = user['review_count'],
            yelping_since = user['yelping_since'],
            friends = user['friends'],
            useful = user['useful'],
            funny = user['funny'],
            cool = user['cool'],
            fans = user['fans'],
            elite = user['elite'],
            average_stars = user['average_stars'],
            compliment_hot = user['compliment_hot'],
            compliment_more = user['compliment_more'],
            compliment_profile = user['compliment_profile'],
            compliment_cute = user['compliment_cute'],
            compliment_list = user['compliment_list'],
            compliment_note = user['compliment_note'],
            compliment_plain = user['compliment_plain'],
            compliment_cool = user['compliment_cool'],
            compliment_funny = user['compliment_funny'],
            compliment_writer = user['compliment_writer'],
            compliment_photos = user['compliment_photos']
            )
        )
        db.commit()

    # Confirmar los cambios en la base de datos
    #db.commit()
    print("Datos cargados exitosamente!")

def load_business(db: Session, business_data: pd.DataFrame):
    """
    Carga los datos de recomendaciones (business) en la base de datos.
    """
    print("Cargando datos de business...")

    # Usamos tqdm para mostrar el progreso mientras insertamos los datos
    for business in tqdm(business_data.to_dict(orient="records"), desc="Business", unit="registro"):
        db.add(DBBusiness(
            business_id = business['business_id'],
            name = business['name'],
            address = business['address'],
            city = business['city'],
            state = business['state'],
            postal_code = business['postal_code'],
            latitude = business['latitude'],
            longitude = business['longitude'],
            stars = business['stars'],
            review_count = business['review_count'],
            is_open = business['is_open'],
            attributes = business['attributes'],
            categories = business['categories'],
            hours = business['hours']
            )
        )
        db.commit()

    # Confirmar los cambios en la base de datos
    #db.commit()
    print("Datos cargados exitosamente!")

def load_review(db: Session, review_data: pd.DataFrame):
    """
    Carga los datos de recomendaciones (review) en la base de datos.
    """
    print("Cargando datos de business...")

    # Usamos tqdm para mostrar el progreso mientras insertamos los datos
    for review in tqdm(review_data.to_dict(orient="records"), desc="Review", unit="registro"):
        db.add(DBReview(
            review_id = review['review_id'],
            user_id = review['user_id'],
            business_id = review['business_id'],
            stars = review['stars'],
            date = review['date'],
            text = review['text'],
            useful = review['useful'],
            funny = review['funny'],
            cool = review['cool']
            )
        )
        db.commit()

    # Confirmar los cambios en la base de datos
    #db.commit()
    print("Datos cargados exitosamente!")

def main():
    # Usar argparse para obtener los parámetros de la línea de comandos
    parser = argparse.ArgumentParser(description="Carga datos en la base de datos")
    
    parser.add_argument('business_file', help="Ruta al archivo de negocios")
    parser.add_argument('checkin_file', help="Ruta al archivo CSV de check-ins")
    parser.add_argument('review_file', help="Ruta al archivo de reseñas")
    parser.add_argument('tip_file', help="Ruta al archivo de recomendaciones")
    parser.add_argument('user_file', help="Ruta al archivo de usuarios")

    args = parser.parse_args()

    # Crear una sesión de base de datos
    db = next(get_db())

    # Limpiar las tablas antes de cargar los nuevos datos
    #clear_data(db)

    ## Cargar los datos desde los archivos proporcionados por línea de comandos
    # tip_data = pd.read_json(args.tip_file, lines=True)
    # load_tip(db, tip_data)
    # del tip_data

    # checkin_data = pd.read_json(args.checkin_file, lines=True)
    # load_checkin(db, checkin_data)
    # del checkin_data

    # user_data = pd.read_json(args.user_file, lines=True)    
    # load_user(db, user_data)
    # del user_data

    # business_data = pd.read_json(args.business_file, lines=True)
    # load_business(db, business_data)
    # del business_data

    chunksize = 10**6  # Lee 1 millón de filas a la vez
    #review_data = pd.read_json(args.review_file, lines=True, chunksize=chunksize)
    ## Procesar cada chunk por separado
    for chunk in review_data:
        # Procesar cada trozo de datos 
        #print(chunk.head())
        load_review(db, chunk)
    del review_data
    
if __name__ == "__main__":
    main()
