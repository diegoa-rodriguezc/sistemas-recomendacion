from sqlalchemy import text
from sqlalchemy.orm import Session
from db.database import engine
from db.models import User as DBUser, Business as DBBusiness, Review as DBReview, Tip as DBTip, Checkin as DBCheckin
from db.session import get_db

"""
Carga tablas en la base de datos
"""

def create_user(db: Session, user_data: list):
    
    # Limpiar tabla antes de insertar información
    db.query(DBUser).delete()

    # Cargar los datos de usuarios
    users = [
        DBUser(
            user_id=user_id,
            name=name,
            review_count=review_count,
            yelping_since=yelping_since,
            friends=friends,
            useful=useful,
            funny=funny,
            cool=cool,
            fans=fans,
            elite=elite,
            average_stars=average_stars,
            compliment_hot=compliment_hot,
            compliment_more=compliment_more,
            compliment_profile=compliment_profile,
            compliment_cute=compliment_cute,
            compliment_list=compliment_list,
            compliment_note=compliment_note,
            compliment_plain=compliment_plain,
            compliment_cool=compliment_cool,
            compliment_funny=compliment_funny,
            compliment_writer=compliment_writer,
            compliment_photos=compliment_photos
        ) for user_id, name, review_count, yelping_since, friends, useful, funny, cool, fans, elite, average_stars,
        compliment_hot, compliment_more, compliment_profile, compliment_cute, compliment_list, compliment_note, 
        compliment_plain, compliment_cool, compliment_funny, compliment_writer, compliment_photos in user_data
    ]
    
    db.add_all(users)
    db.commit()


def create_rating(db: Session, rating_data: list):
    # Limpiar tabla antes de insertar información
    db.query(DBMovie).delete()

    ratings = [DBRating(userId=userId,
                        movieId=movieId,
                        rating=rating,
                        timestamp=timestamp) 
                        for userId,movieId,rating,timestamp in rating_data.itertuples(index=False, name=None)]
    db.add_all(ratings)
    db.commit()


    db.query(DBUser).delete()
    # Insertar userId únicos en la tabla user desde rating
    db.execute(text("""
        INSERT INTO "user" ("userId")
        SELECT DISTINCT "userId"
        FROM   rating 
        ORDER BY "userId" ASC;
    """))
    db.commit()

def create_data(db: Session, user_data: list, business_data: list, review_data: list, tip_data: list, checkin_data: list):
    """
    Carga los datos en las tablas de la base de datos después de limpiarlas.

    Parámetros:
        db: Session - La sesión de la base de datos.
        user_data: list - Lista de datos de usuarios.
        business_data: list - Lista de datos de negocios.
        review_data: list - Lista de datos de reseñas.
        tip_data: list - Lista de datos de recomendaciones (tips).
        checkin_data: list - Lista de datos de check-ins.
    """
    
    # Limpiar las tablas antes de insertar la nueva información
    db.query(DBUser).delete()
    db.query(DBBusiness).delete()
    db.query(DBReview).delete()
    db.query(DBTip).delete()
    db.query(DBCheckin).delete()

    # Cargar los datos de usuarios
    users = [
        DBUser(
            user_id=user_id,
            name=name,
            review_count=review_count,
            yelping_since=yelping_since,
            friends=friends,
            useful=useful,
            funny=funny,
            cool=cool,
            fans=fans,
            elite=elite,
            average_stars=average_stars,
            compliment_hot=compliment_hot,
            compliment_more=compliment_more,
            compliment_profile=compliment_profile,
            compliment_cute=compliment_cute,
            compliment_list=compliment_list,
            compliment_note=compliment_note,
            compliment_plain=compliment_plain,
            compliment_cool=compliment_cool,
            compliment_funny=compliment_funny,
            compliment_writer=compliment_writer,
            compliment_photos=compliment_photos
        ) for user_id, name, review_count, yelping_since, friends, useful, funny, cool, fans, elite, average_stars,
        compliment_hot, compliment_more, compliment_profile, compliment_cute, compliment_list, compliment_note, 
        compliment_plain, compliment_cool, compliment_funny, compliment_writer, compliment_photos in user_data
    ]
    
    # Cargar los datos de negocios
    businesses = [
        DBBusiness(
            business_id=business_id,
            name=name,
            address=address,
            city=city,
            state=state,
            postal_code=postal_code,
            latitude=latitude,
            longitude=longitude,
            stars=stars,
            review_count=review_count,
            is_open=is_open,
            attributes=attributes,
            categories=categories,
            hours=hours
        ) for business_id, name, address, city, state, postal_code, latitude, longitude, stars, review_count,
        is_open, attributes, categories, hours in business_data
    ]
    
    # Cargar los datos de reseñas (Reviews)
    reviews = [
        DBReview(
            review_id=review_id,
            user_id=user_id,
            business_id=business_id,
            stars=stars,
            date=date,
            text=text,
            useful=useful,
            funny=funny,
            cool=cool
        ) for review_id, user_id, business_id, stars, date, text, useful, funny, cool in review_data
    ]
    
    # Cargar los datos de tips
    tips = [
        DBTip(
            text=text,
            date=date,
            compliment_count=compliment_count,
            business_id=business_id,
            user_id=user_id
        ) for text, date, compliment_count, business_id, user_id in tip_data
    ]
    
    # Cargar los datos de checkins
    checkins = [
        DBCheckin(
            business_id=business_id,
            date=date
        ) for business_id, date in checkin_data
    ]
    
    # Agregar todos los datos a la base de datos
    db.add_all(users)
    db.add_all(businesses)
    db.add_all(reviews)
    db.add_all(tips)
    db.add_all(checkins)
    
    # Confirmar los cambios en la base de datos
    db.commit()