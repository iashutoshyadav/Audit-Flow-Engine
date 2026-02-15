# How to Test Locally

Follow these steps to run the application on your local machine.

## Prerequisites
- Python 3.10+
- Node.js & npm

## 1. Start the Backend Server

Open a new terminal and run:

```powershell
cd backend
# Activate virtual environment if you have one (optional but recommended)
# .\venv\Scripts\activate 

# Install dependencies if you haven't already
pip install -r requirements.txt

# Start the server
uvicorn app.main:app --reload
```

The backend will start at `http://127.0.0.1:8000`.

## 2. Start the Frontend Application

Open a **separate** terminal and run:

```powershell
cd frontend

# Install dependencies if you haven't already
npm install

# Start the development server
npm run dev
```

The frontend will start at `http://localhost:3000` (configured in `vite.config.js`).

## 3. Verify the Fix

1. Open your browser and go to `http://localhost:3000`.
2. Upload the **Tata Motors PDF**.
3. Wait for the extraction to complete (should take ~10-15 seconds).
4. Download the Excel report.
5. **Check the Excel file**: You should now see data rows filled in for Revenue, Expenses, Assets, etc., instead of just headers.
