import React, { useState } from "react";
import { Link } from "react-router-dom";
import { X, Megaphone, Info, AlertTriangle } from "lucide-react";
import { useSiteContent } from "../lib/siteContent";

const VARIANTS = {
  promo: { bg: "bg-[#d4ff3a]", text: "text-black", Icon: Megaphone },
  info: { bg: "bg-sky-500", text: "text-white", Icon: Info },
  warning: { bg: "bg-amber-500", text: "text-black", Icon: AlertTriangle },
};

export const AnnouncementBanner = () => {
  const content = useSiteContent();
  const [dismissed, setDismissed] = useState(() => sessionStorage.getItem("pm_announce_dismissed") === "1");
  const banner = content?.banner;
  if (!banner?.active || !banner.text || dismissed) return null;
  const v = VARIANTS[banner.variant] || VARIANTS.info;
  return (
    <div className={`fixed top-0 left-0 right-0 z-[59] ${v.bg} ${v.text}`} data-testid="announcement-banner">
      <div className="flex items-center gap-2 px-3 sm:px-10 py-2 text-xs sm:text-sm font-semibold">
        <v.Icon className="w-4 h-4 shrink-0" />
        <span className="flex-1 truncate sm:text-center">{banner.text}</span>
        {banner.link && (
          <Link to={banner.link} className="underline hover:no-underline shrink-0 font-bold" data-testid="announcement-banner-link">
            {banner.link_label || "Vezi"}
          </Link>
        )}
        <button onClick={() => { sessionStorage.setItem("pm_announce_dismissed", "1"); setDismissed(true); }}
          className="p-1 rounded-full hover:bg-black/10 shrink-0" aria-label="Închide" data-testid="announcement-banner-close">
          <X className="w-4 h-4" />
        </button>
      </div>
    </div>
  );
};

export default AnnouncementBanner;
