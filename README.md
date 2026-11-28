# Universal AI Honeypot Engine
### AI-Assisted Adaptive Honeypot for Attacker Behaviour Analysis

## 1. Project Overview

The **Universal AI Honeypot Engine** is a modular cybersecurity monitoring and threat-analysis system designed to simulate vulnerable services, capture suspicious activities, analyse attacker behaviour, and generate forensic reports.

The system integrates rule-based risk assessment, Machine Learning (ML), adaptive response policies, geolocation, and Google Gemini AI to support security investigation.

It supports multiple honeypot domains, allowing suspicious interactions across different protocols and services to be collected and analysed through a centralized dashboard.

## 2. Key Features

- **Multi-Protocol Honeypot:** Simulates Web, SSH, FTP, Telnet, SMTP, POP3, IMAP, DNS, MySQL, PostgreSQL, SMB, RDP, VNC and MSRPC services.
- **Attacker Behaviour Analysis:** Identifies suspicious activities using configurable rule-based detection.
- **Risk Assessment:** Assigns risk scores and classifies events into Low, Medium and High risk levels.
- **Machine Learning:** Uses ML-based event classification and SSH anomaly detection.
- **Adaptive Response:** Selects appropriate response policies based on assessed risk.
- **AI-Powered Forensic Reports:** Uses Google Gemini API to generate dynamic investigation narratives from recorded honeypot evidence.
- **IP Geolocation:** Provides approximate attacker geolocation for supported public IP addresses.
- **SSH Monitoring:** Integrates with Cowrie to capture SSH attacker interactions.
- **Forensic Evidence Integrity:** Generates SHA-256 hashes to support evidence integrity verification.
- **Interactive Dashboard:** Displays event statistics, risk levels, protocol activity and attacker information.
- **Privacy Protection:** Filters sensitive information before sending selected event evidence to Gemini.

## 3. System Architecture

The system follows a modular event-processing architecture.

```text
             Attacker Activity
                    |
                    v
          Honeypot Services
                    |
                    v
            Event Collection
                    |
                    v
             Event Pipeline
                    |
          +---------+---------+
          |                   |
          v                   v
    Behaviour Analysis   ML Prediction
          |              (Shadow Mode)
          v
      Risk Assessment
          |
          v
     Response Policy
          |
          v
      Event Storage
       /         \
      v           v
   SQLite       JSONL
      |
      v
 Dashboard and Forensic Reports
      |
      v
  Gemini AI Analysis
      |
      v
 Dynamic PDF Investigation Report
      |
      v
 SHA-256 Integrity Verification
```

## 4. Technologies Used

| Category | Technologies |
|---|---|
| Programming Language | Python |
| Backend | Flask |
| Frontend | HTML, CSS, JavaScript |
| Database | SQLite |
| Machine Learning | Scikit-learn |
| AI Integration | Google Gemini API |
| SSH Honeypot | Cowrie |
| Data Storage | JSONL |
| PDF Generation | ReportLab |
| Geolocation | IP Geolocation API |
| Version Control | Git and GitHub |
| Operating System | Kali Linux / Ubuntu |

## 5. Project Structure

```text
Universal-AI-Honeypot/
│
├── app.py
├── run_honeypot.py
├── start.sh
├── requirements.txt
├── README.md
│
├── core/
│   ├── behavior_analyzer.py
│   ├── pipeline.py
│   ├── event_engine.py
│   ├── response_policy.py
│   ├── database.py
│   ├── forensic_report.py
│   ├── ai_report_generator.py
│   ├── geoip_manager.py
│   ├── dashboard_analytics.py
│   └── ssh_command_classifier.py
│
├── integrations/
│   └── cowrie_adapter.py
│
├── ml/
│   ├── models/
│   ├── train_model.py
│   ├── predict_event.py
│   ├── predict_ssh.py
│   └── train_ssh_anomaly.py
│
├── services/
│   ├── database/
│   ├── email/
│   ├── network/
│   ├── remote_access/
│   ├── web/
│   └── windows/
│
├── static/
│   ├── css/
│   └── js/
│
├── templates/
│   ├── dashboard.html
│   └── event_report.html
│
└── test files
```

## 6. Installation and Setup

### Prerequisites

- Python 3
- Git
- Kali Linux or Ubuntu
- Virtual environment support
- Internet connection for Gemini API and supported geolocation lookups

