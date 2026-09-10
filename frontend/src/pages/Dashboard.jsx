import { useEffect, useState } from "react";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

import {
  getKPIs,
  getMonthlyRevenue,
  getTopProducts,
  getTopCountries,
} from "../services/api";

import "./Dashboard.css";


function Dashboard() {

  const [kpis, setKpis] = useState(null);

  const [monthly, setMonthly] = useState([]);

  const [products, setProducts] = useState([]);

  const [countries, setCountries] = useState([]);

  const [loading, setLoading] = useState(true);

  const [error, setError] = useState("");


  // ==========================================
  // LOAD DASHBOARD DATA
  // ==========================================

  useEffect(() => {

    loadDashboard();

  }, []);


  const loadDashboard = async () => {

    try {

      setLoading(true);

      setError("");


      const [
        kpiResponse,
        monthlyResponse,
        productResponse,
        countryResponse,
      ] = await Promise.all([

        getKPIs(),

        getMonthlyRevenue(),

        getTopProducts(10),

        getTopCountries(15),

      ]);


      // ======================================
      // DEBUG API RESPONSES
      // ======================================

      console.log(
        "KPI API:",
        kpiResponse.data
      );

      console.log(
        "MONTHLY API:",
        monthlyResponse.data
      );

      console.log(
        "PRODUCT API:",
        productResponse.data
      );

      console.log(
        "COUNTRY API:",
        countryResponse.data
      );


      // ======================================
      // KPI
      // ======================================

      setKpis(
        kpiResponse.data
      );


      // ======================================
      // EXTRACT ARRAYS
      // ======================================

      const monthlyRaw =
        extractArray(
          monthlyResponse.data,
          [
            "data",
            "monthly_revenue",
            "monthlyRevenue",
            "monthly_sales",
            "monthlySales",
            "results",
          ]
        );


      const productsRaw =
        extractArray(
          productResponse.data,
          [
            "data",
            "products",
            "top_products",
            "topProducts",
            "results",
          ]
        );


      const countriesRaw =
        extractArray(
          countryResponse.data,
          [
            "data",
            "countries",
            "top_countries",
            "topCountries",
            "results",
          ]
        );


      // ======================================
      // NORMALIZE DATA
      // ======================================

      const monthlyData =
        normalizeMonthlyData(
          monthlyRaw
        );


      const productData =
        normalizeProductData(
          productsRaw
        );


      const countryData =
        normalizeCountryData(
          countriesRaw
        );


      // ======================================
      // FINAL DEBUG
      // ======================================

      console.log(
        "FINAL MONTHLY DATA:",
        monthlyData
      );

      console.log(
        "FINAL PRODUCT DATA:",
        productData
      );

      console.log(
        "FINAL COUNTRY DATA:",
        countryData
      );


      console.log(
        "MONTHLY FIRST ROW:",
        monthlyData[0]
      );

      console.log(
        "PRODUCT FIRST ROW:",
        productData[0]
      );

      console.log(
        "COUNTRY FIRST ROW:",
        countryData[0]
      );


      // ======================================
      // SET STATE
      // ======================================

      setMonthly(monthlyData);

      setProducts(productData);

      setCountries(countryData);


    } catch (err) {

      console.error(
        "Dashboard Error:",
        err
      );

      console.error(
        "Response:",
        err.response?.data
      );


      setError(

        err.response?.data?.error ||

        err.message ||

        "Unable to load dashboard data."

      );

    } finally {

      setLoading(false);

    }

  };


  // ==========================================
  // LOADING
  // ==========================================

  if (loading) {

    return (

      <div className="page-loading">

        <div className="dashboard-loader"></div>

        <p>
          Loading dashboard...
        </p>

      </div>

    );

  }


  // ==========================================
  // ERROR
  // ==========================================

  if (error) {

    return (

      <div className="page-error">

        <h3>
          Dashboard Error
        </h3>

        <p>
          {error}
        </p>

        <button
          onClick={loadDashboard}
        >
          Retry
        </button>

      </div>

    );

  }


  // ==========================================
  // KPI HELPER
  // ==========================================

  const getKPI = (key) => {

    if (!kpis) {
      return 0;
    }

    return (

      kpis[key] ??

      kpis.data?.[key] ??

      0

    );

  };


  // ==========================================
  // FORMAT NUMBER
  // ==========================================

  const formatNumber = (value) => {

    const number = Number(value);

    if (Number.isNaN(number)) {
      return "0";
    }

    return number.toLocaleString(
      "en-IN",
      {
        maximumFractionDigits: 2,
      }
    );

  };


  return (

    <div className="dashboard">


      {/* =====================================
          HEADER
      ===================================== */}

      <div className="page-header">

        <div>

          <h1>
            Retail Analytics
          </h1>

          <p>
            Retail performance and demand
            intelligence
          </p>

        </div>


        <button
          className="dashboard-refresh"
          onClick={loadDashboard}
        >
          Refresh Data
        </button>

      </div>


      {/* =====================================
          KPI CARDS
      ===================================== */}

      <div className="kpi-grid">


        {/* PRODUCTS */}

        <div className="kpi-card">

          <div className="kpi-label">
            Total Products
          </div>

          <div className="kpi-value">

            {formatNumber(
              getKPI("total_products")
            )}

          </div>

        </div>


        {/* CUSTOMERS */}

        <div className="kpi-card">

          <div className="kpi-label">
            Total Customers
          </div>

          <div className="kpi-value">

            {formatNumber(
              getKPI("total_customers")
            )}

          </div>

        </div>


        {/* TRANSACTIONS */}

        <div className="kpi-card">

          <div className="kpi-label">
            Total Transactions
          </div>

          <div className="kpi-value">

            {formatNumber(
              getKPI("total_transactions")
            )}

          </div>

        </div>


        {/* REVENUE */}

        <div className="kpi-card">

          <div className="kpi-label">
            Total Revenue
          </div>

          <div className="kpi-value">

            ₹
            {formatNumber(
              getKPI("total_revenue")
            )}

          </div>

        </div>


        {/* QUANTITY */}

        <div className="kpi-card">

          <div className="kpi-label">
            Total Units
          </div>

          <div className="kpi-value">

            {formatNumber(
              getKPI("total_quantity")
            )}

          </div>

        </div>


        {/* COUNTRIES */}

        <div className="kpi-card">

          <div className="kpi-label">
            Countries
          </div>

          <div className="kpi-value">

            {formatNumber(
              getKPI("total_countries")
            )}

          </div>

        </div>


      </div>


      {/* =====================================
          MONTHLY REVENUE
      ===================================== */}

      <div className="chart-card">


        <div className="chart-header">

          <div>

            <h2>
              Monthly Revenue Trend
            </h2>

            <p>
              Revenue performance over time
            </p>

          </div>

        </div>


        {monthly.length === 0 ? (

          <div className="empty-chart">

            <p>
              No monthly revenue data available.
            </p>

          </div>

        ) : (

          <div className="chart">

            <ResponsiveContainer
              width="100%"
              height={350}
            >

              <LineChart
                data={monthly}
                margin={{
                  top: 20,
                  right: 30,
                  left: 20,
                  bottom: 20,
                }}
              >

                <CartesianGrid
                  strokeDasharray="3 3"
                />


                <XAxis
                  dataKey="Date"
                  tick={{
                    fontSize: 12,
                  }}
                />


                <YAxis
                  tick={{
                    fontSize: 12,
                  }}
                  tickFormatter={(value) =>
                    formatCompact(value)
                  }
                />


                <Tooltip
                  formatter={(value) => [
                    `₹${formatNumber(value)}`,
                    "Revenue",
                  ]}
                  labelFormatter={(label) =>
                    `Month: ${label}`
                  }
                />


                <Legend />


                <Line
                  type="monotone"
                  dataKey="Revenue"
                  name="Revenue"
                  stroke="#2563eb"
                  strokeWidth={3}
                  dot={{
                    r: 4,
                  }}
                  activeDot={{
                    r: 7,
                  }}
                  connectNulls
                />

              </LineChart>

            </ResponsiveContainer>

          </div>

        )}

      </div>


      {/* =====================================
          TOP PRODUCTS + TOP COUNTRIES
      ===================================== */}

      <div className="chart-grid">


        {/* ===================================
            TOP PRODUCTS
        =================================== */}

        <div className="chart-card">

          <div className="chart-header">

            <div>

              <h2>
                Top Products
              </h2>

              <p>
                Highest revenue generating products
              </p>

            </div>

          </div>


          {products.length === 0 ? (

            <div className="empty-chart">

              <p>
                No product data available.
              </p>

            </div>

          ) : (

            <ResponsiveContainer
              width="100%"
              height={400}
            >

              <BarChart
                data={products}
                layout="vertical"
                margin={{
                  top: 10,
                  right: 30,
                  left: 20,
                  bottom: 10,
                }}
              >

                <CartesianGrid
                  strokeDasharray="3 3"
                />


                <XAxis
                  type="number"
                  tickFormatter={(value) =>
                    formatCompact(value)
                  }
                />


                <YAxis
                  type="category"
                  dataKey="StockCode"
                  width={90}
                  tick={{
                    fontSize: 11,
                  }}
                />


                <Tooltip
                  formatter={(value) => [
                    `₹${formatNumber(value)}`,
                    "Revenue",
                  ]}
                />


                <Bar
                  dataKey="Total_Revenue"
                  name="Revenue"
                  fill="#2563eb"
                  radius={[
                    0,
                    5,
                    5,
                    0,
                  ]}
                />

              </BarChart>

            </ResponsiveContainer>

          )}

        </div>


        {/* ===================================
            TOP COUNTRIES
        =================================== */}

        <div className="chart-card">

          <div className="chart-header">

            <div>

              <h2>
                Top Countries
              </h2>

              <p>
                Revenue contribution by country
              </p>

            </div>

          </div>


          {countries.length === 0 ? (

            <div className="empty-chart">

              <p>
                No country data available.
              </p>

            </div>

          ) : (

            <ResponsiveContainer
              width="100%"
              height={400}
            >

              <BarChart
                data={countries}
                margin={{
                  top: 20,
                  right: 30,
                  left: 10,
                  bottom: 80,
                }}
              >

                <CartesianGrid
                  strokeDasharray="3 3"
                />


                <XAxis
                  dataKey="Country"
                  angle={-35}
                  textAnchor="end"
                  height={90}
                  interval={0}
                  tick={{
                    fontSize: 11,
                  }}
                />


                <YAxis
                  tickFormatter={(value) =>
                    formatCompact(value)
                  }
                />


                <Tooltip
                  formatter={(value) => [
                    `₹${formatNumber(value)}`,
                    "Revenue",
                  ]}
                />


                <Bar
                  dataKey="Total_Revenue"
                  name="Revenue"
                  fill="#16a34a"
                  radius={[
                    5,
                    5,
                    0,
                    0,
                  ]}
                />

              </BarChart>

            </ResponsiveContainer>

          )}

        </div>


      </div>


      {/* =====================================
          DATA STATUS
      ===================================== */}

      <div className="dashboard-status">

        <span>
          ✓ Connected to Retail Analytics API
        </span>

        <span>
          {monthly.length} months
        </span>

        <span>
          {products.length} products shown
        </span>

        <span>
          {countries.length} countries shown
        </span>

      </div>


    </div>

  );

}


