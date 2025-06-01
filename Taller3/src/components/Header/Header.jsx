import React, { useEffect, useState } from 'react';
import { useNavigate } from 'react-router-dom';
import Heading from '../Heading/Heading';
import Button from '../Button/Button';
import { auth, db } from '../../services/firebase.service';
import { signOut } from 'firebase/auth';
import { doc, getDoc, updateDoc } from 'firebase/firestore';
import './Header.scss';

const Header = () => {
	const navigate = useNavigate();
	const [userData, setUserData] = useState(() => {
		const userId = localStorage.getItem('movieAppUserId');
		return { name: userId ? `Usuario ${userId}` : 'Usuario' };
	});
	const [loading, setLoading] = useState(true);

	useEffect(() => {
		const fetchUserData = async () => {
			try {
				const currentUser = auth.currentUser;

				if (currentUser) {
					const userDocRef = doc(db, 'users', currentUser.uid);
					const userDoc = await getDoc(userDocRef);

					if (userDoc.exists()) {
						setUserData(userDoc.data());
					} else {
						console.error('User document not found');
					}
				}
			} catch (error) {
				console.error('Error fetching user data:', error);
			} finally {
				setLoading(false);
			}
		};

		fetchUserData();
	}, []);

	const handleLogout = async () => {
		try {
			await signOut(auth);
			sessionStorage.removeItem('authToken');
			sessionStorage.removeItem('userData');
			localStorage.removeItem('movieAppUserId');
			navigate('/login');
		} catch (error) {
			console.error('Logout error:', error);
		}
	};

	const handleRateMovies = async () => {
		try {
			const currentUser = auth.currentUser;
			if (currentUser) {
				const userDocRef = doc(db, 'users', currentUser.uid);
				await updateDoc(userDocRef, {
					hasRatedMovies: false
				});
				window.location.reload();
			}
		} catch (error) {
			console.error('Error resetting rating status:', error);
		}
	};

	return (
		<header className="app-header">
			<div className="header-content">
				<div className="welcome-section">
					<Heading level={3}>
						Bienvenido, {loading ? '...' : userData.name}
					</Heading>
				</div>
				<div className="header-actions">
					<Button onClick={handleRateMovies} className="rate-movies-button">Calificar Películas</Button>
					<Button onClick={handleLogout} className="logout-button">Cerrar Sesión</Button>
				</div>
			</div>
		</header>
	);
};

export default Header;