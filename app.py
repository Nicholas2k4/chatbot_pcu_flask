import os, re
from flask import Flask, render_template, request, jsonify
from langchain_ollama.llms import OllamaLLM
from langchain.schema import SystemMessage, HumanMessage, AIMessage
from langchain_huggingface import HuggingFaceEmbeddings
from qdrant_client import QdrantClient

# ---------- Konfigurasi ----------
EMBEDDING_MODEL = "intfloat/multilingual-e5-large"
LLM_MODEL = "qwen3:14b"
TEMPERATURE = 0.3
TOP_K_PER_COLL = 5
TOP_K_TOTAL = 7

# ---------- Flask ----------
app = Flask(__name__)
app.config["JSON_AS_ASCII"] = False  # agar emoji & karakter non-ASCII aman

# ---------- Init Qdrant / Embedding / LLM ----------
qdrant_client = QdrantClient(
    url="https://b7c33b38-67cf-4e61-a9cc-67a8229e1ce1.us-east4-0.gcp.cloud.qdrant.io:6333", 
    api_key="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJhY2Nlc3MiOiJtIn0.8KRdzEsLQdz5HuQW3pdiRhHIJGhQOjGNsFmE6lt67DM",
)
embedder = HuggingFaceEmbeddings(model_name=EMBEDDING_MODEL)
llm = OllamaLLM(model=LLM_MODEL, temperature=TEMPERATURE)


# ---------- Util: retrieve docs ----------
def retrieve_top_docs(query: str):
    qvec = embedder.embed_query(query)
    hits_all = []
    for coll in qdrant.get_collections().collections:
        hits = qdrant.search(
            collection_name=coll.name,
            query_vector=qvec,
            limit=TOP_K_PER_COLL,
            with_payload=True,
        )
        for h in hits:
            hits_all.append(
                {
                    "collection": coll.name,
                    "score": h.score,
                    "content": h.payload.get("text", h.payload.get("page_content", "")),
                }
            )
    hits_all.sort(key=lambda x: x["score"], reverse=True)
    return hits_all[:TOP_K_TOTAL]


# ---------- Routes ----------
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/chat", methods=["POST"])
def chat():
    body = request.get_json(force=True)
    user_msg = body.get("message", "")
    history = body.get("history", [])  # dikirim klien

    # Retrieve
    docs = retrieve_top_docs(user_msg)
    context = "\n\n--------------------\n".join(
        f"[{i+1}] (from {d['collection']}): {d['content']} (Score: {d['score']})"
        for i, d in enumerate(docs)
    )

    # Prompt building
    messages = [
        SystemMessage(
            content="You are a helpful assistant. Use the provided documents to answer."
        )
    ]
    for item in history[-20:]:  # batasi 20 turn terakhir
        if item["role"] == "user":
            messages.append(HumanMessage(content=item["content"]))
        else:
            messages.append(AIMessage(content=item["content"]))
    messages.append(SystemMessage(content=f"Context documents:\n{context}"))
    messages.append(HumanMessage(content=user_msg))

    # LLM call
    raw_resp = llm.invoke(messages)

    # Remove <think>...</think> jika ada
    m = re.search(r"<think>(.*?)</think>", raw_resp, re.DOTALL)
    bot_resp = raw_resp.replace(m.group(0), "", 1).strip() if m else raw_resp.strip()

    return jsonify({"response": bot_resp})


if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=8501)
