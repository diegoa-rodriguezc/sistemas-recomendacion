from fastapi import FastAPI, Request, Form, Depends
from fastapi.responses import HTMLResponse, RedirectResponse, JSONResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from fastapi.middleware.cors import CORSMiddleware
from starlette.middleware.sessions import SessionMiddleware

import pandas as pd
import numpy as np
import pickle
import joblib
from datetime import datetime
from io import BytesIO
import base64
from collections import Counter
import folium
from folium.plugins import MarkerCluster
import matplotlib.pyplot as plt
import seaborn as sns
import os
import json
import uuid
import random
import multiprocessing

from typing import Optional
import hashlib

from recommender_model import HybridRecommender
import sys 
sys.modules['__main__'] = sys.modules['recommender_model']

# Importar datos de Sesión y modelos de Base de Datos
from sqlalchemy.orm import Session
from db.session import get_db
from db.models import Business, User, Review

# Para garantizar reproducibilidad en resultados, se define la semilla global
seed = 10
random.seed(seed)
np.random.seed(seed)

# Activar paralelismo
os.environ["OMP_NUM_THREADS"] = str(multiprocessing.cpu_count()) # Para NumPy y OpenMP
os.environ["MKL_NUM_THREADS"] = str(multiprocessing.cpu_count()) # Para librerías basadas en MKL
os.environ["NUMEXPR_NUM_THREADS"] = str(multiprocessing.cpu_count()) # Para NumExpr
os.environ["OPENBLAS_NUM_THREADS"] = str(multiprocessing.cpu_count()) # Para OpenBLAS
os.environ["TF_NUM_INTRAOP_THREADS"] = str(multiprocessing.cpu_count()) # Para TensorFlow
os.environ["TF_NUM_INTEROP_THREADS"] = str(multiprocessing.cpu_count()) # Para TensorFlow

app = FastAPI()

# Templates and static files
templates = Jinja2Templates(directory="templates")
app.mount("/static", StaticFiles(directory="static"), name="static")

# CORS (por si accedes desde otras apps)
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

# Establece un tamaño máximo para la cookie más grande
SECRET_KEY = os.getenv("SESSION_SECRET_KEY", "yelp_recommendation_system_key")

app.add_middleware(SessionMiddleware, secret_key=SECRET_KEY, max_age=3600)

# Directorio temporal para almacenar recomendaciones
TEMP_DIR = "temp_recommendations"
os.makedirs(TEMP_DIR, exist_ok=True)

with open("model/hybrid_model.joblib", "rb") as f:
    hybrid_model = joblib.load(f)

# Inicializar el diccionario de datos del modelo si no existe
if not hasattr(hybrid_model, 'data_dict'):
    hybrid_model.data_dict = {}

# Function to convert SQLAlchemy models to pandas DataFrames
def load_data_from_db(db: Session):
    # Load businesses
    business_query = db.query(Business).all()
    business_data = [{
        'business_id': b.business_id,
        'name': b.name,
        'address': b.address,
        'city': b.city,
        'state': b.state,
        'postal_code': b.postal_code,
        'latitude': b.latitude,
        'longitude': b.longitude,
        'stars': b.stars,
        'review_count': b.review_count,
        'is_open': b.is_open,
        'attributes': b.attributes,
        'categories': b.categories,
        'hours': b.hours
    } for b in business_query]
    business_df = pd.DataFrame(business_data)
    
    # Load users
    user_query = db.query(User).limit(800000).all()
    user_data = [{
        'user_id': u.user_id,
        'name': u.name,
        'review_count': u.review_count,
        'yelping_since': u.yelping_since,
        'friends': u.friends,
        'useful': u.useful,
        'funny': u.funny,
        'cool': u.cool,
        'fans': u.fans,
        'elite': u.elite,
        'average_stars': u.average_stars,
        'compliment_hot': u.compliment_hot,
        'compliment_more': u.compliment_more,
        'compliment_profile': u.compliment_profile,
        'compliment_cute': u.compliment_cute,
        'compliment_list': u.compliment_list,
        'compliment_note': u.compliment_note,
        'compliment_plain': u.compliment_plain,
        'compliment_cool': u.compliment_cool,
        'compliment_funny': u.compliment_funny,
        'compliment_writer': u.compliment_writer,
        'compliment_photos': u.compliment_photos
    } for u in user_query]
    user_df = pd.DataFrame(user_data)
    
    # Load reviews
    review_query = db.query(Review).limit(800000).all()
    review_data = [{
        'review_id': r.review_id,
        'user_id': r.user_id,
        'business_id': r.business_id,
        'stars': r.stars,
        'date': r.date,
        'text': r.text,
        'useful': r.useful,
        'funny': r.funny,
        'cool': r.cool
    } for r in review_query]
    review_df = pd.DataFrame(review_data)
    
    return business_df, user_df, review_df

