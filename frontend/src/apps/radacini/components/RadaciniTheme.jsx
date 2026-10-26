import { useEffect } from "react";

// Componentele ui/* (dialog, popover, sheet) folosesc variabilele shadcn (--background, --border…), care nu sunt
// definite global în aplicație, așa că dialogurile ar avea fundal transparent. Le definim doar cât timp e deschis
// Rădăcini (clasă pe <body>, pentru că dialogurile se randează în portal, în afara layout-ului).
const CSS = `
body.radacini-app {
  --background: 0 0% 100%; --foreground: 222 47% 11%; --border: 214 32% 91%; --input: 214 32% 91%;
  --ring: 152 61% 36%; --accent: 210 40% 96%; --accent-foreground: 222 47% 11%;
  --muted: 210 40% 96%; --muted-foreground: 215 16% 47%; --popover: 0 0% 100%; --popover-foreground: 222 47% 11%;
}
html.dark body.radacini-app {
  --background: 220 13% 9%; --foreground: 210 40% 98%; --border: 217 19% 22%; --input: 217 19% 22%;
  --ring: 152 61% 46%; --accent: 217 19% 18%; --accent-foreground: 210 40% 98%;
  --muted: 217 19% 18%; --muted-foreground: 215 20% 65%; --popover: 220 13% 11%; --popover-foreground: 210 40% 98%;
}`;

export default function RadaciniTheme() {
  useEffect(() => {
    const style = document.createElement("style");
    style.setAttribute("data-radacini-theme", "");
    style.textContent = CSS;
    document.head.appendChild(style);
    document.body.classList.add("radacini-app");
    return () => {
      document.body.classList.remove("radacini-app");
      style.remove();
    };
  }, []);
  return null;
}
