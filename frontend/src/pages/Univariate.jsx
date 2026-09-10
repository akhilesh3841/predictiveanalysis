import React, { useEffect, useState } from 'react'
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
  ReferenceLine
} from 'recharts'

import './Univariate.css'

const API_BASE =
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000'

const VARIABLES = [
  {
    value: 'Revenue',
    label: 'Revenue',
    description: 'Revenue generated per transaction'
  },
  {
    value: 'Quantity',
    label: 'Quantity',
    description: 'Number of units sold'
  },
  {
    value: 'UnitPrice',
    label: 'Unit Price',
    description: 'Price per unit'
  }
]

function formatNumber(value, decimals = 2) {
  if (value === null || value === undefined || Number.isNaN(Number(value))) {
    return '—'
  }

  return Number(value).toLocaleString('en-IN', {
    maximumFractionDigits: decimals
  })
}

function formatCompact(value) {
  if (value === null || value === undefined) {
    return '—'
  }

  const number = Number(value)

  if (Math.abs(number) >= 1000000) {
    return `${(number / 1000000).toFixed(2)}M`
  }

  if (Math.abs(number) >= 1000) {
    return `${(number / 1000).toFixed(2)}K`
  }

  return formatNumber(number)
}

function Univariate() {
  const [field, setField] = useState('Revenue')

  const [summary, setSummary] = useState(null)
  const [distribution, setDistribution] = useState([])
  const [distributionMeta, setDistributionMeta] = useState(null)
  const [outliers, setOutliers] = useState(null)
  const [normality, setNormality] = useState(null)
  const [qqData, setQqData] = useState([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchJSON = async (url) => {
    const response = await fetch(url)

    const data = await response.json()

    if (!response.ok) {
      throw new Error(data.error || 'API request failed')
    }

    return data
  }

  const loadAnalysis = async () => {

    const requestId = ++loadAnalysis.current

    try {
      setLoading(true)
      setError('')

      const [
        summaryResponse,
        distributionResponse,
        outlierResponse,
        normalityResponse,
        qqResponse
      ] = await Promise.all([
        fetchJSON(
          `${API_BASE}/api/univariate/summary?field=${field}`
        ),

        fetchJSON(
          `${API_BASE}/api/univariate/distribution?field=${field}&bins=20`
        ),

        fetchJSON(
          `${API_BASE}/api/univariate/outliers?field=${field}&limit=100`
        ),

        fetchJSON(
          `${API_BASE}/api/univariate/normality?field=${field}`
        ),

        fetchJSON(
          `${API_BASE}/api/univariate/qq-plot?field=${field}&sample_size=100`
        )
      ])

      if (requestId !== loadAnalysis.current) return

      setSummary(summaryResponse)
      setDistribution(
        distributionResponse.distribution || []
      )
      setDistributionMeta({
        log_scale: distributionResponse.log_scale || false,
        bins: distributionResponse.bins
      })
      setOutliers(outlierResponse)
      setNormality(normalityResponse)
      setQqData(qqResponse.qq_data || [])

    } catch (err) {

      if (requestId !== loadAnalysis.current) return

      console.error('Univariate API error:', err)
      setError(err.message || 'Unable to load univariate analysis')
    } finally {

      if (requestId === loadAnalysis.current) {
        setLoading(false)
      }
    }
  }

  loadAnalysis.current = 0

  useEffect(() => {
    loadAnalysis()
  }, [field])

  const statistics = summary?.summary

  return (
    <div className="analysis-page">

      {/* =====================================================
          HEADER
      ====================================================== */}

      <div className="analysis-header">

        <div>
          <h1>Univariate Analysis</h1>

          <p>
            Analyze the distribution and statistical properties
            of a single variable.
          </p>
        </div>

        <div className="variable-selector">

          <label htmlFor="univariate-variable">
            Variable
          </label>

          <select
            id="univariate-variable"
            value={field}
            onChange={(e) => setField(e.target.value)}
          >
            {VARIABLES.map((variable) => (
              <option
                key={variable.value}
                value={variable.value}
              >
                {variable.label}
              </option>
            ))}
          </select>

        </div>

      </div>

      {/* =====================================================
          ERROR
      ====================================================== */}

      {error && (
        <div className="analysis-error">
          <strong>Error:</strong> {error}

          <button onClick={loadAnalysis}>
            Retry
          </button>
        </div>
      )}

      {/* =====================================================
          LOADING
      ====================================================== */}

      {loading ? (

        <div className="analysis-loading">
          <div className="loading-spinner"></div>
          <p>Loading {field} analysis...</p>
        </div>

      ) : (

        <>

          {/* =================================================
              DATA INFO
          ================================================== */}

          <div className="analysis-info">

            <div>
              <span>Selected Variable</span>
              <strong>{field}</strong>
            </div>

            <div>
              <span>Observations</span>
              <strong>
                {formatNumber(summary?.data_count, 0)}
              </strong>
            </div>

            <div>
              <span>Analysis Type</span>
              <strong>Univariate</strong>
            </div>

          </div>


          {/* =================================================
              STATISTICAL SUMMARY
          ================================================== */}

          <section className="analysis-section">

            <div className="section-heading">
              <div>
                <h2>Statistical Summary</h2>

                <p>
                  Descriptive statistics for {field}.
                </p>
              </div>
            </div>

            <div className="statistics-grid">

              <StatCard
                label="Count"
                value={formatNumber(
                  statistics?.count,
                  0
                )}
              />

              <StatCard
                label="Mean"
                value={formatNumber(
                  statistics?.mean
                )}
              />

              <StatCard
                label="Median"
                value={formatNumber(
                  statistics?.median
                )}
              />

              <StatCard
                label="Standard Deviation"
                value={formatNumber(
                  statistics?.std
                )}
              />

              <StatCard
                label="Variance"
                value={formatCompact(
                  statistics?.variance
                )}
              />

              <StatCard
                label="Minimum"
                value={formatNumber(
                  statistics?.min
                )}
              />

              <StatCard
                label="Maximum"
                value={formatNumber(
                  statistics?.max
                )}
              />

              <StatCard
                label="Q1"
                value={formatNumber(
                  statistics?.q1
                )}
              />

              <StatCard
                label="Q3"
                value={formatNumber(
                  statistics?.q3
                )}
              />

              <StatCard
                label="IQR"
                value={formatNumber(
                  statistics?.iqr
                )}
              />

              <StatCard
                label="Skewness"
                value={formatNumber(
                  statistics?.skewness
                )}
              />

              <StatCard
                label="Kurtosis"
                value={formatCompact(
                  statistics?.kurtosis
                )}
              />

            </div>

          </section>


          {/* =================================================
              DISTRIBUTION
          ================================================== */}

          <section className="analysis-section">

            <div className="section-heading">

              <div>
                <h2>Distribution</h2>

                <p>
                  Frequency distribution of {field}.
                </p>
              </div>

            </div>

            {distributionMeta?.log_scale && (
              <p className="distribution-note">
                Highly skewed data detected. Values are
                binned on a logarithmic scale to
                accurately represent the distribution.
              </p>
            )}

            <div className="analysis-card">

              <div className="chart-wrapper">

                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >

                  <BarChart
                    data={distribution}
                    margin={{
                      top: 20,
                      right: 20,
                      left: 10,
                      bottom: 60
                    }}
                  >

                    <CartesianGrid
                      strokeDasharray="3 3"
                    />

                    <XAxis
                      dataKey="bin_center"
                      tickFormatter={(value) =>
                        formatCompact(value)
                      }
                      angle={-35}
                      textAnchor="end"
                      label={{
                        value: field,
                        position: 'insideBottom',
                        offset: -5,
                        style: { fontSize: 12, fill: '#6b7280' }
                      }}
                    />

                    <YAxis
                      label={{
                        value: 'Frequency',
                        angle: -90,
                        position: 'insideLeft',
                        style: { fontSize: 12, fill: '#6b7280' }
                      }}
                    />

                    <Tooltip
                      formatter={(value, name, props) => [
                        formatNumber(value, 0),
                        'Frequency'
                      ]}
                      labelFormatter={(label, payload) => {
                        if (payload && payload.length > 0) {
                          const item = payload[0].payload;
                          return `Range: ${formatCompact(item.bin_start)} - ${formatCompact(item.bin_end)}`;
                        }
                        return `Bin: ${formatNumber(label)}`;
                      }}
                    />

                    <Bar
                      dataKey="count"
                      name="Frequency"
                      fill="#2563eb"
                      radius={[4, 4, 0, 0]}
                    />

                  </BarChart>

                </ResponsiveContainer>

              </div>

            </div>

          </section>


          {/* =================================================
              OUTLIERS
          ================================================== */}

          <section className="analysis-section">

            <div className="section-heading">

              <div>
                <h2>Outlier Analysis</h2>

                <p>
                  IQR-based detection of unusually high
                  or low observations.
                </p>
              </div>

            </div>

            <div className="outlier-grid">

              <MetricCard
                label="Total Outliers"
                value={formatNumber(
                  outliers?.total_outliers,
                  0
                )}
              />

              <MetricCard
                label="Lower Outliers"
                value={formatNumber(
                  outliers?.lower_outliers,
                  0
                )}
              />

              <MetricCard
                label="Upper Outliers"
                value={formatNumber(
                  outliers?.upper_outliers,
                  0
                )}
              />

              <MetricCard
                label="Lower Bound"
                value={formatNumber(
                  outliers?.lower_bound
                )}
              />

              <MetricCard
                label="Upper Bound"
                value={formatNumber(
                  outliers?.upper_bound
                )}
              />

            </div>


            {outliers?.outliers?.length > 0 && (

              <div className="analysis-card outlier-table-card">

                <h3>Detected Outliers</h3>

                <div className="table-wrapper">

                  <table>

                    <thead>
                      <tr>
                        <th>#</th>
                        <th>Value</th>
                        <th>Type</th>
                      </tr>
                    </thead>

                    <tbody>

                      {outliers.outliers.map(
                        (item, index) => (

                          <tr key={index}>

                            <td>
                              {index + 1}
                            </td>

                            <td>
                              {formatNumber(
                                item.value
                              )}
                            </td>

                            <td>

                              <span
                                className={`outlier-badge ${
                                  item.type === 'upper'
                                    ? 'upper'
                                    : 'lower'
                                }`}
                              >
                                {item.type}
                              </span>

                            </td>

                          </tr>

                        )
                      )}

                    </tbody>

                  </table>

                </div>

              </div>

            )}

          </section>


          {/* =================================================
              NORMALITY
          ================================================== */}

          <section className="analysis-section">

            <div className="section-heading">

              <div>
                <h2>Normality Test</h2>

                <p>
                  Statistical tests for determining whether
                  the selected variable follows a normal distribution.
                </p>
              </div>

            </div>

            <div className="normality-grid">

              <NormalityCard
                title="Shapiro-Wilk"
                result={normality?.test?.shapiro}
              />

              <NormalityCard
                title="D'Agostino K²"
                result={normality?.test?.dagostino}
              />

            </div>

            <div className="normality-note">

              <strong>Interpretation:</strong>

              <span>
                A p-value below 0.05 indicates that the
                normality assumption is rejected.
              </span>

            </div>

          </section>


          {/* =================================================
              Q-Q PLOT
          ================================================== */}

          <section className="analysis-section">

            <div className="section-heading">

              <div>

                <h2>Q-Q Plot</h2>

                <p>
                  Comparison between theoretical normal
                  quantiles and observed values.
                </p>

              </div>

            </div>

            <div className="analysis-card">

              <div className="chart-wrapper">

                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >

                  <ScatterChart
                    margin={{
                      top: 20,
                      right: 20,
                      bottom: 40,
                      left: 20
                    }}
                  >

                    <CartesianGrid />

                    <XAxis
                      type="number"
                      dataKey="theoretical"
                      name="Theoretical"
                    />

                    <YAxis
                      type="number"
                      dataKey="actual"
                      name="Actual"
                    />

                    <Tooltip
                      cursor={{
                        strokeDasharray: '3 3'
                      }}
                    />

                    <Scatter
                      name="Q-Q"
                      data={qqData}
                    />

                    <ReferenceLine
                      segment={[
                        {
                          x: -3,
                          y: -3
                        },
                        {
                          x: 3,
                          y: 3
                        }
                      ]}
                      strokeDasharray="5 5"
                    />

                  </ScatterChart>

                </ResponsiveContainer>

              </div>

            </div>

          </section>

        </>

      )}

    </div>
  )
}


/* ============================================================
   SMALL COMPONENTS
============================================================ */

function StatCard({ label, value }) {
  return (
    <div className="stat-card">

      <span className="stat-label">
        {label}
      </span>

      <strong className="stat-value">
        {value}
      </strong>

    </div>
  )
}


function MetricCard({ label, value }) {
  return (
    <div className="metric-card">

      <span>
        {label}
      </span>

      <strong>
        {value}
      </strong>

    </div>
  )
}


function NormalityCard({ title, result }) {

  const isNormal = result?.is_normal

  return (
    <div className="normality-card">

      <h3>{title}</h3>

      <div
        className={`normality-status ${
          isNormal ? 'normal' : 'not-normal'
        }`}
      >
        {isNormal
          ? 'Approximately Normal'
          : 'Not Normally Distributed'}
      </div>

      <div className="normality-values">

        <div>
          <span>Statistic</span>

          <strong>
            {formatNumber(
              result?.statistic,
              6
            )}
          </strong>
        </div>

        <div>
          <span>P-value</span>

          <strong>
            {result?.p_value !== undefined
              ? Number(result.p_value).toExponential(4)
              : '—'}
          </strong>
        </div>

      </div>

    </div>
  )
}

export default Univariate