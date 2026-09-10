import {
  LayoutDashboard,
  BarChart3,
  GitBranch,
  Brain,
  ChevronDown,
  ChevronRight,
  Activity,
  TrendingUp,
  LineChart,
  Waves,
  Boxes,
  Package,
  LayoutGrid,
} from "lucide-react";

import { useState } from "react";

import "./Sidebar.css";

function Sidebar({ activePage, setActivePage }) {
  const [predictiveOpen, setPredictiveOpen] = useState(true);
  const [timeSeriesOpen, setTimeSeriesOpen] = useState(true);
  const [inventoryOpen, setInventoryOpen] = useState(true);

  const selectPage = (page) => {
    setActivePage(page);
  };

  return (
    <aside className="sidebar">

      <div className="sidebar-logo">
        <div className="logo-icon">
          <BarChart3 size={24} />
        </div>

        <div>
          <h2>Retail IQ</h2>
          <span>Demand Intelligence</span>
        </div>
      </div>


      <nav className="sidebar-nav">

        {/* DASHBOARD */}

        <button
          className={`nav-item ${
            activePage === "dashboard" ? "active" : ""
          }`}
          onClick={() => selectPage("dashboard")}
        >
          <LayoutDashboard size={19} />
          <span>Dashboard</span>
        </button>


        {/* UNIVARIATE */}

        <button
          className={`nav-item ${
            activePage === "univariate" ? "active" : ""
          }`}
          onClick={() => selectPage("univariate")}
        >
          <Activity size={19} />
          <span>Univariate</span>
        </button>


        {/* BIVARIATE */}

        <button
          className={`nav-item ${
            activePage === "bivariate" ? "active" : ""
          }`}
          onClick={() => selectPage("bivariate")}
        >
          <GitBranch size={19} />
          <span>Bivariate</span>
        </button>


        {/* INVENTORY */}

        <div className="nav-group">

          <button
            className="nav-item group-header"
            onClick={() =>
              setInventoryOpen(!inventoryOpen)
            }
          >
            <Boxes size={19} />

            <span>Inventory</span>

            {inventoryOpen ? (
              <ChevronDown size={16} />
            ) : (
              <ChevronRight size={16} />
            )}
          </button>

          {inventoryOpen && (
            <div className="submenu">

              <button
                className={`submenu-item ${
                  activePage === "abc" ? "active" : ""
                }`}
                onClick={() => selectPage("abc")}
              >
                <Package size={16} />
                ABC Analysis
              </button>

              <button
                className={`submenu-item ${
                  activePage === "xyz" ? "active" : ""
                }`}
                onClick={() => selectPage("xyz")}
              >
                <Activity size={16} />
                XYZ Analysis
              </button>

              <button
                className={`submenu-item ${
                  activePage === "abc-xyz" ? "active" : ""
                }`}
                onClick={() => selectPage("abc-xyz")}
              >
                <LayoutGrid size={16} />
                ABC-XYZ Matrix
              </button>

            </div>
          )}

        </div>


        {/* PREDICTIVE */}

        <div className="nav-group">

          <button
            className="nav-item group-header"
            onClick={() =>
              setPredictiveOpen(!predictiveOpen)
            }
          >
            <Brain size={19} />

            <span>Predictive</span>

            {predictiveOpen ? (
              <ChevronDown size={16} />
            ) : (
              <ChevronRight size={16} />
            )}
          </button>


          {predictiveOpen && (
            <div className="submenu">

              {/* MULTIVARIATE */}

              <button
                className={`submenu-item ${
                  activePage === "multivariate"
                    ? "active"
                    : ""
                }`}
                onClick={() =>
                  selectPage("multivariate")
                }
              >
                <TrendingUp size={16} />
                Multivariate
              </button>


              {/* TIME SERIES */}

              <button
                className="submenu-item time-series-header"
                onClick={() =>
                  setTimeSeriesOpen(!timeSeriesOpen)
                }
              >
                <LineChart size={16} />

                <span>Time Series</span>

                {timeSeriesOpen ? (
                  <ChevronDown size={15} />
                ) : (
                  <ChevronRight size={15} />
                )}
              </button>


              {timeSeriesOpen && (
                <div className="nested-submenu">

                  <button
                    className={`nested-item ${
                      activePage === "arima"
                        ? "active"
                        : ""
                    }`}
                    onClick={() =>
                      selectPage("arima")
                    }
                  >
                    <Waves size={14} />
                    ARIMA
                  </button>


                  <button
                    className={`nested-item ${
                      activePage === "sarima"
                        ? "active"
                        : ""
                    }`}
                    onClick={() =>
                      selectPage("sarima")
                    }
                  >
                    <Waves size={14} />
                    SARIMA
                  </button>


                  <button
                    className={`nested-item ${
                      activePage === "holt-winters"
                        ? "active"
                        : ""
                    }`}
                    onClick={() =>
                      selectPage("holt-winters")
                    }
                  >
                    <Waves size={14} />
                    Holt-Winters
                  </button>

                </div>
              )}

            </div>
          )}

        </div>

      </nav>


      <div className="sidebar-footer">
        <span>Retail Analytics</span>
        <small>Real-time Intelligence</small>
      </div>

    </aside>
  );
}

export default Sidebar;