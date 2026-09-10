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
  ComposedChart,
  Line,
  Legend,
} from "recharts";

import {
  getABCAnalysis,
  getDateRange,
} from "../services/api";

import "./Predictive.css";
import "./Inventory.css";


const ABC_COLORS = {
  A: "#2563eb",
  B: "#f59e0b",
  C: "#9ca3af",
};


function ABC() {

  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [dateRange, setDateRange] = useState(null);

  const [thresholdA, setThresholdA] = useState(0.8);
  const [thresholdB, setThresholdB] = useState(0.95);

  const [results, setResults] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  // Table state
  const [search, setSearch] = useState("");
  const [classFilter, setClassFilter] = useState("All");
  const [sortBy, setSortBy] = useState("rank");
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

    if (thresholdA >= thresholdB) {
      return "Threshold A (80%) must be less than Threshold B (95%).";
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
      setPage(1);

      const res = await getABCAnalysis({
        startDate: fromDate || undefined,
        endDate: toDate || undefined,
        thresholdA,
        thresholdB,
      });

      setResults(res.data);

    } catch (err) {

      setError(
        err.response?.data?.error ||
        err.message ||
        "Failed to run ABC analysis."
      );

    } finally {

      setLoading(false);

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
          (item.product_name || "")
            .toLowerCase()
            .includes(query) ||
          (item.product_id || "")
            .toLowerCase()
            .includes(query)
      );
    }

    // Sort
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

    return sortDir === "asc"
      ? "\u2191"
      : "\u2193";

  };


  const renderSetup = () => {

    return (
      <div className="analysis-card">
        <div className="card-header">
          <div>
            <h2>ABC Setup</h2>
            <p>
              Classify inventory items by contribution
              to total consumption value.
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

          <div className="field-group threshold-input">
            <label>Threshold A (cumulative %) </label>
            <input
              type="number"
              min="0"
              max="100"
              step="1"
              value={Math.round(thresholdA * 100)}
              onChange={(e) =>
                setThresholdA(Number(e.target.value) / 100)
              }
            />
          </div>

          <div className="field-group threshold-input">
            <label>Threshold B (cumulative %)</label>
            <input
              type="number"
              min="0"
              max="100"
              step="1"
              value={Math.round(thresholdB * 100)}
              onChange={(e) =>
                setThresholdB(Number(e.target.value) / 100)
              }
            />
          </div>
        </div>

        {dateRange && (
          <p className="date-range-hint">
            Available data: {dateRange.min} to {dateRange.max}
          </p>
        )}

        <div className="threshold-note">
          A: cumulative &le; {Math.round(thresholdA * 100)}% &middot;
          B: {Math.round(thresholdA * 100)}% &lt; cumulative &le;{" "}
          {Math.round(thresholdB * 100)}% &middot;
          C: cumulative &gt; {Math.round(thresholdB * 100)}%
        </div>

        <div className="selection-actions">
          <button
            className="refresh-button"
            onClick={runAnalysis}
            disabled={loading}
          >
            {loading ? "Analyzing..." : "Run ABC Analysis"}
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

    const cards = [
      {
        label: "Total Items",
        value: formatNumber(summary.total_items, 0),
        color: "#111827",
      },
      {
        label: "A Items",
        value: formatNumber(summary.counts.A, 0),
        color: ABC_COLORS.A,
      },
      {
        label: "B Items",
        value: formatNumber(summary.counts.B, 0),
        color: ABC_COLORS.B,
      },
      {
        label: "C Items",
        value: formatNumber(summary.counts.C, 0),
        color: ABC_COLORS.C,
      },
      {
        label: "Total Value",
        value: formatNumber(summary.total_value),
        color: "#059669",
      },
    ];

    return (
      <div className="analysis-card">
        <h2>ABC Summary</h2>
        <p className="card-description">
          Classification based on{" "}
          <strong>{summary.value_metric || "Revenue"}</strong>.
          {summary.thresholds &&
            ` Thresholds: A <= ${formatNumber(summary.thresholds.a * 100, 0)}%, B <= ${formatNumber(summary.thresholds.b * 100, 0)}%.`}
        </p>

        <div className="inventory-kpi-grid">
          {cards.map((card) => (
            <div
              className="inventory-kpi"
              key={card.label}
            >
              <span>{card.label}</span>
              <strong style={{ color: card.color }}>
                {card.value}
              </strong>
            </div>
          ))}
        </div>

        <div className="value-contribution">
          <span>
            A: {formatNumber(summary.value_pct_a, 1)}%
            of value
          </span>
          <span>
            B: {formatNumber(summary.value_pct_b, 1)}%
            of value
          </span>
          <span>
            C: {formatNumber(summary.value_pct_c, 1)}%
            of value
          </span>
        </div>

      </div>
    );

  };


  const renderDistribution = () => {

    const data = results?.distribution || [];

    const hasValid = data.some((d) => d.items > 0);

    if (!hasValid) {
      return null;
    }

    const pieData = data
      .filter((d) => d.items > 0)
      .map((d) => ({
        name: `Class ${d.class}`,
        value: d.items,
        fill: ABC_COLORS[d.class],
      }));

    return (
      <div className="two-column">
        <div className="analysis-card">
          <h2>ABC Distribution</h2>
          <p className="card-description">
            Number of items in each class.
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
          <h2>Value Contribution</h2>
          <p className="card-description">
            Total inventory value contributed by A, B and C.
          </p>
          <ResponsiveContainer width="100%" height={300}>
            <BarChart data={data} layout="vertical">
              <CartesianGrid strokeDasharray="3 3" />
              <XAxis type="number" />
              <YAxis type="category" dataKey="class" width={40} />
              <Tooltip
                formatter={(value, name) => [
                  formatNumber(value),
                  name,
                ]}
              />
              <Bar dataKey="value" name="Value" radius={[0, 4, 4, 0]}>
                {data.map((d) => (
                  <Cell key={d.class} fill={ABC_COLORS[d.class]} />
                ))}
              </Bar>
            </BarChart>
          </ResponsiveContainer>
        </div>
      </div>
    );

  };


  const renderPareto = () => {

    const pareto = results?.pareto || [];

    if (pareto.length === 0) {
      return null;
    }

    const chartData = pareto.map((p) => ({
      name: p.name,
      value: p.value,
      cumulative: Number(p.cumulative_pct) || 0,
      class: p.class,
    }));

    return (
      <div className="analysis-card">
        <h2>Pareto (ABC) Chart</h2>
        <p className="card-description">
          Items sorted by consumption value (bars) with cumulative
          contribution (line). Thresholds A and B are highlighted.
          For large datasets the chart aggregates to the top items.
        </p>

        <ResponsiveContainer width="100%" height={380}>
          <ComposedChart data={chartData}>
            <CartesianGrid strokeDasharray="3 3" />
            <XAxis
              dataKey="name"
              interval={Math.max(0, Math.floor(chartData.length / 12))}
              tick={{ fontSize: 10 }}
            />
            <YAxis yAxisId="left" />
            <YAxis
              yAxisId="right"
              orientation="right"
              domain={[0, 100]}
              tickFormatter={(value) => `${value}%`}
            />
            <Tooltip
              formatter={(value, name) =>
                name === "cumulative"
                  ? `${formatNumber(value, 2)}%`
                  : formatNumber(value)
              }
            />
            <Legend />
            <Bar
              yAxisId="left"
              dataKey="value"
              name="Consumption Value"
              radius={[2, 2, 0, 0]}
            >
              {chartData.map((entry, index) => (
                <Cell
                  key={index}
                  fill={ABC_COLORS[entry.class]}
                />
              ))}
            </Bar>
            <Line
              yAxisId="right"
              type="monotone"
              dataKey="cumulative"
              name="Cumulative %"
              stroke="#dc2626"
              dot={false}
            />
          </ComposedChart>
        </ResponsiveContainer>
      </div>
    );

  };


  const renderTable = () => {

    if (!results?.items || results.items.length === 0) {
      return null;
    }

    return (
      <div className="analysis-card">
        <h2>ABC Item Table</h2>
        <p className="card-description">
          {totalFiltered} item(s) classified. Sorted by{" "}
          {sortBy} ({sortDir}).
        </p>

        <div className="table-toolbar">
          <input
            type="text"
            className="table-search"
            placeholder="Search products..."
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
            <option value="A">A</option>
            <option value="B">B</option>
            <option value="C">C</option>
          </select>
        </div>

        <div className="table-wrapper">
          <table>
            <thead>
              <tr>
                <th className="sortable" onClick={() => handleSort("rank")}>
                  Rank {sortIndicator("rank")}
                </th>
                <th
                  className="sortable"
                  onClick={() => handleSort("product_name")}
                >
                  Product {sortIndicator("product_name")}
                </th>
                <th
                  className="sortable"
                  onClick={() => handleSort("quantity")}
                >
                  Quantity {sortIndicator("quantity")}
                </th>
                <th
                  className="sortable"
                  onClick={() => handleSort("unit_price")}
                >
                  Unit Price {sortIndicator("unit_price")}
                </th>
                <th
                  className="sortable"
                  onClick={() => handleSort("consumption_value")}
                >
                  Value {sortIndicator("consumption_value")}
                </th>
                <th
                  className="sortable"
                  onClick={() => handleSort("contribution_pct")}
                >
                  Contribution {sortIndicator("contribution_pct")}
                </th>
                <th
                  className="sortable"
                  onClick={() => handleSort("cumulative_pct")}
                >
                  Cumulative {sortIndicator("cumulative_pct")}
                </th>
                <th
                  className="sortable"
                  onClick={() => handleSort("class")}
                >
                  Class {sortIndicator("class")}
                </th>
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

              {pageItems.map((item) => (
                <tr key={item.product_id}>
                  <td>{item.rank}</td>
                  <td>
                    <strong>{item.product_name}</strong>
                    <div className="sub-text">{item.product_id}</div>
                  </td>
                  <td>{formatNumber(item.quantity)}</td>
                  <td>{formatNumber(item.unit_price)}</td>
                  <td>{formatNumber(item.consumption_value)}</td>
                  <td>{formatNumber(item.contribution_pct, 2)}%</td>
                  <td>{formatNumber(item.cumulative_pct, 2)}%</td>
                  <td>
                    <span className={`class-badge class-${item.class}`}>
                      {item.class}
                    </span>
                  </td>
                </tr>
              ))}
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
          <h1>ABC Analysis</h1>
          <p>
            Classify inventory items by their contribution to
            total consumption value.
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
          <h3>Running ABC analysis...</h3>
        </div>
      )}

      {!loading && results && (
        <>
          {renderSummary()}
          {renderDistribution()}
          {renderPareto()}
          {renderTable()}
        </>
      )}

      {!loading && results && results.items?.length === 0 && (
        <div className="empty-state">
          No transaction data available for the selected
          date range.
        </div>
      )}

      {!loading && !results && (
        <div className="empty-state">
          Configure the date range and thresholds, then
          click "Run ABC Analysis".
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


export default ABC;
