# Retail Analytics & Demand Intelligence Dashboard

A full-stack web application for retail analytics and demand forecasting with interactive visualizations and machine learning models.

## Tech Stack

### Frontend
- **React 18** with Vite (fast development experience)
- **Recharts** for data visualization
- **Lucide React** for icons
- **CSS3** with responsive design
- **Axios** for API calls

### Backend
- **Flask** (Python web framework)
- **Flask-CORS** for cross-origin requests
- **PyMongo** for MongoDB integration
- **Pandas & NumPy** for data processing

### Database
- **MongoDB Atlas** for cloud database
- Collections: transactions, products, customers, daily_sales, monthly_sales, product_daily_sales, forecasts

## Project Structure

```
retail-analytics/
├── backend/
│   ├── app.py                 # Flask application entry point
│   ├── config.py              # Configuration settings
│   ├── db.py                  # MongoDB connection
│   ├── requirements.txt        # Python dependencies
│   ├── .env.example            # Environment variables template
│   └── __init__.py
│
├── frontend/
│   ├── src/
│   │   ├── App.jsx            # Main React component
│   │   ├── App.css
│   │   ├── main.jsx           # React entry point
│   │   ├── index.css
│   │   ├── components/
│   │   │   ├── Sidebar.jsx    # Navigation sidebar
│   │   │   ├── Sidebar.css
│   │   │   ├── KPICard.jsx    # KPI metric cards
│   │   │   ├── KPICard.css
│   │   │   ├── ChartContainer.jsx
│   │   │   └── ChartContainer.css
│   │   └── pages/
│   │       ├── Dashboard.jsx  # Dashboard home page
│   │       └── Dashboard.css
│   ├── index.html
│   ├── package.json
│   ├── vite.config.js
│   └── .env.example
│
├── scripts/
│   └── import_data.py         # CSV data importer script
│
├── data/                       # Place your CSV files here
│   ├── sales_cleaned.csv
│   ├── product_summary.csv
│   ├── customer_summary.csv
│   ├── daily_sales.csv
│   ├── monthly_sales.csv
│   └── product_daily_sales.csv
│
└── README.md
```

## Prerequisites

