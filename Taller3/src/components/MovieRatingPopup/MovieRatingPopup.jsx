import React, { useEffect, useState } from 'react';
import { auth, db, saveMovieRating, updateUserRatingStatus } from '../../services/firebase.service';
import Heading from '../Heading/Heading';
import Button from '../Button/Button';
import Paragraph from '../Paragraph/Paragraph';
import './MovieRatingPopup.scss';

const MovieRatingPopup = () => {
	const [step, setStep] = useState('genres');
	const [availableGenres, setAvailableGenres] = useState([]);
	const [selectedGenres, setSelectedGenres] = useState([]);
	const [currentGenreIndex, setCurrentGenreIndex] = useState(0);
	const [genreMovies, setGenreMovies] = useState({});
	const [currentMovieIndex, setCurrentMovieIndex] = useState(0);
	const [ratings, setRatings] = useState({});
	const [loading, setLoading] = useState(true);
	const [error, setError] = useState(null);

	const GENRES_TO_SELECT = 5;
	const MOVIES_PER_GENRE = 5;

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

	// Fetch available genres
	useEffect(() => {
		const fetchGenres = async () => {
			try {
				const response = await fetch('http://localhost:8000/api/genres');
				if (!response.ok) throw new Error('Failed to fetch genres');

				const data = await response.json();
				setAvailableGenres(data);
				setLoading(false);
			} catch (err) {
				console.error('Error fetching genres:', err);
				setError('Failed to load genres');
				setLoading(false);
			}
		};

		if (step === 'genres') {
			fetchGenres();
		}
	}, [step]);

	// Fetch movies for selected genres
	useEffect(() => {
		const fetchMoviesForGenres = async () => {
			if (step !== 'movies' || selectedGenres.length === 0) return;

			try {
				setLoading(true);
				const currentGenre = selectedGenres[currentGenreIndex];

				// Check if we already fetched movies for this genre
				if (genreMovies[currentGenre]) {
					setLoading(false);
					return;
				}

				const response = await fetch(`http://localhost:8000/api/movies?genre=${currentGenre}&limit=20`);
				if (!response.ok) throw new Error(`Failed to fetch movies for ${currentGenre}`);

				const data = await response.json();
				// Get 5 random movies from this genre
				const randomMovies = data.sort(() => 0.5 - Math.random()).slice(0, MOVIES_PER_GENRE);

				// Enrich with TMDB data
				const apiKey = import.meta.env.VITE_TMDB_API_KEY;
				const enrichedMovies = await Promise.all(
					randomMovies.map(async (movie) => {
						try {
							const cleanTitle = cleanMovieTitle(movie.title);
							const tmdbResponse = await fetch(
								`https://api.themoviedb.org/3/search/movie?api_key=${apiKey}&query=${encodeURIComponent(cleanTitle)}&page=1`
							);
							const tmdbData = await tmdbResponse.json();
							const movieDetails = tmdbData.results[0] || {};

							return {
								...movie,
								title: cleanTitle,
								originalTitle: movie.title,
								id: movieDetails.id || movie.id,
								poster_path: movieDetails.poster_path || null,
								overview: movieDetails.overview || "No overview available"
							};
						} catch (error) {
							console.error(`Error fetching details for movie ${movie.title}:`, error);
							return {
								...movie,
								title: cleanMovieTitle(movie.title),
								originalTitle: movie.title,
								poster_path: null,
								overview: "No overview available"
							};
						}
					})
				);

				setGenreMovies(prev => ({
					...prev,
					[currentGenre]: enrichedMovies
				}));

				setLoading(false);
			} catch (err) {
				console.error('Error fetching genre movies:', err);
				setError(`Failed to load movies for ${selectedGenres[currentGenreIndex]}`);
				setLoading(false);
			}
		};

		fetchMoviesForGenres();
	}, [step, currentGenreIndex, selectedGenres]);

	const handleGenreToggle = (genre) => {
		if (selectedGenres.includes(genre)) {
			setSelectedGenres(selectedGenres.filter(g => g !== genre));
		} else if (selectedGenres.length < GENRES_TO_SELECT) {
			setSelectedGenres([...selectedGenres, genre]);
		}
	};

	const handleSubmitGenres = () => {
		if (selectedGenres.length === GENRES_TO_SELECT) {
			localStorage.setItem('selectedGenres', JSON.stringify(selectedGenres));
			setStep('movies');
		}
	};

	const handleRateMovie = async (rating) => {
		const currentGenre = selectedGenres[currentGenreIndex];
		const currentMovie = genreMovies[currentGenre][currentMovieIndex];

		// Save rating
		const newRatings = {
			...ratings,
			[currentMovie.id]: { rating, genre: currentGenre, title: currentMovie.title }
		};
		setRatings(newRatings);

		// Save to localStorage
		localStorage.setItem('movieRatings', JSON.stringify(newRatings));

		try {
			if (auth.currentUser) {
				await saveMovieRating(auth.currentUser.uid, currentMovie.id, rating);
			}

			// Navigate to next movie or genre
			if (currentMovieIndex < MOVIES_PER_GENRE - 1) {
				setCurrentMovieIndex(currentMovieIndex + 1);
			} else if (currentGenreIndex < selectedGenres.length - 1) {
				setCurrentGenreIndex(currentGenreIndex + 1);
				setCurrentMovieIndex(0);
			} else {
				// All movies rated
				if (auth.currentUser) {
					await updateUserRatingStatus(auth.currentUser.uid, true);
				}
				localStorage.setItem('hasRatedMovies', 'true');
				window.location.reload();
			}
		} catch (err) {
			setError('Failed to save rating');
			console.error(err);
		}
	};

	if (loading) return (
		<div className="movie-rating-container">
			<Heading level={2}>Loading...</Heading>
		</div>
	);

	if (error) return (
		<div className="movie-rating-container">
			<Heading level={2}>{error}</Heading>
		</div>
	);

	// Genre selection screen
	if (step === 'genres') {
		return (
			<div className="movie-rating-container">
				<Heading level={2} className="main-heading">Select Your Favorite Genres</Heading>
				<Paragraph>Choose {GENRES_TO_SELECT} genres to help us recommend movies for you!</Paragraph>

				<div className="genre-selection">
					{availableGenres.map(genre => (
						<Button
							key={genre}
							onClick={() => handleGenreToggle(genre)}
							className={`genre-btn ${selectedGenres.includes(genre) ? 'selected' : ''}`}
						>
							{genre}
						</Button>
					))}
				</div>

				<div className="genre-count">
					<Paragraph>Selected: {selectedGenres.length} of {GENRES_TO_SELECT}</Paragraph>
				</div>

				<Button
					onClick={handleSubmitGenres}
					disabled={selectedGenres.length !== GENRES_TO_SELECT}
					className="submit-btn"
				>
					Continue to Rating Movies
				</Button>
			</div>
		);
	}

	// Movie rating screen
	const currentGenre = selectedGenres[currentGenreIndex];
	const currentMovies = genreMovies[currentGenre] || [];
	const currentMovie = currentMovies[currentMovieIndex];

	return (
		<div className="movie-rating-container">
			<Heading level={2} className="main-heading">Rate Movies by Genre</Heading>
			<Paragraph className="genre-info">
				Genre: <strong>{currentGenre}</strong> ({currentGenreIndex + 1} of {selectedGenres.length})
			</Paragraph>

			<div className="rating-progress">
				<Paragraph>Movie {currentMovieIndex + 1} of {MOVIES_PER_GENRE}</Paragraph>
			</div>

			{currentMovie && (
				<div className="movie-card">
					<Heading level={3}>{currentMovie.title}</Heading>

					<div className="movie-details">
						{currentMovie.poster_path ? (
							<img
								src={`https://image.tmdb.org/t/p/w500${currentMovie.poster_path}`}
								alt={currentMovie.title}
								className="movie-poster"
							/>
						) : (
							<div className="no-poster">No image available</div>
						)}

						<div className="movie-info">
							<Paragraph>{currentMovie.overview}</Paragraph>
						</div>
					</div>
				</div>
			)}

			<div className="rating-buttons">
				<Paragraph>Your Rating:</Paragraph>
				<div className="stars">
					{[1, 2, 3, 4, 5].map(star => (
						<Button
							key={star}
							onClick={() => handleRateMovie(star)}
							className="rating-btn"
						>
							{star}★
						</Button>
					))}
				</div>
			</div>
		</div>
	);
};

export default MovieRatingPopup;