---
name: propmanage-db
description: PropManage data layer on Supabase — pgmongo (Motor-compatible facade over Postgres JSONB), schema app, indexes, migrations, storage, auth/roles. Use when touching backend queries, schema, migrations, Supabase Auth/Storage, or diagnosing slow/incorrect DB results.
---

# Date în PropManage

- Codul folosește API-ul Motor (`db.<colecție>.find/update_one/aggregate…`); `backend/pgmongo.py` îl execută pe Postgres: SQL prefiltrează (containment GIN, intervale, `$in`, sortare), apoi mongomock aplică semantica Mongo exactă. Scrierile: tranzacție + `FOR UPDATE` + diff.
- Tabele: `app.<colecție>` (`id` text = Mongo `_id`, `data jsonb`, `created_at`, `updated_at`), create automat la prima scriere. Schema `app` NU e expusă în Data API; RLS activ fără politici (doar backend-ul accesează).
- Performanță: proiecțiile/agregările aduc doar câmpurile necesare; `$in` lung citește câmpul o dată. Nu sorta pe câmpuri de tip listă (diferă de Mongo).
- Indexuri unice: `create_index(keys, unique=True[, partialFilterExpression=…])` → index unic Postgres; `DuplicateKeyError` la insert/update.
- `db.py`: `PgDatabase(SUPABASE_DB_URL, schema=PG_SCHEMA or "app")`. Test izolat: `PG_SCHEMA=app_test`.
- Migrări SQL în `supabase/migrations/` (+ MCP `apply_migration`); după DDL rulează `get_advisors`. Orice tabel nou în `public`: RLS + politici explicite.
- Fișiere: `storage_client.put_object/get_object` → bucket privat `propmanage-files` (chei non-ASCII escapate).
- Auth: Supabase Auth (`supabase_auth.py`); roluri DOAR din `users.role`; `ADMIN_EMAILS` promovează/retrogradează adminii la login. Cheia secretă niciodată în frontend.
- Import date: `backend/supabase_migration/import_mongo_dump.py <dump.tar.gz>` (idempotent).
