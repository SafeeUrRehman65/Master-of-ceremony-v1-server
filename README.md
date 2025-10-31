# Master of Ceremony v1 – Server 🧠🎙️

This is the **Python backend** for the *Master of Ceremony v1* project.  
It powers the real-time audio processing, WebSocket streaming, and backend API that supports the [frontend app](https://github.com/SafeeUrRehman65/Master-of-ceremony-v1-frontend).

---

## 🚀 Tech Stack

- **Python 3.10+**  
- **FastAPI** – modern, high-performance web framework  
- **Uvicorn** – lightning-fast ASGI server  
- **WebSockets** – for real-time bi-directional communication  
- **Threading / AsyncIO** – for handling concurrent audio streams  
- **Pydantic** – data validation  
- **dotenv** – for environment variable management  

---

## 🧭 Features

- Real-time **WebSocket** endpoint for sending/receiving audio data  
- Threaded queue system for concurrent audio and text processing  
- Handles **audio decoding**, **transcription**, and **response streaming**  
- Designed for scalability and fast response times  
- Clean, modular structure for future expansion  

---

## 🛠️ Getting Started

### Prerequisites

- Python **3.10 or higher**
- `pip` or `uv` (recommended for fast installs)
- (Optional) Virtual environment setup

---

### 1️⃣ Clone the repository
```bash
git clone https://github.com/SafeeUrRehman65/Master-of-ceremony-v1-server.git
cd Master-of-ceremony-v1-server
```

### 2️⃣ Create and activate a virtual environment
```bash
python -m venv venv
# On Windows
venv\Scripts\activate
# On macOS / Linux
source venv/bin/activate
```

### 3️⃣ Install dependencies
```bash
pip install -r requirements.txt
```

### 4️⃣ Run the development server
```bash
uvicorn main:app --reload --port 8080
```
Server will start on:
👉 http://127.0.0.1:8080

If 8080 is already in use, change the port:
```bash
uvicorn main:app --reload --port 8081
```

### ✅ Contributing

1. **Fork the repository**
2. **Create a feature branch:**
```bash
git checkout -b feature/my-feature
```
3. **Commit and push your changes:**
```bash
git push origin feature/my-feature
```
4. **Open a Pull Request 🚀**