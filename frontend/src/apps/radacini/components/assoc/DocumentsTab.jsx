import React, { useCallback, useEffect, useMemo, useState } from "react";
import { toast } from "sonner";
import { Copy, Download, FileText, History, Upload } from "lucide-react";
import { DSButton } from "../../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogFooter, DialogHeader, DialogTitle } from "../../../../components/ui/dialog";
import { Input } from "../../../../components/ui/input";
import { errMsg } from "../../api";
import { documentAccessLog, documentFileUrl, documentUpload, documentsList } from "../../api_s9";
import { Field, SelectField, fmtDate, fmtDateTime } from "../../shared";

export const DOC_TYPES = [
  { id: "statute", label: "Statut" },
  { id: "aga_minutes", label: "PV AGA" },
  { id: "council_minutes", label: "PV CA" },
  { id: "balance", label: "Bilanț" },
  { id: "censor_report", label: "Raport cenzori" },
  { id: "contract", label: "Contract" },
  { id: "land_registry", label: "CF" },
  { id: "resolution", label: "Hotărâre" },
  { id: "convocation", label: "Convocator" },
  { id: "other", label: "Altul" },
];
const typeLabel = (t) => DOC_TYPES.find((x) => x.id === t)?.label || t || "Altul";
const VIS = [
  { id: "members", label: "Toți membrii" },
  { id: "council", label: "Doar consiliul (CA)" },
];
const UPLOAD_ROLES = ["council", "operator", "manager"];
const LOG_ROLES = ["council", "censor", "manager", "operator"];

