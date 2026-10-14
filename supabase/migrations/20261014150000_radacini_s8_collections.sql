-- Rădăcini S8: termeni proprii (documente + acceptări) și onboarding. Doar colecțiile, fără indexuri btree.
do $$
declare
  c text;
begin
  foreach c in array array[
    'radacini_legal_documents',
    'radacini_legal_acceptances',
    'radacini_onboarding'
  ] loop
    perform app.create_collection(c);
  end loop;
end;
$$;
