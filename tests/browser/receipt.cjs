const { chromium } = require(process.env.HW_PLAYWRIGHT_MODULE || 'playwright');
(async()=>{
 const browser=await chromium.launch({channel:'msedge',headless:true});
 try {
 const page=await browser.newPage({viewport:{width:1280,height:900}});
 const errors=[];page.on('pageerror',error=>errors.push(error.message));
 await page.goto((process.env.HW_TEST_URL || 'http://127.0.0.1:8876')+'/sales.html',{waitUntil:'domcontentloaded'});
 const current=await page.evaluate(async()=>await(await fetch('/api/cashier-sessions/current')).json());
 if(!current.has_active_session) {
 await page.locator('#open-cashier-session').waitFor();
 await page.locator('[name=warehouse_id]').selectOption('1');
 await page.locator('[name=opening_float]').fill('0');
 await page.getByRole('button',{name:'Open session',exact:true}).click();
 }
 await page.locator('#product-select').waitFor();
 await page.evaluate(()=>{localStorage.setItem('hw_theme','dark');document.documentElement.classList.add('dark');});
 const initial=await page.evaluate(async()=>({sales:await(await fetch('/api/sales')).json(),products:await(await fetch('/api/products?warehouse_id=1')).json()}));
 const options=await page.locator('#product-select option').allTextContents();
 if(!options.some(x=>x.includes('Browser test cement')) || options.some(x=>x.includes('Out of stock example'))) throw new Error('Wrong sellable items in dropdown');
 const colors=await page.locator('#product-select').evaluate(e=>({background:getComputedStyle(e).backgroundColor,color:getComputedStyle(e).color,scheme:getComputedStyle(e).colorScheme}));
 if(colors.background===colors.color || colors.scheme!=='dark')throw new Error('Unreadable dark select');
 await page.locator('#product-select').selectOption('1');
 await page.getByRole('button',{name:'Add item',exact:true}).click();
 await page.locator('[name=customername]').fill('Receipt test customer');
 await page.getByRole('button',{name:'Review & complete sale',exact:true}).click();
 await page.locator('[data-confirm-sale]').waitFor();
 if(await page.locator('#pos').isVisible())throw new Error('Cart still visible behind preview');
 const before=await page.evaluate(async()=>await(await fetch('/api/sales')).json());
 if(before.length!==initial.sales.length)throw new Error('Preview committed a sale');
 await page.locator('[data-confirm-sale]').click();
 await page.locator('[data-print-sale]').waitFor();
 const sales=await page.evaluate(async()=>await(await fetch('/api/sales')).json());
 const stock=await page.evaluate(async()=>await(await fetch('/api/products?warehouse_id=1')).json());
 if(sales.length!==initial.sales.length+1 || Number(sales[0].totalamount)!==200 || Number(stock.find(p=>p.itemid===1).available_stock)!==Number(initial.products.find(p=>p.itemid===1).available_stock)-1)throw new Error('Sale/receipt/stock disagree');
 await page.screenshot({path:'.codex-review/receipt-dark.png',fullPage:true});
 await page.setViewportSize({width:390,height:844});
 await page.waitForFunction(()=>document.querySelector('#hw-sidebar').getBoundingClientRect().right<=0);
 if(await page.locator('#pos').isVisible())throw new Error('Completed receipt should offer New sale before showing cart');
 if(await page.evaluate(()=>document.documentElement.scrollWidth>innerWidth))throw new Error('Mobile receipt overflow');
 await page.screenshot({path:'.codex-review/receipt-mobile.png',fullPage:true});
 if(errors.length)throw new Error(errors.join('; '));
 console.log('PASS: readable stock dropdown, no out-of-stock options, preview writes nothing, confirmed receipt/customer/stock agree, desktop/mobile fit.');
 } finally {await browser.close();}
})().catch(error=>{console.error(error);process.exit(1)});
