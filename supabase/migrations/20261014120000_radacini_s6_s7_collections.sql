-- Rădăcini S6/S7: colecții noi (JSONB în schema `app`), după convenția din 20261014090000_radacini_collections.sql.
-- Doar crearea tabelelor (RLS activ fără politici + GIN `jsonb_path_ops` prin app.create_collection); fără indexuri btree.
-- Idempotentă; echivalentă cu ce creează pgmongo la prima scriere.
do $$
declare
  c text;
begin
  foreach c in array array[
    'radacini_communities',
    'radacini_community_members',
    'radacini_community_posts',
    'radacini_consents',
    'radacini_decisions',
    'radacini_disputes',
    'radacini_households',
    'radacini_photos',
    'radacini_project_needs',
    'radacini_providers',
    'radacini_service_requests'
  ] loop
    perform app.create_collection(c);
  end loop;
end;
$$;
