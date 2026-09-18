// PropManage Service Worker - handles Web Push notifications
self.addEventListener("install", (event) => {
  self.skipWaiting();
});

self.addEventListener("activate", (event) => {
  event.waitUntil(self.clients.claim());
});

self.addEventListener("push", (event) => {
  let data = { title: "PropManage", message: "Notificare nouă", link: "/" };
  try {
    if (event.data) data = { ...data, ...event.data.json() };
  } catch (e) {
    /* fall back to default */
  }

  const options = {
    body: data.message,
    icon: "/favicon.ico",
    badge: "/favicon.ico",
    data: { link: data.link || "/" },
    requireInteraction: false,
    tag: "propmanage-notif",
  };

  event.waitUntil(self.registration.showNotification(data.title, options));
});

self.addEventListener("notificationclick", (event) => {
  event.notification.close();
  const target = (event.notification.data && event.notification.data.link) || "/";
  event.waitUntil(
    self.clients.matchAll({ type: "window", includeUncontrolled: true }).then((clients) => {
      // Reuse an open tab if possible
      for (const client of clients) {
        if ("focus" in client) {
          client.navigate(target);
          return client.focus();
        }
      }
      if (self.clients.openWindow) return self.clients.openWindow(target);
    })
  );
});
