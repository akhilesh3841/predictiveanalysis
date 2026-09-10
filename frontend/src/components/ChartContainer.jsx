import React from 'react'
import './ChartContainer.css'

const ChartContainer = ({ title, subtitle, children, height = 400 }) => {
  return (
    <div className="chart-container">
      <div className="chart-header">
        <div>
          <h2 className="chart-title">{title}</h2>
          {subtitle && <p className="chart-subtitle">{subtitle}</p>}
        </div>
      </div>
      <div className="chart-content" style={{ height: `${height}px` }}>
        {children}
      </div>
    </div>
  )
}

export default ChartContainer
