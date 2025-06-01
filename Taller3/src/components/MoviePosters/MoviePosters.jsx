import React, { useEffect, useState, useRef } from 'react';
import Slider from 'react-slick';
import ColorThief from 'colorthief';
import Heading from '../../components/Heading/Heading';
import 'slick-carousel/slick/slick.css';
import 'slick-carousel/slick/slick-theme.css';
import './MoviePosters.scss';

const MoviePosters = () => {
	const [movies, setMovies] = useState([]);
	const [loading, setLoading] = useState(true);
	const [currentMovie, setCurrentMovie] = useState(null);
	const sliderRef = useRef();
	const initialLogged = useRef(false);
	const [mainColors, setMainColors] = useState(['rgb(38,70,83)', 'rgb(42,157,143)']);
	const colorThief = useRef(new ColorThief());

	const cleanMovieTitle = (title) => {
		let cleanTitle = title.replace(/\s*\(\d{4}\)$/, '');
		cleanTitle = cleanTitle.replace(/\s*\(a\.k\.a\.\s+[^)]+\)/i, '');
		const articleRegex = /^(.+),\s+(The|A|An)$/;
		const match = cleanTitle.match(articleRegex);
		if (match) {
			cleanTitle = `${match[2]} ${match[1]}`;
		}
		return cleanTitle;
	};

	// Enhanced function to get detailed movie information from TMDB
	const getDetailedMovieInfo = async (cleanTitle, originalMovie) => {
		try {
			const apiKey = import.meta.env.VITE_TMDB_API_KEY;
			
			// First, search for the movie
			const searchResponse = await fetch(
				`https://api.themoviedb.org/3/search/movie?api_key=${apiKey}&query=${encodeURIComponent(cleanTitle)}&page=1`
			);
			const searchData = await searchResponse.json();
			const movieDetails = searchData.results[0] || {};

			// If we have a movie ID, get detailed information
			let additionalDetails = {};
			let credits = {};
			if (movieDetails.id) {
				try {
					// Get detailed movie information including genres, runtime, etc.
					const detailsResponse = await fetch(
						`https://api.themoviedb.org/3/movie/${movieDetails.id}?api_key=${apiKey}&language=es-ES`
					);
					additionalDetails = await detailsResponse.json();

					// Get cast and crew information
					const creditsResponse = await fetch(
						`https://api.themoviedb.org/3/movie/${movieDetails.id}/credits?api_key=${apiKey}`
					);
					credits = await creditsResponse.json();
				} catch (error) {
					console.error(`Error fetching additional details for movie ${cleanTitle}:`, error);
				}
			}

			return {
				...originalMovie,
				title: cleanTitle,
				originalTitle: originalMovie.originalTitle || originalMovie.title,
				id: movieDetails.id || originalMovie.movieId,
				poster_path: movieDetails.poster_path || null,
				backdrop_path: movieDetails.backdrop_path || null,
				release_date: movieDetails.release_date || additionalDetails.release_date || null,
				overview: movieDetails.overview || additionalDetails.overview || 'No hay descripción disponible',
				genres: additionalDetails.genres || [],
				runtime: additionalDetails.runtime || null,
				vote_average: movieDetails.vote_average || null,
				vote_count: movieDetails.vote_count || null,
				original_language: movieDetails.original_language || null,
				popularity: movieDetails.popularity || null,
				adult: movieDetails.adult || false,
				budget: additionalDetails.budget || null,
				revenue: additionalDetails.revenue || null,
				production_companies: additionalDetails.production_companies || [],
				production_countries: additionalDetails.production_countries || [],
				spoken_languages: additionalDetails.spoken_languages || [],
				tagline: additionalDetails.tagline || null,
				// Cast and crew information
				cast: credits.cast ? credits.cast.slice(0, 5) : [], // Top 5 actors
				director: credits.crew ? credits.crew.find(person => person.job === 'Director') : null,
				writers: credits.crew ? credits.crew.filter(person => person.job === 'Writer' || person.job === 'Screenplay').slice(0, 3) : [],
				producers: credits.crew ? credits.crew.filter(person => person.job === 'Producer').slice(0, 2) : []
			};
		} catch (error) {
			console.error(`Error fetching details for movie ${cleanTitle}:`, error);
			return {
				...originalMovie,
				title: cleanTitle,
				id: originalMovie.movieId,
				poster_path: null,
				backdrop_path: null,
				overview: 'No hay información disponible',
				genres: [],
				cast: [],
				director: null
			};
		}
	};

	const getMainColorsFromImage = (imageUrl) => {
		return new Promise((resolve, reject) => {
			const img = new Image();
			img.crossOrigin = 'Anonymous';
			img.src = imageUrl;

			img.onload = () => {
				try {
					const palette = colorThief.current.getPalette(img, 2);
					const colors = palette.map(color =>
						`rgb(${color[0]}, ${color[1]}, ${color[2]})`
					);
					resolve(colors);
				} catch (error) {
					console.error('ColorThief error:', error);
					resolve(['rgb(38,70,83)', 'rgb(42,157,143)']);
				}
			};

			img.onerror = () => {
				console.error('Error loading image');
				resolve(['rgb(38,70,83)', 'rgb(42,157,143)']);
			};
		});
	};

	const handleAfterChange = (current) => {
		const movie = movies[current];
		setCurrentMovie(movie);

		if (movie && movie.poster_path) {
			const imageUrl = `https://image.tmdb.org/t/p/w300${movie.poster_path}`;
			getMainColorsFromImage(imageUrl)
				.then(colors => {
					setMainColors(colors);
				})
				.catch(() => {
					setMainColors(['rgb(38,70,83)', 'rgb(42,157,143)']);
				});
		} else {
			setMainColors(['rgb(38,70,83)', 'rgb(42,157,143)']);
		}
	};

	useEffect(() => {
		if (!loading && movies.length > 0 && !initialLogged.current) {
			handleAfterChange(0);
			initialLogged.current = true;
		}
	}, [loading, movies]);

	useEffect(() => {
		const fetchRecommendations = async () => {
			try {
				setLoading(true);

				// Check for user authentication type
				const userId = localStorage.getItem('movieAppUserId');
				let requestBody;

				if (userId) {
					// ID-authenticated user - send empty object instead of null
					requestBody = {
						user_id: userId,
						ratings: {}, // Changed from null to empty object
						top_k: 10 // Request 10 recommendations
					};
					console.log("Fetching 10 recommendations for ID-based user:", userId);
				} else {
					// Password-authenticated user - use localStorage ratings
					const storedRatings = JSON.parse(localStorage.getItem('movieRatings') || '{}');

					if (Object.keys(storedRatings).length === 0) {
						console.warn("No ratings found in localStorage");
						setLoading(false);
						return;
					}

					// Create a simplified format that API expects
					const formattedRatings = {};
					Object.entries(storedRatings).forEach(([movieId, data]) => {
						// Extract just the rating value from the stored object
						formattedRatings[movieId] = data.rating;
					});

					requestBody = {
						user_id: "anonymous",
						ratings: formattedRatings,
						top_k: 10 // Request 10 recommendations
					};
					console.log("Fetching 10 recommendations for password user with local ratings");
				}

				// Send request to backend
				const response = await fetch('http://localhost:8000/api/recommendations', {
					method: 'POST',
					headers: {
						'Content-Type': 'application/json'
					},
					body: JSON.stringify(requestBody)
				});

				if (!response.ok) {
					throw new Error(`API responded with status: ${response.status}`);
				}

				const data = await response.json();
				const recommendedMovies = data.recommendations || [];
				console.log("Received 10 recommendations:", recommendedMovies);

				// Enhance recommendations with detailed TMDB data
				const updatedMovies = await Promise.all(
					recommendedMovies.map(async (movie) => {
						// Use the predicted_rating directly from the backend (already normalized to 1-5)
						const predictedRating = movie.predicted_rating;
						console.log(`Movie ${movie.title} predicted rating from backend:`, predictedRating);
						
						const cleanTitle = cleanMovieTitle(movie.title);
						const enhancedMovie = await getDetailedMovieInfo(cleanTitle, {
							...movie,
							originalTitle: movie.title,
							predicted_rating: predictedRating
						});

						return enhancedMovie;
					})
				);

				console.log("Final updated movies with enhanced data (10 movies):", updatedMovies.map(m => ({
					title: m.title,
					predicted_rating: m.predicted_rating,
					genres: m.genres?.map(g => g.name),
					director: m.director?.name
				})));
				setMovies(updatedMovies);
			} catch (error) {
				console.error('Error fetching recommendations:', error);
			} finally {
				setLoading(false);
			}
		};

		fetchRecommendations();
	}, []);

	// Helper functions for display
	const getYear = (releaseDate) => {
		return releaseDate ? new Date(releaseDate).getFullYear() : null;
	};

	const formatRuntime = (runtime) => {
		if (!runtime) return null;
		const hours = Math.floor(runtime / 60);
		const minutes = runtime % 60;
		return hours > 0 ? `${hours}h ${minutes}m` : `${minutes}m`;
	};

	const formatCurrency = (amount) => {
		if (!amount || amount === 0) return null;
		return new Intl.NumberFormat('en-US', {
			style: 'currency',
			currency: 'USD',
			minimumFractionDigits: 0,
			maximumFractionDigits: 0
		}).format(amount);
	};

	const sliderSettings = {
		dots: true, // Enabled dots to help navigate through 10 movies
		arrows: true,
		infinite: true,
		slidesToShow: 4, // Show 4 slides at once to accommodate more movies
		slidesToScroll: 1, // Scroll 2 at a time for better navigation
		autoplay: false,
		afterChange: handleAfterChange,
		focusOnSelect: true,
		responsive: [
			{
				breakpoint: 1400, // Large screens
				settings: {
					slidesToShow: 4,
					slidesToScroll: 1
				}
			},
			{
				breakpoint: 1024, // Medium screens
				settings: {
					slidesToShow: 3,
					slidesToScroll: 1
				}
			},
			{
				breakpoint: 768, // Small tablets
				settings: {
					slidesToShow: 2,
					slidesToScroll: 1
				}
			},
			{
				breakpoint: 600, // Mobile
				settings: {
					slidesToShow: 1,
					slidesToScroll: 1
				}
			}
		]
	};

	return (
		<div
			className="movie-posters"
			style={{
				background: `linear-gradient(to right, 
				  ${mainColors[0].startsWith('rgba') ? mainColors[1] : mainColors[1].replace('#', 'rgba(').replace(')', ', 0)')},  
				  ${mainColors[0].startsWith('rgba') ? mainColors[0] : mainColors[0].replace('#', 'rgba(').replace(')', ', 1)')}, 
				  ${mainColors[1].startsWith('rgba') ? mainColors[0] : mainColors[0].replace('#', 'rgba(').replace(')', ', 1)')}
				)`,
				transition: 'background 0.5s'
			}}
		>
			<div className="movie-backdrop">
				{currentMovie && currentMovie.backdrop_path && (
					<img
						src={`https://image.tmdb.org/t/p/w1280${currentMovie.backdrop_path}`}
						alt={`${currentMovie.title} backdrop`}
						className="movie-backdrop"
					/>
				)}
			</div>
			<Heading level={1} className='heading-3 text-center main-heading'>
				Películas Recomendadas ({movies.length} películas)
			</Heading>
			{loading ? (
				<div className="loading-container">
					<p>Cargando 10 recomendaciones personalizadas...</p>
				</div>
			) : (
				<div className="movies-slider">
					<Slider ref={sliderRef} {...sliderSettings}>
						{movies.map((movie, index) => (
							<div key={movie.id} className="movie-card">
								{movie.poster_path ? (
									<div className="poster">
										<img
											src={`https://image.tmdb.org/t/p/w500${movie.poster_path}`}
											alt={movie.title}
											className="movie-poster"
										/>
										<div className="movie-number">
											{index + 1}
										</div>
									</div>
								) : (
									<div className="no-poster">
										<Heading level={2} className='heading-3'>{movie.title}</Heading>
										<div className="movie-number">
											{index + 1}
										</div>
									</div>
								)}
							</div>
						))}
					</Slider>
					<div className="movie-details">
						{currentMovie && (
							<>
								<Heading level={3} className='heading-5 movie-title'>
									{currentMovie.title}
									{getYear(currentMovie.release_date) && (
										<span className="movie-year"> ({getYear(currentMovie.release_date)})</span>
									)}
								</Heading>

								{/* Tagline */}
								{/* {currentMovie.tagline && (
									<p className="movie-tagline">"{currentMovie.tagline}"</p>
								)} */}

								{/* Basic movie info */}
								<div className="movie-metadata">
									{currentMovie.genres && currentMovie.genres.length > 0 && (
										<div className="genres">
											<span className="label">Géneros: </span>
											<span>{currentMovie.genres.map(g => g.name).join(', ')}</span>
										</div>
									)}
									
									{currentMovie.runtime && (
										<div className="runtime">
											<span className="label">Duración: </span>
											<span>{formatRuntime(currentMovie.runtime)}</span>
										</div>
									)}

									{currentMovie.original_language && (
										<div className="language">
											<span className="label">Idioma: </span>
											<span>{currentMovie.original_language.toUpperCase()}</span>
										</div>
									)}
								</div>

								{/* Cast and crew */}
								{currentMovie.director && (
									<div className="crew-info">
										<div className="director">
											<span className="label">Director: </span>
											<span>{currentMovie.director.name}</span>
										</div>
									</div>
								)}

								{currentMovie.cast && currentMovie.cast.length > 0 && (
									<div className="cast-info">
										<span className="label">Reparto: </span>
										<span>{currentMovie.cast.map(actor => actor.name).join(', ')}</span>
									</div>
								)}

								{/* Production info */}
								{currentMovie.production_companies && currentMovie.production_companies.length > 0 && (
									<div className="production-info">
										<span className="label">Productora: </span>
										<span>{currentMovie.production_companies[0].name}</span>
									</div>
								)}

								{/* Budget and revenue */}
								{(currentMovie.budget > 0 || currentMovie.revenue > 0) && (
									<div className="financial-info">
										{currentMovie.budget > 0 && (
											<div className="budget">
												<span className="label">Presupuesto: </span>
												<span>{formatCurrency(currentMovie.budget)}</span>
											</div>
										)}
										{currentMovie.revenue > 0 && (
											<div className="revenue">
												<span className="label">Recaudación: </span>
												<span>{formatCurrency(currentMovie.revenue)}</span>
											</div>
										)}
									</div>
								)}

								{/* Synopsis */}
								<p className="movie-overview">
									{currentMovie.overview}
								</p>

								{/* Ratings */}
								<div className="movie-rating">
									{currentMovie.vote_average && (
										<p>Calificación : <span className="rating-value tmdb">{(currentMovie.vote_average/2).toFixed(2)}/5</span>
										{currentMovie.vote_count && (
											<span className="vote-count"> ({currentMovie.vote_count} votos)</span>
										)}</p>
									)}
									{currentMovie.predicted_rating && (
										<p>Calificación Predicha: <span className="rating-value predicted">{currentMovie.predicted_rating.toFixed(2)}/5</span></p>
									)}
									{/* {currentMovie.popularity && (
										<p>Popularidad: <span className="popularity-value">{Math.round(currentMovie.popularity)}</span></p>
									)} */}
								</div>
							</>
						)}
					</div>
				</div>
			)}
		</div>
	);
};

export default MoviePosters;