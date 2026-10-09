// PropManage - Web Push subscription helper
import axios from "axios";

const API = `${process.env.NEXT_PUBLIC_BACKEND_URL}/api`;

// Converts a base64-url-safe string to a Uint8Array (required by PushManager.subscribe)
function urlBase64ToUint8Array(base64String) {
  const padding = "=".repeat((4 - (base64String.length % 4)) % 4);
  const base64 = (base64String + padding).replace(/-/g, "+").replace(/_/g, "/");
  const raw = window.atob(base64);
  return Uint8Array.from([...raw].map((c) => c.charCodeAt(0)));
}

export const pushSupported = () =>
  typeof window !== "undefined" &&
  "serviceWorker" in navigator &&
  "PushManager" in window &&
  "Notification" in window;

export async function ensureServiceWorker() {
  if (!pushSupported()) return null;
  try {
    const reg = await navigator.serviceWorker.register("/sw.js");
    await navigator.serviceWorker.ready;
    return reg;
  } catch (e) {
    console.warn("SW registration failed", e);
    return null;
  }
}

export async function getPushStatus() {
  if (!pushSupported()) return "unsupported";
  if (Notification.permission === "denied") return "denied";
  const reg = await navigator.serviceWorker.getRegistration();
  if (!reg) return "uninitialized";
  const sub = await reg.pushManager.getSubscription();
  return sub ? "subscribed" : "available";
}

export async function subscribeToPush() {
  if (!pushSupported()) throw new Error("Browser-ul tău nu suportă notificări push.");
  const permission = await Notification.requestPermission();
  if (permission !== "granted") throw new Error("Permisiunea pentru notificări a fost refuzată.");

  const reg = (await navigator.serviceWorker.getRegistration()) || (await ensureServiceWorker());
  if (!reg) throw new Error("Nu pot înregistra service worker-ul.");

  const { data } = await axios.get(`${API}/push/vapid-public-key`);
  const applicationServerKey = urlBase64ToUint8Array(data.public_key);

  const sub = await reg.pushManager.subscribe({
    userVisibleOnly: true,
    applicationServerKey,
  });

  await axios.post(`${API}/push/subscribe`, sub.toJSON());
  return "subscribed";
}

export async function unsubscribeFromPush() {
  const reg = await navigator.serviceWorker.getRegistration();
  if (!reg) return "uninitialized";
  const sub = await reg.pushManager.getSubscription();
  if (!sub) return "available";
  const subJson = sub.toJSON();
  await sub.unsubscribe();
  try {
    await axios.post(`${API}/push/unsubscribe`, subJson);
  } catch (e) {
    /* server-side cleanup best-effort */
  }
  return "available";
}