export default function DocumentsTab({ assoc, access, reload }) {
  const assocId = assoc?.id;
  const role = access?.role;
  const [docs, setDocs] = useState(null);
  const [error, setError] = useState("");
  const [upOpen, setUpOpen] = useState(false);
  const [logDoc, setLogDoc] = useState(null);

  const load = useCallback(async () => {
    setError("");
    try {
      const r = await documentsList(assocId);
      setDocs(Array.isArray(r) ? r : r?.items || r?.documents || []);
    } catch (e) {
      setError(errMsg(e, "Nu am putut încărca documentele"));
      setDocs([]);
    }
  }, [assocId]);
  useEffect(() => {
    if (assocId) load();
  }, [assocId, load]);

  const grouped = useMemo(() => {
    const g = {};
    (docs || []).forEach((d) => (g[d.type || "other"] ||= []).push(d));
    Object.values(g).forEach((l) => l.sort((a, b) => String(b.date || "").localeCompare(String(a.date || ""))));
    return DOC_TYPES.filter((t) => g[t.id]).map((t) => [t, g[t.id]]);
  }, [docs]);

  const byId = useMemo(() => Object.fromEntries((docs || []).map((d) => [d.id, d])), [docs]);
  const chain = (d) => {
    const out = [];
    let cur = d;
    while (cur?.replaces_id && byId[cur.replaces_id] && out.length < 20) {
      cur = byId[cur.replaces_id];
      out.push(cur);
    }
    return out;
  };
  const replacedIds = useMemo(() => new Set((docs || []).map((d) => d.replaces_id).filter(Boolean)), [docs]);

  const download = async (d) => {
    try {
      const url = await documentFileUrl(d.id);
      if (url) window.open(url, "_blank", "noopener");
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut deschide documentul"));
    }
  };
  const copy = async (h) => {
    try {
      await navigator.clipboard.writeText(h);
      toast.success("SHA-256 copiat");
    } catch {
      toast.error("Nu am putut copia");
    }
  };

  return (
    <div className="space-y-4" data-testid="radacini-docs-tab">
      <div className="flex flex-wrap items-center justify-between gap-2">
        <p className="text-sm text-slate-600 dark:text-slate-300 min-w-0">
          Documentele nu se șterg: o versiune nouă o înlocuiește pe cea veche, iar amprenta SHA-256 dovedește că fișierul nu a fost modificat.
        </p>
        {UPLOAD_ROLES.includes(role) && (
          <DSButton icon={Upload} onClick={() => setUpOpen(true)} data-testid="radacini-docs-upload-btn">
            Încarcă document
          </DSButton>
        )}
      </div>

      {docs === null && <p className="text-sm text-slate-500" data-testid="radacini-docs-loading">Se încarcă…</p>}
      {error && <p className="text-sm text-red-600" data-testid="radacini-docs-error">{error}</p>}
      {docs && !docs.length && !error && (
        <p className="text-sm text-slate-500" data-testid="radacini-docs-empty">Nu există documente publicate încă.</p>
      )}

      {grouped.map(([t, list]) => (
        <section key={t.id} className="space-y-2" data-testid={`radacini-docs-group-${t.id}`}>
          <h3 className="text-sm font-bold uppercase tracking-wide text-slate-500">{t.label}</h3>
          <ul className="space-y-2">
            {list.map((d) => {
              const prev = chain(d);
              return (
                <li key={d.id} className="rounded-lg border border-slate-200 dark:border-slate-700 p-3 space-y-2" data-testid={`radacini-doc-${d.id}`}>
                  <div className="flex flex-wrap items-start justify-between gap-2">
                    <div className="min-w-0">
                      <p className="font-semibold break-words flex items-center gap-1.5">
                        <FileText className="h-4 w-4 shrink-0 text-slate-400" />
                        {d.title}
                      </p>
                      <p className="text-xs text-slate-500">
                        {typeLabel(d.type)} · data {fmtDate(d.date)} · publicat {fmtDate(d.published_at || d.created_at)}
                        {d.version ? ` · v${d.version}` : ""}
                        {d.visibility === "council" ? " · doar CA" : ""}
                        {replacedIds.has(d.id) ? " · înlocuit de o versiune mai nouă" : ""}
                      </p>
                    </div>
                    <div className="flex flex-wrap gap-2">
                      <DSButton variant="secondary" icon={Download} onClick={() => download(d)} data-testid={`radacini-doc-download-${d.id}`}>
                        Descarcă
                      </DSButton>
                      {LOG_ROLES.includes(role) && (
                        <DSButton variant="ghost" icon={History} onClick={() => setLogDoc(d)} data-testid={`radacini-doc-log-${d.id}`}>
                          Jurnal acces
                        </DSButton>
                      )}
                    </div>
                  </div>
                  {d.sha256 && (
                    <p className="text-xs font-mono text-slate-500 flex items-center gap-1.5" title={d.sha256}>
                      SHA-256: {d.sha256.slice(0, 12)}…
                      <button type="button" onClick={() => copy(d.sha256)} className="p-1 rounded hover:bg-slate-100 dark:hover:bg-slate-800" aria-label="Copiază SHA-256" data-testid={`radacini-doc-copy-${d.id}`}>
                        <Copy className="h-3.5 w-3.5" />
                      </button>
                    </p>
                  )}
                  {prev.length > 0 && (
                    <p className="text-xs text-slate-500" data-testid={`radacini-doc-versions-${d.id}`}>
                      Versiuni anterioare: {prev.map((p) => `${p.title} (${fmtDate(p.date)})`).join(" ← ")}
                    </p>
                  )}
                </li>
              );
            })}
          </ul>
        </section>
      ))}

      {upOpen && (
        <UploadDialog assocId={assocId} docs={docs || []} onClose={() => setUpOpen(false)} onDone={() => { setUpOpen(false); load(); reload?.(); }} />
      )}
      {logDoc && <LogDialog doc={logDoc} onClose={() => setLogDoc(null)} />}
    </div>
  );
}

