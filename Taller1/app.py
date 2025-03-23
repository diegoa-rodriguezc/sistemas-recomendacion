from fastapi import FastAPI, HTTPException, Form, Depends, Request, Query, File, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.middleware.cors import CORSMiddleware
from typing import List, Dict, Optional
from datetime import datetime, timedelta
import pandas as pd
import numpy as np
import joblib
import os
from pydantic import BaseModel
from sqlalchemy import asc, desc
from sqlalchemy.orm import Session
from db.models import User as DBUser, movie as DBMovie, rating as DBRating
from db.loadtables import create_movie, create_rating
from db.session import get_db
from sqlalchemy import func

# Modelos para la API
class User(BaseModel):
    userId: int
    username: str

class Movie(BaseModel):
    movieId: int
    title: str
    genres: str

class Rating(BaseModel):
    userId: int
    movieId: int
    rating: float
    timestamp: datetime

class NewUser(BaseModel):
    username: str
    rating: List[Dict[str, float]]  # Lista de {movieId: rating}

class RecommendationResult(BaseModel):
    movieId: int
    title: str
    genres: str
    predicted_rating: float
    #explanation: dict  # Información sobre por qué se recomendó este ítem

class PaginatedResponse(BaseModel):
    items: List[RecommendationResult]
    total: int
    limit: int
    offset: int

# Inicializar FastAPI
app = FastAPI(
    title="Sistema de Recomendación de Películas",
    description="API para el Taller 1 de Sistemas de Recomendación"
    )

# Configurar CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Configurar Jinja2 para templates HTML
templates = Jinja2Templates(directory="templates")

# Cargar los modelos de recomendación
MODEL_USER_PATH = "data/modelUser_pearson.joblib"
MODEL_ITEM_PATH = "data/modelItem_pearson.joblib"

model_user = None
model_item = None

try:
    model_user = joblib.load(MODEL_USER_PATH)
    model_item = joblib.load(MODEL_ITEM_PATH)
except Exception as e:
    print(f"Error cargando los modelos: {e}")

# Variable global para almacenar en caché las recomendaciones
recommendations_cache = {}

# Tiempo de expiración de la caché (por ejemplo, 1 hora)
CACHE_EXPIRY = timedelta(hours=1)

# Función para obtener el conjunto de usuarios y el ID máximo
def get_users_set_and_max_id(db: Session):
    
    max_id_result = db.query(func.max(DBUser.userId)).scalar()
    max_user_id = max_id_result if max_id_result else 0

    users_set = {user_id for (user_id,) in db.query(DBUser.userId).all()}

    return users_set, max_user_id

# Función para obtener un diccionario de películas
def get_movies_dict(db: Session):
    movies = db.query(DBMovie).all()
    return {
        movie.movieId: {
            'title': movie.title,
            'genres': movie.genres
        } for movie in movies
    }

def get_from_cache(key):
    if key in recommendations_cache:
        timestamp, data = recommendations_cache[key]
        # Verificar si la caché ha expirado
        if datetime.now() - timestamp < CACHE_EXPIRY:
            return data
        else:
            # Borrar caché expirada
            del recommendations_cache[key]
    return None

def set_in_cache(key, data):
    recommendations_cache[key] = (datetime.now(), data)

# Función para obtener las películas más populares (para nuevos usuarios)
def get_popular_movies(db: Session, n=20):
    # Contar número de ratings por película
    popular_movies_query = (
        db.query(
            DBRating.movieId,
            func.count(DBRating.id).label('count')
        )
        .group_by(DBRating.movieId)
        .order_by(func.count(DBRating.id).desc())
        .limit(n)
    )
    
    popular_movie_ids = [movie.movieId for movie in popular_movies_query]
    
    # Obtener información de las películas populares
    movies = (
        db.query(DBMovie)
        .filter(DBMovie.movieId.in_(popular_movie_ids))
        .all()
    )
    
    # Crear resultado
    result = []
    for movie in movies:
        result.append({
            'movieId': movie.movieId,
            'title': movie.title,
            'genres': movie.genres
        })
    
    return result

