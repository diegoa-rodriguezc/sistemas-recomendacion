from fastapi import FastAPI, HTTPException, Form, Depends, Request
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
    timestamp: int

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
app = FastAPI(title="Sistema de Recomendación de Películas",
              description="API para el Taller 1 de Sistemas de Recomendación")

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

try:
    model_user = joblib.load(MODEL_USER_PATH)
    model_item = joblib.load(MODEL_ITEM_PATH)
except Exception as e:
    print(f"Error cargando los modelos: {e}")
    model_user = None
    model_item = None

# Cargar datos de MovieLens
try:
    # Ajusta las rutas según donde tengas tus archivos
    movies_df = pd.read_csv("data/movie.csv")
    ratings_df = pd.read_csv("data/rating.csv")

    # Crear un diccionario para mapear movieId a información de la película
    movies_dict = {
        row['movieId']: {
            'title': row['title'],
            'genres': row['genres']
        } for _, row in movies_df.iterrows()
    }
    
    # Crear un set de usuarios existentes
    users_set = set(ratings_df['userId'].unique())
    max_user_id = max(users_set)
    
    # Crear un dataframe para almacenar nuevos usuarios y sus ratings
    new_users_ratings = pd.DataFrame(columns=['userId', 'movieId', 'rating', 'timestamp'])
    
except Exception as e:
    print(f"Error cargando los datos: {e}")
    movies_df = pd.DataFrame()
    ratings_df = pd.DataFrame()
    movies_dict = {}
    users_set = set()
    max_user_id = 0
    new_users_ratings = pd.DataFrame()

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
def get_popular_movies(n=20):
    # Agrupar por película y contar número de ratings
    movie_popularity = ratings_df.groupby('movieId').size().reset_index(name='count')
    # Unir con información de películas
    popular_movies = movie_popularity.merge(movies_df, on='movieId')
    # Ordenar por popularidad y tomar las N más populares
    popular_movies = popular_movies.sort_values('count', ascending=False).head(n)
    return popular_movies[['movieId', 'title', 'genres']].to_dict('records')

# Función para obtener el historial de ratings de un usuario
def get_user_ratings(userId):
    # Obtener ratings del dataset original
    user_ratings = ratings_df[ratings_df['userId'] == userId]
    
    # Obtener ratings del usuario si es nuevo
    if userId > max_user_id:
        new_user_ratings = new_users_ratings[new_users_ratings['userId'] == userId]
        user_ratings = pd.concat([user_ratings, new_user_ratings])
    
    # Unir con información de películas
    user_ratings = user_ratings.merge(movies_df, on='movieId')
    
    return user_ratings[['movieId', 'title', 'genres', 'rating']].sort_values('rating', ascending=False).to_dict('records')


# Función para generar recomendaciones user-user
def get_user_based_recommendations(userId, n=100, filter_ratings=None):
    if model_user is None:
        raise HTTPException(status_code=500, detail="Modelo user-user no disponible")

    # Verificar si el usuario existe en los datos
    if userId not in users_set:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Obtener películas que el usuario ya calificó
    user_rated_movies = set(ratings_df[ratings_df['userId'] == userId]['movieId'])

    # Filtrar películas a predecir
    movies_to_predict = set(movies_df['movieId']) - user_rated_movies
    
    # Para mejor rendimiento, limitar el número de películas a predecir
    # si hay muchas películas sin calificar
    movies_sample = list(movies_to_predict)
    if len(movies_sample) > 500:  # Si hay más de 500 películas, tomar una muestra
        # Deterministic selection: use most popular movies instead of random
        movie_popularity = ratings_df.groupby('movieId').size().reset_index(name='count')
        movie_popularity = movie_popularity[movie_popularity['movieId'].isin(movies_sample)]
        movie_popularity = movie_popularity.sort_values('count', ascending=False).head(500)
        movies_sample = movie_popularity['movieId'].tolist()

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
def get_item_based_recommendations(userId, n=100, filter_ratings=None):
    if model_item is None:
        raise HTTPException(status_code=500, detail="Modelo item-item no disponible")

    # Verificar si el usuario existe en los datos
    if userId not in users_set:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Obtener películas que el usuario ya calificó
    user_rated_movies = set(ratings_df[ratings_df['userId'] == userId]['movieId'])

    # Filtrar películas a predecir
    movies_to_predict = set(movies_df['movieId']) - user_rated_movies
    
    # Para mejor rendimiento, limitar el número de películas a predecir
    # si hay muchas películas sin calificar
    movies_sample = list(movies_to_predict)
    if len(movies_sample) > 500:  # Si hay más de 500 películas, tomar una muestra
        # Deterministic selection: use most popular movies instead of random
        movie_popularity = ratings_df.groupby('movieId').size().reset_index(name='count')
        movie_popularity = movie_popularity[movie_popularity['movieId'].isin(movies_sample)]
        movie_popularity = movie_popularity.sort_values('count', ascending=False).head(500)
        movies_sample = movie_popularity['movieId'].tolist()

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
async def login(request: Request, userId: int = Form(...)):
    if userId not in users_set:
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
async def get_users(limit: int = 300):
    users = []
    # Obtener usuarios del dataset original
    for userId in list(users_set)[:limit]:
        users.append({"userId": int(userId), "username": f"Usuario {userId}"})
    
    # Añadir usuarios nuevos si existen
    new_user_ids = set(new_users_ratings['userId'].unique())
    for userId in new_user_ids:
        if userId not in users_set:
            users.append({"userId": int(userId), "username": f"Nuevo Usuario {userId}"})
    
    return users

@app.get("/movies", response_model=List[Movie])
async def get_movies(limit: int = 100):
    return [
        {"movieId": int(row['movieId']), "title": row['title'], "genres": row['genres']}
        for _, row in movies_df.head(limit).iterrows()
    ]

