from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import math
import requests

app = Flask(__name__)
CORS(app)

# Ollama configuration
OLLAMA_BASE_URL = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434")
OLLAMA_API_URL = os.getenv("OLLAMA_API_URL", f"{OLLAMA_BASE_URL}/api/generate")
OLLAMA_EMBED_URL = os.getenv("OLLAMA_EMBED_URL", f"{OLLAMA_BASE_URL}/api/embed")
OLLAMA_MODEL = os.getenv("OLLAMA_MODEL", "llama3.2:3b")
OLLAMA_EMBED_MODEL = os.getenv("OLLAMA_EMBED_MODEL", "nomic-embed-text")
OLLAMA_TIMEOUT_SECONDS = int(os.getenv("OLLAMA_TIMEOUT_SECONDS", "300"))

# Load knowledge base
KB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'akos_knowledge_base.json')

class AKOSChatBot:
    def __init__(self, kb_path):
        self.kb_path = kb_path
        self.documents = []
        self.chunks = []
        self.chunk_embeddings = []
        self.rag_ready = False
        self.last_rag_error = None
        self.load_knowledge_base()
    
    def load_knowledge_base(self):
        """Load knowledge base from JSON file"""
        try:
            with open(self.kb_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.documents = data.get('documents', [])
            self._build_rag_index()
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            self.documents = []
            self.rag_ready = False

    def _chunk_text(self, text, max_chars=420, overlap=80):
        """Split text into overlapping chunks for retrieval."""
        clean = " ".join((text or "").split())
        if not clean:
            return []

        chunks = []
        start = 0
        text_length = len(clean)
        while start < text_length:
            end = min(text_length, start + max_chars)
            chunk = clean[start:end].strip()
            if chunk:
                chunks.append(chunk)
            if end >= text_length:
                break
            start = max(0, end - overlap)
        return chunks

    def _build_rag_index(self):
        """Build embedding index from KB chunks."""
        self.chunks = []
        self.chunk_embeddings = []
        self.rag_ready = False
        self.last_rag_error = None

        for doc in self.documents:
            text = f"{doc.get('title', '')}. {doc.get('content', '')}".strip()
            split_chunks = self._chunk_text(text)
            for index, chunk in enumerate(split_chunks):
                self.chunks.append({
                    "chunk_id": f"{doc.get('id', 'doc')}_c{index + 1}",
                    "doc_id": doc.get('id'),
                    "title": doc.get('title'),
                    "category": doc.get('category'),
                    "content": chunk
                })

        if not self.chunks:
            self.last_rag_error = "Knowledge base je prazna."
            return

        try:
            for chunk in self.chunks:
                emb = self._embed_text(chunk["content"])
                self.chunk_embeddings.append(emb)
            self.rag_ready = len(self.chunk_embeddings) == len(self.chunks)
        except Exception as e:
            self.last_rag_error = str(e)
            self.rag_ready = False
            self.chunk_embeddings = []
            print(f"RAG index fallback (keyword search): {e}")

    def _embed_text(self, text):
        """Create embedding via Ollama embeddings API."""
        endpoints = [OLLAMA_EMBED_URL]
        if "/api/embed" in OLLAMA_EMBED_URL:
            endpoints.append(OLLAMA_EMBED_URL.replace("/api/embed", "/api/embeddings"))
        elif "/api/embeddings" in OLLAMA_EMBED_URL:
            endpoints.append(OLLAMA_EMBED_URL.replace("/api/embeddings", "/api/embed"))

        last_error = None
        for endpoint in endpoints:
            try:
                body = {
                    "model": OLLAMA_EMBED_MODEL,
                    "input": text
                }
                if endpoint.endswith("/api/embeddings"):
                    body = {
                        "model": OLLAMA_EMBED_MODEL,
                        "prompt": text
                    }

                response = requests.post(endpoint, json=body, timeout=90)
                response.raise_for_status()
                payload = response.json()

                embedding = payload.get("embedding")
                if not embedding and payload.get("embeddings"):
                    embedding = payload.get("embeddings")[0]

                if embedding:
                    return embedding

                last_error = "Embedding odgovor je prazen."
            except Exception as e:
                last_error = str(e)

        raise Exception(last_error or "Embedding endpoint ni dostopen.")

    def _cosine_similarity(self, vector_a, vector_b):
        """Cosine similarity for two vectors."""
        dot = sum(a * b for a, b in zip(vector_a, vector_b))
        norm_a = math.sqrt(sum(a * a for a in vector_a))
        norm_b = math.sqrt(sum(b * b for b in vector_b))
        if norm_a == 0 or norm_b == 0:
            return 0.0
        return dot / (norm_a * norm_b)
    
    def _search_documents_keyword(self, query, top_k=3):
        """Keyword fallback retrieval."""
        query_lower = query.lower()
        query_words = set(query_lower.split())

        scores = []
        for doc in self.documents:
            content = (doc.get('title', '') + ' ' + doc.get('content', '')).lower()
            content_words = set(content.split())

            # Calculate Jaccard similarity
            if len(query_words | content_words) > 0:
                similarity = len(query_words & content_words) / len(query_words | content_words)
                scores.append((doc, similarity))

        # Sort by similarity and return top-k
        scores.sort(key=lambda x: x[1], reverse=True)
        docs = [doc for doc, score in scores[:top_k] if score > 0]
        return [
            {
                "doc_id": d.get("id"),
                "title": d.get("title"),
                "category": d.get("category"),
                "content": d.get("content", ""),
                "score": 0.0
            }
            for d in docs
        ]

    def retrieve_context(self, query, top_k=3):
        """Retrieve relevant chunks using semantic search, fallback to keyword."""
        if not self.rag_ready:
            return self._search_documents_keyword(query, top_k=top_k), "keyword"

        try:
            query_embedding = self._embed_text(query)
            scored_chunks = []
            for chunk, embedding in zip(self.chunks, self.chunk_embeddings):
                score = self._cosine_similarity(query_embedding, embedding)
                scored_chunks.append((chunk, score))

            scored_chunks.sort(key=lambda item: item[1], reverse=True)
            top_chunks = []
            for chunk, score in scored_chunks[:top_k]:
                enriched = dict(chunk)
                enriched["score"] = round(float(score), 4)
                top_chunks.append(enriched)
            return top_chunks, "semantic"
        except Exception as e:
            self.last_rag_error = str(e)
            print(f"Semantic retrieval fallback: {e}")
            return self._search_documents_keyword(query, top_k=top_k), "keyword"
    
    def generate_response(self, query, user_profile=None):
        """Generate response using semantic RAG with local LLM."""
        relevant_chunks, retrieval_method = self.retrieve_context(query, top_k=3)
        context = self._build_context(relevant_chunks)

        # Generate response using local LLM
        try:
            answer = self._generate_with_llm(query, context, user_profile=user_profile)
            method = f"rag-{retrieval_method}-llm"
        except Exception as e:
            print(f"LLM error: {e}")
            # Fallback to simple response
            answer = self._synthesize_answer(query, relevant_chunks, context)
            method = f"fallback-{retrieval_method}"

        unique_sources = {}
        for chunk in relevant_chunks:
            source_key = chunk.get("doc_id") or chunk.get("chunk_id")
            if source_key not in unique_sources:
                unique_sources[source_key] = {
                    "title": chunk.get('title'),
                    "category": chunk.get('category'),
                    "id": chunk.get('doc_id') or chunk.get('chunk_id'),
                    "score": chunk.get('score', 0.0)
                }

        return {
            "answer": answer,
            "sources": list(unique_sources.values()),
            "confidence": min(1.0, len(relevant_chunks) * 0.33) if relevant_chunks else 0.0,
            "method": method,
            "rag": {
                "enabled": self.rag_ready,
                "retrieval": retrieval_method,
                "embed_model": OLLAMA_EMBED_MODEL,
                "last_error": self.last_rag_error
            }
        }

    def _build_context(self, documents):
        """Build context string from documents"""
        if not documents:
            return "Ni dostopnih dokumentov."

        context_parts = []
        for index, doc in enumerate(documents, start=1):
            title = doc.get('title', 'Brez naslova')
            content = (doc.get('content', '') or '').strip()
            if len(content) > 500:
                content = content[:500] + " ..."
            category = doc.get('category', '')
            source_id = doc.get('doc_id') or doc.get('id') or doc.get('chunk_id')
            context_parts.append(
                f"[VIR {index}]\nID: {source_id}\nNaslov: {title}\nKategorija: {category}\nVsebina: {content}"
            )

        context = "\n\n---\n\n".join(context_parts)
        if len(context) > 1500:
            context = context[:1500] + " ..."
        return context

    def _generate_with_llm(self, query, context, user_profile=None):
        """Generate response using Ollama local LLM"""
        user_profile = user_profile or {}
        audience = user_profile.get("audience", "splošna javnost")
        tone = user_profile.get("tone", "prijazen in strokoven")
        detail_level = user_profile.get("detail_level", "kratko")

        prompt = f"""Ti si customer support agent za AKOS (Agencijo za komunikacijska omrežja in storitve Republike Slovenije).

Odgovori na uporabnikovo vprašanje na podlagi naslednjih informacij iz naše baze znanja:

BAZA ZNANJA:
{context}

UPORABNIKOVO VPRAŠANJE: {query}

PROFIL UPORABNIKA:
- Ciljna publika: {audience}
- Želen ton: {tone}
- Nivo podrobnosti: {detail_level}

Navodila:
- Odgovori v slovenščini, jasno in brez ugibanj
- Uporabi samo informacije iz baze znanja
- Če je odgovor v bazi znanja, ga razloži in na koncu navedi uporabljene vire v obliki "Viri: [VIR 1], [VIR 2]"
- Če ga ni, predlagaj kontakt s AKOS: www.akos.si ali 01 581 72 00
- Bodi jedrnat (2-4 stavki, razen če uporabnik želi podrobno)

ODGOVOR:"""

        try:
            response = requests.post(
                OLLAMA_API_URL,
                json={
                    "model": OLLAMA_MODEL,
                    "prompt": prompt,
                    "stream": False,
                    "temperature": 0.4,
                    "top_p": 0.9,
                    "options": {
                        "num_predict": 120
                    }
                },
                timeout=OLLAMA_TIMEOUT_SECONDS
            )
            
            if response.status_code == 200:
                result = response.json()
                return result.get('response', '').strip()
            else:
                return f"Napaka pri LLM-u: {response.status_code}"
                
        except requests.exceptions.ConnectionError:
            raise Exception(f"Ollama ni dostopna na {OLLAMA_API_URL}. Prosimo, zagon Ollama.")
        except Exception as e:
            raise Exception(f"LLM napaka: {str(e)}")
    
    def _synthesize_answer(self, query, docs, context):
        """Synthesize answer from documents"""
        query_lower = query.lower()
        
        # Simple pattern matching for common questions
        if any(word in query_lower for word in ['pritožba', 'pritožbo', 'tožba']):
            return f"Za pritožbe glede komunikacijskih ali poštnih storitev se lahko obrnete na AKOS. " \
                   f"Lahko poddate pritožbo prek našega portala na www.akos.si. {context}"
        
        elif any(word in query_lower for word in ['tarifa', 'cena', 'stroški', 'cene']):
            return f"AKOS nadzira tarife telekomunikacijskih in poštnih operaterjev. " \
                   f"Spremembe cen so dozvoljene samo z 30-dnevnim napovedim. {context}"
        
        elif any(word in query_lower for word in ['internet', 'dostop']):
            return f"Vsak državljan Slovenije ima pravico do dostopa do interneta. " \
                   f"AKOS zagotavlja nepristransko dostopnost za vse operaterje. {context}"
        
        elif any(word in query_lower for word in ['5g', '4g', 'omrežje']):
            return f"AKOS upravlja radiofrekvenčni spekter in dodeljuje dovoljenice za omrežja. " \
                   f"Cilj je, da bi bila 5G dostopna v večini naselij do leta 2027. {context}"
        
        else:
            return f"Na podlagi naše baze znanja vam lahko podam naslednje informacije: {context}"

# Initialize chatbot
chatbot = AKOSChatBot(KB_PATH)

@app.route('/api/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({"status": "ok", "timestamp": datetime.now().isoformat()}), 200

@app.route('/api/chat', methods=['POST'])
def chat():
    """Chat endpoint"""
    try:
        data = request.get_json()
        query = data.get('query', '').strip()
        user_profile = data.get('user_profile', {})
        
        if not query:
            return jsonify({
                "error": "Vprašanje ne sme biti prazno."
            }), 400
        
        response = chatbot.generate_response(query, user_profile=user_profile)
        return jsonify(response), 200
    
    except Exception as e:
        return jsonify({
            "error": f"Napaka pri obdelavi vprašanja: {str(e)}"
        }), 500

@app.route('/api/info', methods=['GET'])
def info():
    """Get info about the chatbot"""
    return jsonify({
        "name": "AKOS ChatBot",
        "description": "Pogovorni agent za odgovore na vprašanja o AKOS",
        "documents_count": len(chatbot.documents),
        "categories": list(set(doc.get('category', 'Neznano') for doc in chatbot.documents)),
        "rag": {
            "enabled": chatbot.rag_ready,
            "embed_model": OLLAMA_EMBED_MODEL,
            "chunk_count": len(chatbot.chunks),
            "last_error": chatbot.last_rag_error
        }
    }), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
