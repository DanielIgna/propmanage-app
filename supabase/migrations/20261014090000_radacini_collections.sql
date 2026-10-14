-- Rădăcini: colecțiile `radacini_*` (JSONB în schema `app`).
-- Decizie 2026-10-14 (fondator): doar crearea oficială a tabelelor, FĂRĂ indexuri btree suplimentare —
-- pgmongo filtrează prin `data @> …`, servit de GIN-ul creat de app.create_collection; btree-urile n-ar fi folosite.
-- NU se aplică automat: rulează manual, cu aprobare (vezi docs/radacini/PLAN.md, Runda 2).
-- Urmează convențiile din 20261009120000_app_collections.sql: tabel per colecție (`id text`, `data jsonb`),
-- RLS activ fără politici, GIN `jsonb_path_ops` creat de `app.create_collection`.
-- Idempotentă: `create ... if not exists`; poate fi rulată din nou.

-- 1. Colecții ------------------------------------------------------------------------------------------------
do $$
declare
  c text;
begin
  foreach c in array array[
    'radacini_activities',
    'radacini_agreements',
    'radacini_allocations',
    'radacini_contributions',
    'radacini_crop_plans',
    'radacini_deletion_requests',
    'radacini_harvests',
    'radacini_land_requests',
    'radacini_listings',
    'radacini_location_access_log',
    'radacini_members',
    'radacini_parcels',
    'radacini_projects',
    'radacini_request_messages',
    'radacini_reservations',
    'radacini_seller_stats',
    'radacini_staff'
  ] loop
    perform app.create_collection(c);
  end loop;
end;
$$;
