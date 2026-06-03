# Roadmap — extract-agent

---

## À faire — infra

- [ ] Vérifier les secrets Railway après migration Supabase 2026-05-22 — les env vars de blossom-intake-agent n'avaient pas été mis à jour. S'assurer que extract-agent est déployé avec les bons secrets (`EXTRACT_SECRET`, `AGENT_GATEWAY_URL`, `AGENT_GATEWAY_SECRET`, `MISTRAL_API_KEY`).

---

## À faire — intégration BlossomDoc

- [ ] Remplacer `extractTextFromPDF(file)` dans les hooks React (flat-file-finder-v3) par un `fetch` vers `POST /extract` (extract-agent Railway). Les 9 EFs d'analyse (`analyze-pv`, `analyze-dpe`, etc.) ne changent pas — elles reçoivent toujours `{ text, fileName, dossierId }` depuis le caller.

ordre : Build + déploie extract-agent sur Railway
Teste POST /extract — vérifie que content_markdown revient correct sur des PDFs natifs et scannés
Seulement après : remplace extractTextFromPDF dans les hooks React

## Roadmap de extract agent (pas MVP, pour contexte) nom de cet agent : XAVIER ? 
- Format XML pour les prompts d'audit (meilleure délimitation des blocs)
- PII masking via Presidio avant transmission
- Cloud partagé : transmission docs au notaire avec vue horodatée
- Sources docs : OneDrive (Graph API / Daniel Féau), Google Drive (MCP), 
  Dropbox lien public