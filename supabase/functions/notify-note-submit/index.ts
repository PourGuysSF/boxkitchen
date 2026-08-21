// Supabase Edge Function: notify-note-submit
// Emails an alert (via Resend) when a Kitchen Note / Issue is posted.
//
// Trigger: a Database Webhook on the `notes` table (INSERT). A note is created
// once, so — unlike the order function — there is no open->submitted transition
// to watch for. Every category is emailed (decision locked in BUILD_PLAN A4).
//
// Env it reads (all shared with notify-order-submit):
//   RESEND_API_KEY   (required)  – the Resend sending key
//   NOTIFY_EMAILS    (optional)  – comma-separated recipients; default below
//   NOTIFY_FROM      (optional)  – From header; default is the Resend quick-path
//   WEBHOOK_SECRET   (optional)  – if set, requests must send matching x-webhook-secret
//
// Deploy (later, only when you say so):
//   supabase functions deploy notify-note-submit --no-verify-jwt

const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY") ?? "";
const NOTIFY_TO = (Deno.env.get("NOTIFY_EMAILS") ?? "stephen@pourguys.com")
  .split(",").map((s) => s.trim()).filter(Boolean);
const NOTIFY_FROM = Deno.env.get("NOTIFY_FROM") ?? "Box Kitchen <onboarding@resend.dev>";
const WEBHOOK_SECRET = Deno.env.get("WEBHOOK_SECRET") ?? "";

// Category emoji/labels mirror tempest_notes.html (var CATS). Keep in sync.
const CATS: Record<string, { emoji: string; label: string; accent: string }> = {
  urgent:    { emoji: "🚨", label: "Urgent",        accent: "#e5484d" },
  equipment: { emoji: "🔧", label: "Equipment",     accent: "#f5a623" },
  supplies:  { emoji: "📋", label: "Supplies & 86'd", accent: "#4a90d9" },
  recipe:    { emoji: "🍳", label: "Recipe issue",  accent: "#e85d3a" },
  other:     { emoji: "💬", label: "Other",         accent: "#888888" },
};
const FALLBACK_CAT = { emoji: "💬", label: "Note", accent: "#888888" };

function esc(s: unknown): string {
  return String(s ?? "").replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] as string));
}

// Kitchen is Pacific; format the post time in the cook's local zone.
function fmtWhen(iso: string | null): string {
  if (!iso) return "";
  try {
    return new Intl.DateTimeFormat("en-US", {
      timeZone: "America/Los_Angeles",
      weekday: "short", month: "short", day: "numeric",
      hour: "numeric", minute: "2-digit",
    }).format(new Date(iso));
  } catch {
    return iso;
  }
}

Deno.serve(async (req) => {
  if (WEBHOOK_SECRET && req.headers.get("x-webhook-secret") !== WEBHOOK_SECRET) {
    return new Response("unauthorized", { status: 401 });
  }

  let body: any;
  try { body = await req.json(); } catch { return new Response("bad json", { status: 400 }); }

  const rec = body?.record;

  // Only fire on an inserted notes row.
  if (body?.table !== "notes" || !rec) {
    return new Response(JSON.stringify({ skipped: true }), {
      status: 200, headers: { "Content-Type": "application/json" },
    });
  }

  const cat = CATS[rec.category] ?? FALLBACK_CAT;
  const who = rec.posted_by || "—";
  const when = fmtWhen(rec.created_at);
  const location = rec.location || "Tempest";
  const noteText = rec.body || "";

  const subject = `${cat.emoji} New ${cat.label} note — ${location}`;
  const html =
    `<div style="font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:0 auto;color:#111">` +
      `<div style="border-left:4px solid ${cat.accent};padding-left:14px">` +
        `<h2 style="margin:0 0 4px">${cat.emoji} ${esc(cat.label)}</h2>` +
        `<p style="margin:0 0 16px;color:#555">Posted by <strong>${esc(who)}</strong> · ${esc(when)}</p>` +
        `<p style="margin:0;font-size:16px;line-height:1.5;white-space:pre-wrap">${esc(noteText)}</p>` +
      `</div>` +
      `<p style="margin:20px 0 0;color:#999;font-size:12px">Box Kitchen · ${esc(location)} · Kitchen Notes & Issues</p>` +
    `</div>`;
  const text = `${cat.emoji} ${cat.label} note\nBy ${who} · ${when}\n\n${noteText}`;

  if (!RESEND_API_KEY) {
    return new Response(JSON.stringify({ error: "RESEND_API_KEY not set" }), {
      status: 500, headers: { "Content-Type": "application/json" },
    });
  }

  const send = await fetch("https://api.resend.com/emails", {
    method: "POST",
    headers: {
      Authorization: `Bearer ${RESEND_API_KEY}`,
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ from: NOTIFY_FROM, to: NOTIFY_TO, subject, html, text }),
  });

  const result = await send.text();
  return new Response(
    JSON.stringify({ sent: send.ok, status: send.status, resend: result }),
    { status: send.ok ? 200 : 500, headers: { "Content-Type": "application/json" } },
  );
});
