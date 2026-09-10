# Quick Start Guide

## Phase 1: Project Initialization & Dashboard (Current)

This guide will help you quickly get the retail analytics application running.

### Prerequisites
- Python 3.8+
- Node.js 16+ and npm
- MongoDB Atlas account

### Step 1: Prepare MongoDB

1. Visit [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create/login to your account
3. Create a free cluster
4. Create a database user (e.g., username: `analytics`, password: strong password)
5. Copy your connection string from the "Connect" button

### Step 2: Prepare Your Data

1. Copy your CSV files to the `/data` folder:
   ```
   data/
   ├── sales_cleaned.csv
   ├── product_summary.csv
   ├── customer_summary.csv
   ├── daily_sales.csv
   ├── monthly_sales.csv
   └── product_daily_sales.csv
   ```

### Step 3: Backend Setup (5 minutes)

```bash
# Navigate to backend
cd backend

# Create and activate virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate
# Or (macOS/Linux)
# source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
# On Windows:
copy .env.example .env
# On macOS/Linux:
# cp .env.example .env

# Edit .env with your MongoDB connection string:
# MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
# DB_NAME=retail_analytics
```

### Step 4: Import Data

```bash
# From the project root
cd scripts
python import_data.py
```

Wait for all 6 datasets to import successfully. You should see:
```
============================================================
Import completed: 6/6 files imported successfully
============================================================
```

### Step 5: Start Backend Server

```bash
cd backend
python app.py
```

You should see:
```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

### Step 6: Frontend Setup (in a new terminal)

```bash
cd frontend
npm install
npm run dev
```

You should see:
```
VITE v4.4.5 ready in 123 ms
➜  Local:   http://localhost:5173/
```

### Step 7: Access the Dashboard

Open browser: **http://localhost:5173**

You should see:
- 🎯 **6 KPI Cards** with key metrics
- 📈 **Monthly Revenue Chart** (line chart)
- 📊 **Monthly Quantity Chart** (bar chart)
- 🏆 **Top 10 Products** by revenue
- 🌍 **Top 15 Countries** by revenue

---

## What's Implemented in Phase 1

### ✅ Backend
- MongoDB connection with singleton pattern
- Flask REST API with CORS support
- Dashboard KPI endpoints
- Data aggregation pipelines
- Proper error handling
- Environment-based configuration

### ✅ Frontend
- Clean, modern UI with dark sidebar
- Responsive design (works on mobile/tablet)
- Recharts-based data visualization
- Loading and error states
- KPI cards with color-coded icons
- Component-based architecture

### ✅ Database
- MongoDB collections created with indexes
- 7 collections ready for data
- Optimized aggregation queries
- No hardcoded credentials

### ✅ Development Tools
- Vite for fast React development
- Hot reload for both frontend and backend
- Python virtual environment setup

---

## Testing the Application

### 1. Verify Backend is Running
```bash
curl http://localhost:5000/health
```

Expected response:
```json
{
  "status": "healthy",
  "timestamp": "2024-01-15T10:30:45.123456",
  "database": "connected"
}
```

### 2. Check KPI Data
```bash
curl http://localhost:5000/api/dashboard/kpis
```

### 3. Verify Dashboard Loads
- Open http://localhost:5173
- Should show 6 KPI cards with actual numbers
- Charts should display data

---

## Common Issues & Solutions

### Issue: "Cannot connect to MongoDB"
**Solution:**
1. Check connection string in `.env`
2. Verify IP is whitelisted in MongoDB Atlas (Network Access)
3. Test connection string in MongoDB Atlas shell

### Issue: "Module not found" error in backend
**Solution:**
```bash
pip install -r requirements.txt
```

### Issue: "npm ERR!" in frontend
**Solution:**
```bash
cd frontend
rm -rf node_modules package-lock.json
npm install
```

### Issue: "Port 5000 is already in use"
**Solution:**
```bash
# Find process
netstat -ano | findstr :5000
# Kill process (Windows)
taskkill /PID <PID> /F
```

### Issue: Dashboard shows "Error: Failed to fetch KPIs"
**Solution:**
1. Check backend is running on http://localhost:5000
2. Check browser console for CORS errors
3. Verify MongoDB connection in backend logs

---

## Next Phase (Phase 2)

Once Phase 1 is tested and working:
1. Confirm all dashboards display correctly
2. Verify data accuracy
3. Test with your actual data volume
4. Notify when ready for Phase 2

Phase 2 will add:
- 📊 Univariate Analysis
- 📈 Bivariate Analysis
- 🎯 Predictive Modeling (Multiple Regression, Random Forest)
- 🔮 Time Series Forecasting (ARIMA, SARIMA, Holt-Winters)
- 📦 ABC & XYZ Analysis
- 📋 EOQ Calculations

---

## File Structure

```
predictive analysis/
├── backend/
│   ├── app.py (Flask app)
│   ├── config.py (Configuration)
│   ├── db.py (MongoDB connection)
│   ├── requirements.txt (Dependencies)
│   ├── .env.example (Template)
│   └── __init__.py
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx
│   │   ├── components/ (Sidebar, KPICard, ChartContainer)
│   │   └── pages/ (Dashboard)
│   ├── package.json
│   ├── vite.config.js
│   ├── index.html
│   └── .env.example
│
├── scripts/
│   └── import_data.py (Data importer)
│
├── data/ (Place CSV files here)
│   └── README.md
│
├── README.md (Full documentation)
└── QUICKSTART.md (This file)
```

---

## Stopping the Application

### To stop the backend server:
- Press `Ctrl+C` in the terminal running `python app.py`

### To stop the frontend server:
- Press `Ctrl+C` in the terminal running `npm run dev`

### To stop MongoDB connection:
- Connections close automatically when servers stop

---

## Support

If you encounter any issues:
1. Check the README.md for detailed documentation
2. Review the troubleshooting section
3. Check backend console for Python errors
4. Check browser console (F12) for JavaScript errors
5. Verify MongoDB Atlas network access settings

---

Ready to test? Start with Step 1 and follow through Step 7!
