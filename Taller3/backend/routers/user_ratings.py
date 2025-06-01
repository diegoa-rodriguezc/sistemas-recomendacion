from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
import pandas as pd
import os
from typing import List, Dict, Optional

from models.data_processor import DataProcessor

router = APIRouter()
data_processor = DataProcessor()

class UserRatingRequest(BaseModel):
    user_id: str
    page: Optional[int] = 1
    limit: Optional[int] = 10

class UserRating(BaseModel):
    movieId: str
    rating: float
    title: str

class UserRatingsResponse(BaseModel):
    ratings: List[UserRating]
    total_count: int

@router.post("/user_ratings", response_model=UserRatingsResponse)
async def get_user_ratings(request: UserRatingRequest):
    user_id = request.user_id
    page = request.page
    limit = request.limit
    offset = (page - 1) * limit

    if not user_id:
        raise HTTPException(status_code=400, detail="user_id is required")

    try:
        # Load ratings and movies data
        ratings_path = os.path.join(data_processor.data_dir, 'ratings.csv')
        movies_path = os.path.join(data_processor.data_dir, 'movies.csv')

        ratings_df = pd.read_csv(ratings_path)
        movies_df = pd.read_csv(movies_path)

        # Filter ratings for this user
        user_ratings = ratings_df[ratings_df['userId'] == int(user_id)]

        if user_ratings.empty:
            return {"ratings": [], "total_count": 0}

        # Get total count before pagination
        total_count = len(user_ratings)

        # Apply pagination
        user_ratings = user_ratings.sort_values(by='timestamp', ascending=False)
        paginated_ratings = user_ratings.iloc[offset:offset + limit]

        # Join with movies data to get titles
        result = paginated_ratings.merge(movies_df, on='movieId', how='left')

        # Convert to list of dictionaries
        ratings_list = []
        for _, row in result.iterrows():
            ratings_list.append({
                "movieId": str(row['movieId']),
                "rating": float(row['rating']),
                "title": row['title'] if not pd.isna(row['title']) else "Unknown Movie"
            })

        return {"ratings": ratings_list, "total_count": total_count}

    except ValueError:
        raise HTTPException(status_code=400, detail="Invalid user_id format")
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))