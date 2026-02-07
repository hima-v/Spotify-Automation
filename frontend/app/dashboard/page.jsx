"use client";

import { useEffect, useMemo, useRef, useState } from "react";

import { ApiError, apiRequest } from "../../lib/api";

function formatTs(iso) {
  const d = new Date(iso);
  if (Number.isNaN(d.getTime())) return iso;
  return d.toLocaleString();
}

export default function DashboardPage() {
  const [me, setMe] = useState(null);
  const [runs, setRuns] = useState([]);
  const [loadingRuns, setLoadingRuns] = useState(false);
  const [syncing, setSyncing] = useState(false);
  const [job, setJob] = useState(null);
  const [error, setError] = useState(null);

  const apiUrl = useMemo(
    () => process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000",
    []
  );
  const connectHref = `${apiUrl.replace(/\/$/, "")}/auth/login`;

  const pollAbort = useRef({ stop: false });

  async function loadMe() {
    try {
      const data = await apiRequest("/auth/me");
      setMe(data);
      setError(null);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setMe({ authenticated: false });
        return;
      }
      setError("Could not reach backend.");
    }
  }

  async function loadRuns() {
    setLoadingRuns(true);
    try {
      const data = await apiRequest("/playlists/runs?limit=20");
      setRuns(data.items || []);
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) return;
      setError("Failed to load runs.");
    } finally {
      setLoadingRuns(false);
    }
  }

  useEffect(() => {
    loadMe().then(() => loadRuns());
    return () => {
      pollAbort.current.stop = true;
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  async function pollJob(jobId) {
    pollAbort.current.stop = false;
    for (let attempts = 0; attempts < 60; attempts += 1) {
      if (pollAbort.current.stop) break;
      try {
        const s = await apiRequest(`/jobs/${jobId}`);
        setJob(s);
        if (s.state === "SUCCESS" || s.state === "FAILURE") return s;
      } catch {
        // transient UI issue; keep polling a bit
      }
      await new Promise((r) => setTimeout(r, 1500));
    }
    return null;
  }

  async function onSync() {
    setError(null);
    setSyncing(true);
    setJob(null);
    try {
      const res = await apiRequest("/playlists/sync/discover-weekly", {
        method: "POST",
        json: { dry_run: false },
      });
      const finalStatus = await pollJob(res.job_id);
      if (finalStatus?.state === "FAILURE") setError("Job failed.");
      await loadRuns();
    } catch (e) {
      if (e instanceof ApiError && e.status === 401) {
        setError("Not authenticated. Connect Spotify first.");
      } else {
        setError("Could not start sync.");
      }
    } finally {
      setSyncing(false);
    }
  }

  return (
    <main className="container">
      <div className="row">
        <div>
          <h1 style={{ marginBottom: 8 }}>Dashboard</h1>
          <p className="muted" style={{ marginTop: 0 }}>
            {me === null
              ? "Checking session…"
              : me.authenticated
                ? `Connected as ${me.spotify_user_id || "unknown"}`
                : "Not connected"}
          </p>
        </div>
        <div style={{ display: "flex", alignItems: "center", gap: 12 }}>
          <a className="btn" href="/">
            Home
          </a>
          {!me || me.authenticated ? null : (
            <a className="btn btnPrimary" href={connectHref}>
              Connect Spotify
            </a>
          )}
        </div>
      </div>

      {error ? <p className="error">{error}</p> : null}

      <section style={{ marginTop: 18 }}>
        <button className="btn" onClick={onSync} disabled={!me?.authenticated || syncing}>
          {syncing ? "Syncing…" : "Sync Discover Weekly"}
        </button>
        {job ? (
          <p className="muted" style={{ marginTop: 10 }}>
            Job <code>{job.job_id}</code>: {job.state} ({job.status})
          </p>
        ) : null}
      </section>

      <section style={{ marginTop: 22 }}>
        <div className="row" style={{ justifyContent: "space-between" }}>
          <h2 style={{ margin: 0 }}>Recent runs</h2>
          <button className="btn" onClick={loadRuns} disabled={loadingRuns}>
            {loadingRuns ? "Loading…" : "Refresh"}
          </button>
        </div>

        <div className="tableWrap">
          <table>
            <thead>
              <tr>
                <th>Started</th>
                <th>Status</th>
                <th>Tracks added</th>
                <th>Error</th>
              </tr>
            </thead>
            <tbody>
              {runs.length === 0 ? (
                <tr>
                  <td colSpan={4} className="muted">
                    No runs yet.
                  </td>
                </tr>
              ) : (
                runs.map((r) => (
                  <tr key={r.id}>
                    <td style={{ whiteSpace: "nowrap" }}>{formatTs(r.started_at)}</td>
                    <td>{r.status}</td>
                    <td>{r.tracks_added_count ?? "—"}</td>
                    <td style={{ maxWidth: 420 }}>
                      <span className={r.error_message ? "" : "muted"}>
                        {r.error_message || "—"}
                      </span>
                    </td>
                  </tr>
                ))
              )}
            </tbody>
          </table>
        </div>
      </section>

      <p className="muted" style={{ marginTop: 26, fontSize: 13 }}>
        CSRF note: requests use SameSite cookies and send JSON + a custom header,
        which triggers CORS preflight; the backend should only allow your frontend
        origin.
      </p>
    </main>
  );
}

