const BACKEND = "https://propmanage.ro";

const SENSITIVE = [
  /^\/backend(\/|$)/i,
  /^\/memory(\/|$)/i,
  /^\/docs(\/|$)/i,
  /^\/enterprise(\/|$)/i,
  /^\/\.git(\/|$)/i,
  /^\/node_modules(\/|$)/i,
  /^\/worker(\/|$)/i,
  /^\/functions(\/|$)/i,
  /^\/package\.json$/i,
  /^\/yarn\.lock$/i,
  /^\/wrangler\./i,
  /^\/\.yarnrc\.yml$/i,
  /^\/\.gitignore$/i,
];

function proxyToBackend(request) {
  const incoming = new URL(request.url);
  const target = new URL(`${incoming.pathname}${incoming.search}`, BACKEND);
  const headers = new Headers(request.headers);
  headers.delete("Host");
  headers.set("X-Forwarded-Host", incoming.host);
  headers.set("X-Forwarded-Proto", "https");
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

export async function onRequest(context) {
  const path = new URL(context.request.url).pathname;

  if (path === "/api" || path.startsWith("/api/") || path.startsWith("/uploads/")) {
    return proxyToBackend(context.request);
  }

  if (SENSITIVE.some((pattern) => pattern.test(path))) {
    return new Response("Not found", { status: 404 });
  }

  return context.next();
}
