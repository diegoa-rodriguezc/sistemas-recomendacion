from fastapi import APIRouter, HTTPException, Depends
from typing import List, Dict, Optional
from pydantic import BaseModel
import pandas as pd
import os
import aiohttp
from models.data_processor import DataProcessor
from models.recommendation_model import RecommendationModel
from models.enhancedhybridrecommender import EnhancedHybridRecommender

router = APIRouter()
data_processor = DataProcessor()
recommendation_model = RecommendationModel(data_processor)

# Load ratings data
ratings_path = os.path.join(data_processor.data_dir, 'ratings.csv')
ratings_df = pd.read_csv(ratings_path) if os.path.exists(ratings_path) else pd.DataFrame()

# TMDB API configuration
TMDB_API_KEY = os.getenv('TMDB_API_KEY', 'your_api_key_here')
TMDB_BASE_URL = 'https://api.themoviedb.org/3'

class UserRatingsInput(BaseModel):
    user_id: str
    ratings: Optional[Dict[str, float]] = None
    top_k: Optional[int] = 10  # Nuevo parámetro con valor por defecto

class RecommendationResponse(BaseModel):
    recommendations: List[Dict]

def clean_movie_title(title: str) -> str:
    """Clean movie title for better TMDB search results"""
    import re
    
    # Remove year in parentheses
    clean_title = re.sub(r'\s*\(\d{4}\)$', '', title)
    
    # Remove "a.k.a" references
    clean_title = re.sub(r'\s*\(a\.k\.a\.\s+[^)]+\)', '', clean_title, flags=re.IGNORECASE)
    
    # Handle articles (The, A, An) at the end
    article_match = re.match(r'^(.+),\s+(The|A|An)$', clean_title)
    if article_match:
        clean_title = f"{article_match.group(2)} {article_match.group(1)}"
    
    return clean_title.strip()

async def get_tmdb_movie_details(session: aiohttp.ClientSession, movie_title: str, movie_id: str) -> Dict:
    """Get detailed movie information from TMDB API"""
    try:
        clean_title = clean_movie_title(movie_title)
        
        # Search for the movie
        search_url = f"{TMDB_BASE_URL}/search/movie"
        search_params = {
            'api_key': TMDB_API_KEY,
            'query': clean_title,
            'page': 1
        }
        
        async with session.get(search_url, params=search_params) as response:
            if response.status != 200:
                print(f"TMDB search failed for {clean_title}: {response.status}")
                return create_fallback_movie_data(movie_title, movie_id)
            
            search_data = await response.json()
            if not search_data.get('results'):
                print(f"No TMDB results found for {clean_title}")
                return create_fallback_movie_data(movie_title, movie_id)
            
            movie_basic = search_data['results'][0]
            tmdb_id = movie_basic.get('id')
            
            if not tmdb_id:
                return create_fallback_movie_data(movie_title, movie_id)
        
        # Get detailed movie information
        details_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}"
        details_params = {
            'api_key': TMDB_API_KEY,
            'language': 'es-ES'
        }
        
        # Get movie credits (cast and crew)
        credits_url = f"{TMDB_BASE_URL}/movie/{tmdb_id}/credits"
        credits_params = {
            'api_key': TMDB_API_KEY
        }
        
        # Fetch both details and credits concurrently
        async with session.get(details_url, params=details_params) as details_response, \
                   session.get(credits_url, params=credits_params) as credits_response:
            
            if details_response.status == 200:
                details_data = await details_response.json()
            else:
                details_data = {}
            
            if credits_response.status == 200:
                credits_data = await credits_response.json()
            else:
                credits_data = {}
        
        # Combine basic search data with detailed information
        return create_enhanced_movie_data(movie_basic, details_data, credits_data, movie_title, movie_id)
        
    except Exception as e:
        print(f"Error fetching TMDB details for {movie_title}: {str(e)}")
        return create_fallback_movie_data(movie_title, movie_id)

def create_fallback_movie_data(original_title: str, movie_id: str) -> Dict:
    """Create fallback movie data when TMDB fails"""
    return {
        'movieId': movie_id,
        'title': clean_movie_title(original_title),
        'originalTitle': original_title,
        'id': movie_id,
        'poster_path': None,
        'backdrop_path': None,
        'release_date': None,
        'overview': 'No hay información disponible',
        'genres': [],
        'runtime': None,
        'vote_average': None,
        'vote_count': None,
        'original_language': None,
        # 'popularity': None,
        'adult': False,
        'budget': None,
        'revenue': None,
        'production_companies': [],
        'production_countries': [],
        'spoken_languages': [],
        'tagline': None,
        'cast': [],
        'director': None,
        'writers': [],
        'producers': []
    }

