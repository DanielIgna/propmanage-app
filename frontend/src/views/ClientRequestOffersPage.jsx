// Sprint C — Page where client browses offers for one of their requests.
import React from "react";
import { useParams } from "react-router-dom";
import { DashLayout } from "./DashShared";
import { OffersList } from "../components/MarketplaceOffers";

export const ClientRequestOffersPage = () => {
  const { requestId } = useParams();
  return (
    <DashLayout role="client" title="Oferte primite la cererea ta">
      <OffersList requestId={requestId} />
    </DashLayout>
  );
};

export default ClientRequestOffersPage;
