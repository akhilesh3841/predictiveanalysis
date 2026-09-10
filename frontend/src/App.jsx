import { useState } from "react";

import Sidebar from "./components/Sidebar";
import Dashboard from "./pages/Dashboard";
import Univariate from "./pages/Univariate";
import Bivariate from "./pages/Bivariate";
import Multivariate from "./pages/Multivariate";
import TimeSeries from "./pages/TimeSeries";
import ABC from "./pages/ABC";
import XYZ from "./pages/XYZ";
import ABCXYZ from "./pages/ABCXYZ";

import "./App.css";

function App() {
  const [activePage, setActivePage] = useState("dashboard");

  const renderPage = () => {
    switch (activePage) {
      case "dashboard":
        return <Dashboard />;

      case "univariate":
        return <Univariate />;

      case "bivariate":
        return <Bivariate />;

      case "multivariate":
        return <Multivariate />;

      case "abc":
        return <ABC />;

      case "xyz":
        return <XYZ />;

      case "abc-xyz":
        return <ABCXYZ />;

      case "arima":
      case "sarima":
      case "holt-winters":
        return <TimeSeries model={activePage} />;

      default:
        return <Dashboard />;
    }
  };

  return (
    <div className="app">
      <Sidebar
        activePage={activePage}
        setActivePage={setActivePage}
      />

      <main className="main-content">
        {renderPage()}
      </main>
    </div>
  );
}

export default App;