def create_enhanced_movie_data(basic_data: Dict, details_data: Dict, credits_data: Dict, 
                              original_title: str, movie_id: str) -> Dict:
    """Create enhanced movie data combining all TMDB information"""
    
    # Extract cast information (top 5 actors)
    cast = []
    if credits_data.get('cast'):
        cast = [
            {
                'name': actor.get('name'),
                'character': actor.get('character'),
                'profile_path': actor.get('profile_path')
            }
            for actor in credits_data['cast'][:5]
        ]
    
    # Extract crew information
    crew = credits_data.get('crew', [])
    director = next((person for person in crew if person.get('job') == 'Director'), None)
    writers = [person for person in crew if person.get('job') in ['Writer', 'Screenplay']][:3]
    producers = [person for person in crew if person.get('job') == 'Producer'][:2]
    
    return {
        'movieId': movie_id,
        'title': clean_movie_title(original_title),
        'originalTitle': original_title,
        'id': basic_data.get('id', movie_id),
        'poster_path': basic_data.get('poster_path'),
        'backdrop_path': basic_data.get('backdrop_path'),
        'release_date': basic_data.get('release_date') or details_data.get('release_date'),
        'overview': basic_data.get('overview') or details_data.get('overview') or 'No hay descripción disponible',
        'genres': details_data.get('genres', []),
        'runtime': details_data.get('runtime'),
        'vote_average': basic_data.get('vote_average'),
        'vote_count': basic_data.get('vote_count'),
        'original_language': basic_data.get('original_language'),
        'popularity': basic_data.get('popularity'),
        'adult': basic_data.get('adult', False),
        'budget': details_data.get('budget'),
        'revenue': details_data.get('revenue'),
        'production_companies': details_data.get('production_companies', []),
        'production_countries': details_data.get('production_countries', []),
        'spoken_languages': details_data.get('spoken_languages', []),
        'tagline': details_data.get('tagline'),
        'cast': cast,
        'director': {
            'name': director.get('name'),
            'profile_path': director.get('profile_path')
        } if director else None,
        'writers': [
            {
                'name': writer.get('name'),
                'job': writer.get('job')
            }
            for writer in writers
        ],
        'producers': [
            {
                'name': producer.get('name')
            }
            for producer in producers
        ]
    }

def normalize_predicted_rating(raw_prediction: float, all_predictions: List[float]) -> float:
    """Normalize predicted rating to 1-5 scale"""
    try:
        if raw_prediction == float('-inf') or raw_prediction == float('inf'):
            return 2.5  # Default neutral rating
        
        # If predictions are similarity scores (typically -1 to 1), normalize to 1-5
        if -1 <= raw_prediction <= 1:
            return ((raw_prediction + 1) / 2) * 4 + 1  # Maps [-1,1] to [1,5]
        
        # If predictions are already in a reasonable range (0-5), use as is
        elif 0 <= raw_prediction <= 5:
            return raw_prediction
        
        # If predictions are cosine similarities (0-1), scale to 1-5
        elif 0 <= raw_prediction <= 1:
            return raw_prediction * 4 + 1  # Maps [0,1] to [1,5]
        
        # For other ranges, normalize using min-max scaling
        else:
            # Filter out infinite values
            valid_predictions = [v for v in all_predictions 
                               if v != float('-inf') and v != float('inf')]
            
            if valid_predictions and len(valid_predictions) > 1:
                min_pred = min(valid_predictions)
                max_pred = max(valid_predictions)
                
                if max_pred != min_pred:
                    normalized = ((raw_prediction - min_pred) / (max_pred - min_pred)) * 4 + 1
                    return max(1.0, min(5.0, normalized))
            
            return 3.0  # Default middle rating
            
    except Exception as e:
        print(f"Error normalizing rating {raw_prediction}: {str(e)}")
        return 3.0

@router.post("/validate-id", response_model=Dict)
async def validate_user_id(user_id: int):
    """Validate if a user ID exists in the dataset"""
    if ratings_df.empty:
        raise HTTPException(status_code=404, detail="Ratings data not available")

    user_exists = user_id in ratings_df['userId'].values
    max_user_id = int(ratings_df['userId'].max())

    return {
        "valid": user_exists,
        "maxUserId": max_user_id
    }

