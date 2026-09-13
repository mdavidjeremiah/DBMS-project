"use client"

import React, { useState, useMemo } from "react"
import { TrendingUp, Activity, Calendar, DollarSign, ShoppingBag } from "lucide-react"

export interface DataPoint {
  date: string
  label: string
  salesRevenue: number
  transactions: number
}

interface ContinuousStatGraphProps {
  initialData?: DataPoint[]
}

const DEFAULT_DATA: DataPoint[] = [
  { date: "2026-09-07", label: "Mon, Sep 7", salesRevenue: 2850000, transactions: 14 },
  { date: "2026-09-08", label: "Tue, Sep 8", salesRevenue: 4120000, transactions: 22 },
  { date: "2026-09-09", label: "Wed, Sep 9", salesRevenue: 3650000, transactions: 19 },
  { date: "2026-09-10", label: "Thu, Sep 10", salesRevenue: 5400000, transactions: 28 },
  { date: "2026-09-11", label: "Fri, Sep 11", salesRevenue: 6980000, transactions: 36 },
  { date: "2026-09-12", label: "Sat, Sep 12", salesRevenue: 8250000, transactions: 44 },
  { date: "2026-09-13", label: "Sun, Sep 13 (Today)", salesRevenue: 7420000, transactions: 38 },
]

