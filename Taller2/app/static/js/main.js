// static/js/main.js
document.addEventListener('DOMContentLoaded', function() {
    // Inicializar mapa
    const map = L.map('map').setView([40.7128, -74.0060], 13);
    L.tileLayer('https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png', {
        attribution: '&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
    }).addTo(map);
    
    // Variables globales
    let markers = [];
    let currentUserId = null;
    let currentLocation = null;
    
    // Funciones auxiliares
    function showLoading(selector) {
        document.querySelector(selector).classList.remove('d-none');
    }
    
    function hideLoading(selector) {
        document.querySelector(selector).classList.add('d-none');
    }
    
    function clearMarkers() {
        markers.forEach(marker => map.removeLayer(marker));
        markers = [];
    }
    
    function addMarker(lat, lng, title, rating, isUserLocation = false) {
        const icon = isUserLocation 
            ? L.divIcon({
                className: 'user-location-marker',
                html: '<div class="marker-icon user-marker"><i class="bi bi-person-fill"></i></div>',
                iconSize: [30, 30]
              })
            : L.divIcon({
                className: 'business-marker',
                html: `<div class="marker-icon" style="background-color: ${getRatingColor(rating)};">${rating.toFixed(1)}</div>`,
                iconSize: [30, 30]
              });
        
        const marker = L.marker([lat, lng], { icon }).addTo(map);
        marker.bindPopup(`<strong>${title}</strong>${isUserLocation ? '' : `<br>Rating: ${rating.toFixed(1)}`}`);
        markers.push(marker);
        return marker;
    }
    
    function getRatingColor(rating) {
        if (rating >= 4.5) return '#28a745'; // Verde
        if (rating >= 4) return '#5cb85c';
        if (rating >= 3.5) return '#ffc107'; // Amarillo
        if (rating >= 3) return '#fd7e14'; // Naranja
        return '#dc3545'; // Rojo
    }
    
    // Cargar usuarios
    async function loadUsers() {
        try {
            const response = await fetch('/api/users');
            const users = await response.json();
            
            const userSelect = document.getElementById('user-select');
            userSelect.innerHTML = '';
            
            users.forEach(userId => {
                const option = document.createElement('option');
                option.value = userId;
                option.textContent = userId;
                userSelect.appendChild(option);
            });
            
            // Seleccionar primer usuario por defecto
            if (users.length > 0) {
                userSelect.value = users[0];
                currentUserId = users[0];
            }
        } catch (error) {
            console.error('Error al cargar usuarios:', error);
            alert('Error al cargar la lista de usuarios');
        }
    }
    
    // Cargar estadísticas
    async function loadStats() {
        try {
            const response = await fetch('/api/stats');
            const stats = await response.json();
            
            // Actualizar estadísticas
            document.getElementById('stat-rmse').textContent = stats.evaluation.rmse.toFixed(3);
            document.getElementById('stat-mae').textContent = stats.evaluation.mae.toFixed(3);
            document.getElementById('stat-f1').textContent = typeof stats.evaluation.f1 === 'number' 
                ? stats.evaluation.f1.toFixed(3) 
                : stats.evaluation.f1;
            
            // Actualizar pesos del modelo
            const weights = stats.model.weights;
            document.getElementById('weight-collaborative').style.width = `${weights.collaborative * 100}%`;
            document.getElementById('weight-collaborative').textContent = `Colaborativo: ${weights.collaborative * 100}%`;
            
            document.getElementById('weight-content').style.width = `${weights.content * 100}%`;
            document.getElementById('weight-content').textContent = `Contenido: ${weights.content * 100}%`;
            
            document.getElementById('weight-context').style.width = `${weights.context * 100}%`;
            document.getElementById('weight-context').textContent = `Contexto: ${weights.context * 100}%`;
            
        } catch (error) {
            console.error('Error al cargar estadísticas:', error);
        }
    }
    
    // Obtener recomendaciones
    async function getRecommendations() {
        if (!currentUserId) {
            alert('Por favor seleccione un usuario');
            return;
        }
        
        showLoading('#recommendations-loading');
        clearMarkers();
        
        try {
            const requestData = {
                user_id: currentUserId,
                num_recommendations: 10
            };
            
            if (currentLocation) {
                requestData.location = currentLocation;
                
                // Añadir marcador de ubicación del usuario
                addMarker(
                    currentLocation.latitude, 
                    currentLocation.longitude, 
                    'Su ubicación', 
                    0, 
                    true
                );
            }
            
            const response = await fetch('/api/recommend', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify(requestData)
            });
            
            const recommendations = await response.json();
            
            // Actualizar lista de recomendaciones
            const container = document.getElementById('recommendations-container');
            container.innerHTML = '';
            
            if (recommendations.length === 0) {
                container.innerHTML = '<p class="text-center">No se encontraron recomendaciones</p>';
                return;
            }
            
            const listGroup = document.createElement('div');
            listGroup.className = 'list-group';
            console.log (recommendations)
            recommendations.forEach(business => {
                const item = document.createElement('a');
                item.href = '#';
                item.className = 'list-group-item list-group-item-action';
                item.dataset.businessId = business.business_id;
                
                item.innerHTML = `
                    <div class="d-flex w-100 justify-content-between">
                        <h5 class="mb-1">${business.name}</h5>
                        <div>
                            <span class="badge bg-primary rounded-pill">${business.predicted_rating.toFixed(1)}</span>
                        </div>
                    </div>
                    <p class="mb-1">${business.categories || 'Sin categorías'}</p>
                `;
                
                // Evento para mostrar explicación
                item.addEventListener('click', (e) => {
                    e.preventDefault();
                    getExplanation(business.business_id);
                    
                    // Resaltar elemento seleccionado
                    document.querySelectorAll('.list-group-item').forEach(el => {
                        el.classList.remove('active');
                    });
                    item.classList.add('active');
                });
                
                listGroup.appendChild(item);
                
                // Añadir marcador al mapa
                const marker = addMarker(
                    business.latitude, 
                    business.longitude, 
                    business.name, 
                    business.predicted_rating
                );
                
                // Enlazar marcador con elemento de lista
                marker.on('click', () => {
                    item.click();
                    marker.openPopup();
                });
            });
            
            container.appendChild(listGroup);
            
            // Ajustar vista del mapa
            if (recommendations.length > 0) {
                const bounds = L.latLngBounds(recommendations.map(b => [b.latitude, b.longitude]));
                if (currentLocation) {
                    bounds.extend([currentLocation.latitude, currentLocation.longitude]);
                }
                map.fitBounds(bounds);
            }
            
        } catch (error) {
            console.error('Error al obtener recomendaciones:', error);
            document.getElementById('recommendations-container').innerHTML = 
                '<p class="text-center text-danger">Error al obtener recomendaciones</p>';
        } finally {
            hideLoading('#recommendations-loading');
        }
    }
    
    // Obtener explicación
    async function getExplanation(businessId) {
        if (!currentUserId || !businessId) return;
        
        const container = document.getElementById('explanation-container');
        container.innerHTML = '<p class="text-center">Cargando explicación...</p>';
        
        try {
            const response = await fetch('/api/explain', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json'
                },
                body: JSON.stringify({
                    user_id: currentUserId,
                    business_id: businessId
                })
            });
            
            const data = await response.json();
            
            // Mostrar explicación
            container.innerHTML = `
                <div class="explanation-card">
                    <h4>${data.business.name}</h4>
                    
                    <div class="card mb-3">
                        <div class="card-header">
                            Filtrado Colaborativo
                        </div>
                        <div class="card-body">
                            ${renderCollaborativeExplanation(data.explanation.collaborative)}
                        </div>
                    </div>
                    
                    <div class="card mb-3">
                        <div class="card-header">
                            Basado en Contenido
                        </div>
                        <div class="card-body">
                            ${renderContentExplanation(data.explanation.content)}
                        </div>
                    </div>
                    
                    <div class="card">
                        <div class="card-header">
                            Basado en Contexto
                        </div>
                        <div class="card-body">
                            ${renderContextExplanation(data.explanation.context)}
                        </div>
                    </div>
                </div>
            `;
            
        } catch (error) {
            console.error('Error al obtener explicación:', error);
            container.innerHTML = '<p class="text-center text-danger">Error al cargar la explicación</p>';
        }
    }
    
    function renderCollaborativeExplanation(data) {
        if (typeof data === 'string') {
            return `<p>${data}</p>`;
        }
        
        if (data.similar_users && data.similar_users.length > 0) {
            const usersList = data.similar_users.map(user => 
                `<li>Usuario similar calificó con ${user.rating.toFixed(1)} estrellas (similitud: ${user.similarity.toFixed(2)})</li>`
            ).join('');
            
            return `
                <p>Esta recomendación se basa en usuarios con gustos similares:</p>
                <ul>${usersList}</ul>
            `;
        }
        
        return '<p>No hay suficientes datos para generar una explicación colaborativa.</p>';
    }
    
    function renderContentExplanation(data) {
        if (typeof data === 'string') {
            return `<p>${data}</p>`;
        }
        
        if (data.similar_businesses && data.similar_businesses.length > 0) {
            const businessList = data.similar_businesses.map(business => 
                `<li>${business.name} (similitud: ${business.similarity.toFixed(2)})</li>`
            ).join('');
            
            return `
                <p>Negocios similares que podrían gustarte:</p>
                <ul>${businessList}</ul>
            `;
        }
        
        return '<p>No hay suficientes datos para generar una explicación basada en contenido.</p>';
    }
    
    function renderContextExplanation(data) {
        if (typeof data === 'string') {
            return `<p>${data}</p>`;
        }
        
        return `
            <p>Factor de proximidad: ${data.distance_factor.toFixed(2)}</p>
            <p class="mb-0 text-muted">Un valor más alto indica mayor cercanía a tu ubicación actual.</p>
        `;
    }
    
    // Eventos
    document.getElementById('user-select').addEventListener('change', function() {
        currentUserId = this.value;
    });
    
    document.getElementById('get-location').addEventListener('click', function() {
        if (navigator.geolocation) {
            navigator.geolocation.getCurrentPosition(
                function(position) {
                    const lat = position.coords.latitude;
                    const lng = position.coords.longitude;
                    
                    document.getElementById('latitude').value = lat;
                    document.getElementById('longitude').value = lng;
                    
                    currentLocation = {
                        latitude: lat,
                        longitude: lng
                    };
                    
                    // Actualizar mapa
                    map.setView([lat, lng], 13);
                    
                },
                function(error) {
                    console.error('Error obteniendo ubicación:', error);
                    alert('No se pudo obtener la ubicación. Por favor, introdúzcala manualmente.');
                }
            );
        } else {
            alert('Tu navegador no soporta geolocalización.');
        }
    });
    
    document.getElementById('latitude').addEventListener('change', updateLocation);
    document.getElementById('longitude').addEventListener('change', updateLocation);
    
    function updateLocation() {
        const lat = parseFloat(document.getElementById('latitude').value);
        const lng = parseFloat(document.getElementById('longitude').value);
        
        if (!isNaN(lat) && !isNaN(lng)) {
            currentLocation = {
                latitude: lat,
                longitude: lng
            };
        } else {
            currentLocation = null;
        }
    }
    
    document.getElementById('get-recommendations').addEventListener('click', getRecommendations);
    
    // Inicialización
    loadUsers();
    loadStats();
});