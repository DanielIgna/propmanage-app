import { ClipboardCheck, FileSignature, Inbox, LayoutDashboard, MapPin, Settings, Sprout, UserRound, Users } from "lucide-react";

export const RADACINI_ENABLED = (process.env.NEXT_PUBLIC_RADACINI_ENABLED ?? "true") !== "false";

// requires: "staff" = is_staff · "manager" = role manager · absent = vizibil pentru toți
export const NAV = [
  { to: "/radacini", label: "Panou", icon: LayoutDashboard, testid: "radacini-nav-panou" },
  { to: "/radacini/terenuri", label: "Terenuri", icon: MapPin, testid: "radacini-nav-terenuri" },
  { to: "/radacini/terenurile-mele", label: "Terenurile mele", icon: Sprout, testid: "radacini-nav-terenurile-mele" },
  { to: "/radacini/cereri", label: "Cereri", icon: Inbox, testid: "radacini-nav-cereri" },
  { to: "/radacini/acorduri", label: "Acorduri", icon: FileSignature, testid: "radacini-nav-acorduri" },
  { to: "/radacini/profil", label: "Profil", icon: UserRound, testid: "radacini-nav-profil" },
  { to: "/radacini/operator", label: "Operator", icon: ClipboardCheck, requires: "staff", testid: "radacini-nav-operator" },
  { to: "/radacini/personal", label: "Personal", icon: Users, requires: "manager", testid: "radacini-nav-personal" },
  { to: "/radacini/setari", label: "Setări", icon: Settings, testid: "radacini-nav-setari" },
];

export const canSee = (item, staff) => {
  if (!item.requires) return true;
  if (item.requires === "staff") return !!staff?.is_staff;
  if (item.requires === "manager") return staff?.role === "manager";
  return false;
};
