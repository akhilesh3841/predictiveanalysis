import { useEffect, useState, useCallback } from "react";

import {
  ResponsiveContainer,
  BarChart,
  Bar,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  ScatterChart,
  Scatter,
  ZAxis,
} from "recharts";

import {
  getMultivariateCorrelation,
  getPCA,
  getMultivariateRegression,
  getMultivariateScatter,
  getDateRange,
} from "../services/api";

import "./Predictive.css";


const ALL_NUMERIC_VARIABLES = [
  "Revenue",
  "Quantity",
  "UnitPrice",
  "Transactions",
];


function Multivariate() {

  const [xVariable, setXVariable] =
    useState("Revenue");

  const [yVariables, setYVariables] =
    useState(["Quantity", "Transactions"]);

  const [fromDate, setFromDate] = useState("");
  const [toDate, setToDate] = useState("");
  const [dateRange, setDateRange] = useState(null);

  const [results, setResults] = useState(null);
  const [scatterResults, setScatterResults] = useState({});

  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");


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

      } catch (e) {
        console.error("Date range error:", e);
      }

    };

    loadDateRange();

  }, []);


  const toggleY = (variable) => {

    setError("");
    setResults(null);
    setScatterResults({});

    setYVariables((prev) =>
      prev.includes(variable)
        ? prev.filter((v) => v !== variable)
        : [...prev, variable]
    );

  };


  const validateForm = () => {

    if (yVariables.length === 0) {
      return "Please select at least one Y variable.";
    }

    if (fromDate && toDate && fromDate > toDate) {
      return "From Date must not be after To Date.";
    }

    if (dateRange) {
      if (fromDate && fromDate < dateRange.min) {
        return `From Date must not be before ${dateRange.min}.`;
      }
      if (toDate && toDate > dateRange.max) {
        return `To Date must not be after ${dateRange.max}.`;
      }
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
      setScatterResults({});

      const allVars = [xVariable, ...yVariables]
        .filter(
          (v, i, arr) =>
            arr.indexOf(v) === i
        );

      const scatterVars = allVars.filter(
        (v) => v !== xVariable
      );

      const [
        correlationRes,
        pcaRes,
        regressionRes,
      ] = await Promise.all([

        getMultivariateCorrelation(
          allVars,
          fromDate || undefined,
          toDate || undefined
        )
          .then((r) => r.data)
          .catch(() => null),

        getPCA(
          2,
          allVars,
          fromDate || undefined,
          toDate || undefined
        )
          .then((r) => r.data)
          .catch(() => null),

        getMultivariateRegression(
          xVariable,
          yVariables.filter((v) => v !== xVariable),
          fromDate || undefined,
          toDate || undefined
        )
          .then((r) => r.data)
          .catch(() => null),

      ]);

      setResults({
        correlation: correlationRes,
        pca: pcaRes,
        regression: regressionRes,
      });

      const scatterMap = {};

      const yPromises = scatterVars.map(
        async (yVar) => {

          try {

            const res = await getMultivariateScatter(
              xVariable,
              yVar,
              fromDate || undefined,
              toDate || undefined
            );

            const data = extractScatterData(res.data);

            if (data && data.length > 0) {
              scatterMap[yVar] = data;
            }

          } catch (err) {
            console.error(
              `Scatter ${xVariable} vs ${yVar}:`,
              err
            );
          }

        }
      );

      await Promise.all(yPromises);

      setScatterResults({ ...scatterMap });

    } catch (err) {

      console.error("Multivariate Error:", err);

      setError(
        err.response?.data?.error ||
        err.message ||
        "Failed to run analysis."
      );

    } finally {

      setLoading(false);

    }

  };


  const getXYCorrelations = () => {

    if (!results?.correlation) {
      return [];
    }

    const corrData = results.correlation;
    const matrix =
      corrData.correlation_matrix ||
      corrData.correlationMatrix ||
      {};

    const pairs = [];

    yVariables.forEach((yVar) => {

      if (yVar === xVariable) {
        return;
      }

      const val =
        matrix[xVariable]?.[yVar] ??
        matrix[yVar]?.[xVariable] ??
        null;

      pairs.push({
        x: xVariable,
        y: yVar,
        value: val,
      });

    });

    return pairs;

  };


  const getValidScatterPairs = useCallback(() => {

    return yVariables.filter(
      (y) =>
        y !== xVariable &&
        scatterResults[y] &&
        scatterResults[y].length > 0
    );

  }, [yVariables, xVariable, scatterResults]);


  const renderSetup = () => {

    return (
      <div className="analysis-card">
        <div className="card-header">
          <div>
            <h2>Variable Selection</h2>
            <p>
              Choose the independent variable (X)
              and one or more dependent variables
              (Y).
            </p>
          </div>
        </div>

        <div className="xy-form">

          <div className="field-group">
            <label>X Variable</label>
            <select
              value={xVariable}
              onChange={(e) => {
                setXVariable(e.target.value);
                setYVariables((prev) =>
                  prev.filter(
                    (v) =>
                      v !== e.target.value
                  )
                );
                setResults(null);
                setScatterResults({});
              }}
            >
              {ALL_NUMERIC_VARIABLES.map((v) => (
                <option key={v} value={v}>
                  {v}
                </option>
              ))}
            </select>
          </div>

          <div className="y-checkbox-group">
            <label>Y Variables</label>
            <div className="variable-checkboxes">
              {ALL_NUMERIC_VARIABLES.map((v) => {

                const isX = v === xVariable;
                const isChecked =
                  yVariables.includes(v);

                return (
                  <label
                    key={v}
                    className={`variable-checkbox ${
                      isChecked ? "checked" : ""
                    } ${isX ? "disabled" : ""}`}
                  >
                    <input
                      type="checkbox"
                      checked={isChecked}
                      disabled={isX}
                      onChange={() =>
                        toggleY(v)
                      }
                    />
                    <span>{v}</span>
                    {isX && (
                      <small>(X variable)</small>
                    )}
                  </label>
                );

              })}
            </div>

            {yVariables.length > 0 && (
              <div className="selected-variables">
                <strong>Selected Y:</strong>{" "}
                {yVariables.join(", ")}
              </div>
            )}

            {yVariables.length === 0 && (
              <div className="validation-message">
                Please select at least one Y
                variable.
              </div>
            )}
          </div>

        </div>
      </div>

    );

  };


  const renderDateRange = () => {

    return (
      <div className="analysis-card">
        <div className="card-header">
          <div>
            <h2>Date Range</h2>
            <p>
              The analysis will use data within
              this date range.
            </p>
          </div>
        </div>

        <div className="forecast-form">

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

        </div>

        {dateRange && (
          <p className="date-range-hint">
            Available data: {dateRange.min} to{" "}
            {dateRange.max}
          </p>
        )}

      </div>

    );

  };


  const renderActions = () => {

    return (
      <div className="selection-actions">
        <button
          className="refresh-button"
          onClick={runAnalysis}
          disabled={loading}
        >
          {loading
            ? "Analyzing..."
            : "Run Analysis"}
        </button>
      </div>

    );

  };


  const renderSummary = () => {

    if (!results) {
      return null;
    }

    return (
      <div className="analysis-card">
        <h2>Analysis Summary</h2>
        <div className="info-row">
          <span>X Variable</span>
          <strong>{xVariable}</strong>
        </div>
        <div className="info-row">
          <span>Y Variables</span>
          <strong>
            {yVariables.join(", ")}
          </strong>
        </div>
        <div className="info-row">
          <span>Date Range</span>
          <strong>
            {fromDate || "All"} → {toDate || "All"}
          </strong>
        </div>
      </div>

    );

  };


  const renderScatterPlots = () => {

    if (!results) {
      return null;
    }

    const validPairs = getValidScatterPairs();

    if (validPairs.length === 0) {
      return null;
    }

    const yLabels = validPairs.join(", ");

    return (
      <div className="analysis-card">
        <h2>Relationships</h2>
        <p className="card-description">
          Relationships between {xVariable} and {yLabels}.
        </p>

        <div className="scatter-grid">
          {validPairs.map((yVar) => {

            const data =
              scatterResults[yVar];

            return (
              <div
                key={yVar}
                className="scatter-card"
              >
                <h3>
                  {xVariable} vs {yVar}
                </h3>

                <ResponsiveContainer
                  width="100%"
                  height={280}
                >
                  <ScatterChart>
                    <CartesianGrid
                      strokeDasharray="3 3"
                    />
                    <XAxis
                      type="number"
                      dataKey="x"
                      name={xVariable}
                      label={{
                        value: xVariable,
                        position: "insideBottom",
                        offset: -5,
                        style: { fontSize: 11, fill: '#6b7280' }
                      }}
                    />
                    <YAxis
                      type="number"
                      dataKey="y"
                      name={yVar}
                      label={{
                        value: yVar,
                        angle: -90,
                        position: "insideLeft",
                        style: { fontSize: 11, fill: '#6b7280' }
                      }}
                    />
                    <ZAxis
                      range={[40, 40]}
                    />
                    <Tooltip
                      cursor={{
                        strokeDasharray:
                          "3 3",
                      }}
                      formatter={(value, name) => [
                        formatNumber(value),
                        name
                      ]}
                    />
                    <Scatter
                      name={`${xVariable} vs ${yVar}`}
                      data={data}
                      fill="#2563eb"
                    />
                  </ScatterChart>
                </ResponsiveContainer>

              </div>
            );

          })}
        </div>

      </div>

    );

  };


  const renderCorrelation = () => {

    const pairs = getXYCorrelations();

    if (pairs.length === 0) {
      return null;
    }

    const hasAnyValue = pairs.some(
      (p) => p.value !== null
    );

    return (
      <div className="analysis-card">
        <h2>Correlation</h2>
        <p className="card-description">
          Pearson correlation between {xVariable} and
          each selected Y variable.
        </p>

        {hasAnyValue ? (
          <div className="table-wrapper">
            <table>
              <thead>
                <tr>
                  <th>X Variable</th>
                  <th>Y Variable</th>
                  <th>Correlation</th>
                </tr>
              </thead>
              <tbody>
                {pairs.map((pair, i) => (
                  <tr key={i}>
                    <td>
                      <strong>
                        {pair.x}
                      </strong>
                    </td>
                    <td>
                      <strong>
                        {pair.y}
                      </strong>
                    </td>
                    <td
                      className={
                        getCorrelationClass(
                          pair.value
                        )
                      }
                    >
                      {pair.value !== null
                        ? formatNumber(
                            pair.value,
                            3
                          )
                        : "\u2014"}
                    </td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        ) : (
          <div className="empty-state compact-empty">
            Correlation data is not available for
            the selected variable pairs.
          </div>
        )}

      </div>

    );

  };


  const renderPCA = () => {

    if (!results?.pca) {
      return null;
    }

    const pcaData = results.pca;
    const features = pcaData.features || [];

    const explainedVariance =
      pcaData.explained_variance_ratio ||
      pcaData.explainedVariance ||
      pcaData.explained_variance ||
      [];

    const cumulativeVariance =
      pcaData.cumulative_explained_variance ||
      pcaData.cumulativeVariance ||
      pcaData.cumulative_variance ||
      [];

    const components =
      pcaData.components || [];

    const chartData = explainedVariance.map(
      (value, index) => ({
        component: `PC${index + 1}`,
        variance: Number(value) || 0,
      })
    );

    const hasValidData = chartData.length > 0 &&
      chartData.some((d) => d.variance > 0);

    return (
      <div className="two-column">

        <div className="analysis-card">
          <h2>Principal Component Analysis</h2>
          <p className="card-description">
            PCA reduces the selected variables into
            principal components while preserving
            maximum variance.
            {features.length > 0 &&
              ` Using: ${features.join(", ")}`}
          </p>

          {hasValidData ? (
            <ResponsiveContainer
              width="100%"
              height={320}
            >
              <BarChart
                data={chartData}
                margin={{
                  top: 20,
                  right: 20,
                  left: 10,
                  bottom: 20,
                }}
              >
                <CartesianGrid
                  strokeDasharray="3 3"
                />
                <XAxis dataKey="component" />
                <YAxis
                  tickFormatter={(value) =>
                    `${(value * 100).toFixed(0)}%`
                  }
                />
                <Tooltip
                  formatter={(value) =>
                    `${(Number(value) * 100).toFixed(2)}%`
                  }
                />
                <Bar
                  dataKey="variance"
                  name="Explained Variance"
                  fill="#2563eb"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          ) : (
            <div className="compact-empty">
              PCA could not be computed for the selected variables. This may be due to insufficient valid numeric data.
            </div>
          )}
        </div>

        <div className="analysis-card">
          <h2>Explained Variance</h2>

          {explainedVariance.length > 0 ? (
            <div className="variance-list">
              {explainedVariance.map(
                (value, index) => (
                  <div
                    className="variance-row"
                    key={index}
                  >
                    <span>PC{index + 1}</span>
                    <strong>
                      {formatNumber(
                        Number(value) * 100,
                        2
                      )}
                      %
                    </strong>
                  </div>
                )
              )}
            </div>
          ) : (
            <div className="compact-empty">
              No explained variance data.
            </div>
          )}

          {cumulativeVariance.length > 0 && (
            <div className="cumulative-box">
              <span>Cumulative Variance</span>
              <strong>
                {formatNumber(
                  Number(
                    cumulativeVariance[
                      cumulativeVariance.length - 1
                    ]
                  ) * 100,
                  2
                )}
                %
              </strong>
            </div>
          )}

          {components.length > 0 && (
            <div style={{ marginTop: 20 }}>
              <h3>Component Loadings</h3>
              <div className="table-wrapper">
                <table>
                  <thead>
                    <tr>
                      <th>Component</th>
                      <th>Loadings</th>
                    </tr>
                  </thead>
                  <tbody>
                    {components.map(
                      (component, index) => (
                        <tr key={index}>
                          <td>
                            PC{index + 1}
                          </td>
                          <td>
                            {Array.isArray(
                              component
                            )
                              ? component
                                  .map((v) =>
                                    formatNumber(
                                      v,
                                      3
                                    )
                                  )
                                  .join(" | ")
                              : "\u2014"}
                          </td>
                        </tr>
                      )
                    )}
                  </tbody>
                </table>
              </div>
            </div>
          )}
        </div>

      </div>

    );

  };


  const renderRegression = () => {

    if (!results?.regression) {
      return null;
    }

    const reg = results.regression;

    const features = reg.features || [];
    const target = reg.target || "Revenue";
    const coefficients = reg.coefficients || {};

    const coefficientRows = Object.entries(
      coefficients
    ).map(([feature, value]) => ({
      feature,
      coefficient: Number(value) || 0,
    }));

    const actualPersist =
      reg.actual_vs_predicted || [];

    const regressionChartData =
      actualPersist.length > 0
        ? actualPersist
            .slice(0, 100)
            .map((item) => ({
              actual:
                Number(item.actual) || 0,
              predicted:
                Number(item.predicted) || 0,
            }))
        : [];

    return (
      <div className="analysis-card">
        <h2>Multivariate Regression</h2>

        <p className="card-description">
          {features.length > 0
            ? `The model predicts ${target} using ${features.join(", ")}.`
            : "Regression uses the backend's feature set to predict the target variable."}
        </p>

        <div className="metrics-row">

          <Metric
            label="R\u00B2"
            value={formatNumber(
              reg.r_squared,
              4
            )}
          />

          <Metric
            label="MAE"
            value={formatNumber(
              reg.mae,
              2
            )}
          />

          <Metric
            label="RMSE"
            value={formatNumber(
              reg.rmse,
              2
            )}
          />

          <Metric
            label="Intercept"
            value={formatNumber(
              reg.intercept,
              4
            )}
          />

        </div>

        {coefficientRows.length > 0 && (
          <div>
            <h3>Model Coefficients</h3>
            <ResponsiveContainer
              width="100%"
              height={280}
            >
              <BarChart data={coefficientRows}>
                <CartesianGrid
                  strokeDasharray="3 3"
                />
                <XAxis dataKey="feature" />
                <YAxis />
                <Tooltip />
                <Bar
                  dataKey="coefficient"
                  name="Coefficient"
                  fill="#7c3aed"
                  radius={[4, 4, 0, 0]}
                />
              </BarChart>
            </ResponsiveContainer>
          </div>
        )}

        {regressionChartData.length > 0 && (
          <div>
            <h3>Actual vs Predicted</h3>
            <ResponsiveContainer
              width="100%"
              height={350}
            >
              <ScatterChart>
                <CartesianGrid />
                <XAxis
                  type="number"
                  dataKey="actual"
                  name="Actual"
                />
                <YAxis
                  type="number"
                  dataKey="predicted"
                  name="Predicted"
                />
                <ZAxis range={[30, 30]} />
                <Tooltip />
                <Scatter
                  name="Predictions"
                  data={regressionChartData}
                  fill="#2563eb"
                />
              </ScatterChart>
            </ResponsiveContainer>
          </div>
        )}

      </div>

    );

  };


  return (

    <div className="predictive-page">

      <div className="page-header">
        <div>
          <h1>Multivariate Analysis</h1>
          <p>
            Analyze relationships among multiple
            retail variables.
          </p>
        </div>
      </div>

      {renderSetup()}
      {renderDateRange()}

      {error && (
        <div className="error-box">
          <h3>Validation Error</h3>
          <p>{error}</p>
        </div>
      )}

      {renderActions()}

      {loading && (
        <div className="loading-box">
          <div className="loader"></div>
          <h3>Running multivariate analysis...</h3>
        </div>
      )}

      {!loading && results && (
        <>
          {renderSummary()}
          {renderScatterPlots()}
          {renderCorrelation()}
          {renderPCA()}
          {renderRegression()}
        </>
      )}

      {!loading && !results && (
        <div className="empty-state">
          Select variables and date range, then
          click "Run Analysis".
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
    return number.toFixed(digits);
  }

  if (Math.abs(number) >= 1000000) {
    return `${(number / 1000000).toFixed(2)}M`;
  }

  if (Math.abs(number) >= 1000) {
    return `${(number / 1000).toFixed(2)}K`;
  }

  return number.toLocaleString("en-IN", {
    maximumFractionDigits: 2,
  });

}


function Metric({ label, value }) {

  return (
    <div className="metric-box">
      <span>{label}</span>
      <strong>{value}</strong>
    </div>
  );

}


function extractScatterData(response) {

  if (!response) {
    return [];
  }

  const data = response.data ?? response;

  const points =
    data.points ??
    data.data ??
    (Array.isArray(data) ? data : []);

  if (!Array.isArray(points)) {
    return [];
  }

  return points
    .filter(
      (item) =>
        item &&
        Number.isFinite(Number(item.x)) &&
        Number.isFinite(Number(item.y))
    )
    .map((item) => ({
      x: Number(item.x),
      y: Number(item.y),
    }));

}


function getCorrelationClass(value) {

  const number = Number(value);

  if (!Number.isFinite(number)) {
    return "";
  }

  const abs = Math.abs(number);

  if (abs >= 0.7) {
    return "strong-correlation";
  }

  if (abs >= 0.4) {
    return "medium-correlation";
  }

  return "weak-correlation";

}


export default Multivariate;
