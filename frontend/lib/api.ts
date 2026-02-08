export type ApiErrorPayload = { detail?: unknown } | unknown;

const DEFAULT_BASE_URL = "http://localhost:8000";

function baseUrl(): string {
  return process.env.NEXT_PUBLIC_API_URL || DEFAULT_BASE_URL;
}

async function parseJsonSafe(res: Response) {
  const text = await res.text();
  if (!text) return null;
  try {
    return JSON.parse(text);
  } catch {
    return text;
  }
}

export class ApiError extends Error {
  status: number;
  payload: ApiErrorPayload;

  constructor(message: string, status: number, payload: ApiErrorPayload) {
    super(message);
    this.status = status;
    this.payload = payload;
  }
}

export async function apiRequest<T>(
  path: string,
  init?: RequestInit & { json?: unknown }
): Promise<T> {
  const url = `${baseUrl()}${path}`;

  const headers = new Headers(init?.headers);
  headers.set("Accept", "application/json");
  headers.set("X-Requested-With", "spotify-playlist-manager");

  let body: BodyInit | undefined = init?.body as BodyInit | undefined;
  if (Object.prototype.hasOwnProperty.call(init || {}, "json")) {
    headers.set("Content-Type", "application/json");
    body = JSON.stringify(init?.json ?? {});
  }

  const res = await fetch(url, {
    ...init,
    body,
    headers,
    credentials: "include",
    mode: "cors",
    cache: "no-store",
  });

  if (!res.ok) {
    const payload = await parseJsonSafe(res);
    throw new ApiError(`Request failed: ${res.status}`, res.status, payload);
  }

  const data = await parseJsonSafe(res);
  return data as T;
}

