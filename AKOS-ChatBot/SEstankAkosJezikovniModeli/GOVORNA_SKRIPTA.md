# GOVORNA SKRIPTA - AKOS ChatBot Benchmark
## Govor za srečanje (5-10 minut)

---

## 🎤 UVOD (30 sekund)

"Dobro jutro/popolo/veče, vsi. Danes vam predstavljam rezultate testiranja LLM modelov za AKOS chatbot.

Pred mesecoma smo imeli nalogo: **izbrati model, ki bo odgovarjal na vprašanja uporabnikov v slovenščini, brez halucinacij in hitro.**

Pokazat vam moram, zakaj je to bilo težje kot se zdi, kako smo jo rešili in seveda - kateri model smo izbrali."

---

## 🔴 PROBLEM (2 minuti)

### "Prvo vprašanje: Kaj je bil sploh problem?"

"Jah, na prvo oko ni videti problema. Imate vprašanja v slovenščini, imate odprtokodne modele (Llama, Mistral, Gemma), v redu?

Vendar, ko smo poskusili lokalno:

**Prvi poskus - lokalno z Ollama:**
- Vzeli smo model `gemma2:9b` in `mistral-nemo:12b`
- Benchmark se je zagnal
- Ampak... pri generiranju odgovorov se je model *zataknil*
- Čakal sem 420 sekund na en sam odgovor
- Potem: TIMEOUT - ne uspevam, no connection
- Model ni mogel niti odgovoriti!

To je bil problem. 🚨

**Zakaj se to dogaja?**
Domači GPU teh modelov pač ni mogel ditati. Premalo VRAM-a, preveč cache-anja, swap na disk... V bistvu smo imeli lokalno superpočasno igranje, ki je propadlo.

**Druga dimenzija problema:**
Model mora biti *zanesljiv* in *natančen* za domeno AKOS.
- Ne sme hallucinate (uganiti pravno svetovanje)
- Mora razumeti: kaj je gostovanje, kako poteka postopek, kaj je račun
- Mora odgovarjati v *naravni* slovenščini (nie 'hello' vmes)

To je zahtevno! Večina modelov je trenirano na angleščini."

---

## 💡 REŠITEV (2 minuti)

### "Potem se je zgodilo ČUDO..."

"Pred nekaj tedni sem naletел na **Groq** - mlado podjetje iz ZDA.

Kaj je Groq?
- Niso AI raziskovalci
- So hardware inženjerji
- Naredili so čip, imenovan 'GroqChip' - čist namenjen tomu da hitro požene LLM-e
- To je kot da bereš procesoj, ki je narejen samo za to: "hitro branje LLM-a"

Rezultat:
- Normalen GPU: 10-100 tokenov na sekundo
- **Groq: 500+ tokenov na sekundo**
- To je 5-50x hitreči!

**Praktično:**
- V Groq sem mogel teči benchmark
- 120 primerov
- 6 različnih modelov
- Povprečno 2-3 sekunde na odgovor
- **BREZ TIMEOUTOV**
- Skupaj: 30 minut (vs. nikoli lokalno!)

API je prosto dostopen:
- Do 7500 zahtevkov na dan
- Potem plačaš ($0.05-$0.20 na milijon tokenov, odvisno od modela)

To je revolucionalo - nisem mogel niti malo domačih testov, zdaj pa imam 720 testnih rezultatov! 🚀"

---

## 📊 REZULTATI (2 minuti)

### "In kaj smo odkrili?"

"OK, testiral sem 6 modelov, 120 primerov na vsakega. Ocene od 0 do 5.

Tukaj so rezultati:"

```
MODEL                                 OCENA    PORABA  STATUS
────────────────────────────────────────────────────────────
llama-3.3-70b-versatile              3.99     1.78s   ✅ PASS
meta-llama/llama-4-scout-17b         3.97     1.40s   ✅ PASS  
openai/gpt-oss-safeguard-20b         3.97     2.05s   ✅ PASS
llama-3.1-8b-instant                 3.95     1.27s   ✅ PASS
qwen/qwen3-32b                       3.92     2.74s   ✅ PASS
openai/gpt-oss-20b                   3.76     1.71s   ❌ FAIL
```

"Prvo: vsi modeli so bili **blizu skupaj**. Razlika med najboljšim (3.99) in 5-tim (3.92) je samo 0.07 točk.

