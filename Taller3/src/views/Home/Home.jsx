import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import { auth, db } from '../../services/firebase.service';
import { onAuthStateChanged, setPersistence, browserSessionPersistence } from 'firebase/auth';
import { doc, getDoc } from 'firebase/firestore';
import Header from '../../components/Header/Header';
import MoviePosters from '../../components/MoviePosters/MoviePosters';
import RecommendationsList from '../../components/RecommendationsList/RecommendationsList';
import MovieRatingPopup from '../../components/MovieRatingPopup/MovieRatingPopup';
import './Home.scss';

const Home = () => {
	const navigate = useNavigate();
	const [isLoading, setIsLoading] = useState(true);
	const [hasRatedMovies, setHasRatedMovies] = useState(false);

	useEffect(() => {
		// Set session persistence
		setPersistence(auth, browserSessionPersistence)
			.then(() => {
				// After setting persistence, set up the auth state listener
				const unsubscribe = onAuthStateChanged(auth, async (user) => {
					const localUserId = localStorage.getItem('movieAppUserId');
					if (!user && !localUserId) {
						navigate('/login', { replace: true });
					} else {
						try {
							if (user) {
								// Handle Firebase authenticated users as before
								const userDoc = await getDoc(doc(db, 'users', user.uid));
								if (userDoc.exists()) {
									const userData = userDoc.data();
									setHasRatedMovies(userData.hasRatedMovies || false);
								}
							} else {
								// ID-based login users can bypass Firebase auth
								setHasRatedMovies(false); // Or set a default value for ID users
							}
						} catch (error) {
							console.error("Error fetching user rating status:", error);
						}
					}
					setIsLoading(false);
				});

				return () => unsubscribe();
			})
			.catch((error) => {
				console.error("Error setting auth persistence:", error);
			});
	}, [navigate]);

	if (isLoading) {
		return <div>Loading...</div>;
	}

	return (
		<div className="home-view">
			{hasRatedMovies || localStorage.getItem('movieAppUserId') ? (
				<>
					<Header />
					<div className="home-content">
						<MoviePosters />
						<RecommendationsList />
					</div>
				</>
			) : (
				<>
					<MovieRatingPopup />
				</>
			)}
		</div>
	);
};

export default Home;