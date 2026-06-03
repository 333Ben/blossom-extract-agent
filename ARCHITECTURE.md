# Architecture — extract-agent

> Service d'extraction PDF partagé pour l'écosystème Blossom.
> Ce doc répond à : "comment fonctionne ce service, quelles sont ses interfaces, et pourquoi ces choix ?"

---

## Rôle dans l'écosystème

`extract-agent` est le seul service autorisé à extraire du texte depuis un PDF.
Il est appelé par tous les canaux (UI web, intake-agent email, futur Iris) avant tout appel aux EFs d'analyse.

```
UI web (bouton universel)  ──┐
blossom-intake-agent       ──┤──→ POST /extract ──→ PyMuPDF ou Mistral OCR
futur Iris / autres agents ──┘                  ──→ Claude build-markdown
                                                 ──→ agent-gateway save_raw_document
                                                 ←── { document_id, content_markdown }
                                                          │
                                              caller appelle analyze-* EFs
                                              avec content_markdown comme texte
```

---

## Endpoint

### `POST /extract`

**Auth :** header `x-extract-secret` (valeur dans `EXTRACT_SECRET` env var)

**Input (multipart/form-data) :**
| Champ | Type | Obligatoire | Description |
|---|---|---|---|
| `pdf_binary` | bytes | ✅ | Contenu binaire du PDF |
| `dossier_id` | str | ✅ | UUID du dossier Supabase |
| `filename` | str | ✅ | Nom de fichier original |
| `user_id` | str | ✅ | UUID user Supabase (pour RLS en DB) |

**Output (JSON) :**
```json
{
  "document_id": "uuid",
  "content_markdown": "texte narratif...\n<!-- page:2 -->\n```json\n{\"tableau_charges\": [{\"poste\": \"Charges générales\", \"montant\": 968.15}]}\n```\nsuite texte...",
  "is_scanned": false,
  "page_count": 12,
  "tables_detected": 3
}
```

**Erreurs :**
| Code | Cas |
|---|---|
| 400 | PDF corrompu ou illisible |
| 401 | `x-extract-secret` absent ou invalide |
| 422 | Champ obligatoire manquant |
| 502 | Mistral OCR API ou agent-gateway injoignable |

**Auth selon le caller :**
- **intake-agent (backend)** → envoie `x-extract-secret` directement
- **Navigateur (UI web)** → passe par l'EF Supabase `start-extraction` (~30 lignes Deno) qui vérifie le JWT et relaie à extract-agent avec `x-extract-secret`

---

## Pipeline interne

```
PDF binaire reçu
      │
      ▼
1. SCAN DETECTION
   PyMuPDF → extrait un échantillon de texte
   avgCharsPerPage < 50 → is_scanned = True
      │
      ├─ is_scanned = False ──→ 2a. PyMuPDF EXTRACTION
      │                              fitz.open() → get_text() par page
      │                              page.find_tables() → tables détectées
      │                              tables sérialisées en markdown | col | col |
      │                              marqueurs <!-- page:N --> ajoutés en Python
      │                              fallback : pdfplumber si find_tables() retourne 0 table
      │                              sur un doc qui semble en avoir
      │
      └─ is_scanned = True  ──→ 2b. MISTRAL OCR
                                    POST api.mistral.ai/v1/ocr
                                    model: mistral-ocr-latest
                                    input: PDF en base64
                                    retourne markdown natif (tables en | col | col | incluses)
                                    marqueurs <!-- page:N --> insérés depuis la structure Mistral
      │
      ▼
3. SAVE via agent-gateway
   POST /agent-gateway { action: "save_raw_document", dossier_id, user_id, content_markdown, filename, is_scanned, page_count }
   ← { document_id }
      │
      ▼
4. RETOUR au caller
   { document_id, content_markdown, is_scanned, page_count, tables_detected }