Vendar:
- Llama 3.3 70B je bil **brez kritičnih napak** (0 hard fails)
- gpt-oss-20b je izbil 4 kritične napake (prazni odgovori)

Hitrost?
- Llama 3.1 8B je bil najhitrejši (1.27s)
- Qwen je počasnejši (2.74s), vendar še vedno OK

*Pokažite slajd s tabelo*"

### "Konkretni primeri odgovorov:"

**Najlepši primer (Llama 3.3, ocena 5.0):**
> Vprašanje: "Med postopkom pri AKOS moram sproti plačati sporni račun?"
>
> Odgovor: "Med postopkom pri AKOS **ni potrebno** takoj poravnati sporni račun. Lahko počakate na izid postopka. Po zaključku postopka boste obveščeni o izidu..."
>
> ✅ Jasno, natančno, slovenščina je odlična, odgovarja na vprašanje. PERFEKT.

**Slab primer (gpt-oss-20b, ocena 1.25):**
> Vprašanje: "Ali lahko mojega pričetka AKOS ..."
>
> Odgovor: "" ← PRAZEN STRING
>
> ❌ Model ni mogel odgovoriti, noč, nič. S tem da je "pametno" abstiniral (dal a točkiv za to) je dosegel samo 1.25, kar je premalo za produkcijo.

"Vidite razliko? Llama je dal *nasesvetan* odgovor, gpt-oss pa je tiho propadel."

---

## 🎯 PRIPOROČILO (2 minuti)

### "Kateri model izbrati?"

"Odgovor je odvisen od tega, kaj vam je prioriteta:

**OPCIJA 1: Maksimalna kakovost**

👑 **Izbira: Llama 3.3 70B Versatile**
- Ocena: 3.99 (najbolja!)
- Napake: 0 (zanesljivo!)
- Hitrost: 1.78 sekund (sprejemljivo)
- Velikost: 70 milijard parametrov

Priporočam to za produkcijo, ker je model največji in je najbolj fleksibilen za domenske nalogo AKOS.

**OPCIJA 2: Kompromis med kvaliteto in velikostjo**

⭐ **Izbira: Qwen 3.32B**
- Ocena: 3.92
- Napake: 0 (zanesljivo!)
- Hitrost: 2.74 sekund
- Velikost: 32 milijard parametrov

Če vam je malo malo manjši (in pocebajši na GPU), je Qwen soliden izbira.

**OPCIJA 3: Super hiter za mobilne/edge**

🚀 **Izbira: Llama 3.1 8B**
- Ocena: 3.95
- Napake: 0 (zanesljivo!)
- Hitrost: 1.27 sekund (NAJHITREJŠI!)
- Velikost: 8 milijard parametrov

To je model, ki ga lahko tečete **tudi lokalno** (Ollama: 'ollama pull llama3.1:8b'). Idealno za testiranje ali za mobilne aplikacije.

**MOJA PRIPOROČILO:**

V produkciji idite z **Llama 3.3 70B** - to je absolutna izbira. 

Kot fallback za manjše resurse idite z **Llama 3.1 8B** - še vedno super rezultat, lahko pa ga tečete lokalno."

---

## 🤔 "KAKO JE TO MOGOČE?" (1 minuta)

### "Obe vprašanja, ki vam gotovo prihajajo..."

**Vprašanje 1: "Je model dejansko mogel odgovoriti v slovenščini?"**

"Ja! Moderne LLM modele so trenirane na stotine milijonov besedil v večjem jezikov, tudi slovenščini.
- Llama 3 je treniran na 141 jezikih
- GPT-3.5+ ima slovenščino
- Qwen ima slovenščino

Vendar: kvaliteta se razlikuje med modeli in jeziki. Zato je testiranje bitega!"

**Vprašanje 2: "Zakaj je Groq tako hiter?"**

"Ker imajo **posvečeno hardware**. Njihov GroqChip je narejen samo za to: hitro poganjati LLM-e.

Normalen GPU (NVIDIA):
- Splošna namera
- Mora delati slike, videe, igre... in LLM-e
- Bottleneck: memory bandwidth

Groq GroqChip:
- Samo za LLM
- Optimizirani za inference (ne training)
- Specializiran procesor
- Rezultat: 500+ tokenov/sekundo

To je kot razlika med avtomobilom in Formulo 1. Oba vozita na cesti, ampak v različnih hitrostih."

---

## ✅ ZAKLJUČEK (1 minuta)

"Povzetek:

