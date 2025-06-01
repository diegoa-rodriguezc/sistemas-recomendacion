import os
import pandas as pd
from typing import Dict, List, Any

class DataProcessor:
    def __init__(self, data_dir: str = "data"):
        self.data_dir = data_dir
        self._load_data()

    def _load_data(self):
        """Load movies and ratings data"""
        movies_path = os.path.join(self.data_dir, 'movies.csv')
        ratings_path = os.path.join(self.data_dir, 'ratings.csv')

        if not os.path.exists(movies_path) or not os.path.exists(ratings_path):
            raise FileNotFoundError(f"Required data files not found in {self.data_dir}")

        self.movies_df = pd.read_csv(movies_path)
        self.ratings_df = pd.read_csv(ratings_path)

        # Create a movie lookup dictionary for faster access
        self.movie_lookup = {str(row['movieId']): {
            'title': row['title'],
            'genres': row['genres']
        } for _, row in self.movies_df.iterrows()}

    def preprocess_user_ratings(self, user_ratings: Dict[str, float]) -> Dict[str, float]:
        """Preprocess user ratings to ensure they're in the correct format"""
        return {str(movie_id): float(rating) for movie_id, rating in user_ratings.items()}

    def get_movie_details(self, movie_ids):
        movies_path = os.path.join(self.data_dir, 'movies.csv')
        movies_df = pd.read_csv(movies_path)

        # Get TMDb data for posters, etc.
        links_path = os.path.join(self.data_dir, 'links.csv')
        tmdb_path = os.path.join(self.data_dir, 'tmdb_data.csv')

        links_df = None
        tmdb_df = None

        if os.path.exists(links_path):
            links_df = pd.read_csv(links_path)

        if os.path.exists(tmdb_path):
            tmdb_df = pd.read_csv(tmdb_path)

        # Get details for requested movie IDs
        movie_details = []
        for movie_id in movie_ids:
            if not isinstance(movie_id, (int, str)):
                continue

            movie_id_int = int(movie_id) if isinstance(movie_id, str) and movie_id.isdigit() else movie_id
            movie_row = movies_df[movies_df['movieId'] == movie_id_int]

            if not movie_row.empty:
                movie_detail = {
                    'id': str(movie_id),  # TMDb ID for frontend
                    'movieId': str(movie_id_int),  # Keep the MovieLens ID for matching with predictions
                    'title': movie_row['title'].iloc[0],
                    'vote_average': float(movie_row['vote_average'].iloc[0]) if 'vote_average' in movie_row.columns else None,
                }

                # Add TMDb details if available
                if links_df is not None and tmdb_df is not None:
                    link_row = links_df[links_df['movieId'] == movie_id_int]
                    if not link_row.empty and 'tmdbId' in link_row.columns:
                        tmdb_id = link_row['tmdbId'].iloc[0]
                        tmdb_row = tmdb_df[tmdb_df['id'] == tmdb_id]
                        if not tmdb_row.empty:
                            movie_detail['poster_path'] = tmdb_row['poster_path'].iloc[0] if 'poster_path' in tmdb_row.columns else None
                            movie_detail['overview'] = tmdb_row['overview'].iloc[0] if 'overview' in tmdb_row.columns else None
                            movie_detail['vote_average'] = float(tmdb_row['vote_average'].iloc[0]) if 'vote_average' in tmdb_row.columns else None

                movie_details.append(movie_detail)

        return movie_details