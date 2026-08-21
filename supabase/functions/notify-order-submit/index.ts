// Supabase Edge Function: notify-order-submit
// Emails an itemized alert (via Resend) when an order guide is submitted.
//
// Trigger: a Database Webhook on the `orders` table (UPDATE + INSERT). The
// function only acts on the open -> submitted transition, so autosaves and
// unlocks are ignored.
//
// Env it reads:
//   RESEND_API_KEY   (required)  – the Resend sending key
//   NOTIFY_EMAILS    (optional)  – comma-separated recipients; default below
//   NOTIFY_FROM      (optional)  – From header; default is the Resend quick-path
//   WEBHOOK_SECRET   (optional)  – if set, requests must send matching x-webhook-secret
//   SUPABASE_URL / SUPABASE_SERVICE_ROLE_KEY  – auto-injected by Supabase
//
// Deploy (later, only when you say so):
//   supabase functions deploy notify-order-submit --no-verify-jwt

const RESEND_API_KEY = Deno.env.get("RESEND_API_KEY") ?? "";
const NOTIFY_TO = (Deno.env.get("NOTIFY_EMAILS") ?? "stephen@pourguys.com")
  .split(",").map((s) => s.trim()).filter(Boolean);
const NOTIFY_FROM = Deno.env.get("NOTIFY_FROM") ?? "Box Kitchen <onboarding@resend.dev>";
const WEBHOOK_SECRET = Deno.env.get("WEBHOOK_SECRET") ?? "";

const SUPABASE_URL = Deno.env.get("SUPABASE_URL") ?? "";
const SERVICE_KEY = Deno.env.get("SUPABASE_SERVICE_ROLE_KEY") ?? "";

const GUIDE_LABELS: Record<string, string> = {
  birite_dairy: "Birite & Dairy",
  produce_protein: "Produce & Protein",
};

function esc(s: unknown): string {
  return String(s ?? "").replace(/[&<>"]/g, (c) =>
    ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] as string));
}

// Kitchen is Pacific; format the submit time in the cook's local zone.
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

async function rest(path: string): Promise<any[]> {
  const res = await fetch(`${SUPABASE_URL}/rest/v1/${path}`, {
    headers: { apikey: SERVICE_KEY, Authorization: `Bearer ${SERVICE_KEY}` },
  });
  if (!res.ok) return [];
  try { return await res.json(); } catch { return []; }
}

Deno.serve(async (req) => {
  if (WEBHOOK_SECRET && req.headers.get("x-webhook-secret") !== WEBHOOK_SECRET) {
    return new Response("unauthorized", { status: 401 });
  }

  let body: any;
  try { body = await req.json(); } catch { return new Response("bad json", { status: 400 }); }

  const rec = body?.record;
  const old = body?.old_record;

  // Only fire on the open -> submitted transition of an orders row.
  if (
    body?.table !== "orders" ||
    !rec ||
    rec.status !== "submitted" ||
    (old && old.status === "submitted")
  ) {
    return new Response(JSON.stringify({ skipped: true }), {
      status: 200, headers: { "Content-Type": "application/json" },
    });
  }

  const guideLabel = GUIDE_LABELS[rec.guide_name] ?? rec.guide_name ?? "Order";
  const who = rec.submitted_by || "—";
  const when = fmtWhen(rec.submitted_at);
  const quantities: Record<string, string> = rec.quantities ?? {};
  const count = rec.item_count ?? Object.keys(quantities).length;
  const location = rec.location || "Tempest";

  // Resolve item ids -> {name, unit} using the same public tables the app reads.
  const [items, unitsList] = await Promise.all([
    rest(`order_items?location=eq.${encodeURIComponent(location)}&select=id,name,unit,unit_id,sort_order`),
    rest(`order_units?select=id,label`),
  ]);
  const unitMap: Record<string, string> = {};
  for (const u of unitsList) unitMap[String(u.id)] = u.label;
  const itemMap: Record<string, any> = {};
  for (const it of items) itemMap[String(it.id)] = it;

  const rows = Object.keys(quantities)
    .map((id) => {
      const it = itemMap[id];
      const name = it?.name ?? `Item #${id}`;
      const unit = it ? (unitMap[String(it.unit_id)] ?? it.unit ?? "") : "";
      const sort = it?.sort_order ?? 9999;
      return { name, unit, qty: quantities[id], sort };
    })
    .sort((a, b) => a.sort - b.sort);

  const listHtml = rows.map((r) =>
    `<tr><td style="padding:6px 0;border-bottom:1px solid #eee">${esc(r.name)}</td>` +
    `<td style="padding:6px 0;border-bottom:1px solid #eee;text-align:right;font-weight:600;white-space:nowrap">${esc(r.qty)} ${esc(r.unit)}</td></tr>`
  ).join("");

  const listText = rows.map((r) => `• ${r.name} — ${r.qty} ${r.unit}`.trim()).join("\n");

  const subject = `🧾 ${guideLabel} order submitted — ${count} item${count === 1 ? "" : "s"}`;
  const html =
    `<div style="font-family:Arial,Helvetica,sans-serif;max-width:520px;margin:0 auto;color:#111">` +
      `<h2 style="margin:0 0 4px">${esc(guideLabel)} order submitted</h2>` +
      `<p style="margin:0 0 16px;color:#555">Submitted by <strong>${esc(who)}</strong> · ${esc(when)} · ${esc(count)} item${count === 1 ? "" : "s"}</p>` +
      `<table style="width:100%;border-collapse:collapse;font-size:15px">${listHtml}</table>` +
      `<p style="margin:20px 0 0;color:#999;font-size:12px">Box Kitchen · ${esc(location)}</p>` +
    `</div>`;
  const text = `${guideLabel} order submitted\nBy ${who} · ${when} · ${count} items\n\n${listText}`;

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