@router.post("/recommendations", response_model=RecommendationResponse)
async def get_recommendations(input_data: UserRatingsInput):
    """Get movie recommendations for a user with enhanced contextual information"""
    user_id = input_data.user_id
    user_ratings = input_data.ratings or {}
    top_k = input_data.top_k or 10  # Usar el valor del request o default a 5

    try:
        # Get recommendations with predicted ratings
        recommendation_ids, predicted_ratings = recommendation_model.get_recommendations(
            user_id=user_id,
            user_ratings=user_ratings,
            top_k=top_k,  # Usar el valor dinámico
            return_scores=True
        )
        print(f"Raw predicted_ratings for top_{top_k}:", predicted_ratings)

        # Get basic movie details from data processor
        basic_movie_details = data_processor.get_movie_details(recommendation_ids)
        
        # Normalize all predicted ratings
        all_raw_predictions = list(predicted_ratings.values())
        
        # Enhance each movie with TMDB data asynchronously
        async with aiohttp.ClientSession() as session:
            enhanced_movies = []
            
            for movie in basic_movie_details:
                movie_id = str(movie.get('movieId', movie.get('id')))
                movie_title = movie.get('title', '')
                
                # Get enhanced TMDB data
                enhanced_data = await get_tmdb_movie_details(session, movie_title, movie_id)
                
                # Add predicted rating
                if movie_id in predicted_ratings:
                    raw_prediction = predicted_ratings[movie_id]
                    normalized_rating = normalize_predicted_rating(raw_prediction, all_raw_predictions)
                    enhanced_data['predicted_rating'] = round(normalized_rating, 2)
                    print(f'Movie {movie_id} ({movie_title}) - Raw: {raw_prediction}, Normalized: {normalized_rating}')
                else:
                    enhanced_data['predicted_rating'] = 3.0
                
                # Add actual TMDB rating for comparison
                enhanced_data['actual_rating'] = enhanced_data.get('vote_average')
                
                enhanced_movies.append(enhanced_data)
        
        print(f"Returning {len(enhanced_movies)} enhanced movies")
        return RecommendationResponse(recommendations=enhanced_movies)

    except Exception as e:
        print(f"Error getting recommendations: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error generating recommendations: {str(e)}")


@router.get("/user/{user_id}/ratings", response_model=Dict)
async def get_user_ratings(user_id: int):
    """Get all ratings for a specific user"""
    if ratings_df.empty:
        raise HTTPException(status_code=404, detail="Ratings data not available")
    
    user_ratings = ratings_df[ratings_df['userId'] == user_id]
    
    if user_ratings.empty:
        raise HTTPException(status_code=404, detail="User not found")
    
    # Convert to dictionary format
    ratings_dict = dict(zip(
        user_ratings['movieId'].astype(str), 
        user_ratings['rating']
    ))
    
    return {
        "userId": user_id,
        "ratings": ratings_dict,
        "totalRatings": len(ratings_dict)
    }

@router.get("/movies/{movie_id}/details", response_model=Dict)
async def get_movie_details(movie_id: str):
    """Get detailed information for a specific movie"""
    try:
        # Get basic movie details from data processor
        basic_details = data_processor.get_movie_details([movie_id])
        
        if not basic_details:
            raise HTTPException(status_code=404, detail="Movie not found")
        
        movie = basic_details[0]
        movie_title = movie.get('title', '')
        
        # Enhance with TMDB data
        async with aiohttp.ClientSession() as session:
            enhanced_data = await get_tmdb_movie_details(session, movie_title, movie_id)
        
        return enhanced_data
        
    except Exception as e:
        print(f"Error getting movie details: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Error fetching movie details: {str(e)}")

@router.get("/stats", response_model=Dict)
async def get_system_stats():
    """Get system statistics"""
    if ratings_df.empty:
        raise HTTPException(status_code=404, detail="Ratings data not available")
    
    total_users = ratings_df['userId'].nunique()
    total_movies = ratings_df['movieId'].nunique()
    total_ratings = len(ratings_df)
    avg_rating = ratings_df['rating'].mean()
    
    return {
        "totalUsers": total_users,
        "totalMovies": total_movies,
        "totalRatings": total_ratings,
        "averageRating": round(avg_rating, 2)
    }