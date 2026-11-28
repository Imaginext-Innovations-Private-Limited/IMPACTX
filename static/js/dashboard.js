
document.addEventListener("DOMContentLoaded", () => {

    // Clock
    function updateClock() {
        const now = new Date();

        document.getElementById("current-date").textContent =
            now.toLocaleDateString();

        document.getElementById("current-time").textContent =
            now.toLocaleTimeString();
    }

    updateClock();
    setInterval(updateClock, 1000);


    // Chart defaults
    Chart.defaults.color = "#91a1b9";
    Chart.defaults.borderColor = "#26364e";
    Chart.defaults.font.family = "Arial";


    const data = window.dashboardData || {};


    // Risk distribution
    const risk = data.risk || {};

    new Chart(document.getElementById("riskChart"), {
        type: "doughnut",

        data: {
            labels: [
                "High Risk",
                "Medium Risk",
                "Low Risk",
                "Unassessed"
            ],

            datasets: [{
                data: [
                    risk.high || 0,
                    risk.medium || 0,
                    risk.low || 0,
                    risk.unassessed || 0
                ],

                backgroundColor: [
                    "#ef5261",
                    "#f2ad39",
                    "#20c98b",
                    "#a16bf2"
                ],

                borderWidth: 0,
                hoverOffset: 7
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                legend: {
                    position: "bottom",
                    labels: {
                        usePointStyle: true,
                        boxWidth: 7,
                        padding: 12,
                        font: { size: 10 }
                    }
                }
            },

            cutout: "68%"
        }
    });


    // Protocol activity
    const protocols = data.protocols || [];

    new Chart(document.getElementById("protocolChart"), {
        type: "bar",

        data: {
            labels: protocols.map(item => item.name),

            datasets: [{
                label: "Recorded events",

                data: protocols.map(item => item.total),

                backgroundColor: protocols.map(item =>
                    item.simulated ? "#a16bf2" : "#3988ed"
                ),

                borderRadius: 5,
                maxBarThickness: 24
            }]
        },

        options: {
            responsive: true,
            maintainAspectRatio: false,

            plugins: {
                legend: { display: false },

                tooltip: {
                    callbacks: {
                        afterLabel: context => {
                            const item = protocols[context.dataIndex];

                            return item && item.simulated
                                ? "Simulated service"
                                : "Recorded protocol event count";
                        }
                    }
                }
            },

            scales: {
                x: {
                    grid: { display: false },
                    ticks: {
                        maxRotation: 45,
                        minRotation: 0,
                        font: { size: 9 }
                    }
                },

                y: {
                    beginAtZero: true,
                    ticks: { precision: 0 },
                    grid: { color: "#26364e" }
                }
            }
        }
    });


    // Interactive attacker geolocation map
    const mapElement = document.getElementById("attack-map");

    if (mapElement && typeof L !== "undefined") {

        const map = L.map("attack-map", {
            zoomControl: true
        }).setView([20, 0], 2);

        L.tileLayer(
            "https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png",
            {
                attribution: "&copy; OpenStreetMap contributors",
                maxZoom: 18
            }
        ).addTo(map);

        const locations = data.geolocations || [];

        const riskColors = {
            high: "#ef5261",
            medium: "#f2ad39",
            low: "#20c98b"
        };

        // Group records with identical coordinates.
        const groupedLocations = new Map();

        locations.forEach(location => {
            const lat = Number(location.latitude);
            const lon = Number(location.longitude);

            if (
                !Number.isFinite(lat) ||
                !Number.isFinite(lon) ||
                lat < -90 || lat > 90 ||
                lon < -180 || lon > 180
            ) {
                return;
            }

            const key = `${lat.toFixed(4)},${lon.toFixed(4)}`;

            if (!groupedLocations.has(key)) {
                groupedLocations.set(key, {
                    latitude: lat,
                    longitude: lon,
                    attackers: []
                });
            }

            groupedLocations.get(key).attackers.push(location);
        });

        groupedLocations.forEach(group => {
            const attackers = group.attackers;

            const highestRisk = attackers.reduce(
                (highest, item) => {
                    const score = Number(item.max_risk) || 0;
                    return Math.max(highest, score);
                },
                0
            );

            const riskLevel =
                highestRisk >= 60 ? "high" :
                highestRisk >= 30 ? "medium" : "low";

            const color = riskColors[riskLevel];

            const totalEvents = attackers.reduce(
                (sum, item) => sum + (Number(item.event_count) || 0),
                0
            );

            const attackerRows = attackers.map(item => `
                <div style="margin-top:8px;border-top:1px solid #ddd;padding-top:7px">
                    <strong>${escapeHTML(item.ip_address || "Unknown IP")}</strong><br>
                    Risk: ${escapeHTML(item.risk_level || "unknown")}
                    (${Number(item.max_risk) || 0}/100)<br>
                    Events: ${Number(item.event_count) || 0}<br>
                    ISP: ${escapeHTML(item.isp || "Unknown")}
                </div>
            `).join("");

            const first = attackers[0];

            const popup = `
                <div style="min-width:190px">
                    <strong>${escapeHTML(first.city || "Unknown city")},
                    ${escapeHTML(first.country || "Unknown country")}</strong>
                    <div style="margin-top:6px">
                        Attackers: ${attackers.length}<br>
                        Total events: ${totalEvents}<br>
                        Highest risk: ${highestRisk}/100
                    </div>
                    ${attackerRows}
                    <small style="display:block;margin-top:8px">
                        Approximate IP geolocation
                    </small>
                </div>
            `;

            L.circleMarker(
                [group.latitude, group.longitude],
                {
                    radius: Math.min(8 + attackers.length * 2, 18),
                    color: color,
                    fillColor: color,
                    fillOpacity: 0.85,
                    weight: 2
                }
            )
            .addTo(map)
            .bindPopup(popup);
        });

        setTimeout(() => map.invalidateSize(), 200);
    }


    // Event filtering
    window.filterDashboardEvents = function () {

        const query = document
            .getElementById("event-search")
            .value.toLowerCase()
            .trim();

        const risk = document
            .getElementById("event-risk-filter")
            .value;

        const rows = document.querySelectorAll(".event-row");

        let visible = 0;

        rows.forEach(row => {

            const matchesText =
                row.dataset.search.toLowerCase().includes(query);

            const matchesRisk =
                risk === "all" || row.dataset.risk === risk;

            const show = matchesText && matchesRisk;

            row.style.display = show ? "" : "none";

            if (show) visible++;
        });

        document.getElementById("event-visible-count").textContent =
            `Showing ${visible} of ${rows.length} recent events`;
    };

    window.filterDashboardEvents();


    // Escape untrusted strings before inserting popup content.
    function escapeHTML(value) {
        return String(value).replace(/[&<>"']/g, character => ({
            "&": "&amp;",
            "<": "&lt;",
            ">": "&gt;",
            '"': "&quot;",
            "'": "&#39;"
        })[character]);
    }

    // --------------------------------------------------
    // LIVE RECENT EVENTS AUTO-REFRESH
    // --------------------------------------------------

    let eventRefreshInProgress = false;

    async function refreshRecentEvents() {

        if (eventRefreshInProgress) return;

        eventRefreshInProgress = true;

        try {
            const response = await fetch(
                "/api/recent-events",
                { cache: "no-store" }
            );

            if (!response.ok) {
                throw new Error("Recent events API unavailable");
            }

            const result = await response.json();
            const events = result.events || [];

            const tableBody = document.getElementById(
                "event-table-body"
            );

            if (!tableBody) return;

            if (events.length === 0) {
                tableBody.innerHTML = `
                    <tr>
                        <td colspan="6">No events recorded.</td>
                    </tr>
                `;
                window.filterDashboardEvents();
                return;
            }

            tableBody.innerHTML = events.map(event => {

                const eventId = escapeHTML(event.event_id);
                const parsedTime = new Date(event.timestamp);

		const timestamp = escapeHTML(
			    Number.isNaN(parsedTime.getTime())
			        ? event.timestamp
	        : new Intl.DateTimeFormat("en-IN", {
        		    timeZone: "Asia/Kolkata",
        	    day: "2-digit",
        	    month: "short",
        	    hour: "2-digit",
       		     minute: "2-digit",
        	    second: "2-digit",
        	    hour12: false
       			 }).format(parsedTime)
			);
                const domain = escapeHTML(event.domain);
                const sourceIP = escapeHTML(event.source_ip);
                const eventType = escapeHTML(event.event_type);
		const commandCategory = escapeHTML(event.command || "");

               const eventLabel = commandCategory
               ? `${eventType} — ${commandCategory}`
                : eventType;
                const riskLevel = escapeHTML(
                    event.risk_level || "unassessed"
                );
                const riskScore = Number(event.risk_score) || 0;

                const searchText = escapeHTML(
    `${event.source_ip} ${event.domain} ${event.event_type} ${event.command || ""} ${event.path || "-"}`
        .toLowerCase()
);
                return `
                    <tr class="event-row"
                        data-risk="${riskLevel}"
                        data-search="${searchText}"
                        onclick="window.location.href='/event-report/${eventId}'"
                        onkeydown="if(event.key === 'Enter') window.location.href='/event-report/${eventId}'"
                        tabindex="0"
                        role="link"
                        title="Click to investigate this event">

                        <td>${timestamp}</td>
                        <td>${domain}</td>
                        <td>${sourceIP}</td>
                        <td>${eventLabel}</td>

                        <td>
                            <span class="risk-badge ${riskLevel}">
                                ${riskLevel.toUpperCase()}
                            </span>
                        </td>

                        <td>${riskScore}/100</td>
                    </tr>
                `;
            }).join("");

            window.filterDashboardEvents();

        } catch (error) {
            console.error(
                "Live events refresh failed:",
                error
            );
        } finally {
            eventRefreshInProgress = false;
        }
    }

    // Load immediately, then refresh every 3 seconds.
    refreshRecentEvents();
    setInterval(refreshRecentEvents, 3000);

});
