# How to Configure Render for Docker Deployment

The live server needs **Tesseract OCR** to read scanned PDFs. This tool is installed via Docker. Follow these steps to ensure your Render service is using Docker.

## Option 1: Create a New Service (Recommended & Easiest)

If you have a "Web Service" currently set to "Python", it is often easiest specifically to just create a new one for Docker.

1.  Go to your **Render Dashboard**.
2.  Click **New +** -> **Web Service**.
3.  Connect your GitHub repository (`Audit-Flow-Engine`).
4.  **Crucial Step**: When asked for "Runtime" or "Environment", select **Docker**.
    *   *Note: If it detects `render.yaml`, it might auto-select Docker. If not, select it manually.*
5.  Click **Create Web Service**.
6.  Wait for the build to finish. It will install Tesseract automatically.

## Option 2: Check Existing Service Settings

If you want to keep your current service URL:

1.  Go to your **Render Dashboard**.
2.  Click on your `financial-extractor-backend` service.
3.  Click on **Settings** in the left sidebar.
4.  Scroll down to the **Environment** section.
5.  Check the **Runtime** label.
    *   **If it says "Docker"**: You are good! Just wait for the latest deployment to finish.
    *   **If it says "Python 3"**: You **MUST** change it to **Docker**.
        *   If there is no "Edit" button to switch runtime, you **must use Option 1** (Create New Service). Render often locks the runtime after creation.

## Option 3: Deploy via Blueprint (Advanced)

Since I pushed a `render.yaml` file:

1.  Go to **Render Dashboard**.
2.  Click **New +** -> **Blueprint**.
3.  Connect your repository.
4.  It will read the `render.yaml` file and automatically create a service with **Docker** and the correct settings.
5.  Click **Apply**.

---
**Summary**: The key is that the service **Runtime** must be **Docker**, not Python.
