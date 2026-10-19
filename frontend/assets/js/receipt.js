/**
 * Hardware World ERP — Sale Receipt
 *
 * Renders a thermal-printer–style receipt that matches the design reference:
 *   - Store header (name, branch, address, phone)
 *   - Sale # and transaction #
 *   - Item lines: SKU · qty × unit price → line total
 *   - Subtotal, tax, grand total
 *   - Payment method and tender
 *   - Footer thank-you message
 *
 * Two modes:
 *   preview:true  — shows "SALE PREVIEW" with Edit / Confirm buttons
 *   preview:false — shows "SALE RECEIPT" with Print / New Sale buttons
 */

import { escapeHtml, money } from './ui.js';

const shortDate = (value) => {
  const d = value ? new Date(value) : new Date();
  return d.toLocaleDateString('en-UG', { year: 'numeric', month: '2-digit', day: '2-digit' })
    + '  ' + d.toLocaleTimeString('en-UG', { hour: '2-digit', minute: '2-digit' });
};

// Generate a simple visual QR-code placeholder (text-art until a real QR lib is added)
function receiptBrand(receipt) {
  const txRef = receipt.transaction_id || receipt.saleid || 'PENDING';
  return `
    <div class="sale-receipt-brand">HARDWARE WORLD</div>
    <div class="sale-receipt-address">
      ${escapeHtml(receipt.branch_name || 'Main Branch')}${receipt.branch_address ? '<br>' + escapeHtml(receipt.branch_address) : ''}
      ${receipt.branch_phone ? '<br>' + escapeHtml(receipt.branch_phone) : ''}
    </div>
    <div class="sale-receipt-tagline">TRACK PURCHASES &amp; MANAGE YOUR ACCOUNT</div>
    <div class="sale-receipt-rule"></div>
    <div class="sale-receipt-tx-ref">— SALE —</div>
    <div class="sale-receipt-meta">
      <span>SALES #</span>  <strong>${escapeHtml(String(receipt.saleid || 'PENDING'))}</strong>
      <span>TRANS #</span>  <strong>${escapeHtml(String(txRef))}</strong>
      <span>DATE</span>     <strong>${escapeHtml(shortDate(receipt.saledate))}</strong>
    </div>
  `;
}

function itemRows(items) {
  if (!items || !items.length) return '<p class="muted" style="text-align:center">No items.</p>';
  return items.map((item) => {
    const qty = Number(item.quantity);
    const unitprice = Number(item.unitprice);
    const lineTotal = Number(item.line_total ?? (qty * unitprice).toFixed(2));
    return `
      <div class="sale-receipt-item">
        <div class="sale-receipt-item-main">
          <strong>${escapeHtml(item.item_name || item.itemname || 'Unknown')}</strong>
          <span>${escapeHtml(String(item.itemid ?? ''))}  ${qty.toLocaleString('en-UG', { maximumFractionDigits: 3 })}-${escapeHtml(item.unit || 'PC')} × ${money(unitprice)}</span>
        </div>
        <strong>${money(lineTotal)}</strong>
      </div>`;
  }).join('');
}

function totalsBlock(receipt) {
  const subtotal = Number(receipt.subtotal ?? receipt.totalamount ?? 0);
  const tax      = Number(receipt.taxamount ?? 0);
  const total    = Number(receipt.totalamount ?? subtotal);
  const discount = Number(receipt.discountamount ?? 0);
  const payment  = (receipt.payment_method || 'cash').replaceAll('_', ' ').toUpperCase();

  return `
    <div class="sale-receipt-totals">
      ${discount > 0 ? `<div><span>DISCOUNT</span><strong>-${money(discount)}</strong></div>` : ''}
      <div><span>SUBTOTAL</span>       <strong>${money(subtotal)}</strong></div>
      <div><span>TOTAL TAX</span>      <strong>${money(tax)}</strong></div>
      <div class="sale-receipt-grand-total">
        <span>INVOICE TOTAL</span>     <strong>${money(total)}</strong>
      </div>
      <div class="sale-receipt-payment-line">
        <span>${escapeHtml(payment)}</span>
        <strong>${money(total)}</strong>
      </div>
    </div>
  `;
}

function receiptMeta(receipt, isPreview) {
  return `
    <div class="sale-receipt-meta">
      <span>CASHIER</span>   <strong>${escapeHtml(receipt.cashier_name || 'Cashier')}</strong>
      <span>CUSTOMER</span>  <strong>${escapeHtml(receipt.customer_name || 'Walk-in')}</strong>
      <span>STATUS</span>    <strong>${isPreview ? 'AWAITING CONFIRMATION' : 'COMPLETED'}</strong>
    </div>
  `;
}

/**
 * Render the receipt HTML string.
 * @param {object} receipt
 * @param {{ preview?: boolean }} options
 */
