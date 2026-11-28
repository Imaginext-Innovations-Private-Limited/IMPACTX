
import { useEffect, useMemo, useRef, useState } from "react";
import { Link, useNavigate } from "react-router-dom";

import {
  Waves,
  LayoutDashboard,
  FileText,
  Camera,
  MapPin,
  Droplets,
  LogOut,
  Menu,
  X,
  Bell,
  RefreshCw,
  Database,
  Activity,
  Thermometer,
  Search,
  Download,
  ClipboardList,
  TrendingUp,
  CheckCircle,
  AlertCircle,
  Leaf,
  CalendarDays,
  Gauge
} from "lucide-react";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend
} from "recharts";

import LocationSearch from "../components/LocationSearch";

import {
  getMyWaterReadings,
  getNearbyHistoricalReadings
} from "../services/waterService";

import { generateWaterQualityPDF } from "../utils/waterQualityReport";


function WaterQuality() {
  const navigate = useNavigate();

  const chartsRef = useRef(null);

  const [myReadings, setMyReadings] = useState([]);
  const [selectedLake, setSelectedLake] = useState(null);
  const [historicalReadings, setHistoricalReadings] = useState([]);

  const [loading, setLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(true);

  const [error, setError] = useState("");
  const [message, setMessage] = useState("");

  const [radius, setRadius] = useState(25);
  const [menuOpen, setMenuOpen] = useState(false);

  const user = JSON.parse(
    localStorage.getItem("aquawatch_user") || "{}"
  );


  // -----------------------------------------
  // LOAD PERSONAL READINGS
  // -----------------------------------------

  const loadMyReadings = async () => {
    try {
      setHistoryLoading(true);

      const response = await getMyWaterReadings();

      setMyReadings(response.readings || []);

    } catch (err) {
      console.error("Unable to load personal readings:", err);
    } finally {
      setHistoryLoading(false);
    }
  };


  useEffect(() => {
    loadMyReadings();
  }, []);


  // -----------------------------------------
  // FETCH HISTORICAL CPCB DATA
  // -----------------------------------------

  const fetchHistoricalData = async (
    latitude,
    longitude,
    searchRadius
  ) => {
    try {
      setLoading(true);
      setError("");
      setMessage("");
      setHistoricalReadings([]);

      const response = await getNearbyHistoricalReadings(
        latitude,
        longitude,
        searchRadius
      );

      const readings = response.readings || [];

      setHistoricalReadings(readings);

      if (!readings.length) {
        setMessage(
          "No CPCB monitoring stations were found within this search radius."
        );
      } else {
        setMessage(
          `${readings.length} historical readings found.`
        );
      }

    } catch (err) {
      console.error(err);

      setError(
        err.response?.data?.detail ||
        "Unable to retrieve historical water-quality data."
      );

    } finally {
      setLoading(false);
    }
  };


  // -----------------------------------------
  // SELECT LAKE LOCATION
  // -----------------------------------------

  const handleLocationSelect = async (location) => {
    if (!location) {
      setSelectedLake(null);
      setHistoricalReadings([]);
      setMessage("");
      setError("");
      return;
    }

    setSelectedLake(location);
    setHistoricalReadings([]);
    setError("");
    setMessage("");

    await fetchHistoricalData(
      location.latitude,
      location.longitude,
      radius
    );
  };


  // -----------------------------------------
  // REFRESH DATA
  // -----------------------------------------

  const handleRefresh = () => {
    if (!selectedLake) return;

    fetchHistoricalData(
      selectedLake.latitude,
      selectedLake.longitude,
      radius
    );
  };


  // -----------------------------------------
  // DOWNLOAD PDF
  // -----------------------------------------

  const handleDownloadPDF = async () => {
    if (!selectedLake || !historicalReadings.length) {
      setError("Search for a lake with historical records before downloading the PDF.");
      return;
    }

    try {
      await generateWaterQualityPDF({
        selectedLake,
        historicalReadings,
        uniqueStations,
        waterStatus,
        chartElement: chartsRef.current
      });
    } catch (err) {
      console.error("PDF generation error:", err);
      setError("Unable to generate the PDF report. Please try again.");
    }
  };


  // -----------------------------------------
  // DISPLAY MISSING VALUES
  // -----------------------------------------

  const showValue = (value, unit = "") => {
    if (
      value === null ||
      value === undefined ||
      value === ""
    ) {
      return "Not available";
    }

    return `${value}${unit ? ` ${unit}` : ""}`;
  };


  // -----------------------------------------
  // FORMAT DATE
  // -----------------------------------------

  const formatDate = (date) => {
    if (!date) return "Date unavailable";

    const parsedDate = new Date(date);

    if (Number.isNaN(parsedDate.getTime())) {
      return "Date unavailable";
    }

    return parsedDate.toLocaleDateString("en-IN", {
      day: "2-digit",
      month: "short",
      year: "numeric"
    });
  };


  // -----------------------------------------
  // SORT HISTORICAL READINGS
  // -----------------------------------------

  const sortedReadings = useMemo(() => {
    return [...historicalReadings].sort(
      (a, b) =>
        new Date(a.measurement_date) -
        new Date(b.measurement_date)
    );
  }, [historicalReadings]);


  // -----------------------------------------
  // LATEST AVAILABLE READING
  // -----------------------------------------

  const latestReading = sortedReadings.length
    ? sortedReadings[sortedReadings.length - 1]
    : null;


  // -----------------------------------------
  // UNIQUE MONITORING STATIONS
  // -----------------------------------------

  const uniqueStations = [
    ...new Map(
      historicalReadings.map((item) => [
        item.station,
        item
      ])
    ).values()
  ];


  // -----------------------------------------
  // CHART DATA
  // -----------------------------------------

  const chartData = sortedReadings.map((reading) => ({
    date: formatDate(reading.measurement_date),
    ph: reading.ph ?? null,
    dissolved_oxygen: reading.dissolved_oxygen ?? null,
    turbidity: reading.turbidity ?? null,
    temperature: reading.temperature ?? null,
    station: reading.station
  }));


  // -----------------------------------------
  // PRELIMINARY WATER STATUS
  // -----------------------------------------

  const getWaterStatus = (reading) => {
    if (!reading) {
      return {
        label: "No data",
        color: "#94a3b8",
        description: "No historical measurement available."
      };
    }

    const checks = [];

    if (
      reading.ph !== null &&
      reading.ph !== undefined &&
      reading.ph !== ""
    ) {
      checks.push(
        Number(reading.ph) >= 6.5 &&
        Number(reading.ph) <= 8.5
      );
    }

    if (
      reading.dissolved_oxygen !== null &&
      reading.dissolved_oxygen !== undefined &&
      reading.dissolved_oxygen !== ""
    ) {
      checks.push(
        Number(reading.dissolved_oxygen) >= 5
      );
    }

    if (checks.length < 2) {
      return {
        label: "Limited data",
        color: "#fbbf24",
        description:
          "Both pH and dissolved oxygen are needed for this preliminary screening."
      };
    }

    const failedChecks = checks.filter(
      (check) => !check
    ).length;

    if (failedChecks === 0) {
      return {
        label: "Good",
        color: "#4ade80",
        description:
          "The available pH and dissolved oxygen values meet the screening ranges."
      };
    }

    if (failedChecks === 1) {
      return {
        label: "Moderate",
        color: "#fbbf24",
        description:
          "One available pH or dissolved oxygen value is outside its screening range."
      };
    }

    return {
      label: "Poor",
      color: "#fb7185",
      description:
        "Both available pH and dissolved oxygen values are outside their screening ranges."
    };
  };


  const waterStatus = getWaterStatus(latestReading);


  // -----------------------------------------
  // CHART COMPONENT
  // -----------------------------------------

  const renderChart = (
    title,
    dataKey,
    color,
    unit,
    description
  ) => (
    <div className="water-premium-card water-chart-card">

      <div className="water-card-heading">
        <div className="water-card-icon">
          <TrendingUp size={19} />
        </div>

        <div>
          <h3>{title}</h3>
          <p>{description}</p>
        </div>
      </div>

      <div className="water-chart-area">
        <ResponsiveContainer width="100%" height="100%">
          <LineChart
            data={chartData}
            margin={{
              top: 10,
              right: 20,
              left: 5,
              bottom: 10
            }}
          >
            <CartesianGrid
              stroke="rgba(142, 207, 205, 0.13)"
              strokeDasharray="4 4"
            />

            <XAxis
              dataKey="date"
              tick={{ fill: "#9bbfc1", fontSize: 10 }}
              axisLine={{ stroke: "#315b62" }}
              tickLine={false}
            />

            <YAxis
              unit={unit}
              tick={{ fill: "#9bbfc1", fontSize: 10 }}
              axisLine={false}
              tickLine={false}
            />

            <Tooltip
              contentStyle={{
                background: "#092e38",
                border: "1px solid #28616a",
                borderRadius: "10px",
                color: "#eaffff"
              }}
              formatter={(value) => [
                value === null || value === undefined
                  ? "Not available"
                  : `${value} ${unit}`,
                title
              ]}
            />

            <Legend
              wrapperStyle={{
                color: "#c3dddd",
                fontSize: "11px"
              }}
            />

            <Line
              type="monotone"
              dataKey={dataKey}
              name={title}
              stroke={color}
              strokeWidth={2.5}
              dot={{ r: 3, fill: color }}
              activeDot={{ r: 6 }}
              connectNulls={false}
            />

          </LineChart>
        </ResponsiveContainer>
      </div>

    </div>
  );


  // -----------------------------------------
  // LOGOUT
  // -----------------------------------------

  const handleLogout = () => {
    localStorage.removeItem("aquawatch_token");
    localStorage.removeItem("aquawatch_user");

    navigate("/login");
  };


  const closeMenu = () => setMenuOpen(false);


  // -----------------------------------------
  // UI
  // -----------------------------------------

  return (
    <div className="dashboard-page premium-dashboard water-premium-page">

      {menuOpen && (
        <div
          className="water-sidebar-overlay"
          onClick={closeMenu}
        />
      )}


      {/* SIDEBAR */}

      <aside
        className={`dashboard-sidebar premium-sidebar ${
          menuOpen ? "open" : ""
        }`}
      >

        <Link
          to="/dashboard"
          className="premium-brand"
          onClick={closeMenu}
        >
          <span className="brand-icon">
            <Waves size={28} />
          </span>

          <span>
            <strong>AquaWatch</strong>
            <small>LAKE MONITORING PLATFORM</small>
          </span>

          <button
            className="mobile-close"
            onClick={(e) => {
              e.preventDefault();
              closeMenu();
            }}
          >
            <X />
          </button>
        </Link>


        <p className="premium-nav-label">WORKSPACE</p>


        <Link
          to="/dashboard"
          className="sidebar-link"
          onClick={closeMenu}
        >
          <LayoutDashboard size={19} />
          Dashboard
        </Link>


        <Link
          to="/my-reports"
          className="sidebar-link"
          onClick={closeMenu}
        >
          <FileText size={19} />
          My Reports
        </Link>


        <Link
          to="/report"
          className="sidebar-link"
          onClick={closeMenu}
        >
          <Camera size={19} />
          Report Pollution
        </Link>


        <Link
          to="/map"
          className="sidebar-link"
          onClick={closeMenu}
        >
          <MapPin size={19} />
          Lake Map
        </Link>


        <Link
          to="/water-quality"
          className="sidebar-link active"
          onClick={closeMenu}
        >
          <Droplets size={19} />
          Water Quality
        </Link>


        <div className="sidebar-environment-card">
          <Leaf size={23} />

          <strong>Be a Lake Guardian</strong>

          <p>
            Your contribution helps protect our water resources.
          </p>
        </div>


        <button
          className="sidebar-logout"
          onClick={handleLogout}
        >
          <LogOut size={19} />
          Logout
        </button>

      </aside>


      {/* MAIN CONTENT */}

      <main className="dashboard-main premium-main">

        {/* TOPBAR */}

        <header className="premium-topbar">

          <button
            className="mobile-menu"
            onClick={() => setMenuOpen(true)}
          >
            <Menu />
          </button>

          <div className="premium-page-title">
            <h2>Water Quality Monitoring</h2>
            <p>Historical water-quality insights from CPCB</p>
          </div>

          <div className="premium-topbar-right">

            <div className="notification-icon">
              <Bell size={19} />
              <span></span>
            </div>

            <div className="premium-user">
              <div className="premium-avatar">
                {user.name?.charAt(0)?.toUpperCase() || "U"}
              </div>

              <div>
                <strong>{user.name || "Citizen"}</strong>
                <small>Citizen Account</small>
              </div>
            </div>

          </div>

        </header>


        {/* HERO */}

        <section className="water-premium-hero">

          <div className="water-hero-content">

            <span className="water-hero-tag">
              <Droplets size={15} />
              WATER RESOURCE INTELLIGENCE
            </span>

            <h1>
              Understand Water.
              <br />
              <span>Protect Every Lake.</span>
            </h1>

            <p>
              Explore historical water-quality measurements
              from nearby CPCB monitoring stations.
            </p>

            <div className="water-hero-note">
              <Database size={16} />
              Government monitoring records
            </div>

          </div>


          <div className="water-hero-art">
            <div className="water-hero-art-icon">
              <Waves size={42} />
            </div>

            <strong>AquaWatch Insights</strong>
            <small>Historical water monitoring</small>
          </div>

        </section>


        {/* DATA SOURCE BANNER */}

        <div className="water-source-banner-premium">

          <div className="water-source-icon">
            <Database size={21} />
          </div>

          <div>
            <strong>Official Historical Data – CPCB</strong>

            <p>
              Readings are obtained from government monitoring
              records. They are not live sensor measurements.
            </p>
          </div>

          <span className="water-source-badge">
            HISTORICAL DATA
          </span>

        </div>


        {/* PARAMETER CARDS */}

        <section className="water-parameter-grid-premium">

          <div className="water-metric-card">
            <div className="water-metric-icon aqua">
              <Activity size={22} />
            </div>

            <div>
              <span>PARAMETER</span>
              <h3>pH Level</h3>
              <p>Acidity or alkalinity</p>
              <strong>pH</strong>
            </div>
          </div>


          <div className="water-metric-card">
            <div className="water-metric-icon blue">
              <Waves size={22} />
            </div>

            <div>
              <span>PARAMETER</span>
              <h3>Turbidity</h3>
              <p>Water cloudiness</p>
              <strong>NTU</strong>
            </div>
          </div>


          <div className="water-metric-card">
            <div className="water-metric-icon green">
              <Droplets size={22} />
            </div>

            <div>
              <span>PARAMETER</span>
              <h3>Dissolved Oxygen</h3>
              <p>Oxygen in water</p>
              <strong>mg/L</strong>
            </div>
          </div>


          <div className="water-metric-card">
            <div className="water-metric-icon purple">
              <Thermometer size={22} />
            </div>

            <div>
              <span>PARAMETER</span>
              <h3>Temperature</h3>
              <p>Water temperature</p>
              <strong>°C</strong>
            </div>
          </div>

        </section>


        {/* LAKE SEARCH */}

        <section className="water-premium-card water-search-card">

          <div className="water-card-heading">

            <div className="water-card-icon">
              <MapPin size={20} />
            </div>

            <div>
              <h3>Find Lake Water Quality</h3>
              <p>
                Search for a lake and discover nearby CPCB monitoring stations.
              </p>
            </div>

          </div>


          <div className="water-search-content">

            <label className="water-search-label">
              Search Lake Location
            </label>

            <LocationSearch
              onSelect={handleLocationSelect}
            />


            {selectedLake && (
              <div className="water-selected-location">

                <div className="water-selected-heading">
                  <CheckCircle size={18} />
                  <strong>Selected Lake</strong>
                </div>

                <h4>{selectedLake.display_name}</h4>

                <div className="water-coordinates">
                  <span>
                    Latitude: {selectedLake.latitude.toFixed(6)}
                  </span>

                  <span>
                    Longitude: {selectedLake.longitude.toFixed(6)}
                  </span>
                </div>

              </div>
            )}


            <div className="water-search-controls">

              <div className="water-radius-field">

                <label htmlFor="radius">
                  Search nearby stations
                </label>

                <select
                  id="radius"
                  value={radius}
                  onChange={(e) =>
                    setRadius(Number(e.target.value))
                  }
                >
                  <option value={10}>Within 10 km</option>
                  <option value={25}>Within 25 km</option>
                  <option value={50}>Within 50 km</option>
                  <option value={100}>Within 100 km</option>
                  <option value={250}>Within 250 km</option>
                  <option value={500}>Within 500 km</option>
                </select>

              </div>


              <button
                type="button"
                className="water-search-button"
                onClick={() => {
                  if (selectedLake) {
                    fetchHistoricalData(
                      selectedLake.latitude,
                      selectedLake.longitude,
                      radius
                    );
                  }
                }}
                disabled={!selectedLake || loading}
              >
                <Search size={17} />
                Search Stations
              </button>


              <button
                type="button"
                className="water-refresh-button"
                onClick={handleRefresh}
                disabled={!selectedLake || loading}
              >
                <RefreshCw size={16} />
                Refresh Data
              </button>

            </div>

          </div>

        </section>


        {/* LOADING */}

        {loading && (
          <div className="water-status-message">
            <RefreshCw size={20} className="water-spin" />
            <div>
              <strong>Searching CPCB monitoring records</strong>
              <p>Finding historical readings near your selected lake...</p>
            </div>
          </div>
        )}


        {/* ERROR */}

        {error && (
          <div className="water-error-premium">
            <AlertCircle size={19} />
            {error}
          </div>
        )}


        {/* SUCCESS */}

        {message && !loading && (
          <div className="water-success-premium">
            <CheckCircle size={19} />
            {message}
          </div>
        )}


        {/* HISTORICAL RESULTS */}

        {selectedLake && !loading && historicalReadings.length > 0 && (

          <>

            {/* SUMMARY */}

            <section className="water-results-section">

              <div className="water-section-title">

                <div>
                  <span>SEARCH RESULTS</span>
                  <h2>Historical Water Quality Summary</h2>
                  <p>
                    Data returned from nearby monitoring stations.
                  </p>
                </div>


                <button
                  className="water-download-button"
                  onClick={handleDownloadPDF}
                >
                  <Download size={17} />
                  Download PDF
                </button>

              </div>


              <div className="water-result-grid">

                <div className="water-result-card">
                  <div className="water-result-icon aqua">
                    <Database size={20} />
                  </div>

                  <span>HISTORICAL RECORDS</span>
                  <h2>{historicalReadings.length}</h2>
                  <p>Available measurements</p>
                </div>


                <div className="water-result-card">
                  <div className="water-result-icon blue">
                    <MapPin size={20} />
                  </div>

                  <span>MONITORING STATIONS</span>
                  <h2>{uniqueStations.length}</h2>
                  <p>Nearby stations found</p>
                </div>


                <div className="water-result-card">
                  <div className="water-result-icon green">
                    <Activity size={20} />
                  </div>

                  <span>LATEST AVAILABLE pH</span>
                  <h2>{showValue(latestReading?.ph)}</h2>
                  <p>Historical measurement</p>
                </div>


                <div className="water-result-card">
                  <div className="water-result-icon purple">
                    <Droplets size={20} />
                  </div>

                  <span>LATEST AVAILABLE DO</span>
                  <h2>
                    {showValue(latestReading?.dissolved_oxygen)}
                  </h2>
                  <p>Historical measurement</p>
                </div>

              </div>


              {latestReading && (
                <div className="water-latest-note">
                  <CalendarDays size={17} />

                  Latest record in the returned results:{" "}
                  <strong>
                    {formatDate(latestReading.measurement_date)}
                  </strong>

                  <span>
                    This is historical data, not a live reading.
                  </span>
                </div>
              )}

            </section>


            {/* STATUS */}

            <section className="water-premium-card water-status-card">

              <div className="water-card-heading">
                <div className="water-card-icon">
                  <Gauge size={20} />
                </div>

                <div>
                  <h3>Indicative Water Quality Status</h3>
                  <p>
                    Preliminary screening using the latest available pH and DO.
                  </p>
                </div>
              </div>


              <div className="water-status-content">

                <div
                  className="water-status-indicator"
                  style={{ borderColor: waterStatus.color }}
                >
                  <span
                    className="water-status-dot"
                    style={{ background: waterStatus.color }}
                  />

                  <strong style={{ color: waterStatus.color }}>
                    {waterStatus.label}
                  </strong>
                </div>

                <p>{waterStatus.description}</p>

                <div className="water-status-disclaimer">
                  <AlertCircle size={17} />

                  This is a simplified screening reference, not a
                  complete water-quality assessment or drinking-water
                  safety certification. Other parameters and laboratory
                  tests are necessary.
                </div>

              </div>

            </section>


            {/* CHARTS */}

            <section className="water-results-section">

              <div className="water-section-title">
                <div>
                  <span>DATA ANALYTICS</span>
                  <h2>Historical Water Quality Trends</h2>
                  <p>
                    Available measurements arranged by recorded date.
                  </p>
                </div>
              </div>


              <div ref={chartsRef} className="water-chart-grid">

                {renderChart(
                  "pH Level Trend",
                  "ph",
                  "#56dfce",
                  "pH",
                  "Historical pH measurements."
                )}

                {renderChart(
                  "Dissolved Oxygen Trend",
                  "dissolved_oxygen",
                  "#60a5fa",
                  "mg/L",
                  "Historical dissolved oxygen measurements."
                )}

                {renderChart(
                  "Turbidity Trend",
                  "turbidity",
                  "#fbbf24",
                  "NTU",
                  "Historical turbidity measurements."
                )}

                {renderChart(
                  "Temperature Trend",
                  "temperature",
                  "#c084fc",
                  "°C",
                  "Historical temperature measurements."
                )}

              </div>

              <p className="water-chart-disclaimer">
                Missing measurements are not estimated or filled in.
              </p>

            </section>


            {/* STATIONS TABLE */}

            <section className="water-premium-card water-table-card">

              <div className="water-card-heading">
                <div className="water-card-icon">
                  <MapPin size={20} />
                </div>

                <div>
                  <h3>Nearby Monitoring Stations</h3>
                  <p>Stations within your selected search radius.</p>
                </div>
              </div>


              <div className="water-table-wrapper">
                <table className="water-premium-table">

                  <thead>
                    <tr>
                      <th>Station</th>
                      <th>District</th>
                      <th>Distance</th>
                      <th>State</th>
                    </tr>
                  </thead>

                  <tbody>
                    {uniqueStations.map((station, index) => (
                      <tr key={`${station.station}-${index}`}>
                        <td>{station.station || "-"}</td>
                        <td>{station.district || "-"}</td>
                        <td>{showValue(station.distance_km, "km")}</td>
                        <td>{station.state || "-"}</td>
                      </tr>
                    ))}
                  </tbody>

                </table>
              </div>

            </section>


            {/* HISTORICAL READINGS TABLE */}

            <section className="water-premium-card water-table-card">

              <div className="water-card-heading">
                <div className="water-card-icon">
                  <ClipboardList size={20} />
                </div>

                <div>
                  <h3>Historical Measurements</h3>
                  <p>
                    Individual measurements obtained from CPCB records.
                  </p>
                </div>
              </div>


              <div className="water-table-wrapper">
                <table className="water-premium-table">

                  <thead>
                    <tr>
                      <th>Station</th>
                      <th>Date</th>
                      <th>pH</th>
                      <th>Dissolved Oxygen</th>
                      <th>Turbidity</th>
                      <th>Temperature</th>
                      <th>Distance</th>
                    </tr>
                  </thead>

                  <tbody>
                    {historicalReadings.map((reading, index) => (
                      <tr key={reading._id || index}>
                        <td>{reading.station || "-"}</td>

                        <td>
                          {formatDate(reading.measurement_date)}
                        </td>

                        <td>{showValue(reading.ph)}</td>

                        <td>
                          {showValue(reading.dissolved_oxygen, "mg/L")}
                        </td>

                        <td>
                          {showValue(reading.turbidity, "NTU")}
                        </td>

                        <td>
                          {showValue(reading.temperature, "°C")}
                        </td>

                        <td>
                          {showValue(reading.distance_km, "km")}
                        </td>
                      </tr>
                    ))}
                  </tbody>

                </table>
              </div>

            </section>

          </>

        )}


        {/* NO RESULTS */}

        {selectedLake &&
          !loading &&
          historicalReadings.length === 0 &&
          !error && (

          <div className="water-empty-premium">
            <Droplets size={35} />

            <h3>No Historical Records Found</h3>

            <p>
              No matching CPCB monitoring records were found
              within the selected search radius.
            </p>

            <p>Try increasing the search radius.</p>

          </div>

        )}


        {/* PERSONAL READINGS */}

        <section className="water-premium-card water-table-card">

          <div className="water-card-heading">
            <div className="water-card-icon">
              <ClipboardList size={20} />
            </div>

            <div>
              <h3>My Previously Recorded Readings</h3>
              <p>
                Personal readings saved through your AquaWatch account,
                separate from CPCB records.
              </p>
            </div>
          </div>


          {historyLoading ? (

            <div className="water-table-loading">
              <RefreshCw size={19} className="water-spin" />
              Loading your records...
            </div>

          ) : myReadings.length === 0 ? (

            <div className="water-personal-empty">
              No personal readings recorded yet.
            </div>

          ) : (

            <div className="water-table-wrapper">

              <table className="water-premium-table">

                <thead>
                  <tr>
                    <th>Lake</th>
                    <th>pH</th>
                    <th>Dissolved Oxygen</th>
                    <th>Date</th>
                  </tr>
                </thead>

                <tbody>
                  {myReadings.map((reading, index) => (
                    <tr key={reading._id || index}>
                      <td>{reading.lake_name}</td>

                      <td>{showValue(reading.ph)}</td>

                      <td>
                        {showValue(reading.dissolved_oxygen, "mg/L")}
                      </td>

                      <td>
                        {formatDate(
                          reading.created_at || reading.measurement_date
                        )}
                      </td>
                    </tr>
                  ))}
                </tbody>

              </table>

            </div>

          )}

        </section>


        {/* DATA LIMITATIONS */}

        <div className="water-data-limitation">

          <Database size={19} />

          <div>
            <strong>Understanding the data</strong>

            <p>
              Nearby monitoring stations may be located on rivers or
              other water bodies, not the selected lake itself.
              Distance is measured from the selected lake location.
              Historical measurements must not be interpreted as
              current water conditions or proof that water is safe to drink.
            </p>
          </div>

        </div>


        {/* FOOTER */}

        <footer className="premium-footer">
          AquaWatch © 2026 · Protecting lakes, preserving life.
        </footer>

      </main>

    </div>
  );
}

export default WaterQuality;
