import MatrixRain from "./MatrixRain";
import AssistantBot from "./AssistantBot";
import { useEffect, useMemo, useRef, useState } from "react";
import Globe from "react-globe.gl";
import * as THREE from "three";
import {
  Area,
  AreaChart,
  CartesianGrid,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import {
  Activity,
  AlertTriangle,
  ArrowDownToLine,
  ArrowLeft,
  ArrowUpFromLine,
  ChevronRight,
  FileText,
  Globe2,
  LayoutDashboard,
  Network,
  Radar,
  Radio,
  ShieldAlert,
  ShieldCheck,
  Wifi,
  RefreshCw,
} from "lucide-react";
import "./App.css";

const API = "http://127.0.0.1:5000";

// Photographic Earth surface plus relief bump map, served from the same CDN
// pattern the dashboard already uses. Blue Marble is NASA imagery shipped with
// the three-globe package.
const EARTH_TEXTURE =
  "https://unpkg.com/three-globe/example/img/earth-blue-marble.jpg";
const EARTH_BUMP =
  "https://unpkg.com/three-globe/example/img/earth-topology.png";

const detectors = [
  { key: "ddos", name: "DDoS Detection", icon: ShieldAlert, color: "#ff596b" },
  { key: "c2", name: "C2 Beaconing", icon: Radio, color: "#22d3ee" },
  { key: "exfiltration", name: "Data Exfiltration", icon: ArrowUpFromLine, color: "#b18aff" },
  { key: "dns", name: "DNS Tunnelling", icon: Globe2, color: "#f6c85f" },
];

const tabs = [
  { key: "dashboard", label: "Home", icon: LayoutDashboard },
  { key: "network", label: "Network", icon: Network },
  { key: "reports", label: "Reports", icon: FileText },
];

// Used only until the backend reports the machine's real capture adapters.
const fallbackInterfaceOptions = [
  { id: "4", label: "Wi-Fi · Interface 4" },
  { id: "1", label: "Interface 1" },
  { id: "9", label: "Ethernet · Interface 9" },
];

// A Wi-Fi adapter is labelled with the network it is joined to, so the capture
// controls name what this device is actually connected to.
const interfaceLabelOf = (item) =>
  item.wifi_name
    ? `Wi-Fi · ${item.wifi_name}`
    : item.name || `Interface ${item.id}`;

// Nothing about the map's location layer is invented here. Arc lines and
// markers are built only from addresses observed in a real capture, resolved
// to coordinates on the backend. Until a capture produces such data the globe
// draws no routes at all.
const toCoordinate = (item) => {
  const lat = Number(item?.lat);
  const lng = Number(item?.lng);

  if (!Number.isFinite(lat) || !Number.isFinite(lng)) return null;

  return { ...item, lat, lng };
};

// Arc, marker and ring colours follow the detector verdict for the traffic
// that reached each location: calm cyan when nothing was flagged, warming to
// red as the strongest non-benign verdict's confidence rises.
const THREAT_STYLES = {
  none: { color: "#35d9f4", stroke: 0.3, size: 0.24, label: "No threat detected", tag: "Clear" },
  low: { color: "#ffe873", stroke: 0.38, size: 0.28, label: "Low threat", tag: "Low" },
  medium: { color: "#ffb020", stroke: 0.46, size: 0.32, label: "Medium threat", tag: "Medium" },
  high: { color: "#ff6b3d", stroke: 0.54, size: 0.36, label: "High threat", tag: "High" },
  critical: { color: "#ff2d55", stroke: 0.64, size: 0.42, label: "Critical threat", tag: "Critical" },
};

const threatLevelOf = (item) => {
  const level = String(item?.threat?.level || "none").toLowerCase();

  return THREAT_STYLES[level] ? level : "none";
};

const threatStyleOf = (item) => THREAT_STYLES[threatLevelOf(item)];

const threatTextOf = (item) => {
  const style = threatStyleOf(item);
  const threat = item?.threat;
  const parts = [style.label];

  if (threat?.detector) parts.push(threat.detector);

  const confidence = Number(threat?.confidence);

  if (Number.isFinite(confidence) && confidence > 0) {
    parts.push(`${Math.round(confidence * 100)}% confidence`);
  }

  return parts.join(" · ");
};

// Illustrative satellites: circular orbits described by inclination and RAAN.
// They are part of the visual layer, not observed space traffic.
const satelliteDefs = [
  { inclination: 51.6, raan: 20, altitude: 0.13, period: 150, scale: 0.95, color: "#9fe8ff" },
  { inclination: 98.2, raan: 145, altitude: 0.18, period: 205, scale: 0.85, color: "#c9b6ff" },
  { inclination: 28.5, raan: 258, altitude: 0.24, period: 265, scale: 0.78, color: "#a6ffe0" },
];

// Illustrative Moon on a wide, gently inclined orbit. Earth's radius is 100
// units in this scene, so altitude 1.05 puts the Moon 205 units from the centre.
const MOON_TEXTURE = "/textures/moon.jpg";

const moonDef = {
  radius: 7.5,
  altitude: 1.05,
  inclination: 18,
  raan: 42,
  period: 180,
};

const DEG = Math.PI / 180;

// Ground-track point for a circular orbit at argument of latitude u.
const orbitalPosition = (inclination, raan, u) => {
  const inc = inclination * DEG;

  return {
    lat: Math.asin(Math.sin(inc) * Math.sin(u)) / DEG,
    lng: raan + Math.atan2(Math.cos(inc) * Math.sin(u), Math.cos(u)) / DEG,
  };
};

// A small spacecraft: pressurised body, two solar wings on booms, dish antenna.
function createSatelliteModel(color) {
  const group = new THREE.Group();
  group.name = "CYVORA-SAT";

  const bodyMaterial = new THREE.MeshStandardMaterial({
    color: "#dce8f2",
    metalness: 0.85,
    roughness: 0.28,
    emissive: new THREE.Color("#16303f"),
    emissiveIntensity: 0.5,
  });
  const panelMaterial = new THREE.MeshStandardMaterial({
    color: "#1b5fa8",
    metalness: 0.7,
    roughness: 0.22,
    emissive: new THREE.Color("#0a2a4d"),
    emissiveIntensity: 0.55,
  });
  const metalMaterial = new THREE.MeshStandardMaterial({
    color: "#9db4c6",
    metalness: 0.9,
    roughness: 0.35,
    emissive: new THREE.Color(color),
    emissiveIntensity: 0.12,
  });

  const body = new THREE.Mesh(
    new THREE.BoxGeometry(1.4, 1.4, 2.6),
    bodyMaterial
  );

  const wingGeometry = new THREE.BoxGeometry(4.6, 0.08, 2.2);
  const leftWing = new THREE.Mesh(wingGeometry, panelMaterial);
  leftWing.position.x = -3.5;
  const rightWing = new THREE.Mesh(wingGeometry, panelMaterial);
  rightWing.position.x = 3.5;

  const boomGeometry = new THREE.BoxGeometry(2.4, 0.14, 0.14);
  const leftBoom = new THREE.Mesh(boomGeometry, metalMaterial);
  leftBoom.position.x = -1.8;
  const rightBoom = new THREE.Mesh(boomGeometry, metalMaterial);
  rightBoom.position.x = 1.8;

  const dish = new THREE.Mesh(
    new THREE.SphereGeometry(0.55, 14, 14),
    metalMaterial
  );
  dish.scale.set(1, 0.45, 1);
  dish.position.z = 1.6;

  group.add(body, leftWing, rightWing, leftBoom, rightBoom, dish);
  group.userData.meshes = [body, leftWing, rightWing, leftBoom, rightBoom, dish];

  return group;
}

const isThreatRecord = (item) =>
  Boolean(item.prediction) &&
  !String(item.prediction).toLowerCase().includes("benign");

const formatTimestamp = (value) => {
  if (!value) return "—";

  const date = new Date(value);
  if (Number.isNaN(date.getTime())) return "—";

  return date.toLocaleString(undefined, {
    day: "2-digit",
    month: "short",
    hour: "2-digit",
    minute: "2-digit",
  });
};

function StatCard({ label, value, Icon, note }) {
  return (
    <article className="panel stat">
      <div className="stat-top">
        <span>{label}</span>
        <Icon />
      </div>
      <strong>{value}</strong>
      <small>{note}</small>
    </article>
  );
}

function CaptureControls({
  interfaceId,
  interfaceOptions,
  onInterfaceChange,
  duration,
  onDurationChange,
  loading,
  elevated,
  onCapture,
}) {
  return (
    <section className="capture-controls panel">
      <div className="capture-title">
        <Wifi size={19} />
        <div>
          <strong>LIVE NETWORK CAPTURE</strong>
          <small>Capture traffic using your selected TShark interface</small>
          {elevated === false && (
            <small className="capture-hint">
              Administrator rights are missing, so Windows asks on every
              capture. Restart the backend once and accept the prompt.
            </small>
          )}
        </div>
      </div>

      <div className="capture-actions">
        <select
          value={interfaceId}
          onChange={(event) => onInterfaceChange(event.target.value)}
          disabled={loading}
        >
          {interfaceOptions.map((option) => (
            <option key={option.id} value={option.id}>
              {option.label}
            </option>
          ))}
        </select>

        <select
          value={duration}
          onChange={(event) => onDurationChange(event.target.value)}
          disabled={loading}
        >
          <option value="10">10 seconds</option>
          <option value="15">15 seconds</option>
          <option value="30">30 seconds</option>
        </select>

        <button className="capture-button" onClick={onCapture} disabled={loading}>
          {loading ? (
            <>
              <RefreshCw size={15} className="spin" /> CAPTURING
            </>
          ) : (
            <>
              <Activity size={15} /> START CAPTURE
            </>
          )}
        </button>
      </div>
    </section>
  );
}

function DetectorModules({ health }) {
  return (
    <aside className="panel detector-panel">
      <div className="section-heading">
        <h2>DETECTION MODULES</h2>
        <span className="live-label">MODEL STATUS</span>
      </div>

      {detectors.map((detector) => {
        const Icon = detector.icon;
        const status = health?.detectors?.[detector.key] || "Unavailable";

        return (
          <div className="detector" key={detector.key}>
            <span className="detector-icon" style={{ color: detector.color }}>
              <Icon size={20} />
            </span>
            <div className="detector-info">
              <strong>{detector.name}</strong>
              <small style={{ color: detector.color }}>{status}</small>
            </div>
            <span
              className="module-dot"
              style={{
                background: status === "loaded" ? "#35d49a" : "#e4ae54",
              }}
            />
          </div>
        );
      })}

      <div className="detector-note">
        Live prediction coverage varies by detector. Check capture summary for
        skipped predictions.
      </div>
    </aside>
  );
}

function ThreatAlerts({ alerts, total }) {
  return (
    <aside className="panel alert-panel">
      <div className="section-heading">
        <h2>THREAT ALERTS</h2>
        <span className="alert-count">{total}</span>
      </div>

      {alerts.length === 0 ? (
        <div className="alert-empty">
          <ShieldCheck size={28} />
          <p>No threat records in recent history</p>
          <small>Run a capture to generate detection results</small>
        </div>
      ) : (
        alerts.map((alert, index) => (
          <div className="alert-item" key={alert._id || index}>
            <AlertTriangle size={16} />
            <div>
              <strong>{alert.prediction}</strong>
              <small>
                {alert.detector || "Detector"} · Confidence:{" "}
                {alert.confidence ?? "N/A"}
              </small>
            </div>
          </div>
        ))
      )}
    </aside>
  );
}

function DetectionHistory({ history, onRefresh, limit }) {
  return (
    <article className="panel history-panel">
      <div className="history-heading">
        <h2>RECENT DETECTIONS</h2>
        <button onClick={onRefresh}>
          <RefreshCw size={13} /> REFRESH
        </button>
      </div>

      {history.length === 0 ? (
        <div className="empty-chart">No detection history available.</div>
      ) : (
        <div className="history-list">
          {history.slice(0, limit).map((item, index) => (
            <div className="history-item" key={item._id || index}>
              <div>
                <strong>{item.prediction || "Unknown"}</strong>
                <small>{item.detector || "Detector"}</small>
              </div>
              <span>{item.confidence ?? "—"}</span>
            </div>
          ))}
        </div>
      )}
    </article>
  );
}

function CaptureOverview({ chartData }) {
  return (
    <article className="panel traffic-panel">
      <div className="section-heading">
        <h2>CAPTURE OVERVIEW</h2>
        <span>LAST SESSION</span>
      </div>

      {chartData.length ? (
        <ResponsiveContainer width="100%" height={210}>
          <AreaChart data={chartData}>
            <defs>
              <linearGradient id="packetFill" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stopColor="#20c9e8" stopOpacity={0.35} />
                <stop offset="100%" stopColor="#20c9e8" stopOpacity={0.02} />
              </linearGradient>
            </defs>
            <CartesianGrid stroke="#1b3043" strokeDasharray="3 3" />
            <XAxis dataKey="time" stroke="#7890a5" />
            <YAxis stroke="#7890a5" />
            <Tooltip
              contentStyle={{
                background: "rgba(12, 26, 41, 0.55)",
                border: "1px solid rgba(126, 214, 245, 0.22)",
                borderRadius: 8,
                backdropFilter: "blur(16px) saturate(150%)",
                WebkitBackdropFilter: "blur(16px) saturate(150%)",
                boxShadow: "0 8px 28px rgba(0, 0, 0, 0.35)",
              }}
              itemStyle={{ color: "#dceaf5" }}
              labelStyle={{ color: "#8edff0" }}
            />
            <Area
              type="monotone"
              dataKey="packets"
              stroke="#20c9e8"
              fill="url(#packetFill)"
            />
          </AreaChart>
        </ResponsiveContainer>
      ) : (
        <div className="empty-chart">
          Start a capture to display session packet data.
        </div>
      )}
    </article>
  );
}

function CaptureSummary({ capture, summary }) {
  return (
    <section className="panel capture-summary">
      <h2>LATEST CAPTURE SUMMARY</h2>
      <p>
        {capture.packet_count} packets · {capture.flow_count} flows
      </p>
      <div className="summary-grid">
        {detectors.map((detector) => {
          const result = summary[detector.key];

          return (
            <div key={detector.key}>
              <strong>{detector.name}</strong>
              <small>
                {result
                  ? `${result.predictions_completed ?? 0} completed · ${
                      result.skipped ?? 0
                    } skipped`
                  : "No prediction summary returned"}
              </small>
            </div>
          );
        })}
      </div>
    </section>
  );
}

function ConnectedLocations({ geo }) {
  const origin = toCoordinate(geo?.origin);
  const locations = useMemo(() => {
    if (!Array.isArray(geo?.locations)) return [];

    return geo.locations.map((item) => toCoordinate(item)).filter(Boolean);
  }, [geo]);

  const hostLabel = origin
    ? `${origin.city || origin.country || "Unknown"}${
        origin.city && origin.country ? `, ${origin.country}` : ""
      }`
    : null;

  return (
    <article className="panel locations-panel">
      <div className="section-heading">
        <h2>CONNECTED LOCATIONS</h2>
        <span className="alert-count">{locations.length}</span>
      </div>

      {!origin ? (
        <div className="alert-empty">
          <Globe2 size={28} />
          <p>No device locations resolved yet</p>
          <small>Run a capture to see where connected devices are</small>
        </div>
      ) : (
        <div className="location-list">
          <div className="location-row location-row--host">
            <span
              className="location-dot"
              style={{ background: "#35e6a3", color: "#35e6a3" }}
              aria-hidden="true"
            />
            <div className="location-text">
              <strong>{hostLabel}</strong>
              <small>{origin.ip} · host device</small>
            </div>
            <span className="location-tag location-tag--host">Host</span>
          </div>

          {locations.length === 0 ? (
            <div className="empty-chart">
              Host location resolved, but no connected device addresses could be
              geolocated in this capture.
            </div>
          ) : (
            locations.map((location) => {
              const style = threatStyleOf(location);
              const flows = location.connections ?? 0;

              return (
                <div className="location-row" key={`${location.ip}-${location.lat}-${location.lng}`}>
                  <span
                    className="location-dot"
                    style={{ background: style.color, color: style.color }}
                    aria-hidden="true"
                  />
                  <div className="location-text">
                    <strong>
                      {location.city || location.country || "Unknown location"}
                      {location.city && location.country
                        ? `, ${location.country}`
                        : ""}
                    </strong>
                    <span
                      className={`location-dns${
                        location.hostname ? "" : " location-dns--empty"
                      }`}
                    >
                      {location.hostname || "DNS name not observed"}
                    </span>
                    <small>
                      {location.ip} · {flows} flow{flows === 1 ? "" : "s"}
                      {location.threat?.detector
                        ? ` · ${location.threat.detector}`
                        : ""}
                    </small>
                    <span className="location-apps">
                      {location.ports?.map((endpoint) => (
                        <span
                          className="location-port"
                          key={`${endpoint.port}-${endpoint.protocol}`}
                          title={`Seen in ${endpoint.flows} captured flow${
                            endpoint.flows === 1 ? "" : "s"
                          }`}
                        >
                          {endpoint.port
                            ? `${endpoint.port}/${endpoint.protocol}`
                            : endpoint.protocol}
                        </span>
                      ))}
                      {location.applications?.length ? (
                        location.applications.map((app) => (
                          <span className="location-app" key={app.name}>
                            {app.name}
                            {app.connections > 1 ? ` ×${app.connections}` : ""}
                          </span>
                        ))
                      ) : (
                        <span className="location-app location-app--empty">
                          Application not identified
                        </span>
                      )}
                    </span>
                  </div>
                  <span
                    className="location-tag"
                    style={{ color: style.color, borderColor: `${style.color}66` }}
                    title={threatTextOf(location)}
                  >
                    {style.tag}
                  </span>
                </div>
              );
            })
          )}
        </div>
      )}
    </article>
  );
}

function ThreatIntelligenceContent({
  threats,
  benign,
  averageConfidence,
  detectors,
  loadedDetectors,
  health,
  history,
}) {
  return (
    <>
      <section className="stats">
        <StatCard
          label="THREAT RECORDS"
          value={threats.length}
          Icon={ShieldAlert}
          note="Latest 20 history records"
        />
        <StatCard
          label="BENIGN RECORDS"
          value={benign.length}
          Icon={ShieldCheck}
          note="Latest 20 history records"
        />
        <StatCard
          label="AVG CONFIDENCE"
          value={
            averageConfidence === null
              ? "—"
              : averageConfidence <= 1
              ? `${(averageConfidence * 100).toFixed(1)}%`
              : averageConfidence.toFixed(1)
          }
          Icon={Activity}
          note="Across recent records"
        />
        <StatCard
          label="ACTIVE DETECTORS"
          value={`${loadedDetectors} / ${detectors.length}`}
          Icon={Radio}
          note="Model load status"
        />
      </section>

      <section className="panel ti-detectors">
        <div className="section-heading">
          <h2>DETECTION MODULES</h2>
          <span className="live-label">MODEL STATUS</span>
        </div>

        <div className="detector-cards">
          {detectors.map((detector) => {
            const Icon = detector.icon;
            const status = health?.detectors?.[detector.key] || "Unavailable";

            return (
              <div
                className="detector-card"
                key={detector.key}
                style={{ borderColor: `${detector.color}33` }}
              >
                <span
                  className="detector-icon"
                  style={{ color: detector.color }}
                >
                  <Icon size={20} />
                </span>
                <div className="detector-info">
                  <strong>{detector.name}</strong>
                  <small style={{ color: detector.color }}>{status}</small>
                  <small className="detector-source">
                    {status === "loaded"
                      ? "Model loaded · live capture enabled"
                      : "Status unavailable · check backend"}
                  </small>
                </div>
              </div>
            );
          })}
        </div>

        <div className="detector-note">
          Live prediction coverage varies by detector. Check capture summary
          for skipped predictions.
        </div>
      </section>

      <section className="panel records-panel">
        <div className="section-heading">
          <h2>THREAT RECORDS</h2>
          <span>
            {threats.length} of {history.length} recent
          </span>
        </div>

        {threats.length === 0 ? (
          <div className="alert-empty">
            <ShieldCheck size={28} />
            <p>No threat records in recent history</p>
            <small>Run a capture to generate detection results</small>
          </div>
        ) : (
          <div className="record-table">
            <div className="record-row record-head">
              <span>Verdict</span>
              <span>Detector</span>
              <span>Confidence</span>
              <span>Detected</span>
            </div>
            {threats.map((item, index) => (
              <div className="record-row" key={item._id || index}>
                <span className="record-verdict">{item.prediction}</span>
                <span className="record-meta">
                  {item.detector || item.detector_key || "Detector"}
                </span>
                <span className="record-meta">
                  {item.confidence ?? "—"}
                </span>
                <span className="record-time">
                  {formatTimestamp(item.created_at)}
                </span>
              </div>
            ))}
          </div>
        )}
      </section>
    </>
  );
}
function Starfield() {
  const stars = useMemo(() => {
    // Deterministic pseudo-random: same stars on every render, no state needed.
    const pseudo = (n) => {
      const x = Math.sin(n * 127.1 + 311.7) * 43758.5453;
      return x - Math.floor(x);
    };
    return Array.from({ length: 46 }, (_, i) => ({
      left: pseudo(i + 1) * 100,
      top: pseudo(i + 101) * 100,
      size: pseudo(i + 201) > 0.85 ? 3 : pseudo(i + 302) > 0.5 ? 2 : 1,
      delay: pseudo(i + 401) * 6,
      duration: 2.4 + pseudo(i + 501) * 4.6,
    }));
  }, []);

  return (
    <span className="starfield">
      {stars.map((star, index) => (
        <i
          key={index}
          style={{
            left: `${star.left}%`,
            top: `${star.top}%`,
            width: star.size,
            height: star.size,
            animationDelay: `${star.delay}s`,
            animationDuration: `${star.duration}s`,
          }}
        />
      ))}
    </span>
  );
}

function GlobalMap({ galaxy = false, geo = null }) {
  const [fullscreen, setFullscreen] = useState(false);
  const [size, setSize] = useState({ width: 0, height: 0 });
  const [ready, setReady] = useState(false);
  const containerRef = useRef(null);
  const globeRef = useRef(null);
  const pointerStart = useRef(null);
  const [mapHover, setMapHover] = useState({ on: false, x: 0, y: 0 });

  // Only real, resolved observations reach the globe.
  const origin = useMemo(() => toCoordinate(geo?.origin), [geo]);

  const locations = useMemo(() => {
    if (!Array.isArray(geo?.locations)) return [];

    return geo.locations
      .map((item) => toCoordinate(item))
      .filter((item) => Boolean(item));
  }, [geo]);

  const arcData = useMemo(() => {
    if (!origin) return [];

    return locations.map((location) => {
      const style = threatStyleOf(location);

      return {
        startLat: origin.lat,
        startLng: origin.lng,
        endLat: location.lat,
        endLng: location.lng,
        color: style.color,
        stroke: style.stroke,
        label: `${location.city || location.ip} · ${location.connections ?? 1} flow${
          (location.connections ?? 1) === 1 ? "" : "s"
        } · ${threatTextOf(location)}`,
      };
    });
  }, [origin, locations]);

  const pointData = useMemo(() => {
    if (!origin) return [];

    return [
      {
        ...origin,
        color: "#35e6a3",
        size: 0.42,
        label: `This machine · ${origin.city || origin.ip}`,
      },
      ...locations.map((location) => {
        const style = threatStyleOf(location);

        return {
          ...location,
          color: style.color,
          size: style.size,
          label: `${location.city || "Unknown"}${
            location.country ? `, ${location.country}` : ""
          } · ${location.ip} · ${threatTextOf(location)}`,
        };
      }),
    ];
  }, [origin, locations]);

  const ringData = useMemo(() => {
    const rings = origin
      ? [{ lat: origin.lat, lng: origin.lng, color: "#35e6a3", maxRadius: 4 }]
      : [];

    locations.forEach((location) => {
      const level = threatLevelOf(location);

      if (level !== "high" && level !== "critical") return;

      rings.push({
        lat: location.lat,
        lng: location.lng,
        color: THREAT_STYLES[level].color,
        maxRadius: 3.2,
      });
    });

    return rings;
  }, [origin, locations]);

  const threatLegend = useMemo(
    () =>
      Object.entries(THREAT_STYLES).map(([level, style]) => ({
        level,
        ...style,
      })),
    []
  );

  const reducedMotion =
    typeof window !== "undefined" &&
    window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  // Size the WebGL canvas to the panel box. clientWidth/clientHeight ignore the
  // float animation's transform, so the globe does not resize while drifting.
  useEffect(() => {
    const container = containerRef.current;
    if (!container) return undefined;

    const measure = () => {
      setSize({
        width: Math.max(240, Math.round(container.clientWidth)),
        height: Math.max(240, Math.round(container.clientHeight)),
      });
    };

    measure();
    const observer = new ResizeObserver(measure);
    observer.observe(container);

    return () => observer.disconnect();
  }, []);

  useEffect(() => {
    if (!ready) return;

    const globe = globeRef.current;
    if (!globe) return;

    // Development-only handle for inspecting the scene in the browser.
    if (import.meta.env.DEV) window.__cyvoraGlobe = globe;

    const controls = globe.controls();
    controls.autoRotate = true;
    // Slow, continuous drift.
    controls.autoRotateSpeed = 0.32;
    controls.enableZoom = false;
    controls.enablePan = false;
    controls.enableDamping = true;
    controls.dampingFactor = 0.12;

    // Start looking at this machine's observed location, or a neutral view
    // before any capture has produced a location.
    if (origin) {
      globe.pointOfView({ lat: origin.lat, lng: origin.lng, altitude: 1.9 }, 0);
    } else {
      globe.pointOfView({ lat: 16, lng: 78, altitude: 1.74 }, 0);
    }
  }, [ready, fullscreen, origin]);

  // Orbit the satellites in real 3D, in the same space as the Earth sphere.
  useEffect(() => {
    if (!ready) return undefined;

    const globe = globeRef.current;
    if (!globe) return undefined;

    const scene = globe.scene();
    const tracked = [];

    satelliteDefs.forEach((definition) => {
      const model = createSatelliteModel(definition.color);
      model.scale.setScalar(definition.scale);
      scene.add(model);

      // Trace the same orbit the satellite follows, as a faint ring.
      const points = [];
      const steps = 180;

      for (let step = 0; step < steps; step += 1) {
        const u = (step / steps) * Math.PI * 2;
        const { lat, lng } = orbitalPosition(
          definition.inclination,
          definition.raan,
          u
        );
        points.push(globe.getCoords(lat, lng, definition.altitude));
      }

      const ringGeometry = new THREE.BufferGeometry().setFromPoints(points);
      const ringMaterial = new THREE.LineBasicMaterial({
        color: definition.color,
        transparent: true,
        opacity: 0.16,
      });
      const ring = new THREE.LineLoop(ringGeometry, ringMaterial);
      ring.name = "CYVORA-ORBIT";
      scene.add(ring);

      tracked.push({ definition, model, ring, ringGeometry, ringMaterial });
    });

    // The Moon: a texture-mapped sphere on its own wide orbit.
    const moonTexture = new THREE.TextureLoader().load(MOON_TEXTURE);
    moonTexture.colorSpace = THREE.SRGBColorSpace;

    const moonGeometry = new THREE.SphereGeometry(moonDef.radius, 48, 48);
    const moonMaterial = new THREE.MeshStandardMaterial({
      map: moonTexture,
      bumpMap: moonTexture,
      bumpScale: 0.02,
      roughness: 0.98,
      metalness: 0,
      emissive: new THREE.Color("#1c2128"),
      emissiveIntensity: 0.6,
    });
    const moon = new THREE.Mesh(moonGeometry, moonMaterial);
    moon.name = "CYVORA-MOON";
    scene.add(moon);

    const moonOrbitPoints = [];

    for (let step = 0; step < 240; step += 1) {
      const u = (step / 240) * Math.PI * 2;
      const { lat, lng } = orbitalPosition(
        moonDef.inclination,
        moonDef.raan,
        u
      );
      moonOrbitPoints.push(globe.getCoords(lat, lng, moonDef.altitude));
    }

    const moonRingGeometry = new THREE.BufferGeometry().setFromPoints(
      moonOrbitPoints
    );
    const moonRingMaterial = new THREE.LineBasicMaterial({
      color: "#9fb4c7",
      transparent: true,
      opacity: 0.1,
    });
    const moonRing = new THREE.LineLoop(moonRingGeometry, moonRingMaterial);
    moonRing.name = "CYVORA-MOON-ORBIT";
    scene.add(moonRing);

    const startedAt = performance.now();
    let frameId;

    const animate = () => {
      const elapsed = (performance.now() - startedAt) / 1000;

      tracked.forEach(({ definition, model }) => {
        const u = (elapsed / definition.period) * Math.PI * 2;
        const { lat, lng } = orbitalPosition(
          definition.inclination,
          definition.raan,
          u
        );

        model.position.copy(
          globe.getCoords(lat, lng, definition.altitude)
        );
        // Point the dish at the Earth, wings broadside to the orbit track.
        model.lookAt(0, 0, 0);
        model.rotateZ(u * 0.5);
      });

      const moonU = (elapsed / moonDef.period) * Math.PI * 2;
      const moonSpot = orbitalPosition(
        moonDef.inclination,
        moonDef.raan,
        moonU
      );
      moon.position.copy(
        globe.getCoords(moonSpot.lat, moonSpot.lng, moonDef.altitude)
      );
      // Tidally locked, like the real Moon: one face stays toward the Earth.
      moon.lookAt(0, 0, 0);

      frameId = requestAnimationFrame(animate);
    };

    animate();

    return () => {
      cancelAnimationFrame(frameId);

      tracked.forEach(({ model, ring, ringGeometry, ringMaterial }) => {
        scene.remove(model);
        scene.remove(ring);
        model.userData.meshes.forEach((mesh) => {
          mesh.geometry.dispose();
          mesh.material.dispose();
        });
        ringGeometry.dispose();
        ringMaterial.dispose();
      });

      scene.remove(moon);
      scene.remove(moonRing);
      moonGeometry.dispose();
      moonMaterial.dispose();
      moonTexture.dispose();
      moonRingGeometry.dispose();
      moonRingMaterial.dispose();
    };
  }, [ready]);
  

  useEffect(() => {
    const onKeyDown = (event) => {
      if (event.key === "Escape") setFullscreen(false);
    };

    window.addEventListener("keydown", onKeyDown);
    return () => window.removeEventListener("keydown", onKeyDown);
  }, []);

  // Dragging spins the globe, so only a near-stationary tap may toggle fullscreen.
  const handlePointerDown = (event) => {
    pointerStart.current = { x: event.clientX, y: event.clientY };
  };

  // Hovering gently pulls the Earth toward the cursor and swells it a little.
  const handleMapMove = (event) => {
    if (reducedMotion) return;
    const rect = event.currentTarget.getBoundingClientRect();
    const nx = ((event.clientX - rect.left) / rect.width) * 2 - 1;
    const ny = ((event.clientY - rect.top) / rect.height) * 2 - 1;
    setMapHover({ on: true, x: nx * 14, y: ny * 11 });
  };

  const handleMapLeave = () => setMapHover({ on: false, x: 0, y: 0 });

  const handlePointerUp = (event) => {
    const start = pointerStart.current;
    pointerStart.current = null;
    if (!start) return;

    const travel = Math.hypot(event.clientX - start.x, event.clientY - start.y);
    if (travel < 6) setFullscreen((value) => !value);
  };

  return (
    <section className={`panel map-panel ${fullscreen ? "fullscreen" : ""}`}>
      <div className="map-heading">
        <div>
          <h2>
            <Globe2 size={17} /> GLOBAL NETWORK MAP
          </h2>
          <small>
            {origin
              ? `Real Earth globe · ${locations.length} location${
                  locations.length === 1 ? "" : "s"
                } observed in captured traffic · Origin: ${
                  origin.city || origin.country || origin.ip
                } · arcs coloured by threat level`
              : "Real Earth globe · no capture yet — run a capture to plot the locations actually seen"}
          </small>
          <div className="map-threat-legend" aria-label="Map colours by threat level">
            {threatLegend.map((item) => (
              <span key={item.level} className="map-threat-key">
                <i style={{ background: item.color }} aria-hidden="true" />
                {item.label}
              </span>
            ))}
          </div>
        </div>
      </div>

      <div
        className={`world-map globe-map${galaxy ? " globe-galaxy" : ""}`}
        ref={containerRef}
        onPointerDown={handlePointerDown}
        onPointerUp={handlePointerUp}
        onMouseEnter={() => setMapHover((value) => ({ ...value, on: true }))}
        onMouseMove={handleMapMove}
        onMouseLeave={handleMapLeave}
        style={{
          transform: `scale(${mapHover.on && !reducedMotion ? 1.06 : 1}) translate(${mapHover.x}px, ${mapHover.y}px)`,
          transition: mapHover.on ? "transform 0.18s ease-out" : "transform 0.5s ease",
        }}
        title={
          fullscreen
            ? "Click to exit fullscreen · drag to spin the Earth"
            : "Click to expand · drag to spin the Earth"
        }
      >
        {size.width > 0 && (
          <Globe
            ref={globeRef}
            width={size.width}
            height={size.height}
            backgroundColor="rgba(0,0,0,0)"
            globeImageUrl={EARTH_TEXTURE}
            bumpImageUrl={EARTH_BUMP}
            showAtmosphere
            atmosphereColor="#4fc9ef"
            atmosphereAltitude={0.2}
            animateIn={false}
            arcsData={arcData}
            arcColor={(arc) => arc.color}
            arcStroke={(arc) => arc.stroke}
            arcDashLength={0.4}
            arcDashGap={0.22}
            arcDashAnimateTime={2800}
            arcAltitudeAutoScale={0.35}
            arcLabel={(arc) => arc.label}
            pointsData={pointData}
            pointColor={(point) => point.color}
            pointAltitude={0.012}
            pointRadius={(point) => point.size}
            pointLabel={(point) => point.label}
            pointsMerge={false}
            ringsData={ringData}
            ringColor={(ring) => ring.color}
            ringMaxRadius={(ring) => ring.maxRadius}
            ringPropagationSpeed={1.6}
            ringRepeatPeriod={1800}
            onGlobeReady={() => setReady(true)}
          />
        )}

        {!ready && (
          <div className="globe-loading" role="status">
            <div className="radar-loader" aria-hidden="true">
              <span className="radar-ring" />
              <span className="radar-ring" />
              <span className="radar-ring" />
              <span className="radar-cross" />
              <span className="radar-sweep" />
              <span
                className="radar-blip"
                style={{ top: "32%", left: "60%", animationDelay: "0.4s" }}
              />
              <span
                className="radar-blip"
                style={{ top: "62%", left: "33%", animationDelay: "1.6s" }}
              />
              <span
                className="radar-blip"
                style={{ top: "47%", left: "24%", animationDelay: "2.7s" }}
              />
            </div>
            <span className="globe-loading-label">SCANNING NETWORK TOPOLOGY</span>
          </div>
        )}
      </div>
    </section>
  );
}

function App() {
  const [activeTab, setActiveTab] = useState("dashboard");
  const [socOpen, setSocOpen] = useState(false);
  const [health, setHealth] = useState(null);
  const [history, setHistory] = useState([]);
  const [capture, setCapture] = useState(null);
  const [loading, setLoading] = useState(false);
  const [duration, setDuration] = useState("10");
  const [interfaceId, setInterfaceId] = useState("4");
  const [network, setNetwork] = useState(null);
  const [error, setError] = useState("");

  const loadHealth = async () => {
    try {
      const response = await fetch(`${API}/api/health`);
      if (!response.ok) throw new Error();
      setHealth(await response.json());
    } catch {
      setHealth(null);
    }
  };

  const loadHistory = async () => {
    try {
      const response = await fetch(`${API}/api/history?limit=20`);
      if (!response.ok) throw new Error();
      const data = await response.json();
      if (data.success) setHistory(data.history || []);
    } catch {
      // Keep the last successfully loaded history.
    }
  };

  const loadNetwork = async () => {
    try {
      const response = await fetch(`${API}/api/network`);
      if (!response.ok) throw new Error();
      const data = await response.json();
      if (data.success) setNetwork(data);
    } catch {
      // Keep the last successfully loaded adapter list.
    }
  };

  const startCapture = async () => {
    if (loading) return;
    setLoading(true);
    setError("");

    try {
      const response = await fetch(`${API}/api/capture`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({
          interface: interfaceId,
          duration: Number(duration),
        }),
      });

      const data = await response.json();
      if (!response.ok || !data.success) {
        throw new Error(data.error || "Capture failed");
      }

      setCapture(data);
      await loadHistory();
    } catch (err) {
      setError(err.message || "Unable to capture traffic");
    } finally {
      setLoading(false);
    }
  };

  const loadTick = useRef(false);

  useEffect(() => {
    if (loadTick.current) return;
    loadTick.current = true;
    loadHealth();
    loadHistory();
    loadNetwork();

    const timer = setInterval(() => {
      loadHealth();
      loadHistory();
      loadNetwork();
    }, 15000);

    return () => {
      clearInterval(timer);
      loadTick.current = false;
    };
  }, []);

  useEffect(() => {
    window.scrollTo({ top: 0 });
  }, [activeTab]);

  const threats = history.filter(isThreatRecord);
  const benign = history.filter(
    (item) => item.prediction && !isThreatRecord(item)
  );
  const latestAlerts = threats.slice(0, 6);

  const loadedDetectors = detectors.filter(
    (detector) => health?.detectors?.[detector.key] === "loaded"
  ).length;

  const numericConfidences = history
    .map((item) => Number(item.confidence))
    .filter((value) => Number.isFinite(value));

  const averageConfidence = numericConfidences.length
    ? numericConfidences.reduce((total, value) => total + value, 0) /
      numericConfidences.length
    : null;

  const chartData = capture
    ? [
        {
          time: "Capture",
          packets: capture.packet_count || 0,
          flows: capture.flow_count || 0,
        },
      ]
    : [];

  const captureSummary = capture?.detection_summary || {};

  const interfaceOptions = useMemo(() => {
    const live = network?.interfaces || [];

    if (!live.length) return fallbackInterfaceOptions;

    const options = live.map((item) => ({
      id: String(item.id),
      label: interfaceLabelOf(item),
    }));

    // The chosen adapter can disappear (Wi-Fi turned off, cable unplugged), so
    // keep it listed rather than silently showing a different one.
    if (!options.some((option) => option.id === interfaceId)) {
      options.unshift({ id: interfaceId, label: `Interface ${interfaceId}` });
    }

    return options;
  }, [network, interfaceId]);

  const interfaceLabel =
    interfaceOptions.find((option) => option.id === interfaceId)?.label ||
    `Interface ${interfaceId}`;

  return (
    <>
      {/* Full-bleed bar, flush with the top edge of the page */}
      <header className="topbar">
        <div className="brand">◈ CYVORA</div>
        <nav className="top-nav" role="tablist" aria-label="Dashboard sections">
          {tabs.map((tab) => {
            const Icon = tab.icon;

            return (
              <button
                key={tab.key}
                type="button"
                role="tab"
                aria-selected={activeTab === tab.key}
                className={activeTab === tab.key ? "active" : ""}
                onClick={() => setActiveTab(tab.key)}
              >
                <Icon size={12} />
                {tab.label}
              </button>
            );
          })}
        </nav>
        <div className="online">
          <span
            className={
              health?.status === "running" ? "status-dot" : "status-dot offline"
            }
          />
          {health?.status === "running" ? "SYSTEM ONLINE" : "BACKEND OFFLINE"}
        </div>
      </header>

      <main
        className="dashboard"
        data-galaxy={activeTab === "dashboard" && !socOpen ? "true" : undefined}
      >
      <MatrixRain />

      {/* Galaxy backdrop spans the whole Home page, behind the content */}
      {activeTab === "dashboard" && !socOpen && (
        <div className="galaxy" aria-hidden="true">
          <span className="nebula nebula-one" />
          <span className="nebula nebula-two" />
          <Starfield />
          <span className="shooting-star" />
        </div>
      )}

      {/* Keyed wrapper: re-mounts on every tab change so the entrance animation replays */}
      <div className="tab-view" key={`${activeTab}${socOpen ? "-soc" : ""}`}>
      {activeTab === "dashboard" && !socOpen && (
        <>
          {/* Global map sits directly beneath the fixed top bar */}
          <div className="dashboard-map">
            <GlobalMap galaxy geo={capture?.geo} />
          </div>

          <div className="soc-cta-wrap">
            <button
              type="button"
              className="soc-cta"
              onClick={() => setSocOpen(true)}
            >
              <span className="soc-cta-icon">
                <Radar size={18} />
              </span>
              <span className="soc-cta-text">
                <strong>Security Operations Center</strong>
                <small>Live capture · detection stats · history</small>
              </span>
              <ChevronRight size={16} className="soc-cta-arrow" />
            </button>
          </div>
        </>
      )}

      {activeTab === "dashboard" && socOpen && (
        <div className="soc-view">
          <button
            type="button"
            className="soc-back"
            onClick={() => setSocOpen(false)}
          >
            <ArrowLeft size={13} /> GLOBAL NETWORK MAP
          </button>

          <section className="dashboard-intro">
            <div>
              <h1>Security Operations Center</h1>
              <p>Network visibility · Threat detection · Live traffic analysis</p>
            </div>
            <div className="intro-time">
              <span>MONITORING STATUS</span>
              <strong>
                {health?.status === "running" ? "Operational" : "Disconnected"}
              </strong>
            </div>
          </section>

          {/* Collapsed vertical tabs that widen on hover, one per section */}
          <section className="soc-strip has-open" aria-label="Security operations panels">
            <article
              className="soc-panel soc-panel--primary"
              tabIndex={0}
              style={{
                "--accent": "#35d9f4",
                "--accent-soft": "rgba(53, 217, 244, 0.22)",
              }}
            >
              <div className="soc-panel-tab">
                <span className="soc-panel-icon">
                  <Wifi size={16} />
                </span>
                <span className="soc-panel-label">Live capture</span>
              </div>
              <div className="soc-panel-body">
                <CaptureControls
                  interfaceId={interfaceId}
                  interfaceOptions={interfaceOptions}
                  onInterfaceChange={setInterfaceId}
                  duration={duration}
                  onDurationChange={setDuration}
                  loading={loading}
                  elevated={health?.elevated}
                  onCapture={startCapture}
                />

                {error && (
                  <div className="error-message">
                    <AlertTriangle size={16} /> {error}
                  </div>
                )}
              </div>
            </article>

            <article
              className="soc-panel"
              tabIndex={0}
              style={{
                "--accent": "#39d7a4",
                "--accent-soft": "rgba(57, 215, 164, 0.22)",
                "--i": 1,
              }}
            >
              <div className="soc-panel-tab">
                <span className="soc-panel-icon">
                  <Activity size={16} />
                </span>
                <span className="soc-panel-label">Live stats</span>
              </div>
              <div className="soc-panel-body">
                <section className="stats">
                  <StatCard
                    label="PACKETS CAPTURED"
                    value={capture?.packet_count ?? "—"}
                    Icon={ArrowDownToLine}
                    note="Latest capture session"
                  />
                  <StatCard
                    label="NETWORK FLOWS"
                    value={capture?.flow_count ?? "—"}
                    Icon={Network}
                    note="Extracted network flows"
                  />
                  <StatCard
                    label="THREAT RECORDS"
                    value={threats.length}
                    Icon={ShieldAlert}
                    note="Latest 20 history records"
                  />
                  <StatCard
                    label="BENIGN RECORDS"
                    value={benign.length}
                    Icon={ShieldCheck}
                    note="Latest 20 history records"
                  />
                </section>
              </div>
            </article>

            <article
              className="soc-panel"
              tabIndex={0}
              style={{
                "--accent": "#b18aff",
                "--accent-soft": "rgba(177, 138, 255, 0.22)",
                "--i": 2,
              }}
            >
              <div className="soc-panel-tab">
                <span className="soc-panel-icon">
                  <ShieldAlert size={16} />
                </span>
                <span className="soc-panel-label">Detector modules</span>
              </div>
              <div className="soc-panel-body">
                <DetectorModules health={health} />
              </div>
            </article>

            <article
              className="soc-panel"
              tabIndex={0}
              style={{
                "--accent": "#ff7a8a",
                "--accent-soft": "rgba(255, 122, 138, 0.22)",
                "--i": 3,
              }}
            >
              <div className="soc-panel-tab">
                <span className="soc-panel-icon">
                  <AlertTriangle size={16} />
                </span>
                <span className="soc-panel-label">Threat alerts</span>
              </div>
              <div className="soc-panel-body">
                <ThreatAlerts alerts={latestAlerts} total={threats.length} />
              </div>
            </article>

            <article
              className="soc-panel"
              tabIndex={0}
              style={{
                "--accent": "#f6c85f",
                "--accent-soft": "rgba(246, 200, 95, 0.22)",
                "--i": 4,
              }}
            >
              <div className="soc-panel-tab">
                <span className="soc-panel-icon">
                  <Radio size={16} />
                </span>
                <span className="soc-panel-label">Capture overview</span>
              </div>
              <div className="soc-panel-body">
                <CaptureOverview chartData={chartData} />
              </div>
            </article>

            <article
              className="soc-panel"
              tabIndex={0}
              style={{
                "--accent": "#7fe3ff",
                "--accent-soft": "rgba(127, 227, 255, 0.22)",
                "--i": 5,
              }}
            >
              <div className="soc-panel-tab">
                <span className="soc-panel-icon">
                  <FileText size={16} />
                </span>
                <span className="soc-panel-label">Recent detections</span>
              </div>
              <div className="soc-panel-body">
                <DetectionHistory
                  history={history}
                  onRefresh={loadHistory}
                  limit={8}
                />
              </div>
            </article>

            {capture && (
              <article
                className="soc-panel"
                tabIndex={0}
                style={{
                  "--accent": "#35e6a3",
                  "--accent-soft": "rgba(53, 230, 163, 0.22)",
                  "--i": 6,
                }}
              >
                <div className="soc-panel-tab">
                  <span className="soc-panel-icon">
                    <ShieldCheck size={16} />
                  </span>
                  <span className="soc-panel-label">Session summary</span>
                </div>
                <div className="soc-panel-body">
                  <CaptureSummary capture={capture} summary={captureSummary} />
                </div>
              </article>
            )}

            <article
              className="soc-panel"
              tabIndex={0}
              style={{
                "--accent": "#8ab4ff",
                "--accent-soft": "rgba(138, 180, 255, 0.22)",
                "--i": 7,
              }}
            >
              <div className="soc-panel-tab">
                <span className="soc-panel-icon">
                  <Globe2 size={16} />
                </span>
                <span className="soc-panel-label">Connected locations</span>
              </div>
              <div className="soc-panel-body">
                <ConnectedLocations geo={capture?.geo} />
              </div>
            </article>
          </section>

          {/* Threat intelligence sits directly beneath the panel strip */}
          <section className="ti-section">
            <header className="ti-head">
              <div className="ti-head-main">
                <span className="ti-eyebrow">
                  <span className="ti-eyebrow-dot" />
                  Security operations · detection layer
                </span>
                <h2 className="ti-title">Threat Intelligence</h2>
                <p className="ti-sub">
                  Detector verdicts · Confidence scoring · Recent threat records
                </p>
              </div>

              <div className="ti-meta">
                <div className="ti-meta-item">
                  <strong>{threats.length}</strong>
                  <span>Threats</span>
                </div>
                <div className="ti-meta-item">
                  <strong>{loadedDetectors}</strong>
                  <span>Detectors loaded</span>
                </div>
              </div>
            </header>

            <ThreatIntelligenceContent
              threats={threats}
              benign={benign}
              averageConfidence={averageConfidence}
              detectors={detectors}
              loadedDetectors={loadedDetectors}
              health={health}
              history={history}
            />
          </section>
        </div>
      )}

      {activeTab === "network" && (
        <>
          <section className="dashboard-intro">
            <div>
              <h1>Network</h1>
              <p>Interface capture · Flow extraction · Global path view</p>
            </div>
            <div className="intro-time">
              <span>SELECTED INTERFACE</span>
              <strong>{interfaceLabel}</strong>
            </div>
          </section>

          <CaptureControls
            interfaceId={interfaceId}
            interfaceOptions={interfaceOptions}
            onInterfaceChange={setInterfaceId}
            duration={duration}
            onDurationChange={setDuration}
            loading={loading}
            elevated={health?.elevated}
            onCapture={startCapture}
          />

          {error && (
            <div className="error-message">
              <AlertTriangle size={16} /> {error}
            </div>
          )}

          <section className="stats">
            <StatCard
              label="PACKETS CAPTURED"
              value={capture?.packet_count ?? "—"}
              Icon={ArrowDownToLine}
              note="Latest capture session"
            />
            <StatCard
              label="NETWORK FLOWS"
              value={capture?.flow_count ?? "—"}
              Icon={Network}
              note="Extracted network flows"
            />
            <StatCard
              label="DETECTORS LOADED"
              value={`${loadedDetectors} / ${detectors.length}`}
              Icon={ShieldCheck}
              note="Modules available for capture"
            />
            <StatCard
              label="DATABASE"
              value={health?.mongodb ? health.mongodb.toUpperCase() : "UNKNOWN"}
              Icon={Radio}
              note="Detection record storage"
            />
          </section>

          <div className="network-map-wrap">
            <GlobalMap geo={capture?.geo} />
          </div>
        </>
      )}

      {activeTab === "reports" && (
        <>
          <section className="dashboard-intro">
            <div>
              <h1>Reports</h1>
              <p>Capture session summary · Detection log</p>
            </div>
            <div className="intro-time">
              <span>LATEST SESSION</span>
              <strong>{capture ? "Report ready" : "No capture yet"}</strong>
            </div>
          </section>

          <section className="panel report-panel">
            <div className="section-heading">
              <h2>CAPTURE SESSION REPORT</h2>
              <span>{capture ? "COMPLETED" : "WAITING FOR CAPTURE"}</span>
            </div>

            <div className="report-grid">
              <div className="report-cell">
                <span>INTERFACE</span>
                <strong>{interfaceLabel}</strong>
              </div>
              <div className="report-cell">
                <span>CAPTURE DURATION</span>
                <strong>{duration} seconds</strong>
              </div>
              <div className="report-cell">
                <span>PACKETS CAPTURED</span>
                <strong>{capture?.packet_count ?? "—"}</strong>
              </div>
              <div className="report-cell">
                <span>FLOWS EXTRACTED</span>
                <strong>{capture?.flow_count ?? "—"}</strong>
              </div>
              <div className="report-cell">
                <span>THREAT RECORDS</span>
                <strong>{threats.length}</strong>
              </div>
              <div className="report-cell">
                <span>BENIGN RECORDS</span>
                <strong>{benign.length}</strong>
              </div>
            </div>

            {!capture && (
              <div className="empty-chart report-empty">
                Run a network capture from the Network tab to generate a session
                report.
              </div>
            )}
          </section>

          {capture && (
            <CaptureSummary capture={capture} summary={captureSummary} />
          )}

          <section className="bottom-grid">
            <CaptureOverview chartData={chartData} />
            <DetectionHistory
              history={history}
              onRefresh={loadHistory}
              limit={20}
            />
          </section>
        </>
      )}
      </div>
      </main>

      {/* Full-bleed status bar, pinned to the bottom on every page */}
      <footer className="footer">
        <div className="footer-row">
          <span>CYVORA · NETWORK SECURITY MONITORING</span>
          <span>DATABASE: {health?.mongodb || "UNKNOWN"}</span>
          <span className="footer-credit"><i>◈</i> Developed by Sachin N</span>
          <span className="footer-email">sachinnsagar089@gmail.com</span>
        </div>
      </footer>

      {/* Robot assistant for new users, on every page */}
      <AssistantBot
        onAction={(action) => {
          if (action === "soc") {
            setActiveTab("dashboard");
            setSocOpen(true);
          } else if (action === "home") {
            setActiveTab("dashboard");
            setSocOpen(false);
          } else if (action === "network") {
            setActiveTab("network");
          } else if (action === "reports") {
            setActiveTab("reports");
          }
        }}
      />
    </>
  );
}

export default App;