function buildPopup(pothole) {
  const image = pothole.thumbnail_url
    ? `<img src="${pothole.thumbnail_url}" alt="Pothole thumbnail">`
    : "";
  const progress = pothole.funding_goal_cents
    ? Math.min(100, Math.floor((pothole.amount_raised_cents / pothole.funding_goal_cents) * 100))
    : 0;

  return `
    <div class="popup-card">
      ${image}
      <div style="font-weight:800; margin-bottom:4px; color:#ffffff;">${pothole.pothole_name || pothole.status_label}</div>
      <div style="font-size:13px; color:#808080;">${pothole.severity_label}</div>
      <div style="font-size:13px; margin-top:8px; color:#ffffff;">${(pothole.amount_raised_cents / 100).toFixed(0)} / ${(pothole.funding_goal_cents || 0) / 100}</div>
      <div style="margin-top:8px; height:8px; background:#1b1b1b; border-radius:999px; overflow:hidden;">
        <div style="height:100%; width:${progress}%; background:#ffa31a;"></div>
      </div>
      <a href="${pothole.detail_url}" style="display:inline-block; margin-top:12px; font-weight:700; color:#ffa31a;">Open detail</a>
    </div>
  `;
}

function initStaticMap(element) {
  const lat = parseFloat(element.dataset.lat || "");
  const lng = parseFloat(element.dataset.lng || "");
  if (Number.isNaN(lat) || Number.isNaN(lng)) return;

  const map = L.map(element, { zoomControl: false, dragging: false, scrollWheelZoom: false, doubleClickZoom: false, boxZoom: false, keyboard: false, tap: false });
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);
  L.marker([lat, lng]).addTo(map);
  map.setView([lat, lng], 16);
}

function renderNearbyWarnings(items) {
  const container = document.querySelector("#nearby-warning-container");
  const overrideRow = document.querySelector("#duplicate-override-row");
  if (!container || !overrideRow) return;

  if (!items.length) {
    container.innerHTML = "";
    overrideRow.classList.add("hidden");
    overrideRow.classList.remove("flex");
    return;
  }

  container.innerHTML = `
    <div class="rounded-[1.75rem] border border-ember/30 bg-coal p-5 text-white">
      <div class="text-xs uppercase tracking-[0.24em] text-ember">Possible duplicate</div>
      <h3 class="mt-2 font-display text-2xl font-bold">Looks like someone may have already found this hole.</h3>
      <p class="mt-3 text-sm leading-6 text-white/68">Check the nearby approved reports below before creating a new one.</p>
      <div class="mt-4 grid gap-3">
        ${items
          .map(
            (item) => `
            <a href="${item.detail_url}" class="grid gap-3 rounded-3xl border border-smoke/25 bg-pitch/70 p-3 sm:grid-cols-[88px_1fr_auto]">
              <div class="overflow-hidden rounded-2xl bg-pitch">
                ${item.thumbnail_url ? `<img src="${item.thumbnail_url}" alt="Nearby pothole" class="h-20 w-full object-cover">` : `<div class="flex h-20 items-center justify-center text-xs uppercase tracking-[0.22em] text-smoke">No image</div>`}
              </div>
              <div>
                <div class="font-semibold">${item.public_id}</div>
                <div class="mt-1 text-sm text-smoke">${item.status_label}</div>
              </div>
              <div class="text-sm font-semibold text-smoke">${Math.round(item.distance_meters)}m</div>
            </a>
          `
          )
          .join("")}
      </div>
    </div>
  `;
  overrideRow.classList.remove("hidden");
  overrideRow.classList.add("flex");
}

function initSubmitMap(element) {
  const latInput = document.querySelector(element.dataset.latInput);
  const lngInput = document.querySelector(element.dataset.lngInput);
  const status = document.querySelector("#location-status");
  const useLocationButton = document.querySelector("#use-location-btn");
  if (!latInput || !lngInput) return;

  const startingLat = parseFloat(latInput.value || "41.8781");
  const startingLng = parseFloat(lngInput.value || "-87.6298");
  const map = L.map(element).setView([startingLat, startingLng], 12);
  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  let marker = null;
  function setPoint(lat, lng, updateView = true) {
    latInput.value = lat.toFixed(6);
    lngInput.value = lng.toFixed(6);
    status.textContent = `Pinned at ${lat.toFixed(5)}, ${lng.toFixed(5)}.`;

    if (!marker) {
      marker = L.marker([lat, lng]).addTo(map);
    } else {
      marker.setLatLng([lat, lng]);
    }

    if (updateView) {
      map.setView([lat, lng], 16);
    }
    fetch(`/api/nearby?lat=${lat}&lng=${lng}`)
      .then((response) => response.json())
      .then((items) => renderNearbyWarnings(items))
      .catch(() => {});
  }

  if (!Number.isNaN(parseFloat(latInput.value)) && !Number.isNaN(parseFloat(lngInput.value))) {
    setPoint(parseFloat(latInput.value), parseFloat(lngInput.value), false);
  }

  map.on("click", (event) => setPoint(event.latlng.lat, event.latlng.lng));

  latInput.addEventListener("change", () => {
    if (latInput.value && lngInput.value) {
      setPoint(parseFloat(latInput.value), parseFloat(lngInput.value));
    }
  });
  lngInput.addEventListener("change", () => {
    if (latInput.value && lngInput.value) {
      setPoint(parseFloat(latInput.value), parseFloat(lngInput.value));
    }
  });

  useLocationButton?.addEventListener("click", () => {
    if (!navigator.geolocation) {
      status.textContent = "Geolocation is not available on this device.";
      return;
    }
    status.textContent = "Finding your location...";
    navigator.geolocation.getCurrentPosition(
      (position) => {
        setPoint(position.coords.latitude, position.coords.longitude);
      },
      () => {
        status.textContent = "Could not access your location. Tap the map instead.";
      }
    );
  });
}

function initPublicMap(element) {
  const map = L.map(element).setView([41.8781, -87.6298], 11);
  const markersLayer = L.layerGroup().addTo(map);
  const filters = Array.from(document.querySelectorAll(".map-status-filter"));
  let potholes = [];

  L.tileLayer("https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png", {
    attribution: "&copy; OpenStreetMap contributors",
  }).addTo(map);

  function activeStatuses() {
    return filters.filter((filter) => filter.checked).map((filter) => filter.value);
  }

  function drawMarkers() {
    markersLayer.clearLayers();
    const enabled = new Set(activeStatuses());
    potholes
      .filter((pothole) => enabled.has(pothole.status))
      .forEach((pothole) => {
        const marker = L.marker([pothole.latitude, pothole.longitude]);
        marker.bindPopup(buildPopup(pothole));
        marker.addTo(markersLayer);
      });
  }

  fetch(element.dataset.endpoint || "/api/potholes")
    .then((response) => response.json())
    .then((items) => {
      potholes = items;
      drawMarkers();
    })
    .catch(() => {});

  filters.forEach((filter) => filter.addEventListener("change", drawMarkers));
}

document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll("[data-static-map='true']").forEach(initStaticMap);

  const submitMap = document.querySelector("#submit-map");
  if (submitMap) initSubmitMap(submitMap);

  const publicMap = document.querySelector("#public-map");
  if (publicMap) initPublicMap(publicMap);
});
