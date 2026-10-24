const BASE = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export function getToken() { return typeof window === "undefined" ? "" : localStorage.getItem("beforeimpact_token") || ""; }

export async function api<T>(path:string, init:RequestInit = {}):Promise<T> {
  const headers = new Headers(init.headers);
  const token = getToken();
  if (token) headers.set("Authorization", `Bearer ${token}`);
  if (init.body && !(init.body instanceof FormData)) headers.set("Content-Type", "application/json");
  const response = await fetch(`${BASE}${path}`, {...init, headers, cache:"no-store"});
  if (!response.ok) {
    const body = await response.json().catch(() => ({detail:"Request failed"}));
    throw new Error(body.detail || "Request failed");
  }
  return response.json();
}

export { BASE };
