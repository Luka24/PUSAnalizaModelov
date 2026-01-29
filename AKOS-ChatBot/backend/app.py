from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import os
from datetime import datetime
import re

app = Flask(__name__)
CORS(app)

# Load knowledge base
KB_PATH = os.path.join(os.path.dirname(__file__), 'data', 'akos_knowledge_base.json')

class AKOSChatBot:
    def __init__(self, kb_path):
        self.kb_path = kb_path
        self.documents = []
        self.load_knowledge_base()
    
    def load_knowledge_base(self):
        """Load knowledge base from JSON file"""
        try:
            with open(self.kb_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
                self.documents = data.get('documents', [])
        except Exception as e:
            print(f"Error loading knowledge base: {e}")
            self.documents = []
    
    def search_documents(self, query, top_k=3):
        """Search documents based on keyword similarity"""
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
        return [doc for doc, score in scores[:top_k] if score > 0]
    
    def generate_response(self, query):
        """Generate response based on query"""
        # Search for relevant documents
        relevant_docs = self.search_documents(query, top_k=3)
        
        if not relevant_docs:
            return {
                "answer": "Žal, ne najdem direktnega odgovora na vaše vprašanje v naši bazi znanja. Prosimo, da kontaktirate AKOS direktno na www.akos.si ali prek telefona 01 581 72 00.",
                "sources": [],
                "confidence": 0.0
            }
        
        # Build response from relevant documents
        context = "\n".join([
            f"- {doc.get('title', 'Brez naslova')}: {doc.get('content', '')}"
            for doc in relevant_docs
        ])
        
        # Generate a more contextual response
        answer = self._synthesize_answer(query, relevant_docs, context)
        
        return {
            "answer": answer,
            "sources": [
                {
                    "title": doc.get('title'),
                    "category": doc.get('category'),
                    "id": doc.get('id')
                }
                for doc in relevant_docs
            ],
            "confidence": min(1.0, len(relevant_docs) * 0.3)
        }
    
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
        
        if not query:
            return jsonify({
                "error": "Vprašanje ne sme biti prazno."
            }), 400
        
        response = chatbot.generate_response(query)
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
        "categories": list(set(doc.get('category', 'Neznano') for doc in chatbot.documents))
    }), 200

if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0', port=5000)
