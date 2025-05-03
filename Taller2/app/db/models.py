from sqlalchemy import Column, Integer, String, Float, BIGINT, TIMESTAMP, BigInteger, Boolean, JSON, ForeignKey
from sqlalchemy.orm import relationship

from db.database import Base

class Business(Base):
    """
    Tabla de Business

    Atributos:
        business_id (str): Identificador único del negocio.
        name (str): Nombre del negocio.
        address (str): Dirección completa del negocio.
        city (str): Ciudad.
        state (str): Código de estado (3 caracteres).
        postal_code (str): Código postal.
        latitude (float): Latitud.
        longitude (float): Longitud.
        stars (float): Calificación en estrellas (con incrementos de medio punto).
        review_count (int): Número de reseñas.
        is_open (int): 0 o 1 para cerrado o abierto, respectivamente.
        attributes (dict): Atributos del negocio, algunos valores podrían ser objetos.
        categories (list): Categorías del negocio como lista de cadenas.
        hours (dict): Horarios del negocio organizados por día.
    """
    __tablename__ = 'business'

    business_id = Column(String(22), primary_key=True, index=True, comment="Identificador único del negocio (22 caracteres).")
    name = Column(String, comment="Nombre del negocio.")
    address = Column(String, comment="Dirección completa del negocio.")
    city = Column(String, comment="Ciudad donde se ubica el negocio.")
    state = Column(String(3), comment="Código de estado de 3 caracteres.")
    postal_code = Column(String, comment="Código postal del negocio.")
    latitude = Column(Float, comment="Latitud del negocio.")
    longitude = Column(Float, comment="Longitud del negocio.")
    stars = Column(Float, comment="Calificación del negocio en estrellas, redondeado a medio punto.")
    review_count = Column(Integer, comment="Número de reseñas del negocio.")
    is_open = Column(Integer, comment="0 si está cerrado, 1 si está abierto.")
    attributes = Column(JSON, comment="Atributos adicionales del negocio como un objeto.")
    categories = Column(JSON, comment="Lista de categorías del negocio.")
    hours = Column(JSON, comment="Horario de apertura del negocio organizado por días.")

    def __init__(self, business_id, name, address, city, state, postal_code, latitude, longitude, stars, review_count, is_open, attributes, categories, hours):
        self.business_id = business_id
        self.name = name
        self.address = address
        self.city = city
        self.state = state
        self.postal_code = postal_code
        self.latitude = latitude
        self.longitude = longitude
        self.stars = stars
        self.review_count = review_count
        self.is_open = is_open
        self.attributes = attributes
        self.categories = categories
        self.hours = hours

class User(Base):
    """
    Tabla de User

    Atributos:
        user_id (str): Identificador único del usuario (22 caracteres).
        name (str): Nombre del usuario.
        review_count (int): Número de reseñas que el usuario ha escrito.
        yelping_since (str): Fecha de cuando el usuario se unió a Yelp, formato YYYY-MM-DD.
        friends (list): Lista de usuarios amigos.
        useful (int): Número de votos útiles enviados por el usuario.
        funny (int): Número de votos graciosos enviados por el usuario.
        cool (int): Número de votos cool enviados por el usuario.
        fans (int): Número de fans del usuario.
        elite (list): Años en los que el usuario fue considerado élite.
        average_stars (float): Calificación promedio de todas las reseñas del usuario.
        compliment_* (int): Número de cada tipo de cumplido recibido por el usuario.
    """
    __tablename__ = 'user'

    user_id = Column(String(22), primary_key=True, index=True, comment="Identificador único del usuario (22 caracteres).")
    name = Column(String, comment="Nombre del usuario.")
    review_count = Column(Integer, comment="Número de reseñas que el usuario ha escrito.")
    yelping_since = Column(String, comment="Fecha de cuando el usuario se unió a Yelp (formato YYYY-MM-DD).")
    friends = Column(JSON, comment="Lista de usuarios amigos (IDs).")
    useful = Column(Integer, comment="Número de votos útiles enviados por el usuario.")
    funny = Column(Integer, comment="Número de votos graciosos enviados por el usuario.")
    cool = Column(Integer, comment="Número de votos cool enviados por el usuario.")
    fans = Column(Integer, comment="Número de fans del usuario.")
    elite = Column(JSON, comment="Años en los que el usuario fue considerado élite.")
    average_stars = Column(Float, comment="Promedio de calificación de todas las reseñas del usuario.")
    
    # Complimentos recibidos por el usuario (diferentes tipos)
    compliment_hot = Column(Integer, comment="Número de cumplidos calientes recibidos.")
    compliment_more = Column(Integer, comment="Número de cumplidos de 'más' recibidos.")
    compliment_profile = Column(Integer, comment="Número de cumplidos de perfil recibidos.")
    compliment_cute = Column(Integer, comment="Número de cumplidos de 'lindo' recibidos.")
    compliment_list = Column(Integer, comment="Número de cumplidos de lista recibidos.")
    compliment_note = Column(Integer, comment="Número de cumplidos de notas recibidos.")
    compliment_plain = Column(Integer, comment="Número de cumplidos 'plano' recibidos.")
    compliment_cool = Column(Integer, comment="Número de cumplidos 'cool' recibidos.")
    compliment_funny = Column(Integer, comment="Número de cumplidos graciosos recibidos.")
    compliment_writer = Column(Integer, comment="Número de cumplidos de escritor recibidos.")
    compliment_photos = Column(Integer, comment="Número de cumplidos de fotos recibidos.")
    
    def __init__(self, user_id, name, review_count, yelping_since, friends, useful, funny, cool, fans, elite, average_stars,
                 compliment_hot, compliment_more, compliment_profile, compliment_cute, compliment_list, compliment_note, 
                 compliment_plain, compliment_cool, compliment_funny, compliment_writer, compliment_photos):
        self.user_id = user_id
        self.name = name
        self.review_count = review_count
        self.yelping_since = yelping_since
        self.friends = friends
        self.useful = useful
        self.funny = funny
        self.cool = cool
        self.fans = fans
        self.elite = elite
        self.average_stars = average_stars
        self.compliment_hot = compliment_hot
        self.compliment_more = compliment_more
        self.compliment_profile = compliment_profile
        self.compliment_cute = compliment_cute
        self.compliment_list = compliment_list
        self.compliment_note = compliment_note
        self.compliment_plain = compliment_plain
        self.compliment_cool = compliment_cool
        self.compliment_funny = compliment_funny
        self.compliment_writer = compliment_writer
        self.compliment_photos = compliment_photos

