import { useEffect, useState, useCallback } from "react";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  PieChart,
  Pie,
  Legend,
  LineChart,
  Line,
  ScatterChart,
  Scatter,
  ZAxis,
} from "recharts";

import {
  getXYZAnalysis,
  getXYZTrend,
  getDateRange,
} from "../services/api";

import "./Predictive.css";
import "./Inventory.css";


const XYZ_COLORS = {
  X: "#059669",
  Y: "#f59e0b",
  Z: "#dc2626",
  ND: "#9ca3af",
  U: "#6b7280",
};


function XYZ() {

  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [dateRange, setDateRange] = useState(null);

  const [period, setPeriod] = useState("M");

  const [cvX, setCvX] = useState(0.5);
  const [cvY, setCvY] = useState(1.0);

  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  const [selectedTrend, setSelectedTrend] = useState(null);
  const [trendData, setTrendData] = useState(null);
  const [trendLoading, setTrendLoading] = useState(false);

  // Table state
  const [search, setSearch] = useState("");
  const [classFilter, setClassFilter] = useState("All");
  const [sortBy, setSortBy] = useState("cv");
  const [sortDir, setSortDir] = useState("asc");
  const [page, setPage] = useState(1);
  const pageSize = 10;


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


  const validateForm = () => {

    if (fromDate && toDate && fromDate > toDate) {
      return "From Date must not be after To Date.";
    }

    if (cvX >= cvY) {
      return "CV X threshold must be less than CV Y threshold.";
    }

    return "";

  };


  const runAnalysis = async () => {

    const validation = validateForm();

    if (validation) {
      setError(validation);
      return;
    }

    try {

      setLoading(true);
      setError("");
      setResults(null);
      setSelectedTrend(null);
      setTrendData(null);
      setPage(1);

      const res = await getXYZAnalysis({
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
        "Failed to run XYZ analysis."
      );

    } finally {

      setLoading(false);

    }

  };


  const loadTrend = async (productId) => {

    setSelectedTrend(productId);
    setTrendData(null);
    setTrendLoading(true);

    try {

      const res = await getXYZTrend(productId, {
        period,
        startDate: fromDate || undefined,
        endDate: toDate || undefined,
      });

      setTrendData(res.data?.trend || []);

    } catch (err) {

      setTrendData([]);

    } finally {

      setTrendLoading(false);

    }

  };


  const getFilteredItems = useCallback(() => {

    if (!results?.items) {
      return [];
    }

    let items = results.items.slice();

    if (classFilter !== "All") {
      items = items.filter(
        (item) => item.class === classFilter
      );
    }

    const query = search.trim().toLowerCase();

    if (query) {
      items = items.filter(
        (item) =>
          (item.product_id || "")
            .toLowerCase()
            .includes(query)
      );
    }

    const dir = sortDir === "asc" ? 1 : -1;

    items.sort((a, b) => {
      const av = a[sortBy];
      const bv = b[sortBy];
      if (typeof av === "string" || typeof bv === "string") {
        return String(av).localeCompare(String(bv)) * dir;
      }
      return ((Number(av) || 0) - (Number(bv) || 0)) * dir;
    });

    return items;

  }, [results, classFilter, search, sortBy, sortDir]);


  const totalFiltered = getFilteredItems().length;
  const totalPages = Math.max(1, Math.ceil(totalFiltered / pageSize));
  const safePage = Math.min(page, totalPages);
  const pageItems = getFilteredItems().slice(
    (safePage - 1) * pageSize,
    safePage * pageSize
  );


  const handleSort = (key) => {

    if (sortBy === key) {
      setSortDir((prev) =>
        prev === "asc" ? "desc" : "asc"
      );
    } else {
      setSortBy(key);
      setSortDir("asc");
    }

  };


  const sortIndicator = (key) => {
    if (sortBy !== key) {
      return "";
    }
    return sortDir === "asc" ? "\u2191" : "\u2193";
  };


  const renderSetup = () => {

    return (
      <div className="analysis-card">
        <div className="card-header">
          <div>
            <h2>XYZ Setup</h2>
            <p>
              Classify items by demand variability
              (coefficient of variation).
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
            <label>Period</label>
            <select
              value={period}
              onChange={(e) => setPeriod(e.target.value)}
            >
              <option value="M">Monthly</option>
              <option value="W">Weekly</option>
              <option value="Q">Quarterly</option>
            </select>
          </div>

          <div className="field-group threshold-input">
            <label>CV X (stable &le;)</label>
            <input
              type="number"
              min="0"
              step="0.1"
              value={cvX}
              onChange={(e) => setCvX(Number(e.target.value))}
            />
          </div>

          <div className="field-group threshold-input">
            <label>CV Y (&le;)</label>
            <input
              type="number"
              min="0"
              step="0.1"
              value={cvY}
              onChange={(e) => setCvY(Number(e.target.value))}
            />
          </div>
        </div>

        {dateRange && (
          <p className="date-range-hint">
            Available data: {dateRange.min} to {dateRange.max}
          </p>
        )}

        <div className="threshold-note">
          X: CV &le; {cvX} &middot; Y: {cvX} &lt; CV &le; {cvY}
          {" "}&middot; Z: CV &gt; {cvY}. Items with zero demand are
          marked "No Demand"; items with too few periods are
          "Unclassified".
        </div>

        <div className="selection-actions">
          <button
            className="refresh-button"
            onClick={runAnalysis}
            disabled={loading}
          >
            {loading ? "Analyzing..." : "Run XYZ Analysis"}
          </button>
        </div>

      </div>
    );

  };


  const renderSummary = () => {

    if (!results?.summary) {
      return null;
    }

    const summary = results.summary;
    const counts = summary.counts || {};

    const labels = [
      { key: "total_items", label: "Total Items", color: "#111827" },
      { key: "X", label: "X Items", color: XYZ_COLORS.X, count: true },
      { key: "Y", label: "Y Items", color: XYZ_COLORS.Y, count: true },
      { key: "Z", label: "Z Items", color: XYZ_COLORS.Z, count: true },
      {
        key: "unclassified",
        label: "Unclassified",
        color: XYZ_COLORS.U,
        custom: true,
      },
    ];

    return (
      <div className="analysis-card">
        <h2>XYZ Summary</h2>
        <p className="card-description">
          {summary.total_items} items analyzed across{" "}
          {summary.total_periods} {summary.period === "W" ? "weeks" : summary.period === "Q" ? "quarters" : "months"}.
          Average CV: {formatNumber(summary.average_cv, 3)}.
        </p>

        <div className="inventory-kpi-grid">
          {labels.map((card) => {

            let value = summary.total_items;

            if (card.count) {
              value = counts[card.key] ?? 0;
            } else if (card.custom) {
              value =
                (counts.ND ?? 0) +
                (counts.U ?? 0);
            }

            return (
              <div
                className="inventory-kpi"
                key={card.label}
              >
                <span>{card.label}</span>
                <strong style={{ color: card.color }}>
                  {formatNumber(value, 0)}
                </strong>
              </div>
            );
          })}
        </div>

        {(summary.most_stable || summary.most_variable) && (
          <div className="xyz-highlights">
            {summary.most_stable && (
              <div className="highlight-chip stable-chip">
                <strong>Most Stable:</strong>{" "}
                {summary.most_stable.product_id}
                <span>
                  CV {formatNumber(summary.most_stable.cv, 3)}
                </span>
              </div>
            )}
            {summary.most_variable && (
              <div className="highlight-chip variable-chip">
                <strong>Most Variable:</strong>{" "}
                {summary.most_variable.product_id}
                <span>
                  CV {formatNumber(summary.most_variable.cv, 3)}
                </span>
              </div>
            )}
          </div>
        )}

      </div>
    );

  };


  const renderDistribution = () => {

    const data = results?.distribution || [];

    const pieData = data
      .filter((d) => d.items > 0)
      .map((d) => ({
        name: d.label,
        value: d.items,
        fill: XYZ_COLORS[d.class] || "#9ca3af",
      }));

    if (pieData.length === 0) {
      return null;
    }

    return (
      <div className="two-column">
        <div className="analysis-card">
          <h2>XYZ Distribution</h2>
          <p className="card-description">
            Items by demand variability class.
          </p>
          <ResponsiveContainer width="100%" height={300}>
            <PieChart>
              <Pie
                data={pieData}
                dataKey="value"
                nameKey="name"
                cx="50%"
                cy="50%"
                outerRadius={100}
                label={(entry) => entry.name}
              >
                {pieData.map((entry) => (
                  <Cell key={entry.name} fill={entry.fill} />
                ))}
              </Pie>
              <Tooltip formatter={(value) => formatNumber(value, 0)} />
              <Legend />
            </PieChart>
          </ResponsiveContainer>
        </div>

        <div className="analysis-card">
          <h2>Demand Variability</h2>
          <p className="card-description">
            CV values for each classified item.
          </p>
          {renderVariabilityChart()}
        </div>
      </div>
    );

  };


  const renderVariabilityChart = () => {

    const variability = results?.variability || [];

    if (variability.length === 0) {
      return (
        <div className="compact-empty">
          No classified item variability data available.
        </div>
      );
    }

    const chartData = variability.slice(0, 100).map((v) => ({
      name: v.product_id,
      value: Number(v.cv_pct) || 0,
      class: v.class,
    }));

    const thresholdX = (cvX || 0.5) * 100;

    return (
      <ResponsiveContainer width="100%" height={300}>
        <BarChart data={chartData}>
          <CartesianGrid strokeDasharray="3 3" />
          <XAxis
            dataKey="name"
            interval={Math.max(0, Math.floor(chartData.length / 10))}
          />
          <YAxis
            label={{
              value: "CV %",
              angle: -90,
              position: "insideLeft",
              style: { fontSize: 11, fill: "#6b7280" },
            }}
          />
          <Tooltip
            formatter={(value) => `${formatNumber(value, 2)}%`}
          />
          <Bar dataKey="value" name="CV %" radius={[4, 4, 0, 0]}>
            {chartData.map((entry, index) => (
              <Cell
                key={index}
                fill={XYZ_COLORS[entry.class] || "#9ca3af"}
              />
            ))}
          </Bar>
        </BarChart>
      </ResponsiveContainer>
    );
  };


  const renderMeanCvScatter = () => {

    const variability = results?.variability || [];

    if (variability.length === 0) {
      return null;
    }

    const chartData = variability
      .filter((v) => Number(v.mean) > 0)
      .slice(0, 300)
      .map((v) => ({
        x: Number(v.mean),
        y: Number(v.cv),
        class: v.class,
        product_id: v.product_id,
      }));

    if (chartData.length === 0) {
      return null;
    }

    return (
      <div className="analysis-card">
        <h2>Demand Volume vs Variability</h2>
        <p className="card-description">
          X-axis: mean demand &middot; Y-axis: CV. Helps identify
          high-demand stable vs high-demand variable products.
        </p>
        <ResponsiveContainer width="100%" height={340}>
          <ScatterChart>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              type="number"
              dataKey="x"
              name="Mean Demand"
              label={{
                value: "Mean Demand",
                position: "insideBottom",
                offset: -5,
                style: { fontSize: 11, fill: "#6b7280" },
              }}
            />
            <YAxis
              type="number"
              dataKey="y"
              name="CV"
              label={{
                value: "CV",
                angle: -90,
                position: "insideLeft",
                style: { fontSize: 11, fill: "#6b7280" },
              }}
            />
            <ZAxis range={[50, 50]} />
            <Tooltip
              cursor={{ strokeDasharray: "3 3" }}
              formatter={(value, name) =>
                name === "y" ? formatNumber(value, 3) : formatNumber(value)
              }
            />
            {["X", "Y", "Z"].map((cls) => {
              const subset = chartData.filter(
                (d) => d.class === cls
              );
              if (subset.length === 0) {
                return null;
              }
              return (
                <Scatter
                  key={cls}
                  name={`Class ${cls}`}
                  data={subset}
                  fill={XYZ_COLORS[cls]}
                />
              );
            })}
          </ScatterChart>
        </ResponsiveContainer>
      </div>
    );

  };


  const renderTrend = () => {

    if (!selectedTrend) {
      return null;
    }

    return (
      <div className="analysis-card">
        <div className="card-header">
          <div>
            <h2>Demand Trend</h2>
            <p className="card-description">
              Historical demand for{" "}
              <strong>{selectedTrend}</strong>. Explains why this
              item was classified as it was.
            </p>
          </div>
        </div>

        {trendLoading && (
          <div className="compact-empty">Loading trend...</div>
        )}

        {!trendLoading && trendData && trendData.length > 0 && (
          <ResponsiveContainer width="100%" height={300}>
            <LineChart data={trendData}>
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis dataKey="label" />
              <YAxis />
              <Tooltip
                formatter={(value) => formatNumber(value)}
              />
              <Line
                type="monotone"
                dataKey="quantity"
                name="Demand"
                stroke="#2563eb"
                strokeWidth={2}
                dot={false}
              />
            </LineChart>
          </ResponsiveContainer>
        )}

        {!trendLoading && trendData && trendData.length === 0 && (
          <div className="compact-empty">
            No demand data available for this product.
          </div>
        )}
      </div>
    );

  };


  const renderTable = () => {

    if (!results?.items || results.items.length === 0) {
      return null;
    }

    const counts = results.summary?.counts || {};

    return (
      <div className="analysis-card">
        <h2>XYZ Item Table</h2>
        <p className="card-description">
          {totalFiltered} item(s). Period:{" "}
          {results.summary?.period === "M"
            ? "monthly"
            : results.summary?.period === "W"
            ? "weekly"
            : "quarterly"}
          {" (" + (results.summary?.total_periods || 0) + " total)."}
        </p>

        <div className="table-toolbar">
          <input
            type="text"
            className="table-search"
            placeholder="Search product ID..."
            value={search}
            onChange={(e) => {
              setSearch(e.target.value);
              setPage(1);
            }}
          />

          <select
            className="table-filter"
            value={classFilter}
            onChange={(e) => {
              setClassFilter(e.target.value);
              setPage(1);
            }}
          >
            <option value="All">All Classes</option>
            <option value="X">X (Stable)</option>
            <option value="Y">Y (Moderate)</option>
            <option value="Z">Z (Variable)</option>
            <option value="ND">No Demand</option>
            <option value="U">Unclassified</option>
          </select>

          {counts && (
            <span className="table-counts">
              X:{counts.X} &middot; Y:{counts.Y} &middot; Z:{counts.Z}
            </span>
          )}
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th className="sortable" onClick={() => handleSort("product_id")}>
                  Product {sortIndicator("product_id")}
                </th>
                <th className="sortable" onClick={() => handleSort("mean_demand")}>
                  Mean Demand {sortIndicator("mean_demand")}
                </th>
                <th className="sortable" onClick={() => handleSort("std_dev")}>
                  Std Dev {sortIndicator("std_dev")}
                </th>
                <th className="sortable" onClick={() => handleSort("cv")}>
                  CV {sortIndicator("cv")}
                </th>
                <th className="sortable" onClick={() => handleSort("cv_pct")}>
                  CV % {sortIndicator("cv_pct")}
                </th>
                <th className="sortable" onClick={() => handleSort("periods")}>
                  Periods {sortIndicator("periods")}
                </th>
                <th className="sortable" onClick={() => handleSort("class")}>
                  Class {sortIndicator("class")}
                </th>
                <th>Trend</th>
              </tr>
            </thead>
            <tbody>
              {pageItems.length === 0 && (
                <tr>
                  <td colSpan={8} className="table-empty">
                    No items match the current filters.
                  </td>
                </tr>
              )}

              {pageItems.map((item) => {
                const cls = item.class;
                return (
                  <tr key={item.product_id}>
                    <td>
                      <strong>{item.product_id}</strong>
                    </td>
                    <td>{formatNumber(item.mean_demand)}</td>
                    <td>{formatNumber(item.std_dev)}</td>
                    <td>{formatNumber(item.cv, 3)}</td>
                    <td>{formatNumber(item.cv_pct, 2)}%</td>
                    <td>{item.periods}</td>
                    <td>
                      <span
                        className={`class-badge class-${cls}`}
                        title={item.class_label}
                      >
                        {cls}
                      </span>
                      <div className="sub-text">{item.class_label}</div>
                    </td>
                    <td>
                      <button
                        className="trend-button"
                        onClick={() => loadTrend(item.product_id)}
                      >
                        View Trend
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>

        <div className="pagination-row">
          <span>
            Showing {totalFiltered === 0 ? 0 : (safePage - 1) * pageSize + 1}–
            {Math.min(safePage * pageSize, totalFiltered)} of {totalFiltered}
          </span>
          <div className="pagination-buttons">
            <button
              disabled={safePage <= 1}
              onClick={() => setPage((p) => Math.max(1, p - 1))}
            >
              Prev
            </button>
            <span>
              {safePage} / {totalPages}
            </span>
            <button
              disabled={safePage >= totalPages}
              onClick={() => setPage((p) => Math.min(totalPages, p + 1))}
            >
              Next
            </button>
          </div>
        </div>

      </div>
    );

  };


  return (
    <div className="predictive-page">
      <div className="page-header">
        <div>
          <h1>XYZ Analysis</h1>
          <p>
            Classify inventory items by demand variability
            and predictability.
          </p>
        </div>
      </div>

      {renderSetup()}

      {error && (
        <div className="error-box">
          <h3>Validation Error</h3>
          <p>{error}</p>
        </div>
      )}

      {loading && (
        <div className="loading-box">
          <div className="loader"></div>
          <h3>Running XYZ analysis...</h3>
        </div>
      )}

      {!loading && results && (
        <>
          {renderSummary()}
          {renderDistribution()}
          {renderMeanCvScatter()}
          {renderTrend()}
          {renderTable()}
        </>
      )}

      {!loading && results && results.items?.length === 0 && (
        <div className="empty-state">
          No product demand data available for the selected
          date range.
        </div>
      )}

      {!loading && !results && (
        <div className="empty-state">
          Configure the parameters, then click "Run XYZ Analysis".
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

  if (Math.abs(number) >= 1000000) {
    return `${(number / 1000000).toFixed(2)}M`;
  }

  if (Math.abs(number) >= 1000) {
    return `${(number / 1000).toFixed(1)}K`;
  }

  return number.toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  });

}


export default XYZ;
