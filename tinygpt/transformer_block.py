"""
transformer_block.py  -  one Transformer block (the thing you import as `Block`)

    x --> LayerNorm --> Causal Self-Attention --(+)--> LayerNorm --> MLP --(+)--> out
    |_____________________residual_______________|  |__________residual__________|
"""
import math

import torch
import torch.nn as nn
import torch.nn.functional as F


class CausalSelfAttention(nn.Module):
    def __init__(self, dim, block_size, n_heads, dropout=0.1):
        super().__init__()
        assert dim % n_heads == 0, "embedding_dim must be divisible by n_heads"
        self.n_heads = n_heads
        self.qkv = nn.Linear(dim, 3 * dim)      # one matmul gives Query, Key and Value
        self.proj = nn.Linear(dim, dim)         # mixes the heads back together
        self.drop = nn.Dropout(dropout)
        # lower-triangular matrix of 1s: token t may look at tokens 0..t but NOT the future
        self.register_buffer("mask", torch.tril(torch.ones(block_size, block_size)).view(1, 1, block_size, block_size))

    def forward(self, x):
        B, T, C = x.shape
        q, k, v = self.qkv(x).split(C, dim=2)                         # each (B, T, C)
        h = self.n_heads
        q, k, v = [t.view(B, T, h, C // h).transpose(1, 2) for t in (q, k, v)]   # (B, heads, T, C/heads)
        att = (q @ k.transpose(-2, -1)) / math.sqrt(C // h)           # how much each token cares about each other token
        att = att.masked_fill(self.mask[:, :, :T, :T] == 0, float("-inf"))   # hide the future
        att = self.drop(F.softmax(att, dim=-1))                       # scores -> probabilities that sum to 1
        y = (att @ v).transpose(1, 2).contiguous().view(B, T, C)      # weighted mix of Values, heads glued together
        return self.drop(self.proj(y))


class Block(nn.Module):
    def __init__(self, dim, block_size, n_heads, dropout=0.1):
        super().__init__()
        self.ln1 = nn.LayerNorm(dim)
        self.attn = CausalSelfAttention(dim, block_size, n_heads, dropout)
        self.ln2 = nn.LayerNorm(dim)
        self.mlp = nn.Sequential(                # "thinking" step applied to each token separately
            nn.Linear(dim, 4 * dim), nn.GELU(), nn.Linear(4 * dim, dim), nn.Dropout(dropout))

    def forward(self, x):
        x = x + self.attn(self.ln1(x))           # residual connection: keep the original signal + add what attention found
        x = x + self.mlp(self.ln2(x))
        return x