class Review(Base):
    """
    Tabla de Review

    Atributos:
        review_id (str): Identificador único de la reseña.
        user_id (str): Identificador único del usuario, mapeado a un usuario en user.json.
        business_id (str): Identificador único del negocio, mapeado a un negocio en business.json.
        stars (int): Calificación en estrellas.
        date (str): Fecha de la reseña, con formato YYYY-MM-DD.
        text (str): El contenido de la reseña.
        useful (int): Número de votos útiles recibidos.
        funny (int): Número de votos graciosos recibidos.
        cool (int): Número de votos "cool" recibidos.
    """
    __tablename__ = 'review'

    review_id = Column(String(22), primary_key=True, index=True, comment="Identificador único de la reseña (22 caracteres).")
    #user_id = Column(String(22), ForeignKey('user.user_id'), index=True, comment="Identificador único del usuario que escribió la reseña.")
    user_id = Column(String(22), index=True, comment="Identificador único del usuario que escribió la reseña.")
    #business_id = Column(String(22), ForeignKey('business.business_id'), index=True, comment="Identificador único del negocio sobre el que se escribió la reseña.")
    business_id = Column(String(22), index=True, comment="Identificador único del negocio sobre el que se escribió la reseña.")
    stars = Column(Integer, comment="Calificación en estrellas de la reseña.")
    date = Column(String, comment="Fecha de la reseña, con formato YYYY-MM-DD.")
    text = Column(String, comment="Contenido de la reseña.")
    useful = Column(Integer, comment="Número de votos útiles recibidos.")
    funny = Column(Integer, comment="Número de votos graciosos recibidos.")
    cool = Column(Integer, comment="Número de votos 'cool' recibidos.")
    
    # Relaciones para hacer el join con las tablas de User y Business
    #user = relationship("User", backref="reviews")
    #business = relationship("Business", backref="reviews")

    def __init__(self, review_id, user_id, business_id, stars, date, text, useful, funny, cool):
        self.review_id = review_id
        self.user_id = user_id
        self.business_id = business_id
        self.stars = stars
        self.date = date
        self.text = text
        self.useful = useful
        self.funny = funny
        self.cool = cool

class Checkin(Base):
    """
    Tabla de Checkin

    Atributos:
        business_id (str): Identificador único del negocio (22 caracteres), mapeado a un negocio en business.json.
        date (str): Lista separada por comas de timestamps (formato YYYY-MM-DD HH:MM:SS) de cada checkin.
    """
    __tablename__ = 'checkin'

    business_id = Column(String(22), primary_key=True, index=True, comment="Identificador único del negocio (22 caracteres).")
    date = Column(String, comment="Lista separada por comas de timestamps (formato YYYY-MM-DD HH:MM:SS) de cada checkin.")
    
    def __init__(self, business_id, date):
        self.business_id = business_id
        self.date = date

class Tip(Base):
    """
    Tabla de Tip

    Atributos:
        id (int): Identificador único.
        text (str): Texto de la recomendación (tip).
        date (str): Fecha de cuando se escribió la recomendación, en formato YYYY-MM-DD.
        compliment_count (int): Número de cumplidos que ha recibido la recomendación.
        business_id (str): Identificador único del negocio, mapeado a un negocio en business.json.
        user_id (str): Identificador único del usuario, mapeado a un usuario en user.json.
    """
    __tablename__ = 'tip'

    # Columnas
    id = Column(BigInteger, primary_key=True, index=False, autoincrement=True)
    text = Column(String, comment="Texto de la recomendación (tip).")
    date = Column(String, comment="Fecha de cuando se escribió la recomendación, en formato YYYY-MM-DD.")
    compliment_count = Column(Integer, comment="Número de cumplidos que ha recibido la recomendación.")
    business_id = Column(String(22), index=True, comment="Identificador único del negocio.")
    user_id = Column(String(22), index=True, comment="Identificador único del usuario que escribió la recomendación.")
    # business_id = Column(String(22), ForeignKey('business.business_id'), index=True, comment="Identificador único del negocio.")
    # user_id = Column(String(22), ForeignKey('user.user_id'), index=True, comment="Identificador único del usuario que escribió la recomendación.")

    # Relaciones
    #business = relationship("Business", backref="tips")
    #user = relationship("User", backref="tips")

    def __init__(self, text, date, compliment_count, business_id, user_id):
        self.text = text
        self.date = date
        self.compliment_count = compliment_count
        self.business_id = business_id
        self.user_id = user_id