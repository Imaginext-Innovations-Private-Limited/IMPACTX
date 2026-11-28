
# IMPACTX – Team Nexora

**The Industry Driven Hackathon | Dayananda Sagar University | Imaginext & Wise Work**

## Project: AquaWatch

AquaWatch is an AI-powered lake and water quality monitoring platform that enables citizens to report pollution using photographs and GPS locations.

The platform uses YOLO11n for visible waste detection, maps pollution reports, and provides historical CPCB water-quality data to support environmental awareness and lake protection.

## Key Features

- **Pollution Reporting:** Citizens can report lake pollution with photographs and GPS locations.
- **AI-Based Detection:** Uses YOLO11n to detect visible waste and pollution.
- **Interactive Lake Map:** Displays reported pollution locations.
- **Water Quality Monitoring:** Provides historical CPCB water-quality information.
- **User Authentication:** Supports secure user registration and login.
- **Report Management:** Allows users to submit and track pollution reports.

## Technology Stack

### Frontend
- React.js
- JavaScript
- HTML
- CSS
- Vite

### Backend
- Python
- FastAPI
- REST APIs

### Database
- MongoDB

### Artificial Intelligence
- YOLO11n
- Python
- Computer Vision

## Project Structure

```text
AquaWatch/
│
├── ai model/
│   ├── convert_annotations.py
│   ├── data.yaml
│   ├── split_dataset.py
│   ├── test_model.py
│   └── train.py
│
├── backend/
│   ├── app/
│   │   ├── ai/
│   │   ├── routers/
│   │   ├── schemas/
│   │   ├── utils/
│   │   ├── database.py
│   │   └── main.py
│   ├── data/
│   │   └── water_quality/
│   └── requirement.txt
│
├── web/
│   ├── public/
│   ├── src/
│   │   ├── components/
│   │   ├── pages/
│   │   ├── services/
│   │   ├── App.jsx
│   │   └── main.jsx
│   ├── package.json
│   └── vite.config.js
│
├── .gitignore
└── README.md
```

## Team

**Team Name:** Nexora

**Hackathon:** IMPACTX

**Institution:** Dayananda Sagar University

## Objective

To develop an intelligent and accessible platform that helps citizens identify, report, and monitor lake pollution using artificial intelligence, geolocation, and water-quality data.

## Project Vision

To promote cleaner lakes, improve environmental awareness, and support data-driven water pollution monitoring through technology.
