import React from 'react'
import './KPICard.css'

const KPICard = ({ icon, label, value, color }) => {
  return (
    <div className="kpi-card">
      <div className="kpi-icon" style={{ color }}>
        {icon}
      </div>
      <div className="kpi-content">
        <p className="kpi-label">{label}</p>
        <h3 className="kpi-value">{value}</h3>
      </div>
    </div>
  )
}

export default KPICard
