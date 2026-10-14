-- Rădăcini S9 (Composesorate): colecții noi. Doar colecțiile (RLS + GIN prin app.create_collection), fără indexuri btree.
do $$
declare
  c text;
begin
  foreach c in array array[
    'radacini_associations',
    'radacini_assoc_members',
    'radacini_assoc_claims',
    'radacini_assoc_audit',
    'radacini_assoc_documents',
    'radacini_assoc_doc_access',
    'radacini_assoc_meetings',
    'radacini_assoc_mandates',
    'radacini_assoc_petitions',
    'radacini_assoc_requests',
    'radacini_assoc_obligation_evidence',
    'radacini_assoc_finance_years',
    'radacini_assoc_distributions'
  ] loop
    perform app.create_collection(c);
  end loop;
end;
$$;
