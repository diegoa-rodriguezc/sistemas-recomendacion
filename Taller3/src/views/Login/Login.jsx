import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import Heading from '../../components/Heading/Heading';
import Input from '../../components/Input/Input';
import Button from '../../components/Button/Button';
import Paragraph from '../../components/Paragraph/Paragraph';
import { registerUser, loginUser, auth } from '../../services/firebase.service';
import { movielensService } from '../../services/movielensService.service';
import { onAuthStateChanged } from 'firebase/auth';
import './Login.scss';

const Login = () => {
	const navigate = useNavigate();
	const [loginType, setLoginType] = useState('id');
	const [isLogin, setIsLogin] = useState(true);
	const [loading, setLoading] = useState(false);
	const [formData, setFormData] = useState({
		name: '',
		username: '',
		password: ''
	});
	const [userId, setUserId] = useState('');
	const [error, setError] = useState('');
    const [maxUserId, setMaxUserId] = useState(null);
    const [loadingMaxId, setLoadingMaxId] = useState(true);

	useEffect(() => {
		// Check if user is already authenticated
		const unsubscribe = onAuthStateChanged(auth, (user) => {
			if (user || localStorage.getItem('movieAppUserId')) {
				navigate('/');
			}
		});

        // Cargar el último ID de usuario
        const loadMaxUserId = async () => {
            try {
                setLoadingMaxId(true);
                const maxId = await movielensService.getMaxUserId();
                setMaxUserId(maxId);
            } catch (error) {
                console.error('Error cargando max user ID:', error);
                setMaxUserId('Error');
            } finally {
                setLoadingMaxId(false);
            }
        };

        loadMaxUserId();

		// Cleanup subscription
		return () => unsubscribe();
	}, [navigate]);

	const handleChange = (e) => {
		const { name, value } = e.target;
		setFormData({
			...formData,
			[name]: value
		});
	};

	const handleIdChange = (e) => {
        const value = e.target.value;
        if (value === '' || /^\d+$/.test(value)) {
            setUserId(value);
        }
    };

	const handleSubmit = async (e) => {
		e.preventDefault();
		setError('');
		setLoading(true);

		try {
			if (isLogin) {
				if (!formData.username || !formData.password) {
					throw new Error('Por favor ingresa usuario y contraseña');
				}

				await loginUser(formData.username, formData.password);
				navigate('/');
			} else {
				if (!formData.name || !formData.username || !formData.password) {
					throw new Error('Por favor completa todos los campos');
				}

				if (formData.password.length < 6) {
					throw new Error('La contraseña debe tener al menos 6 caracteres');
				}

				await registerUser({
					name: formData.name,
					username: formData.username,
					password: formData.password
				});

				// Show success message and switch to login
				setError('');
				setIsLogin(true);
				setFormData({...formData, password: ''});
			}
		} catch (err) {
			// Format error message
			const errorMessage = err.message || err.toString();

			if (errorMessage.includes('auth/invalid-credential')) {
				setError('Usuario o contraseña incorrectos');
			} else if (errorMessage.includes('Username already taken')) {
				setError('Este nombre de usuario ya está en uso');
			} else if (errorMessage.includes('auth/email-already-in-use')) {
				setError('Este nombre de usuario ya está en uso');
			} else if (errorMessage.includes('auth/')) {
				setError('Error de autenticación, intenta de nuevo');
			} else {
				setError(errorMessage);
			}
		} finally {
			setLoading(false);
		}
	};

	const handleIdLogin = async (e) => {
		e.preventDefault();
		setError('');
		setLoading(true);

		try {
			if (!userId) {
				throw new Error('Por favor ingresa un ID de usuario');
			}

			const userIdNum = parseInt(userId);
			if (isNaN(userIdNum) || userIdNum < 1 || userIdNum > maxUserId) {
				throw new Error(`Por favor ingresa un ID válido (entre 1 y ${maxUserId})`);
			}

			// Store user ID in localStorage to mark as logged in
			localStorage.setItem('movieAppUserId', userId);

			// Navigate to home page
			navigate('/');
		} catch (err) {
			setError(err.message);
		} finally {
			setLoading(false);
		}
	};

	const toggleMode = () => {
		setIsLogin(!isLogin);
		setError('');
		setFormData({
			name: '',
			username: '',
			password: ''
		});
	};

	return (
		<div className="login-view">
			<div className="login-container">
				<Heading level={2} className='heading-1 text-center'>
					{isLogin ? 'Bienvenido' : 'Regístrate'}
				</Heading>

                <div className="login-tabs">
                    <Button
                        className={`tab-button ${loginType === 'id' ? 'active' : ''}`}
                        onClick={() => setLoginType('id')}
                    >
                        Inicio por ID
                    </Button>
                    <Button
                        className={`tab-button ${loginType === 'user' ? 'active' : ''}`}
                        onClick={() => setLoginType('user')}
                    >
                        Inicio con Usuario
                    </Button>
                </div>

				{error && <Paragraph className="error">{error}</Paragraph>}

				{loginType === 'id' && (
					<>
						<Paragraph className="heading-context text-center">
							Por favor ingresa tus datos a continuación
						</Paragraph>

	                    <form onSubmit={handleIdLogin}>
	                        <Input
	                            type="text"
	                            placeholder={`Ej: ${Math.floor(Math.random() * (maxUserId || 100)) + 1}`}
	                            name="userId"
	                            label={`ID de Usuario`}
	                            value={userId}
	                            onChange={handleIdChange}
	                            disabled={loading}
	                        />

	                        <Button
	                            type="submit"
	                            className="submit-button"
	                            disabled={loading}
	                        >
	                            {loading ? 'Verificando...' : 'Iniciar con ID'}
	                        </Button>
	                    </form>
					</>
                )}

				{loginType === 'user' && (
                    <>
						<Paragraph className="heading-context text-center">
							Por favor ingresa tus datos a continuación
						</Paragraph>

						<form onSubmit={handleSubmit}>
							{!isLogin && (
								<Input
									type="text"
									placeholder="Nombre"
									name="name"
									label="Nombre Completo"
									value={formData.name}
									onChange={handleChange}
									disabled={loading}
								/>
							)}

							<Input
								type="text"
								placeholder="Usuario"
								name="username"
								label="Nombre de Usuario"
								value={formData.username}
								onChange={handleChange}
								disabled={loading}
							/>

							<Input
								type="password"
								placeholder="Contraseña"
								name="password"
								label="Contraseña"
								value={formData.password}
								onChange={handleChange}
								disabled={loading}
							/>

							<Button
								type="submit"
								className="submit-button"
								disabled={loading}
							>
								{loading
									? 'Procesando...'
									: (isLogin ? 'Iniciar Sesión' : 'Registrarse')
								}
							</Button>
						</form>

						<Paragraph className="toggle-form text-center">
							{isLogin ? "¿No tienes una cuenta? " : "¿Ya tienes una cuenta? "}
							<span onClick={!loading ? toggleMode : undefined} className={`toggle-link ${loading ? 'disabled' : ''}`}>
								{isLogin ? 'Regístrate aquí' : 'Inicia sesión aquí'}
							</span>
						</Paragraph>
                    </>
                )}
			</div>
		</div>
	);
};

export default Login;