# Función para cargar sólo los datos necesarios para inicialización
def load_minimal_data_for_init(db: Session):
    # Cargar solo las ciudades para el filtro inicial
    cities_query = db.query(Business.city).distinct().order_by(Business.city).all()
    valid_cities = [city[0] for city in cities_query if city[0]]
    
    # Cargar solo los IDs de usuario para el inicio de sesión de demostración
    user_ids_query = db.query(User.user_id).distinct().limit(100).all()
    valid_users = [user_id[0] for user_id in user_ids_query]
    
    return valid_cities, valid_users

# Initialize data for the model
@app.on_event("startup")
async def startup_db_client():
    
    # Inicializar solo datos mínimos al iniciar la aplicación
    db = next(get_db())
    valid_cities, valid_users = load_minimal_data_for_init(db)
    
    # Guardar en app.state para uso global
    app.state.valid_cities = valid_cities
    app.state.valid_users = valid_users
    
    # Limpiar archivos temporales antiguos
    if os.path.exists(TEMP_DIR):
        files = os.listdir(TEMP_DIR)
        for file in files:
            file_path = os.path.join(TEMP_DIR, file)
            try:
                os.remove(file_path)
            except:
                pass

# Función para cargar datos perezosamente cuando se necesiten
def ensure_data_loaded(db: Session):
    """Asegura que los datos estén cargados cuando sea necesario"""

    # Verificar si ya tenemos los datos de business (como mínimo)
    if "business" not in hybrid_model.data_dict or hybrid_model.data_dict["business"].empty:
        print("Cargando datos desde la base de datos...")
        business_df, user_df, review_df = load_data_from_db(db)
        
        # 🔍 Prints para ver si realmente se están datos
        print("   Users    cargados:", len(user_df))
        print("   Business cargados:", len(business_df))
        print("   Reviews  cargados:", len(review_df))

        # Guardar los datos en el modelo
        hybrid_model.data_dict["business"] = business_df
        hybrid_model.data_dict["user"] = user_df
        hybrid_model.data_dict["review"] = review_df
        print("Datos cargados correctamente.")

    return hybrid_model.data_dict

@app.get("/test_user_data")
async def test_user_data(db: Session = Depends(get_db)):
    data_dict = ensure_data_loaded(db)
    user_df = data_dict["user"]
    return {"user_count": len(user_df), "sample_ids": user_df["user_id"].head(5).tolist()}

# ----------------- ROUTES -------------------
@app.get("/", response_class=HTMLResponse)
async def home(request: Request, db: Session = Depends(get_db)):
    # Verificar user logeado
    if "user_id" not in request.session:
        return RedirectResponse(url="/login", status_code=303)
    
    # Validar datos cargados después del login
    if not hasattr(app.state, "valid_cities") or not app.state.valid_cities:
        valid_cities, _ = load_minimal_data_for_init(db)
        app.state.valid_cities = valid_cities
    
    # Cargar datos perezosamente al inicio para evitar problemas en otras rutas
    ensure_data_loaded(db)

    return templates.TemplateResponse("index.html", {
        "request": request, 
        "cities": app.state.valid_cities,
        "session": request.session
    })


