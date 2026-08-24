const api = "/api";
let activeFlight = "SKY281";
let cachedFlights = [];

const byId = (id) => document.getElementById(id);
const escapeHtml = (value) => String(value).replace(/[&<>'"]/g, (char) => ({"&":"&amp;","<":"&lt;",">":"&gt;","'":"&#39;","\"":"&quot;"}[char]));

function timeFromIso(value) {
  return new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", timeZone: "UTC" }).format(new Date(value));
}

function updateClock() {
  byId("utc-clock").textContent = new Intl.DateTimeFormat("en-GB", { hour: "2-digit", minute: "2-digit", second: "2-digit", timeZone: "UTC" }).format(new Date());
}

function countdown(value) {
  const seconds = Math.max(0, Math.ceil((new Date(value).getTime() - Date.now()) / 1000));
  return `${String(Math.floor(seconds / 60)).padStart(2, "0")}:${String(seconds % 60).padStart(2, "0")}`;
}

function statusClass(status) { return status.toLowerCase(); }

function drawCards() {
  byId("flight-cards").innerHTML = cachedFlights.map((flight) => `
    <button class="flight-card ${flight.id === activeFlight ? "selected" : ""}" data-flight="${flight.id}">
      <span class="card-status ${statusClass(flight.status)}">${escapeHtml(flight.status)}</span>
      <strong>${escapeHtml(flight.number)}</strong>
      <span class="route">${flight.origin.code} <i>→</i> ${flight.destination.code}</span>
      <small>${flight.checked_in}/${flight.capacity} checked in · ${timeFromIso(flight.scheduled_departure)} UTC</small>
    </button>`).join("");
  document.querySelectorAll("[data-flight]").forEach((button) => button.addEventListener("click", () => { activeFlight = button.dataset.flight; refresh(); }));
}

function drawFlight(flight) {
  byId("flight-detail").innerHTML = `
    <p class="eyebrow">ACTIVE FLIGHT</p>
    <div class="route-head"><div><strong>${flight.origin.code}</strong><span>${escapeHtml(flight.origin.city)}</span></div><div class="route-line"><span class="plane">✈</span><small>${flight.number}</small></div><div class="align-right"><strong>${flight.destination.code}</strong><span>${escapeHtml(flight.destination.city)}</span></div></div>
    <div class="flight-meta"><span><b>Aircraft</b>${escapeHtml(flight.aircraft.registration)} · ${escapeHtml(flight.aircraft.model)}</span><span><b>Scheduled</b>${timeFromIso(flight.scheduled_departure)} UTC</span><span><b>Status</b><em class="card-status ${statusClass(flight.status)}">${escapeHtml(flight.status)}</em></span></div>`;
  byId("next-tick-label").textContent = flight.status === "Departed" ? "Flight departed" : `Next automatic check-in in ${countdown(flight.next_tick_at)}`;
  byId("gauge").style.setProperty("--value", `${flight.occupancy_percent * 3.6}deg`);
  byId("occupancy-value").textContent = `${flight.occupancy_percent}%`;
  byId("occupancy-copy").textContent = `${flight.checked_in} of ${flight.capacity} passengers checked in`;
}

function drawManifest(flight, manifest) {
  byId("manifest-count").textContent = `${flight.checked_in} / ${flight.capacity}`;
  byId("manifest").innerHTML = manifest.map((passenger) => `
    <div class="passenger ${passenger.checked_in ? "checked" : ""}">
      <span class="avatar">${passenger.name.split(" ").map((part) => part[0]).join("")}</span>
      <span><strong>${escapeHtml(passenger.name)}</strong><small>Seat ${escapeHtml(passenger.seat)}</small></span>
      ${passenger.checked_in ? "<span class=\"check\">✓ Checked in</span>" : `<button class="checkin-button" data-passenger="${passenger.id}">Check in</button>`}
    </div>`).join("");
  document.querySelectorAll("[data-passenger]").forEach((button) => button.addEventListener("click", () => manualCheckin(button.dataset.passenger)));
}

function drawEvents(events) {
  byId("events").innerHTML = events.length ? events.slice(0, 6).map((event) => `<div class="event"><span class="event-icon">${event.source === "automatic" ? "◌" : "✓"}</span><span><strong>${escapeHtml(event.passenger_name)}</strong> checked in <small>${event.seat} · ${event.source}</small></span><time>${timeFromIso(event.at)}</time></div>`).join("") : "<p class=\"empty\">The first check-in is on its way.</p>";
}

async function manualCheckin(passengerId) {
  try {
    const response = await fetch(`${api}/flights/${activeFlight}/checkins`, { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ passenger_id: passengerId }) });
    const result = await response.json();
    if (!response.ok) throw new Error(result.detail || "Could not check in passenger.");
    byId("message").textContent = `${result.event.passenger_name} checked in successfully.`;
    await refresh();
  } catch (error) { byId("message").textContent = error.message; }
}

async function refresh() {
  try {
    const [flightsResponse, manifestResponse] = await Promise.all([fetch(`${api}/flights`), fetch(`${api}/flights/${activeFlight}/manifest`)]);
    if (!flightsResponse.ok || !manifestResponse.ok) throw new Error("Operations data is temporarily unavailable.");
    cachedFlights = await flightsResponse.json();
    const manifestData = await manifestResponse.json();
    const flight = cachedFlights.find((item) => item.id === activeFlight) || cachedFlights[0];
    activeFlight = flight.id;
    drawCards(); drawFlight(flight); drawManifest(flight, manifestData.passengers); drawEvents(manifestData.events);
  } catch (error) { byId("message").textContent = error.message; }
}

updateClock(); setInterval(updateClock, 1000); setInterval(() => { const flight = cachedFlights.find((item) => item.id === activeFlight); if (flight) drawFlight(flight); }, 1000); setInterval(refresh, 4000); refresh();
