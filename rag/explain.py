import os
import chromadb
import ollama
from sentence_transformers import SentenceTransformer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MODEL = "llama3.2:3b"

embedder = SentenceTransformer("all-MiniLM-L6-v2")
collection = chromadb.PersistentClient(path=os.path.join(ROOT, "rag_store")).get_collection("faults")


def explain(symptom_text, n_results=2):
    hits = collection.query(
        query_embeddings=embedder.encode([symptom_text]).tolist(),
        n_results=n_results,
    )
    context = "\n\n".join(hits["documents"][0])
    sources = [m["section"] for m in hits["metadatas"][0]]

    prompt = f"""You are a wind turbine maintenance assistant.

Current symptoms:
{symptom_text}

Reference text:
{context}

Using ONLY the reference text above, answer in exactly this format:
Likely fault: <one name>
Why: <one or two sentences linking the symptoms to the fault>
Probable causes: <short list>
Recommended checks: <short numbered list>

If the reference text does not match the symptoms, say so instead of guessing."""

    response = ollama.chat(
        model=MODEL,
        messages=[{"role": "user", "content": prompt}],
        options={"temperature": 0.2},
    )
    return response["message"]["content"], sources


if __name__ == "__main__":
    symptoms = ("Gearbox oil temperature 85 C (critical); "
                "gearbox bearing temperature 90 C (critical); "
                "vibration normal")
    answer, sources = explain(symptoms)
    print(answer)
    print("\nSources:", ", ".join(sources))