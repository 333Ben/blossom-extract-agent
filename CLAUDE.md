# extract-agent — règles pour l'IA

## Ce que fait ce service
Service Python FastAPI qui reçoit un PDF binaire, extrait le texte (PyMuPDF pour les natifs, Mistral OCR pour les scannés), sérialise les tables en markdown `| col | col |`, et écrit le résultat dans `documents.content_markdown` via agent-gateway. Pas de LLM dans ce service.

Voir `ARCHITECTURE.md` pour le détail complet.

## Règles absolues

- Ne jamais stocker le PDF binaire sur disque ou en DB
- Ne jamais appeler les EFs d'analyse (analyze-pv, analyze-charges…) — c'est le caller qui le fait
- Ne jamais appeler un LLM ici — extract-agent est entièrement déterministe (Python pur)
- Ne jamais modifier agent-gateway directement — ouvrir une issue dans flat-file-finder-v3
- `EXTRACT_SECRET` et `AGENT_GATEWAY_SECRET` ne sont jamais committés

## Runtime
Python 3.11+. Commandes :
- `uvicorn main:app --reload` (dev)
- `pip install -r requirements.txt`

## Supabase
Projet : `aavfqfqvufepjrbqwowi` (BlossomDoc production)
Écriture uniquement via agent-gateway (jamais en direct).

## Points d'attention
- PyMuPDF s'importe `import fitz` (pas `import pymupdf`)
- Mistral OCR : modèle `mistral-ocr-latest`, input PDF en base64
- pdfplumber est le fallback si `page.find_tables()` retourne 0 table sur un doc qui semble en avoir
- Le caller attend la réponse de façon synchrone — pas de background task sur /extract
