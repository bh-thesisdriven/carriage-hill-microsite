/* Carriage Hill microsite — tabs, map, lot interactions. No build step. */

// ── Contact form (Formsubmit.co relay — no account/DB) ──
// Hashed alias so the delivery email isn't exposed in page source.
const CONTACT = {
  endpoint: "1ae87ed7c9cade3bf4988178847aabf3",   // Formsubmit alias for the delivery inbox
};

const TABS = ["carriage-hill", "why-roxbury", "contact"];

// ── Scroll-spy: highlight the nav item for the section in view ──
function initScrollSpy() {
  const setActive = (id) =>
    document.querySelectorAll(".tab").forEach((a) =>
      a.classList.toggle("active", a.dataset.tab === id)
    );
  const obs = new IntersectionObserver(
    (entries) => {
      entries.forEach((e) => { if (e.isIntersecting) setActive(e.target.id); });
    },
    { rootMargin: "-45% 0px -50% 0px", threshold: 0 }
  );
  TABS.forEach((id) => { const el = document.getElementById(id); if (el) obs.observe(el); });
}

// ── Contact form ───────────────────────────────────────────────
function wireContact() {
  const form = document.getElementById("contact-form");
  if (!form) return;
  const status = document.getElementById("cf-status");
  const btn = document.getElementById("cf-submit");

  form.addEventListener("submit", async (e) => {
    e.preventDefault();
    if (form._honey && form._honey.value) return;          // bot filled the honeypot
    if (!form.checkValidity()) { form.reportValidity(); return; }

    btn.disabled = true;
    const btnText = btn.textContent;
    btn.textContent = "Sending…";
    status.className = "cf-status";
    status.textContent = "";

    const payload = {
      name: form.name.value.trim(),
      email: form.email.value.trim(),
      phone: form.phone.value.trim(),
      message: form.message.value.trim(),
      _subject: "Carriage Hill — website inquiry",
      _template: "table",
    };

    try {
      const res = await fetch("https://formsubmit.co/ajax/" + CONTACT.endpoint, {
        method: "POST",
        headers: { "Content-Type": "application/json", "Accept": "application/json" },
        body: JSON.stringify(payload),
      });
      const data = await res.json().catch(() => ({}));
      if (res.ok && (data.success === "true" || data.success === true)) {
        form.reset();
        status.className = "cf-status ok";
        status.textContent = "Thank you. We'll be in touch.";
        btn.textContent = "Sent";
        return;
      }
      throw new Error((data && data.message) || "Request failed");
    } catch (err) {
      status.className = "cf-status err";
      status.textContent = "Something went wrong sending your note. Please try again in a moment.";
      btn.disabled = false;
      btn.textContent = btnText;
    }
  });
}

// ── Map ────────────────────────────────────────────────────────
const layers = {};   // lot number -> leaflet layer
let LOTS = [];       // feature props, in order
let activeTypes = null; // Set of use_types currently shown, or null = all

function lotStyle(f, active) {
  return {
    color: active ? "#CBFB45" : "#ffffff",
    weight: active ? 3 : 1.6,
    opacity: 0.95,
    fillColor: f.properties.color,
    fillOpacity: active ? 0.72 : 0.48,
  };
}

async function initMap() {
  const map = L.map("map", { scrollWheelZoom: false, zoomControl: false, maxZoom: 19 });
  window._map = map;
  L.control.zoom({ position: "bottomleft" }).addTo(map);

  // ── Base layers (all free / no API token) ──
  const esriImg = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 19, attribution: "Imagery &copy; Esri, Maxar, Earthstar Geographics" }
  );
  const esriRoads = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Transportation/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 19 }
  );
  const esriLabels = L.tileLayer(
    "https://server.arcgisonline.com/ArcGIS/rest/services/Reference/World_Boundaries_and_Places/MapServer/tile/{z}/{y}/{x}",
    { maxZoom: 19 }
  );
  const aerialLabeled = L.layerGroup([esriImg, esriRoads, esriLabels]);

  const terrain = L.tileLayer(
    "https://{s}.tile.opentopomap.org/{z}/{x}/{y}.png",
    { maxZoom: 19, maxNativeZoom: 17, subdomains: "abc",
      attribution: "&copy; OpenTopoMap (CC-BY-SA), &copy; OpenStreetMap contributors" }
  );
  const cartoMap = L.tileLayer(
    "https://{s}.basemaps.cartocdn.com/rastertiles/voyager/{z}/{x}/{y}{r}.png",
    { maxZoom: 19, subdomains: "abcd", attribution: "&copy; OpenStreetMap contributors, &copy; CARTO" }
  );

  aerialLabeled.addTo(map); // default
  L.control.layers(
    { "Aerial + labels": aerialLabeled, "Aerial": esriImg, "Terrain": terrain, "Map": cartoMap },
    null,
    { position: "topright", collapsed: false }
  ).addTo(map);

  const data = await fetch("data/parcels.geojson?v=15").then((r) => r.json());
  if (data.metadata && data.metadata.provisional) {
    document.getElementById("provisional-banner").hidden = false;
  }

  const gj = L.geoJSON(data, {
    style: (f) => lotStyle(f, false),
    onEachFeature: (f, layer) => {
      const n = f.properties.id;
      layers[n] = layer;
      layer.on("click", (e) => {
        selectLot(n, true);
        const el = e && e.originalEvent && e.originalEvent.target;
        if (el && el.blur) el.blur();
      });
      layer.on("mouseover", () => highlight(n, true));
      layer.on("mouseout", () => { if (!layer._selected) highlight(n, false); });
      layer.bindTooltip(f.properties.label, { direction: "top", opacity: 0.9 });
    },
  }).addTo(map);

  map.fitBounds(gj.getBounds().pad(0.15));
  LOTS = data.features.map((f) => f.properties);
  buildFilter();
  updateSummary();
}

