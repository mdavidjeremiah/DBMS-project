import { apiRequest } from './api.js';

// Convert FormData to JSON object, handling numbers appropriately
function formDataToJson(formData) {
  const json = {};
  for (const [key, value] of formData.entries()) {
    // Basic type inference
    if (value === '') {
      json[key] = null;
    } else if (!isNaN(Number(value)) && key.toLowerCase().includes('id')) {
      json[key] = Number(value);
    } else if (!isNaN(Number(value)) && (key === 'unitprice' || key === 'salary' || key === 'approvallimit')) {
      json[key] = Number(value);
    } else {
      json[key] = value;
    }
  }
  return json;
}

export async function createCategory(formData) {
  await apiRequest('/categories', {
    method: 'POST',
    body: JSON.stringify(formDataToJson(formData))
  });
}

export async function createSupplier(formData) {
  await apiRequest('/suppliers', {
    method: 'POST',
    body: JSON.stringify(formDataToJson(formData))
  });
}

export async function createProduct(formData) {
  await apiRequest('/products', {
    method: 'POST',
    body: JSON.stringify(formDataToJson(formData))
  });
}

export async function createEmployee(formData) {
  const employeePayload = {
    name: formData.get('name'),
    nin: formData.get('nin'),
    email: formData.get('email') || null,
    password: formData.get('password') || null,
    phone: formData.get('phone') || null,
    salary: Number(formData.get('salary')),
    datehired: formData.get('datehired') || new Date().toISOString().split('T')[0],
    branchid: Number(formData.get('branchid')),
    departmentid: Number(formData.get('departmentid')),
    roletype: formData.get('roletype'),
  };

  if (formData.get('supervisorid')) {
    employeePayload.supervisorid = Number(formData.get('supervisorid'));
  }

  // Handle subtype fields based on role
  const role = formData.get('roletype');
  if (role === 'Cashier') {
    employeePayload.pos_terminalid = formData.get('pos_terminalid');
  } else if (role === 'Procurement Officer') {
    employeePayload.approvallimit = Number(formData.get('approvallimit'));
  } else if (role === 'Accountant') {
    employeePayload.certificationnumber = formData.get('certificationnumber');
  } else if (role === 'HR Staff') {
    employeePayload.hr_role = formData.get('hr_role');
  } else if (role === 'Branch Manager') {
    employeePayload.managementlevel = formData.get('managementlevel');
  }

  await apiRequest('/employees', {
    method: 'POST',
    body: JSON.stringify(employeePayload)
  });
}

export async function createPurchaseOrder(formData) {
  await apiRequest('/purchase-orders', {
    method: 'POST',
    body: JSON.stringify(formDataToJson(formData))
  });
}

export async function createPayroll(formData) {
  await apiRequest('/payroll', {
    method: 'POST',
    body: JSON.stringify(formDataToJson(formData))
  });
}

export async function createLedgerEntry(formData) {
  await apiRequest('/ledger', {
    method: 'POST',
    body: JSON.stringify(formDataToJson(formData))
  });
}

export async function createSale(formData) {
  // Handle the complex payload from the POS checkout
  const salePayload = {
    branchid: Number(formData.get('branchid')),
    employeeid: Number(formData.get('employeeid')),
    customername: formData.get('customername') || null,
    customerphone: formData.get('customerphone') || null,
    totalamount: 0,
    items: []
  };

  const itemids = formData.getAll('itemid');
  const quantities = formData.getAll('quantity');
  const unitprices = formData.getAll('unitprice');

  for (let i = 0; i < itemids.length; i++) {
    const qty = Number(quantities[i]);
    const price = Number(unitprices[i]);
    if (qty > 0) {
      salePayload.items.push({
        itemid: Number(itemids[i]),
        quantity: qty,
        unitprice: price
      });
      salePayload.totalamount += (qty * price);
    }
  }

  await apiRequest('/sales', {
    method: 'POST',
    body: JSON.stringify(salePayload)
  });
}

// Universal submit handler wrapper
export async function handleSubmit(event, actionFn, successRedirect = null) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const submitBtn = form.querySelector('button[type="submit"]');
  const originalText = submitBtn.innerText;
  
  try {
    submitBtn.disabled = true;
    submitBtn.innerText = 'Saving...';
    await actionFn(formData);
    if (successRedirect) {
      window.location.href = successRedirect;
    } else {
      window.location.reload();
    }
  } catch (error) {
    alert(`Error: ${error.message}`);
    submitBtn.disabled = false;
    submitBtn.innerText = originalText;
  }
}
