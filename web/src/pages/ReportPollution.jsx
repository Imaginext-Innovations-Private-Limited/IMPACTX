
import { useState } from "react";
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
  ImagePlus,
  Send,
  BrainCircuit,
  CheckCircle,
  LoaderCircle,
  AlertCircle,
  FileText as FileIcon,
  ShieldCheck,
  Leaf,
  Trash2
} from "lucide-react";

import {
  uploadPhoto,
  detectPollution,
  createReport
} from "../services/reportService";

import LocationSearch from "../components/LocationSearch";


function ReportPollution() {
  const navigate = useNavigate();

  const [menuOpen, setMenuOpen] = useState(false);

  const [formData, setFormData] = useState({
    lake_name: "",
    description: "",
    latitude: "",
    longitude: "",
    pollution_type: ""
  });

  const [photo, setPhoto] = useState(null);
  const [preview, setPreview] = useState("");

  const [loading, setLoading] = useState(false);
  const [stage, setStage] = useState("");

  const [message, setMessage] = useState("");
  const [error, setError] = useState("");

  const [analysis, setAnalysis] = useState(null);
  const [reportId, setReportId] = useState("");

  const user = JSON.parse(
    localStorage.getItem("aquawatch_user") || "{}"
  );


  // Receive selected lake location
  const handleLocationSelect = (location) => {
    if (!location) {
      setFormData((previous) => ({
        ...previous,
        lake_name: "",
        latitude: "",
        longitude: ""
      }));
      return;
    }

    setFormData((previous) => ({
      ...previous,
      lake_name: location.lake_name,
      latitude: String(location.latitude),
      longitude: String(location.longitude)
    }));

    setError("");
    setMessage("");
  };


  // Handle form fields
  const handleChange = (e) => {
    setFormData((previous) => ({
      ...previous,
      [e.target.name]: e.target.value
    }));
  };


  // Photo upload validation
  const handlePhotoChange = (e) => {
    const file = e.target.files[0];

    if (!file) return;

    if (!["image/jpeg", "image/png", "image/webp"].includes(file.type)) {
      setError("Please select a JPG, PNG or WEBP image.");
      e.target.value = "";
      return;
    }

    if (file.size > 5 * 1024 * 1024) {
      setError("Image size must be less than 5 MB.");
      e.target.value = "";
      return;
    }

    setError("");
    setMessage("");
    setPhoto(file);
    setPreview(URL.createObjectURL(file));

    setAnalysis(null);
    setReportId("");
  };


  // Remove selected photo
  const removePhoto = () => {
    if (preview) {
      URL.revokeObjectURL(preview);
    }

    setPhoto(null);
    setPreview("");
    setAnalysis(null);
    setReportId("");
  };


  // Validate GPS coordinates
  const validateCoordinates = () => {
    const { latitude, longitude, lake_name } = formData;

    if (!lake_name.trim() || latitude === "" || longitude === "") {
      setError("Please search for and select your lake location.");
      return false;
    }

    const lat = Number(latitude);
    const lng = Number(longitude);

    if (!Number.isFinite(lat) || lat < -90 || lat > 90) {
      setError("Invalid latitude. Please select the lake again.");
      return false;
    }

    if (!Number.isFinite(lng) || lng < -180 || lng > 180) {
      setError("Invalid longitude. Please select the lake again.");
      return false;
    }

    return true;
  };


  // Submit report
  const handleSubmit = async (e) => {
    e.preventDefault();

    setError("");
    setMessage("");
    setAnalysis(null);
    setReportId("");

    if (!validateCoordinates()) return;

    if (!photo) {
      setError("Please upload a lake photograph.");
      return;
    }

    if (formData.description.trim().length < 5) {
      setError("Please enter a description of at least 5 characters.");
      return;
    }

    setLoading(true);

    try {
      // STEP 1: Upload photo
      setStage("Uploading photograph...");

      const uploadResponse = await uploadPhoto(photo);

      const filename = uploadResponse.filename;
      const photoUrl = uploadResponse.photo_url;

      // STEP 2: AI detection
      setStage("AI is analyzing your photograph...");

      const detectionResponse = await detectPollution(filename);

      const detectionId = detectionResponse.detection_id;
      const aiResult = detectionResponse.analysis;

      setAnalysis(aiResult);

      // STEP 3: Prepare report
      setStage("Saving your pollution report...");

      const reportData = {
        lake_name: formData.lake_name.trim(),
        description: formData.description.trim(),

        latitude: Number(formData.latitude),
        longitude: Number(formData.longitude),

        pollution_type: formData.pollution_type || null,

        photo_url: photoUrl,
        detection_id: detectionId
      };

      // STEP 4: Save in MongoDB
      const reportResponse = await createReport(reportData);

      setReportId(reportResponse.report_id);

      setMessage(
        "Your pollution report was submitted successfully!"
      );

      setStage("");

    } catch (err) {
      setError(
        err.response?.data?.detail ||
        "Something went wrong. Please try again."
      );

      setStage("");

    } finally {
      setLoading(false);
    }
  };


  const handleLogout = () => {
    localStorage.removeItem("aquawatch_token");
    localStorage.removeItem("aquawatch_user");
    navigate("/login");
  };


  const closeMenu = () => setMenuOpen(false);


  return (
    <div className="dashboard-page premium-dashboard pollution-page">

      {/* MOBILE OVERLAY */}
      {menuOpen && (
        <div
          className="pollution-sidebar-overlay"
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
          className="sidebar-link active"
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
          className="sidebar-link"
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
            <h2>Report Pollution</h2>
            <p>Help protect lakes and water resources</p>
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
        <section className="pollution-hero">

          <div className="pollution-hero-content">

            <div className="pollution-hero-tag">
              <ShieldCheck size={15} />
              COMMUNITY WATER PROTECTION
            </div>

            <h1>
              Report Pollution.
              <br />
              <span>Protect Our Lakes.</span>
            </h1>

            <p>
              Upload a photograph, select your lake location
              and help identify visible pollution with AI.
            </p>

            <div className="pollution-hero-note">
              <CheckCircle size={16} />
              Every report makes a difference
            </div>

          </div>

          <div className="pollution-hero-art">
            <div className="pollution-hero-art-icon">
              <Camera size={35} />
            </div>

            <strong>AquaWatch AI</strong>
            <small>Visual pollution detection</small>
          </div>

        </section>


        {/* FORM LAYOUT */}
        <div className="pollution-layout">

          <form
            className="pollution-form premium-panel"
            onSubmit={handleSubmit}
          >

            <div className="pollution-form-heading">
              <div>
                <span>NEW SUBMISSION</span>
                <h2>Pollution Report Form</h2>
                <p>Provide the details of the pollution you observed.</p>
              </div>

              <div className="pollution-form-icon">
                <FileIcon size={24} />
              </div>
            </div>


            {/* PHOTO UPLOAD */}
            <section className="pollution-form-section">

              <div className="pollution-section-heading">
                <div className="pollution-section-icon">
                  <Camera size={19} />
                </div>

                <div>
                  <h3>Lake Photograph</h3>
                  <p>Upload a clear photograph of the pollution.</p>
                </div>
              </div>


              <label className={`pollution-upload-box ${
                preview ? "has-preview" : ""
              }`}>

                {preview ? (
                  <div className="pollution-preview-wrap">

                    <img
                      src={preview}
                      alt="Selected lake"
                    />

                    <div className="pollution-preview-caption">
                      <CheckCircle size={17} />
                      Photograph selected
                    </div>

                  </div>
                ) : (
                  <div className="pollution-upload-placeholder">

                    <div className="pollution-upload-icon">
                      <ImagePlus size={32} />
                    </div>

                    <strong>Click to upload a photograph</strong>

                    <span>
                      or choose an image from your device
                    </span>

                    <small>JPG, PNG or WEBP · Maximum 5 MB</small>

                  </div>
                )}

                <input
                  type="file"
                  accept="image/jpeg,image/png,image/webp"
                  onChange={handlePhotoChange}
                  required={!photo}
                  disabled={loading}
                />

              </label>


              {photo && (
                <div className="pollution-file-info">
                  <div>
                    <ImagePlus size={17} />
                    <span>{photo.name}</span>
                  </div>

                  <button
                    type="button"
                    onClick={removePhoto}
                    disabled={loading}
                    aria-label="Remove selected photo"
                  >
                    <Trash2 size={17} />
                    Remove
                  </button>
                </div>
              )}

            </section>


            {/* LOCATION */}
            <section className="pollution-form-section">

              <div className="pollution-section-heading">
                <div className="pollution-section-icon">
                  <MapPin size={19} />
                </div>

                <div>
                  <h3>Lake Information</h3>
                  <p>
                    Search and select your lake to automatically
                    fill its GPS coordinates.
                  </p>
                </div>
              </div>


              <div className="pollution-location-box">
                <LocationSearch
                  onSelect={handleLocationSelect}
                />
              </div>


              {formData.lake_name && (
                <div className="pollution-selected-location">

                  <div className="pollution-location-success">
                    <CheckCircle size={18} />
                    <strong>Lake location selected</strong>
                  </div>

                  <h4>{formData.lake_name}</h4>

                  <div className="pollution-coordinates">
                    <span>
                      Latitude: {formData.latitude}
                    </span>

                    <span>
                      Longitude: {formData.longitude}
                    </span>
                  </div>

                </div>
              )}

            </section>


            {/* POLLUTION DETAILS */}
            <section className="pollution-form-section">

              <div className="pollution-section-heading">
                <div className="pollution-section-icon">
                  <FileIcon size={19} />
                </div>

                <div>
                  <h3>Pollution Details</h3>
                  <p>Describe the issue you observed at the lake.</p>
                </div>
              </div>


              <div className="pollution-field">

                <label htmlFor="pollution_type">
                  Pollution Type
                  <span>Optional</span>
                </label>

                <select
                  id="pollution_type"
                  name="pollution_type"
                  value={formData.pollution_type}
                  onChange={handleChange}
                  disabled={loading}
                >
                  <option value="">Select pollution type</option>
                  <option value="Floating Waste">Floating Waste</option>
                  <option value="Plastic Waste">Plastic Waste</option>
                  <option value="Oil or Surface Film">Oil or Surface Film</option>
                  <option value="Other">Other</option>
                </select>

              </div>


              <div className="pollution-field">

                <label htmlFor="description">
                  Description
                  <span className="required-label">Required *</span>
                </label>

                <textarea
                  id="description"
                  name="description"
                  placeholder="Describe the pollution observed..."
                  rows="6"
                  value={formData.description}
                  onChange={handleChange}
                  required
                  minLength={5}
                  maxLength={1000}
                  disabled={loading}
                />

                <small className="pollution-character-count">
                  {formData.description.length}/1000 characters
                </small>

              </div>

            </section>


            {/* AI PROCESSING */}
            {loading && (
              <div className="pollution-processing">

                <LoaderCircle size={23} className="pollution-spin" />

                <div>
                  <strong>Processing your report</strong>
                  <p>{stage}</p>
                </div>

              </div>
            )}


            {/* AI RESULTS */}
            {analysis && (
              <section className="pollution-ai-result">

                <div className="pollution-ai-heading">
                  <BrainCircuit size={23} />

                  <div>
                    <h3>AI Detection Results</h3>
                    <p>Visual analysis of your uploaded photograph</p>
                  </div>
                </div>

                <div className="pollution-ai-summary">
                  <span>Model</span>
                  <strong>{analysis.model || "YOLO11n"}</strong>
                </div>

                <div className="pollution-ai-count">
                  <strong>
                    {analysis.total_detections ?? 0}
                  </strong>
                  <span>Floating waste detection(s)</span>
                </div>

                {analysis.detections?.map((item, index) => (
                  <div
                    className="pollution-detection-item"
                    key={index}
                  >
                    <span>{item.class_name}</span>

                    <strong>
                      {(item.confidence * 100).toFixed(2)}% confidence
                    </strong>
                  </div>
                ))}

                <p className="pollution-ai-disclaimer">
                  AI identifies visible floating waste only.
                  It does not determine chemical water quality or toxicity.
                </p>

              </section>
            )}


            {/* ERROR */}
            {error && (
              <div className="pollution-message pollution-error">
                <AlertCircle size={19} />
                <span>{error}</span>
              </div>
            )}


            {/* SUCCESS */}
            {message && (
              <div className="pollution-message pollution-success">

                <CheckCircle size={23} />

                <div>
                  <strong>{message}</strong>

                  <p>Report ID: {reportId}</p>

                  <Link to="/my-reports">
                    View My Reports
                  </Link>
                </div>

              </div>
            )}


            {/* SUBMIT */}
            <button
              type="submit"
              className="pollution-submit-btn"
              disabled={loading || Boolean(reportId)}
            >

              {loading ? (
                <>
                  <LoaderCircle size={19} className="pollution-spin" />
                  Processing Report...
                </>
              ) : reportId ? (
                <>
                  <CheckCircle size={19} />
                  Report Submitted
                </>
              ) : (
                <>
                  <Send size={19} />
                  Submit Pollution Report
                </>
              )}

            </button>


            <p className="pollution-form-footer">
              <ShieldCheck size={15} />
              Your report will be securely saved in AquaWatch.
            </p>

          </form>


          {/* SIDE INFORMATION */}
          <aside className="pollution-info-column">

            <div className="pollution-info-card">

              <div className="pollution-info-icon">
                <BrainCircuit size={23} />
              </div>

              <h3>AI-Powered Detection</h3>

              <p>
                Your uploaded photograph is analyzed by the
                AquaWatch YOLO model to identify visible floating waste.
              </p>

            </div>


            <div className="pollution-info-card">

              <div className="pollution-info-icon">
                <MapPin size={23} />
              </div>

              <h3>Accurate Location</h3>

              <p>
                Select the correct lake location so the report
                includes its GPS coordinates.
              </p>

            </div>


            <div className="pollution-info-card">

              <div className="pollution-info-icon">
                <ShieldCheck size={23} />
              </div>

              <h3>Report Tracking</h3>

              <p>
                After submission, track your report status
                from the My Reports section.
              </p>

              <Link to="/my-reports">
                View My Reports →
              </Link>

            </div>


            <div className="pollution-reminder">
              <Leaf size={22} />

              <strong>Be a Lake Guardian</strong>

              <p>
                Small actions can create a cleaner and healthier
                environment for everyone.
              </p>

            </div>

          </aside>

        </div>


        {/* FOOTER */}
        <footer className="premium-footer">
          AquaWatch © 2026 · Protecting lakes, preserving life.
        </footer>

      </main>

    </div>
  );
}

export default ReportPollution;
