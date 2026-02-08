"use client";

const NOTICE_URL =
  "https://developer.spotify.com/blog/2026-02-06-update-on-developer-access-and-platform-security";

export function SpotifyNotice() {
  return (
    <div className="notice" role="status" aria-live="polite">
      <div className="noticeTitle">Spotify developer access update</div>
      <div className="noticeBody">
        OAuth setup may be limited right now (e.g., redirect URI updates / dev-mode constraints). If
        Connect Spotify fails, check Spotify’s notice and try again later.
      </div>
      <a className="noticeLink" href={NOTICE_URL} target="_blank" rel="noreferrer">
        Read the Spotify update
      </a>
    </div>
  );
}

