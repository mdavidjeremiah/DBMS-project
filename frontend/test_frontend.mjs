import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { test } from 'node:test';
import { buildGraphData, renderGraph } from './assets/js/graph.js';

const sourceRoot = new URL('.', import.meta.url);

function isoDate(daysAgo) {
  const date = new Date();
  date.setDate(date.getDate() - daysAgo);
  return date.toISOString().split('T')[0];
}

test('buildGraphData returns seven database-backed daily points', () => {
  const sales = [
    { saledate: `${isoDate(0)}T10:00:00`, totalamount: '125000' },
    { saledate: `${isoDate(0)}T11:00:00`, totalamount: '75000' },
    { saledate: `${isoDate(1)}T09:00:00`, totalamount: '50000' },
  ];

  const graphData = buildGraphData(sales);
  const today = graphData.find((point) => point.date === isoDate(0));
  const yesterday = graphData.find((point) => point.date === isoDate(1));

  assert.equal(graphData.length, 7);
  assert.deepEqual(today, {
    date: isoDate(0),
    label: today.label,
    salesRevenue: 200000,
    transactions: 2,
  });
  assert.equal(yesterday.salesRevenue, 50000);
  assert.equal(yesterday.transactions, 1);
});

test('buildGraphData returns zero values when no sales exist', () => {
  const graphData = buildGraphData([]);

  assert.equal(graphData.length, 7);
  assert.ok(graphData.every((point) => point.salesRevenue === 0 && point.transactions === 0));
});

test('renderGraph shows an empty state instead of invented values', () => {
  const container = { innerHTML: '' };

  renderGraph(container, []);

  assert.match(container.innerHTML, /No sales data has been entered yet/);
  assert.doesNotMatch(container.innerHTML, /DEFAULT_DATA|2850000/);
});

test('application pages reference the shared stylesheet', async () => {
  for (const page of ['index.html', 'login.html', 'sign-up.html']) {
    const html = await readFile(new URL(page, sourceRoot), 'utf8');
    assert.match(html, /assets\/css\/style\.css/);
  }
});

test('frontend source contains no demo login or fallback graph data', async () => {
  const [pages, graph] = await Promise.all([
    readFile(new URL('./assets/js/pages.js', sourceRoot), 'utf8'),
    readFile(new URL('./assets/js/graph.js', sourceRoot), 'utf8'),
  ]);

  assert.doesNotMatch(pages, /data-fill|adminpassword|staff123|Akena/);
  assert.doesNotMatch(graph, /DEFAULT_DATA|2850000|7420000/);
});