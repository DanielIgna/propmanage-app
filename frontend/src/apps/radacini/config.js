import {
  ArrowLeftRight,
  Briefcase,
  ClipboardCheck,
  FileSignature,
  Inbox,
  LayoutDashboard,
  ListChecks,
  MapPin,
  Settings,
  Sprout,
  Store,
  UserRound,
  Users,
} from "lucide-react";

export const RADACINI_ENABLED = (process.env.NEXT_PUBLIC_RADACINI_ENABLED ?? "true") !== "false";

// requires: "staff" = is_staff · "manager" = role manager · absent = vizibil pentru toți
const NAV_ITEMS = [
  { to: "/radacini", label: "Panou", icon: LayoutDashboard, testid: "radacini-nav-panou" },
  { to: "/radacini/terenuri", label: "Terenuri", icon: MapPin, testid: "radacini-nav-terenuri" },
  { to: "/radacini/terenurile-mele", label: "Terenurile mele", icon: Sprout, testid: "radacini-nav-terenurile-mele" },
  { to: "/radacini/cereri", label: "Cereri", icon: Inbox, testid: "radacini-nav-cereri" },
  { to: "/radacini/acorduri", label: "Acorduri", icon: FileSignature, testid: "radacini-nav-acorduri" },
  { to: "/radacini/proiecte", label: "Proiecte", icon: Briefcase, testid: "radacini-nav-proiecte" },
  { to: "/radacini/piata", label: "Piață", icon: Store, testid: "radacini-nav-piata" },
  { to: "/radacini/rezervari", label: "Rezervări", icon: ArrowLeftRight, testid: "radacini-nav-rezervari" },
  { to: "/radacini/profil", label: "Profil", icon: UserRound, testid: "radacini-nav-profil" },
  { to: "/radacini/operator", label: "Operator", icon: ClipboardCheck, requires: "staff", testid: "radacini-nav-operator" },
  { to: "/radacini/personal", label: "Personal", icon: Users, requires: "manager", testid: "radacini-nav-personal" },
  { to: "/radacini/setari", label: "Setări", icon: Settings, testid: "radacini-nav-setari" },
];

// Progres (dev) nu apare în producție.
const DEV_ITEMS =
  process.env.NODE_ENV !== "production"
    ? [{ to: "/radacini/progres", label: "Progres", icon: ListChecks, testid: "radacini-nav-progres" }]
    : [];

export const NAV = [...NAV_ITEMS, ...DEV_ITEMS];

export const canSee = (item, staff) => {
  if (!item.requires) return true;
  if (item.requires === "staff") return !!staff?.is_staff;
  if (item.requires === "manager") return staff?.role === "manager";
  return false;
};