function UploadDialog({ assocId, docs, onClose, onDone }) {
  const [f, setF] = useState({ type: "other", title: "", date: "", visibility: "members", replaces_id: "none" });
  const [file, setFile] = useState(null);
  const [busy, setBusy] = useState(false);
  const set = (k) => (v) => setF((p) => ({ ...p, [k]: v }));
  const submit = async () => {
    if (!file) return toast.error("Alege un fișier (PDF sau imagine, max. 10 MB).");
    if (!f.title.trim()) return toast.error("Completează titlul.");
    if (!f.date) return toast.error("Completează data documentului.");
    const fd = new FormData();
    fd.append("file", file);
    fd.append("type", f.type);
    fd.append("title", f.title.trim());
    fd.append("date", f.date);
    fd.append("visibility", f.visibility);
    if (f.replaces_id !== "none") fd.append("replaces_id", f.replaces_id);
    setBusy(true);
    try {
      await documentUpload(assocId, fd);
      toast.success("Document încărcat");
      onDone();
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut încărca documentul"));
    } finally {
      setBusy(false);
    }
  };
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-docs-upload-dialog" className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Încarcă document</DialogTitle>
          <DialogDescription>PDF, JPEG, PNG sau WebP, până la 10 MB. Documentul nu poate fi șters ulterior.</DialogDescription>
        </DialogHeader>
        <div className="space-y-3">
          <Field label="Tip" htmlFor="doc-type"><SelectField id="doc-type" value={f.type} onValueChange={set("type")} options={DOC_TYPES} testid="radacini-docs-type" /></Field>
          <Field label="Titlu" htmlFor="doc-title"><Input id="doc-title" value={f.title} onChange={(e) => set("title")(e.target.value)} data-testid="radacini-docs-title" /></Field>
          <Field label="Data documentului" htmlFor="doc-date"><Input id="doc-date" type="date" value={f.date} onChange={(e) => set("date")(e.target.value)} data-testid="radacini-docs-date" /></Field>
          <Field label="Vizibilitate" htmlFor="doc-vis"><SelectField id="doc-vis" value={f.visibility} onValueChange={set("visibility")} options={VIS} testid="radacini-docs-visibility" /></Field>
          <Field label="Înlocuiește o versiune" htmlFor="doc-repl" hint="Opțional: versiunea veche rămâne păstrată în istoric.">
            <SelectField id="doc-repl" value={f.replaces_id} onValueChange={set("replaces_id")} testid="radacini-docs-replaces"
              options={[{ id: "none", label: "— document nou —" }, ...docs.map((d) => ({ id: d.id, label: `${d.title} (${fmtDate(d.date)})` }))]} />
          </Field>
          <Field label="Fișier" htmlFor="doc-file">
            <Input id="doc-file" type="file" accept="application/pdf,image/jpeg,image/png,image/webp" onChange={(e) => setFile(e.target.files?.[0] || null)} data-testid="radacini-docs-file" />
          </Field>
        </div>
        <DialogFooter>
          <DSButton variant="secondary" onClick={onClose}>Renunță</DSButton>
          <DSButton onClick={submit} disabled={busy} data-testid="radacini-docs-upload-submit">{busy ? "Se încarcă…" : "Încarcă"}</DSButton>
        </DialogFooter>
      </DialogContent>
    </Dialog>
  );
}

function LogDialog({ doc, onClose }) {
  const [rows, setRows] = useState(null);
  const [err, setErr] = useState("");
  useEffect(() => {
    documentAccessLog(doc.id)
      .then((r) => setRows(Array.isArray(r) ? r : r?.items || r?.log || []))
      .catch((e) => { setErr(errMsg(e, "Nu am putut încărca jurnalul")); setRows([]); });
  }, [doc.id]);
  return (
    <Dialog open onOpenChange={(o) => !o && onClose()}>
      <DialogContent data-testid="radacini-docs-log-dialog" className="max-h-[90vh] overflow-y-auto">
        <DialogHeader>
          <DialogTitle>Jurnal de acces</DialogTitle>
          <DialogDescription className="break-words">{doc.title}</DialogDescription>
        </DialogHeader>
        {rows === null && <p className="text-sm text-slate-500">Se încarcă…</p>}
        {err && <p className="text-sm text-red-600">{err}</p>}
        {rows && !rows.length && !err && <p className="text-sm text-slate-500">Nicio descărcare înregistrată.</p>}
        <ul className="space-y-1 text-sm">
          {(rows || []).map((r, i) => (
            <li key={r.id || i} className="flex flex-wrap justify-between gap-2 border-b border-slate-100 dark:border-slate-800 py-1">
              <span className="break-words">{r.user_name || r.user_id || "Utilizator"}{r.role ? ` (${r.role})` : ""}</span>
              <span className="text-xs text-slate-500">{fmtDateTime(r.at || r.accessed_at)}</span>
            </li>
          ))}
        </ul>
      </DialogContent>
    </Dialog>
  );
}