@app.get("/user/{user_id}", response_class=HTMLResponse)
async def user_profile(request: Request, user_id: str, db: Session = Depends(get_db)):
    # Cargar datos perezosamente si no están disponibles
    data_dict = ensure_data_loaded(db)
    
    user_df = data_dict["user"]
    review_df = data_dict["review"]
    business_df = data_dict["business"]
    
    # print("user_id recibido:", user_id)
    # print("User ID tipo:", type(user_id))
    # print("Primeros user_ids disponibles:", user_df["user_id"].head(5).tolist())
    # print("¿Existe user_id en user_df?", user_id in user_df["user_id"].values)
    #print("Busqueda de Id ", user_df[user_df["user_id"] == user_id].iloc[0].to_dict())

    # if user_id not in user_df["user_id"].values:
    # # if not user_df["user_id"].isin([user_id]).any():
    # #     return HTMLResponse(content="User not found", status_code=404)

    # # user_info = user_df[user_df["user_id"] == user_id].iloc[0].to_dict()

    filtered_user = db.query(User).filter(User.user_id == user_id).first()
    
    if filtered_user is None or filtered_user == '':
        print(f"Usuario {user_id} no encontrado en user_df.")
        return HTMLResponse(f"Usuario '{user_id}' no encontrado", status_code=404)
    
    user_info = filtered_user#.iloc[0].to_dict()
    
    if isinstance(user_info.yelping_since, datetime):
        user_info.yelping_since = user_info.yelping_since.strftime("%B %d, %Y")
    
    user_reviews = review_df[review_df["user_id"] == user_id].sort_values("date", ascending=False)
    user_reviews = user_reviews.merge(business_df[["business_id", "name", "city", "categories"]], on="business_id")

    review_stats = {
        "count": len(user_reviews),
        "avg_rating": user_reviews["stars"].mean(),
        "rating_dist": user_reviews["stars"].value_counts().sort_index().to_dict(),
    }

    # Plot
    fig = plt.figure(figsize=(6, 4))
    # sns.countplot(x="stars", data=user_reviews, palette="viridis")
    sns.countplot(x="stars", data=user_reviews, hue="stars", palette="viridis", legend=False)
    plt.title("Rating Distribution")
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    rating_chart = f"data:image/png;base64,{base64.b64encode(buffer.read()).decode('utf-8')}"
    buffer.close()
    plt.close(fig)

    city_counts = user_reviews["city"].value_counts().head(5).to_dict()

    categories = []
    for cat_str in user_reviews["categories"].dropna():
        if cat_str:
            categories.extend([c.strip() for c in cat_str.split(",")])
    top_categories = dict(Counter(categories).most_common(10))

    recent_activities = user_reviews.head(5).to_dict("records")
    for activity in recent_activities:
        if isinstance(activity['date'], datetime):
            activity['date'] = activity['date'].strftime("%B %d, %Y")

    return templates.TemplateResponse("user_profile.html", {
        "request": request,
        "user": user_info,
        "review_stats": review_stats,
        "rating_chart": rating_chart,
        "city_counts": city_counts,
        "top_categories": top_categories,
        "recent_activities": recent_activities,
    })

@app.post("/recommendations")
async def get_recommendations(
    request: Request,
    user_id: str = Form(...),
    city: str = Form(None),
    num_recommendations: int = Form(10),
    db: Session = Depends(get_db)
):
    # Cargar datos perezosamente si no están disponibles
    data_dict = ensure_data_loaded(db)
    business_df = data_dict["business"]
    
    now = datetime.now()
    hour, month, day_of_week = now.hour, now.month, now.weekday()

    context_features = {}

    # Time
    if 0 <= hour < 6:
        context_features["time_of_day_night"] = 1
    elif 6 <= hour < 12:
        context_features["time_of_day_morning"] = 1
    elif 12 <= hour < 18:
        context_features["time_of_day_afternoon"] = 1
    else:
        context_features["time_of_day_evening"] = 1

    # Season
    if 1 <= month <= 3:
        context_features["season_winter"] = 1
    elif 4 <= month <= 6:
        context_features["season_spring"] = 1
    elif 7 <= month <= 9:
        context_features["season_summer"] = 1
    else:
        context_features["season_fall"] = 1

    context_features[f"day_of_week_{day_of_week}"] = 1

    # Make sure the city is correctly processed
    print(f"Selected city: {city}")
    
    candidate_items = None
    if city and city.strip() and city != "None":  # Verify that the city is not None or empty string
        context_features[f"city_{city}"] = 1
        candidate_items = business_df[business_df["city"] == city]["business_id"].tolist()
        print(f"Number of businesses in {city}: {len(candidate_items)}")
    
    # If there are no candidates for the city, show a message
    if candidate_items is not None and len(candidate_items) == 0:
        print(f"No businesses available in city: {city}")

    # Get recommendations
    recommendations = hybrid_model.recommend(
        user_id=user_id,
        context_features=context_features,
        n=num_recommendations,
        candidate_items=candidate_items,
        explanation=True,
    )

    recommendations = sorted(recommendations, key=lambda x: x["stars"], reverse=True)

    # Generate a unique ID for recommendations
    rec_id = str(uuid.uuid4())
    
    # Save recommendations to a temporary file
    rec_file_path = os.path.join(TEMP_DIR, f"{rec_id}.json")

    # Make sure the data is serializable
    serializable_recs = []
    for rec in recommendations:
        ser_rec = {k: v for k, v in rec.items()}
        # Convert numpy values to native Python types
        for key, value in ser_rec.items():
            if isinstance(value, (np.int64, np.int32, np.float64, np.float32)):
                ser_rec[key] = float(value) if isinstance(value, (np.float64, np.float32)) else int(value)
        serializable_recs.append(ser_rec)
    
    with open(rec_file_path, 'w') as f:
        json.dump(serializable_recs, f)
    
    # Only store the recommendation ID in the session, not all content
    request.session["recommendation_id"] = rec_id
    request.session["user_id"] = user_id
    request.session["selected_city"] = city if city else ""

    return RedirectResponse(url="/show_recommendations", status_code=303)

