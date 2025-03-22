from sqlalchemy import Column, Integer, String, Float, BIGINT, TIMESTAMP
from database import Base

class User(Base):
    """
    Tabla de User

    Atributos:
        userId (int): Identificador único.
        userName (str): Nombre usuario.
    """
    __tablename__ = "user"

    #id = Column(Integer, primary_key=True, index=False, autoincrement=True)
    userId = Column(Integer, primary_key=True, index=False, autoincrement=False)
    userName = Column(String, index=False, default="")

    def __init__(self, userId, userName):
        self.userId = userId
        self.userName = userName

class rating(Base):

    __tablename__ = "rating"

    id = Column(BIGINT, primary_key=True, index=False, autoincrement=True)
    userId = Column(BIGINT, index=True)
    movieId = Column(BIGINT, index=True)
    rating = Column(Float, index=False)
    timestamp = Column(TIMESTAMP, index=False)

    def __init__(self, id, userId, movieId, rating, timestamp):
        self.id = id
        self.userId = userId
        self.movieId = movieId
        self.rating = rating
        self.timestamp = timestamp

class movie(Base):

    __tablename__ = "movie"

    movieId = Column(BIGINT, primary_key=True, index=False, autoincrement=False)
    title = Column(String, index=False)
    genres = Column(String, index=False)

    def __init__(self, movieId, title, genres):
        self.movieId = movieId
        self.title = title
        self.genres = genres