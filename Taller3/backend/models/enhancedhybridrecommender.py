import os
import ast
import numpy as np
import pandas as pd
import torch
import torch.nn as nn
import torch.optim as optim
from torch.utils.data import Dataset, DataLoader
from transformers import BertModel, BertTokenizer
from torch_geometric.nn import GATConv
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_squared_error
from tqdm import tqdm

class EnhancedHybridRecommender(nn.Module):
    def __init__(self, num_users, num_items, bert_model_name='bert-base-uncased',
                 embedding_dim=64, num_heads=4, use_gat=True):
        super().__init__()
        self.use_gat = use_gat

        self.user_embedding = nn.Embedding(num_users, embedding_dim)
        self.item_embedding = nn.Embedding(num_items, embedding_dim)
        nn.init.normal_(self.user_embedding.weight, std=0.01)
        nn.init.normal_(self.item_embedding.weight, std=0.01)

        if use_gat:
            self.gat = GATConv(
                embedding_dim,
                embedding_dim // num_heads,
                heads=num_heads,
                dropout=0.1
            )

        self.bert = BertModel.from_pretrained(bert_model_name)
        self.bert_projection = nn.Sequential(
            nn.Linear(self.bert.config.hidden_size, embedding_dim),
            nn.LayerNorm(embedding_dim)
        )

        combined_dim = embedding_dim * 3
        self.prediction = nn.Sequential(
            nn.Linear(combined_dim, embedding_dim * 2),
            nn.LayerNorm(embedding_dim * 2),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(embedding_dim * 2, 1)
        )

        self.device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')

    def forward(self, user_ids, item_ids, item_input_ids, item_attention_mask):
        user_emb = self.user_embedding(user_ids)
        item_emb = self.item_embedding(item_ids)

        if self.use_gat:
            batch_size = user_ids.size(0)
            x = torch.cat([user_emb, item_emb], dim=0)
            edge_index = torch.stack([
                torch.arange(batch_size, device=user_ids.device),
                torch.arange(batch_size, device=user_ids.device)
            ], dim=0)
            gat_out = self.gat(x, edge_index)
            user_gat = gat_out[:batch_size]
            item_gat = gat_out[batch_size:]
        else:
            user_gat = user_emb
            item_gat = item_emb

        bert_output = self.bert(
            input_ids=item_input_ids,
            attention_mask=item_attention_mask
        )
        text_emb = self.bert_projection(bert_output.last_hidden_state[:, 0, :])

        combined = torch.cat([user_gat, item_gat, text_emb], dim=1)
        rating = self.prediction(combined)
        rating = torch.clamp(rating, 0, 5)  # Garantiza rango 0–5 sin usar sigmoide
        return rating.squeeze()