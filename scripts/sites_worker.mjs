export function renderSitesWorker(apiOrigin) {
  const parsedOrigin = new URL(apiOrigin);
  if (parsedOrigin.origin !== apiOrigin || parsedOrigin.pathname !== "/") {
    throw new Error("Sites API proxy requires an HTTPS origin without a path");
  }
  if (parsedOrigin.protocol !== "https:") {
    throw new Error("Sites API proxy requires HTTPS");
  }

  return `const API_ORIGIN = ${JSON.stringify(parsedOrigin.origin)};

function isApiRequest(pathname) {
  return pathname === "/health" || pathname.startsWith("/api/");
}

export default {
  async fetch(request, env) {
    const url = new URL(request.url);
    if (isApiRequest(url.pathname)) {
      const target = new URL(url.pathname + url.search, API_ORIGIN);
      const proxyRequest = new Request(target, request);
      proxyRequest.headers.delete("host");
      return fetch(proxyRequest);
    }

    const response = await env.ASSETS.fetch(request);
    if (response.status !== 404) {
      return response;
    }
    const indexUrl = new URL("/index.html", url.origin);
    return env.ASSETS.fetch(new Request(indexUrl, request));
  },
};
`;
}
