import { apiRequest } from './api.js';

import { can } from './permissions.js';

import { escapeHtml, field, selectField, openDialog, renderTable, showNotice } from './ui.js';

const num=(f,k)=>Number(f.get(k));

export const WORKFLOW_ACTIONS = [

 ['Pay approved payroll','finance:payment',f=>`/api/payroll/${num(f,'pay_run')}/pay`,['pay_run'],()=>({})],

 ['Process return','sales:refund','/api/returns',['sale_id','product','quantity','reason'],f=>({sale_id:num(f,'sale_id'),reason:f.get('reason'),refund_method:'ORIGINAL_METHOD',items:[{item_id:num(f,'product'),quantity:f.get('quantity'),condition:'GOOD'}]})],

 ['Record attendance','hr:attendance','/api/attendance',['employee_id','date'],f=>({employee_id:num(f,'employee_id'),date:f.get('date'),status:'PRESENT'})],

 ['Request leave','hr:leave','/api/leave',['employee_id','start_date','end_date'],f=>({employee_id:num(f,'employee_id'),start_date:f.get('start_date'),end_date:f.get('end_date'),leave_type:'ANNUAL'})],

 ['Record customer payment','finance:payment','/api/customers/credit-payment',['customer_id','amount'],f=>({customer_id:num(f,'customer_id'),amount:f.get('amount'),payment_method:'CASH'})],

 ['Opening stock','inventory:manage','/api/inventory/opening-stock',['product','warehouse','quantity','cost'],f=>({items:[{item_id:num(f,'product'),warehouse_id:num(f,'warehouse'),quantity:f.get('quantity'),unit_cost:f.get('cost')}]})],

 ['Create requisition','procurement:requisition','/api/purchase-requisitions',['product','quantity','cost'],f=>({items:[{itemid:num(f,'product'),quantity:f.get('quantity'),estimated_unit_cost:f.get('cost')}]})],

 ['Receive goods','procurement:grn','/api/goods-receipts',['order','warehouse','product','quantity','cost'],f=>({po_id:num(f,'order'),warehouse_id:num(f,'warehouse'),items:[{item_id:num(f,'product'),quantity_received:f.get('quantity'),unit_cost:f.get('cost')}]})],

 ['Record invoice','finance:invoice','/api/supplier-invoices',['receipt','invoice_number','amount'],(f,c)=>({po_id:c.receipts.find(r=>r.id===num(f,'receipt')).po_id,grn_id:num(f,'receipt'),invoice_number:f.get('invoice_number'),amount:f.get('amount')})],

 ['Pay supplier','finance:payment','/api/supplier-payments',['invoice','amount'],f=>({invoice_id:num(f,'invoice'),amount:f.get('amount'),payment_method:'bank'})],

 ['Prepare payroll','payroll:prepare','/api/payroll/run',['month'],f=>({month:f.get('month')})],

 ['Approve payroll','payroll:approve','/api/payroll/approve',['run'],f=>({run_id:num(f,'run')})],

 ['Close till','sales:pos',f=>`/api/cashier-sessions/${num(f,'session')}/close`,['session','actual_cash'],f=>({actual_cash:f.get('actual_cash')})],

 ['Review till variance','sales:approve',f=>`/api/cashier-sessions/${num(f,'review_session')}/review`,['review_session'],()=>({})],

 ['Request adjustment','inventory:adjust','/api/stock-adjustments',['product','warehouse','variance','reason'],f=>({item_id:num(f,'product'),warehouse_id:num(f,'warehouse'),variance_quantity:f.get('variance'),reason_code:f.get('reason')})],

 ['Transfer stock','inventory:adjust','/api/transfers',['warehouse','destination','product','quantity'],f=>({from_warehouse_id:num(f,'warehouse'),to_warehouse_id:num(f,'destination'),items:[{item_id:num(f,'product'),quantity:f.get('quantity')}]})],

];


