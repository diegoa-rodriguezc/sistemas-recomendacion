from sqlalchemy import Column, Integer, String, Float, BIGINT, TIMESTAMP, BigInteger
from db.database import Base

class User(Base):
    """
    Tabla de User

    Atributos:
        userId (int): Identificador único.
        userName (str): Nombre usuario.
    """
    __tablename__ = "user"

    #id = Column(Integer, primary_key=True, index=False, autoincrement=True)
    userId = Column(BigInteger, primary_key=True, index=False, autoincrement=False)
    userName  = Column(String, index=False, default="")

    def __init__(self, userId, userName ):
        self.userId = userId
        self.userName = userName 

class rating(Base):
    """
    Tabla de rating

    Atributos:
        id (int): Identificador único.
        userId (int): Identificador de usuario.
        movieId (int): Identificador de película.
        rating (float): Calificación de película.
        timestamp (datetime): Fecha y hora de calificación.
    """
    __tablename__ = "rating"

    id = Column(BigInteger, primary_key=True, index=False, autoincrement=True)
    userId = Column(BigInteger, index=True)
    movieId = Column(BigInteger, index=True)
    rating = Column(Float, index=False)
    timestamp = Column(TIMESTAMP, index=False)

    def __init__(self, id, userId, movieId, rating, timestamp):
        self.id = id
        self.userId = userId
        self.movieId = movieId
        self.rating = rating
        self.timestamp = timestamp

class movie(Base):
    """
    Tabla de movie (películas)

    Atributos:
        movieId (int): Identificador de película.
        title (str): Nombre de película.
        genres (str): Genero(s) de la película.
    """
    __tablename__ = "movie"

    movieId = Column(BigInteger, primary_key=True, index=False, autoincrement=False)
    title = Column(String, index=False)
    genres = Column(String, index=False)

    def __init__(self, movieId, title, genres):
        self.movieId = movieId
        self.title = title
        self.genres = genres