/* ==================================================
   EXTRACT ARRAY
================================================== */

function extractArray(
  response,
  possibleKeys
) {

  // ------------------------------------------
  // API directly returns array
  // ------------------------------------------

  if (
    Array.isArray(response)
  ) {

    return response;

  }


  // ------------------------------------------
  // API returns object
  // ------------------------------------------

  if (
    response &&
    typeof response === "object"
  ) {

    for (
      const key of possibleKeys
    ) {

      if (
        Array.isArray(
          response[key]
        )
      ) {

        return response[key];

      }

    }

  }


  return [];

}


/* ==================================================
   NORMALIZE MONTHLY DATA
================================================== */

function normalizeMonthlyData(
  data
) {

  if (!Array.isArray(data)) {
    return [];
  }


  return data
    .map((item) => {

      const rawDate =
        item.Date ??
        item.date ??
        item.Month ??
        item.month ??
        item._id ??
        "";


      const rawRevenue =
        item.Revenue ??
        item.revenue ??
        item.Total_Revenue ??
        item.total_revenue ??
        0;


      return {

        Date: formatDateLabel(
          rawDate
        ),

        Revenue: Number(
          rawRevenue
        ) || 0,

      };

    })
    .filter(
      (item) =>
        item.Date !== ""
    );

}


