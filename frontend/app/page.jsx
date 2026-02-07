"use client";

import { useEffect, useMemo, useState } from "react";

import { ApiError, apiRequest } from "../lib/api";

export default function Home() {
  const [me, setMe] = useState(null);
  const [error, setError] = useState(null);

  const apiUrl = useMemo(
    () => process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    []
  );

  useEffect(() => {
    let cancelled = false;
    (async () => {
      try {
        const data = await apiRequest("/auth/me");
        if (!cancelled) setMe(data);
      } catch (e) {
        if (e instanceof ApiError && e.status === 401) {
          if (!cancelled) setMe({ authenticated: false });
          return;
        }
        if (!cancelled) setError("Could not reach backend.");
      }
    })();
    return () => {
      cancelled = true;
    };
  }, []);

  const connectHref = `${apiUrl.replace(/\/$/, "")}/auth/login`;

  return (
    <main className="container" style={{ maxWidth: 900 }}>
      <h1 style={{ marginBottom: 8 }}>Spotify Playlist Manager</h1>
      <p className="muted" style={{ marginTop: 0 }}>
        Save Discover Weekly to a dedicated playlist, safely and automatically.
      </p>

      {error ? (
        <p className="error">{error}</p>
      ) : me === null ? (
        <p className="muted">Checking session…</p>
      ) : me.authenticated ? (
        <div style={{ marginTop: 20 }}>
          <p className="muted">
            Connected as <code>{me.spotify_user_id || "unknown"}</code>.
          </p>
          <a className="btn" href="/dashboard">
            Go to dashboard
          </a>
        </div>
      ) : (
        <div style={{ marginTop: 20 }}>
          <a className="btn btnPrimary" href={connectHref}>
            Connect Spotify
          </a>
          <p className="muted" style={{ marginTop: 10, maxWidth: 650 }}>
            You’ll be redirected to Spotify to authorize. This app never exposes
            Spotify tokens to the browser.
          </p>
        </div>
      )}
    </main>
  );
}

