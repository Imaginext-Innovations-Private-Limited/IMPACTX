
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
  Leaf,
  BookOpen,
  UserPlus,
  Upload,
  BrainCircuit,
  Map,
  CircleHelp,
  ChevronDown,
  ChevronUp,
  ShieldCheck,
  Database,
  ArrowRight
} from "lucide-react";


function Support() {
  const navigate = useNavigate();

  const [menuOpen, setMenuOpen] = useState(false);
  const [activeFaq, setActiveFaq] = useState(0);

  const user = JSON.parse(
    localStorage.getItem("aquawatch_user") || "{}"
  );

  const closeMenu = () => setMenuOpen(false);


  // Logout
  const handleLogout = () => {
    localStorage.removeItem("aquawatch_token");
    localStorage.removeItem("aquawatch_user");
    navigate("/login");
  };


  // User guide steps
  const steps = [
    {
      number: "01",
      icon: UserPlus,
      title: "Create an Account",
      description:
        "Register using your name, email address and password. After registration, log in to access your AquaWatch dashboard.",
      link: "/register",
      linkText: "Create Account"
    },
    {
      number: "02",
      icon: Upload,
      title: "Report Lake Pollution",
      description:
        "Open Report Pollution, upload a JPG, PNG or WEBP photograph (maximum 5 MB), search for the lake and select its correct location. Add a description and submit your report.",
      link: "/report",
      linkText: "Report Pollution"
    },
    {
      number: "03",
      icon: BrainCircuit,
      title: "AI Image Detection",
      description:
        "AquaWatch uses its integrated YOLO11n model to identify supported visible pollution-related objects in uploaded photographs.",
      link: "/report",
      linkText: "Try AI Detection"
    },
    {
      number: "04",
      icon: FileText,
      title: "Track Your Reports",
      description:
        "Open My Reports to view your submitted pollution reports, photographs, lake details and current report statuses.",
      link: "/my-reports",
      linkText: "View My Reports"
    },
    {
      number: "05",
      icon: Map,
      title: "Explore the Lake Map",
      description:
        "Open Lake Map to explore pollution reports with valid GPS coordinates. Use the available status filters to view different report categories.",
      link: "/map",
      linkText: "Explore Map"
    },
    {
      number: "06",
      icon: Database,
      title: "Check Water Quality",
      description:
        "Search for a lake, select its location and choose a search radius. AquaWatch retrieves available nearby historical CPCB records and displays measurements, charts and station details.",
      link: "/water-quality",
      linkText: "Check Water Quality"
    }
  ];


  // Frequently asked questions
  const faqs = [
    {
      question: "How do I submit a pollution report?",
      answer:
        "Log in, open Report Pollution, upload a lake photograph, search and select the lake location, enter a description and submit the form. The image is analysed by the integrated AI model before the report is saved."
    },
    {
      question: "Which image formats are supported?",
      answer:
        "The report upload form supports JPG, PNG and WEBP images with a maximum file size of 5 MB."
    },
    {
      question: "Does AI detect every type of pollution?",
      answer:
        "No. The YOLO11n model detects only the object categories it was trained to recognise. Results depend on image quality, visibility and model performance."
    },
    {
      question: "Does AI measure water contamination?",
      answer:
        "No. AI image detection identifies visible objects in photographs. It cannot measure pH, chemical contamination, toxicity or drinking-water safety."
    },
    {
      question: "Are water-quality readings live?",
      answer:
        "No. The Water Quality module currently displays historical CPCB monitoring records. These are not live sensor measurements."
    },
    {
      question: "Why are no nearby CPCB records displayed?",
      answer:
        "There may be no available monitoring records within your selected radius. Try increasing the search radius to find more nearby stations."
    },
    {
      question: "Why is my report not visible on the map?",
      answer:
        "The map displays reports with valid GPS coordinates. Check that the correct lake location was selected while submitting the report."
    },
    {
      question: "Can I download a water-quality report?",
      answer:
        "Yes. After selecting a lake and retrieving historical readings, use the Download PDF button on the Water Quality page."
    }
  ];


  return (
    <div className="dashboard-page premium-dashboard support-premium-page">

      {/* MOBILE OVERLAY */}
      {menuOpen && (
        <div
          className="support-sidebar-overlay"
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
          className="sidebar-link"
          onClick={closeMenu}
        >
          <Droplets size={19} />
          Water Quality
        </Link>


        <p className="premium-nav-label support-nav-heading">
          HELP & INFORMATION
        </p>


        <Link
          to="/support"
          className="sidebar-link active"
          onClick={closeMenu}
        >
          <CircleHelp size={19} />
          Support & Guide
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
            <h2>Support & User Guide</h2>
            <p>Learn how to use AquaWatch</p>
          </div>

          <div className="premium-topbar-right">
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
        <section className="support-hero">

          <div className="support-hero-content">

            <span className="support-hero-tag">
              <BookOpen size={15} />
              AQUAWATCH HELP CENTER
            </span>

            <h1>
              Need Help?
              <br />
              <span>We're Here to Guide You.</span>
            </h1>

            <p>
              Learn how to report lake pollution, use AI detection,
              explore pollution locations and understand water-quality data.
            </p>

            <Link
              to="/report"
              className="support-hero-button"
            >
              <Camera size={18} />
              Start Reporting
              <ArrowRight size={17} />
            </Link>

          </div>


          <div className="support-hero-art">

            <div className="support-hero-icon">
              <CircleHelp size={46} />
            </div>

            <strong>AquaWatch Guide</strong>

            <small>
              Your guide to protecting lakes
            </small>

          </div>

        </section>


        {/* INTRO */}
        <section className="support-intro">

          <div>
            <span>GETTING STARTED</span>

            <h2>How to use AquaWatch</h2>

            <p>
              Follow these simple steps to explore the platform
              and contribute to lake protection.
            </p>
          </div>

          <div className="support-intro-badge">
            <ShieldCheck size={20} />
            <span>Citizen User Guide</span>
          </div>

        </section>


        {/* STEP CARDS */}
        <section className="support-steps-grid">

          {steps.map((step) => {
            const Icon = step.icon;

            return (
              <article
                className="support-step-card"
                key={step.number}
              >

                <div className="support-step-top">

                  <span className="support-step-number">
                    {step.number}
                  </span>

                  <div className="support-step-icon">
                    <Icon size={23} />
                  </div>

                </div>

                <h3>{step.title}</h3>

                <p>{step.description}</p>

                <Link
                  to={step.link}
                  className="support-step-link"
                >
                  {step.linkText}
                  <ArrowRight size={15} />
                </Link>

              </article>
            );
          })}

        </section>


        {/* IMPORTANT INFORMATION */}
        <section className="support-info-section">

          <div className="support-section-heading">
            <span>IMPORTANT INFORMATION</span>
            <h2>Understand the platform</h2>
          </div>


          <div className="support-info-grid">

            <div className="support-info-card">

              <div className="support-info-icon aqua">
                <BrainCircuit size={22} />
              </div>

              <h3>AI Detection Limitations</h3>

              <p>
                AI analyses visible objects in uploaded photographs.
                Detection depends on the categories supported by the
                trained model. It does not determine chemical pollution
                or water safety.
              </p>

            </div>


            <div className="support-info-card">

              <div className="support-info-icon blue">
                <Database size={22} />
              </div>

              <h3>Historical CPCB Data</h3>

              <p>
                Water-quality information comes from available historical
                government monitoring records. Nearby stations may monitor
                a different water body from the selected lake.
              </p>

            </div>


            <div className="support-info-card">

              <div className="support-info-icon green">
                <MapPin size={22} />
              </div>

              <h3>Location Accuracy</h3>

              <p>
                Select the correct lake from the location search results.
                GPS coordinates help display reports on the pollution map
                and find nearby monitoring stations.
              </p>

            </div>

          </div>

        </section>


        {/* FAQ */}
        <section className="support-faq-section">

          <div className="support-section-heading">
            <span>COMMON QUESTIONS</span>
            <h2>Frequently Asked Questions</h2>

            <p>
              Quick answers to common questions about using AquaWatch.
            </p>
          </div>


          <div className="support-faq-list">

            {faqs.map((faq, index) => (

              <div
                className={`support-faq-item ${
                  activeFaq === index ? "expanded" : ""
                }`}
                key={index}
              >

                <button
                  className="support-faq-question"
                  onClick={() =>
                    setActiveFaq(
                      activeFaq === index ? -1 : index
                    )
                  }
                >

                  <span>{faq.question}</span>

                  {activeFaq === index
                    ? <ChevronUp size={19} />
                    : <ChevronDown size={19} />
                  }

                </button>


                {activeFaq === index && (
                  <div className="support-faq-answer">
                    {faq.answer}
                  </div>
                )}

              </div>

            ))}

          </div>

        </section>


        {/* QUICK LINKS */}
        <section className="support-quick-links">

          <div>
            <span>QUICK ACCESS</span>
            <h2>Ready to get started?</h2>

            <p>
              Choose a feature and start exploring AquaWatch.
            </p>
          </div>

          <div className="support-quick-buttons">

            <Link to="/report">
              <Camera size={17} />
              Report Pollution
            </Link>

            <Link to="/map">
              <MapPin size={17} />
              Open Lake Map
            </Link>

            <Link to="/water-quality">
              <Droplets size={17} />
              Water Quality
            </Link>

          </div>

        </section>


        {/* FOOTER */}
        <footer className="premium-footer">
          AquaWatch © 2026 · Protecting lakes, preserving life.
        </footer>

      </main>

    </div>
  );
}

export default Support;