export function ContinuousStatGraph({ initialData = DEFAULT_DATA }: ContinuousStatGraphProps) {
  const [metric, setMetric] = useState<"salesRevenue" | "transactions">("salesRevenue")
  const [hoveredPoint, setHoveredPoint] = useState<{ point: DataPoint; x: number; y: number } | null>(null)

  const data = initialData.length > 0 ? initialData : DEFAULT_DATA

  // Graph Dimensions
  const width = 800
  const height = 300
  const paddingX = 50
  const paddingY = 40

  const { points, maxValue, minValue, total, avg, peak } = useMemo(() => {
    const values = data.map((d) => d[metric])
    const max = Math.max(...values, 1)
    const min = Math.min(...values)
    const tot = values.reduce((acc, v) => acc + v, 0)
    const average = Math.round(tot / values.length)
    const peakIdx = values.indexOf(max)

    const pts = data.map((d, index) => {
      const x = paddingX + (index / (data.length - 1)) * (width - paddingX * 2)
      // Normalize y
      const normalizedY = (d[metric] - 0) / (max * 1.15)
      const y = height - paddingY - normalizedY * (height - paddingY * 2)
      return { x, y, data: d }
    })

    return {
      points: pts,
      maxValue: max,
      minValue: min,
      total: tot,
      avg: average,
      peak: { value: max, point: data[peakIdx] }
    }
  }, [data, metric, width, height, paddingX, paddingY])

  // Generate Smooth Cubic Bezier Path
  const linePath = useMemo(() => {
    if (points.length === 0) return ""
    let d = `M ${points[0].x} ${points[0].y}`
    for (let i = 0; i < points.length - 1; i++) {
      const p0 = points[i]
      const p1 = points[i + 1]
      const cpX1 = p0.x + (p1.x - p0.x) / 2
      const cpY1 = p0.y
      const cpX2 = p0.x + (p1.x - p0.x) / 2
      const cpY2 = p1.y
      d += ` C ${cpX1} ${cpY1}, ${cpX2} ${cpY2}, ${p1.x} ${p1.y}`
    }
    return d
  }, [points])

  // Area under the curve
  const areaPath = useMemo(() => {
    if (points.length === 0) return ""
    const first = points[0]
    const last = points[points.length - 1]
    const baselineY = height - paddingY
    return `${linePath} L ${last.x} ${baselineY} L ${first.x} ${baselineY} Z`
  }, [linePath, points, height, paddingY])

  return (
    <div className="rounded-3xl border border-slate-200 bg-white p-6 shadow-xl dark:border-slate-800 dark:bg-slate-900">
      {/* Header & Controls */}
      <div className="flex flex-col gap-4 sm:flex-row sm:items-center sm:justify-between border-b border-slate-100 pb-5 dark:border-slate-800">
        <div>
          <div className="flex items-center gap-2 text-xs font-bold uppercase tracking-wider text-orange-600 dark:text-orange-400">
            <Activity className="h-4 w-4" />
            <span>Continuous Performance Plotted Graph</span>
          </div>
          <h2 className="mt-1 text-2xl font-black tracking-tight text-slate-900 dark:text-white">
            {metric === "salesRevenue" ? "Continuous Sales Revenue Flow" : "Continuous Transactions Density"}
          </h2>
          <p className="text-xs text-slate-500">
            Real-time continuous spline curve plotting node values across operating cycles.
          </p>
        </div>

        {/* Metric Switcher */}
        <div className="flex items-center gap-1.5 rounded-2xl bg-slate-100 p-1.5 dark:bg-slate-800">
          <button
            type="button"
            onClick={() => setMetric("salesRevenue")}
            className={`flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-bold transition-all ${
              metric === "salesRevenue"
                ? "bg-gradient-to-r from-orange-600 to-amber-600 text-white shadow-md shadow-orange-600/25"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white"
            }`}
          >
            <DollarSign className="h-3.5 w-3.5" />
            Revenue (UGX)
          </button>
          <button
            type="button"
            onClick={() => setMetric("transactions")}
            className={`flex items-center gap-1.5 rounded-xl px-3 py-2 text-xs font-bold transition-all ${
              metric === "transactions"
                ? "bg-gradient-to-r from-orange-600 to-amber-600 text-white shadow-md shadow-orange-600/25"
                : "text-slate-600 hover:text-slate-900 dark:text-slate-300 dark:hover:text-white"
            }`}
          >
            <ShoppingBag className="h-3.5 w-3.5" />
            Order Count
          </button>
        </div>
      </div>

      {/* KPI Highlight Strip */}
      <div className="my-5 grid grid-cols-3 gap-3">
        <div className="rounded-2xl border border-slate-100 bg-slate-50/70 p-3.5 dark:border-slate-800/80 dark:bg-slate-950/50">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">Period Aggregate</span>
          <strong className="text-lg font-black text-slate-900 dark:text-white">
            {metric === "salesRevenue" ? `UGX ${total.toLocaleString()}` : `${total.toLocaleString()} sales`}
          </strong>
        </div>
        <div className="rounded-2xl border border-slate-100 bg-slate-50/70 p-3.5 dark:border-slate-800/80 dark:bg-slate-950/50">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">Daily Mean</span>
          <strong className="text-lg font-black text-orange-600 dark:text-orange-400">
            {metric === "salesRevenue" ? `UGX ${avg.toLocaleString()}` : `${avg.toLocaleString()} / day`}
          </strong>
        </div>
        <div className="rounded-2xl border border-slate-100 bg-slate-50/70 p-3.5 dark:border-slate-800/80 dark:bg-slate-950/50">
          <span className="text-[11px] font-semibold text-slate-500 uppercase tracking-wider block">Plotted Peak</span>
          <strong className="text-lg font-black text-emerald-600 dark:text-emerald-400">
            {metric === "salesRevenue" ? `UGX ${peak.value.toLocaleString()}` : `${peak.value} items`}
          </strong>
        </div>
      </div>

      {/* SVG Canvas Area */}
      <div className="relative w-full overflow-hidden">
        <svg
          viewBox={`0 0 ${width} ${height}`}
          className="w-full h-auto overflow-visible select-none"
        >
          <defs>
            {/* Ambient Background Gradient */}
            <linearGradient id="curveGradient" x1="0" y1="0" x2="0" y2="1">
              <stop offset="0%" stopColor="#ea580c" stopOpacity="0.38" />
              <stop offset="60%" stopColor="#f59e0b" stopOpacity="0.12" />
              <stop offset="100%" stopColor="#ea580c" stopOpacity="0.0" />
            </linearGradient>

            {/* Glowing Stroke Filter */}
            <filter id="glow" x="-20%" y="-20%" width="140%" height="140%">
              <feGaussianBlur stdDeviation="3.5" result="coloredBlur" />
              <feMerge>
                <feMergeNode in="coloredBlur" />
                <feMergeNode in="SourceGraphic" />
              </feMerge>
            </filter>
          </defs>

          {/* Grid lines */}
          {[0.25, 0.5, 0.75, 1].map((pct, i) => {
            const y = height - paddingY - pct * (height - paddingY * 2)
            return (
              <g key={i}>
                <line
                  x1={paddingX}
                  y1={y}
                  x2={width - paddingX}
                  y2={y}
                  stroke="currentColor"
                  className="text-slate-200 dark:text-slate-800"
                  strokeDasharray="4 4"
                  strokeWidth="1"
                />
              </g>
            )
          })}

          {/* Area Under Continuous Curve */}
          <path d={areaPath} fill="url(#curveGradient)" />

          {/* Continuous Spline Line */}
          <path
            d={linePath}
            fill="none"
            stroke="#ea580c"
            strokeWidth="3.5"
            strokeLinecap="round"
            filter="url(#glow)"
          />

          {/* Plotted Dots / Nodes */}
          {points.map((pt, index) => {
            const isHovered = hoveredPoint?.point.date === pt.data.date
            return (
              <g
                key={index}
                className="cursor-pointer"
                onMouseEnter={() => setHoveredPoint({ point: pt.data, x: pt.x, y: pt.y })}
                onMouseLeave={() => setHoveredPoint(null)}
              >
                {/* Outer halo when hovered or regular pulse */}
                <circle
                  cx={pt.x}
                  cy={pt.y}
                  r={isHovered ? "9" : "6"}
                  className="transition-all duration-200"
                  fill="#f97316"
                  fillOpacity={isHovered ? "0.4" : "0.2"}
                />

                {/* Inner solid plotted dot */}
                <circle
                  cx={pt.x}
                  cy={pt.y}
                  r={isHovered ? "5" : "3.5"}
                  fill="#ea580c"
                  stroke="#ffffff"
                  strokeWidth="2"
                  className="transition-all duration-200"
                />

                {/* X-Axis Labels */}
                <text
                  x={pt.x}
                  y={height - 12}
                  textAnchor="middle"
                  className="text-[10px] font-semibold fill-slate-500 dark:fill-slate-400"
                >
                  {pt.data.date.slice(5)}
                </text>
              </g>
            )
          })}
        </svg>

        {/* Dynamic Tooltip on Dot Hover */}
        {hoveredPoint && (
          <div
            style={{
              left: `${(hoveredPoint.x / width) * 100}%`,
              top: `${(hoveredPoint.y / height) * 100}%`,
              transform: "translate(-50%, -125%)"
            }}
            className="pointer-events-none absolute z-20 rounded-2xl border border-slate-700 bg-slate-900/95 p-3 text-white shadow-2xl backdrop-blur-md transition-all duration-150 whitespace-nowrap"
          >
            <div className="flex items-center gap-1.5 text-[10px] font-medium text-amber-400">
              <Calendar className="h-3 w-3" />
              <span>{hoveredPoint.point.label}</span>
            </div>
            <div className="mt-1 text-sm font-extrabold text-white">
              {metric === "salesRevenue"
                ? `UGX ${hoveredPoint.point.salesRevenue.toLocaleString()}`
                : `${hoveredPoint.point.transactions} Orders recorded`}
            </div>
            <div className="mt-0.5 text-[10px] text-slate-400">
              Plotted Point #{data.findIndex((d) => d.date === hoveredPoint.point.date) + 1}
            </div>
          </div>
        )}
      </div>

      {/* Graph Legend & Status */}
      <div className="mt-4 flex flex-wrap items-center justify-between gap-2 border-t border-slate-100 pt-3 text-xs text-slate-500 dark:border-slate-800">
        <div className="flex items-center gap-4">
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full bg-orange-600" />
            <span className="font-medium text-slate-700 dark:text-slate-300">Continuous Spline Value</span>
          </div>
          <div className="flex items-center gap-2">
            <span className="h-2.5 w-2.5 rounded-full border-2 border-white bg-orange-500 ring-2 ring-orange-500/30" />
            <span className="font-medium text-slate-700 dark:text-slate-300">Plotted Coordinates</span>
          </div>
        </div>
        <span className="text-[11px] text-slate-400">
          Hover over plotted nodes to inspect instantaneous metrics.
        </span>
      </div>
    </div>
  )
}