1. **Problem:** Potreben zanesljiv model za AKOS v slovenščini
2. **Izziv:** Lokalno je bilo neuspe je (timeouti, GPU prešibek)
3. **Rešitev:** Groq API - super hiter inference service
4. **Test:** 6 modelov, 120 primerov, 30 minut benchmarka
5. **Rezultat:** **Llama 3.3 70B je bednja (3.99 ocena, 0 napak)**
6. **Naslednji korak:** Integracija v produkcijo

Vprašanja?"

---

## 💬 ODGOVORI NA POGOSTA VPRAŠANJA

### V1: "Ali je Groq varno za podatke?"

"Groq je resna kompanija, imajo privacy policy, podatki se ne shranjujejo. To je samo API. Vendar, za zelo občutljive podatke (npr. zdravstvene), bi moral ponovno preveriti njihove pogoje."

### V2: "Kaj se zgodi, ko presežem 7500 zahtevkov na dan?"

"Plačaš pay-as-you-go. Cena: $0.05-$0.20 na milijon tokenov (odvisno od modela). Pri 1000 dnevnih zahtevkih bi bil stroški ~$5-15/mesec."

### V3: "Kako namestimo to na produkcijo?"

"Backend je že nameren za Groq (--backend groq flag). Potem samo nastavimo `GROQ_API_KEY` in je gotovo. Eno minutko koda spremembe."

### V4: "Kaj pa če Groq pade?"

"Imamo fallback: Llama 3.1 8B lokalno (Ollama). To te traja minuto za nameščanje i je spet živajoč, četudi počasnejši."

### V5: "Kateri podatki se pošljejo Groq-u?"

"Samo prompt (vprašanje). Znanje baza ostane lokalna (RAG je v backendu). Torej, samo vprašanja - brez občutljivih dokumentov."

---

## 📈 VIZUALNI MATERIALI (za PowerPoint/prezentacijo)

### Grafikon 1: Primerjava modelov
```
Llama 3.3 70B   ████████████████ 3.99 ✅
Scout 17B       ████████████████ 3.97 ✅
SafeGuard 20B   ████████████████ 3.97 ✅
Llama 3.1 8B    ████████████████ 3.95 ✅
Qwen 32B        ███████████████  3.92 ✅
GPT-OSS 20B     █████████████    3.76 ❌
```

### Grafikon 2: Hitrost
```
Llama 3.1 8B    ███████████ 1.27s ⚡ HITER
Scout 17B       ███████████████ 1.40s ⚡
Llama 3.3 70B   ██████████████████ 1.78s OK
GPT-OSS 20B     ██████████████████ 1.71s OK
SafeGuard 20B   ███████████████████ 2.05s OK
Qwen 32B        ██████████████████████ 2.74s POČASNO
```

### Grafikon 3: Local vs. Groq
```
Local Ollama         ███████████████████████████████████ 420s+ ❌ TIMEOUT
                     
Groq Llama 70B       ████████ 1.78s ✅ HITER 236x!
```

---

## 🎁 DODATNA OPOMBA

"Za tiste, ki vas zanima bolj tehnični del - imam podrobne benchmark rezultate:
- CSV datoteka s vsemi podocenami
- JSON datoteka s konkretnimi odgovori modelov
- Markdown poročilo s podrobnima analizo

Vse je na voljo v folderju `/results` v tem GitHub repozitoriju."

---

## ⏱️ TIMELINE

- **1. minuta:** Uvod + motivacija
- **2. minuti:** Kaj je bil problem (lokalni timeouti)
- **2. minuti:** Kako je Groq rešil problem
- **2. minuti:** Rezultati in primeri
- **2. minuti:** Priporočilo (kateri model)
- **1. minuta:** Zaključek + vprašanja
- **Do 10 minut:** Diskusija

**Skupno: 10-12 minut (fleksibilno)**

---

## 🎯 KLJUČNE TOČKE ZA ZAPAMTITI

1. "Testiral sem 6 modelov na 120 primerih preko Groq API"
2. "Lokalno je bilo nemogoče - Groq je omogočil test"
3. "Rezultati: Llama 3.3 70B je najbolja (3.99 ocena, 0 napak)"
4. "Hitrost: 1.78 sekund povprečno - odličko za chat"
5. "Produkcija: Groq API + Llama 3.3 70B"
6. "Fallback: Llama 3.1 8B lokalno (Ollama)"

---

Lyoko za slušnost! Kakšnega pitanja ste imeli? 🎤
