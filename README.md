# Student Wellbeing Companion

A Full-Stack Web Application for Integrated Student Wellbeing and Academic Management.

## 1. Project Overview

Student Wellbeing Companion is a web-based platform developed to support students in managing their academic responsibilities and personal wellbeing through a unified digital environment.

The application integrates emotional self-monitoring, AI-assisted conversational support, academic task management, peer-to-peer communication, and digital counselling request management.

It provides a centralised interface for students and a dedicated administrative interface for managing student-related activities and counselling workflows.

## 2. Problem Statement

Students often experience academic pressure, stress, and difficulties accessing appropriate support services. Academic planning and wellbeing support are frequently managed through separate platforms, making it difficult to access these services in one place.

This project addresses these challenges by providing an integrated platform that combines academic organisation and student wellbeing support.

## 3. Project Objectives

- Develop a unified student wellbeing and academic management platform.
- Provide emotional self-monitoring through a Mood Tracker.
- Support academic organisation through task scheduling and reminders.
- Implement an AI-assisted conversational interface.
- Enable peer-to-peer interaction among authenticated students.
- Digitise counselling request submission and management.
- Provide administrative facilities for student and request management.

## 4. Key Features and Modules

### Student Modules

**1. User Authentication**
- Student registration and login.
- Session management.
- Authenticated access to student functionalities.

**2. Student Dashboard**
- Centralised access to application modules.
- Overview of available student functionalities.

**3. Mood Tracker**
- Emotional self-monitoring.
- Recording and reviewing mood information.

**4. Study Planner**
- Academic task organisation.
- Study activity management.

**5. Reminders**
- Reminder creation and management.
- Support for organising academic activities.

**6. AI Assistant**
- AI-assisted conversational interface.
- Supportive responses to student messages.
- Encourages positive wellbeing practices.

**7. Peer Support**
- Student-to-student communication.
- Publishing queries and viewing posts from other students.
- Reply management through individual student accounts.
- Encourages collaborative support.

**8. Counselling Management**
- Online counselling request submission.
- Preferred counselling date selection.
- Request status tracking.

**9. Notification System**
- Displays important student updates.
- Provides counselling request status notifications.
- Supports notification status management.

### Administrator Modules

**1. Admin Authentication**
- Separate administrator login.
- Authenticated administrative access.

**2. Admin Dashboard**
- Centralised administrative interface.
- Overview of counselling request statistics.

**3. Counselling Request Management**
- View submitted counselling requests.
- Approve or reject requests.
- Update request status.

**4. Student Management**
- View and manage student information.

## 5. Technology Stack

| Layer | Technologies |
|---|---|
| Frontend | React.js, Vite, JavaScript |
| UI Development | HTML5, CSS3 |
| Backend | Python, Flask |
| API Communication | REST API |
| Database | MySQL |
| Version Control | Git, GitHub |

## 6. System Architecture

The application follows a three-tier architecture.

### Presentation Layer
React.js and Vite are used to develop the frontend interface and handle user interactions.

### Application Layer
Python Flask manages backend application logic, authentication, API requests, and communication with the database.

### Data Layer
MySQL provides persistent data storage and retrieval for application information.

### Architecture Workflow

1. The user interacts with the React.js frontend.
2. The frontend sends HTTP requests to Flask API endpoints.
3. Flask processes the requests and executes the required application logic.
4. The backend communicates with the MySQL database.
5. The server returns the appropriate response to the frontend.
6. React.js updates the user interface based on the response.

## 7. Counselling Request Workflow

1. The student logs into the application.
2. The student submits a counselling request.
3. Flask processes the request and stores the information in MySQL.
4. The administrator views the submitted request through the Admin Dashboard.
5. The administrator approves or rejects the request.
6. The request status is updated.
7. A notification is made available to the student's account.

## 8. Installation and Setup

### Prerequisites

Ensure that the following software is installed:

- Python
- Node.js and npm
- MySQL Server
- Git
- Visual Studio Code (recommended)

### Step 1: Clone the Repository

```bash
git clone https://github.com/rekhatanushree/Student_Wellbeing_Companion.git
```

Navigate into the project directory:

```bash
cd Student_Wellbeing_Companion
```

### Step 2: Backend Setup

Navigate to the backend directory:

```bash
cd backend
```

Create a Python virtual environment:

```bash
python -m venv venv
```

Activate the virtual environment on Windows:

```powershell
.\venv\Scripts\Activate.ps1
```

Install the required Python dependencies:

```bash
pip install -r requirements.txt
```

Configure the MySQL database connection using the appropriate local configuration or environment variables.

Start the Flask backend:

```bash
python app.py
```

### Step 3: Frontend Setup

Open a separate terminal and navigate to the frontend directory:

```bash
cd frontend
```

Install the required Node.js dependencies:

```bash
npm install
```

Start the Vite development server:

```bash
npm run dev
```

Open the local frontend URL displayed in the terminal.

## 9. Database Configuration

The application uses MySQL for persistent data management.

Configure the database name, username, password, and connection settings according to the backend configuration.

Ensure that the required database and tables are created before running the application.

**Security Note:** Database credentials, secret keys, and sensitive student information must not be committed to the public repository.

## 10. Testing

The application has been tested for its major functional workflows, including:

- Student registration and authentication.
- Student login and logout.
- Dashboard navigation.
- Mood Tracker functionality.
- Study Planner and Reminders.
- AI Assistant interaction.
- Peer Support posting and replies.
- Counselling request submission.
- Administrator approval and rejection of requests.
- Notification generation and status updates.
- Student Management functionality.

## 11. Future Enhancements

- Development of a dedicated mobile application.
- Enhanced student progress monitoring.
- Additional reporting and analytics capabilities.
- Improved accessibility and user experience.
- Expansion of student wellbeing resources.

## 12. Project Purpose

Student Wellbeing Companion aims to integrate academic organisation and student wellbeing support into a unified web application.

By combining student-centric functionalities with administrative request management, the platform provides an organised digital environment that encourages academic responsibility, student interaction, and access to wellbeing support.

---

**Project:** Student Wellbeing Companion  
**Category:** Full-Stack Web Application  
**Frontend:** React.js  
**Backend:** Python Flask  
**Database:** MySQL  
**Version Control:** Git and GitHub