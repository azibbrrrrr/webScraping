# McDonald's Outlet Finder - Backend (FastAPI)

## 📌 Overview

This repository contains the **FastAPI backend** for the **McDonald's Outlet Finder** project. It provides APIs for:

- Fetching McDonald's outlets in **Kuala Lumpur**.
- Retrieving details of a **specific outlet**.
- **AI-powered search** using GPT-4o-mini for natural language queries (e.g., "Which outlets in KL operate 24 hours?").

## 🚀 Live API & Documentation

- **Backend API (Railway):** [https://web-production-c43c.up.railway.app/](https://web-production-c43c.up.railway.app/)
- **API Documentation (Swagger UI):** [https://web-production-c43c.up.railway.app/docs](https://web-production-c43c.up.railway.app/docs)

## 📄 Full Project Documentation

The full project documentation is available in **PDF format**:
[📥 Download Project Documentation (PDF)](docs/Project_Documentation.pdf)

## 🛠️ Setup Instructions

### 1️⃣ Clone the Repository

```sh
git clone "https://github.com/azibbrrrrr/webScraping.git"
cd webScraping
```

### 2️⃣ Install Dependencies

```sh
pip install -r requirements.txt
```

### 3️⃣ Run the FastAPI Server

```sh
uvicorn app.main:app --reload
```

## 🔹 API Endpoints

| Method | Endpoint               | Description                                 |
| ------ | ---------------------- | ------------------------------------------- |
| `GET`  | `/outlets`             | Fetch all outlets (filters: `city`, `name`) |
| `GET`  | `/outlets/{outlet_id}` | Fetch details of a specific outlet          |
| `GET`  | `/search`              | AI-powered search based on user query       |

---

## 🔗 Related Repositories

🔹 **Frontend Repository (Next.js)**:
[https://github.com/azibbrrrrr/mcdonalds-outlets-map](https://github.com/azibbrrrrr/mcdonalds-outlets-map)

For more details, refer to the **full project documentation (PDF)**.
