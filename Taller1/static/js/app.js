// Variables globales
let currentUserId = null;
let allMovies = [];
let userRatings = [];
let newUserRatings = {};

// Función para cargar la lista de usuarios
async function loadUsers() {
    try {
        const response = await fetch('/users');
        const users = await response.json();
        
        const userSelect = document.getElementById('userSelect');
        userSelect.innerHTML = '<option value="">Seleccionar usuario...</option>';
        
        users.forEach(user => {
            const option = document.createElement('option');
            option.value = user.userId;
            option.textContent = `${user.username} (ID: ${user.userId})`;
            userSelect.appendChild(option);
        });

        // Si hay un usuario en la URL, seleccionarlo
        const params = new URLSearchParams(window.location.search);
        const userId = params.get("userId");
        if (userId) {
            userSelect.value = userId;
        }
        
    } catch (error) {
        console.error('Error cargando usuarios:', error);
        alert('Error cargando la lista de usuarios');
    }
}

// Función para cargar películas populares (para nuevos usuarios)
async function loadPopularMovies() {
    try {
        const response = await fetch('/popular-movies');
        const movies = await response.json();
        
        const popularMoviesList = document.getElementById('popularMoviesList');
        popularMoviesList.innerHTML = '';
        
        movies.forEach(movie => {
            const movieCol = document.createElement('div');
            movieCol.className = 'col-md-6 mb-3';
            
            movieCol.innerHTML = `
                <div class="card h-100">
                    <div class="card-body">
                        <h6 class="card-title">${movie.title}</h6>
                        <p class="card-text"><small>${movie.genres}</small></p>
                        <div class="btn-group w-100" role="group">
                            ${[0.5, 1, 1.5, 2, 2.5, 3, 3.5, 4, 4.5, 5].map(rating => 
                                `<button type="button" class="btn btn-sm btn-outline-warning new-user-rating-btn" 
                                 data-movie-id="${movie.movieId}" data-rating="${rating}">${rating}</button>`
                            ).join('')}
                        </div>
                    </div>
                </div>
            `;
            
            popularMoviesList.appendChild(movieCol);
        });
        
        // Agregar event listeners a los botones de rating
        document.querySelectorAll('.new-user-rating-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                const movieId = e.target.dataset.movieId;
                const rating = parseFloat(e.target.dataset.rating);
                
                // Reiniciar botones para esta película
                document.querySelectorAll(`.new-user-rating-btn[data-movie-id="${movieId}"]`).forEach(b => {
                    b.classList.remove('btn-warning');
                    b.classList.add('btn-outline-warning');
                });
                
                // Activar botón seleccionado
                e.target.classList.remove('btn-outline-warning');
                e.target.classList.add('btn-warning');
                
                // Guardar rating
                newUserRatings[movieId] = rating;
            });
        });
    } catch (error) {
        console.error('Error cargando películas populares:', error);
    }
}

// Función para cargar todas las películas
async function loadAllMovies() {
    try {
        const response = await fetch('/movies?limit=1000');
        allMovies = await response.json();
        
        const movieSelect = document.getElementById('movieSelect');
        movieSelect.innerHTML = '<option value="">Seleccionar película...</option>';
        
        allMovies.forEach(movie => {
            const option = document.createElement('option');
            option.value = movie.movieId;
            option.textContent = movie.title;
            movieSelect.appendChild(option);
        });
    } catch (error) {
        console.error('Error cargando películas:', error);
    }
}

// Función para cargar los ratings de un usuario
async function loadUserRatings(userId) {
    try {
        const response = await fetch(`/user/${userId}/ratings`);
        userRatings = await response.json();
        
        const userRatingsList = document.getElementById('userRatingsList');
        userRatingsList.innerHTML = '';
        
        if (userRatings.length === 0) {
            userRatingsList.innerHTML = '<p class="text-center my-3">Este usuario aún no ha calificado películas</p>';
            return;
        }
        
        userRatings.forEach(rating => {
            const item = document.createElement('div');
            item.className = 'list-group-item d-flex justify-content-between align-items-center';
            
            // Crear estrellas basadas en el rating
            /*const stars = '★'.repeat(Math.floor(rating.rating)) + 
                         (rating.rating % 1 >= 0.5 ? '½' : '');*/
            const stars = '⭐' + 
                         (rating.rating % 1 >= 0.5 ? '½' : '');
                         
            item.innerHTML = `
                <div>
                    <h6 class="mb-0">${rating.title}</h6>
                    <small class="text-muted">${rating.genres}</small>
                </div>
                <span class="rating-star">${stars} <small>(${rating.rating})</small></span>
            `;
            
            userRatingsList.appendChild(item);
        });
        
        // Mostrar el card de ratings
        document.getElementById('userRatingsCard').style.display = 'block';
    } catch (error) {
        console.error('Error cargando ratings del usuario:', error);
    }
}

