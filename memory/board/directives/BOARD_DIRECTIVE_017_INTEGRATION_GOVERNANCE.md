# BOARD DIRECTIVE 017 — Integration Governance Mode
Data: Iun 2026. Orice integrare externă = asset de platformă gestionat.
Nicio integrare fără health monitoring, validare configurare și documentație operațională.

## INTEGRATION REGISTRY (centralizat, obligatoriu per integrare)
Name · Purpose · Owner · Status · Environment (Dev/Staging/Prod) · API Key Status ·
Domain Status (dacă e cazul) · Webhook Status · Last Successful Check · Last Failure ·
Documentation Link.

## HEALTH CHECK
Fiecare integrare are health check periodic. Stări posibile:
Configured · Operational · Warning · Action Required · Offline.
CEO Dashboard afișează sănătatea integrărilor.

## SELF DIAGNOSTICS (înainte de a cere intervenție manuală, verifică automat)
API keys lipsă · credențiale invalide · status verificare DNS · webhooks lipsă ·
env vars lipsă · secrete expirate · rate limit · conectivitate.
Raportează ÎNTOTDEAUNA cauza exactă (root cause).

## MANUAL TASKS
Dacă e nevoie de intervenție manuală → checklist precis:
Ce lipsește · Unde se configurează · Valorile exacte de copiat · Rezultatul așteptat.
Nu cere Board-ului să investigheze manual ce poate identifica sistemul automat.

## BOARD PRINCIPLE
Integrările sunt infrastructură de platformă — monitorizate, validate și documentate
ca orice sistem critic.
