import { apiRequest, loadList } from './api.js';
import { escapeHtml, money, renderLoadingState, renderTable, showNotice } from './ui.js';
import { icons } from './icons.js';
import { printSaleReceipt, saleReceiptMarkup } from './receipt.js';

export async function renderSales(page, user = window.__HW_USER__) {
  renderLoadingState(page, 'Loading sales and products…');
  const canSell = (user?.permissions || []).includes('sales:pos');
  let cashierSession = null;
  let cashierSessionError = null;
  let warehouses = { data: [], error: null };

  if (canSell) {
    try {
      const currentSession = await apiRequest('/api/cashier-sessions/current');
      cashierSession = currentSession?.has_active_session ? currentSession : null;
      if (!cashierSession && user?.branchid) {
        warehouses = await loadList(`/api/warehouses?branch_id=${encodeURIComponent(user.branchid)}`);
        const assignedWarehouseIds = new Set((user.warehouse_ids || []).map(Number));
        if (assignedWarehouseIds.size) {
          warehouses.data = warehouses.data.filter((warehouse) => assignedWarehouseIds.has(Number(warehouse.warehouse_id)));
        }
      }
    } catch (error) {
      cashierSessionError = error instanceof Error ? error.message : 'Unable to check the cashier session.';
    }
  }
  const warehouseQuery = cashierSession?.warehouse_id
    ? `?warehouse_id=${encodeURIComponent(cashierSession.warehouse_id)}`
    : '';
  const [sales, productsResult] = await Promise.all([
    loadList('/api/sales'),
    loadList(`/api/products${warehouseQuery}`),
  ]);
  const products = {
    ...productsResult,
    data: productsResult.data.map((product) => ({ ...product, stock_qty: Number(product.available_stock || 0) })),
  };

  page.innerHTML = `
    <header class="page-head card">
      <div>
        <div class="kicker">${icons.banknote} Point of sale</div>
        <h1>Sales & Retail Checkout</h1>
        <p class="muted">Review a customer receipt before committing the sale to stock and finance records.</p>
      </div>
    </header>
    <div id="session-notice"></div><a class="btn btn-outline" href="operations.html">Close or review till</a>
    ${canSell && !cashierSession && !cashierSessionError ? `
      <form id="open-cashier-session" class="card form-grid">
        <h2>Open cashier session</h2>
        <label class="field">Warehouse
          <select class="control" name="warehouse_id" required ${!warehouses.data.length ? 'disabled' : ''}>
            <option value="">Select a warehouse</option>
            ${warehouses.data.map((warehouse) => `<option value="${warehouse.warehouse_id}">${escapeHtml(warehouse.warehouse_name)}</option>`).join('')}
          </select>
        </label>
        <label class="field">Opening cash float (UGX)
          <input class="control" name="opening_float" type="number" min="0" step="0.01" value="0" required>
        </label>
        <button class="btn btn-primary" type="submit" ${!warehouses.data.length ? 'disabled' : ''}>Open session</button>
        ${!user?.branchid ? '<p class="muted">Your account must be assigned to a branch before opening a till.</p>' : ''}
        ${warehouses.error ? `<p class="muted">${escapeHtml(warehouses.error)}</p>` : ''}
        ${user?.branchid && !warehouses.error && !warehouses.data.length ? '<p class="muted">There is no active warehouse assigned to this branch.</p>' : ''}
      </form>` : ''}
    ${cashierSession ? `<div class="notice">Cashier session #${escapeHtml(cashierSession.session_id)} is open · ${escapeHtml(cashierSession.warehouse_name || `Warehouse #${cashierSession.warehouse_id}`)} · Opening float ${money(cashierSession.opening_float)}</div>` : ''}
    <section id="sale-receipt-panel" class="sale-receipt-panel hidden" aria-live="polite"></section>
    <div id="notice"></div>
    <form id="pos" class="pos-grid ${!canSell || !cashierSession ? 'hidden' : ''}">
      <section class="card">
        <div class="sale-product-picker">
          <select class="control" id="product-select" aria-label="Select a product">
            <option value="">Select a product</option>
            ${products.data.map((product) => `<option value="${product.itemid}" ${!product.is_active || Number(product.stock_qty) <= 0 ? 'disabled' : ''}>${escapeHtml(product.itemname)} · ${money(product.unitprice)} · ${Number(product.stock_qty || 0).toLocaleString()} available</option>`).join('')}
          </select>
          <button class="btn btn-outline" type="button" id="add-line">Add item</button>
        </div>
        <div id="lines"><p class="muted center">Add products to begin a sale.</p></div>
      </section>
      <aside class="card form-grid">
        <h2>Sale details</h2>
        <label class="field">Payment method
          <select class="control" name="payment_method">
            <option value="cash">Cash</option>
            <option value="mobile_money">Mobile Money</option>
            <option value="card">Card / Bank</option>
          </select>
        </label>
        <label class="field">Customer name <span class="muted">(optional)</span>
          <input class="control" name="customername" autocomplete="name" placeholder="Walk-in customer">
        </label>
        <label class="field">Customer phone <span class="muted">(optional)</span>
          <input class="control" name="customerphone" autocomplete="tel" placeholder="Phone number">
        </label>
        <div class="sale-total-preview"><span>Sale total</span><strong id="pos-total">${money(0)}</strong></div>
        <button class="btn btn-primary" type="submit" id="complete-sale" disabled>Review & complete sale</button>
      </aside>
    </form>
    <div id="table"></div>
  `;

  showNotice(page.querySelector('#notice'), sales.error || products.error, { onRetry: () => window.location.reload() });
  showNotice(page.querySelector('#session-notice'), cashierSessionError, { onRetry: () => window.location.reload() });

  const receiptPanel = page.querySelector('#sale-receipt-panel');
  const posForm = page.querySelector('#pos');
  const storedReceipt = sessionStorage.getItem('hw_last_receipt');
  if (storedReceipt) {
    try {
      const finalReceipt = JSON.parse(storedReceipt);
      receiptPanel.innerHTML = saleReceiptMarkup(finalReceipt);
      receiptPanel.classList.remove('hidden');
      bindFinalReceiptActions(receiptPanel, finalReceipt);
    } catch {
      sessionStorage.removeItem('hw_last_receipt');
    }
    sessionStorage.removeItem('hw_last_receipt');
  }

  page.querySelector('#open-cashier-session')?.addEventListener('submit', async (event) => {
    event.preventDefault();
    const form = event.currentTarget;
    const submitButton = form.querySelector('button[type="submit"]');
    submitButton.disabled = true;
    submitButton.textContent = 'Opening session…';
    try {
      await apiRequest('/api/cashier-sessions/open', {
        method: 'POST',
        body: JSON.stringify({
          branch_id: Number(user.branchid),
          warehouse_id: Number(form.warehouse_id.value),
          opening_float: form.opening_float.value,
        }),
      });
      window.location.reload();
    } catch (error) {
      showNotice(page.querySelector('#notice'), error instanceof Error ? error.message : 'Unable to open cashier session.');
      submitButton.disabled = false;
      submitButton.textContent = 'Open session';
    }
  });

  if (!sales.error) {
    renderTable(page.querySelector('#table'), {
      columns: [
        { header: 'Receipt #', key: 'saleid', sortable: true },
        { header: 'Date', key: 'saledate', sortable: true },
        { header: 'Customer', key: 'customer_name' },
        { header: 'Cashier', key: 'cashier_name' },
        { header: 'Branch', key: 'branch_name' },
        { header: 'Payment', key: 'payment_method' },
        { header: 'Total', key: 'totalamount', sortable: true, cell: (row) => money(row.totalamount) },
      ],
      data: sales.data,
      searchKey: 'customer_name',
    });
  }

  if (products.error) return;

  const lines = [];
  const paintLines = () => {
    const box = page.querySelector('#lines');
    if (!lines.length) {
      box.innerHTML = '<p class="muted center">Add products to begin a sale.</p>';
    } else {
      box.innerHTML = lines.map((line) => {
        const product = products.data.find((item) => item.itemid === line.itemid);
        return `<div class="line" data-id="${line.itemid}">
          <div><strong>${escapeHtml(product.itemname)}</strong><div class="muted">${money(product.unitprice)} each · ${Number(product.stock_qty).toLocaleString()} available</div></div>
          <div class="qty"><button type="button" data-dec aria-label="Decrease quantity">−</button><input class="control" aria-label="Quantity" type="number" min="0.001" step="0.001" value="${line.quantity}"><button type="button" data-inc aria-label="Increase quantity">+</button></div>
          <button type="button" data-del aria-label="Remove item">${icons.trash}</button>
        </div>`;
      }).join('');
    }
    const total = lines.reduce((sum, line) => sum + Number(products.data.find((product) => product.itemid === line.itemid)?.unitprice || 0) * line.quantity, 0);
    page.querySelector('#pos-total').textContent = money(total);
    page.querySelector('#complete-sale').disabled = !lines.length;
  };

  page.querySelector('#add-line').addEventListener('click', () => {
    const selector = page.querySelector('#product-select');
    const itemid = Number(selector.value);
    if (!itemid) return;
    const product = products.data.find((item) => item.itemid === itemid);
    const existing = lines.find((line) => line.itemid === itemid);
    if (existing) existing.quantity = Math.min(Number(product.stock_qty), existing.quantity + 1);
    else lines.push({ itemid, quantity: 1 });
    selector.value = '';
    showNotice(page.querySelector('#notice'), null);
    paintLines();
  });

  page.querySelector('#lines').addEventListener('click', (event) => {
    const row = event.target.closest('.line');
    if (!row) return;
    const line = lines.find((item) => item.itemid === Number(row.dataset.id));
    const product = products.data.find((item) => item.itemid === line.itemid);
    if (event.target.closest('[data-del]')) lines.splice(lines.indexOf(line), 1);
    else if (event.target.closest('[data-inc]')) line.quantity = Math.min(Number(product.stock_qty), line.quantity + 1);
    else if (event.target.closest('[data-dec]')) {
      line.quantity -= 1;
      if (line.quantity <= 0) lines.splice(lines.indexOf(line), 1);
    } else return;
    paintLines();
  });

  page.querySelector('#lines').addEventListener('change', (event) => {
    if (!event.target.matches('input[type="number"]')) return;
    const row = event.target.closest('.line');
    const line = lines.find((item) => item.itemid === Number(row.dataset.id));
    const product = products.data.find((item) => item.itemid === line.itemid);
    const quantity = Number(event.target.value);
    line.quantity = Number.isFinite(quantity) && quantity > 0 ? Math.min(quantity, Number(product.stock_qty)) : 0;
    if (!line.quantity) lines.splice(lines.indexOf(line), 1);
    paintLines();
  });

  page.querySelector('#pos').addEventListener('submit', (event) => {
    event.preventDefault();
    if (!lines.length) return;
    const form = event.currentTarget;
    const items = lines.map((line) => {
      const product = products.data.find((item) => item.itemid === line.itemid);
      return {
        itemid: line.itemid,
        item_name: product.itemname,
        quantity: line.quantity,
        unitprice: Number(product.unitprice),
        line_total: Number((Number(product.unitprice) * line.quantity).toFixed(2)),
      };
    });
    const subtotal = Number(items.reduce((sum, item) => sum + item.line_total, 0).toFixed(2));
    const receipt = {
      items,
      subtotal,
      taxamount: 0,
      totalamount: subtotal,
      payment_method: form.payment_method.value,
      customer_name: form.customername.value.trim() || 'Walk-in',
      cashier_name: user?.name || 'Cashier',
      branch_name: user?.branch_name || 'Hardware World',
      branch_phone: user?.branch_phone || '',
      saledate: new Date().toISOString(),
    };
    receiptPanel.innerHTML = saleReceiptMarkup(receipt, { preview: true });
    receiptPanel.classList.remove('hidden');
    posForm.classList.add('hidden');
    showNotice(page.querySelector('#notice'), null);
    receiptPanel.querySelector('[data-edit-sale]').addEventListener('click', () => {
      receiptPanel.classList.add('hidden');
      receiptPanel.replaceChildren();
      posForm.classList.remove('hidden');
    });
    receiptPanel.querySelector('[data-confirm-sale]').addEventListener('click', async (confirmEvent) => {
      const button = confirmEvent.currentTarget;
      button.disabled = true;
      button.textContent = 'Completing sale…';
      try {
        const result = await apiRequest('/api/sales', {
          method: 'POST',
          body: JSON.stringify({
            branchid: user.branchid,
            warehouseid: cashierSession.warehouse_id,
            cashiersessionid: cashierSession.session_id,
            customername: form.customername.value.trim() || null,
            customerphone: form.customerphone.value.trim() || null,
            payment_method: form.payment_method.value,
            items: lines.map(({ itemid, quantity }) => ({ itemid, quantity })),
          }),
        });
        const completed = {
          ...receipt,
          saleid: result.saleid,
          transaction_id: `SALE-${result.saleid}`,
          totalamount: Number(result.totalamount),
          subtotal: Number(result.totalamount),
          payment_method: result.payment_method || receipt.payment_method,
          saledate: result.saledate || receipt.saledate,
        };
        sessionStorage.setItem('hw_last_receipt', JSON.stringify(completed));
        window.location.reload();
      } catch (error) {
        showNotice(page.querySelector('#notice'), error instanceof Error ? error.message : 'Unable to complete sale.');
        button.disabled = false;
        button.textContent = 'Confirm and complete sale';
      }
    });
    receiptPanel.scrollIntoView({ behavior: 'smooth', block: 'start' });
  });
}

function bindFinalReceiptActions(panel, receipt) {
  panel.querySelector('[data-print-sale]')?.addEventListener('click', () => {
    if (!printSaleReceipt(receipt)) {
      showNotice(document.querySelector('#notice'), 'Allow pop-ups for this site to print the receipt.');
    }
  });
  panel.querySelector('[data-new-sale]')?.addEventListener('click', () => {
    sessionStorage.removeItem('hw_last_receipt');
    window.location.reload();
  });
}
