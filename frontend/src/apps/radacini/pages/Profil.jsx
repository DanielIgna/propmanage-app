import React, { useEffect, useState } from "react";
import { toast } from "sonner";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { Input } from "../../../components/ui/input";
import { Textarea } from "../../../components/ui/textarea";
import { AlertTriangle } from "lucide-react";
import { radaciniApi, errMsg } from "../api";
import { useMember, useMeta } from "../hooks";
import { CheckGroup, COUNTY, Field, PageHeader, PageSkeleton, SelectField, toOpts } from "../shared";

export default function Profil() {
  const { member, loading: memberLoading, refresh } = useMember();
  const { meta, loading: metaLoading, error: metaError } = useMeta();
  const [form, setForm] = useState({ interests: [], locality: "", bio: "" });
  const [hydrated, setHydrated] = useState(false);
  const [saving, setSaving] = useState(false);

  // Completează formularul o singură dată, după încărcarea profilului existent.
  useEffect(() => {
    if (memberLoading || hydrated) return;
    if (member) {
      setForm({ interests: member.interests || [], locality: member.locality || "", bio: member.bio || "" });
    }
    setHydrated(true);
  }, [member, memberLoading, hydrated]);

  const upd = (k, v) => setForm((f) => ({ ...f, [k]: v }));

  const save = async (e) => {
    e.preventDefault();
    if (!form.interests.length) return toast.error("Alege cel puțin un interes.");
    if (!form.locality) return toast.error("Alege localitatea.");
    setSaving(true);
    try {
      await radaciniApi.saveMember({
        interests: form.interests,
        county: COUNTY,
        locality: form.locality,
        bio: form.bio.trim(),
      });
      toast.success("Profil salvat");
      refresh();
    } catch (err) {
      toast.error(errMsg(err, "Nu am putut salva profilul"));
    } finally {
      setSaving(false);
    }
  };

  if (memberLoading || metaLoading) return <PageSkeleton />;
  if (metaError || !meta) {
    return <EmptyState icon={AlertTriangle} title="Nu am putut încărca formularul" hint={errMsg(metaError)} testid="radacini-profil-error" />;
  }

  return (
    <div className="space-y-6 max-w-2xl">
      <PageHeader
        title={member ? "Profilul tău" : "Creează profilul"}
        subtitle="Cu ce te ocupi în Rădăcini și unde ești. Poți modifica oricând."
      />

      <form onSubmit={save} className={`${CARD} p-5 md:p-6 space-y-6`} data-testid="radacini-profil-form">
        <Field label="Ce vrei să faci în Rădăcini?" hint="Poți alege mai multe.">
          <CheckGroup
            name="interest"
            options={meta.interests}
            value={form.interests}
            onChange={(v) => upd("interests", v)}
            testid="radacini-profil-interest"
          />
        </Field>

        <div className="grid grid-cols-1 sm:grid-cols-2 gap-4">
          <Field label="Județ">
            <Input value={COUNTY} disabled />
          </Field>
          <Field label="Localitate" htmlFor="radacini-profil-localitate">
            <SelectField
              id="radacini-profil-localitate"
              value={form.locality || undefined}
              onValueChange={(v) => upd("locality", v)}
              options={toOpts(meta.localities)}
              placeholder="Alege localitatea"
              testid="radacini-profil-localitate"
            />
          </Field>
        </div>

        <Field label="Despre tine" htmlFor="radacini-profil-bio" hint={`${form.bio.length}/500`}>
          <Textarea
            id="radacini-profil-bio"
            rows={4}
            maxLength={500}
            value={form.bio}
            onChange={(e) => upd("bio", e.target.value)}
            placeholder="Câteva rânduri despre tine sau despre ce cauți (opțional)."
            data-testid="radacini-profil-bio"
          />
        </Field>

        <div className="flex justify-end">
          <DSButton type="submit" disabled={saving} data-testid="radacini-profil-salveaza">
            {saving ? "Se salvează…" : "Salvează profilul"}
          </DSButton>
        </div>
      </form>
    </div>
  );
}
