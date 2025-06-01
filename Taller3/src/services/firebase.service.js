// src/services/firebase.movielensService.service.js
import { initializeApp } from 'firebase/app';
import {
	getAuth,
	createUserWithEmailAndPassword,
	signInWithEmailAndPassword,
	onAuthStateChanged
} from 'firebase/auth';
import { getFirestore, doc, setDoc, getDoc, collection, query, where, getDocs } from 'firebase/firestore';

// Your web app's Firebase configuration
const firebaseConfig = {
	apiKey: import.meta.env.VITE_FIREBASE_API_KEY,
	authDomain: import.meta.env.VITE_FIREBASE_AUTH_DOMAIN,
	projectId: import.meta.env.VITE_FIREBASE_PROJECT_ID,
	storageBucket: import.meta.env.VITE_FIREBASE_STORAGE_BUCKET,
	messagingSenderId: import.meta.env.VITE_FIREBASE_MESSAGING_SENDER_ID,
	appId: import.meta.env.VITE_FIREBASE_APP_ID
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const auth = getAuth(app);
const db = getFirestore(app);

// Authentication functions
export const registerUser = async ({ name, username, password }) => {
	try {
		// Create email from username for Firebase auth
		const email = `${username}@example.com`;

		// Create the user in Firebase Authentication
		const userCredential = await createUserWithEmailAndPassword(auth, email, password);
		const user = userCredential.user;

		// Create user document in Firestore with explicit ID matching auth UID
		await setDoc(doc(db, "users", user.uid), {
			uid: user.uid,
			name: name,
			username: username,
			createdAt: new Date().toISOString(),
		});

		console.log("User registered successfully with ID:", user.uid);
		return user;
	} catch (error) {
		console.error("Registration error:", error);
		throw error;
	}
};

export const loginUser = async (username, password) => {
	try {
		// Create email from username (matching registration pattern)
		const email = `${username}@example.com`;

		// First authenticate with Firebase Auth
		const userCredential = await signInWithEmailAndPassword(auth, email, password);

		// After authentication, get user profile data
		const userDoc = await getDoc(doc(db, 'users', userCredential.user.uid));

		if (userDoc.exists()) {
			return {
				uid: userCredential.user.uid,
				...userDoc.data()
			};
		} else {
			throw new Error('User profile not found');
		}
	} catch (error) {
		console.error("Login error:", error);
		throw new Error(`Login failed: ${error.message}`);
	}
};

export const getCurrentUser = () => {
	return new Promise((resolve, reject) => {
		const unsubscribe = onAuthStateChanged(auth,
			(user) => {
				unsubscribe();
				resolve(user);
			},
			(error) => {
				reject(error);
			}
		);
	});
};

export const saveMovieRating = async (userId, movieId, rating) => {
	try {
		await setDoc(doc(db, `ratings/${userId}/movies`, movieId), {
			movieId,
			rating,
			timestamp: new Date().toISOString()
		});
		return true;
	} catch (error) {
		console.error('Error saving rating:', error);
		return false;
	}
};

export const updateUserRatingStatus = async (userId, hasRated) => {
	try {
		await setDoc(doc(db, 'users', userId), {
			hasRatedMovies: hasRated
		}, { merge: true });
		return true;
	} catch (error) {
		console.error('Error updating user rating status:', error);
		return false;
	}
};

export { auth, db };