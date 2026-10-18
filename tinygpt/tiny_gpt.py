"""
tiny_gpt.py  -  your TinyGPT, cleaned up and made trainable on a Mac CPU

    python tinygpt/tiny_gpt.py train
    python tinygpt/tiny_gpt.py generate "The Moon"

Fixes compared with the first draft:
  * word2ind / ind2word did not exist       -> we decode with the SentencePiece tokenizer
  * torch.cuda.is_available (no brackets)   -> is_available()   (a function is always truthy!)
  * vocab_size=40 was tiny                  -> 300 for our ~12 KB corpus (grow it as the corpus grows)
  * the model learned nothing about unseen  -> we hold out 10% of the text and print a validation loss
    text, so you notice over-fitting
  * `generate` always sampled               -> temperature + top-k, much less random garbage
  * the trained weights were thrown away    -> saved to tinygpt/tinygpt.pt, so the web app can load them
"""
import glob
import os
import sys

import sentencepiece as spm
import torch
import torch.nn as nn
import torch.nn.functional as F

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from transformer_block import Block  # noqa: E402

HERE = os.path.dirname(os.path.abspath(__file__))
KNOWLEDGE = os.path.join(os.path.dirname(HERE), "data", "knowledge")
CORPUS = os.path.join(HERE, "corpus.txt")
SPM_PREFIX = os.path.join(HERE, "tokenizer")
CKPT = os.path.join(HERE, "tinygpt.pt")

# ----------------------------- hyper-parameters ------------------------------
vocab_size_target = 300   # how many sub-word pieces the tokenizer learns
block_size = 64           # context window: the model sees at most 64 previous tokens
embedding_dim = 128       # each token becomes a vector of 128 numbers
n_heads = 4               # 4 attention heads, each looks at 32 of the 128 numbers
n_layers = 4              # 4 stacked transformer blocks
dropout = 0.1             # randomly switch off 10% of units while training -> less memorising
lr = 1e-3                 # learning rate: size of each weight update
steps = 3000              # training steps ("epochs" in the first draft; really one batch per step)
batch_size = 32

device = "cpu"            # small model: CPU is fine, and avoids Apple-GPU (mps) edge cases
torch.manual_seed(1337)


# ------------------------------ data preparation -----------------------------
def build_corpus():
    """Glue every knowledge file into one training text."""
    parts = []
    for p in sorted(glob.glob(os.path.join(KNOWLEDGE, "*.txt"))):
        with open(p, encoding="utf-8") as f:
            parts.append(f.read().strip())
    text = "\n\n".join(parts)
    with open(CORPUS, "w", encoding="utf-8") as f:
        f.write(text)
    return text


def train_tokenizer():
    """BPE tokenizer: produces tokenizer.model (the rules) and tokenizer.vocab (the pieces)."""
    spm.SentencePieceTrainer.Train(
        input=CORPUS, model_prefix=SPM_PREFIX, vocab_size=vocab_size_target,
        model_type="bpe", hard_vocab_limit=False)


def load_tokenizer():
    sp = spm.SentencePieceProcessor()
    sp.load(SPM_PREFIX + ".model")
    return sp