```

**Pourquoi pas de LLM dans extract-agent :**
- PyMuPDF `find_tables()` retourne les tables structurées directement — sérialisation Python pure
- Mistral OCR retourne déjà du markdown avec tables — utilisé tel quel
- Les EFs d'analyse (analyze-charges, analyze-pv…) ont leurs propres appels LLM
- extract-agent est entièrement déterministe, testable sans API, zéro token

---

## Format content_markdown

Produit par Python (PyMuPDF ou Mistral OCR), sans LLM.

```
texte narratif page 1...

<!-- page:2 -->

texte narratif page 2...

| Poste | Montant | Unité |
|---|---|---|
| Charges générales | 968,15 | EUR/an |
| Eau froide | 234,00 | EUR/an |

suite texte page 2...
```

**Règles :**
- Les marqueurs `<!-- page:N -->` sont insérés par Python à chaque changement de page
- Les tables sont en markdown standard `| col | col |` — lisibles par Claude dans les EFs et le chat futur
- Le texte narratif est conservé tel quel
- Pas de transformation LLM — ce que PyMuPDF ou Mistral retournent est utilisé directement

---

## Authentification

| Direction | Header | Valeur | Source |
|---|---|---|---|
| Caller → extract-agent | `x-extract-secret` | secret partagé | `EXTRACT_SECRET` env var |
| extract-agent → agent-gateway | `x-agent-secret` | même secret que les autres agents | `AGENT_GATEWAY_SECRET` env var |

---

## Variables d'environnement

```env
# Auth
EXTRACT_SECRET=<secret à générer — partagé avec UI web et intake-agent>

# Blossom backend
AGENT_GATEWAY_URL=https://aavfqfqvufepjrbqwowi.supabase.co/functions/v1/agent-gateway
AGENT_GATEWAY_SECRET=<même valeur que les autres agents>

# APIs
MISTRAL_API_KEY=<clé Mistral pour OCR scannés>

# Config
PORT=8000
```

---

## Structure fichiers

```
extract-agent/
├── src/
│   ├── pdf/
│   │   ├── extractor.py        # PyMuPDF : extraction texte + find_tables() → markdown
│   │   └── fallback.py         # pdfplumber : fallback si PyMuPDF rate les tables
│   ├── ocr/
│   │   └── mistral.py          # Client Mistral OCR API → markdown natif
│   └── blossom/
│       └── gateway.py          # HTTP client → agent-gateway save_raw_document
├── main.py                     # FastAPI app + endpoint POST /extract
├── requirements.txt
├── railway.toml
├── ARCHITECTURE.md             # ← vous êtes ici
├── CLAUDE.md                   # Règles absolues pour l'IA qui code dans ce repo
└── .env.example
```

---

## Dépendances

```
fastapi
uvicorn[standard]
pymupdf
pdfplumber
httpx
mistralai
python-multipart
```

---

## Déploiement Railway

Nom du service : **`blossom-extract-agent`** (aligne avec `blossom-intake-agent`).

```toml
# railway.toml
[deploy]
startCommand = "uvicorn main:app --host 0.0.0.0 --port $PORT"
```

Variables à configurer dans le dashboard Railway : voir section Variables d'environnement ci-dessus.

---

## Ce que ce service ne fait PAS

- Ne classe pas le document (c'est `classify-document` EF existante)
- Ne stocke pas le PDF binaire (consommé en mémoire, jeté après extraction)
- N'appelle pas les EFs d'analyse (c'est le caller qui le fait avec le content_markdown retourné)
- Ne crée pas de dossier (c'est agent-gateway via le caller)

---

## Lien avec les autres services

| Service | Relation |
|---|---|
| **agent-gateway** | extract-agent écrit via `save_raw_document` (action à créer dans agent-gateway, ~20 lignes) |
| **analyze-* EFs** | appelées par le caller (UI web ou intake-agent) avec `content_markdown` comme `text` |
| **blossom-intake-agent** | passe ses PDFs à extract-agent au lieu d'extraire lui-même — répare le bug scannés ignorés |
| **bouton universel (front)** | appelle extract-agent, reçoit `content_markdown`, passe aux EFs d'analyse |

---

*Dernière mise à jour : 2026-06-03 — spec initiale*
