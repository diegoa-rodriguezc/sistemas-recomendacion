from fastapi import APIRouter, HTTPException
import pandas as pd
import os

# Create a router instance
router = APIRouter()

# Path to the movies.csv file
MOVIES_CSV_PATH = os.path.join("data", "movies.csv")

@router.get("/genres")
async def get_genres():
    """Return all unique genres from movies.csv"""
    try:
        # Check if file exists
        if not os.path.exists(MOVIES_CSV_PATH):
            raise HTTPException(status_code=404, detail="Movies data file not found")

        # Read the CSV file
        df = pd.read_csv(MOVIES_CSV_PATH)

        # Extract and process genres
        genres_set = set()
        if 'genres' in df.columns:
            for genre_str in df['genres'].dropna():
                if isinstance(genre_str, str):
                    # Split genres if they're in pipe-separated format
                    genres = genre_str.split('|')
                    genres_set.update([g.strip() for g in genres if g.strip()])

        return sorted(list(genres_set))

    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error processing genres: {str(e)}")