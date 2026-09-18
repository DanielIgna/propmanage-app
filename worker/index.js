export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    const backendUrl = typeof env.BACKEND_URL === "string" ? env.BACKEND_URL.trim() : "";

    if (url.pathname === "/health") {
      return Response.json({
        ok: true,
        service: "propmanage-app",
        backend_configured: Boolean(backendUrl),
      });
    }

    if (backendUrl && (url.pathname === "/api" || url.pathname.startsWith("/api/"))) {
      const target = new URL(`${url.pathname}${url.search}`, backendUrl);
      const headers = new Headers(request.headers);
      headers.delete("Host");
      const init = {
        method: request.method,
        headers,
        redirect: "manual",
      };
      if (request.method !== "GET" && request.method !== "HEAD") {
        init.body = request.body;
      }
      return fetch(target, init);
    }

    return Response.json({
      ok: true,
      service: "propmanage-app",
    });
  },
};