### Step 1: Clone the Repository

```bash
git clone <YOUR_REPOSITORY_URL>
cd <PROJECT_DIRECTORY>
```

### Step 2: Create a Virtual Environment

```bash
python3 -m venv venv
```

Activate it:

```bash
source venv/bin/activate
```

### Step 3: Install Dependencies

```bash
pip install -r requirements.txt
```

### Step 4: Configure Gemini API

Create a `.env` file in the project root directory.

```env
GEMINI_API_KEY=YOUR_GEMINI_API_KEY
```

Generate an API key through Google AI Studio:

https://aistudio.google.com/apikey

**Security Notice:** Never upload your `.env` file or API key to GitHub. Keep the file excluded through `.gitignore`.

### Step 5: Start the Honeypot

Run:

```bash
python run_honeypot.py
```

Alternatively, use the startup script if your environment is configured for it:

```bash
chmod +x start.sh
./start.sh
```

### Step 6: Access the Dashboard

Open your browser and visit:

```text
http://127.0.0.1:5000
```

## 7. Gemini AI Forensic Report Generation

The project integrates Google's Gemini API to generate dynamic forensic investigation narratives.

### Workflow

1. Honeypot services capture attacker activity.
2. The event pipeline processes and stores the event.
3. The behaviour analyzer calculates the risk score.
4. Selected and sanitized event evidence is prepared.
5. Gemini analyses the supplied evidence.
6. AI-generated investigation sections are added to the PDF.
7. The final PDF is generated with SHA-256 integrity verification.

### AI-Generated Report Sections

- Executive Summary
- Attack Analysis
- Attacker Behaviour Assessment
- Potential Security Impact
- Security Recommendations
- Investigation Conclusion

The Gemini model is configured in:

```text
core/ai_report_generator.py
```

The current configuration uses:

```python
MODEL_NAME = "gemini-3.5-flash-lite"
```

The AI-generated narrative does not replace the existing rule-based risk score. If Gemini is unavailable, the report generator uses a fallback narrative so that PDF generation can continue.

## 8. Machine Learning Module

The project uses Machine Learning to support event analysis.

### Implemented Components

- Web event classification using TF-IDF and Logistic Regression.
- SSH anomaly detection using Isolation Forest.
- Shadow-mode predictions that do not independently control the response policy.

The rule-based behaviour analyzer remains responsible for the existing risk assessment.

## 9. Forensic Evidence and Security

The forensic reporting module preserves important event information, including:

- Event ID and timestamp
- Attacker source IP
- Protocol and event type
- Risk score and risk level
- Suspicious indicators
- Recorded SSH activity where available
- Machine Learning prediction information
- Evidence integrity hashes

SHA-256 checksums are generated for PDF reports to help verify that the report file has not changed.

Geolocation information is approximate and may not be available for private IP addresses.

## 10. Testing

Run the automated tests using:

```bash
pytest -q
```

Run pipeline tests separately:

```bash
pytest -q test_pipeline.py
```

The pipeline tests cover:

- SSH command classification
- Sensitive-data sanitization
- Web event processing
- ML failure handling

## 11. Security and Ethical Considerations

This project is developed for cybersecurity education, controlled security research and authorized testing.

- Deploy honeypots only in environments you own or have permission to monitor.
- Do not expose sensitive production systems.
- Protect API keys and stored forensic evidence.
- Sanitize event data before external AI processing.
- Treat geolocation as approximate.
- Do not interpret a honeypot interaction as proof of successful compromise.
- Review generated AI analysis alongside the original event evidence.

## 12. Future Enhancements

- Advanced attacker behaviour correlation.
- Improved anomaly detection.
- Multi-event AI forensic analysis.
- Enhanced threat intelligence integration.
- Automated incident investigation.
- Additional protocol simulations.
- Advanced dashboard visualizations.
- Improved detection accuracy and automated testing.

## 13. Project Information

**Project Name:** Universal AI Honeypot Engine

**Project Type:** Cybersecurity / Machine Learning / Artificial Intelligence

**Primary Language:** Python

**AI Integration:** Google Gemini API

**Backend:** Flask

**Database:** SQLite

**Version Control:** GitHub

## 14. Author

**Developed as an academic cybersecurity project.**

---

*Universal AI Honeypot Engine – Intelligent Attacker Behaviour Analysis and AI-Assisted Digital Forensics.*
