import { useEffect, useState } from "react";

import {
  ResponsiveContainer,
  LineChart,
  Line,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
} from "recharts";

import {
  getARIMA,
  getSARIMA,
  getHoltWinters,
  getDateRange,
} from "../services/api";

import "./Predictive.css";


const METRICS = [
  "Revenue",
  "Quantity",
  "Transactions",
];

const HORIZONS = [7, 14, 30, 60];


function TimeSeries({ model = "arima" }) {

  const [metric, setMetric] = useState("Revenue");
  const [forecastDays, setForecastDays] = useState(30);
  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [dateRange, setDateRange] = useState(null);
  const [rangeError, setRangeError] = useState("");

  const [result, setResult] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


  // ==========================================
  // LOAD AVAILABLE DATE RANGE (once, on mount)
  // ==========================================

  useEffect(() => {
    loadDateRange();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const loadDateRange = async () => {

    try {

      const res = await getDateRange();

      const data = res.data;

      const min = data.min_date || data.minDate || "";
      const max = data.max_date || data.maxDate || "";

      setDateRange({ min, max });

      if (min && max) {
        setFromDate(min);
        setToDate(max);
      }

    } catch (e) {

      console.error("Date range error:", e);

      setRangeError(
        "Could not load available dates."
      );

    }

  };


  // ==========================================
  // VALIDATION
  // ==========================================

  const validateDates = () => {

    if (!fromDate) {
      return "From Date is required.";
    }

    if (!toDate) {
      return "To Date is required.";
    }

    if (fromDate > toDate) {
      return "From Date must not be after To Date.";
    }

    if (dateRange) {

      if (fromDate < dateRange.min) {
        return `From Date must not be before ${dateRange.min}.`;
      }

      if (toDate > dateRange.max) {
        return `To Date must not be after ${dateRange.max}.`;
      }

    }

    return "";

  };


  // ==========================================
  // GENERATE FORECAST
  // ==========================================

  const generateForecast = async () => {

    const validation = validateDates();

    if (validation) {
      setError("");
      setResult(null);
      return;
    }

    setError("");
    setRangeError("");
    setLoading(true);

    try {

      let response;

      if (model === "arima") {

        response = await getARIMA(
          metric,
          forecastDays,
          fromDate,
          toDate
        );

      } else if (model === "sarima") {

        response = await getSARIMA(
          metric,
          forecastDays,
          fromDate,
          toDate
        );

      } else if (model === "holt-winters") {

        response = await getHoltWinters(
          metric,
          forecastDays,
          fromDate,
          toDate
        );

      } else {

        throw new Error(
          "Unknown forecasting model."
        );

      }

      setResult(response.data);

    } catch (err) {

      console.error(err);

      setResult(null);

      setError(
        err.response?.data?.error ||
        err.message ||
        "Failed to generate forecast."
      );

    } finally {

      setLoading(false);

    }

  };


  const getModelName = () => {

    switch (model) {

      case "arima":
        return "ARIMA";

      case "sarima":
        return "SARIMA";

      case "holt-winters":
        return "Holt-Winters";

      default:
        return "Time Series";

    }

  };


  // ==========================================
  // NORMALIZE DATA
  // ==========================================

  const forecastData =
    result?.forecast ||
    result?.predictions ||
    result?.data?.forecast ||
    result?.data?.predictions ||
    [];

  const historicalData =
    result?.history ||
    result?.historical ||
    result?.data?.historical ||
    [];

  const history = Array.isArray(historicalData)
    ? historicalData.map((item, index) => {

        if (typeof item === "number") {
          return { index, actual: item };
        }

        return {
          date:
            item.date ||
            item.Date ||
            item.ds ||
            "",
          actual: Number(
            item.value ??
              item.Revenue ??
              item.Quantity ??
              item.actual ??
              item.y ??
              0
          ),
        };

      })
    : [];

  const forecast = Array.isArray(forecastData)
    ? forecastData.map((item, index) => {

        if (typeof item === "number") {
          return { index, forecast: item };
        }

        return {
          date:
            item.date ||
            item.Date ||
            item.ds ||
            "",
          forecast: Number(
            item.value ??
              item.forecast ??
              item.prediction ??
              item.yhat ??
              0
          ),
        };

      })
    : [];

  const chartData = [];

  history.forEach((item, index) => {
    chartData.push({
      date: item.date || `Historical ${index + 1}`,
      actual: item.actual,
      forecast: null,
    });
  });

  forecast.forEach((item, index) => {
    chartData.push({
      date: item.date || `Forecast ${index + 1}`,
      actual: null,
      forecast: item.forecast,
    });
  });

  const metrics = result?.metrics || result?.evaluation || {};

  const modelDetails = result?.model_details || {};

  const lastDate = result?.last_date || "";

  const historicalRange =
    history.length > 0
      ? `${history[0].date || "—"} → ${
          history[history.length - 1].date || "—"
        }`
      : "—";


  // ==========================================
  // RENDER
  // ==========================================

  return (

    <div className="predictive-page">

      <div className="page-header">
        <div>
          <h1>{getModelName()} Forecasting</h1>
          <p>
            Time series demand forecasting
            using {getModelName()}.
          </p>
        </div>
      </div>

      {/* CONTROL CARD */}

      <div className="analysis-card forecast-setup">

        <div className="card-header">
          <div>
            <h2>Forecast Configuration</h2>
            <p>
              Configure the metric and date range,
              then generate a forecast.
            </p>
          </div>
        </div>

        <div className="forecast-form">

          <div className="field-group">
            <label>Metric</label>
            <select
              value={metric}
              onChange={(e) =>
                setMetric(e.target.value)
              }
            >
              {METRICS.map((m) => (
                <option key={m} value={m}>
                  {m}
                </option>
              ))}
            </select>
          </div>

          <div className="field-group">
            <label>From Date</label>
            <input
              type="date"
              value={fromDate}
              min={dateRange?.min || ""}
              max={dateRange?.max || ""}
              onChange={(e) =>
                setFromDate(e.target.value)
              }
            />
          </div>

          <div className="field-group">
            <label>To Date</label>
            <input
              type="date"
              value={toDate}
              min={dateRange?.min || ""}
              max={dateRange?.max || ""}
              onChange={(e) =>
                setToDate(e.target.value)
              }
            />
          </div>

          <div className="field-group">
            <label>Forecast Horizon</label>
            <select
              value={forecastDays}
              onChange={(e) =>
                setForecastDays(
                  Number(e.target.value)
                )
              }
            >
              {HORIZONS.map((d) => (
                <option key={d} value={d}>
                  {d} Days
                </option>
              ))}
            </select>
          </div>

        </div>

        {rangeError && (
          <div className="validation-message">
            {rangeError}
          </div>
        )}

        <div className="date-range-hint">
          {dateRange
            ? `Available data: ${dateRange.min} to ${dateRange.max}`
            : "Loading available date range..."}
        </div>

        <div className="selection-actions">
          <button
            className="forecast-button"
            onClick={generateForecast}
            disabled={loading}
          >
            {loading
              ? "Generating..."
              : "Generate Forecast"}
          </button>
        </div>

      </div>


      {loading && (
        <div className="loading-box">
          <div className="loader"></div>
          <h3>Generating forecast...</h3>
          <p>
            Please wait while the {getModelName()}
            model is trained.
          </p>
        </div>
      )}


      {!loading && error && (
        <div className="error-box">
          <h3>Forecast Error</h3>
          <p>{error}</p>
        </div>
      )}


      {!loading && !error && !result && (
        <div className="empty-state">
          Configure the settings above and click
          "Generate Forecast" to view the results.
        </div>
      )}


      {!loading && !error && result && (
        <>

          {/* FORECAST SUMMARY */}

          <div className="predictive-stats">

            <div className="predictive-stat">
              <span>Model</span>
              <strong>{getModelName()}</strong>
            </div>

            <div className="predictive-stat">
              <span>Metric</span>
              <strong>{metric}</strong>
            </div>

            <div className="predictive-stat">
              <span>Historical Range</span>
              <strong>{historicalRange}</strong>
            </div>

            <div className="predictive-stat">
              <span>Forecast Horizon</span>
              <strong>{forecastDays} Days</strong>
            </div>

            <div className="predictive-stat">
              <span>Forecast Points</span>
              <strong>{forecast.length}</strong>
            </div>

          </div>


          {/* FORECAST CHART */}

          {chartData.length > 0 && (
            <div className="analysis-card">

              <div className="card-header">
                <div>
                  <h2>{metric} Forecast</h2>
                  <p>
                    Historical observations and
                    future predictions.
                  </p>
                </div>
              </div>

              <ResponsiveContainer
                width="100%"
                height={420}
              >
                <LineChart data={chartData}>
                  <CartesianGrid
                    strokeDasharray="3 3"
                  />
                  <XAxis dataKey="date" />
                  <YAxis />
                  <Tooltip />
                  <Legend />
                  <Line
                    type="monotone"
                    dataKey="actual"
                    name="Historical"
                    strokeWidth={2}
                    dot={false}
                    stroke="#6b7280"
                    connectNulls={false}
                  />
                  <Line
                    type="monotone"
                    dataKey="forecast"
                    name="Forecast"
                    strokeWidth={3}
                    dot={false}
                    stroke="#2563eb"
                    connectNulls={false}
                  />
                </LineChart>
              </ResponsiveContainer>

            </div>
          )}


          {/* MODEL INFO + EVALUATION */}

          <div className="two-column">

            <div className="analysis-card">
              <h2>Model Information</h2>
              <div className="model-info">

                <InfoRow
                  label="Algorithm"
                  value={getModelName()}
                />

                <InfoRow
                  label="Target"
                  value={metric}
                />

                <InfoRow
                  label="Forecast Horizon"
                  value={`${forecastDays} Days`}
                />

                <InfoRow
                  label="Last Historical Date"
                  value={lastDate || "—"}
                />

                {result.order && (
                  <InfoRow
                    label="ARIMA Order"
                    value={JSON.stringify(result.order)}
                  />
                )}

                {result.seasonal_order && (
                  <InfoRow
                    label="Seasonal Order"
                    value={JSON.stringify(result.seasonal_order)}
                  />
                )}

                {result.aic !== undefined && (
                  <InfoRow
                    label="AIC"
                    value={formatNumber(result.aic, 2)}
                  />
                )}

                {result.bic !== undefined && (
                  <InfoRow
                    label="BIC"
                    value={formatNumber(result.bic, 2)}
                  />
                )}

                {Object.keys(modelDetails)
                  .filter(
                    (key) =>
                      ![].includes(key)
                  )
                  .map((key) => (
                    <InfoRow
                      key={key}
                      label={formatMetricName(key)}
                      value={
                        typeof modelDetails[key] === "object"
                          ? JSON.stringify(modelDetails[key])
                          : typeof modelDetails[key] === "number"
                          ? formatNumber(modelDetails[key], 4)
                          : String(modelDetails[key])
                      }
                    />
                  ))}

              </div>
            </div>

            <div className="analysis-card">
              <h2>Model Evaluation</h2>

              {Object.keys(metrics).length > 0 ? (
                <div className="metrics-list">
                  {Object.entries(metrics).map(
                    ([key, value]) => (
                      <div
                        className="evaluation-row"
                        key={key}
                      >
                        <span>
                          {formatMetricName(key)}
                        </span>
                        <strong>
                          {typeof value === "number"
                            ? formatNumber(value, 4)
                            : value}
                        </strong>
                      </div>
                    )
                  )}
                </div>
              ) : (
                <div className="empty-state">
                  Forecast evaluation metrics are
                  not available for this model.
                </div>
              )}
            </div>

          </div>


          {/* FORECAST TABLE */}

          {forecast.length > 0 && (
            <div className="analysis-card">
              <h2>Forecast Values</h2>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Date</th>
                      <th>Predicted {metric}</th>
                    </tr>
                  </thead>
                  <tbody>
                    {forecast.map((item, index) => (
                      <tr key={index}>
                        <td>
                          {item.date || `Day ${index + 1}`}
                        </td>
                        <td>
                          {formatNumber(item.forecast, 2)}
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          )}

        </>
      )}

    </div>

  );

}


function InfoRow({ label, value }) {

  return (
    <div className="info-row">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );

}


function formatMetricName(name) {

  return String(name)
    .replaceAll("_", " ")
    .replace(/\b\w/g, (letter) =>
      letter.toUpperCase()
    );

}


function formatNumber(value, digits) {

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "—";
  }

  return number.toLocaleString(undefined, {
    minimumFractionDigits: digits,
    maximumFractionDigits: digits,
  });

}


export default TimeSeries;