- **Python 3.8+** installed
- **Node.js 16+** and npm installed
- **MongoDB Atlas** account (free tier available at https://www.mongodb.com/cloud/atlas)
- Git (optional, for cloning)

## Setup Instructions

### 1. MongoDB Setup

1. Go to [MongoDB Atlas](https://www.mongodb.com/cloud/atlas)
2. Create a free account
3. Create a new project
4. Create a cluster (free tier available)
5. Create a database user with username and password
6. Get your connection string (it looks like: `mongodb+srv://user:password@cluster.xxxxx.mongodb.net/?retryWrites=true&w=majority`)

### 2. Backend Setup

```bash
# Navigate to backend directory
cd backend

# Create virtual environment
python -m venv venv

# Activate virtual environment
# On Windows:
venv\Scripts\activate
# On macOS/Linux:
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Create .env file (copy from .env.example and fill in your credentials)
cp .env.example .env

# Edit .env with your MongoDB connection string and database name
```

**Backend .env file:**
```
MONGODB_URI=mongodb+srv://username:password@cluster0.xxxxx.mongodb.net/?retryWrites=true&w=majority
DB_NAME=retail_analytics
FLASK_ENV=development
FLASK_DEBUG=True
VITE_API_URL=http://localhost:5173
```

### 3. Frontend Setup

```bash
# Navigate to frontend directory
cd frontend

# Install dependencies
npm install

# Create .env file
cp .env.example .env

# .env already configured correctly for local development
# VITE_API_BASE_URL=http://localhost:5000
# VITE_API_URL=http://localhost:5173
```

### 4. Data Import

Before running the app, you need to prepare your data:

1. **Place CSV files in the `/data` folder:**
   - sales_cleaned.csv
   - product_summary.csv
   - customer_summary.csv
   - daily_sales.csv
   - monthly_sales.csv
   - product_daily_sales.csv

2. **Run the data importer:**
   ```bash
   cd scripts
   python import_data.py
   ```

   This will:
   - Read all CSV files
   - Transform data to match MongoDB schema
   - Create proper indexes for performance
   - Populate the retail_analytics database

   Expected output:
   ```
   ============================================================
   Starting data import...
   ============================================================
   Importing transactions from sales_cleaned.csv...
   ✓ Imported 500000 transaction records
   Importing products from product_summary.csv...
   ✓ Imported 4000 product records
   ...
   ============================================================
   Import completed: 6/6 files imported successfully
   ============================================================
   ```

## Running the Application

### Terminal 1: Start Backend Server

```bash
cd backend
python app.py
```

Expected output:
```
 * Running on http://0.0.0.0:5000
 * Debug mode: on
```

### Terminal 2: Start Frontend Development Server

```bash
cd frontend
npm run dev
```

Expected output:
```
VITE v4.4.5 ready in 123 ms

➜  Local:   http://localhost:5173/
```

### Access the Application

Open your browser and navigate to: **http://localhost:5173**

You should see:
- Dark sidebar with navigation menu
- Dashboard home with 6 KPI cards
- Monthly revenue trend chart
- Monthly quantity bar chart
- Top 10 products by revenue
- Top 15 countries by revenue

## API Endpoints (Phase 1)

### Health Check
- `GET /health` - Server health status

### Dashboard KPIs
- `GET /api/dashboard/kpis` - KPI metrics (products, customers, transactions, revenue, units, countries)
- `GET /api/dashboard/monthly-revenue` - Monthly revenue and quantity trends
- `GET /api/dashboard/top-products?limit=10` - Top products by revenue
- `GET /api/dashboard/top-countries?limit=15` - Top countries by revenue
- `GET /api/data/summary` - Collection record counts

## Key Features (Phase 1)

✅ **Dashboard Home**
- 6 KPI cards with key metrics
- Monthly revenue trend line chart
- Monthly quantity bar chart
- Top 10 products by revenue
- Top 15 countries by revenue
- Responsive design
- Loading and error states

✅ **Database**
- MongoDB Atlas integration
- 7 collections with indexes
- Efficient aggregation pipelines
- No fake data - all real data from CSV files

✅ **Data Import**
- Automated CSV to MongoDB import
- Data validation and transformation
- Schema mapping
- Performance indexes

✅ **Clean Code**
- Modular React components
- Proper error handling
- Environment variables for configuration
- CORS enabled for development

## Phase 2 Features (Coming Next)

After Phase 1 is tested, we'll implement:

📊 **Analytics Modules**
- Univariate Analysis (mean, median, std, histograms, box plots)
- Bivariate Analysis (correlation, scatter plots)
- ABC and XYZ Analysis

🎯 **Predictive Models**
- Multivariate Regression (Linear Regression, Random Forest)
- Time Series Forecasting (ARIMA, SARIMA, Holt-Winters)
- EOQ (Economic Order Quantity) calculation
- RMLC Product Lifecycle Analysis

## Troubleshooting

### MongoDB Connection Error
```
Error: Failed to connect to MongoDB
```
**Solution:**
1. Check your connection string in `.env`
2. Verify MongoDB Atlas IP whitelist includes your IP
3. Verify username/password are correct
4. Test connection at MongoDB Atlas Dashboard

### CORS Error
```
Access to XMLHttpRequest at 'http://localhost:5000...' blocked by CORS policy
```
**Solution:**
1. Ensure backend is running on port 5000
2. Check VITE_API_URL in frontend .env matches backend origin

### No Data Displaying
```
Dashboard loads but no KPI values shown
```
**Solution:**
1. Run the data importer: `python scripts/import_data.py`
2. Check that all CSV files are in `/data` folder
3. Verify MongoDB collections have documents: 
   ```bash
   # In MongoDB shell
   use retail_analytics
   db.transactions.countDocuments()
   ```

### Port Already in Use
```
Address already in use: ('0.0.0.0', 5000)
```
**Solution:**
1. Change port in backend/app.py: `app.run(port=5001)`
2. Or kill process using port: 
   ```bash
   # Windows
   netstat -ano | findstr :5000
   taskkill /PID <PID> /F
   
   # macOS/Linux
   lsof -i :5000
   kill -9 <PID>
   ```

## Development Tips

### Hot Reload
- Frontend: Vite provides instant hot reload when you save files
- Backend: Flask debug mode auto-reloads when you change Python files

### Testing API Endpoints
Use cURL or Postman:
```bash
curl http://localhost:5000/api/dashboard/kpis
curl http://localhost:5000/api/dashboard/monthly-revenue
curl http://localhost:5000/api/dashboard/top-products?limit=10
```

### Database Queries
Debug in Python:
```python
from backend.db import get_db
db = get_db()
print(db['transactions'].count_documents({}))
print(db['transactions'].find_one())
```

## Performance Optimization

- **Pagination**: API responses are already optimized with aggregation pipelines
- **Indexes**: MongoDB indexes created on Date, ProductID, CustomerID fields
- **Frontend**: Recharts efficiently handles large datasets
- **Caching**: Add Redis for production deployments

## Security Checklist (Before Production)

- [ ] Remove FLASK_DEBUG=True in production
- [ ] Use secure MongoDB password (at least 12 chars)
- [ ] Enable MongoDB IP whitelist with specific IPs
- [ ] Use HTTPS/SSL for all connections
- [ ] Set CORS origin to your domain only
- [ ] Move secrets to secure vault (AWS Secrets Manager, Azure Key Vault)
- [ ] Add authentication/authorization to APIs

## Next Steps

1. Test Phase 1 components thoroughly
2. Verify all dashboard charts load with your data
3. Test with different data volumes
4. Once confirmed working, notify to proceed with Phase 2
5. Phase 2 will add analytics and ML modules

## Support & Resources

- [React Documentation](https://react.dev)
- [Vite Documentation](https://vitejs.dev)
- [Recharts Documentation](https://recharts.org)
- [Flask Documentation](https://flask.palletsprojects.com)
- [MongoDB Documentation](https://docs.mongodb.com)
- [PyMongo Documentation](https://pymongo.readthedocs.io)

## License

Private Project - All Rights Reserved

---

**Questions or issues?** Test the application and let me know what needs adjustment before proceeding to Phase 2.