function highlight(n, on) {
  const l = layers[n];
  if (l) {
    l.setStyle(lotStyle({ properties: LOTS.find((x) => x.id === n) }, on));
    // Bring highlighted parcels to the front so neighbors don't paint over their outline.
    if (on && l.bringToFront) l.bringToFront();
  }
  document.querySelectorAll(`.lot-row[data-lot="${CSS.escape(n)}"]`).forEach((r) =>
    r.classList.toggle("active", on)
  );
}

// ── Lot list + filter (grouped by street) ──────────────────────
function groups() {
  const seen = new Map();
  LOTS.forEach((l) => { if (!seen.has(l.group)) seen.set(l.group, l); });
  return [...seen.values()];
}

function buildFilter() {
  const wrap = document.getElementById("filter");
  const mk = (label, color, grp) => {
    const b = document.createElement("button");
    b.setAttribute("aria-pressed", grp === null ? "true" : "false");
    b.innerHTML = (color ? `<span class="dot" style="background:${color}"></span>` : "") + label;
    b.onclick = () => applyFilter(grp, b);
    b.dataset.group = grp ?? "";
    return b;
  };
  wrap.appendChild(mk("All", null, null));
  groups().forEach((l) => wrap.appendChild(mk(l.group_label, l.color, l.group)));
}

function applyFilter(grp, btn) {
  activeTypes = grp === null ? null : new Set([grp]);
  document.querySelectorAll("#filter button").forEach((b) =>
    b.setAttribute("aria-pressed", b === btn ? "true" : "false")
  );
  LOTS.forEach((l) => {
    const show = !activeTypes || activeTypes.has(l.group);
    const layer = layers[l.id];
    if (!layer) return;
    if (show) layer.addTo(window._map); else window._map.removeLayer(layer);
  });
  updateSummary();
}

function hexA(hex, a) {
  const n = hex.replace("#", "");
  const r = parseInt(n.slice(0, 2), 16), g = parseInt(n.slice(2, 4), 16), b = parseInt(n.slice(4, 6), 16);
  return `rgba(${r},${g},${b},${a})`;
}

function updateSummary() {
  const sel = LOTS.filter((l) => !activeTypes || activeTypes.has(l.group));
  const n = sel.length;
  const ac = Math.round(sel.reduce((s, l) => s + (l.acreage || 0), 0) * 10) / 10;
  const el = document.getElementById("mf-summary");
  if (el) el.textContent = `${n} lot${n === 1 ? "" : "s"} · ${ac} acres`;
}

// ── Lot detail drawer ──────────────────────────────────────────
function selectLot(n, pan) {
  const l = LOTS.find((x) => x.id === n);
  if (!l) return;
  // Clear any prior selection AND redraw those parcels back to the base style.
  Object.entries(layers).forEach(([id, lay]) => {
    lay._selected = false;
    lay.setStyle(lotStyle({ properties: LOTS.find((x) => x.id === id) }, false));
  });
  const layer = layers[n];
  if (layer) {
    layer._selected = true;
    highlight(n, true);
    if (pan && layer.getBounds) window._map.panTo(layer.getBounds().getCenter(), { animate: true });
  }
  const gal = document.getElementById("ld-gallery");
  const imgs = l.images || [];
  gal.innerHTML = imgs.map((im) =>
    `<figure><img src="${im.src}" alt="${im.caption || l.label}" loading="lazy">` +
    (im.caption ? `<figcaption>${im.caption}</figcaption>` : "") + `</figure>`
  ).join("");
  gal.style.display = imgs.length ? "block" : "none";

  document.getElementById("ld-type").textContent = l.group_label;
  document.getElementById("ld-title").textContent = l.label;
  document.getElementById("ld-headline").textContent = l.headline;
  document.getElementById("ld-desc").textContent = l.description;
  document.getElementById("ld-status").textContent =
    l.status === "available" ? "Available" : l.status;
  document.getElementById("ld-acre").textContent = l.acreage ? l.acreage + " acres" : "—";
  const inq = document.getElementById("ld-inquire");
  inq.href = "#contact";
  inq.onclick = () => {
    const msg = document.querySelector('#contact-form [name="message"]');
    if (msg) msg.value = `${l.label} — ${l.group_label}\n`;
    closeDetail();
  };
  document.getElementById("lot-detail").hidden = false;
}
function closeDetail() {
  document.getElementById("lot-detail").hidden = true;
  Object.entries(layers).forEach(([n, lay]) => { lay._selected = false; highlight(n, false); });
}

// ── Boot ───────────────────────────────────────────────────────
document.getElementById("ld-close").onclick = closeDetail;
document.addEventListener("keydown", (e) => { if (e.key === "Escape") closeDetail(); });
wireContact();
initScrollSpy();
window.addEventListener("resize", () => { if (window._map) window._map.invalidateSize(); });
initMap().catch((err) => {
  console.error(err);
  document.getElementById("map").innerHTML =
    '<p style="padding:24px;font-family:var(--mono);color:var(--muted)">Map failed to load. ' +
    "Run via a local server (python3 -m http.server) so the lot data can be fetched.</p>";
});