# Función para obtener el historial de ratings de un usuario
def get_user_ratings(db: Session, userId):
    # Obtener los ratings del usuario junto con la información de las películas
    ratings = (
        db.query(DBRating, DBMovie)
        .join(DBMovie, DBRating.movieId == DBMovie.movieId)
        .filter(DBRating.userId == userId)
        .all()
    )
    
    result = []
    for rating, movie in ratings:
        result.append({
            'movieId': movie.movieId,
            'title': movie.title,
            'genres': movie.genres,
            'rating': rating.rating
        })
    
    # Ordenar por rating descendente
    result.sort(key=lambda x: x['rating'], reverse=True)
    
    return result

# Función para generar recomendaciones user-user
def get_user_based_recommendations(db: Session, userId, n=100, filter_ratings=None):
    if model_user is None:
        raise HTTPException(status_code=500, detail="Modelo user-user no disponible")

    user_exists = db.query(func.count(DBUser.userId)).filter(DBUser.userId == userId).scalar() > 0
    
    # Verificar si el usuario existe en los datos
    if not user_exists:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Obtener películas que el usuario ya calificó
    user_rated_query = db.query(DBRating.movieId).filter(DBRating.userId == userId)
    user_rated_movies = {rating.movieId for rating in user_rated_query}

    # Obtener todas las películas
    all_movies_query = db.query(DBMovie.movieId)
    all_movies = {movie.movieId for movie in all_movies_query}

    # Filtrar películas a predecir
    movies_to_predict = all_movies - user_rated_movies
    
    # Para mejor rendimiento, limitar el número de películas a predecir
    movies_sample = list(movies_to_predict)
    if len(movies_sample) > 500:
        # Obtener las películas más populares
        popular_movies_query = (
            db.query(
                DBRating.movieId,
                func.count(DBRating.id).label('count')
            )
            .filter(DBRating.movieId.in_(movies_sample))
            .group_by(DBRating.movieId)
            .order_by(func.count(DBRating.id).desc())
            .limit(500)
        )
        
        movies_sample = [movie.movieId for movie in popular_movies_query]

    # Obtener diccionario de películas
    movies_dict = get_movies_dict(db)

    # Preprocesar el filtro de ratings
    filter_list = None
    if filter_ratings and filter_ratings != 'all':
        # Convertir filter_ratings a una lista de enteros si es una cadena separada por comas
        if isinstance(filter_ratings, str):
            try:
                filter_list = [int(r) for r in filter_ratings.split(',')]
            except ValueError:
                # Si hay un error al convertir, usar el valor original
                filter_list = [int(filter_ratings)]
        else:
            filter_list = [int(filter_ratings)]
        
        print(f"Filtrando resultados por ratings: {filter_list}")

    recommendations = []
    raw_predictions = []  # Almacenar todas las predicciones para filtrar después

    for movieId in movies_sample:
        try:
            # Obtener predicción del modelo
            prediction = model_user.predict(userId, movieId)

            # Si la predicción es None, continuar con la siguiente
            if prediction is None:
                continue

            # Extraer rating estimado y detalles
            pred_rating = prediction.est
            details = prediction.details if hasattr(prediction, 'details') else {}

            # Validar si la predicción es imposible
            if details.get('was_impossible', True):
               continue  # Omitir predicciones imposibles

            if movieId in movies_dict:
                raw_predictions.append({
                    'movieId': int(movieId),
                    'title': movies_dict[movieId]['title'],
                    'genres': movies_dict[movieId]['genres'],
                    'predicted_rating': float(pred_rating)
                })
        except Exception as e:
            print(f"❌ UserBaseRecommendations: Error prediciendo para película {movieId}: {e}")
            continue  # Continuar con la siguiente película si hay error

    # Aplicar filtro si existe
    if filter_list:
        for item in raw_predictions:
            rating_value = round(item['predicted_rating'],1)
            
            for filter_value in filter_list:
                if filter_value <= rating_value < filter_value + 1:
                    recommendations.append({
                        'movieId': item['movieId'],
                        'title': item['title'],
                        'genres': item['genres'],
                        'predicted_rating': round(item['predicted_rating'], 2)
                    })
                    break  # Salir del bucle una vez que se ha encontrado una coincidencia
    else:
        # Si no hay filtro, usar todas las predicciones
        recommendations = [{
            'movieId': item['movieId'],
            'title': item['title'],
            'genres': item['genres'],
            'predicted_rating': round(item['predicted_rating'], 2)
        } for item in raw_predictions]

    # Ordenar por rating estimado
    recommendations.sort(key=lambda x: x['predicted_rating'], reverse=True)

    print(f"🔹 UBR Total recomendaciones generadas: {len(recommendations)}")
    if filter_list:
        print(f"🔹 UBR Recomendaciones después del filtro {filter_list}: {len(recommendations)}")

    # Limitar al número solicitado
    return recommendations[:n]

