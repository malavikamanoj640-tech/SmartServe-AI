(() => {
  const $ = (id) => document.getElementById(id);
  const esc = (v) => String(v ?? '').replace(/[&<>"']/g, c => ({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  async function api(url, options={}) {
    const res = await fetch(url,{headers:{'Content-Type':'application/json'},...options});
    const data = await res.json().catch(()=>({error:'Invalid server response'}));
    if(!res.ok) throw new Error(data.error || `Request failed (${res.status})`);
    return data;
  }
  function message(el,text,isError=false){ if(el){el.textContent=text;el.classList.toggle('error-text',isError);} }
  async function loadWaste(){
    const out=$('waste-result'); out.innerHTML='<div class="empty-state">Analyzing historical data…</div>';
    try{const d=await api('/api/waste-analysis?item='+encodeURIComponent($('waste-item').value));
      out.innerHTML=[['Prepared',d.prepared],['Sold',d.sold],['Estimated waste',d.waste],['Waste rate',d.waste_rate+'%']].map(([k,v])=>`<div class="kpi-card"><small>${k}</small><strong>${esc(v)}</strong><em>historical units</em></div>`).join('');
      message($('waste-note'),`${d.source}. ${d.note} Records analysed: ${d.observations}.`);
    }catch(e){message($('waste-note'),e.message,true);out.innerHTML='';}
  }
  async function loadInventory(){try{const a=await api('/api/inventory');$('inv-body').innerHTML=a.map(x=>`<tr><td>${esc(x.ingredient)}</td><td>${Number(x.quantity).toFixed(3)}</td><td>${esc(x.unit)}</td><td>₹${Number(x.unit_cost).toFixed(2)}</td><td>₹${(x.quantity*x.unit_cost).toFixed(2)}</td><td><button class="btn-small" data-del-inv="${x.id}">Delete</button></td></tr>`).join('')||'<tr><td colspan="6">No ingredients saved.</td></tr>';}catch(e){message($('inv-body'),e.message,true);}}
  async function saveInventory(){try{await api('/api/inventory',{method:'POST',body:JSON.stringify({ingredient:$('inv-name').value,quantity:$('inv-qty').value,unit:$('inv-unit').value,unit_cost:$('inv-cost').value})});['inv-name','inv-qty','inv-unit','inv-cost'].forEach(id=>$(id).value='');loadInventory();}catch(e){alert(e.message);}}
  async function loadSuppliers(){try{const a=await api('/api/suppliers');$('sup-body').innerHTML=a.map(x=>`<tr><td>${esc(x.name)}</td><td>${esc(x.contact)}</td><td>${esc(x.email)}</td><td>${esc(x.category)}</td><td><button class="btn-small" data-del-sup="${x.id}">Delete</button></td></tr>`).join('')||'<tr><td colspan="5">No suppliers saved.</td></tr>';$('po-supplier').innerHTML=a.map(x=>`<option value="${x.id}">${esc(x.name)}</option>`).join('')||'<option value="">Add a supplier first</option>';}catch(e){alert(e.message);}}
  async function loadPO(){try{const a=await api('/api/purchase-orders');$('po-body').innerHTML=a.map(x=>`<tr><td>#${x.id}</td><td>${esc(x.supplier_name||'—')}</td><td>${esc(x.ingredient)}</td><td>${x.quantity}</td><td>₹${Number(x.total).toFixed(2)}</td><td>${esc(x.status)}</td></tr>`).join('')||'<tr><td colspan="6">No purchase order drafts.</td></tr>';}catch(e){alert(e.message);}}
  async function loadFinance(){try{const d=await api('/api/finance');const t=d.totals;$('fin-kpis').innerHTML=[['Revenue','₹'+Number(t.revenue).toFixed(2)],['Cost','₹'+Number(t.cost).toFixed(2)],['Gross profit','₹'+Number(t.gross_profit).toFixed(2)],['Units sold',t.units]].map(([k,v])=>`<div class="kpi-card"><small>${k}</small><strong>${esc(v)}</strong></div>`).join('');$('fin-body').innerHTML=d.records.map(x=>`<tr><td>${esc(x.sale_date)}</td><td>${esc(x.item)}</td><td>${x.quantity}</td><td>₹${Number(x.revenue).toFixed(2)}</td><td>₹${Number(x.cost).toFixed(2)}</td><td>₹${Number(x.gross_profit).toFixed(2)}</td></tr>`).join('')||'<tr><td colspan="6">No sales records yet.</td></tr>';}catch(e){alert(e.message);}}
  async function checkOllama(){try{const d=await api('/api/assistant',{method:'POST',body:JSON.stringify({question:'Reply with: connection successful.',model:$('ollama-model').value})});message($('ollama-status-text'),'Connected to Ollama ('+d.model+').');}catch(e){message($('ollama-status-text'),e.message,true);}}
  async function askAssistant(){const q=$('assistant-question').value.trim();if(!q)return message($('assistant-answer'),'Enter a question first.',true);message($('assistant-answer'),'Thinking…');$('assistant-send').disabled=true;try{const d=await api('/api/assistant',{method:'POST',body:JSON.stringify({question:q,model:$('ollama-model').value})});message($('assistant-answer'),d.answer||'No response received.');}catch(e){message($('assistant-answer'),e.message,true);}finally{$('assistant-send').disabled=false;}}
  async function loadMonitor(){try{const d=await api('/api/model/metrics');$('monitor-status').innerHTML=[['Demand model',d.model_loaded?'Loaded':'Fallback mode'],['Historical dataset',d.dataset_loaded?'Available':'Unavailable'],['Evaluation metrics',d.metrics_available?'Available':'Not evaluated']].map(([k,v])=>`<div class="kpi-card"><small>${k}</small><strong>${esc(v)}</strong></div>`).join('');const m=d.metrics||{};const entries=Object.entries(m).filter(([k,v])=>typeof v==='number'||typeof v==='string');$('monitor-metrics').innerHTML=entries.map(([k,v])=>`<div class="kpi-card"><small>${esc(k)}</small><strong>${esc(v)}</strong></div>`).join('');message($('monitor-note'),d.status+' '+d.evaluation_note);}catch(e){message($('monitor-note'),e.message,true);}}
  document.addEventListener('click',async e=>{
    const inv=e.target.closest('[data-del-inv]'); if(inv){try{await api('/api/inventory/'+inv.dataset.delInv,{method:'DELETE'});loadInventory();}catch(x){alert(x.message);}}
    const sup=e.target.closest('[data-del-sup]'); if(sup){try{await api('/api/suppliers/'+sup.dataset.delSup,{method:'DELETE'});loadSuppliers();}catch(x){alert(x.message);}}
  });
  document.addEventListener('DOMContentLoaded',()=>{
    $('waste-load')?.addEventListener('click',loadWaste);$('inv-save')?.addEventListener('click',saveInventory);
    $('sup-save')?.addEventListener('click',async()=>{try{await api('/api/suppliers',{method:'POST',body:JSON.stringify({name:$('sup-name').value,contact:$('sup-contact').value,email:$('sup-email').value,category:$('sup-category').value})});['sup-name','sup-contact','sup-email','sup-category'].forEach(id=>$(id).value='');loadSuppliers();}catch(e){alert(e.message);}});
    $('po-save')?.addEventListener('click',async()=>{try{await api('/api/purchase-orders',{method:'POST',body:JSON.stringify({supplier_id:$('po-supplier').value,ingredient:$('po-item').value,quantity:$('po-qty').value,unit_price:$('po-price').value})});loadPO();}catch(e){alert(e.message);}});
    $('fin-save')?.addEventListener('click',async()=>{try{await api('/api/finance',{method:'POST',body:JSON.stringify({item:$('fin-item').value,quantity:$('fin-qty').value,selling_price:$('fin-price').value,unit_cost:$('fin-cost').value,sale_date:$('fin-date').value})});loadFinance();}catch(e){alert(e.message);}});
    $('assistant-send')?.addEventListener('click',askAssistant);$('ollama-status')?.addEventListener('click',checkOllama);$('monitor-refresh')?.addEventListener('click',loadMonitor);
    $('fin-date') && ($('fin-date').value=new Date().toISOString().slice(0,10));
    document.querySelectorAll('.tab-btn').forEach(b=>b.addEventListener('click',()=>{const t=b.dataset.tab;if(t==='waste')loadWaste();if(t==='inventory')loadInventory();if(t==='suppliers'){loadSuppliers();loadPO();}if(t==='profit')loadFinance();if(t==='monitor')loadMonitor();}));
  });
})();