/* ==================================================
   NORMALIZE PRODUCT DATA
================================================== */

function normalizeProductData(
  data
) {

  if (!Array.isArray(data)) {
    return [];
  }


  return data
    .map((item) => {

      const product =
        item.StockCode ??
        item.stock_code ??
        item.ProductID ??
        item.product_id ??
        item._id ??
        item.Description ??
        item.description ??
        "Unknown";


      const revenue =
        item.Total_Revenue ??
        item.total_revenue ??
        item.Revenue ??
        item.revenue ??
        0;


      return {

        StockCode: String(
          product
        ),

        Total_Revenue:
          Number(revenue) || 0,

      };

    })
    .filter(
      (item) =>
        item.Total_Revenue !== 0
    );

}


/* ==================================================
   NORMALIZE COUNTRY DATA
================================================== */

function normalizeCountryData(
  data
) {

  if (!Array.isArray(data)) {
    return [];
  }


  return data
    .map((item) => {

      const country =
        item.Country ??
        item.country ??
        item._id ??
        "Unknown";


      const revenue =
        item.Total_Revenue ??
        item.total_revenue ??
        item.Revenue ??
        item.revenue ??
        0;


      return {

        Country: String(
          country
        ),

        Total_Revenue:
          Number(revenue) || 0,

      };

    })
    .filter(
      (item) =>
        item.Total_Revenue !== 0
    );

}


