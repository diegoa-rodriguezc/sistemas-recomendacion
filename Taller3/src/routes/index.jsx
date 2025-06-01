import React from 'react';
import { Routes, Route } from 'react-router-dom';
import Home from '../views/Home/Home';
import Login from '../views/Login/Login';

const AppRoutes = () => {
	return (
		<Routes>
			<Route path="/" element={<Home />} />
			<Route path="/login" element={<Login />} />
		</Routes>
	);
};

export default AppRoutes;