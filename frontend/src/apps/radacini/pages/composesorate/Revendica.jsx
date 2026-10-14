import React, { useEffect, useState } from "react";
import { Link, useNavigate, useSearchParams } from "react-router-dom";
import { toast } from "sonner";
import { CARD, DSButton } from "../../../../design-system";
import { Input } from "../../../../components/ui/input";
import { Textarea } from "../../../../components/ui/textarea";
import { asList, errMsg } from "../../api";
import { assocList, claimCreate } from "../../api_s9";
import { Field, PageHeader, SelectField } from "../../shared";

const RELATIONS = ["Fiu/fiică", "Soț/soție", "Nepot", "Frate/soră", "Altă rudenie"].map((l) => ({ id: l, label: l }));

export default function Revendica() {
  const nav = useNavigate();
  const [sp] = useSearchParams();
  const [list, setList] = useState([]);
  const [q, setQ] = useState("");
  const [assocId, setAssocId] = useState(sp.get("assoc") || "");
  const [kind, setKind] = useState("self");
  const [f, setF] = useState({ member_code: "", name_on_record: "", relation: RELATIONS[0].id, note: "" });
  const [busy, setBusy] = useState(false);

  useEffect(() => {
    const t = setTimeout(() => assocList(q.trim() ? { q: q.trim() } : undefined).then((d) => setList(asList(d))).catch(() => {}), 250);
    return () => clearTimeout(t);
  }, [q]);

  const submit = async (e) => {
    e.preventDefault();
    if (!assocId) return toast.error("Alege asociația.");
    if (!f.member_code.trim() && !f.name_on_record.trim()) return toast.error("Indică codul din registru sau numele cum apare în registru.");
    if (kind === "heir" && f.note.trim().length < 10) return toast.error("Descrie pe scurt legătura (cine a fost titularul, ce acte ai).");
    setBusy(true);
    try {
      await claimCreate(assocId, {
        kind, member_code: f.member_code.trim() || undefined, name_on_record: f.name_on_record.trim() || undefined,
        relation: kind === "heir" ? f.relation : undefined, note: f.note.trim(), document_ids: [],
      });
      toast.success("Revendicare trimisă. Conducerea o va analiza; poate cere acte ulterior.");
      nav(`/radacini/composesorate/${assocId}?tab=cota`);
    } catch (err) {
      toast.error(errMsg(err, "Nu am putut trimite revendicarea"));
    } finally {
      setBusy(false);
    }
  };
  const set = (k) => (e) => setF({ ...f, [k]: e.target.value });

  return (
    <div className="space-y-5 max-w-2xl" data-testid="revendica-page">
      <PageHeader title="Revendică / Sunt moștenitor" subtitle="Leagă-ți contul de rândul tău din registrul asociației." actions={<Link to="/radacini/composesorate/ghid" className="text-sm underline font-semibold">Ghid</Link>} />
      <form onSubmit={submit} className={`${CARD} p-5 space-y-4`}>
        <Field label="Caută asociația"><Input value={q} onChange={(e) => setQ(e.target.value)} placeholder="Nume sau localitate" /></Field>
        <Field label="Asociația"><SelectField value={assocId} onValueChange={setAssocId} placeholder="Alege" options={list.map((a) => ({ id: a.id, label: `${a.name} (${(a.localities || []).join(", ")})` }))} testid="revendica-assoc" /></Field>
        <Field label="Cine ești?">
          <SelectField value={kind} onValueChange={setKind} options={[{ id: "self", label: "Sunt eu (titularul din registru)" }, { id: "heir", label: "Sunt moștenitor" }]} testid="revendica-kind" />
        </Field>
        <Field label="Codul din registru (dacă îl știi)"><Input value={f.member_code} onChange={set("member_code")} placeholder="M001" /></Field>
        <Field label="Numele cum apare în registru"><Input value={f.name_on_record} onChange={set("name_on_record")} /></Field>
        {kind === "heir" && <Field label="Relația cu titularul"><SelectField value={f.relation} onValueChange={(v) => setF({ ...f, relation: v })} options={RELATIONS} /></Field>}
        <Field label="Mențiuni" hint="Actele (certificat de moștenitor, act de identitate) vor fi cerute de conducere după analiza solicitării."><Textarea value={f.note} onChange={set("note")} /></Field>
        <DSButton type="submit" disabled={busy} data-testid="revendica-submit">Trimite revendicarea</DSButton>
      </form>
    </div>
  );
}
