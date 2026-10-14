import React, { useCallback, useEffect, useRef, useState } from "react";
import { AlertTriangle } from "lucide-react";
import { DSButton, DSSkeleton, EmptyState } from "../../../../design-system";
import { asList, errMsg } from "../../api";

// Cerere GET cu stare {data, loading, error} și reîncărcare. Datele anterioare rămân vizibile cât timp se reîncarcă.
export function useFetch(fetcher, deps) {
  const [state, setState] = useState({ loading: true, error: null, data: null });
  const [tick, setTick] = useState(0);
  useEffect(() => {
    let alive = true;
    setState((s) => ({ ...s, loading: true, error: null }));
    fetcher()
      .then((data) => alive && setState({ loading: false, error: null, data }))
      .catch((error) => alive && setState({ loading: false, error, data: null }));
    return () => {
      alive = false;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps, tick]);
  const reload = useCallback(() => setTick((t) => t + 1), []);
  return { ...state, reload };
}

// Listă paginată. fetchPage(cursor) întoarce {items, total?, next_before?}.
//  - mod skip (implicit): cursor = numărul de rânduri deja încărcate; continuă cât timp nu s-a atins `total`.
//  - mod cursor ({cursor: true}): cursor = `next_before` din răspunsul anterior; continuă cât timp există.
// Se reia de la început când se schimbă `deps`. Rândurile sunt deduplicate după `id`.
export function usePaged(fetchPage, deps, { cursor = false, pageSize = 50 } = {}) {
  const fetchRef = useRef(fetchPage);
  fetchRef.current = fetchPage;
  const seq = useRef(0);
  const [st, setSt] = useState({ rows: [], total: null, meta: null, next: null, hasMore: false, loading: true, loadingMore: false, error: null, moreError: false });

  const load = useCallback(async (next) => {
    const more = next != null && next !== 0;
    const mine = ++seq.current;
    setSt((s) => ({ ...s, loading: !more, loadingMore: more }));
    try {
      const d = await fetchRef.current(more ? next : cursor ? undefined : 0);
      if (mine !== seq.current) return;
      const page = asList(d);
      const total = typeof d?.total === "number" ? d.total : null;
      const nextCursor = cursor ? d?.next_before ?? null : (more ? next : 0) + page.length;
      const hasMore = cursor ? !!nextCursor : page.length > 0 && (total != null ? nextCursor < total : page.length >= pageSize);
      setSt((s) => {
        const seen = more ? new Set(s.rows.map((r) => r.id)) : null;
        return {
          rows: more ? [...s.rows, ...page.filter((r) => !seen.has(r.id))] : page,
          total,
          meta: d,
          next: nextCursor,
          hasMore,
          loading: false,
          loadingMore: false,
          error: null,
          moreError: false,
        };
      });
    } catch (e) {
      if (mine !== seq.current) return;
      setSt((s) => (more ? { ...s, loading: false, loadingMore: false, moreError: true } : { ...s, rows: [], hasMore: false, loading: false, loadingMore: false, error: e }));
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [cursor, pageSize]);

  useEffect(() => {
    load(null);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [...deps]);

  const reload = useCallback(() => load(null), [load]);
  const loadMore = useCallback(() => load(st.next), [load, st.next]);
  return { ...st, reload, loadMore };
}

// Elimină parametrii goi / „all” din cerere.
export const clean = (params) =>
  Object.fromEntries(Object.entries(params).filter(([, v]) => v !== "" && v != null && v !== "all"));

export const ErrorBox = ({ title, error, onRetry, testid }) => (
  <EmptyState
    icon={AlertTriangle}
    title={title}
    hint={errMsg(error)}
    testid={testid}
    action={
      onRetry ? (
        <DSButton variant="secondary" onClick={onRetry} data-testid={`${testid}-retry`}>
          Reîncearcă
        </DSButton>
      ) : null
    }
  />
);

export const TabSkeleton = () => <DSSkeleton kpis={4} blocks={1} />;

export const firstName = (name) => (name || "").trim().split(/\s+/)[0] || "—";

// Contor dintr-un rând: acceptă `<cheie>_count`, `counts.<cheie>`, un număr sau o listă.
export const pickCount = (row, key) => {
  const v = row?.[`${key}_count`] ?? row?.counts?.[key] ?? row?.[key];
  if (Array.isArray(v)) return v.length;
  return Number.isFinite(Number(v)) ? Number(v) : 0;
};

// Perechi [cheie, valoare] în ordinea dată; cheile necunoscute vin la sfârșit. Cheile din `order` lipsă au 0.
export const orderedEntries = (obj, order = []) => {
  const src = obj || {};
  const known = order.map((k) => [k, Number(src[k]) || 0]);
  const extra = Object.keys(src)
    .filter((k) => !order.includes(k))
    .map((k) => [k, Number(src[k]) || 0]);
  return [...known, ...extra];
};

export const nf = (v) => Number(v || 0).toLocaleString("ro-RO");

// ── Evenimente (activity_events, event_type = "radacini.<tip>") ─────────────

const EVENT_LABELS = {
  member_updated: "Profil de membru actualizat",
  parcel_submitted: "Teren trimis spre verificare",
  parcel_verified: "Teren verificat",
  request_created: "Cerere de teren trimisă",
  request_message: "Mesaj în negocierea unei cereri",
  request_countered: "Contrapropunere la o cerere",
  request_accepted: "Cerere acceptată",
  request_declined: "Cerere refuzată",
  request_withdrawn: "Cerere retrasă",
  agreement_edited: "Acord modificat",
  agreement_proposed: "Acord trimis spre semnare",
  agreement_signed: "Acord semnat",
  agreement_completed: "Acord finalizat",
  agreement_cancelled: "Acord anulat",
  project_created: "Proiect creat",
  project_completed: "Proiect finalizat",
  project_member_added: "Membru adăugat în proiect",
  project_member_removed: "Membru scos din proiect",
  project_member_role_changed: "Rol schimbat în proiect",
  project_crop_added: "Cultură adăugată în plan",
  project_crop_updated: "Cultură modificată în plan",
  project_crop_removed: "Cultură ștearsă din plan",
  activity_created: "Activitate programată",
  activity_updated: "Activitate modificată",
  activity_joined: "Înscriere la activitate",
  activity_left: "Retragere de la activitate",
  activity_done: "Activitate încheiată",
  activity_cancelled: "Activitate anulată",
  contribution_logged: "Contribuție înregistrată",
  contribution_reviewed: "Contribuție evaluată",
  harvest_recorded: "Recoltă înregistrată",
  harvest_confirmed: "Recoltă confirmată",
  allocation_created: "Recoltă alocată",
  allocation_removed: "Alocare ștearsă",
  allocation_received: "Alocare primită",
  listing_created: "Anunț publicat",
  listing_updated: "Anunț modificat",
  listing_closed: "Anunț închis",
  reservation_requested: "Rezervare cerută",
  reservation_confirmed: "Rezervare confirmată",
  reservation_declined: "Rezervare refuzată",
  reservation_cancelled: "Rezervare anulată",
  reservation_picked_up: "Rezervare ridicată",
  reservation_no_show: "Neprezentare la ridicare",
  reservation_rated: "Rezervare evaluată",
  deletion_requested: "Cerere de ștergere a datelor",
  deletion_resolved: "Cerere de ștergere rezolvată",
};

const stripNs = (t) => String(t || "").replace(/^radacini\./, "");
export const eventLabel = (type) => EVENT_LABELS[stripNs(type)] || type || "—";

export const EVENT_GROUPS = [
  { id: "all", label: "Toate evenimentele" },
  { id: "terenuri", label: "Terenuri", prefixes: ["parcel"] },
  { id: "cereri", label: "Cereri", prefixes: ["request"] },
  { id: "acorduri", label: "Acorduri", prefixes: ["agreement"] },
  { id: "proiecte", label: "Proiecte", prefixes: ["project", "activity", "contribution"] },
  { id: "recolta", label: "Recoltă", prefixes: ["harvest", "allocation"] },
  { id: "piata", label: "Piață și rezervări", prefixes: ["listing", "reservation"] },
  { id: "membri", label: "Membri și GDPR", prefixes: ["member", "deletion"] },
];

export const eventInGroup = (type, groupId) => {
  if (groupId === "all") return true;
  const g = EVENT_GROUPS.find((x) => x.id === groupId);
  const head = stripNs(type).split(/[._]/)[0];
  return !!g?.prefixes?.includes(head);
};

// ── Jurnal de audit (acțiuni „radacini.*”) ───────────────────────────────────

const AUDIT_LABELS = {
  "parcel.approve": "Teren aprobat",
  "parcel.reject": "Teren respins",
  "staff.add": "Membru de personal adăugat",
  "staff.remove": "Acces de personal eliminat",
  "listing.close": "Anunț închis de administrator",
  "deletion.resolve": "Cerere GDPR rezolvată",
  "test_accounts.ensure": "Conturi de test create",
  "test_accounts.seed": "Scenariu demo încărcat",
  "test_accounts.reset": "Scenariu demo șters",
};
export const auditLabel = (action) => AUDIT_LABELS[stripNs(action)] || action || "—";

const TARGET_LABELS = {
  parcel: "Teren",
  staff: "Personal",
  listing: "Anunț",
  deletion_request: "Cerere GDPR",
  test_accounts: "Conturi de test",
};
// „radacini_listing” + id → „Anunț · 3fa9c1d2”.
export const auditTarget = (type, id) => {
  const key = String(type || "").replace(/^radacini_/, "");
  const parts = [TARGET_LABELS[key] || key, id ? String(id).slice(0, 8) : ""].filter(Boolean);
  return parts.join(" · ") || "—";
};

// Cererile GDPR: „pending”/„open” = deschisă.
export const isOpenDeletion = (status) => status === "pending" || status === "open";
export const DELETION_STATUS = {
  open: { label: "Deschisă", cls: "bg-amber-50 text-amber-700 dark:bg-amber-500/15 dark:text-amber-300" },
  done: { label: "Finalizată", cls: "bg-emerald-50 text-emerald-700 dark:bg-emerald-500/15 dark:text-emerald-300" },
  rejected: { label: "Respinsă", cls: "bg-rose-50 text-rose-700 dark:bg-rose-500/15 dark:text-rose-300" },
};
export const deletionStatusDef = (status) =>
  DELETION_STATUS[isOpenDeletion(status) ? "open" : status] || { label: status || "—", cls: "bg-slate-100 text-slate-600" };