/* ==================================================
   DATE FORMAT
================================================== */

function formatDateLabel(
  value
) {

  if (
    value === null ||
    value === undefined ||
    value === ""
  ) {

    return "";

  }


  // If already looks like YYYY-MM
  if (
    /^\d{4}-\d{2}$/.test(
      String(value)
    )
  ) {

    return String(value);

  }


  const date =
    new Date(value);


  if (
    !Number.isNaN(
      date.getTime()
    )
  ) {

    return date.toLocaleDateString(
      "en-US",
      {
        month: "short",
        year: "numeric",
      }
    );

  }


  return String(value);

}


/* ==================================================
   COMPACT NUMBER
================================================== */

function formatCompact(
  value
) {

  const number =
    Number(value);


  if (
    Number.isNaN(number)
  ) {

    return "0";

  }


  if (
    Math.abs(number) >= 10000000
  ) {

    return (
      (number / 10000000)
        .toFixed(1)
      + "Cr"
    );

  }


  if (
    Math.abs(number) >= 1000000
  ) {

    return (
      (number / 1000000)
        .toFixed(1)
      + "M"
    );

  }


  if (
    Math.abs(number) >= 1000
  ) {

    return (
      (number / 1000)
        .toFixed(1)
      + "K"
    );

  }


  return String(
    Math.round(number)
  );

}


export default Dashboard;