@app.get("/popular-movies", response_model=List[Movie])
async def get_popular():
    return get_popular_movies()

@app.get("/user/{userId}/ratings", response_model=List[Dict])
async def get_ratings(userId: int):
    return get_user_ratings(userId)

# Variable global para almacenar en caché las recomendaciones
recommendations_cache = {}

# Tiempo de expiración de la caché (por ejemplo, 1 hora)
CACHE_EXPIRY = timedelta(hours=1)

@app.get("/user/{userId}/recommendations/user-based", response_model=PaginatedResponse)
async def get_user_recommendations(userId: int, limit: int = 9, offset: int = 0, filter_ratings: Optional[str] = None):
    if userId not in users_set and userId not in set(new_users_ratings['userId'].unique()):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Crear una clave de caché única
    cache_key = f"user_{userId}_filter_{filter_ratings}"
    
    # Intentar recuperar de caché
    all_recommendations = get_from_cache(cache_key)
    
    if all_recommendations is None:
        # Si no está en caché, calcular las recomendaciones
        all_recommendations = get_user_based_recommendations(userId, n=100, filter_ratings=filter_ratings)
        
        # Ordenar de manera determinística
        all_recommendations.sort(key=lambda x: (-x["predicted_rating"], x["movieId"]))
        
        # Guardar en caché
        set_in_cache(cache_key, all_recommendations)
    
    # Aplicar paginación
    paginated_recommendations = all_recommendations[offset:offset+limit]
    
    return {
        "items": paginated_recommendations,
        "total": len(all_recommendations),
        "limit": limit,
        "offset": offset
    }

@app.get("/user/{userId}/recommendations/item-based", response_model=PaginatedResponse)
async def get_item_recommendations(userId: int, limit: int = 9, offset: int = 0, filter_ratings: Optional[str] = None):
    if userId not in users_set and userId not in set(new_users_ratings['userId'].unique()):
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    # Crear una clave de caché única
    cache_key = f"item_{userId}_filter_{filter_ratings}"
    
    # Intentar recuperar de caché
    all_recommendations = get_from_cache(cache_key)

    if all_recommendations is None:
        # Si no está en caché, calcular las recomendaciones
        all_recommendations = get_item_based_recommendations(userId, n=100, filter_ratings=filter_ratings)
        
        # Ordenar de manera determinística
        all_recommendations.sort(key=lambda x: (-x["predicted_rating"], x["movieId"]))
        
        # Guardar en caché
        set_in_cache(cache_key, all_recommendations)
    
    
    # Aplicar paginación
    paginated_recommendations = all_recommendations[offset:offset+limit]
    
    # Retornar meta información para la paginación
    return {
        "items": paginated_recommendations,
        "total": len(all_recommendations),
        "limit": limit,
        "offset": offset
    }

@app.post("/users/new")
async def create_user(new_user: NewUser):
    global max_user_id, ratings_df, users_set
    
    # Crear nuevo userId
    new_id = max_user_id + 1
    max_user_id = new_id
    users_set.add(new_id)  # Agregar usuario a la lista de usuarios existentes
    
    # Guardar ratings del nuevo usuario
    timestamp = pd.Timestamp.now().timestamp()
    new_ratings = []

    for rating_data in new_user.ratings:
        for movieId, rating in rating_data.items():
            new_ratings = pd.DataFrame({
                'userId': [new_id],
                'movieId': [int(movieId)],
                'rating': [float(rating)],
                'timestamp': [int(timestamp)]
            })
            #new_users_ratings = pd.concat([new_users_ratings, new_rating], ignore_index=True)
    if new_ratings:
        new_ratings_df = pd.DataFrame(new_ratings)
        ratings_df = pd.concat([ratings_df, new_ratings_df], ignore_index=True)  # Agregar a ratings_df
        #ratings_df.to_csv("rating.csv", index=False)  # Guardar en CSV
        new_ratings_df.to_csv("rating.csv", mode='a', header=False, index=False)
    
    return {"userId": new_id, "username": new_user.username, "num_ratings": len(new_user.ratings)}

@app.post("/user/{userId}/rate")
async def add_rating(userId: int, movieId: int, rating: float):
    #global new_users_ratings
    global ratings_df, users_set
    
    if userId not in users_set:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    
    if rating < 0.5 or rating > 5.0:
        raise HTTPException(status_code=400, detail="El rating debe estar entre 0.5 y 5.0")
    
    # Agregar nuevo rating
    timestamp = pd.Timestamp.now().timestamp()
    new_rating = pd.DataFrame({
        'userId': [userId],
        'movieId': [movieId],
        'rating': [rating],
        'timestamp': [int(timestamp)]
    })
    
    #new_users_ratings = pd.concat([new_users_ratings, new_rating], ignore_index=True)
    ratings_df = pd.concat([ratings_df, new_rating], ignore_index=True)
    #ratings_df.to_csv("rating.csv", index=False)  # Guardar en CSV
    # Guardar en CSV sin sobrescribir datos previos
    new_rating.to_csv("rating.csv", mode='a', header=False, index=False)
    #print(new_users_ratings)
    #return {"userId": userId, "movieId": movieId, "rating": rating}
    print(ratings_df.tail(5))

    # Limpiar la caché para este usuario
    for key in list(recommendations_cache.keys()):
        if key.startswith(f"user_{userId}"):
            del recommendations_cache[key]
    
    return {"message": "Calificación guardada", "userId": userId, "movieId": movieId, "rating": rating}

# Montar archivos estáticos
app.mount("/static", StaticFiles(directory="static"), name="static")

# Iniciar el servidor con uvicorn
if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)