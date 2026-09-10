import axios from "axios";

const API_BASE_URL =
  import.meta.env.VITE_API_BASE_URL || "http://localhost:5000";

const api = axios.create({
  baseURL: API_BASE_URL,
  timeout: 120000,
  headers: {
    "Content-Type": "application/json",
  },
});

export const healthCheck = () =>
  api.get("/health");


// ===============================
// DASHBOARD
// ===============================

export const getKPIs = () =>
  api.get("/api/dashboard/kpis");

export const getMonthlyRevenue = () =>
  api.get("/api/dashboard/monthly-revenue");

export const getTopProducts = (limit = 10) =>
  api.get(`/api/dashboard/top-products?limit=${limit}`);

export const getTopCountries = (limit = 15) =>
  api.get(`/api/dashboard/top-countries?limit=${limit}`);

export const getDataSummary = () =>
  api.get("/api/data/summary");

export const getDateRange = () =>
  api.get("/api/data/date-range");


// ===============================
// UNIVARIATE
// ===============================

export const getUnivariateSummary = (field) =>
  api.get(`/api/univariate/summary?field=${field}`);

export const getDistribution = (field, bins = 20) =>
  api.get(
    `/api/univariate/distribution?field=${field}&bins=${bins}`
  );

export const getOutliers = (field, limit = 100) =>
  api.get(
    `/api/univariate/outliers?field=${field}&limit=${limit}`
  );

export const getNormality = (field) =>
  api.get(`/api/univariate/normality?field=${field}`);

export const getQQPlot = (field, sampleSize = 100) =>
  api.get(
    `/api/univariate/qq-plot?field=${field}&sample_size=${sampleSize}`
  );


// ===============================
// BIVARIATE
// ===============================

export const getCorrelation = (x, y) =>
  api.get(`/api/bivariate/correlation?x=${x}&y=${y}`);

export const getScatter = (x, y) =>
  api.get(`/api/bivariate/scatter?x=${x}&y=${y}`);

export const getRegression = (x, y) =>
  api.get(`/api/bivariate/regression?x=${x}&y=${y}`);

export const getProductBivariate = () =>
  api.get("/api/bivariate/product");

export const getCountryBivariate = () =>
  api.get("/api/bivariate/country");


// ===============================
// MULTIVARIATE
// ===============================

export const getMultivariateSummary = () =>
  api.get("/api/multivariate/summary");

export const getMultivariateCorrelation = (variables, startDate, endDate) => {
  const vars = Array.isArray(variables) ? variables.join(",") : "";
  const params = new URLSearchParams({ variables: vars });
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  return api.get(`/api/multivariate/correlation?${params.toString()}`);
};

export const getPCA = (components = 2, variables, startDate, endDate) => {
  const vars = Array.isArray(variables) ? variables.join(",") : "";
  const params = new URLSearchParams({ n_components: components, variables: vars });
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  return api.get(`/api/multivariate/pca?${params.toString()}`);
};

export const getMultivariateRegression = (target, features, startDate, endDate) => {
  const params = new URLSearchParams();
  if (target) params.set("target", target);
  if (features && Array.isArray(features)) {
    params.set("features", features.join(","));
  }
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  return api.get(`/api/multivariate/regression?${params.toString()}`);
};

export const getMultivariateScatter = (x, y, startDate, endDate) => {
  const params = new URLSearchParams({ x, y });
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  return api.get(`/api/multivariate/scatter?${params.toString()}`);
};


// ===============================
// TIME SERIES
// ===============================

export const getARIMA = (
  metric = "Revenue",
  forecastDays = 30,
  startDate = null,
  endDate = null
) => {
  const params = new URLSearchParams({ metric, forecast_days: forecastDays });
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  return api.get(`/api/forecast/arima?${params.toString()}`);
};

export const getSARIMA = (
  metric = "Revenue",
  forecastDays = 30,
  startDate = null,
  endDate = null
) => {
  const params = new URLSearchParams({ metric, forecast_days: forecastDays });
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  return api.get(`/api/forecast/sarima?${params.toString()}`);
};

export const getHoltWinters = (
  metric = "Revenue",
  forecastDays = 30,
  startDate = null,
  endDate = null
) => {
  const params = new URLSearchParams({ metric, forecast_days: forecastDays });
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  return api.get(`/api/forecast/holt-winters?${params.toString()}`);
};

export const compareForecastModels = (
  metric = "Revenue",
  forecastDays = 30,
  startDate = null,
  endDate = null
) => {
  const params = new URLSearchParams({ metric, forecast_days: forecastDays });
  if (startDate) params.set("start_date", startDate);
  if (endDate) params.set("end_date", endDate);
  return api.get(`/api/forecast/compare?${params.toString()}`);
};


// ===============================
// INVENTORY ANALYSIS (ABC / XYZ)
// ===============================

export const getABCAnalysis = (options = {}) => {
  const params = new URLSearchParams();
  if (options.startDate) params.set("start_date", options.startDate);
  if (options.endDate) params.set("end_date", options.endDate);
  if (options.thresholdA !== null && options.thresholdA !== undefined)
    params.set("threshold_a", options.thresholdA);
  if (options.thresholdB !== null && options.thresholdB !== undefined)
    params.set("threshold_b", options.thresholdB);
  return api.get(`/api/analysis/abc?${params.toString()}`);
};

export const getXYZAnalysis = (options = {}) => {
  const params = new URLSearchParams();
  if (options.startDate) params.set("start_date", options.startDate);
  if (options.endDate) params.set("end_date", options.endDate);
  if (options.period) params.set("period", options.period);
  if (options.cvX !== null && options.cvX !== undefined)
    params.set("cv_x", options.cvX);
  if (options.cvY !== null && options.cvY !== undefined)
    params.set("cv_y", options.cvY);
  return api.get(`/api/analysis/xyz?${params.toString()}`);
};

export const getXYZTrend = (productId, options = {}) => {
  const params = new URLSearchParams({ product_id: productId });
  if (options.period) params.set("period", options.period);
  if (options.startDate) params.set("start_date", options.startDate);
  if (options.endDate) params.set("end_date", options.endDate);
  return api.get(`/api/analysis/xyz/trend?${params.toString()}`);
};

export const getABCXYZMatrix = (options = {}) => {
  const params = new URLSearchParams();
  if (options.startDate) params.set("start_date", options.startDate);
  if (options.endDate) params.set("end_date", options.endDate);
  if (options.thresholdA !== null && options.thresholdA !== undefined)
    params.set("threshold_a", options.thresholdA);
  if (options.thresholdB !== null && options.thresholdB !== undefined)
    params.set("threshold_b", options.thresholdB);
  if (options.cvX !== null && options.cvX !== undefined)
    params.set("cv_x", options.cvX);
  if (options.cvY !== null && options.cvY !== undefined)
    params.set("cv_y", options.cvY);
  return api.get(`/api/analysis/abc-xyz?${params.toString()}`);
};

export default api;