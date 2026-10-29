import os
import chromadb
from sentence_transformers import SentenceTransformer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KB_FILE = os.path.join(ROOT, "knowledge", "wind_turbine_faults.md")

text = open(KB_FILE, encoding="utf-8").read()
sections = [s.strip() for s in text.split("## ") if s.strip()]
titles = [s.split("\n")[0] for s in sections]

embedder = SentenceTransformer("all-MiniLM-L6-v2")
client = chromadb.PersistentClient(path=os.path.join(ROOT, "rag_store"))

try:
    client.delete_collection("faults")      # rebuild from scratch each run
except Exception:
    pass
col = client.create_collection("faults")

col.add(
    ids=[f"s{i}" for i in range(len(sections))],
    documents=sections,
    embeddings=embedder.encode(sections).tolist(),
    metadatas=[{"source": "wind_turbine_faults.md", "section": t} for t in titles],
)
print(f"Indexed {len(sections)} sections.\n")

# quick retrieval test
queries = [
    "gearbox oil temperature high and gearbox bearing temperature high",
    "vibration above normal",
    "power is low for the wind speed but temperatures are normal",
]
for q in queries:
    result = col.query(query_embeddings=embedder.encode([q]).tolist(), n_results=2)
    print("Query:", q)
    for meta, dist in zip(result["metadatas"][0], result["distances"][0]):
        print(f"   {meta['section']}  (distance {dist:.2f})")
    print()