import React, { useState } from "react";
import { toast } from "sonner";
import { LocateFixed } from "lucide-react";
import { Field, SelectField, toOpts } from "../shared";

const RADII = [5, 10, 25, 50].map((r) => ({ id: String(r), label: `${r} km` }));
const NONE = "none";

const round4 = (n) => Math.round(n * 1e4) / 1e4;

// Filtru de distanță. value = {mode:"off"|"me"|"locality", lat?, lng?, locality?, radius:number}
// onChange(value). nearParams(value) -> {near, radius_km} (lângă mine) sau {near_locality, radius_km}.
// allowMe / allowLocality: GET /parcels acceptă doar near=lat,lng; GET /listings doar near_locality.
export const NEAR_OFF = { mode: "off", radius: 25 };

export const nearParams = (v) => {
  if (!v || v.mode === "off") return {};
  if (v.mode === "me" && Number.isFinite(v.lat)) return { near: `${v.lat},${v.lng}`, radius_km: v.radius };
  if (v.mode === "locality" && v.locality) return { near_locality: v.locality, radius_km: v.radius };
  return {};
};

export default function NearFilter({ value = NEAR_OFF, onChange, localities = [], allowMe = true, allowLocality = true }) {
  const [locating, setLocating] = useState(false);
  const set = (patch) => onChange({ ...value, ...patch });

  const useMyLocation = () => {
    if (typeof navigator === "undefined" || !navigator.geolocation) return toast.error("Browserul nu oferă localizare.");
    setLocating(true);
    navigator.geolocation.getCurrentPosition(
      (pos) => {
        setLocating(false);
        onChange({ ...value, mode: "me", lat: round4(pos.coords.latitude), lng: round4(pos.coords.longitude), locality: undefined });
      },
      () => {
        setLocating(false);
        toast.error("Nu am putut obține locația ta. Alege o localitate.");
      },
      { enableHighAccuracy: false, timeout: 10000, maximumAge: 300000 }
    );
  };

  const locOpts = [{ id: NONE, label: "—" }, ...toOpts(localities)];

  return (
    <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 items-end" data-testid="radacini-near-filter">
      {allowMe ? (<Field label="Distanță">
        <div className="flex gap-2">
          <button
            type="button"
            onClick={useMyLocation}
            disabled={locating}
            className={`inline-flex items-center gap-1.5 rounded-lg border px-3 py-2 text-sm font-semibold ${
              value.mode === "me" ? "border-emerald-500 text-emerald-700 dark:text-emerald-300" : "border-slate-300 dark:border-white/15 text-slate-700 dark:text-slate-200"
            }`}
            data-testid="radacini-near-me"
          >
            <LocateFixed className="w-4 h-4" /> {locating ? "Se localizează…" : "Lângă mine"}
          </button>
          {value.mode !== "off" && (
            <button type="button" onClick={() => onChange({ ...NEAR_OFF, radius: value.radius })} className="rounded-lg px-3 py-2 text-sm text-slate-500 hover:underline" data-testid="radacini-near-off">
              Fără filtru
            </button>
          )}
        </div>
      </Field>) : <div />}
      {allowLocality ? (<Field label="Lângă localitatea" htmlFor="near-localitate">
        <SelectField
          id="near-localitate"
          value={value.mode === "locality" && value.locality ? value.locality : NONE}
          onValueChange={(v) => (v === NONE ? onChange({ ...NEAR_OFF, radius: value.radius }) : onChange({ ...value, mode: "locality", locality: v, lat: undefined, lng: undefined }))}
          options={locOpts}
          testid="radacini-near-localitate"
        />
      </Field>) : <div />}
      <Field label="Rază" htmlFor="near-raza">
        <SelectField id="near-raza" value={String(value.radius)} onValueChange={(v) => set({ radius: Number(v) })} options={RADII} testid="radacini-near-raza" />
      </Field>
    </div>
  );
}
