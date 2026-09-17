import { handleSubmit } from './actions.js';

export function createDataNotice(error, rlsBlocked) {
  if (error) {
    const div = document.createElement('div');
    div.className = 'flex items-start gap-2 rounded-lg border border-destructive/30 bg-destructive/10 p-3 text-sm text-destructive mb-4';
    div.innerHTML = `<i data-lucide="alert-triangle" class="mt-0.5 w-4 h-4 shrink-0"></i>Couldn't load this data: ${error}`;
    return div;
  }
  if (rlsBlocked) {
    const div = document.createElement('div');
    div.className = 'flex items-start gap-2 rounded-lg border border-amber-500/30 bg-amber-50 p-3 text-sm text-amber-800 dark:bg-amber-950/30 dark:text-amber-300 mb-4';
    div.innerHTML = `<i data-lucide="shield-alert" class="mt-0.5 w-4 h-4 shrink-0"></i>Your FastAPI role does not currently permit this view.`;
    return div;
  }
  return null;
}

export function createAccessDenied(userRole = "Staff Member", userDepartment = "General Staff", requiredDepartment = null) {
  const div = document.createElement('div');
  div.className = 'mx-auto flex min-h-[60vh] max-w-2xl flex-col items-center justify-center p-6 text-center';
  
  let requiredHtml = '';
  if (requiredDepartment) {
    requiredHtml = `
      <div class="flex items-center justify-between mt-3 pt-3 border-t border-border">
        <span class="text-xs text-muted-foreground">Target Area Requirement:</span>
        <span class="rounded-full bg-destructive/10 px-3 py-1 text-xs font-bold text-destructive">
          ${requiredDepartment} Only
        </span>
      </div>
    `;
  }

  div.innerHTML = `
    <div class="mb-4 flex h-20 w-20 items-center justify-center rounded-3xl bg-destructive/10 text-destructive border border-destructive/20 shadow-xl">
      <i data-lucide="shield-off" class="w-10 h-10"></i>
    </div>
    <h1 class="text-3xl font-black tracking-tight text-foreground">
      Access Denied (ABAC / RBAC)
    </h1>
    <p class="mt-2 text-xs font-bold uppercase tracking-widest text-destructive">
      Departmental Boundary Policy Violation
    </p>

    <div class="mt-6 w-full rounded-2xl border border-border bg-card p-6 text-left shadow-sm space-y-3">
      <div class="flex items-center justify-between border-b border-border pb-3">
        <span class="text-xs text-muted-foreground">Active Account Role:</span>
        <span class="rounded-full bg-secondary px-3 py-1 text-xs font-bold text-secondary-foreground">
          ${userRole}
        </span>
      </div>
      <div class="flex items-center justify-between border-b border-border pb-3">
        <span class="text-xs text-muted-foreground">Assigned Department:</span>
        <span class="rounded-full bg-accent/20 px-3 py-1 text-xs font-bold text-accent-foreground">
          ${userDepartment}
        </span>
      </div>
      ${requiredHtml}
      <p class="pt-2 text-xs leading-relaxed text-muted-foreground">
        Under Attribute-Based Access Control (ABAC), employees cannot access dashboards or records assigned to another department. Only the <strong>System Administrator</strong> possesses cross-departmental clearance.
      </p>
    </div>

    <div class="mt-6 flex gap-3">
      <a href="/index.html" class="btn btn-primary">
        <i data-lucide="arrow-left" class="w-4 h-4"></i>
        Return to Dashboard
      </a>
    </div>
  `;
  return div;
}

export function createFormDialog({ title, description, triggerHtml, actionFn, successRedirect, fieldsHtml }) {
  const container = document.createElement('div');
  container.style.display = 'inline-block';

  // Create Trigger
  const trigger = document.createElement('div');
  trigger.innerHTML = triggerHtml;
  container.appendChild(trigger);

  // Create Dialog
  const dialog = document.createElement('dialog');
  dialog.innerHTML = `
    <div class="dialog-header">
      <h2 class="text-lg font-bold">${title}</h2>
      ${description ? `<p class="text-sm text-muted-foreground mt-1">${description}</p>` : ''}
    </div>
    <form>
      <div class="dialog-body">
        ${fieldsHtml}
      </div>
      <div class="dialog-footer">
        <button type="button" class="btn btn-ghost" id="cancel-btn">Cancel</button>
        <button type="submit" class="btn btn-primary">Save Changes</button>
      </div>
    </form>
  `;
  container.appendChild(dialog);

  // Event Listeners
  const triggerBtn = trigger.firstElementChild;
  triggerBtn.addEventListener('click', () => dialog.showModal());

  const cancelBtn = dialog.querySelector('#cancel-btn');
  cancelBtn.addEventListener('click', () => dialog.close());

  const form = dialog.querySelector('form');
  form.addEventListener('submit', (e) => handleSubmit(e, actionFn, successRedirect));

  return container;
}