# Función para generar recomendaciones item-item
def get_item_based_recommendations(db: Session, userId, n=100, filter_ratings=None):
    if model_item is None:
        raise HTTPException(status_code=500, detail="Modelo item-item no disponible")

    # Obtener el conjunto de usuarios
    users_set, _ = get_users_set_and_max_id(db)

    # Verificar si el usuario existe en los datos
    if userId not in users_set:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Obtener películas que el usuario ya calificó
    user_rated_query = db.query(DBRating.movieId).filter(DBRating.userId == userId)
    user_rated_movies = {rating.movieId for rating in user_rated_query}

    # Obtener todas las películas
    all_movies_query = db.query(DBMovie.movieId)
    all_movies = {movie.movieId for movie in all_movies_query}

    # Filtrar películas a predecir
    movies_to_predict = all_movies - user_rated_movies
    
    # Para mejor rendimiento, limitar el número de películas a predecir
    movies_sample = list(movies_to_predict)
    if len(movies_sample) > 500:
        # Obtener las películas más populares
        popular_movies_query = (
            db.query(
                DBRating.movieId,
                func.count(DBRating.id).label('count')
            )
            .filter(DBRating.movieId.in_(movies_sample))
            .group_by(DBRating.movieId)
            .order_by(func.count(DBRating.id).desc())
            .limit(500)
        )
        
        movies_sample = [movie.movieId for movie in popular_movies_query]

    # Obtener diccionario de películas
    movies_dict = get_movies_dict(db)

    # Preprocesar el filtro de ratings
    filter_list = None
    if filter_ratings and filter_ratings != 'all':
        # Convertir filter_ratings a una lista de enteros si es una cadena separada por comas
        if isinstance(filter_ratings, str):
            try:
                filter_list = [int(r) for r in filter_ratings.split(',')]
            except ValueError:
                # Si hay un error al convertir, usar el valor original
                filter_list = [int(filter_ratings)]
        else:
            filter_list = [int(filter_ratings)]
        
        print(f"Filtrando resultados por ratings: {filter_list}")

    recommendations = []
    raw_predictions = []  # Almacenar todas las predicciones para filtrar después

    for movieId in movies_sample:
        try:
            # Obtener predicción del modelo
            prediction = model_item.predict(userId, movieId)

            # Verificar si el modelo devolvió un resultado válido
            if prediction is None:
                continue

            # Extraer rating estimado y detalles
            pred_rating = getattr(prediction, "est", None)
            details = getattr(prediction, "details", {})

            # Si no hay rating, continuar
            if pred_rating is None:
                continue

            # Validar si la predicción es imposible
            if details.get('was_impossible', True):
                continue  # Omitir predicciones imposibles
            
            if movieId in movies_dict:
                raw_predictions.append({
                    'movieId': int(movieId),
                    'title': movies_dict[movieId]['title'],
                    'genres': movies_dict[movieId]['genres'],
                    'predicted_rating': float(pred_rating)
                })
        except Exception as e:
            print(f"❌ ItemBaseRecommendations: Error prediciendo para película {movieId}: {e}")
            continue  # Continuar con la siguiente película si hay error
    
    # For debugging
    if filter_list:
        for filter_value in filter_list:
            ratings_in_range = [item['predicted_rating'] for item in raw_predictions 
                            if filter_value <= round(item['predicted_rating'], 1) < filter_value + 1]
            print(f"Filter {filter_value}: Found {len(ratings_in_range)} items with ratings {min(ratings_in_range, default=0)}-{max(ratings_in_range, default=0)}")

    # Aplicar filtro si existe
    if filter_list:
        for item in raw_predictions:
            rating_value = round(item['predicted_rating'],1)
            
            for filter_value in filter_list:
                if filter_value <= rating_value < filter_value + 1:
                    recommendations.append({
                        'movieId': item['movieId'],
                        'title': item['title'],
                        'genres': item['genres'],
                        'predicted_rating': round(item['predicted_rating'], 2)
                    })
                    break  # Salir del bucle una vez que se ha encontrado una coincidencia
    else:
        # Si no hay filtro, usar todas las predicciones
        recommendations = [{
            'movieId': item['movieId'],
            'title': item['title'],
            'genres': item['genres'],
            'predicted_rating': round(item['predicted_rating'], 2)
        } for item in raw_predictions]

    # Ordenar por rating estimado
    recommendations.sort(key=lambda x: x['predicted_rating'], reverse=True)

    print(f"🔹 IBR Total recomendaciones generadas: {len(recommendations)}")
    if filter_list:
        print(f"🔹 IBR Recomendaciones después del filtro {filter_list}: {len(recommendations)}")

    # Limitar al número solicitado
    return recommendations[:n]