// Función para cargar recomendaciones basadas en usuario
async function loadUserBasedRecommendations(userId) {
    try {
        const response = await fetch(`/user/${userId}/recommendations/user-based?n=15`);
        if (!response.ok) throw new Error('Error al obtener recomendaciones');

        const recommendations = await response.json();
        const recommendationsDiv = document.getElementById('userBasedRecommendations');
        recommendationsDiv.innerHTML = '';

        if (!recommendations.length) {
            recommendationsDiv.innerHTML = '<div class="col-12 text-center my-5"><p>No hay suficientes datos para generar recomendaciones</p></div>';
            return;
        }

        recommendations.forEach(rec => {
            const movieCard = document.createElement('div');
            movieCard.className = 'col-md-6 col-lg-4 mb-4';

            // Crear estrellas basadas en el rating predicho
            //.repeat(Math.floor(rec.predicted_rating)) + 
            const stars = '⭐' + 
                         (rec.predicted_rating % 1 >= 0.5 ? '½' : '');

            // Verificar si hay explicación disponible
            let explanationHtml = '<p>No hay información de explicación disponible</p>';
            if (rec.explanation && rec.explanation.relevant_neighbors) {
                explanationHtml = `
                    <h6 class="card-subtitle mb-2">¿Por qué recomendamos esta película?</h6>
                    <p>Método: Filtrado colaborativo basado en usuarios</p>
                    <p>La predicción se basó en usuarios similares que han visto esta película:</p>
                    <ul class="list-group list-group-flush">
                `;

                rec.explanation.relevant_neighbors.forEach(neighbor => {
                    explanationHtml += `
                        <li class="list-group-item neighbor-item">
                            <div>
                                <strong>Usuario ${neighbor.userId}</strong> 
                                <span class="similarity-score">(Similitud: ${(neighbor.similarity * 100).toFixed(1)}%)</span>
                            </div>
                    `;

                    if (neighbor.rating_for_this_movie) {
                        explanationHtml += `
                            <div>
                                Calificó esta película: 
                                <span class="badge bg-primary">${neighbor.rating_for_this_movie.toFixed(1)}</span>
                            </div>
                        `;
                    }

                    if (neighbor.top_ratings && neighbor.top_ratings.length > 0) {
                        explanationHtml += `<div><small>También le gustaron:</small>`;
                        neighbor.top_ratings.slice(0, 2).forEach(rating => {
                            explanationHtml += `
                                <div class="d-flex align-items-center mt-1">
                                    <span class="user-rating">${rating.rating.toFixed(1)}</span>
                                    <span>${rating.title}</span>
                                </div>
                            `;
                        });
                        explanationHtml += `</div>`;
                    }

                    explanationHtml += `</li>`;
                });

                explanationHtml += `</ul>`;
            }

            movieCard.innerHTML = `
                <div class="card movie-card h-100">
                    <div class="card-body">
                        <h5 class="card-title">${rec.title}</h5>
                        <h6 class="card-subtitle mb-2 text-muted">${rec.genres}</h6>
                        <p class="card-text">
                            <span class="rating-star">${stars}</span>
                            <span class="fw-bold">${rec.predicted_rating.toFixed(2)}</span>/5.0 (predicción)
                        </p>
                        <button class="btn btn-sm btn-outline-info" type="button" data-bs-toggle="collapse" 
                                data-bs-target="#explanation-user-${rec.movieId}" aria-expanded="false">
                            Mostrar explicación
                        </button>
                        <div class="collapse mt-3" id="explanation-user-${rec.movieId}">
                            <div class="card card-body explanation-card">
                                ${explanationHtml}
                            </div>
                        </div>
                    </div>
                </div>
            `;

            recommendationsDiv.appendChild(movieCard);
        });
    } catch (error) {
        console.error('Error cargando recomendaciones basadas en usuario:', error);
        document.getElementById('userBasedRecommendations').innerHTML = '<div class="col-12 text-center my-5"><p>Error al cargar recomendaciones. Intente nuevamente.</p></div>';
    }
}

