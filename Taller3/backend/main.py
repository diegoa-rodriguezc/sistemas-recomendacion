from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from routers import recommendations, user_ratings, genres, movies


app = FastAPI(title="Movie Recommendation API")

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your frontend URL
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(recommendations.router, prefix="/api", tags=["recommendations"])
app.include_router(user_ratings.router, prefix="/api" , tags=["user_ratings"])
app.include_router(genres.router, prefix="/api", tags=["genres"])
app.include_router(movies.router, prefix="/api", tags=["movies"])

@app.get("/")
async def root():
    return {"message": "Movie Recommendation API is running"}