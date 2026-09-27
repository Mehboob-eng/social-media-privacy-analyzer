# 🔒 Social Media Privacy Analyzer

An AI-powered security platform that combines a React web dashboard, Django backend, and a Python desktop monitoring application to enhance users' social media privacy. The system monitors network traffic in real time using Tshark (Wireshark), detects suspicious packets, and provides AI-powered security recommendations through Grok API.

---

## 🚀 Features

* Secure user registration with Email OTP verification
* User authentication and login
* User dashboard
* Profile management
* Enable/Disable Two-Factor Authentication (2FA)
* Session management
* Account deletion
* Real-time network packet monitoring using Tshark (Wireshark)
* Detection of suspicious network traffic
* Automatic threat alerts
* Automatic connection termination upon malicious activity
* AI-powered privacy recommendations using Grok API
* Responsive React-based user interface

---

## 🏗️ System Architecture

```
React Frontend
      │
      ▼
 Django REST API
      │
      ▼
Authentication & User Management
      │
      ▼
Desktop Monitoring Application
      │
      ▼
Tshark Packet Capture
      │
      ▼
Threat Detection
      │
      ▼
Grok AI Recommendation Engine
```

---

## 🛠️ Tech Stack

### Frontend

* React.js
* JavaScript
* HTML5
* CSS3

### Backend

* Python
* Django
* Django REST Framework

### AI Integration

* Grok API

### Network Monitoring

* Tshark (Wireshark)
* PyShark
* Scapy

### Database

* SQLite

### Authentication

* Email OTP Verification
* JWT Authentication
* Two-Factor Authentication (2FA)

### Development Tools

* Git
* GitHub
* VS Code

---

## 📂 Project Structure

```
social-media-privacy-analyzer/
│
├── backend/
│
├── frontend/
│
├── desktop-monitor/
│
├── .env.example
├── .gitignore
├── requirements.txt
└── README.md
```

---

## ⚙️ Installation

### Clone Repository

```bash
git clone https://github.com/Mehboob-eng/social-media-privacy-analyzer.git
```

### Backend

```bash
cd backend
pip install -r requirements.txt
python manage.py migrate
python manage.py runserver
```

### Frontend

```bash
cd frontend
npm install
npm start
```

### Desktop Monitor

Run the desktop monitoring application after installing Tshark (Wireshark).

## 🔮 Future Improvements

* Support for additional social media platforms
* Advanced AI-based threat classification
* Cloud deployment
* Real-time analytics dashboard
* Multi-device monitoring

---

## 👨‍💻 Author

**Mehboob Ashraf**

GitHub: https://github.com/Mehboob-eng
