# AKOS ChatBot - Pogovorni Agent

Pogovorni agentni sistem za AKOS (Agencija za komunikacijska omrežja in storitve) namenjen odgovarjanju na vprašanja javnosti glede storitev AKOS.

## 📋 Opis

Sistem omogoča javnosti, da postavi vprašanja v naravnem jeziku in prejme odgovore na podlagi baze znanja AKOS. ChatBot uporablja lokalni LLM (Ollama) in RAG (retrieval-augmented generation) za semantično iskanje po dokumentih.

## 🏗️ Arhitektura

```
AKOS-ChatBot/
├── backend/
│   ├── app.py                      # Flask aplikacija
│   ├── requirements.txt             # Python odvisnosti
│   └── data/
│       └── akos_knowledge_base.json # Baza znanja
└── frontend/
    └── index.html                   # HTML ChatBot UI
```

## 🚀 Začetek

### Zahteve

- Python 3.8+
- pip
- Spletni brskalnik
- Ollama (lokalni LLM)

### Namestitev

1. **Kloniraj projekt**
```bash
cd AKOS-ChatBot
```

2. **Namesti Python odvisnosti**
```bash
cd backend
pip install -r requirements.txt
```

3. **Pripravi Ollama modele (LLM + embedding)**
```bash
ollama pull llama3.2:3b
ollama pull nomic-embed-text
```

4. **Zaženi Flask strežnik**
```bash
python app.py
```

Strežnik se bo zagnal na `http://localhost:5000`

5. **Odpri ChatBot v brskalniku**
```
Odpri `frontend/index.html` v spletnem brskalniku
ali
Obiskar: http://localhost/frontend/index.html (če je nastavljeno z drugimi orodji)
```

## 📚 API Endpoints

### POST `/api/chat`
Pošlje vprašanje in prejme odgovor

**Zahtevek:**
```json
{
  "query": "Kako lahko poddam pritožbo?",
  "user_profile": {
    "audience": "potrošnik",
    "tone": "prijazen",
    "detail_level": "kratko"
  }
}
```

**Odgovor:**
```json
{
  "answer": "Za pritožbe...",
  "method": "rag-semantic-llm",
  "sources": [
    {
      "title": "Varstvo potrošnikov",
      "category": "Varstvo potrošnikov",
      "id": "doc_002",
      "score": 0.87
    }
  ],
  "confidence": 0.9,
  "rag": {
    "enabled": true,
    "retrieval": "semantic",
    "embed_model": "nomic-embed-text",
    "last_error": null
  }
}
```

### GET `/api/info`
Pridobi informacije o ChatBot-u

**Odgovor:**
```json
{
  "name": "AKOS ChatBot",
  "description": "Pogovorni agent...",
  "documents_count": 10,
  "categories": ["Splošno", "Varstvo potrošnikov", ...]
}
```

### GET `/api/health`
Preveri stanje strežnika

## 🔧 Konfiguracija

### Dodajanje novih dokumentov

Uredi `backend/data/akos_knowledge_base.json` in dodaj nove dokumente:

```json
{
  "id": "doc_011",
  "title": "Naslov dokumenta",
  "category": "Kategorija",
  "content": "Vsebina dokumenta..."
}
```

## 📖 Primeri uporabe

1. **Vprašanje o pritožbah:**
   - "Kako lahko poddam pritožbo?"
   - "Kako do zavarovanja potrošnika?"

2. **Vprašanja o internetnem dostopu:**
   - "Kako deluje internetni dostop?"
   - "Kakšna je najmanjša hitrost interneta?"

3. **Vprašanja o specifikacijah:**
   - "Kakšne so tarife za storitve?"
   - "Kaj je 5G omrežje?"

## 🔐 Varnost

- CORS je omogočen za testiranje
- Za produkcijo ga je potrebno konfigurirati bolj restriktivno

## 📝 Napredne možnosti (v budućnosti)

- Vključitev AI modelov (OpenAI API, HuggingFace)
- Vektor iskanje z `FAISS` ali `Pinecone`
- Dinamično učenje od uporabnikov
- Multi-jezična podpora
- Slike in multimedijski odgovori
- Integracija s spletno stranjo AKOS

## 📞 Dostopanje do AKOS

- **Spletna stran:** www.akos.si
- **Telefon:** 01 581 72 00
- **E-pošta:** info@akos.si

## 📄 Licenca

MIT License

## 👥 Avtorji

Projekt je narejen za UL FRI v sodelovanju z AKOS

---

**Verzija:** 1.0.0  
**Datum:** Januar 2026