def get_stored_recommendations(rec_id: str):
    """Helper function to retrieve saved recommendations"""
    rec_file_path = os.path.join(TEMP_DIR, f"{rec_id}.json")
    if os.path.exists(rec_file_path):
        with open(rec_file_path, 'r') as f:
            return json.load(f)
    return []

@app.get("/show_recommendations", response_class=HTMLResponse)
async def show_recommendations(request: Request):
    rec_id = request.session.get("recommendation_id")
    user_id = request.session.get("user_id", "")
    selected_city = request.session.get("selected_city", "")
    
    recommendations = []
    if rec_id:
        recommendations = get_stored_recommendations(rec_id)
    
    if not recommendations:
        return RedirectResponse(url="/", status_code=303)

    map_html = None
    if recommendations and all(r.get("latitude") is not None and r.get("longitude") is not None for r in recommendations):
    # if recommendations and all(r.get("latitude") and r.get("longitude") for r in recommendations):
        map_center = [recommendations[0].get("latitude", 0), recommendations[0].get("longitude", 0)]
        recommendation_map = folium.Map(location=map_center, zoom_start=12)
        marker_cluster = MarkerCluster().add_to(recommendation_map)

        for rec in recommendations:
            if rec.get("latitude") and rec.get("longitude"):
                popup_text = f"""
                <strong>{rec['name']}</strong><br>
                Rating: {rec['stars']}<br>
                Score: {rec['score']:.2f}<br>
                Categories: {rec['categories']}
                """
                folium.Marker(
                    location=[rec["latitude"], rec["longitude"]],
                    popup=folium.Popup(popup_text, max_width=300),
                    icon=folium.Icon(color="blue", icon="info-sign"),
                ).add_to(marker_cluster)

        map_html = recommendation_map._repr_html_()

    return templates.TemplateResponse("recommendations.html", {
        "request": request,
        "recommendations": recommendations,
        "user_id": user_id,
        "selected_city": selected_city,
        "map_html": map_html,
    })

