"use client";

import { useEffect, useMemo, useState } from "react";

import { ApiError, apiRequest } from "../lib/api";
import { SpotifyNotice } from "./components/SpotifyNotice";

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
    <main className="container pageFadeIn" style={{ maxWidth: 900 }}>
      <div className="row" style={{ alignItems: "flex-start" }}>
        <div>
          <h1 style={{ marginBottom: 8 }}>Spotify Playlist Manager</h1>
          <p className="muted" style={{ marginTop: 0 }}>
            Save Discover Weekly to a dedicated playlist, safely and automatically.
          </p>
        </div>
        <div style={{ display: "flex", gap: 10, paddingTop: 4 }}>
          <a className="btn" href="/dashboard">
            Dashboard
          </a>
        </div>
      </div>

      <div className="slideUp1">
        <SpotifyNotice />
      </div>

      <section className="hero card slideUp2">
        <h2 style={{ margin: 0, fontSize: 18 }}>
          Tired of losing Discover Weekly tracks?
        </h2>
        <p className="muted" style={{ margin: "8px 0 0", maxWidth: 760 }}>
          Sometimes Discover Weekly is really good, but you miss a few songs when it refreshes.
          This app saves those tracks for you by copying them into a “Saved Weekly” playlist which
          ensures no manual adding.
        </p>

        <div style={{ display: "flex", gap: 10, marginTop: 14, flexWrap: "wrap" }}>
          <a className="btn btnPrimary btnPop" href={connectHref}>
            Connect Spotify
          </a>
          <a className="btn" href="/dashboard">
            View dashboard
          </a>
        </div>
      </section>

      <section className="card">
        <h2 style={{ margin: 0, fontSize: 16 }}>What it does</h2>
        <ul className="featureList">
          <li>Connect Spotify securely (tokens stay server-side).</li>
          <li>Copy Discover Weekly into “Saved Weekly” without duplicates.</li>
          <li>Run sync as a background job and track status.</li>
          <li>View recent sync run history in the dashboard.</li>
        </ul>
      </section>

      {error ? (
        <p className="error">{error}</p>
      ) : me === null ? (
        <p className="muted">Checking session…</p>
      ) : me.authenticated ? (
        <div style={{ marginTop: 20 }}>
          <p className="muted">
            Connected as <code>{me.spotify_user_id || "unknown"}</code>.
          </p>
          <a className="btn" href="/dashboard">Go to dashboard</a>
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

