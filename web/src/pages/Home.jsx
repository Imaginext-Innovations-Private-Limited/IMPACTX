import { Link } from "react-router-dom";
import {
  Waves,
  MapPin,
  ShieldCheck,
  BrainCircuit,
  ArrowRight,
  Droplets,
  Activity,
  Camera
} from "lucide-react";

function Home() {
  return (
    <div className="home-page">

      <nav className="navbar">
        <div className="brand">
          <Waves size={30} />
          <span>AquaWatch</span>
        </div>

        <div className="nav-links">
          <a href="#home">Home</a>
          <a href="#features">Features</a>
          <a href="#about">About</a>
        </div>

        <div className="nav-actions">
  <Link to="/login" className="login-btn">Login</Link>
  <Link to="/register" className="register-btn">Get Started</Link>
</div>
      </nav>

      <section className="hero" id="home">
        <div className="hero-content">
          <span className="tag">
            AI POWERED WATER MONITORING
          </span>

          <h1>
            Protect Our Lakes.
            <span> Preserve Our Future.</span>
          </h1>

          <p>
            AquaWatch uses artificial intelligence and
            community participation to identify floating
            waste and monitor lake pollution.
          </p>

          <div className="hero-buttons">
            <Link to="/login" className="primary-btn">
  Report Pollution <ArrowRight size={18} />
</Link>
            

            <button className="secondary-btn">
              Explore Platform
            </button>
          </div>

          <div className="hero-points">
            <span><ShieldCheck size={17} /> Community Driven</span>
            <span><BrainCircuit size={17} /> AI Powered</span>
          </div>
        </div>

        <div className="hero-visual">
          <div className="water-card">
            <Waves size={70} />
            <h2>Clean Water</h2>
            <p>Healthy Lakes, Better Tomorrow</p>
            <div className="water-status">
              <span></span> Monitoring Platform
            </div>
          </div>
        </div>
      </section>

      <section className="stats-section">
        <div className="stat-card">
          <Droplets />
          <h2>Water Protection</h2>
          <p>Promoting cleaner lakes</p>
        </div>

        <div className="stat-card">
          <Camera />
          <h2>Photo Reporting</h2>
          <p>Citizen pollution reports</p>
        </div>

        <div className="stat-card">
          <BrainCircuit />
          <h2>AI Detection</h2>
          <p>Floating waste identification</p>
        </div>

        <div className="stat-card">
          <MapPin />
          <h2>Location Tracking</h2>
          <p>Map pollution hotspots</p>
        </div>
      </section>

      <section className="features-section" id="features">
        <span className="tag">OUR TECHNOLOGY</span>
        <h2>Smarter Lake Monitoring</h2>
        <p>
          Technology and community action working together
          to protect our water resources.
        </p>

        <div className="feature-grid">
          <div className="feature-card">
            <BrainCircuit size={35} />
            <h3>AI Pollution Detection</h3>
            <p>
              Custom YOLO model analyses images to identify
              floating waste.
            </p>
          </div>

          <div className="feature-card">
            <MapPin size={35} />
            <h3>Pollution Mapping</h3>
            <p>
              Geographic locations help identify affected
              lakes and pollution hotspots.
            </p>
          </div>

          <div className="feature-card">
            <Activity size={35} />
            <h3>Report Tracking</h3>
            <p>
              Citizens can submit reports and track their
              complaint status.
            </p>
          </div>
        </div>
      </section>

      <footer id="about">
        <div className="brand">
          <Waves size={25} />
          AquaWatch
        </div>
        <p>Technology for cleaner lakes and a healthier future.</p>
        <small>© 2026 AquaWatch. All rights reserved.</small>
      </footer>

    </div>
  );
}

export default Home;
