import { useEffect, useState } from "react";

import {
  getABCXYZMatrix,
  getDateRange,
} from "../services/api";

import "./Predictive.css";
import "./Inventory.css";


const STRATEGY = {
  AX: "Tight control, reliable replenishment, high service",
  AY: "Moderate safety stock, monitor closely",
  AZ: "Careful forecasting, safety-stock review",
  BX: "Standard replenishment policies",
  BY: "Moderate monitoring",
  BZ: "Watch forecast accuracy, avoid overstock",
  CX: "Simpler replenishment policies, low priority",
  CY: "Periodic review, minimal stock",
  CZ: "Avoid excess investment, order on demand",
};

const CELL_DESCRIPTIONS = {
  A: "High-value",
  B: "Medium-value",
  C: "Low-value",
  X: "Stable demand",
  Y: "Moderately variable",
  Z: "Highly variable",
};

const ABC_COLORS = { A: "#2563eb", B: "#f59e0b", C: "#9ca3af" };
const XYZ_COLORS = { X: "#059669", Y: "#f59e0b", Z: "#dc2626" };


function ABCXYZ() {

  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [dateRange, setDateRange] = useState(null);

  const [period, setPeriod] = useState("M");

  const [cvX, setCvX] = useState(0.5);
  const [cvY, setCvY] = useState(1.0);

  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [selectedCell, setSelectedCell] = useState(null);


  useEffect(() => {

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

      } catch (err) {
        console.error("Date range error:", err);
      }

    };

    loadDateRange();

  }, []);


  const runAnalysis = async () => {

    if (fromDate && toDate && fromDate > toDate) {
      setError("From Date must not be after To Date.");
      return;
    }

    if (cvX >= cvY) {
      setError("CV X threshold must be less than CV Y threshold.");
      return;
    }

    try {

      setLoading(true);
      setError("");
      setResults(null);
      setSelectedCell(null);

      const res = await getABCXYZMatrix({
        startDate: fromDate || undefined,
        endDate: toDate || undefined,
        period,
        cvX,
        cvY,
      });

      setResults(res.data);

    } catch (err) {

      setError(
        err.response?.data?.error ||
        err.message ||
        "Failed to run ABC-XYZ matrix."
      );

    } finally {

      setLoading(false);

    }

  };


  const handleCellClick = (abc, xyz) => {
    setSelectedCell(`${abc}${xyz}`);
  };


  const renderSetup = () => {

    return (
      <div className="analysis-card">
        <div className="card-header">
          <div>
            <h2>ABC-XYZ Matrix Setup</h2>
            <p>
              Combine value-based (ABC) and variability-based (XYZ)
              classifications into a strategic inventory matrix.
            </p>
          </div>
        </div>

        <div className="inventory-filters">
          <div className="field-group">
            <label>From Date</label>
            <input
              type="date"
              value={fromDate}
              min={dateRange?.min || ""}
              max={dateRange?.max || ""}
              onChange={(e) => setFromDate(e.target.value)}
            />
          </div>

          <div className="field-group">
            <label>To Date</label>
            <input
              type="date"
              value={toDate}
              min={dateRange?.min || ""}
              max={dateRange?.max || ""}
              onChange={(e) => setToDate(e.target.value)}
            />
          </div>

          <div className="field-group">
            <label>XYZ Period</label>
            <select value={period} onChange={(e) => setPeriod(e.target.value)}>
              <option value="M">Monthly</option>
              <option value="W">Weekly</option>
              <option value="Q">Quarterly</option>
            </select>
          </div>

          <div className="field-group threshold-input">
            <label>CV X</label>
            <input
              type="number"
              min="0"
              step="0.1"
              value={cvX}
              onChange={(e) => setCvX(Number(e.target.value))}
            />
          </div>

          <div className="field-group threshold-input">
            <label>CV Y</label>
            <input
              type="number"
              min="0"
              step="0.1"
              value={cvY}
              onChange={(e) => setCvY(Number(e.target.value))}
            />
          </div>
        </div>

        <div className="selection-actions">
          <button
            className="refresh-button"
            onClick={runAnalysis}
            disabled={loading}
          >
            {loading ? "Analyzing..." : "Build Matrix"}
          </button>
        </div>

      </div>
    );

  };


  const renderSummary = () => {

    if (!results) {
      return null;
    }

    const abc = results.abc_summary || {};
    const xyz = results.xyz_summary || {};

    return (
      <div className="analysis-card">
        <h2>Classification Summary</h2>
        <div className="summary-grid-2">
          <div>
            <h3>ABC ({abc.value_metric || "Revenue"})</h3>
            <div className="legend-line">
              <span className="legend-dot" style={{ background: ABC_COLORS.A }} />
              A: {abc.counts?.A ?? 0}
            </div>
            <div className="legend-line">
              <span className="legend-dot" style={{ background: ABC_COLORS.B }} />
              B: {abc.counts?.B ?? 0}
            </div>
            <div className="legend-line">
              <span className="legend-dot" style={{ background: ABC_COLORS.C }} />
              C: {abc.counts?.C ?? 0}
            </div>
          </div>
          <div>
            <h3>XYZ (CV thresholds {xyz.thresholds?.x} / {xyz.thresholds?.y})</h3>
            <div className="legend-line">
              <span className="legend-dot" style={{ background: XYZ_COLORS.X }} />
              X: {xyz.counts?.X ?? 0}
            </div>
            <div className="legend-line">
              <span className="legend-dot" style={{ background: XYZ_COLORS.Y }} />
              Y: {xyz.counts?.Y ?? 0}
            </div>
            <div className="legend-line">
              <span className="legend-dot" style={{ background: XYZ_COLORS.Z }} />
              Z: {xyz.counts?.Z ?? 0}
            </div>
          </div>
        </div>
      </div>
    );

  };


  const renderMatrix = () => {

    if (!results?.matrix_counts) {
      return null;
    }

    const matrix = results.matrix_counts;

    const rows = ["A", "B", "C"];

    return (
      <div className="analysis-card">
        <h2>ABC-XYZ Strategic Matrix</h2>
        <p className="card-description">
          {results.total} item(s) with both ABC and XYZ classifications.
          Click a cell to highlight its strategy.
        </p>

        <div className="matrix-table-wrap">
          <table className="matrix-table">
            <thead>
              <tr>
                <th>ABC \\ XYZ</th>
                <th>X (Stable)</th>
                <th>Y (Moderate)</th>
                <th>Z (Variable)</th>
              </tr>
            </thead>
            <tbody>
              {rows.map((abc) => (
                <tr key={abc}>
                  <th className="matrix-row-label">
                    <span className={`class-badge class-${abc}`}>{abc}</span>
                    {CELL_DESCRIPTIONS[abc]}
                  </th>
                  {["X", "Y", "Z"].map((xyz) => {

                    const key = `${abc}${xyz}`;
                    const count = matrix[abc]?.[xyz] ?? 0;
                    const active = selectedCell === key;
                    const percent =
                      results.matrix_percentages?.[abc]?.[xyz] ??
                      (
                        results.total > 0
                          ? count / results.total * 100
                          : 0
                      );

                    return (
                      <td
                        key={key}
                        className={
                          `matrix-cell ${active ? "active" : ""} ${count > 0 ? "has-data" : "no-data"}`
                        }
                        onClick={() => handleCellClick(abc, xyz)}
                        title={STRATEGY[key]}
                      >
                        <div className="matrix-cell-count">{count}</div>
                        <div className="matrix-cell-percent">
                          {formatNumber(percent, 1)}%
                        </div>
                        <div className="matrix-cell-strategy">
                          {STRATEGY[key]}
                        </div>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {selectedCell && (
          <div className="selected-cell-info">
            <h3>
              {selectedCell}: {CELL_DESCRIPTIONS[selectedCell[0]]} +{" "}
              {CELL_DESCRIPTIONS[selectedCell[1]]}
            </h3>
            <p>{STRATEGY[selectedCell]}</p>
          </div>
        )}

      </div>
    );

  };


  const renderInsights = () => {

    const insights = results?.insights || [];

    if (insights.length === 0) {
      return null;
    }

    return (
      <div className="analysis-card">
        <h2>Inventory Management Insights</h2>
        <p className="card-description">
          Insights generated from the actual classification results.
        </p>

        <div className="insights-grid">
          {insights.map((insight) => (
            <div className="insight-card" key={insight.combination}>
              <div className="insight-header">
                <span className="class-badge">{insight.combination}</span>
                <strong>{insight.count} items</strong>
                <span>{formatNumber(insight.percent, 1)}%</span>
              </div>
              <p>{insight.message}</p>
            </div>
          ))}
        </div>
      </div>
    );

  };


  return (
    <div className="predictive-page">
      <div className="page-header">
        <div>
          <h1>ABC-XYZ Matrix</h1>
          <p>
            Combine value and demand-variability classifications
            into a strategic inventory matrix.
          </p>
        </div>
      </div>

      {renderSetup()}

      {error && (
        <div className="error-box">
          <h3>Error</h3>
          <p>{error}</p>
        </div>
      )}

      {loading && (
        <div className="loading-box">
          <div className="loader"></div>
          <h3>Building ABC-XYZ matrix...</h3>
        </div>
      )}

      {!loading && results && (
        <>
          {renderSummary()}
          {renderMatrix()}
          {renderInsights()}
        </>
      )}

      {!loading && results && results.total === 0 && (
        <div className="empty-state">
          No items with both ABC and XYZ classifications found in the
          selected range.
        </div>
      )}

      {!loading && !results && (
        <div className="empty-state">
          Configure the parameters, then click "Build Matrix".
        </div>
      )}

    </div>
  );

}


function formatNumber(value, digits) {

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "\u2014";
  }

  if (digits !== undefined) {
    return number.toLocaleString("en-IN", {
      minimumFractionDigits: digits,
      maximumFractionDigits: digits,
    });
  }

  return number.toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  });

}


export default ABCXYZ;
