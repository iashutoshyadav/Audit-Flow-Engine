# Deployment Guide: Vercel & Render

## Overview

This guide explains how to deploy your **Financial Extractor Pro** application.

- **Frontend**: [Vercel](https://vercel.com/)
- **Backend**: [Render](https://render.com/)

---

## 1. Prerequisites

1.  **Code on GitHub**: Ensure your project is pushed to a GitHub repository.
2.  **Config Files**: We've already added:
    -   `backend/requirements.txt` (Python dependencies)
    -   `backend/render.yaml` (Backend configuration)
    -   `frontend/vercel.json` (Frontend routing rules)

---

## 2. Deploy Backend (Render)

1.  Log in to [Render Dashboard](https://dashboard.render.com/).
2.  Click **New +** -> **Web Service**.
3.  Connect your GitHub repository.
4.  **Configuration**:
    -   **Name**: `financial-extractor-backend`
    -   **Root Directory**: `backend`
    -   **Runtime**: Python 3
    -   **Build Command**: `pip install -r requirements.txt`
    -   **Start Command**: `uvicorn app.main:app --host 0.0.0.0 --port 10000`
5.  **Environment Variables**:
    -   Click **Advanced**.
    -   Add `PYTHON_VERSION` with value `3.11.0`.
    -   Add `PORT` with value `10000`.
6.  Click **Create Web Service**.

**Wait for Deployment**: Once live, copy the URL (e.g., `https://financial-extractor-backend.onrender.com`).

---

## 3. Deploy Frontend (Vercel)

1.  Log in to [Vercel Dashboard](https://vercel.com/dashboard).
2.  Click **Add New...** -> **Project**.
3.  Import your GitHub repository.
4.  **Framework Preset**: Select **Vite**.
5.  **Root Directory**: Click **Edit** and select `frontend`.
6.  **Environment Variables**:
    -   Name: `VITE_API_URL`
    -   Value: Your Render Backend URL (e.g., `https://financial-extractor-backend.onrender.com`).
    -   **Important**: Remove any trailing slash `/`.
7.  Click **Deploy**.

---

## 4. Final Steps

1.  Visit your Vercel deployment URL.
2.  The app should load with the Aurora background.
3.  Try uploading a PDF to test the connection.

### Troubleshooting
-   **CORS Error**: If the frontend can't talk to the backend, update `backend/app/main.py` -> `allow_origins`. Add your Vercel domain there.
-   **Database Reset**: On the free tier of Render, the SQLite database resets on restarts. For production, consider using Render PostgreSQL.