const LABELS = {product:'Product', warehouse:'Source warehouse', destination:'Destination warehouse', order:'Approved purchase order', receipt:'Goods receipt', invoice:'Supplier invoice', run:'Draft payroll run', pay_run:'Approved payroll run', session:'Your open till', review_session:'Till awaiting review', employee_id:'Employee', customer_id:'Customer', sale_id:'Original receipt', actual_cash:'Cash counted (UGX)', quantity:'Quantity', cost:'Unit cost (UGX)', amount:'Amount (UGX)', variance:'Stock change (+ gain / - loss)', reason:'Reason', invoice_number:'Supplier invoice number', month:'Payroll month', start_date:'Start date', end_date:'End date', date:'Attendance date'};
const optionMarkup = rows => '<option value="">Select a record</option>' + rows.map(r => `<option value="${r.id}">${escapeHtml(r.name || r.month || '#'+r.id)}${r.status ? ' - '+escapeHtml(r.status) : ''}</option>`).join('');

export async function renderOperations(page) {
 page.innerHTML='<div class="card" role="status">Loading operations...</div>';
 let context;
 try { context=await apiRequest('/api/operations/context'); }
 catch(error) { page.replaceChildren(); showNotice(page,error.message,{onRetry:()=>renderOperations(page)}); return; }
 page.innerHTML=`<header class="page-head card"><div><div class="kicker">Daily work</div><h1>Operations</h1><p class="muted">Choose a task, review the saved records, and confirm your transaction.</p></div><button class="btn btn-outline" type="button" id="refresh-operations">Refresh</button></header><div id="feedback" role="status" aria-live="polite"></div><section class="card"><h2>Available tasks</h2><p class="muted">Tasks follow your permissions. Complete the stated prerequisite when no eligible records are available.</p><div class="workflow-actions" id="actions"></div></section><div class="workflow-records"><section class="card"><h2>Payroll runs</h2><div id="runs"></div></section><section class="card"><h2>Active and pending tills</h2><div id="sessions"></div></section></div>`;
 page.querySelector('#refresh-operations').addEventListener('click',()=>renderOperations(page));
 const choices={employee_id:context.employees||[],customer_id:context.customers||[],sale_id:context.sales||[],pay_run:context.runs.filter(r=>r.status==='APPROVED'),product:context.products,warehouse:context.warehouses,destination:context.warehouses,order:context.orders.filter(o=>['APPROVED','PARTIALLY_RECEIVED'].includes(o.status)),receipt:context.receipts,invoice:context.invoices.filter(i=>['MATCHED','PARTIAL'].includes(i.status)),run:context.runs.filter(r=>r.status==='DRAFT'),session:context.sessions.filter(s=>s.status==='OPEN'),review_session:context.sessions.filter(s=>s.status==='PENDING_REVIEW')};
 if(can('procurement:supplier') || can('inventory:manage')) {
  const button=document.createElement('button');button.type='button';button.className='btn btn-primary';button.textContent='Set product prices';
  button.addEventListener('click',async()=>{
   button.disabled=true;
   try {
    const products=await apiRequest('/api/catalogue/pricing');
    if(!products.length) {page.querySelector('#feedback').textContent='Create or import products before setting prices.';return;}
    const dialog=openDialog({title:'Set product prices',description:'Enter verified prices. Saving activates the product; stock is received separately.',bodyHtml:selectField('product','Product',optionMarkup(products),true)+field('price','Selling price (UGX)','type="number" min="0.01" step="0.01" required')+field('cost','Unit cost (UGX)','type="number" min="0" step="0.01" required'),submitLabel:'Save prices and activate',onSubmit:async f=>{
     await apiRequest(`/api/products/${num(f,'product')}/pricing`,{method:'PATCH',body:JSON.stringify({unitprice:f.get('price'),costprice:f.get('cost'),is_active:true})});
     await renderOperations(page);page.querySelector('#feedback').textContent='Product prices saved and product activated.';
    }});
    dialog.querySelector('[name="product"]').addEventListener('change',event=>{
     const product=products.find(p=>p.id===Number(event.target.value));
     dialog.querySelector('[name="price"]').value=product?.unitprice||'';
     dialog.querySelector('[name="cost"]').value=product?.costprice||'';
    });
   } catch(error) {showNotice(page.querySelector('#feedback'),error.message);}
   finally {button.disabled=false;}
  });page.querySelector('#actions').append(button);
 }
 for(const [name,permission,endpoint,fields,payload] of WORKFLOW_ACTIONS.filter(a=>can(a[1]) && (a[0]!=='Process return' || can('sales:approve')))) {
  const wrapper=document.createElement('div');wrapper.className='workflow-task';
  const button=document.createElement('button');button.type='button';button.className='btn btn-outline';button.textContent=name;
  const missing=fields.find(key=>choices[key] && !choices[key].length);
  if(missing) {
   button.disabled=true;
   const hint=document.createElement('p');hint.className='muted';hint.textContent=`No eligible ${LABELS[missing].toLowerCase()} records. Complete that step first, then refresh.`;wrapper.append(hint);
  }
  button.addEventListener('click',()=>{
   const html=fields.map(key=>choices[key]?selectField(key,LABELS[key],optionMarkup(choices[key]),true):field(key,LABELS[key]||key,key==='month'?'type="month" required':key.includes('date')?'type="date" required':['quantity','cost','amount','actual_cash','variance'].includes(key)?`type="number" step="${['cost','amount','actual_cash'].includes(key)?'0.01':'0.001'}" ${key==='variance'?'':'min="'+(['quantity','amount'].includes(key)?'0.001':'0')+'"'} required`:'required maxlength="255"')).join('');
   const dialog=openDialog({title:name,description:'Review the values before saving. A receipt must use the approved order quantities and cost.',bodyHtml:html,submitLabel:'Confirm and save',onSubmit:async form=>{
    if(fields.includes('destination') && form.get('warehouse')===form.get('destination')) throw new Error('Choose different source and destination warehouses.');
    if(fields.includes('variance') && Number(form.get('variance'))===0) throw new Error('Enter a non-zero stock change.');
    if(fields.includes('end_date') && form.get('end_date')<form.get('start_date')) throw new Error('End date must be on or after the start date.');
    await apiRequest(typeof endpoint==='function'?endpoint(form):endpoint,{method:'POST',body:JSON.stringify(payload(form,context))});
    await renderOperations(page);page.querySelector('#feedback').textContent=name+' saved successfully.';
   }});
   const parent=dialog.querySelector('[name="order"], [name="sale_id"]');
   const productSelect=dialog.querySelector('[name="product"]');
   if(parent && productSelect) {
    const updateLine=()=>{
     const record=(fields.includes('order')?context.orders:context.sales).find(r=>r.id===Number(parent.value));
     const line=record?.items.find(i=>i.item_id===Number(productSelect.value));
     const quantity=dialog.querySelector('[name="quantity"]');
     if(quantity) {quantity.max=line?.quantity||'';quantity.value=line?.quantity||'';}
     const cost=dialog.querySelector('[name="cost"]');
     if(cost && line) cost.value=line.unit_cost;
    };
    parent.addEventListener('change',()=>{
     const record=(fields.includes('order')?context.orders:context.sales).find(r=>r.id===Number(parent.value));
     const eligible=context.products.filter(p=>record?.items.some(i=>i.item_id===p.id && Number(i.quantity)>0));
     productSelect.innerHTML=optionMarkup(eligible);updateLine();
    });
    productSelect.innerHTML=optionMarkup([]);productSelect.addEventListener('change',updateLine);
   }
  });wrapper.prepend(button);page.querySelector('#actions').append(wrapper);
 }
 if(!page.querySelector('#actions').children.length) page.querySelector('#actions').textContent='Your account has no transaction permissions.';
 renderTable(page.querySelector('#runs'),{columns:[{header:'Run',key:'id'},{header:'Month',key:'month'},{header:'Status',key:'status'},{header:'Net pay',key:'total'}],data:context.runs});
 renderTable(page.querySelector('#sessions'),{columns:[{header:'Till',key:'id'},{header:'Status',key:'status'},{header:'Expected cash',key:'expected'},{header:'Variance',key:'variance'}],data:context.sessions});
}
