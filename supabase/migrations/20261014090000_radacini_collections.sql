-- Rădăcini: colecțiile `radacini_*` (JSONB în schema `app`) + indexuri.
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

-- 2. Indexuri btree pe expresii ------------------------------------------------------------------------------
-- Notă: pgmongo traduce egalitatea (`{"owner_user_id": x}`) în `data @> ...`, servită de GIN-ul existent; aceste
-- btree-uri ajută interogările SQL directe / predicatele `data->>'câmp'` (rapoarte, consola admin, optimizări
-- viitoare ale pgmongo). Verifică cu EXPLAIN înainte să te bazezi pe ele; costă puțin la scriere.
-- Câmpurile din `radacini_location_access_log` urmează numele folosite de export (parcel_id, owner_user_id, user_id).

-- parcels
create index if not exists radacini_parcels_owner_user_id_idx on app.radacini_parcels ((data->>'owner_user_id'));
create index if not exists radacini_parcels_status_locality_idx on app.radacini_parcels ((data->>'status'), (data->>'locality'));

-- land_requests
create index if not exists radacini_land_requests_parcel_id_idx on app.radacini_land_requests ((data->>'parcel_id'));
create index if not exists radacini_land_requests_owner_user_id_idx on app.radacini_land_requests ((data->>'owner_user_id'));
create index if not exists radacini_land_requests_requester_user_id_idx on app.radacini_land_requests ((data->>'requester_user_id'));
create index if not exists radacini_land_requests_status_idx on app.radacini_land_requests ((data->>'status'));

-- request_messages
create index if not exists radacini_request_messages_request_id_idx on app.radacini_request_messages ((data->>'request_id'));

-- agreements
create index if not exists radacini_agreements_parcel_id_idx on app.radacini_agreements ((data->>'parcel_id'));
create index if not exists radacini_agreements_request_id_idx on app.radacini_agreements ((data->>'request_id'));
create index if not exists radacini_agreements_status_idx on app.radacini_agreements ((data->>'status'));

-- projects
create index if not exists radacini_projects_parcel_id_idx on app.radacini_projects ((data->>'parcel_id'));
create index if not exists radacini_projects_status_idx on app.radacini_projects ((data->>'status'));

-- crop_plans
create index if not exists radacini_crop_plans_project_id_idx on app.radacini_crop_plans ((data->>'project_id'));

-- activities
create index if not exists radacini_activities_project_id_idx on app.radacini_activities ((data->>'project_id'));

-- contributions
create index if not exists radacini_contributions_project_id_idx on app.radacini_contributions ((data->>'project_id'));
create index if not exists radacini_contributions_member_user_id_idx on app.radacini_contributions ((data->>'member_user_id'));
create index if not exists radacini_contributions_corrects_id_idx on app.radacini_contributions ((data->>'corrects_id'));

-- harvests
create index if not exists radacini_harvests_project_id_idx on app.radacini_harvests ((data->>'project_id'));
create index if not exists radacini_harvests_status_idx on app.radacini_harvests ((data->>'status'));

-- allocations
create index if not exists radacini_allocations_harvest_id_idx on app.radacini_allocations ((data->>'harvest_id'));
create index if not exists radacini_allocations_project_id_idx on app.radacini_allocations ((data->>'project_id'));
create index if not exists radacini_allocations_member_user_id_idx on app.radacini_allocations ((data->>'member_user_id'));

-- listings
create index if not exists radacini_listings_seller_user_id_idx on app.radacini_listings ((data->>'seller_user_id'));
create index if not exists radacini_listings_status_idx on app.radacini_listings ((data->>'status'));
create index if not exists radacini_listings_project_id_idx on app.radacini_listings ((data->>'project_id'));

-- reservations
create index if not exists radacini_reservations_listing_id_idx on app.radacini_reservations ((data->>'listing_id'));
create index if not exists radacini_reservations_buyer_user_id_idx on app.radacini_reservations ((data->>'buyer_user_id'));
create index if not exists radacini_reservations_seller_user_id_idx on app.radacini_reservations ((data->>'seller_user_id'));
create index if not exists radacini_reservations_status_idx on app.radacini_reservations ((data->>'status'));

-- location_access_log
create index if not exists radacini_location_access_log_parcel_id_idx on app.radacini_location_access_log ((data->>'parcel_id'));
create index if not exists radacini_location_access_log_owner_user_id_idx on app.radacini_location_access_log ((data->>'owner_user_id'));
create index if not exists radacini_location_access_log_user_id_idx on app.radacini_location_access_log ((data->>'user_id'));

-- deletion_requests
create index if not exists radacini_deletion_requests_user_id_idx on app.radacini_deletion_requests ((data->>'user_id'));

-- 3. Unicitate (apără invarianții și la scrieri concurente) --------------------------------------------------
-- Fiecare index e creat izolat: dacă există deja dubluri în date, se emite un WARNING și migrarea continuă
-- (curăță dublurile și rulează din nou blocul respectiv).
do $$
declare
  stmt text;
begin
  foreach stmt in array array[
    -- un singur profil de membru / membru de personal per utilizator
    'create unique index if not exists radacini_members_user_id_uidx on app.radacini_members ((data->>''user_id''))',
    'create unique index if not exists radacini_staff_user_id_uidx on app.radacini_staff ((data->>''user_id''))',
    -- un singur proiect per acord semnat (parțial: proiectele fără acord nu intră în index)
    'create unique index if not exists radacini_projects_agreement_id_uidx on app.radacini_projects ((data->>''agreement_id'')) where data ? ''agreement_id''',
    -- un singur document de statistici per vânzător
    'create unique index if not exists radacini_seller_stats_seller_user_id_uidx on app.radacini_seller_stats ((data->>''seller_user_id''))',
    -- o singură cerere de ștergere „pending” per utilizator
    'create unique index if not exists radacini_deletion_requests_pending_uidx on app.radacini_deletion_requests ((data->>''user_id'')) where data->>''status'' = ''pending'''
  ] loop
    begin
      execute stmt;
    exception when unique_violation then
      raise warning 'radacini: index unic omis (dubluri existente): %', stmt;
    end;
  end loop;
end;
$$;
