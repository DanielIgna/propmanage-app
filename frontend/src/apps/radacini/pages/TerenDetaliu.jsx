import React, { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import { toast } from "sonner";
import { ArrowLeft, MapPin, Send } from "lucide-react";
import { CARD, DSButton, EmptyState } from "../../../design-system";
import { Dialog, DialogContent, DialogDescription, DialogHeader, DialogTitle } from "../../../components/ui/dialog";
import { useAuth } from "../../../auth";
import ApproxMap from "../components/ApproxMap";
import ProposalForm from "../components/ProposalForm";
import { radaciniApi, errMsg } from "../api";
import { useMeta } from "../hooks";
import { Chips, COUNTY, fmtArea, fmtDate, labelOf, PageSkeleton, StatusBadge } from "../shared";

const Row = ({ label, children }) => (
  <div className="flex flex-col sm:flex-row sm:gap-4 py-2 border-b border-slate-100 dark:border-white/5 last:border-0">
    <dt className="sm:w-40 shrink-0 text-sm font-semibold text-slate-500 dark:text-slate-400">{label}</dt>
    <dd className="text-sm text-slate-800 dark:text-slate-200 min-w-0">{children}</dd>
  </div>
);

export default function TerenDetaliu() {
  const { id } = useParams();
  const navigate = useNavigate();
  const { user } = useAuth();
  const { meta } = useMeta();
  const [p, setP] = useState(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState(null);
  const [reqOpen, setReqOpen] = useState(false);
  const [sending, setSending] = useState(false);

  useEffect(() => {
    let alive = true;
    setLoading(true);
    setError(null);
    radaciniApi
      .parcel(id)
      .then((d) => alive && setP(d))
      .catch((e) => alive && setError(e))
      .finally(() => alive && setLoading(false));
    return () => {
      alive = false;
    };
  }, [id]);

  // Proprietarul nu își poate cere propriul teren (backend: 403). Vizualizarea publică nu include owner_user_id:
  // în acel caz butonul apare și eroarea backend-ului ajunge în toast.
  const isOwner = !!user && !!p?.owner_user_id && p.owner_user_id === user.id;

  const sendRequest = async (body) => {
    setSending(true);
    try {
      const request = await radaciniApi.createRequest(p.id, body);
      toast.success("Cererea a fost trimisă");
      navigate(`/radacini/cereri/${request.id}`);
    } catch (e) {
      toast.error(errMsg(e, "Nu am putut trimite cererea"));
    } finally {
      setSending(false);
    }
  };

  const back = (
    <Link to="/radacini/terenuri" className="inline-flex items-center gap-1.5 text-sm font-semibold text-emerald-700 dark:text-emerald-300 hover:underline">
      <ArrowLeft className="w-4 h-4" /> Înapoi la terenuri
    </Link>
  );

  if (loading) return <PageSkeleton />;
  if (error || !p) {
    return (
      <div className="space-y-4">
        {back}
        <EmptyState
          icon={MapPin}
          title="Terenul nu există sau nu este publicat"
          hint={error ? errMsg(error) : undefined}
          testid="radacini-teren-negasit"
        />
      </div>
    );
  }

  const offer = p.offer || {};
  const models = (offer.models || []).map((m) => labelOf(meta?.offer_models, m));
  const modelOpts = (offer.models || []).map((m) => ({ id: m, label: labelOf(meta?.offer_models, m) }));
  const water = (p.water_sources || []).map((w) => labelOf(meta?.water_sources, w));
  const availability =
    p.availability_from || p.availability_to
      ? `${fmtDate(p.availability_from)} – ${fmtDate(p.availability_to)}`
      : null;

  return (
    <div className="space-y-5 max-w-4xl" data-testid="radacini-teren-detaliu">
      {back}

      <div className="flex flex-wrap items-start justify-between gap-3">
        <div className="min-w-0">
          <h2 className="text-xl font-bold text-slate-900 dark:text-white break-words">{p.title}</h2>
          <p className="text-sm text-slate-500 dark:text-slate-400">
            {p.locality} · {COUNTY}
          </p>
        </div>
        <div className="flex flex-wrap items-center gap-2">
          {p.status && p.status !== "published" && <StatusBadge status={p.status} />}
          {p.status === "published" && !isOwner && (
            <DSButton icon={Send} onClick={() => setReqOpen(true)} data-testid="radacini-btn-solicita">
              Solicită terenul
            </DSButton>
          )}
        </div>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-4">
        <section className={`${CARD} p-5`}>
          <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-2">Teren</h3>
          <dl>
            <Row label="Suprafață">{fmtArea(p.area_m2)}</Row>
            <Row label="Acces">{p.access || "Nespecificat"}</Row>
            <Row label="Surse de apă">{water.length ? <Chips items={water} /> : "Nespecificate"}</Row>
            <Row label="Culturi actuale">{p.current_crops?.length ? <Chips items={p.current_crops} /> : "Nespecificate"}</Row>
            {availability && <Row label="Disponibil">{availability}</Row>}
          </dl>
          {p.description && (
            <p className="mt-4 text-sm text-slate-600 dark:text-slate-300 whitespace-pre-line">{p.description}</p>
          )}
        </section>

        <section className={`${CARD} p-5`}>
          <h3 className="text-sm font-bold text-slate-900 dark:text-white mb-2">Ofertă</h3>
          <dl>
            <Row label="Model">{models.length ? <Chips items={models} /> : "Nespecificat"}</Row>
            {offer.price_ron_per_year != null && <Row label="Preț">{`${offer.price_ron_per_year} RON / an`}</Row>}
            {offer.harvest_share_percent != null && <Row label="Parte din recoltă">{`${offer.harvest_share_percent}%`}</Row>}
            {offer.terms && <Row label="Condiții">{<span className="whitespace-pre-line">{offer.terms}</span>}</Row>}
            {p.owner_name && <Row label="Proprietar">{p.owner_name}</Row>}
          </dl>
        </section>
      </div>

      <section className={`${CARD} p-5 space-y-3`}>
        <div className="flex items-center justify-between gap-2">
          <h3 className="text-sm font-bold text-slate-900 dark:text-white">Locație</h3>
          <span className="text-xs text-slate-500 dark:text-slate-400">Aproximativă</span>
        </div>
        <ApproxMap points={[{ id: p.id, lat: p.lat, lng: p.lng, title: p.title, subtitle: `${p.locality} · locație aproximativă` }]} height="280px" />
      </section>

      <Dialog open={reqOpen} onOpenChange={(open) => !sending && setReqOpen(open)}>
        <DialogContent className="max-w-lg max-h-[90vh] overflow-y-auto" data-testid="radacini-cerere-dialog">
          <DialogHeader>
            <DialogTitle>Solicită terenul</DialogTitle>
            <DialogDescription>Propune condițiile. Proprietarul poate accepta, refuza sau face o contrapropunere.</DialogDescription>
          </DialogHeader>
          {reqOpen && (
            <ProposalForm
              idPrefix="cerere"
              testidPrefix="radacini-cerere-form"
              models={modelOpts}
              areaMax={p.area_m2}
              submitLabel="Trimite cererea"
              submitting={sending}
              onSubmit={sendRequest}
              onCancel={() => setReqOpen(false)}
            />
          )}
        </DialogContent>
      </Dialog>
    </div>
  );
}
