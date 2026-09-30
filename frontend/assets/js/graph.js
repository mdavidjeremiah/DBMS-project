import { money } from './ui.js';
import { icons } from './icons.js';

export function renderGraph(container, initialData) {
  const data = initialData ?? [];
  if (!data.length) {
    container.innerHTML = '<div class="card"><p class="muted center">No sales data has been entered yet.</p></div>';
    return;
  }
  let metric = 'salesRevenue';
  const width = 800;
  const height = 300;
  const paddingX = 50;
  const paddingY = 40;

  const paint = () => {
    const values = data.map((d) => d[metric]);
    const max = Math.max(...values, 1);
    const total = values.reduce((acc, v) => acc + v, 0);
    const avg = Math.round(total / values.length);
    const peak = Math.max(...values);
    const points = data.map((d, index) => {
      const x = paddingX + (index / (data.length - 1)) * (width - paddingX * 2);
      const y = height - paddingY - (d[metric] / (max * 1.15)) * (height - paddingY * 2);
      return { x, y, data: d };
    });
    let path = `M ${points[0].x} ${points[0].y}`;
    for (let i = 0; i < points.length - 1; i += 1) {
      const p0 = points[i];
      const p1 = points[i + 1];
      const cpX = p0.x + (p1.x - p0.x) / 2;
      path += ` C ${cpX} ${p0.y}, ${cpX} ${p1.y}, ${p1.x} ${p1.y}`;
    }
    const last = points[points.length - 1];
    const first = points[0];
    const area = `${path} L ${last.x} ${height - paddingY} L ${first.x} ${height - paddingY} Z`;

    container.innerHTML = `
      <div class="card">
        <div class="page-head">
          <div>
            <div class="kicker">${icons.activity} Continuous Performance Plotted Graph</div>
            <h2>${metric === 'salesRevenue' ? 'Continuous Sales Revenue Flow' : 'Continuous Transactions Density'}</h2>
            <p class="muted">Real-time continuous spline curve plotting node values across operating cycles.</p>
          </div>
          <div class="graph-controls">
            <button class="btn ${metric === 'salesRevenue' ? 'btn-primary' : 'btn-ghost'}" data-metric="salesRevenue">Revenue (UGX)</button>
            <button class="btn ${metric === 'transactions' ? 'btn-primary' : 'btn-ghost'}" data-metric="transactions">Order Count</button>
          </div>
        </div>
        <div class="grid-3" style="margin:1rem 0">
          <div class="card"><span class="muted">Period Aggregate</span><strong>${metric === 'salesRevenue' ? money(total) : `${total.toLocaleString()} sales`}</strong></div>
          <div class="card"><span class="muted">Daily Mean</span><strong>${metric === 'salesRevenue' ? money(avg) : `${avg.toLocaleString()} / day`}</strong></div>
          <div class="card"><span class="muted">Plotted Peak</span><strong>${metric === 'salesRevenue' ? money(peak) : `${peak} items`}</strong></div>
        </div>
        <div class="graph-wrap">
          <svg viewBox="0 0 ${width} ${height}">
            <defs>
              <linearGradient id="curveGradient" x1="0" y1="0" x2="0" y2="1">
                <stop offset="0%" stop-color="#ea580c" stop-opacity="0.38" />
                <stop offset="100%" stop-color="#ea580c" stop-opacity="0" />
              </linearGradient>
            </defs>
            <path d="${area}" fill="url(#curveGradient)"></path>
            <path d="${path}" fill="none" stroke="#ea580c" stroke-width="3.5" stroke-linecap="round"></path>
            ${points.map((pt) => `<g class="node" data-date="${pt.data.date}"><circle cx="${pt.x}" cy="${pt.y}" r="6" fill="#f97316" fill-opacity="0.25"></circle><circle cx="${pt.x}" cy="${pt.y}" r="3.5" fill="#ea580c" stroke="#fff" stroke-width="2"></circle><text x="${pt.x}" y="${height - 12}" text-anchor="middle" font-size="10" fill="#64748b">${pt.data.date.slice(5)}</text></g>`).join('')}
          </svg>
          <div class="tooltip hidden" id="graph-tip"></div>
        </div>
      </div>
    `;

    container.querySelectorAll('[data-metric]').forEach((btn) => {
      btn.addEventListener('click', () => {
        metric = btn.getAttribute('data-metric');
        paint();
      });
    });

    const tip = container.querySelector('#graph-tip');
    container.querySelectorAll('.node').forEach((node) => {
      node.addEventListener('mouseenter', () => {
        const point = data.find((d) => d.date === node.getAttribute('data-date'));
        const circle = node.querySelector('circle');
        tip.classList.remove('hidden');
        tip.style.left = `${(Number(circle.getAttribute('cx')) / width) * 100}%`;
        tip.style.top = `${(Number(circle.getAttribute('cy')) / height) * 100}%`;
        tip.innerHTML = `<div>${point.label}</div><strong>${metric === 'salesRevenue' ? money(point.salesRevenue) : `${point.transactions} Orders recorded`}</strong>`;
      });
      node.addEventListener('mouseleave', () => tip.classList.add('hidden'));
    });
  };

  paint();
}

export function buildGraphData(sales) {
  const now = new Date();
  const days = Array.from({ length: 7 }, (_, i) => {
    const d = new Date();
    d.setDate(now.getDate() - (6 - i));
    return d;
  });
  const graphData = days.map((d) => {
    const dateStr = d.toISOString().split('T')[0];
    const daySales = sales.filter((s) => s.saledate && s.saledate.startsWith(dateStr));
    const rev = daySales.reduce((sum, s) => sum + Number(s.totalamount || 0), 0);
    return {
      date: dateStr,
      label: d.toLocaleDateString('en-US', { weekday: 'short', month: 'short', day: 'numeric' }),
      salesRevenue: rev,
      transactions: daySales.length,
    };
  });
  return graphData;
}
