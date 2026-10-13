import { LayoutDashboard, Settings } from "lucide-react";

export const RADACINI_ENABLED = (process.env.NEXT_PUBLIC_RADACINI_ENABLED ?? "true") !== "false";

export const NAV = [
  { to: "/radacini", label: "Panou", icon: LayoutDashboard },
  { to: "/radacini/setari", label: "Setări", icon: Settings },
];