# Rutas de la API
@app.get("/", response_class=HTMLResponse)
async def read_root(request: Request):
    return templates.TemplateResponse("login.html", {"request": request})

@app.post("/login")
async def login(request: Request, userId: int = Form(...), db: Session = Depends(get_db)):
    # Verificar el usuario en la base de datos
    user = db.query(DBUser).filter(DBUser.userId == userId).first()
    
    if not user:
        return templates.TemplateResponse("login.html", {"request": request, "error": "Usuario no encontrado"})
    
    response = RedirectResponse(url=f"/index?userId={userId}", status_code=303)
    response.set_cookie(key="userId", value=str(userId))  # Guardar sesión
    return response

@app.get("/logout")
async def logout(request: Request):
    # Intentar obtener el userId de la cookie
    userId = request.cookies.get("userId")
    if userId:
        # Convertir a entero si existe
        try:
            userId = int(userId)
            print('userId',userId)
            # Limpiar la caché para este usuario
            keys_to_remove = []
            for key in recommendations_cache.keys():
                if key.startswith(f"user_{userId}"):
                    keys_to_remove.append(key)
            
            for key in recommendations_cache.keys():
                if key.startswith(f"item_{userId}"):
                    keys_to_remove.append(key)

            # Eliminar las claves de caché de este usuario
            for key in keys_to_remove:
                del recommendations_cache[key]
            
        except (ValueError, TypeError):
            # Si la cookie no contiene un entero válido, ignorar
            pass
    
    # Redirigir y eliminar cookie
    response = RedirectResponse(url="/")
    response.delete_cookie("userId")
    return response

@app.get("/index", response_class=HTMLResponse)
async def index(request: Request, userId: int):
    return templates.TemplateResponse("index.html", {"request": request, "userId": userId})

@app.get("/users", response_model=List[User])
async def get_users(db: Session = Depends(get_db), limit: int = 300):
    users_db = db.query(DBUser).limit(limit).all()
    return [{"userId": user.userId, "username": user.userName or f"Usuario {user.userId}"} for user in users_db]

@app.get("/movies", response_model=List[Movie])
async def get_movies(
    db: Session = Depends(get_db), 
    limit: int = Query(100, gt=0, le=1000),  # Limita el número de resultados entre 1 y 1000
    offset: int = Query(0, ge=0),  # Permite paginación
    order: str = Query("asc", regex="^(asc|desc)$")  # Permite ordenar dinámicamente
    ):
    
    order_by_column = asc(DBMovie.title) if order == "asc" else desc(DBMovie.title)

    movies_db = db.query(DBMovie).order_by(order_by_column).offset(offset).limit(limit).all()

    return [{"movieId": movie.movieId, "title": movie.title, "genres": movie.genres} for movie in movies_db]

