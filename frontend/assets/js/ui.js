import { icons } from './icons.js';

export const money = (value) => `UGX ${Number(value || 0).toLocaleString()}`;

export function el(html) {
  const wrap = document.createElement('div');
  wrap.innerHTML = html.trim();
  return wrap.firstElementChild;
}

export function showNotice(target, error) {
  if (!target) return;
  target.innerHTML = error
    ? `<div class="notice error">${icons.alert}<span>Couldn't load this data: ${escapeHtml(error)}</span></div>`
    : '';
}

export function escapeHtml(value) {
  return String(value ?? '')
    .replaceAll('&', '&amp;')
    .replaceAll('<', '&lt;')
    .replaceAll('>', '&gt;')
    .replaceAll('"', '&quot;');
}

export function renderTable(container, { columns, data, searchKey }) {
  let search = '';
  let sortKey = null;
  let sortDir = 'asc';
  let page = 1;
  const perPage = 10;

  const paint = () => {
    const active = document.activeElement;
    const caret = active?.matches?.('[data-search]') ? active.selectionStart : null;
    let rows = data;
    if (searchKey && search) {
      rows = rows.filter((row) => String(row[searchKey] ?? '').toLowerCase().includes(search.toLowerCase()));
    }
    if (sortKey) {
      rows = [...rows].sort((a, b) => {
        const av = a[sortKey];
        const bv = b[sortKey];
        if (av < bv) return sortDir === 'asc' ? -1 : 1;
        if (av > bv) return sortDir === 'asc' ? 1 : -1;
        return 0;
      });
    }
    const totalPages = Math.max(1, Math.ceil(rows.length / perPage));
    page = Math.min(page, totalPages);
    const slice = rows.slice((page - 1) * perPage, page * perPage);
    const start = rows.length === 0 ? 0 : (page - 1) * perPage + 1;
    const end = Math.min(page * perPage, rows.length);

    container.innerHTML = `
      ${searchKey ? `<div class="table-tools"><div class="search"><span style="position:absolute;left:.75rem;top:.65rem;color:var(--primary)">${icons.search}</span><input data-search placeholder="Filter by ${escapeHtml(searchKey)}..." value="${escapeHtml(search)}"></div></div>` : ''}
      <div class="table-wrap">
        <table class="data">
          <thead><tr>${columns.map((col) => `<th class="${col.sortable ? 'sortable' : ''}" data-sort="${escapeHtml(col.key)}">${escapeHtml(col.header)}</th>`).join('')}</tr></thead>
          <tbody>
            ${
              slice.length
                ? slice.map((row) => `<tr>${columns.map((col) => `<td>${col.cell ? col.cell(row) : escapeHtml(row[col.key])}</td>`).join('')}</tr>`).join('')
                : `<tr><td colspan="${columns.length}">No records match your filter criteria.</td></tr>`
            }
          </tbody>
        </table>
      </div>
      <div class="pager">
        <div>Showing <strong>${start}</strong> to <strong>${end}</strong> of <strong>${rows.length}</strong> entries</div>
        <div>
          <button class="btn btn-outline" data-prev>Prev</button>
          <span>Page ${page} of ${totalPages}</span>
          <button class="btn btn-outline" data-next>Next</button>
        </div>
      </div>
    `;

    const searchInput = container.querySelector('[data-search]');
    searchInput?.addEventListener('input', (event) => {
      search = event.target.value;
      page = 1;
      paint();
    });
    if (caret !== null && searchInput) {
      searchInput.focus();
      searchInput.setSelectionRange(caret, caret);
    }
    container.querySelectorAll('[data-sort]').forEach((th) => {
      th.addEventListener('click', () => {
        const key = th.getAttribute('data-sort');
        if (sortKey === key) sortDir = sortDir === 'asc' ? 'desc' : 'asc';
        else {
          sortKey = key;
          sortDir = 'asc';
        }
        paint();
      });
    });
    container.querySelector('[data-prev]')?.addEventListener('click', () => {
      page = Math.max(1, page - 1);
      paint();
    });
    container.querySelector('[data-next]')?.addEventListener('click', () => {
      page = Math.min(totalPages, page + 1);
      paint();
    });
  };

  paint();
}

export function openDialog({ title, description, bodyHtml, submitLabel, onSubmit }) {
  const backdrop = el(`
    <div class="dialog-backdrop open">
      <div class="dialog" role="dialog" aria-modal="true">
        <h2>${escapeHtml(title)}</h2>
        <p class="muted">${escapeHtml(description)}</p>
        <form>
          <div class="form-grid">${bodyHtml}</div>
          <p class="notice error hidden" data-error></p>
          <div class="dialog-actions">
            <button type="button" class="btn btn-outline" data-cancel>Cancel</button>
            <button type="submit" class="btn btn-primary">${escapeHtml(submitLabel)}</button>
          </div>
        </form>
      </div>
    </div>
  `);
  const close = () => backdrop.remove();
  backdrop.addEventListener('click', (event) => {
    if (event.target === backdrop) close();
  });
  backdrop.querySelector('[data-cancel]').addEventListener('click', close);
  backdrop.querySelector('form').addEventListener('submit', async (event) => {
    event.preventDefault();
    const errorEl = backdrop.querySelector('[data-error]');
    errorEl.classList.add('hidden');
    try {
      await onSubmit(new FormData(event.target));
      close();
    } catch (error) {
      errorEl.textContent = error instanceof Error ? error.message : 'Request failed';
      errorEl.classList.remove('hidden');
    }
  });
  document.body.append(backdrop);
  return backdrop;
}

export function field(name, label, attrs = '') {
  return `<label class="field">${escapeHtml(label)}<input class="control" name="${name}" ${attrs}></label>`;
}

export function selectField(name, label, optionsHtml, required = false) {
  return `<label class="field">${escapeHtml(label)}<select class="control" name="${name}" ${required ? 'required' : ''}>${optionsHtml}</select></label>`;
}
