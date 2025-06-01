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
        # with open(os.path.join("data", "user_mapping.pkl"), 'rb') as f:
        #     self.user_mapping = pickle.load(f)
        
        # with open(os.path.join("data", "item_mapping.pkl"), 'rb') as f:
        #     self.item_mapping = pickle.load(f)

        self.item_mapping = self.movie_id_to_idx
        
        # Guardar referencias a los DataFrames
        self.user_movie_matrix = user_movie_matrix
        self.ratings_df = ratings_df
        self.movies_df = movies_df

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
            #model_data = torch.load(self.model_path, map_location=self.device)

            print(f"Modelo cargado exitosamente. Tipo: {type(model)}")
            
            # # Determinar dimensiones necesarias para recrear el modelo
            # num_users = len(self.user_ids)
            # print('num_users: ', num_users)

            # num_items = len(self.movie_ids)
            # print('num_items: ', num_items)
            
            # # Si el modelo cargado es un state_dict, necesitamos recrear el modelo
            # if isinstance(model_data, dict) and 'state_dict' in model_data:
            #     print("Modelo cargado como state_dict - recreando modelo...")
                
            #     # Extraer el state_dict
            #     state_dict = model_data['state_dict']
                
            #     # Detectar parámetros del modelo desde el state_dict
            #     embedding_dim = 64  # valor por defecto
            #     use_gat = True  # valor por defecto
            #     num_heads = 4  # valor por defecto
                
            #     # Intentar detectar embedding_dim desde el state_dict
            #     if 'user_embedding.weight' in state_dict:
            #         embedding_dim = state_dict['user_embedding.weight'].shape[1]
            #         print(f"Detectado embedding_dim: {embedding_dim}")
                
            #     # Detectar si usa GAT
            #     gat_keys = [k for k in state_dict.keys() if 'gat' in k.lower()]
            #     use_gat = len(gat_keys) > 0
            #     print(f"Detectado use_gat: {use_gat}")
                
            #     # Detectar número de heads si usa GAT
            #     if use_gat and 'gat.lin_l.weight' in state_dict:
            #         gat_out_dim = state_dict['gat.lin_l.weight'].shape[0]
            #         num_heads = embedding_dim // gat_out_dim if gat_out_dim > 0 else 4
            #         print(f"Detectado num_heads: {num_heads}")
                
            #     # Recrear el modelo con los parámetros detectados
            #     model = EnhancedHybridRecommender(
            #         num_users=610,
            #         num_items=9724,
            #         bert_model_name='bert-base-uncased',
            #         embedding_dim=embedding_dim,
            #         num_heads=num_heads,
            #         use_gat=use_gat
            #     )
                
            #     # Cargar el state_dict
            #     model.load_state_dict(state_dict)
            #     model.to(self.device)
            #     model.eval()
                
            #     print("Modelo recreado y cargado exitosamente")
            #     return model
                
            # elif isinstance(model_data, dict) and any(key.startswith('user_embedding') or key.startswith('item_embedding') for key in model_data.keys()):
            #     print("Modelo cargado como state_dict directo - recreando modelo...")
                
            #     # Es un state_dict directo (sin la clave 'state_dict')
            #     state_dict = model_data
                
            #     # Detectar parámetros del modelo
            #     embedding_dim = num_users
            #     use_gat = True
            #     num_heads = 4
                
            #     if 'user_embedding.weight' in state_dict:
            #         embedding_dim = state_dict['user_embedding.weight'].shape[1]
            #         print(f"Detectado embedding_dim: {embedding_dim}")
                
            #     gat_keys = [k for k in state_dict.keys() if 'gat' in k.lower()]
            #     use_gat = len(gat_keys) > 0
            #     print(f"Detectado use_gat: {use_gat}")
                
            #     if use_gat and 'gat.lin_l.weight' in state_dict:
            #         gat_out_dim = state_dict['gat.lin_l.weight'].shape[0]
            #         num_heads = embedding_dim // gat_out_dim if gat_out_dim > 0 else 4
            #         print(f"Detectado num_heads: {num_heads}")
                
            #     # Recrear el modelo
            #     model = EnhancedHybridRecommender(
            #         num_users=num_users,
            #         num_items=num_items,
            #         bert_model_name='bert-base-uncased',
            #         embedding_dim=embedding_dim,
            #         num_heads=num_heads,
            #         use_gat=use_gat
            #     )
                
            #     # Cargar el state_dict
            #     model.load_state_dict(state_dict)
            #     model.to(self.device)
                # model.eval()
                
                # print("Modelo recreado y cargado exitosamente")
                # return model
                
            # elif isinstance(model_data, torch.nn.Module):
            #     print("Modelo cargado como módulo completo")
            #     model_data.to(self.device)
            #     model_data.eval()
            #     return model_data
                
            # else:
            #     print(f"Formato de modelo no reconocido: {type(model_data)}")
            #     print("Intentando crear modelo con parámetros por defecto...")
                
            #     # Crear modelo con parámetros por defecto
            #     model = EnhancedHybridRecommender(
            #         num_users=num_users,
            #         num_items=num_items,
            #         bert_model_name='bert-base-uncased',
            #         embedding_dim=64,
            #         num_heads=4,
            #         use_gat=True
            #     )
            #     model.to(self.device)
            #     model.eval()
                
            #     print("Modelo creado con parámetros por defecto")
            #     return model
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
                    embedding_dim=64,
                    num_heads=4
                )
                model.to(self.device)
                model.eval()
                
                print("Modelo creado con parámetros por defecto como fallback")
                return model
                
            except Exception as fallback_error:
                raise RuntimeError(f"Error crítico al cargar/crear el modelo: {str(e)}. Error de fallback: {str(fallback_error)}")
    
    def _get_user_vector(self, user_id: Union[str, int], user_ratings: Dict[str, float] = None) -> torch.Tensor:
        """
        Crea un vector de calificaciones para el usuario
        
        Args:
            user_id: ID del usuario o 'new' para usuario nuevo
            user_ratings: Diccionario de calificaciones para usuario nuevo
            
        Returns:
            Tensor con las calificaciones del usuario
        """
        # Inicializar vector de calificaciones con ceros
        user_vector = torch.zeros(len(self.movie_ids), dtype=torch.float32, device=self.device)
        
        # Caso 1: Usuario existente del dataset
        if isinstance(user_id, (str, int)) and str(user_id).isdigit() and int(user_id) in self.user_ids:
            user_idx = self.user_id_to_idx[int(user_id)]
            # Obtener calificaciones del usuario de la matriz
            for i, movie_id in enumerate(self.movie_ids):
                rating = self.user_movie_matrix.iloc[user_idx][movie_id]
                user_vector[i] = rating
        
        # Caso 2: Usuario nuevo con calificaciones proporcionadas
        elif user_ratings and len(user_ratings) > 0:
            # Llenar el vector con las calificaciones proporcionadas
            for movie_id_str, rating in user_ratings.items():
                if not str(movie_id_str).isdigit():
                    continue
                    
                movie_id = int(movie_id_str)
                if movie_id in self.movie_id_to_idx:
                    idx = self.movie_id_to_idx[movie_id]
                    user_vector[idx] = float(rating)
        
        # Si no se pudo construir un vector de calificaciones, usar películas populares
        if torch.sum(user_vector) == 0:
            print(f"No se encontraron calificaciones para el usuario {user_id}. Utilizando películas populares.")
            
            # Obtener las películas más populares basadas en el promedio de calificaciones
            popular_movies = self.data_processor.ratings_df.groupby('movieId')['rating'].mean().sort_values(ascending=False)
            
            # Asignar calificaciones "ficticias" a las 5 películas más populares
            for i, movie_id in enumerate(popular_movies.index[:5]):
                if movie_id in self.movie_id_to_idx:
                    idx = self.movie_id_to_idx[movie_id]
                    # Asignar calificación 5 a las películas más populares (como si al usuario le gustaran)
                    user_vector[idx] = 5.0
        
        return user_vector

    def recommend_movies(self, user_id, top_k=10, total_movies=500):
        """
        Función de recomendación que utiliza el modelo EnhancedHybridRecommender
        
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
            # Si no se puede convertir a int, lo dejamos tal cual para el fallback más adelante:
            user_id_int = user_id
    
        #print(self.user_mapping.keys())
        # Verificar si el usuario existe en el mapping
        if user_id_int not in self.user_mapping:
            print(f"Usuario {user_id_int} no encontrado en el dataset")
            # Fallback: usar un usuario aleatorio existente
            if self.user_mapping:
                user_id_int = list(self.user_mapping.keys())[0]
                print(f"Usando user_id {user_id_int} como fallback")
            else:
                return []
                
        #user_idx = self.user_mapping[user_id]
        user_idx = self.user_mapping[user_id_int]

        # Seleccionar películas no vistas por el usuario
        seen_movies = self.ratings_df[self.ratings_df['userId'] == user_id]['movieId'].tolist()
        all_movie_ids = self.movies_df['movieId'].tolist()
        candidate_movie_ids = [mid for mid in all_movie_ids if mid not in seen_movies]
        
        # Limitar número de candidatos por eficiencia
        candidate_movie_ids = candidate_movie_ids[:total_movies]
        
        if not candidate_movie_ids:
            print("No hay películas candidatas para recomendar")
            return []

        predictions = []
        
        for mid in candidate_movie_ids:
            # Verificar que la película esté en el mapping de items
            if mid not in self.item_mapping:
                continue
                
            item_idx = self.item_mapping[mid]

            # Obtener el título de la película para tokenización
            try:
                movie_row = self.movies_df[self.movies_df['movieId'] == mid]
                if movie_row.empty:
                    continue
                title = movie_row['title'].values[0]
            except (IndexError, KeyError):
                # Si no se puede obtener el título, usar un título por defecto
                title = "Unknown Movie"

            # Tokenizar el título
            try:
                inputs = self.tokenizer(
                    title, 
                    return_tensors='pt', 
                    padding='max_length',
                    truncation=True, 
                    max_length=32
                )
                input_ids = inputs['input_ids'].to(self.device)
                attention_mask = inputs['attention_mask'].to(self.device)
            except Exception as e:
                print(f"Error al tokenizar título '{title}': {e}")
                continue

            # Crear tensores para usuario e item
            user_tensor = torch.tensor([user_idx], device=self.device)
            item_tensor = torch.tensor([item_idx], device=self.device)

            # Realizar predicción
            try:
                with torch.no_grad():
                    rating_pred = self.model(user_tensor, item_tensor, input_ids, attention_mask)
                    rating_score = rating_pred.item()  # Ya debe venir entre 0 y 5 por torch.clamp
                    
                    # Asegurar que el score esté en el rango válido
                    rating_score = max(0.0, min(5.0, rating_score))
                    
                predictions.append((mid, rating_score))
                
            except Exception as e:
                print(f"Error al predecir para película {mid}: {e}")
                continue

        if not predictions:
            print("No se pudieron generar predicciones")
            return []

        # Ordenar por calificación descendente y tomar los top_k
        top_preds = sorted(predictions, key=lambda x: x[1], reverse=True)[:top_k]

        # Construir la lista de recomendaciones con metadatos
        recommendations = []
        for mid, score in top_preds:
            try:
                movie_data = self.movies_df[self.movies_df['movieId'] == mid].iloc[0]
                recommendations.append({
                    'movieId': mid,
                    'title': movie_data['title'],
                    'genres': movie_data['genres'],
                    'predicted_rating': round(score, 3)  # Redondear para mejor presentación
                })
            except Exception as e:
                print(f"Error al obtener datos de película {mid}: {e}")
                continue

        return recommendations
    
    def _predict_with_model(self, user_vector: torch.Tensor) -> np.ndarray:
        """
        Realiza predicciones utilizando el modelo pre-entrenado
        NOTA: Esta función se mantiene para compatibilidad, pero ahora se usa recommend_movies
        
        Args:
            user_vector: Vector de calificaciones del usuario
            
        Returns:
            Array con puntuaciones de predicción para todas las películas
        """
        print("Usando recommend_movies en lugar de _predict_with_model para mejor compatibilidad")
        return np.array([])

    def get_recommendations(self, user_id: str, user_ratings: Dict[str, float] = None, 
                           top_k: int = 10, return_scores: bool = False) -> Union[List[str], Tuple[List[str], Dict[str, float]]]:
        """
        Obtiene recomendaciones para un usuario usando el modelo híbrido
        
        Args:
            user_id: ID del usuario
            user_ratings: Diccionario de calificaciones para usuario nuevo (no usado en esta versión)
            top_k: Número de recomendaciones a devolver
            return_scores: Si es True, devuelve también las puntuaciones
            
        Returns:
            Lista de IDs de películas recomendadas y opcionalmente un diccionario de puntuaciones
        """
        try:
            # Usar la función recommend_movies adaptada
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
                    fallback_scores = {mid: 4.0 for mid in fallback_movies}  # Puntaje por defecto
                    return fallback_movies, fallback_scores
                else:
                    return fallback_movies
            except:
                return [] if not return_scores else ([], {})