@app.get("/business/{business_id}", response_class=HTMLResponse)
async def business_details(request: Request, business_id: str, db: Session = Depends(get_db)):
    # Cargar datos perezosamente si no están disponibles
    data_dict = ensure_data_loaded(db)
    
    business_df = data_dict["business"]
    review_df = data_dict["review"]
    user_df = data_dict["user"]
    
    if business_id not in business_df["business_id"].values:
        return HTMLResponse(content="Business not found", status_code=404)

    business_info = business_df[business_df["business_id"] == business_id].iloc[0].to_dict()
    business_reviews = review_df[review_df["business_id"] == business_id].sort_values("date", ascending=False)
    business_reviews = business_reviews.merge(user_df[["user_id", "name"]], on="user_id")

    avg_rating = business_reviews["stars"].mean()
    if pd.isna(avg_rating):
        avg_rating = 0.0
        
    review_stats = {
        "count": len(business_reviews),
        "avg_rating": avg_rating,
        "rating_dist": business_reviews["stars"].value_counts().sort_index().to_dict(),
    }

    fig = plt.figure(figsize=(6, 4))
    #sns.countplot(x="stars", data=business_reviews, palette="viridis")
    sns.countplot(x="stars", data=business_reviews, hue="stars", palette="viridis", legend=False)

    plt.title("Rating Distribution")
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    rating_chart = f"data:image/png;base64,{base64.b64encode(buffer.read()).decode('utf-8')}"
    buffer.close()
    plt.close(fig)

    recent_reviews = business_reviews.head(10).to_dict("records")
    for review in recent_reviews:
        if isinstance(review["date"], str):
            # ya está formateado
            continue
        review["date"] = review["date"].strftime("%B %d, %Y")

    if business_info.get("latitude") and business_info.get("longitude"):
        business_map = folium.Map(location=[business_info["latitude"], business_info["longitude"]], zoom_start=15)
        popup_text = f"""
        <strong>{business_info['name']}</strong><br>
        Rating: {business_info['stars']}<br>
        Categories: {business_info['categories']}
        """
        folium.Marker(
            location=[business_info["latitude"], business_info["longitude"]],
            popup=folium.Popup(popup_text, max_width=300),
            icon=folium.Icon(color="red", icon="info-sign"),
        ).add_to(business_map)

        map_html = business_map._repr_html_()
    else:
        map_html = None

    return templates.TemplateResponse("business_details.html", {
        "request": request,
        "business": business_info,
        "review_stats": review_stats,
        "rating_chart": rating_chart,
        "recent_reviews": recent_reviews,
        "map_html": map_html,
    })

@app.post("/feedback")
async def submit_feedback(feedback_data: dict):
    print(f"Received feedback: {feedback_data}")
    return JSONResponse(content={"status": "success"})

@app.get("/about", response_class=HTMLResponse)
async def about(request: Request):
    return templates.TemplateResponse("about.html", {"request": request})

# Add this function in the appropriate section (with other helper functions)
def authenticate_user(username: str, password: str, db: Session):
    """
    Authenticate a user using username/email and password
    
    For a real application, this should use proper password hashing
    """
    
    user = db.query(User).filter(User.user_id == username).first()
    
    if not user:
        return None
    
    if password == user.user_id:
        return user
        
    return None

@app.get("/login", response_class=HTMLResponse)
async def login_page(request: Request, db: Session = Depends(get_db)):
    # Check if user is already logged in
    if "user_id" in request.session:
        return RedirectResponse(url="/", status_code=303)
    
    # Usar la lista de usuarios ya cargada en app.state si existe
    if not hasattr(app.state, "valid_users") or not app.state.valid_users:
        # Si no existe, cargar un conjunto mínimo de datos
        _, valid_users = load_minimal_data_for_init(db)
        app.state.valid_users = valid_users
    
    # Obtener los usuarios para el formulario de login
    user_objects = db.query(User).filter(User.user_id.in_(app.state.valid_users)).all()
    
    return templates.TemplateResponse("login.html", {
        "request": request,
        "users": user_objects,
        "error": None
    })

@app.post("/login", response_class=HTMLResponse)
async def login(
    request: Request,
    username: str = Form(...),
    password: str = Form(...),
    db: Session = Depends(get_db)
):
    user = authenticate_user(username, password, db)
    
    if not user:
        # Si la autenticación falla, mostrar error
        user_objects = db.query(User).filter(User.user_id.in_(app.state.valid_users)).all()
        return templates.TemplateResponse("login.html", {
            "request": request,
            "users": user_objects,
            "error": "Invalid username or password"
        })
    
    # Set session data
    request.session["user_id"] = user.user_id
    request.session["user_name"] = user.name
    
    return RedirectResponse(url="/", status_code=303)

@app.post("/login_as_demo_user")
async def login_as_demo_user(
    request: Request,
    demo_user: str = Form(...),
    db: Session = Depends(get_db)
):
    user = db.query(User).filter(User.user_id == demo_user).first()
    
    if not user:
        return RedirectResponse(url="/login", status_code=303)
    
    # Establecer la sesión con el usuario seleccionado
    request.session["user_id"] = user.user_id
    request.session["user_name"] = user.name
    
    # Precargar los datos mínimos necesarios justo después del login
    if not hasattr(app.state, "valid_cities") or not app.state.valid_cities:
        valid_cities, _ = load_minimal_data_for_init(db)
        app.state.valid_cities = valid_cities
    
    return RedirectResponse(url="/", status_code=303)

@app.get("/logout")
async def logout(request: Request):
    # Clear session data
    request.session.clear()
    return RedirectResponse(url="/login", status_code=303)