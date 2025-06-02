import pandas as pd
import numpy as np
import torch
import os
from typing import Dict, List, Tuple, Union
from models.data_processor import DataProcessor
from transformers import BertTokenizer
from models.enhancedhybridrecommender import EnhancedHybridRecommender
import pickle

class RecommendationModel:
    def __init__(self, data_processor: DataProcessor):
        """
        Inicializa el modelo de recomendación cargando el modelo pre-entrenado
        
        Args:
            data_processor: Instancia del procesador de datos
        """
        self.data_processor = data_processor
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model_path = os.path.join("data", "bert_gat_with_graphsage_finetuned.pt")
        
        # Inicializar tokenizer BERT
        self.tokenizer = BertTokenizer.from_pretrained('bert-base-uncased')
        
        # Preparar datos necesarios para hacer recomendaciones
        self._prepare_data()
        
        # Cargar el modelo pre-entrenado
        self.model = self._load_model()
        
        # Pre-computar títulos tokenizados para optimización
        self._precompute_movie_tokens()
    
    def _prepare_data(self):
        """Prepara los datos necesarios para las recomendaciones"""
        ratings_df = self.data_processor.ratings_df
        movies_df = self.data_processor.movies_df
        
        # Crear la matriz usuario-película
        user_movie_matrix = ratings_df.pivot(
            index='userId',
            columns='movieId',
            values='rating'
        ).fillna(0)
        
        # Guardar IDs de usuarios y películas
        self.user_ids = user_movie_matrix.index.tolist()
        self.movie_ids = user_movie_matrix.columns.tolist()
        
        # Crear mapeos para acceso rápido
        self.user_id_to_idx = {uid: idx for idx, uid in enumerate(self.user_ids)}
        self.movie_id_to_idx = {mid: idx for idx, mid in enumerate(self.movie_ids)}
        
        # Crear mappings necesarios para el modelo
        self.user_mapping = self.user_id_to_idx
        self.item_mapping = self.movie_id_to_idx
        
        # Guardar referencias a los DataFrames
        self.user_movie_matrix = user_movie_matrix
        self.ratings_df = ratings_df
        self.movies_df = movies_df

    def _precompute_movie_tokens(self):
        """Pre-computa los tokens BERT para todas las películas para optimizar velocidad"""
        print("Pre-computando tokens de películas...")
        self.movie_tokens = {}
        
        # Crear un diccionario de movieId -> título para acceso rápido
        movie_titles = {}
        for _, row in self.movies_df.iterrows():
            movie_titles[row['movieId']] = row['title']
        
        # Tokenizar todos los títulos de una vez
        all_titles = []
        all_movie_ids = []
        
        for movie_id in self.movie_ids:
            if movie_id in movie_titles:
                all_titles.append(movie_titles[movie_id])
                all_movie_ids.append(movie_id)
            else:
                all_titles.append("Unknown Movie")
                all_movie_ids.append(movie_id)
        
        # Tokenizar en lotes para mayor eficiencia
        batch_size = 100
        for i in range(0, len(all_titles), batch_size):
            batch_titles = all_titles[i:i+batch_size]
            batch_movie_ids = all_movie_ids[i:i+batch_size]
            
            try:
                batch_tokens = self.tokenizer(
                    batch_titles,
                    return_tensors='pt',
                    padding='max_length',
                    truncation=True,
                    max_length=32
                )
                
                # Guardar los tokens para cada película
                for j, movie_id in enumerate(batch_movie_ids):
                    self.movie_tokens[movie_id] = {
                        'input_ids': batch_tokens['input_ids'][j].unsqueeze(0),
                        'attention_mask': batch_tokens['attention_mask'][j].unsqueeze(0)
                    }
            except Exception as e:
                print(f"Error tokenizando lote {i//batch_size}: {e}")
                # Fallback: tokenizar individualmente
                for j, (title, movie_id) in enumerate(zip(batch_titles, batch_movie_ids)):
                    try:
                        tokens = self.tokenizer(
                            title,
                            return_tensors='pt',
                            padding='max_length',
                            truncation=True,
                            max_length=32
                        )
                        self.movie_tokens[movie_id] = {
                            'input_ids': tokens['input_ids'],
                            'attention_mask': tokens['attention_mask']
                        }
                    except:
                        # Último fallback: token vacío
                        self.movie_tokens[movie_id] = {
                            'input_ids': torch.zeros((1, 32), dtype=torch.long),
                            'attention_mask': torch.zeros((1, 32), dtype=torch.long)
                        }
        
        print(f"Pre-computados tokens para {len(self.movie_tokens)} películas")

    def _load_model(self):
        """Carga el modelo pre-entrenado desde el archivo"""
        try:
            print(f"Cargando modelo desde {self.model_path}")

            num_users = len(self.user_ids)
            print('num_users: ', num_users)

            num_items = len(self.movie_ids)
            print('num_items: ', num_items)

            model = EnhancedHybridRecommender(
                num_users=num_users,
                num_items=num_items,
                bert_model_name='bert-base-uncased',
                embedding_dim=128,
                use_gat=True
            ).to(self.device)
            
            model.load_state_dict(torch.load(self.model_path, map_location=self.device))
            model.eval()
            return model    
        except Exception as e:
            print(f"Error al cargar el modelo pre-entrenado: {str(e)}")
            print("Creando modelo con parámetros por defecto...")
            
            # Fallback: crear modelo con parámetros por defecto
            try:
                num_users = len(self.user_ids)
                num_items = len(self.movie_ids)
                
                model = EnhancedHybridRecommender(
                    num_users=num_users,
                    num_items=num_items,
                    embedding_dim=128,
                    num_heads=4
                )
                model.to(self.device)
                model.eval()
                
                print("Modelo creado con parámetros por defecto como fallback")
                return model
                
            except Exception as fallback_error:
                raise RuntimeError(f"Error crítico al cargar/crear el modelo: {str(e)}. Error de fallback: {str(fallback_error)}")

    def recommend_movies_batch(self, user_id, top_k=10, total_movies=1000):
        """
        Función de recomendación optimizada que utiliza procesamiento por lotes
        
        Args:
            user_id: ID del usuario
            top_k: Número de recomendaciones a devolver
            total_movies: Número máximo de películas candidatas a evaluar
            
        Returns:
            Lista de diccionarios con recomendaciones
        """
        self.model.eval()

        try:
            user_id_int = int(user_id)
        except ValueError:
            print(f"Error: user_id '{user_id}' no es un número válido")
            return []
    
        # Verificar si el usuario existe
        if user_id_int not in self.user_mapping:
            print(f"Usuario {user_id_int} no encontrado en el dataset")
            return self._get_popular_movies_fallback(top_k)
                
        user_idx = self.user_mapping[user_id_int]
        print(f"Generando recomendaciones para usuario {user_id_int} (idx: {user_idx})")

        # Obtener películas vistas por el usuario correcto
        seen_movies = set(self.ratings_df[self.ratings_df['userId'] == user_id_int]['movieId'].tolist())
        print(f"Usuario {user_id_int} ha visto {len(seen_movies)} películas")
        
        # FIX CRÍTICO: Aplicar diversidad en la selección de candidatos
        # En lugar de tomar siempre las primeras 500 películas, seleccionar una muestra diversa
        candidate_movie_ids = [mid for mid in self.movie_ids if mid not in seen_movies]
        
        # Mezclar aleatoriamente los candidatos para generar diversidad
        np.random.seed(user_id_int)  # Usar el user_id como semilla para reproducibilidad
        np.random.shuffle(candidate_movie_ids)
        
        # Limitar número de candidatos por eficiencia
        candidate_movie_ids = candidate_movie_ids[:total_movies]
        
        if not candidate_movie_ids:
            print("No hay películas candidatas para recomendar")
            return self._get_popular_movies_fallback(top_k)

        # Procesar en lotes para mayor eficiencia
        batch_size = 64
        predictions = []
        
        print(f"Procesando {len(candidate_movie_ids)} películas candidatas en lotes de {batch_size}")
        
        for i in range(0, len(candidate_movie_ids), batch_size):
            batch_movie_ids = candidate_movie_ids[i:i+batch_size]
            
            # Preparar tensores del lote
            batch_user_ids = []
            batch_item_ids = []
            batch_input_ids = []
            batch_attention_masks = []
            
            valid_indices = []
            
            for j, mid in enumerate(batch_movie_ids):
                if mid not in self.item_mapping or mid not in self.movie_tokens:
                    continue
                    
                item_idx = self.item_mapping[mid]
                
                # Usar el user_idx correcto para cada predicción
                batch_user_ids.append(user_idx)
                batch_item_ids.append(item_idx)
                
                # Usar tokens pre-computados
                tokens = self.movie_tokens[mid]
                batch_input_ids.append(tokens['input_ids'].squeeze(0))
                batch_attention_masks.append(tokens['attention_mask'].squeeze(0))
                
                valid_indices.append((j, mid))
            
            if not batch_user_ids:
                continue
            
            # Convertir a tensores
            try:
                user_tensor = torch.tensor(batch_user_ids, device=self.device)
                item_tensor = torch.tensor(batch_item_ids, device=self.device)
                input_ids_tensor = torch.stack(batch_input_ids).to(self.device)
                attention_mask_tensor = torch.stack(batch_attention_masks).to(self.device)
                
                # Realizar predicción del lote
                with torch.no_grad():
                    batch_predictions = self.model(
                        user_tensor, 
                        item_tensor, 
                        input_ids_tensor, 
                        attention_mask_tensor
                    )
                    
                    # Procesar resultados del lote
                    for k, (original_idx, mid) in enumerate(valid_indices):
                        rating_score = batch_predictions[k].item()
                        rating_score = max(0.0, min(5.0, rating_score))
                        predictions.append((mid, rating_score))
                        
            except Exception as e:
                print(f"Error procesando lote {i//batch_size}: {e}")
                # Fallback: procesar individualmente
                for j, mid in enumerate(batch_movie_ids):
                    try:
                        if mid not in self.item_mapping or mid not in self.movie_tokens:
                            continue
                            
                        item_idx = self.item_mapping[mid]
                        tokens = self.movie_tokens[mid]
                        
                        user_tensor = torch.tensor([user_idx], device=self.device)
                        item_tensor = torch.tensor([item_idx], device=self.device)
                        input_ids = tokens['input_ids'].to(self.device)
                        attention_mask = tokens['attention_mask'].to(self.device)
                        
                        with torch.no_grad():
                            rating_pred = self.model(user_tensor, item_tensor, input_ids, attention_mask)
                            rating_score = rating_pred.item()
                            rating_score = max(0.0, min(5.0, rating_score))
                            predictions.append((mid, rating_score))
                            
                    except Exception as individual_error:
                        print(f"Error procesando película individual {mid}: {individual_error}")
                        continue

        if not predictions:
            print("No se pudieron generar predicciones")
            return self._get_popular_movies_fallback(top_k)

        # Ordenar por calificación descendente y tomar los top_k
        top_preds = sorted(predictions, key=lambda x: x[1], reverse=True)[:top_k]
        
        # Logging para verificar las predicciones
        print(f"Top {len(top_preds)} predicciones para usuario {user_id_int}:")
        for i, (mid, score) in enumerate(top_preds[:5]):
            movie_title = self.movies_df[self.movies_df['movieId'] == mid]['title'].iloc[0] if len(self.movies_df[self.movies_df['movieId'] == mid]) > 0 else "Desconocida"
            print(f"  {i+1}. Movie {mid} ({movie_title}): {score:.3f}")

        # Construir la lista de recomendaciones con metadatos
        recommendations = []
        for mid, score in top_preds:
            try:
                movie_data = self.movies_df[self.movies_df['movieId'] == mid].iloc[0]
                recommendations.append({
                    'movieId': mid,
                    'title': movie_data['title'],
                    'genres': movie_data['genres'],
                    'predicted_rating': round(score, 3)
                })
            except Exception as e:
                print(f"Error al obtener datos de película {mid}: {e}")
                continue

        print(f"Generadas {len(recommendations)} recomendaciones para usuario {user_id_int}")
        return recommendations

    def recommend_movies_enhanced(self, user_id, top_k=10, total_movies=1000, use_collaborative_filtering=True):
        """
        Versión mejorada de recomendación que considera el perfil del usuario
        
        Args:
            user_id: ID del usuario
            top_k: Número de recomendaciones a devolver
            total_movies: Número máximo de películas candidatas a evaluar
            use_collaborative_filtering: Si usar filtrado colaborativo para preseleccionar candidatos
            
        Returns:
            Lista de diccionarios con recomendaciones
        """
        self.model.eval()

        try:
            user_id_int = int(user_id)
        except ValueError:
            print(f"Error: user_id '{user_id}' no es un número válido")
            return []
    
        if user_id_int not in self.user_mapping:
            print(f"Usuario {user_id_int} no encontrado en el dataset")
            return self._get_popular_movies_fallback(top_k)
                
        user_idx = self.user_mapping[user_id_int]
        print(f"Generando recomendaciones mejoradas para usuario {user_id_int} (idx: {user_idx})")

        # Obtener películas vistas y el perfil del usuario
        user_ratings = self.ratings_df[self.ratings_df['userId'] == user_id_int]
        seen_movies = set(user_ratings['movieId'].tolist())
        
        # Analizar géneros preferidos del usuario
        user_genres = self._get_user_preferred_genres(user_id_int)
        print(f"Géneros preferidos del usuario: {user_genres[:3]}")
        
        # Candidatos iniciales (todas las películas no vistas)
        all_candidate_ids = [mid for mid in self.movie_ids if mid not in seen_movies]
        
        # Estrategia de selección inteligente de candidatos
        if use_collaborative_filtering and len(all_candidate_ids) > total_movies:
            candidate_movie_ids = self._select_smart_candidates(
                user_id_int, all_candidate_ids, user_genres, total_movies
            )
        else:
            # Usar diversidad aleatoria basada en el usuario
            np.random.seed(user_id_int)
            np.random.shuffle(all_candidate_ids)
            candidate_movie_ids = all_candidate_ids[:total_movies]
        
        if not candidate_movie_ids:
            print("No hay películas candidatas para recomendar")
            return self._get_popular_movies_fallback(top_k)

        print(f"Seleccionados {len(candidate_movie_ids)} candidatos inteligentes de {len(all_candidate_ids)} posibles")

        # Procesar predicciones por lotes
        predictions = self._process_predictions_batch(user_idx, candidate_movie_ids)

        if not predictions:
            print("No se pudieron generar predicciones")
            return self._get_popular_movies_fallback(top_k)

        # Ordenar y seleccionar top recomendaciones
        top_preds = sorted(predictions, key=lambda x: x[1], reverse=True)[:top_k]
        
        # Logging detallado
        print(f"Top {len(top_preds)} predicciones para usuario {user_id_int}:")
        for i, (mid, score) in enumerate(top_preds[:5]):
            movie_title = self.movies_df[self.movies_df['movieId'] == mid]['title'].iloc[0] if len(self.movies_df[self.movies_df['movieId'] == mid]) > 0 else "Desconocida"
            print(f"  {i+1}. Movie {mid} ({movie_title}): {score:.3f}")

        # Construir recomendaciones finales
        recommendations = []
        for mid, score in top_preds:
            try:
                movie_data = self.movies_df[self.movies_df['movieId'] == mid].iloc[0]
                recommendations.append({
                    'movieId': mid,
                    'title': movie_data['title'],
                    'genres': movie_data['genres'],
                    'predicted_rating': round(score, 3)
                })
            except Exception as e:
                print(f"Error al obtener datos de película {mid}: {e}")
                continue

        print(f"Generadas {len(recommendations)} recomendaciones mejoradas para usuario {user_id_int}")
        return recommendations

    def _get_user_preferred_genres(self, user_id):
        """Analiza los géneros preferidos del usuario basado en sus calificaciones altas"""
        user_ratings = self.ratings_df[self.ratings_df['userId'] == user_id]
        high_rated = user_ratings[user_ratings['rating'] >= 4.0]
        
        if high_rated.empty:
            return []
        
        # Obtener géneros de películas bien calificadas
        preferred_genres = {}
        for _, rating_row in high_rated.iterrows():
            movie_id = rating_row['movieId']
            movie_info = self.movies_df[self.movies_df['movieId'] == movie_id]
            if not movie_info.empty:
                genres = movie_info.iloc[0]['genres'].split('|')
                for genre in genres:
                    if genre not in preferred_genres:
                        preferred_genres[genre] = 0
                    preferred_genres[genre] += rating_row['rating']
        
        # Ordenar géneros por preferencia
        sorted_genres = sorted(preferred_genres.items(), key=lambda x: x[1], reverse=True)
        return [genre for genre, _ in sorted_genres]

    def _select_smart_candidates(self, user_id, all_candidates, user_genres, total_movies):
        """Selecciona candidatos inteligentemente basado en el perfil del usuario"""
        # Dividir candidatos en categorías
        genre_candidates = []
        popular_candidates = []
        random_candidates = []
        
        # Obtener estadísticas de popularidad
        movie_popularity = self.ratings_df.groupby('movieId')['rating'].agg(['count', 'mean']).reset_index()
        popular_movie_ids = set(movie_popularity[movie_popularity['count'] >= 10]['movieId'].tolist())
        
        for mid in all_candidates:
            movie_info = self.movies_df[self.movies_df['movieId'] == mid]
            if movie_info.empty:
                continue
                
            movie_genres = movie_info.iloc[0]['genres'].split('|')
            
            # Categorizar película
            if any(genre in user_genres[:3] for genre in movie_genres):
                genre_candidates.append(mid)
            elif mid in popular_movie_ids:
                popular_candidates.append(mid)
            else:
                random_candidates.append(mid)
        
        # Selección balanceada
        selected = []
        
        # 50% de géneros preferidos
        np.random.seed(user_id)
        np.random.shuffle(genre_candidates)
        selected.extend(genre_candidates[:int(total_movies * 0.5)])
        
        # 30% populares
        np.random.shuffle(popular_candidates)
        selected.extend(popular_candidates[:int(total_movies * 0.3)])
        
        # 20% aleatorio para diversidad
        np.random.shuffle(random_candidates)
        remaining = total_movies - len(selected)
        selected.extend(random_candidates[:remaining])
        
        # Si no hay suficientes, completar con lo que sea
        if len(selected) < total_movies:
            remaining_candidates = [mid for mid in all_candidates if mid not in selected]
            np.random.shuffle(remaining_candidates)
            selected.extend(remaining_candidates[:total_movies - len(selected)])
        
        return selected[:total_movies]

    def _process_predictions_batch(self, user_idx, candidate_movie_ids):
        """Procesa las predicciones por lotes de manera eficiente"""
        batch_size = 64
        predictions = []
        
        for i in range(0, len(candidate_movie_ids), batch_size):
            batch_movie_ids = candidate_movie_ids[i:i+batch_size]
            
            batch_user_ids = []
            batch_item_ids = []
            batch_input_ids = []
            batch_attention_masks = []
            valid_indices = []
            
            for j, mid in enumerate(batch_movie_ids):
                if mid not in self.item_mapping or mid not in self.movie_tokens:
                    continue
                    
                item_idx = self.item_mapping[mid]
                batch_user_ids.append(user_idx)
                batch_item_ids.append(item_idx)
                
                tokens = self.movie_tokens[mid]
                batch_input_ids.append(tokens['input_ids'].squeeze(0))
                batch_attention_masks.append(tokens['attention_mask'].squeeze(0))
                valid_indices.append((j, mid))
            
            if not batch_user_ids:
                continue
            
            try:
                user_tensor = torch.tensor(batch_user_ids, device=self.device)
                item_tensor = torch.tensor(batch_item_ids, device=self.device)
                input_ids_tensor = torch.stack(batch_input_ids).to(self.device)
                attention_mask_tensor = torch.stack(batch_attention_masks).to(self.device)
                
                with torch.no_grad():
                    batch_predictions = self.model(
                        user_tensor, item_tensor, input_ids_tensor, attention_mask_tensor
                    )
                    
                    for k, (original_idx, mid) in enumerate(valid_indices):
                        rating_score = max(0.0, min(5.0, batch_predictions[k].item()))
                        predictions.append((mid, rating_score))
                        
            except Exception as e:
                print(f"Error procesando lote: {e}")
                continue
        
        return predictions

    def _get_popular_movies_fallback(self, top_k):
        """Función auxiliar para devolver películas populares cuando no se puede generar recomendaciones personalizadas"""
        try:
            print("Devolviendo películas populares como fallback")
            popular_movies = self.data_processor.ratings_df.groupby('movieId')['rating'].agg(['mean', 'count']).reset_index()
            popular_movies = popular_movies[popular_movies['count'] >= 50]
            popular_movies = popular_movies.sort_values('mean', ascending=False)
            
            recommendations = []
            for _, row in popular_movies.head(top_k).iterrows():
                mid = row['movieId']
                try:
                    movie_data = self.movies_df[self.movies_df['movieId'] == mid].iloc[0]
                    recommendations.append({
                        'movieId': mid,
                        'title': movie_data['title'],
                        'genres': movie_data['genres'],
                        'predicted_rating': round(row['mean'], 3)
                    })
                except:
                    continue
            
            return recommendations
        except Exception as e:
            print(f"Error en fallback de películas populares: {e}")
            return []

    def recommend_movies(self, user_id, top_k=10, total_movies=1000):
        """
        Función principal de recomendación - usa la versión mejorada
        """
        return self.recommend_movies_enhanced(user_id, top_k, total_movies)

    def get_recommendations(self, user_id: str, user_ratings: Dict[str, float] = None, 
                           top_k: int = 10, return_scores: bool = False) -> Union[List[str], Tuple[List[str], Dict[str, float]]]:
        """
        Obtiene recomendaciones para un usuario usando el modelo híbrido optimizado
        
        Args:
            user_id: ID del usuario
            user_ratings: Diccionario de calificaciones para usuario nuevo (no usado en esta versión)
            top_k: Número de recomendaciones a devolver
            return_scores: Si es True, devuelve también las puntuaciones
            
        Returns:
            Lista de IDs de películas recomendadas y opcionalmente un diccionario de puntuaciones
        """
        try:
            print(f"Generando recomendaciones para usuario: {user_id}")
            
            # Usar la función recommend_movies optimizada
            recommendations = self.recommend_movies(user_id, top_k=top_k)
            
            if not recommendations:
                print("No se pudieron generar recomendaciones")
                return [] if not return_scores else ([], {})
            
            # Extraer IDs de películas
            top_movie_ids = [str(rec['movieId']) for rec in recommendations]
            
            if return_scores:
                scores = {str(rec['movieId']): rec['predicted_rating'] for rec in recommendations}
                return top_movie_ids, scores
            else:
                return top_movie_ids
                
        except Exception as e:
            print(f"Error al generar recomendaciones: {str(e)}")
            
            # Fallback: devolver películas populares
            try:
                popular_movies = self.data_processor.ratings_df.groupby('movieId')['rating'].mean().sort_values(ascending=False)
                fallback_movies = [str(mid) for mid in popular_movies.index[:top_k]]
                
                if return_scores:
                    fallback_scores = {mid: 4.0 for mid in fallback_movies}
                    return fallback_movies, fallback_scores
                else:
                    return fallback_movies
            except:
                return [] if not return_scores else ([], {})