from surprise import SVD
import numpy as np
import pandas as pd
from typing import Dict, List, Tuple, Any, Optional
from sklearn.metrics.pairwise import cosine_similarity
from collections import defaultdict
from concurrent.futures import ThreadPoolExecutor
import time
from tqdm import tqdm  # Para mostrar barras de progreso
import random

seed = 10
random.seed(seed)
np.random.seed(seed)

class HybridRecommender:
    """
    Hybrid recommendation system that combines collaborative filtering and context-aware models
    with optimized performance for large datasets and reduced memory footprint for serialization
    """

    def __init__(self, cf_model, context_model, data_dict,
                 cf_weight=0.7, context_weight=0.3, precompute=True):
        """
        Initialize the hybrid recommender

        Args:
            cf_model: Collaborative filtering model
            context_model: Context-aware model
            data_dict (dict): Dictionary containing DataFrames
            cf_weight (float): Weight for collaborative filtering predictions
            context_weight (float): Weight for context-aware predictions
            precompute (bool): Whether to precompute and cache data for faster recommendations
        """
        self.cf_model = cf_model
        self.context_model = context_model
        self.cf_weight = cf_weight
        self.context_weight = context_weight
        
        # Process and efficiently store data dictionaries
        self.process_data_dict(data_dict)
        
        # Maps for converting between internal IDs and actual IDs
        self.raw_to_inner_user_id = cf_model.trainset._raw2inner_id_users
        self.raw_to_inner_item_id = cf_model.trainset._raw2inner_id_items
        self.inner_to_raw_user_id = cf_model.trainset._inner2raw_id_users
        self.inner_to_raw_item_id = cf_model.trainset._inner2raw_id_items
        
        # Cache global mean for fallback
        self.global_mean = cf_model.trainset.global_mean

        # Flag to track whether precomputed data is available
        self._precomputed = False
        
        # Precompute and cache user and item factors for faster access
        if precompute:
            self._precompute_factors()
            self._precompute_similarity_matrix()
            self._precompute_review_lookup()
            self._precomputed = True

    def process_data_dict(self, data_dict):
        """Process and optimize data storage"""
        self.data_dict = {}
        
        # Optimize business dataframe
        if 'business' in data_dict:
            # Convert to dictionary for O(1) lookups
            business_df = data_dict['business']
            self.business_lookup = {}
            for _, row in business_df.iterrows():
                business_id = row['business_id']
                self.business_lookup[business_id] = {
                    'name': row.get('name', 'Unknown'),
                    'categories': row.get('categories', ''),
                    'city': row.get('city', ''),
                    'state': row.get('state', ''),
                    'stars': row.get('stars', 0)
                }
            
            # Keep all business IDs in a set for fast membership testing
            self.all_business_ids = set(business_df['business_id'].unique())
            
            # Don't store the original dataframe - we have the lookup now
            # self.data_dict['business'] = business_df
        
        # Optimize review dataframe - store only what's needed for recommendations
        if 'review' in data_dict:
            # Instead of storing full dataframe, create a slim dictionary structure
            self.user_ratings = {}
            review_df = data_dict['review']
            
            # Reset index if it was set
            if isinstance(review_df.index, pd.MultiIndex):
                review_df = review_df.reset_index()
                
            for _, row in review_df.iterrows():
                user_id = row['user_id']
                business_id = row['business_id']
                stars = row['stars']
                
                if user_id not in self.user_ratings:
                    self.user_ratings[user_id] = {}
                
                self.user_ratings[user_id][business_id] = stars
            
            # Don't store the original review dataframe
            # self.data_dict['review'] = data_dict['review'][['user_id', 'business_id', 'stars']].copy()
            
            # Garantiza que ningún valor sea None o mal formado
            for uid in list(self.user_ratings.keys()):
                if self.user_ratings[uid] is None or not isinstance(self.user_ratings[uid], dict):
                    self.user_ratings[uid] = {}
            
    def _precompute_factors(self):
        """Precompute and cache user and item factors"""
        print("Precomputing user and item factors...")
        start_time = time.time()
        
        # We won't cache these for serialization, but will use them in the current session
        self.user_factors = {}
        for uid, iid in self.raw_to_inner_user_id.items():
            self.user_factors[uid] = self.cf_model.pu[iid]
        
        self.item_factors = {}
        for iid, inner_iid in self.raw_to_inner_item_id.items():
            self.item_factors[iid] = self.cf_model.qi[inner_iid]
            
        print(f"Factors precomputed in {time.time() - start_time:.2f} seconds")

    def _precompute_similarity_matrix(self):
        """Precompute similarity matrix for all users"""
        print("Precomputing user similarity matrix...")
        start_time = time.time()
        
        # Create a matrix of all user factors
        n_users = len(self.raw_to_inner_user_id)
        user_factor_matrix = np.zeros((n_users, len(self.cf_model.pu[0])))
        
        for uid, inner_id in self.raw_to_inner_user_id.items():
            user_factor_matrix[inner_id] = self.cf_model.pu[inner_id]
        
        # Compute full similarity matrix
        self.user_similarity_matrix = cosine_similarity(user_factor_matrix)
        
        print(f"Similarity matrix precomputed in {time.time() - start_time:.2f} seconds")
    
    def _precompute_review_lookup(self):
        """Precompute review lookup for faster access to ratings"""
        # We already created this in process_data_dict
        pass

    def get_cf_predictions_batch(self, user_id, business_ids):
        """Get predictions from collaborative filtering model for multiple items at once"""
        predictions = {}
        
        # Check if user is in training set
        if user_id not in self.raw_to_inner_user_id:
            # Return global mean for all items
            return {bid: self.global_mean for bid in business_ids}
        
        user_inner_id = self.raw_to_inner_user_id[user_id]
        
        # Use cached user factors if available, otherwise get from model
        if self._precomputed and user_id in self.user_factors:
            user_factor = self.user_factors[user_id]
        else:
            user_factor = self.cf_model.pu[user_inner_id]
        
        for business_id in business_ids:
            # Check if business is in training set
            if business_id in self.raw_to_inner_item_id:
                item_inner_id = self.raw_to_inner_item_id[business_id]
                
                # Use cached item factors if available, otherwise get from model
                if self._precomputed and business_id in self.item_factors:
                    item_factor = self.item_factors[business_id]
                else:
                    item_factor = self.cf_model.qi[item_inner_id]
                
                # Calculate dot product
                pred = np.dot(user_factor, item_factor) + self.global_mean
                predictions[business_id] = pred
            else:
                predictions[business_id] = self.global_mean
                
        return predictions

    def get_context_predictions_batch(self, user_id, business_ids, context_features):
        """Get predictions from context-aware model for multiple items at once"""
        if not context_features:
            return {}
            
        predictions = {}
        
        # Check if user exists in context model
        user_idx = self.context_model['user_id_map'].get(user_id)
        if user_idx is None:
            return {}
        
        # Prepare batch input for the model
        batch_features = []
        valid_business_ids = []
        
        for business_id in business_ids:
            business_idx = self.context_model['business_id_map'].get(business_id)
            if business_idx is not None:
                # Base features
                features = [user_idx, business_idx]
                
                # Add context features
                for col in self.context_model['feature_cols']:
                    if col in context_features:
                        features.append(context_features[col])
                    else:
                        features.append(0)  # Default value
                
                batch_features.append(features)
                valid_business_ids.append(business_id)
        
        if not batch_features:
            return {}
            
        # Create DataFrame for batch prediction
        columns = ['user_idx', 'business_idx'] + self.context_model['feature_cols']
        X_batch = pd.DataFrame(batch_features, columns=columns)
        
        # Perform batch prediction
        try:
            batch_predictions = self.context_model['model'].predict(X_batch)
            
            # Map predictions back to business IDs
            for i, business_id in enumerate(valid_business_ids):
                predictions[business_id] = batch_predictions[i]
                
        except Exception as e:
            print(f"Error in context prediction: {e}")
            
        return predictions

    def get_similar_users_for_business(self, user_id, business_id, top_n=3):
        """Get similar users who rated this business highly"""
        similar_users_text = []
        
        try:
            # Check if user and item exist in training set
            if user_id not in self.raw_to_inner_user_id or business_id not in self.raw_to_inner_item_id:
                return []
                
            user_inner_id = self.raw_to_inner_user_id[user_id]
            
            # If similarity matrix is precomputed, use it
            if self._precomputed and hasattr(self, 'user_similarity_matrix'):
                # Get similarity scores for all users using precomputed matrix
                similarities = self.user_similarity_matrix[user_inner_id]
                
                # Create a list of (inner_id, similarity) pairs
                user_similarities = [(i, similarities[i]) for i in range(len(similarities)) if i != user_inner_id]
            else:
                # Compute similarities on the fly
                user_factor = self.cf_model.pu[user_inner_id]
                user_similarities = []
                
                # Limit to a subset of users for performance
                sample_users = list(self.raw_to_inner_user_id.items())[:1000]
                
                for uid, inner_id in sample_users:
                    if inner_id != user_inner_id:
                        other_user_factor = self.cf_model.pu[inner_id]
                        sim = np.dot(user_factor, other_user_factor) / (np.linalg.norm(user_factor) * np.linalg.norm(other_user_factor))
                        user_similarities.append((inner_id, sim))
            
            # Sort by similarity (descending)
            user_similarities.sort(key=lambda x: x[1], reverse=True)
            
            # Get top similar users
            top_similar_users = user_similarities[:top_n]
            
            # Check if they rated this item highly
            for inner_id, sim in top_similar_users:
                raw_id = self.inner_to_raw_user_id[inner_id]
                
                # Use the ratings lookup
                if (hasattr(self, 'user_ratings') and 
                    raw_id in self.user_ratings and 
                    isinstance(self.user_ratings[raw_id], dict) and ##
                    business_id in self.user_ratings[raw_id]
                    ):
                    user_rating = self.user_ratings[raw_id][business_id]
                    if user_rating >= 4:
                        similar_users_text.append(f"a similar user rated it {user_rating}/5")
                
        except Exception as e:
            print(f"Error finding similar users: {e} \n   — user_id: {user_id}, business_id: {business_id} \n")
            
        return similar_users_text

    def recommend(self, user_id, context_features=None, n=10, candidate_items=None, explanation=True):
        """
        Generate recommendations for a user with optimized performance

        Args:
            user_id (str): User ID
            context_features (dict): Contextual features
            n (int): Number of recommendations to generate
            candidate_items (list): List of candidate business IDs (if None, use all businesses)
            explanation (bool): Whether to include explanations

        Returns:
            list: List of recommendation dictionaries with scores and explanations
        """
        start_time = time.time()
        
        # Determine candidate items
        if candidate_items is None:
            candidate_items = list(self.all_business_ids)
        else:
            # Filter to make sure all candidates exist in our data
            candidate_items = [bid for bid in candidate_items if bid in self.all_business_ids]
        
        # Early exit if no candidates
        if not candidate_items:
            return []
            
        print(f"Generating recommendations for {len(candidate_items)} candidate items")
        
        # Get batch predictions from both models
        cf_scores = self.get_cf_predictions_batch(user_id, candidate_items)
        context_scores = {}
        
        if context_features and self.context_weight > 0:
            context_scores = self.get_context_predictions_batch(user_id, candidate_items, context_features)
        
        # Calculate final scores and create recommendation objects
        recommendations = []
        
        for business_id in candidate_items:
            cf_score = cf_scores.get(business_id, self.global_mean)
            context_score = context_scores.get(business_id)
            
            # Calculate final score
            if context_score is not None and self.context_weight > 0:
                final_score = (self.cf_weight * cf_score + self.context_weight * context_score)
            else:
                final_score = cf_score
            
            # Create recommendation object with business details
            business_details = self.business_lookup.get(business_id, {})
            
            rec = {
                'business_id': business_id,
                'score': final_score,
                'cf_score': cf_score,
                'context_score': context_score,
                'name': business_details.get('name', 'Unknown'),
                'categories': business_details.get('categories', ''),
                'city': business_details.get('city', ''),
                'stars': business_details.get('stars', 0)
            }
            
            # Don't generate explanations here to speed up the process
            recommendations.append(rec)
        
        # Sort recommendations by score and take top n
        recommendations.sort(key=lambda x: x['score'], reverse=True)
        top_recommendations = recommendations[:n]
        
        # Generate explanations for top recommendations if requested
        if explanation:
            with ThreadPoolExecutor(max_workers=min(10, n)) as executor:
                # Process explanations in parallel
                futures = []
                for rec in top_recommendations:
                    future = executor.submit(
                        self.generate_explanation,
                        user_id, 
                        rec['business_id'],
                        rec['cf_score'],
                        rec['context_score']
                    )
                    futures.append((rec, future))
                
                # Collect results
                for rec, future in futures:
                    rec['explanation'] = future.result()
        
        print(f"Recommendations generated in {time.time() - start_time:.2f} seconds")
        return top_recommendations

    def generate_explanation(self, user_id, business_id, cf_score, context_score):
        """
        Generate an explanation for a recommendation

        Args:
            user_id (str): User ID
            business_id (str): Business ID
            cf_score (float): Collaborative filtering score
            context_score (float): Context-aware score

        Returns:
            dict: Explanation dictionary
        """
        explanation = {}

        # Collaborative filtering explanation
        explanation['collaborative'] = "This recommendation is based on the ratings of users with similar preferences to yours."

        # Get similar users who rated this business highly
        similar_users_text = self.get_similar_users_for_business(user_id, business_id)
        if similar_users_text:
            explanation['similar_users'] = "Users with similar tastes to yours enjoyed this business: " + ", ".join(similar_users_text)

        # Context-aware explanation
        if context_score is not None:
            # Get the most important context features
            top_features = self.context_model['feature_importance'].head(5)['feature'].tolist()
            context_explanation = "This recommendation matches your current context"

            # Add specific context information if available
            context_specifics = []
            for feature in top_features:
                if feature.startswith('time_of_day_') or feature.startswith('season_') or feature.startswith('day_of_week_'):
                    context_specifics.append(feature.split('_', 1)[1])

            if context_specifics:
                context_explanation += " (" + ", ".join(context_specifics) + ")"

            explanation['context'] = context_explanation

        # Business attributes explanation
        business_details = self.business_lookup.get(business_id, {})
        categories = business_details.get('categories', '')
        
        if categories and categories != '':
            explanation['categories'] = f"This business is categorized as: {categories}"

        location = f"{business_details.get('city', '')}, {business_details.get('state', '')}"
        explanation['location'] = f"Located in: {location}"

        return explanation
        
    def __getstate__(self):
        """Custom method to control what gets pickled"""
        # Start with the object's dictionary
        state = self.__dict__.copy()
        
        # Don't save precomputed data
        if 'user_factors' in state:
            del state['user_factors']
        if 'item_factors' in state:
            del state['item_factors']
        if 'user_similarity_matrix' in state:
            del state['user_similarity_matrix']
        
        # Set flag to indicate precomputed data is missing
        state['_precomputed'] = False
        
        # Keep model core but remove large data structures
        if 'data_dict' in state:
            # Remove potentially large dataframes
            state['data_dict'] = {}
        
        return state
    
    def __setstate__(self, state):
        """Custom method to control what happens during unpickling"""
        # Restore instance attributes
        self.__dict__.update(state)
        
        # Mark as not precomputed
        self._precomputed = False