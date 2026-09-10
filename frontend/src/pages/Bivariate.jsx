import React, { useEffect, useState } from 'react'

import {
  ResponsiveContainer,
  ScatterChart,
  Scatter,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  BarChart,
  Bar
} from 'recharts'

import './Bivariate.css'

const API_BASE =
  import.meta.env.VITE_API_URL || 'http://127.0.0.1:5000'

const VARIABLES = [
  {
    value: 'Revenue',
    label: 'Revenue'
  },
  {
    value: 'Quantity',
    label: 'Quantity'
  },
  {
    value: 'UnitPrice',
    label: 'Unit Price'
  }
]

function formatNumber(value, decimals = 2) {
  if (
    value === null ||
    value === undefined ||
    Number.isNaN(Number(value))
  ) {
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

function Bivariate() {

  const [xField, setXField] = useState('Quantity')
  const [yField, setYField] = useState('Revenue')

  const [correlation, setCorrelation] = useState(null)
  const [scatterData, setScatterData] = useState([])
  const [regression, setRegression] = useState(null)
  const [productData, setProductData] = useState([])
  const [countryData, setCountryData] = useState([])

  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  const fetchJSON = async (url) => {

    const response = await fetch(url)

    const data = await response.json()

    if (!response.ok) {
      throw new Error(
        data.error || 'API request failed'
      )
    }

    return data
  }

  const loadAnalysis = async () => {

    const requestId = ++loadAnalysis.current

    try {

      setLoading(true)
      setError('')

      const [
        correlationResponse,
        scatterResponse,
        regressionResponse,
        productResponse,
        countryResponse,
      ] = await Promise.all([

        fetchJSON(
          `${API_BASE}/api/bivariate/correlation?x=${xField}&y=${yField}`
        ),

        fetchJSON(
          `${API_BASE}/api/bivariate/scatter?x=${xField}&y=${yField}&limit=1000`
        ),

        fetchJSON(
          `${API_BASE}/api/bivariate/regression?x=${xField}&y=${yField}`
        ),

        fetchJSON(
          `${API_BASE}/api/bivariate/product?limit=20`
        ),

        fetchJSON(
          `${API_BASE}/api/bivariate/country?limit=20`
        ),

      ])

      if (requestId !== loadAnalysis.current) return

      setCorrelation(correlationResponse)
      setScatterData(scatterResponse.data || [])
      setRegression(regressionResponse)
      setProductData(productResponse.data || [])
      setCountryData(countryResponse.data || [])

    } catch (err) {

      if (requestId !== loadAnalysis.current) return

      console.error(
        'Bivariate API error:',
        err
      )

      setError(
        err.message ||
        'Unable to load bivariate analysis'
      )

    } finally {

      if (requestId === loadAnalysis.current) {
        setLoading(false)
      }

    }
  }

  loadAnalysis.current = 0

  useEffect(() => {
    loadAnalysis()
  }, [xField, yField])


  const correlationValue =
    correlation?.pearson?.correlation


  return (

    <div className="analysis-page">

      {/* ==================================================
          HEADER
      =================================================== */}

      <div className="analysis-header">

        <div>

          <h1>Bivariate Analysis</h1>

          <p>
            Analyze relationships between two variables.
          </p>

        </div>


        <div className="bivariate-selectors">

          <div>

            <label>
              X Variable
            </label>

            <select
              value={xField}
              onChange={(e) =>
                setXField(e.target.value)
              }
            >

              {VARIABLES.map(
                (variable) => (

                  <option
                    key={variable.value}
                    value={variable.value}
                  >
                    {variable.label}
                  </option>

                )
              )}

            </select>

          </div>


          <div>

            <label>
              Y Variable
            </label>

            <select
              value={yField}
              onChange={(e) =>
                setYField(e.target.value)
              }
            >

              {VARIABLES.map(
                (variable) => (

                  <option
                    key={variable.value}
                    value={variable.value}
                  >
                    {variable.label}
                  </option>

                )
              )}

            </select>

          </div>

        </div>

      </div>


      {error && (

        <div className="analysis-error">

          <strong>
            Error:
          </strong>

          <span>
            {error}
          </span>

          <button
            onClick={loadAnalysis}
          >
            Retry
          </button>

        </div>

      )}


      {loading ? (

        <div className="analysis-loading">

          <div className="loading-spinner"></div>

          <p>
            Loading bivariate analysis...
          </p>

        </div>

      ) : (

        <>


          {/* ==================================================
              CORRELATION
          =================================================== */}

          <section className="analysis-section">

            <div className="section-heading">

              <div>

                <h2>
                  Correlation Analysis
                </h2>

                <p>
                  Relationship between {xField} and {yField}.
                </p>

              </div>

            </div>


            <div className="correlation-grid">

              <MetricCard
                label="Pearson Correlation"
                value={formatNumber(
                  correlation?.pearson?.correlation,
                  4
                )}
              />

              <MetricCard
                label="Pearson P-value"
                value={
                  correlation?.pearson?.p_value !== undefined
                    ? Number(
                        correlation.pearson.p_value
                      ).toExponential(4)
                    : '—'
                }
              />

              <MetricCard
                label="Spearman Correlation"
                value={formatNumber(
                  correlation?.spearman?.correlation,
                  4
                )}
              />

              <MetricCard
                label="Spearman P-value"
                value={
                  correlation?.spearman?.p_value !== undefined
                    ? Number(
                        correlation.spearman.p_value
                      ).toExponential(4)
                    : '—'
                }
              />

              <MetricCard
                label="Covariance"
                value={formatCompact(
                  correlation?.covariance
                )}
              />

              <MetricCard
                label="Observations"
                value={formatNumber(
                  correlation?.data_count,
                  0
                )}
              />

            </div>


            <div className="relationship-box">

              <span>
                Relationship strength
              </span>

              <strong>
                {getCorrelationLabel(
                  correlationValue
                )}
              </strong>

            </div>

          </section>


          {/* ==================================================
              SCATTER PLOT
          =================================================== */}

          <section className="analysis-section">

            <div className="section-heading">

              <div>

                <h2>
                  Scatter Plot
                </h2>

                <p>
                  {xField} versus {yField}.
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
                      right: 30,
                      bottom: 50,
                      left: 20
                    }}
                  >

                    <CartesianGrid />

                    <XAxis
                      type="number"
                      dataKey="x"
                      name={xField}
                      tickFormatter={
                        formatCompact
                      }
                    />

                    <YAxis
                      type="number"
                      dataKey="y"
                      name={yField}
                      tickFormatter={
                        formatCompact
                      }
                    />

                    <Tooltip
                      cursor={{
                        strokeDasharray: '3 3'
                      }}
                      formatter={(value, name, props) => [
                        formatNumber(value),
                        name
                      ]}
                      labelFormatter={(label, payload) => {
                        if (payload && payload.length > 0) {
                          const p = payload[0].payload;
                          return `${xField}: ${formatNumber(p.x)}`;
                        }
                        return '';
                      }}
                    />

                    <Scatter
                      name={`${xField} vs ${yField}`}
                      data={scatterData}
                    />

                  </ScatterChart>

                </ResponsiveContainer>

              </div>

            </div>

          </section>


          {/* ==================================================
              REGRESSION
          =================================================== */}

          <section className="analysis-section">

            <div className="section-heading">

              <div>

                <h2>
                  Linear Regression
                </h2>

                <p>
                  Linear relationship between {xField} and {yField}.
                </p>

              </div>

            </div>


            <div className="regression-grid">

              <MetricCard
                label="Slope"
                value={formatNumber(
                  regression?.regression?.slope,
                  6
                )}
              />

              <MetricCard
                label="Intercept"
                value={formatNumber(
                  regression?.regression?.intercept,
                  4
                )}
              />

              <MetricCard
                label="R-value"
                value={formatNumber(
                  regression?.regression?.r_value,
                  4
                )}
              />

              <MetricCard
                label="R²"
                value={formatNumber(
                  regression?.regression?.r_squared,
                  4
                )}
              />

              <MetricCard
                label="P-value"
                value={
                  regression?.regression?.p_value !== undefined
                    ? Number(
                        regression.regression.p_value
                      ).toExponential(4)
                    : '—'
                }
              />

              <MetricCard
                label="Standard Error"
                value={formatNumber(
                  regression?.regression?.std_error,
                  6
                )}
              />

            </div>


            <div className="equation-box">

              <span>
                Regression equation
              </span>

              <strong>

                {yField} ={' '}

                {formatNumber(
                  regression?.regression?.intercept,
                  4
                )}

                {' + '}

                {formatNumber(
                  regression?.regression?.slope,
                  4
                )}

                {' × '}

                {xField}

              </strong>

            </div>

          </section>


          {/* ==================================================
              PRODUCT ANALYSIS
          =================================================== */}

          <section className="analysis-section">

            <div className="section-heading">

              <div>

                <h2>
                  Product Quantity vs Revenue
                </h2>

                <p>
                  Relationship between product sales quantity
                  and revenue for the top products.
                </p>

              </div>

            </div>


            <div className="analysis-card">

              <div className="chart-wrapper">

                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >

                  <BarChart
                    data={productData}
                    margin={{
                      top: 20,
                      right: 20,
                      bottom: 90,
                      left: 20
                    }}
                  >

                    <CartesianGrid
                      strokeDasharray="3 3"
                    />

                    <XAxis
                      dataKey="product_id"
                      angle={-45}
                      textAnchor="end"
                    />

                    <YAxis />

                    <Tooltip />

                    <Bar
                      dataKey="revenue"
                      name="Revenue"
                    />

                  </BarChart>

                </ResponsiveContainer>

              </div>

            </div>

          </section>


          {/* ==================================================
              COUNTRY ANALYSIS
          =================================================== */}

          <section className="analysis-section">

            <div className="section-heading">

              <div>

                <h2>
                  Country Quantity vs Revenue
                </h2>

                <p>
                  Revenue comparison across countries.
                </p>

              </div>

            </div>


            <div className="analysis-card">

              <div className="chart-wrapper">

                <ResponsiveContainer
                  width="100%"
                  height="100%"
                >

                  <BarChart
                    data={countryData}
                    margin={{
                      top: 20,
                      right: 20,
                      bottom: 90,
                      left: 20
                    }}
                  >

                    <CartesianGrid
                      strokeDasharray="3 3"
                    />

                    <XAxis
                      dataKey="country"
                      angle={-45}
                      textAnchor="end"
                    />

                    <YAxis />

                    <Tooltip />

                    <Bar
                      dataKey="revenue"
                      name="Revenue"
                    />

                  </BarChart>

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
   COMPONENTS
============================================================ */

function MetricCard({
  label,
  value
}) {

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


function getCorrelationLabel(value) {

  if (
    value === null ||
    value === undefined
  ) {
    return '—'
  }

  const absolute = Math.abs(
    Number(value)
  )

  if (absolute >= 0.8) {
    return 'Very Strong'
  }

  if (absolute >= 0.6) {
    return 'Strong'
  }

  if (absolute >= 0.4) {
    return 'Moderate'
  }

  if (absolute >= 0.2) {
    return 'Weak'
  }

  return 'Very Weak / None'
}

export default Bivariate