export function saleReceiptMarkup(receipt, { preview = false } = {}) {
  const stateClass = preview ? 'sale-receipt-preview' : 'sale-receipt-final';
  const heading    = preview ? 'SALE PREVIEW' : 'SALE RECEIPT';

  const actions = preview
    ? `<button type="button" class="btn btn-outline" data-edit-sale>← Edit sale</button>
       <button type="button" class="btn btn-primary" data-confirm-sale>Confirm &amp; complete sale</button>`
    : `<button type="button" class="btn btn-outline" data-print-sale>🖨 Print receipt</button>
       <button type="button" class="btn btn-ghost"   data-new-sale>New sale</button>`;

  return `
    <article class="sale-receipt ${stateClass}" role="region" aria-label="Sale receipt">
      <header class="sale-receipt-header">
        ${receiptBrand(receipt)}
      </header>

      <h2>${heading}</h2>

      <div class="sale-receipt-rule"></div>
      <div class="sale-receipt-items-heading">
        <strong>ITEM</strong>
        <strong>AMOUNT</strong>
      </div>
      <div class="sale-receipt-items">
        ${itemRows(receipt.items)}
      </div>

      <div class="sale-receipt-rule"></div>
      ${totalsBlock(receipt)}

      <div class="sale-receipt-rule"></div>
      ${receiptMeta(receipt, preview)}

      ${preview ? `
        <div class="sale-receipt-rule"></div>
        <p class="sale-receipt-footer">
          Please verify the items and total before confirming.
          This sale will update stock, finance journals, and the audit log.
        </p>` : `
        <div class="sale-receipt-rule"></div>
        <p class="sale-receipt-footer">
          Thank you for shopping at Hardware World.<br>
          Keep this receipt for returns and exchanges.
        </p>`}

      <div class="sale-receipt-actions">${actions}</div>
    </article>
  `;
}

/**
 * Open a print popup for the completed receipt.
 * Returns false if the popup was blocked.
 * @param {object} receipt
 */
export function printSaleReceipt(receipt) {
  const popup = window.open('', '_blank', 'width=480,height=760,resizable=yes');
  if (!popup) return false;
  popup.opener = null;

  const markup = saleReceiptMarkup(receipt, { preview: false });

  popup.document.open();
  popup.document.write(`<!doctype html>
<html lang="en">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width,initial-scale=1">
  <title>Receipt #${escapeHtml(String(receipt.saleid || ''))}</title>
  <style>
    /* Thermal 80 mm print layout */
    @page { size: 80mm auto; margin: 4mm 2mm; }
    * { box-sizing: border-box; }
    body {
      margin: 0;
      color: #111;
      background: #fff;
      font-family: "Courier New", Courier, monospace;
      font-size: 11.5px;
      line-height: 1.45;
    }

    /* Receipt wrapper */
    .sale-receipt { width: 100%; max-width: 76mm; margin: 0 auto; }
    .sale-receipt-header,
    .sale-receipt h2,
    .sale-receipt-footer,
    .sale-receipt-tx-ref,
    .sale-receipt-tagline { text-align: center; }

    .sale-receipt-brand {
      font-size: 22px;
      font-weight: 900;
      letter-spacing: 1.5px;
      text-transform: uppercase;
      margin-bottom: 3px;
    }
    .sale-receipt-address { font-size: 10.5px; margin-bottom: 3px; }
    .sale-receipt-tagline {
      font-size: 9.5px;
      letter-spacing: 0.5px;
      margin: 6px 0 4px;
      text-transform: uppercase;
    }
    .sale-receipt-tx-ref {
      font-size: 13px;
      font-weight: 900;
      margin: 8px 0 4px;
      letter-spacing: 2px;
    }
    .sale-receipt h2 {
      font-size: 12px;
      font-weight: 900;
      letter-spacing: 2px;
      text-transform: uppercase;
      margin: 10px 0 6px;
    }
    .sale-receipt-rule {
      border: none;
      border-top: 1px dashed #666;
      margin: 7px 0;
    }
    .sale-receipt-meta {
      display: grid;
      grid-template-columns: 56px 1fr;
      gap: 2px 8px;
      font-size: 10px;
    }
    .sale-receipt-meta strong { text-align: right; word-break: break-all; }
    .sale-receipt-items-heading,
    .sale-receipt-item {
      display: flex;
      justify-content: space-between;
      gap: 8px;
    }
    .sale-receipt-items-heading {
      font-size: 9.5px;
      font-weight: 900;
      text-transform: uppercase;
      letter-spacing: 0.5px;
      margin-bottom: 6px;
    }
    .sale-receipt-item { margin: 7px 0; align-items: flex-start; }
    .sale-receipt-item-main { flex: 1; min-width: 0; }
    .sale-receipt-item-main strong { display: block; font-size: 11px; }
    .sale-receipt-item-main span { display: block; font-size: 9.5px; color: #444; }
    .sale-receipt-item > strong { white-space: nowrap; font-size: 11px; }
    .sale-receipt-totals > div {
      display: flex;
      justify-content: space-between;
      margin: 3px 0;
      font-size: 11px;
    }
    .sale-receipt-grand-total { font-size: 13.5px !important; font-weight: 900; padding-top: 3px; }
    .sale-receipt-payment-line {
      font-size: 11px;
      font-weight: 700;
      padding-top: 2px;
    }
    .sale-receipt-footer {
      font-size: 9.5px;
      color: #444;
      text-align: center;
      margin-top: 10px;
      line-height: 1.5;
    }
    .sale-receipt-actions { display: none !important; }
  </style>
</head>
<body>${markup}</body>
</html>`);
  popup.document.close();
  popup.focus();
  // Small delay so the browser renders before opening the print dialog
  popup.setTimeout(() => { popup.print(); }, 350);
  return true;
}
