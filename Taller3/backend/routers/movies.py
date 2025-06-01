from fastapi import APIRouter, HTTPException
import pandas as pd
import os
from typing import List, Optional

router = APIRouter()

# Path to the movies.csv file
MOVIES_CSV_PATH = os.path.join("data", "movies.csv")

@router.get("/movies")
async def get_movies_by_genre(genre: str, limit: Optional[int] = 20):
    """Return movies for a specific genre from movies.csv"""
    try:
        # Check if file exists
        if not os.path.exists(MOVIES_CSV_PATH):
            raise HTTPException(status_code=404, detail="Movies data file not found")

        # Read the CSV file
        df = pd.read_csv(MOVIES_CSV_PATH)

        # Filter movies by genre
        matching_movies = []
        for _, movie in df.iterrows():
            if 'genres' in df.columns and isinstance(movie.genres, str):
                movie_genres = movie.genres.split('|')
                if genre in movie_genres:
                    # Format the movie object for frontend
                    movie_data = {
                        "id": movie.get("movieId", ""),
                        "title": movie.get("title", ""),
                        "genres": movie.get("genres", "").split('|'),
                        # Add any additional fields you need
                        "poster_path": "",  # If you have poster paths in your CSV
                        "overview": ""      # If you have overviews in your CSV
                    }
                    matching_movies.append(movie_data)

        # Apply limit and return random selection
        import random
        if len(matching_movies) > limit:
            return random.sample(matching_movies, limit)
        return matching_movies

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching movies: {str(e)}")