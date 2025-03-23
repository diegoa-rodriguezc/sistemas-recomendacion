from sqlalchemy import text
from sqlalchemy.orm import Session
from db.database import engine
from db.models import movie as DBMovie, rating as DBRating, User as DBUser
from db.session import get_db

"""
Carga tablas en la base de datos
"""

def create_movie(db: Session, movie_data: list):
    
    # Limpiar tabla antes de insertar información
    db.query(DBMovie).delete()

    movies = [DBMovie(movieId=movieId,
                      title=title,
                      genres=genres) 
                      for movieId,title,genres in movie_data.itertuples(index=False, name=None)]
    
    db.add_all(movies)
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