export function createDataTable(data, columns, searchKey = null) {
  if (!data || data.length === 0) {
    const empty = document.createElement('div');
    empty.className = 'text-center p-8 border border-border rounded-lg text-muted-foreground';
    empty.innerText = 'No data available.';
    return empty;
  }

  const container = document.createElement('div');
  
  // Search bar
  let currentData = [...data];
  if (searchKey) {
    const searchDiv = document.createElement('div');
    searchDiv.className = 'mb-4 flex items-center relative';
    searchDiv.innerHTML = `
      <i data-lucide="search" class="w-4 h-4 absolute left-3 text-muted-foreground"></i>
      <input type="text" placeholder="Search by ${searchKey}..." class="input search-input pl-9 max-w-sm" />
    `;
    const searchInput = searchDiv.querySelector('input');
    searchInput.addEventListener('input', (e) => {
      const q = e.target.value.toLowerCase();
      currentData = data.filter(item => 
        String(item[searchKey] || '').toLowerCase().includes(q)
      );
      renderTable();
    });
    container.appendChild(searchDiv);
  }

  // Table
  const tableContainer = document.createElement('div');
  tableContainer.className = 'table-container';
  container.appendChild(tableContainer);

  const renderTable = () => {
    let html = `<table class="table"><thead><tr>`;
    columns.forEach(col => {
      html += `<th>${col.header}</th>`;
    });
    html += `</tr></thead><tbody>`;

    if (currentData.length === 0) {
      html += `<tr><td colspan="${columns.length}" class="text-center text-muted-foreground py-8">No matching records found.</td></tr>`;
    } else {
      currentData.forEach(row => {
        html += `<tr>`;
        columns.forEach(col => {
          html += `<td>${col.cell ? col.cell(row) : (row[col.accessorKey] || '')}</td>`;
        });
        html += `</tr>`;
      });
    }
    
    html += `</tbody></table>`;
    tableContainer.innerHTML = html;
    if (window.lucide) window.lucide.createIcons();
  };

  renderTable();
  return container;
}

export function createContinuousStatGraph(data) {
  // Simplified implementation for the vanilla port
  // In a real scenario, consider using Chart.js or D3, 
  // but we implement a basic HTML/CSS bar chart here for zero dependencies.
  
  const container = document.createElement('div');
  container.className = 'h-[300px] w-full flex items-end justify-between gap-2 mt-4 p-4 border border-border rounded-lg bg-card';
  
  if (!data || data.length === 0) {
    container.innerHTML = '<div class="w-full text-center text-muted-foreground">No data for chart</div>';
    return container;
  }

  const maxVal = Math.max(...data.map(d => d.value), 1); // Avoid div by 0
  
  data.forEach(item => {
    const percentage = (item.value / maxVal) * 100;
    const barWrap = document.createElement('div');
    barWrap.className = 'flex flex-col items-center gap-2 flex-1 group';
    
    barWrap.innerHTML = `
      <div class="relative w-full flex justify-center h-48 items-end">
        <div class="w-full max-w-[40px] bg-primary/20 group-hover:bg-primary transition-colors rounded-t-md" style="height: ${percentage}%"></div>
        <div class="absolute -top-8 bg-foreground text-background text-xs px-2 py-1 rounded opacity-0 group-hover:opacity-100 transition-opacity pointer-events-none whitespace-nowrap z-10">
          ${item.value}
        </div>
      </div>
      <div class="text-xs text-muted-foreground rotate-45 md:rotate-0 mt-2">${item.label}</div>
    `;
    container.appendChild(barWrap);
  });

  return container;
}

// Helper to format money
export function formatMoney(amount) {
  return new Intl.NumberFormat('en-UG', {
    style: 'currency',
    currency: 'UGX',
    maximumFractionDigits: 0
  }).format(amount);
}