async function loadUserBasedRecommendations_version1(userId) {
    try {
        const response = await fetch(`/user/${userId}/recommendations/user-based?n=15`);
        const recommendations = await response.json();
        
        const recommendationsDiv = document.getElementById('userBasedRecommendations');
        recommendationsDiv.innerHTML = '';
        
        if (recommendations.length === 0) {
            recommendationsDiv.innerHTML = '<div class="col-12 text-center my-5"><p>No hay suficientes datos para generar recomendaciones</p></div>';
            return;
        }
        
        recommendations.forEach(rec => {
            const movieCard = document.createElement('div');
            movieCard.className = 'col-md-6 col-lg-4 mb-4';
            
            // Crear estrellas basadas en el rating predicho
            //.repeat(Math.floor(rec.predicted_rating)) + 
            const stars = '⭐' + 
                         (rec.predicted_rating % 1 >= 0.5 ? '½' : '');
            
            // Preparar la explicación de la recomendación
            let explanationHtml = `
                <h6 class="card-subtitle mb-2">¿Por qué recomendamos esta película?</h6>
                <p>Método: Filtrado colaborativo basado en usuarios</p>
                <p>La predicción se basó en usuarios similares que han visto esta película:</p>
                <ul class="list-group list-group-flush">
            `;
            
            rec.explanation.relevant_neighbors.forEach(neighbor => {
                explanationHtml += `
                    <li class="list-group-item neighbor-item">
                        <div>
                            <strong>Usuario ${neighbor.userId}</strong> 
                            <span class="similarity-score">(Similitud: ${(neighbor.similarity * 100).toFixed(1)}%)</span>
                        </div>
                `;
                
                if (neighbor.rating_for_this_movie) {
                    explanationHtml += `
                        <div>
                            Calificó esta película: 
                            <span class="badge bg-primary">${neighbor.rating_for_this_movie.toFixed(1)}</span>
                        </div>
                    `;
                }
                
                if (neighbor.top_ratings && neighbor.top_ratings.length > 0) {
                    explanationHtml += `<div><small>También le gustaron:</small>`;
                    
                    neighbor.top_ratings.slice(0, 2).forEach(rating => {
                        explanationHtml += `
                            <div class="d-flex align-items-center mt-1">
                                <span class="user-rating">${rating.rating.toFixed(1)}</span>
                                <span>${rating.title}</span>
                            </div>
                        `;
                    });
                    
                    explanationHtml += `</div>`;
                }
                
                explanationHtml += `</li>`;
            });
            
            explanationHtml += `</ul>`;
            
            movieCard.innerHTML = `
                <div class="card movie-card h-100">
                    <div class="card-body">
                        <h5 class="card-title">${rec.title}</h5>
                        <h6 class="card-subtitle mb-2 text-muted">${rec.genres}</h6>
                        <p class="card-text">
                            <span class="rating-star">${stars}</span>
                            <span class="fw-bold">${rec.predicted_rating.toFixed(2)}</span>/5.0 (predicción)
                        </p>
                        <button class="btn btn-sm btn-outline-info" type="button" data-bs-toggle="collapse" 
                                data-bs-target="#explanation-user-${rec.movieId}" aria-expanded="false">
                            Mostrar explicación
                        </button>
                        <div class="collapse mt-3" id="explanation-user-${rec.movieId}">
                            <div class="card card-body explanation-card">
                                ${explanationHtml}
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            recommendationsDiv.appendChild(movieCard);
        });
    } catch (error) {
        console.error('Error cargando recomendaciones basadas en usuario:', error);
        const recommendationsDiv = document.getElementById('userBasedRecommendations');
        recommendationsDiv.innerHTML = '<div class="col-12 text-center my-5"><p>Error al cargar recomendaciones. Intente nuevamente.</p></div>';
    }
}

// Función para cargar recomendaciones basadas en ítem
async function loadItemBasedRecommendations(userId) {
    try {
        const response = await fetch(`/user/${userId}/recommendations/item-based?n=15`);
        if (!response.ok) throw new Error('Error al obtener recomendaciones');

        const recommendations = await response.json();
        const recommendationsDiv = document.getElementById('itemBasedRecommendations');
        recommendationsDiv.innerHTML = '';

        if (!recommendations.length) {
            recommendationsDiv.innerHTML = '<div class="col-12 text-center my-5"><p>No hay suficientes datos para generar recomendaciones</p></div>';
            return;
        }

        recommendations.forEach(rec => {
            const movieCard = document.createElement('div');
            movieCard.className = 'col-md-6 col-lg-4 mb-4';

            // Crear estrellas basadas en el rating predicho
            //.repeat(Math.floor(rec.predicted_rating)) + 
            const stars = '⭐' + 
                         (rec.predicted_rating % 1 >= 0.5 ? '½' : '');

            // Verificar si hay explicación disponible
            let explanationHtml = '<p>No hay información de explicación disponible</p>';
            if (rec.explanation && rec.explanation.similar_items_rated_by_user) {
                explanationHtml = `
                    <h6 class="card-subtitle mb-2">¿Por qué recomendamos esta película?</h6>
                    <p>Método: Filtrado colaborativo basado en ítems</p>
                    <p>La predicción se basó en películas similares que has visto:</p>
                    <ul class="list-group list-group-flush">
                `;

                rec.explanation.similar_items_rated_by_user.forEach(item => {
                    explanationHtml += `
                        <li class="list-group-item neighbor-item">
                            <div>
                                <strong>${item.title}</strong>
                                <span class="similarity-score">(Similitud: ${(item.similarity * 100).toFixed(1)}%)</span>
                            </div>
                            <div>
                                Tu calificación: 
                                <span class="badge bg-success">${item.user_rating.toFixed(1)}</span>
                            </div>
                            <div><small>${item.genres}</small></div>
                        </li>
                    `;
                });

                explanationHtml += `</ul>`;
            }

            movieCard.innerHTML = `
                <div class="card movie-card h-100">
                    <div class="card-body">
                        <h5 class="card-title">${rec.title}</h5>
                        <h6 class="card-subtitle mb-2 text-muted">${rec.genres}</h6>
                        <p class="card-text">
                            <span class="rating-star">${stars}</span>
                            <span class="fw-bold">${rec.predicted_rating.toFixed(2)}</span>/5.0 (predicción)
                        </p>
                        <button class="btn btn-sm btn-outline-info" type="button" data-bs-toggle="collapse" 
                                data-bs-target="#explanation-item-${rec.movieId}" aria-expanded="false">
                            Mostrar explicación
                        </button>
                        <div class="collapse mt-3" id="explanation-item-${rec.movieId}">
                            <div class="card card-body explanation-card">
                                ${explanationHtml}
                            </div>
                        </div>
                    </div>
                </div>
            `;

            recommendationsDiv.appendChild(movieCard);
        });
    } catch (error) {
        console.error('Error cargando recomendaciones basadas en ítem:', error);
        document.getElementById('itemBasedRecommendations').innerHTML = '<div class="col-12 text-center my-5"><p>Error al cargar recomendaciones. Intente nuevamente.</p></div>';
    }
}

async function loadItemBasedRecommendations_version1(userId) {
    try {
        const response = await fetch(`/user/${userId}/recommendations/item-based?n=15`);
        const recommendations = await response.json();
        
        const recommendationsDiv = document.getElementById('itemBasedRecommendations');
        recommendationsDiv.innerHTML = '';
        
        if (recommendations.length === 0) {
            recommendationsDiv.innerHTML = '<div class="col-12 text-center my-5"><p>No hay suficientes datos para generar recomendaciones</p></div>';
            return;
        }
        
        recommendations.forEach(rec => {
            const movieCard = document.createElement('div');
            movieCard.className = 'col-md-6 col-lg-4 mb-4';
            
            // Crear estrellas basadas en el rating predicho
            //.repeat(Math.floor(rec.predicted_rating)) + 
            const stars = '⭐' + 
                         (rec.predicted_rating % 1 >= 0.5 ? '½' : '');
            
            // Preparar la explicación de la recomendación
            let explanationHtml = `
                <h6 class="card-subtitle mb-2">¿Por qué recomendamos esta película?</h6>
                <p>Método: Filtrado colaborativo basado en ítems</p>
                <p>La predicción se basó en películas similares que has visto:</p>
                <ul class="list-group list-group-flush">
            `;
            
            rec.explanation.similar_items_rated_by_user.forEach(item => {
                explanationHtml += `
                    <li class="list-group-item neighbor-item">
                        <div>
                            <strong>${item.title}</strong>
                            <span class="similarity-score">(Similitud: ${(item.similarity * 100).toFixed(1)}%)</span>
                        </div>
                        <div>
                            Tu calificación: 
                            <span class="badge bg-success">${item.user_rating.toFixed(1)}</span>
                        </div>
                        <div><small>${item.genres}</small></div>
                    </li>
                `;
            });
            
            explanationHtml += `</ul>`;
            
            movieCard.innerHTML = `
                <div class="card movie-card h-100">
                    <div class="card-body">
                        <h5 class="card-title">${rec.title}</h5>
                        <h6 class="card-subtitle mb-2 text-muted">${rec.genres}</h6>
                        <p class="card-text">
                            <span class="rating-star">${stars}</span>
                            <span class="fw-bold">${rec.predicted_rating.toFixed(2)}</span>/5.0 (predicción)
                        </p>
                        <button class="btn btn-sm btn-outline-info" type="button" data-bs-toggle="collapse" 
                                data-bs-target="#explanation-item-${rec.movieId}" aria-expanded="false">
                            Mostrar explicación
                        </button>
                        <div class="collapse mt-3" id="explanation-item-${rec.movieId}">
                            <div class="card card-body explanation-card">
                                ${explanationHtml}
                            </div>
                        </div>
                    </div>
                </div>
            `;
            
            recommendationsDiv.appendChild(movieCard);
        });
    } catch (error) {
        console.error('Error cargando recomendaciones basadas en ítem:', error);
        const recommendationsDiv = document.getElementById('itemBasedRecommendations');
        recommendationsDiv.innerHTML = '<div class="col-12 text-center my-5"><p>Error al cargar recomendaciones. Intente nuevamente.</p></div>';
    }
}

// Evento para seleccionar usuario
document.getElementById('userSelect').addEventListener('change', async (e) => {
    const userId = e.target.value;
    if (!userId) return;
    
    currentUserId = parseInt(userId);
    await loadUserRatings(userId);
    await loadUserBasedRecommendations(userId);
    await loadItemBasedRecommendations(userId);
});

// Evento para crear nuevo usuario
document.getElementById('createUserBtn').addEventListener('click', async () => {
    const username = document.getElementById('newUsername').value.trim();

    if (!username) {
        alert('Por favor ingrese un nombre de usuario');
        return;
    }

    if (Object.keys(newUserRatings).length < 5) {
        alert('Por favor califique al menos 5 películas para obtener mejores recomendaciones');
        return;
    }

    try {
        // Preparar datos para enviar al servidor
        const ratingsArray = [];
        for (const movieId in newUserRatings) {
            ratingsArray.push({ [movieId]: newUserRatings[movieId] });
        }

        const response = await fetch('/users/new', {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                username: username,
                ratings: ratingsArray
            })
        });

        const result = await response.json();

        // Cerrar correctamente el modal usando Bootstrap Modal
        const newUserModal = document.getElementById('newUserModal');
        const modalInstance = bootstrap.Modal.getInstance(newUserModal);
        if (modalInstance) modalInstance.hide();  // Asegurar que el modal se cierre bien

        // Limpiar formulario
        document.getElementById('newUsername').value = '';
        newUserRatings = {};
        document.querySelectorAll('.new-user-rating-btn').forEach(btn => {
            btn.classList.remove('btn-warning');
            btn.classList.add('btn-outline-warning');
        });

        // Recargar lista de usuarios y seleccionar el nuevo
        await loadUsers();
        currentUserId = result.userId;
        document.getElementById('userSelect').value = result.userId;

        // Cargar datos del nuevo usuario
        await loadUserRatings(result.userId);
        await loadUserBasedRecommendations(result.userId);
        await loadItemBasedRecommendations(result.userId);

        alert(`Usuario creado exitosamente con ID: ${result.userId}`);
    } catch (error) {
        console.error('Error creando usuario:', error);
        alert('Error al crear usuario');
    }
});

/*
document.getElementById('createUserBtn').addEventListener('click', async () => {
    const username = document.getElementById('newUsername').value.trim();
    
    if (!username) {
        alert('Por favor ingrese un nombre de usuario');
        return;
    }
    
    if (Object.keys(newUserRatings).length < 5) {
        alert('Por favor califique al menos 5 películas para obtener mejores recomendaciones');
        return;
    }
    
    try {
        // Preparar datos para enviar al servidor
        const ratingsArray = [];
        for (const movieId in newUserRatings) {
            const ratingObj = {};
            ratingObj[movieId] = newUserRatings[movieId];
            ratingsArray.push(ratingObj);
        }
        
        const response = await fetch('/users/new', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json'
            },
            body: JSON.stringify({
                username: username,
                ratings: ratingsArray
            })
        });
        
        const result = await response.json();
        
        // Cerrar modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('newUserModal'));
        modal.hide();
        
        // Limpiar datos de nuevo usuario
        document.getElementById('newUsername').value = '';
        newUserRatings = {};
        document.querySelectorAll('.new-user-rating-btn').forEach(btn => {
            btn.classList.remove('btn-warning');
            btn.classList.add('btn-outline-warning');
        });
        
        // Recargar lista de usuarios y seleccionar el nuevo
        await loadUsers();
        currentUserId = result.userId;
        document.getElementById('userSelect').value = result.userId;
        
        // Cargar datos del nuevo usuario
        await loadUserRatings(result.userId);
        await loadUserBasedRecommendations(result.userId);
        await loadItemBasedRecommendations(result.userId);
        
        alert(`Usuario creado exitosamente con ID: ${result.userId}`);
    } catch (error) {
        console.error('Error creando usuario:', error);
        alert('Error al crear usuario');
    }
});
*/

// Eventos para calificar películas
document.querySelectorAll('.rating-btn').forEach(btn => {
    btn.addEventListener('click', (e) => {
        // Reiniciar botones
        document.querySelectorAll('.rating-btn').forEach(b => {
            b.classList.remove('btn-warning');
            b.classList.add('btn-outline-warning');
        });
        
        // Activar botón seleccionado
        e.target.classList.remove('btn-outline-warning');
        e.target.classList.add('btn-warning');
        
        // Guardar rating
        document.getElementById('selectedRating').value = e.target.dataset.value;
    });
});

// Evento para enviar nueva calificación
document.getElementById('submitRatingBtn').addEventListener('click', async () => {
    if (!currentUserId) {
        alert('Por favor seleccione un usuario');
        return;
    }
    
    const movieId = document.getElementById('movieSelect').value;
    const rating = document.getElementById('selectedRating').value;
    
    if (!movieId) {
        alert('Por favor seleccione una película');
        return;
    }
    
    if (!rating) {
        alert('Por favor seleccione una calificación');
        return;
    }
    
    try {
        const response = await fetch(`/user/${currentUserId}/rate?movieId=${movieId}&rating=${rating}`, {
            method: 'POST'
        });
        
        await response.json();
        
        // Cerrar modal
        const modal = bootstrap.Modal.getInstance(document.getElementById('rateMovieModal'));
        modal.hide();
        
        // Limpiar selección
        document.getElementById('movieSelect').value = '';
        document.getElementById('selectedRating').value = '';
        document.querySelectorAll('.rating-btn').forEach(btn => {
            btn.classList.remove('btn-warning');
            btn.classList.add('btn-outline-warning');
        });
        
        // Recargar datos del usuario
        await loadUserRatings(currentUserId);
        await loadUserBasedRecommendations(currentUserId);
        await loadItemBasedRecommendations(currentUserId);
        
        alert('Calificación guardada exitosamente');
    } catch (error) {
        console.error('Error guardando calificación:', error);
        alert('Error al guardar la calificación');
    }
});


// Inicializar la aplicación
window.addEventListener('DOMContentLoaded', async () => {
    await loadUsers();
    await loadPopularMovies();
    await loadAllMovies();
});