@app.get("/popular-movies", response_model=List[Movie])
async def get_popular(db: Session = Depends(get_db)):
    return get_popular_movies(db)

@app.get("/user/{userId}", response_model=User)
async def get_user(userId: int, db: Session = Depends(get_db)):
    try:
        user = db.query(DBUser).filter(DBUser.userId == userId).first()
       
        if user is None:
            raise HTTPException(status_code=404, detail="Usuario no encontrado")
        
        user_dict = {
            "userId": user.userId,
            "username": user.userName if (user.userName) else f"Usuario #{userId}" # if hasattr(user, 'userName ') else f"Usuario #{userId}"
        }

        return user_dict

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {str(e)}")


@app.get("/user/{userId}/ratings", response_model=List[Dict])
async def get_ratings(userId: int, db: Session = Depends(get_db)):
    return get_user_ratings(db, userId)

@app.get("/user/{userId}/recommendations/user-based", response_model=PaginatedResponse)
async def get_user_recommendations(userId: int, db: Session = Depends(get_db), limit: int = 9, offset: int = 0, filter_ratings: Optional[str] = None):
    # Verificar si el usuario existe
    user_exists = db.query(DBUser.userId).filter(DBUser.userId == userId).first() is not None
    
    if not user_exists:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Crear una clave de caché única
    cache_key = f"user_{userId}_filter_{filter_ratings}"
    
    # Intentar recuperar de caché
    all_recommendations = get_from_cache(cache_key)
    
    if all_recommendations is None:
        # Si no está en caché, calcular las recomendaciones
        all_recommendations = get_user_based_recommendations(db, userId, n=100, filter_ratings=filter_ratings)

        # Ordenar de manera determinística
        #all_recommendations.sort(key=lambda x: (-x["predicted_rating"], x["movieId"]))
        
        # Guardar en caché
        set_in_cache(cache_key, all_recommendations)
    
    total = len(all_recommendations)

    # Aplicar paginación
    paginated_recommendations = all_recommendations[offset:offset+limit]

    return {
        "items": paginated_recommendations,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.get("/user/{userId}/recommendations/item-based", response_model=PaginatedResponse)
async def get_item_recommendations(userId: int, db: Session = Depends(get_db), limit: int = 9, offset: int = 0, filter_ratings: Optional[str] = None):
    # Verificar si el usuario existe
    user_exists = db.query(DBUser.userId).filter(DBUser.userId == userId).first() is not None
    if not user_exists:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Crear una clave de caché única
    cache_key = f"item_{userId}_filter_{filter_ratings}"
    
    # Intentar recuperar de caché
    all_recommendations = get_from_cache(cache_key)

    if all_recommendations is None:
        # Si no está en caché, calcular las recomendaciones
        all_recommendations = get_item_based_recommendations(db, userId, n=100, filter_ratings=filter_ratings)
        
        # Ordenar de manera determinística
        #all_recommendations.sort(key=lambda x: (-x["predicted_rating"], x["movieId"]))
        
        # Guardar en caché
        set_in_cache(cache_key, all_recommendations)
    
    total = len(all_recommendations)

    # Aplicar paginación
    paginated_recommendations = all_recommendations[offset:offset+limit]
    
    # Retornar meta información para la paginación
    return {
        "items": paginated_recommendations,
        "total": total,
        "limit": limit,
        "offset": offset
    }

@app.post("/users/new")
async def create_user(new_user: NewUser, db: Session = Depends(get_db)):
    try:
        # Obtener el máximo ID de usuario
        _, max_user_id = get_users_set_and_max_id(db)
        
        # Crear nuevo userId
        new_id = max_user_id + 1
        
        # Crear el nuevo usuario en la base de datos
        db_user = DBUser(userId=new_id, userName=new_user.username)  # Usar el nombre proporcionado
        db.add(db_user)
        
        # Guardar ratings del nuevo usuario
        timestamp = datetime.now().timestamp()
        # Convertirlo a un objeto datetime 
        timestamp_dt = datetime.fromtimestamp(timestamp)

        rating_count = 0
        
        for rating_data in new_user.rating:
            for movieId, rating_value in rating_data.items():
                # Verificar si existe la película
                movie = db.query(DBMovie).filter(DBMovie.movieId == int(movieId)).first()
                if movie:
                    db_rating = DBRating(
                        id=None,  # Autoincremento
                        userId=new_id,
                        movieId=int(movieId),
                        rating=float(rating_value),
                        timestamp=timestamp_dt
                    )
                    db.add(db_rating)
                    rating_count += 1
        
        # Commit para guardar los cambios
        db.commit()
        
        return {"userId": new_id, "username": new_user.username, "num_ratings": rating_count}
    
    except Exception as e:
        # Revertir transacción en caso de error
        db.rollback()
        print(f"Error al crear usuario: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error al crear usuario: {str(e)}")

@app.post("/user/{userId}/rate")
async def add_rating(userId: int, movieId: int, rating: float, db: Session = Depends(get_db)):
    # Verificar si el usuario existe
    user = db.query(DBUser).filter(DBUser.userId == userId).first()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if rating < 0.5 or rating > 5.0:
        raise HTTPException(status_code=400, detail="El rating debe estar entre 0.5 y 5.0")
    
    # Verificar si la película existe
    movie = db.query(DBMovie).filter(DBMovie.movieId == movieId).first()
    if not movie:
        raise HTTPException(status_code=404, detail="Película no encontrada")
    
    # Verificar si ya existe un rating para este usuario y película
    existing_rating = db.query(DBRating).filter(
        DBRating.userId == userId,
        DBRating.movieId == movieId
    ).first()
    
    timestamp = int(datetime.now().timestamp())
    # Convertirlo a un objeto datetime 
    timestamp_dt = datetime.fromtimestamp(timestamp)
    
    if existing_rating:
        # Actualizar rating existente
        existing_rating.rating = rating
        existing_rating.timestamp = timestamp_dt
    else:
        # Agregar nuevo rating
        new_rating = DBRating(
            id=None,  # Autoincremento
            userId=userId,
            movieId=movieId,
            rating=rating,
            timestamp=timestamp_dt
        )
        db.add(new_rating)
    
    # Guardar cambios
    db.commit()

    # Limpiar la caché para este usuario
    for key in list(recommendations_cache.keys()):
        if key.startswith(f"user_{userId}") or key.startswith(f"item_{userId}"):
            del recommendations_cache[key]
    
    return {"message": "Calificación guardada", "userId": userId, "movieId": movieId, "rating": rating}

@app.post("/upload/movie", tags=['Upload'])
def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Leer datos del CSV
    movie_data = pd.read_csv(file.file, 
                             delimiter=',',
                             index_col=False, 
                             header=0)
    
    # Verificar que las columnas sean las correctas
    expected_columns = {'movieId', 'title', 'genres'}
    if not expected_columns.issubset(movie_data.columns):
        return {"error": "El archivo CSV no tiene las columnas esperadas."}
    
    # Cargar 
    create_movie(db, movie_data)

    return {"message": "CSV movie uploaded successfully!"}

@app.post("/upload/rating", tags=['Upload'])
def upload_csv(file: UploadFile = File(...), db: Session = Depends(get_db)):
    # Leer datos del CSV
    rating_data = pd.read_csv(file.file, 
                             delimiter=',',
                             index_col=False, 
                             header=0)
    
    # Verificar que las columnas sean las correctas
    expected_columns = {'userId','movieId','rating','timestamp'}
    if not expected_columns.issubset(rating_data.columns):
        return {"error": "El archivo CSV no tiene las columnas esperadas."}
    
    # Cargar 
    create_rating(db, rating_data)

    return {"message": "CSV rating uploaded successfully!"}

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Iniciar el servidor con uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)