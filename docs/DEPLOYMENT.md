# McLarens Transformation Excel Assistant (MTEA)

## Complete Setup & Deployment Guide

---

## Architecture Overview

```
┌─────────────────────┐     HTTPS      ┌─────────────────────┐     API      ┌──────────────┐
│   Excel Desktop     │ ◄───────────► │   Vercel (Frontend)  │ ◄─────────► │ Render (API)  │
│   Office Add-in     │                │   Static HTML/JS     │             │ FastAPI + AI   │
│   - Taskpane UI     │                │   - taskpane.html    │             │ - Gemini Vision│
│   - Office.js       │                │   - taskpane.js/css  │             │ - OpenRouter   │
└─────────────────────┘                └─────────────────────┘             └──────────────┘
```

---

## 1. Prerequisites

- **Node.js** 18+ (for frontend build)
- **Python** 3.11+ (for backend)
- **Git** (for deployment)
- **Gemini API Key** from [Google AI Studio](https://aistudio.google.com/app/apikey)
- **Vercel account** (free) at [vercel.com](https://vercel.com)
- **Render account** (free) at [render.com](https://render.com)
- **Microsoft 365 subscription** (for Excel Add-in deployment)

---

## 2. Local Development Setup

### Backend

```bash
cd backend

# Create virtual environment
python -m venv venv
source venv/bin/activate       # Mac/Linux
# venv\Scripts\activate        # Windows

# Install dependencies
pip install -r requirements.txt

# Configure environment
cp .env.example .env
# Edit .env and add your GEMINI_API_KEY

# Run development server
uvicorn main:app --reload --port 8000
```

Verify: Open `http://localhost:8000/health` — should return `{"status": "ok", ...}`

### Frontend

```bash
cd excel-addin

# Install dependencies
npm install

# Start dev server (HTTPS on port 3000)
npm start
```

Verify: Open `https://localhost:3000/taskpane.html`

### Sideload in Excel (Development)

1. Open Excel Desktop
2. Go to **Insert** → **My Add-ins** → **Upload My Add-in**
3. Browse to `excel-addin/manifest.xml`
4. The add-in appears in the Home tab ribbon

---

## 3. Deploy Backend to Render

### Option A: Dashboard Deploy

1. Push `backend/` to a GitHub repo
2. Go to [render.com/dashboard](https://dashboard.render.com)
3. **New** → **Web Service**
4. Connect your GitHub repo
5. Configure:
   - **Name:** `mtea-backend`
   - **Root Directory:** `backend`
   - **Runtime:** Python
   - **Build Command:** `pip install -r requirements.txt`
   - **Start Command:** `uvicorn main:app --host 0.0.0.0 --port $PORT`
   - **Plan:** Free
6. **Environment Variables:**
   - `GEMINI_API_KEY` = your key
   - `OPENROUTER_API_KEY` = your key (optional)
   - `ALLOWED_ORIGINS` = `https://your-frontend.vercel.app`
   - `MAX_FILE_SIZE_MB` = `10`
7. Click **Create Web Service**
8. Note your Render URL: `https://mtea-backend.onrender.com`

### Option B: Blueprint Deploy

1. Push entire repo with `render.yaml` in `backend/`
2. Render Dashboard → **Blueprints** → Connect repo
3. Render auto-creates the service from `render.yaml`

**⚠️ Note:** Render free tier has cold starts (~30s first request after sleep). The frontend shows "Warming up..." during this.

---

## 4. Deploy Frontend to Vercel

### Before Deploying — Update URLs

1. **`manifest.xml`** — Replace ALL `https://localhost:3000` with your Vercel URL:
   ```xml
   <SourceLocation DefaultValue="https://your-app.vercel.app/taskpane.html"/>
   ```

2. **`taskpane.js`** — Update the default backend URL:
   ```javascript
   BACKEND_URL: localStorage.getItem("mtea_backend_url") || "https://mtea-backend.onrender.com",
   ```

### Deploy

1. Push `excel-addin/` to GitHub
2. Go to [vercel.com/new](https://vercel.com/new)
3. Import your GitHub repo
4. Configure:
   - **Root Directory:** `excel-addin`
   - **Framework:** Other
   - **Build Command:** `npm run build`
   - **Output Directory:** `dist`
5. Click **Deploy**
6. Note your URL: `https://your-app.vercel.app`

### Update Render CORS

Go back to Render → Environment Variables → Update `ALLOWED_ORIGINS` to include your Vercel URL.

---

## 5. Team Deployment (Microsoft 365)

### Method 1: Admin Center (Recommended)

1. Sign in to [admin.microsoft.com](https://admin.microsoft.com) with admin credentials
2. Navigate: **Settings** → **Integrated apps** → **Upload custom apps**
3. Upload your updated `manifest.xml` (with Vercel URLs)
4. **Assign users:**
   - Entire organization
   - Specific users/groups
   - Just me (for testing first)
5. Click **Deploy**
6. Wait up to 24 hours (usually <1 hour)

### Users Access the Add-in

1. Open Excel Desktop
2. **Insert** → **My Add-ins** → **Admin Managed** tab
3. Click **McLarens Excel Assistant**
4. The taskpane opens on the right side

### Method 2: SharePoint App Catalog

1. SharePoint Admin Center → **More features** → **Apps** → **App Catalog**
2. Create catalog if needed
3. Upload `manifest.xml` to **Apps for Office**
4. Toggle **Enabled** → ON
5. Users find it in **Insert** → **Office Add-ins** → **My Organization**

---

## 6. Configuration

### Settings Screen (In Add-in)

Users can configure:
- **Backend URL** — Points to your Render service
- **Max file size** — Default 10MB
- **Date format** — ISO, DD/MM/YYYY, or MM/DD/YYYY
- **Default currency** — LKR, USD, EUR, GBP

### Environment Variables (Backend)

| Variable | Required | Description |
|----------|----------|-------------|
| `GEMINI_API_KEY` | ✅ | Google AI Studio API key |
| `OPENROUTER_API_KEY` | ❌ | Free text model fallback |
| `ALLOWED_ORIGINS` | ✅ | CORS whitelist (your Vercel URL) |
| `MAX_FILE_SIZE_MB` | ❌ | Max upload size (default: 10) |
| `PORT` | ❌ | Server port (Render sets this) |

---

## 7. Running Tests

### Frontend Tests
```bash
cd excel-addin
npm test                 # Run all tests
npm test -- --watch      # Watch mode
npm test -- --coverage   # Coverage report
```

### Backend Tests
```bash
cd backend
pip install pytest pytest-asyncio httpx
pytest tests/ -v                        # All tests
pytest tests/ -v --cov=. --cov-report=html   # With coverage
```

---

## 8. Feature Reference

| Feature | Screen | SRS Ref |
|---------|--------|---------|
| Data Cleaning (trim, whitespace, numbers, dates, empty rows, currency) | Clean | FR-A1.1–A1.6 |
| Validation (duplicates, missing, type mismatch, outliers) | Validate | FR-A2.1–A2.5 |
| Summary Report (totals, counts, top-N per column) | Home → Summary Report | FR-A3.1–A3.3 |
| Create Standard Tables (Invoices, Items, Log) | Home → Create Tables | FR-A4.1–A4.2 |
| Invoice PDF Import (drag-drop, AI extraction, review, fill) | Invoice | FR-B1–B7 |
| Duplicate Protection (vendor + invoice# check) | Invoice | FR-B6.1–B6.2 |
| Audit Log (automatic import logging) | History / Import_Log sheet | FR-B7.1 |
| AI Formula Builder (natural language → formula) | AI | FR-C1.1–C1.4 |
| Model Switching (Gemini / OpenRouter / Auto) | Header dropdown | FR-C2.1–C2.3 |

---

## 9. Troubleshooting

| Problem | Solution |
|---------|----------|
| Add-in doesn't appear after deploy | Wait 24h, restart Excel, validate manifest |
| Blank taskpane panel | Check Vercel URL is accessible, verify HTTPS |
| "Backend offline" status | Check Render URL, may need cold-start wake-up |
| "Warming up..." message | Render free-tier cold start — wait 30s |
| Invoice extraction fails | Verify GEMINI_API_KEY is set in Render env vars |
| CORS errors in browser console | Update ALLOWED_ORIGINS in Render to match Vercel URL |
| File too large error | Increase MAX_FILE_SIZE_MB in Render env vars |
| Formulas not inserting | Ensure cell is selected before clicking "Insert Formula" |

### Validate Manifest
```bash
cd excel-addin
npx office-addin-manifest validate manifest.xml
```

---

## 10. Security Checklist

- [x] NFR-S1: No API keys in frontend code
- [x] NFR-S2: All communication via HTTPS
- [x] NFR-S3: CORS restricted to Vercel domain
- [x] NFR-S4: Rate limiting on API endpoints (30/min invoice, 60/min text)
- [x] NFR-S5: No invoice images stored in logs
- [ ] Optional: Add Azure AD authentication to backend
- [ ] Optional: Restrict Render to VPN/corporate network

---

## 11. Project Structure

```
mtea/
├── excel-addin/                    # Frontend (Vercel)
│   ├── package.json
│   ├── webpack.config.js
│   ├── vercel.json
│   ├── jest.config.js
│   ├── manifest.xml                # Office Add-in manifest
│   ├── src/
│   │   ├── taskpane/
│   │   │   ├── taskpane.html       # UI with 7 screens
│   │   │   ├── taskpane.css        # Dark theme styles
│   │   │   └── taskpane.js         # All feature logic
│   │   └── commands/
│   │       └── commands.js         # Ribbon button handlers
│   ├── test/
│   │   ├── setup.js                # Office.js mocks
│   │   └── taskpane.test.js        # 30+ test cases
│   └── assets/                     # Icons (create 16/32/64/80/128px PNGs)
├── backend/                        # Backend (Render)
│   ├── main.py                     # FastAPI server
│   ├── requirements.txt
│   ├── render.yaml                 # Render blueprint
│   ├── .env.example
│   ├── models/
│   │   ├── router.py               # AI model routing
│   │   ├── gemini_handler.py       # Gemini Vision + text
│   │   └── openrouter_handler.py   # Free text fallback
│   ├── ocr/
│   │   └── pdf_converter.py        # PDF → images (PyMuPDF)
│   └── tests/
│       └── test_backend.py         # 30+ test cases
├── docs/
│   └── DEPLOYMENT.md               # This file
└── .gitignore
```