# ---------------------------------- the model --------------------------------
class TinyGPT(nn.Module):
    def __init__(self, vocab_size):
        super().__init__()
        self.token_embedding = nn.Embedding(vocab_size, embedding_dim)      # (vocab, 128): one row per token
        self.position_embedding = nn.Embedding(block_size, embedding_dim)   # (64, 128): one row per position
        self.blocks = nn.Sequential(*[Block(embedding_dim, block_size, n_heads, dropout) for _ in range(n_layers)])
        self.ln_f = nn.LayerNorm(embedding_dim)
        self.head = nn.Linear(embedding_dim, vocab_size)                    # 128 -> one score per vocabulary token

    def forward(self, idx, targets=None):
        B, T = idx.shape                                           # (batch, time)
        tok = self.token_embedding(idx)                            # (B, T, 128)  what the token is
        pos = self.position_embedding(torch.arange(T, device=idx.device))   # (T, 128)  where it is (broadcast over B)
        x = self.blocks(tok + pos)                                 # (B, T, 128)
        logits = self.head(self.ln_f(x))                           # (B, T, vocab)  raw scores for the NEXT token
        loss = None
        if targets is not None:
            loss = F.cross_entropy(logits.view(B * T, -1), targets.view(B * T))
        return logits, loss

    @torch.no_grad()
    def generate(self, idx, max_new_tokens, temperature=0.8, top_k=20):
        for _ in range(max_new_tokens):
            idx_cond = idx[:, -block_size:]                        # never feed more than the context window
            logits, _ = self(idx_cond)
            logits = logits[:, -1, :] / temperature                # only the last position predicts what comes next
            if top_k:                                              # keep the k best candidates, drop the rest
                v, _ = torch.topk(logits, min(top_k, logits.size(-1)))
                logits[logits < v[:, [-1]]] = float("-inf")
            probs = F.softmax(logits, dim=-1)
            idx = torch.cat((idx, torch.multinomial(probs, 1)), dim=1)
        return idx


# ---------------------------------- training ---------------------------------
def train():
    build_corpus()
    train_tokenizer()
    sp = load_tokenizer()
    vocab_size = sp.get_piece_size()

    with open(CORPUS, encoding="utf-8") as f:
        data = torch.tensor(sp.encode(f.read(), out_type=int), dtype=torch.long)
    n = int(0.9 * len(data))
    splits = {"train": data[:n], "val": data[n:]}
    print(f"vocab={vocab_size}  tokens={len(data)}  train={n}  val={len(data) - n}")

    def get_batch(split):
        d = splits[split]
        ix = torch.randint(len(d) - block_size - 1, (batch_size,))        # random starting points
        x = torch.stack([d[i:i + block_size] for i in ix])                # input tokens
        y = torch.stack([d[i + 1:i + block_size + 1] for i in ix])        # same window shifted by one = the answers
        return x, y

    @torch.no_grad()
    def evaluate():
        model.eval()
        out = {}
        for s in ("train", "val"):
            out[s] = sum(model(*get_batch(s))[1].item() for _ in range(10)) / 10
        model.train()
        return out

    model = TinyGPT(vocab_size).to(device)
    print(f"parameters: {sum(p.numel() for p in model.parameters()) / 1e6:.2f}M")
    opt = torch.optim.AdamW(model.parameters(), lr=lr)

    for step in range(steps):
        xb, yb = get_batch("train")
        _, loss = model(xb, yb)
        opt.zero_grad()      # forget the gradients of the previous step
        loss.backward()      # work out how each weight contributed to the error
        opt.step()           # nudge every weight a little in the helpful direction
        if step % 300 == 0 or step == steps - 1:
            e = evaluate()
            print(f"step {step:5d}  train loss {e['train']:.3f}  val loss {e['val']:.3f}")

    torch.save({"state": model.state_dict(), "vocab_size": vocab_size}, CKPT)
    print("saved ->", CKPT)
    print("\nSample:\n", generate_text("The Moon", 60))


# --------------------------------- inference ---------------------------------
_cache = {}


def generate_text(prompt, max_new_tokens=60):
    if "model" not in _cache:
        sp = load_tokenizer()
        ckpt = torch.load(CKPT, map_location=device)
        m = TinyGPT(ckpt["vocab_size"])
        m.load_state_dict(ckpt["state"])
        m.eval()
        _cache.update(model=m, sp=sp)
    sp, m = _cache["sp"], _cache["model"]
    ids = torch.tensor([sp.encode(prompt, out_type=int)], dtype=torch.long)
    out = m.generate(ids, max_new_tokens)
    return sp.decode(out[0].tolist())


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else "train"
    if cmd == "train":
        train()
    else:
        print(generate_text(" ".join(sys.argv[2:]) or "The Sun", 80))
