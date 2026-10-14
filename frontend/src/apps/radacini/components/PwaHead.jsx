import { useEffect } from "react";

// Manifest PWA Rădăcini doar cât timp ești în /radacini; la ieșire se restaurează capul PropManage.
export default function PwaHead() {
  useEffect(() => {
    const head = document.head;
    const removed = []; // [{node, next}]
    const added = [];
    head.querySelectorAll('link[rel="manifest"], link[rel="apple-touch-icon"], meta[name="theme-color"]').forEach((n) => {
      removed.push({ node: n, next: n.nextSibling });
      n.remove();
    });
    const add = (tag, attrs) => {
      const el = document.createElement(tag);
      Object.entries(attrs).forEach(([k, v]) => el.setAttribute(k, v));
      head.appendChild(el);
      added.push(el);
    };
    add("link", { rel: "manifest", href: "/radacini-manifest.webmanifest" });
    add("meta", { name: "theme-color", content: "#0b0c0d" });
    add("link", { rel: "apple-touch-icon", href: "/radacini-icons/icon-192.png" });
    return () => {
      added.forEach((n) => n.remove());
      removed.forEach(({ node, next }) => head.insertBefore(node, next && next.parentNode === head ? next : null));
    };
  }, []);
  return null;
}
