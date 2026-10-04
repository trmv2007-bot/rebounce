const safeStorage={get(k){try{return localStorage.getItem(k)}catch{return null}},set(k,v){try{localStorage.setItem(k,v)}catch{}}};
const uid=()=>globalThis.crypto?.randomUUID?.()||`mutwsk24-${Math.random().toString(36).slice(2)}`;
const state={userId:safeStorage.get("rebounce_user_id")||uid(),companion:null,view:"Chat",conversationId:null,dashboard:null,provider:null,sending:false};
safeStorage.set("rebounce_user_id",state.userId);
const $=s=>document.querySelector(s), esc=s=>String(s??"").replace(/[&<>"]/g,c=>({"&":"&amp;","<":"&lt;",">":"&gt;",'"':"&quot;"}[c]));

async function api(path,opt={}){
  const r=await fetch(path,{headers:{"Content-Type":"application/json",...(opt.headers||{})},...opt});
  const data=await r.json().catch(()=>({}));
  if(!r.ok) throw Error(data.error||`HTTP ${r.status}`);
  return data;
}
const cid=()=>state.companion?.companion_id;
async function load(){
  if(!cid())return;
  state.dashboard=await api(`/v1/companions/${cid()}/dashboard`);
  state.provider=state.dashboard.provider||await api("/v1/config/provider");
  if(state.conversationId){
    const d=await api(`/v1/companions/${cid()}/conversations/${state.conversationId}`);
    state.dashboard.messages=d.messages||[];
  }else if(state.dashboard.conversations?.[0]){
    state.conversationId=state.dashboard.conversations[0].id;
    const d=await api(`/v1/companions/${cid()}/conversations/${state.conversationId}`);
    state.dashboard.messages=d.messages||[];
  }else state.dashboard.messages=[];
}
function modal(html){$("#modal-root").innerHTML=`<div class="modal"><div class="dialog">${html}</div></div>`}
function closeModal(){$("#modal-root").innerHTML=""}
function shell(){
  document.querySelector("#app").innerHTML=`<div class="shell">
    <aside class="sidebar">
      <div class="brand"><div class="orb"></div><div>ReBounce<div class="eyebrow">personal companion</div></div></div>
      <div class="companion-card"><div class="eyebrow">your companion</div><div class="companion-name">${esc(state.companion?.name||"Not created")}</div><div class="muted small">${esc(state.companion?.relationship_style||"Create an identity to begin")}</div></div>
      <nav class="nav">${["Chat","Memory","Relationship","Activity","Models","Settings"].map(v=>`<button data-view="${v}" class="${state.view===v?"active":""}">${v}</button>`).join("")}</nav>
      <div class="sidebar-spacer"></div><div class="muted small">Local-first · explicit controls · portable data</div>
    </aside>
    <section class="main"><header class="topbar"><div><div class="eyebrow">workspace</div><div class="topbar-title">${state.view}</div></div><div class="row"><div class="status"><span class="dot"></span>${esc(state.provider?.provider||"stub")}</div>${state.view==="Chat"?'<button class="btn primary" data-action="new-chat">New chat</button>':""}</div></header><main class="content" id="view"></main></section>
  </div>`;
  render();
}
function stat(label,value){return`<div class="card"><div class="metric">${esc(value)}</div><div class="metric-label">${esc(label)}</div></div>`}
function render(){
  const v=$("#view");
  if(!state.companion){v.innerHTML=`<div class="card hero"><div><div class="eyebrow">first launch</div><h1>Name your companion.</h1><p class="muted">Your chosen name, identity, memories and relationship survive model changes.</p><button class="btn primary" data-action="onboard">Create companion</button></div></div>`;return}
  const f={Chat:renderChat,Memory:renderMemory,Relationship:renderRelationship,Activity:renderActivity,Models:renderModels,Settings:renderSettings}[state.view];
  f(v);
}
function renderChat(v){
  const d=state.dashboard||{}, msgs=d.messages||[], conv=d.conversations||[];
  v.innerHTML=`<div class="chat-layout">
    <aside class="card"><div class="section-head"><h2>Conversations</h2><button class="btn" data-action="refresh">↻</button></div><div class="conversation-list">${conv.map(c=>`<div class="conversation ${c.id===state.conversationId?"active":""}" data-conversation="${esc(c.id)}"><strong>${esc((d.messagesByTitle?.[c.id])||"Conversation")}</strong><div class="small muted">${esc(c.updated_at||c.created_at)}</div></div>`).join("")||'<div class="empty">No conversations yet.</div>'}</div></aside>
    <section class="card"><div class="section-head"><div><div class="eyebrow">with ${esc(state.companion.name)}</div><h2>Chat that remembers context.</h2></div><div class="small muted">${esc(d.provider?.model||"stub")}</div></div>
    <div class="chipbar"><button class="chip" data-prompt="What do you remember about me?">What do you remember?</button><button class="chip" data-prompt="Help me plan my next step.">Plan next step</button><button class="chip" data-prompt="Let's work on a goal together.">Work on a goal</button></div>
    <div class="messages">${msgs.map(m=>`<div class="bubble ${m.role==="user"?"user":"assistant"}">${esc(m.content)}</div>`).join("")||'<div class="empty">Start a conversation with your companion.</div>'}</div>
    <form id="chat-form" class="composer"><textarea id="chat-input" class="textarea" placeholder="Say something…"></textarea><button class="btn primary" type="submit" ${state.sending?"disabled":""}>${state.sending?"Sending…":"Send"}</button></form></section>
  </div>`;
}
function memoryCard(m){
  return`<article class="memory"><div class="row between"><span class="type">${esc(m.memory_type)}</span><span class="small muted">${Math.round(Number(m.confidence)*100)}% confidence</span></div><p class="content">${esc(m.content)}</p><div class="row"><button class="btn" data-edit-memory="${esc(m.id)}">Correct</button><button class="btn danger" data-forget-memory="${esc(m.id)}">Forget</button></div></article>`
}
function renderMemory(v){
  const d=state.dashboard||{}, memories=d.memories||[];
  v.innerHTML=`<div class="section-head"><div><div class="eyebrow">memory engine</div><h2>What ${esc(state.companion.name)} remembers</h2></div><button class="btn primary" data-action="add-memory">Add memory</button></div>
  <div class="grid grid-2"><div class="card"><input class="input" id="memory-search" placeholder="Search memories…"><select class="select" id="memory-type" style="margin-top:10px"><option value="">All types</option><option>fact</option><option>preference</option><option>project</option><option>goal</option><option>episodic</option></select></div><div class="card"><div class="metric">${memories.length}</div><div class="metric-label">active memories</div><p class="muted small">User-owned, correctable and deletable. Provenance is recorded with each entry.</p></div></div>
  <div class="list" id="memory-list" style="margin-top:18px">${memories.map(memoryCard).join("")||'<div class="empty">No memories yet.</div>'}</div>`;
}
function renderRelationship(v){
  const d=state.dashboard||{}, r=d.relationship||{}, goals=d.goals||[], ms=d.milestones||[], cs=d.commitments||[], top=Object.entries(r.topics||{}).slice(0,7);
  v.innerHTML=`<div class="grid grid-3">${stat("Interactions",r.interactions||0)}${stat("Active days",r.active_days||0)}${stat("Current goals",goals.filter(g=>g.status==="active").length)}</div>
  <div class="grid grid-2" style="margin-top:18px">
    <section class="card"><div class="section-head"><h2>Shared history</h2><button class="btn" data-action="add-milestone">Add milestone</button></div><div class="list">${ms.map(m=>`<div class="timeline-item"><strong>${esc(m.title)}</strong><div class="small muted">${esc(m.created_at)}</div><p class="muted">${esc(m.description)}</p></div>`).join("")||'<div class="empty">No milestones yet.</div>'}</div></section>
    <section class="card"><div class="section-head"><h2>Recurring themes</h2></div><div class="chipbar">${top.map(([k,n])=>`<span class="chip">${esc(k)} · ${n}</span>`).join("")||'<span class="muted">Themes will appear as you talk.</span>'}</div><div class="section-head" style="margin-top:18px"><h2>Interaction style</h2></div><p class="muted">Directness ${Math.round((r.directness||.5)*100)}% · Warmth ${Math.round((r.warmth||.6)*100)}% · Detail ${Math.round((r.verbosity||.5)*100)}%</p></section>
  </div>
  <div class="grid grid-2" style="margin-top:18px">
    <section class="card"><div class="section-head"><h2>Goals</h2><button class="btn" data-action="add-goal">Add goal</button></div><div class="list">${goals.map(g=>`<div class="goal row between"><div><strong>${esc(g.title)}</strong><div class="small muted">${esc(g.status)}</div></div><button class="btn" data-goal-status="${esc(g.id)}" data-next-status="${g.status==="active"?"completed":"active"}">${g.status==="active"?"Complete":"Reactivate"}</button></div>`).join("")||'<div class="empty">No shared goals yet.</div>'}</div></section>
    <section class="card"><div class="section-head"><h2>Commitments</h2><button class="btn" data-action="add-commitment">Add commitment</button></div><div class="list">${cs.map(c=>`<div class="goal"><strong>${esc(c.title)}</strong><div class="small muted">${esc(c.due_at||"No due date")} · ${esc(c.status)}</div></div>`).join("")||'<div class="empty">No commitments yet.</div>'}</div></section>
  </div>`;
}
function renderActivity(v){
  const events=state.dashboard?.events||[];
  v.innerHTML=`<div class="section-head"><div><div class="eyebrow">audit trail</div><h2>What ReBounce has done</h2></div><button class="btn" data-action="refresh">Refresh</button></div><div class="list">${events.map(e=>`<div class="timeline-item"><div class="row between"><strong>${esc(e.event_type)}</strong><span class="small muted">${esc(e.created_at)}</span></div><pre class="small muted">${esc(JSON.stringify(JSON.parse(e.data_json||"{}"),null,2))}</pre></div>`).join("")||'<div class="empty">No activity yet.</div>'}</div>`;
}
function renderModels(v){
  const p=state.provider||{};
  v.innerHTML=`<div class="grid grid-2"><section class="card"><div class="eyebrow">model provider</div><h2>Choose the brain</h2><div class="stack"><select class="select" id="provider-kind"><option value="stub" ${p.provider==="stub"?"selected":""}>Stub / offline</option><option value="openai-compatible" ${p.provider!=="stub"?"selected":""}>OpenAI-compatible</option></select><input class="input" id="provider-url" value="${esc(p.base_url||"http://127.0.0.1:8080/v1")}" placeholder="http://127.0.0.1:8080/v1"><input class="input" id="provider-model" value="${esc(p.model||"")}" placeholder="Model name"><input class="input" id="provider-key" type="password" placeholder="API key (not stored in memory/database)"><div class="row"><button class="btn primary" data-action="save-provider">Save provider</button><button class="btn" data-action="test-provider">Test</button></div><div id="provider-result" class="small muted"></div></div></section><section class="card"><div class="eyebrow">architecture</div><h2>Identity ≠ model</h2><p class="muted">Your companion identity and memory live in ReBounce's SQLite store. The provider is a replaceable adapter.</p><div class="permission"><span>Current provider</span><span class="badge">${esc(p.provider||"stub")}</span></div><div class="permission"><span>Configured model</span><span>${esc(p.model||"—")}</span></div><div class="permission"><span>Secret persistence</span><span class="badge off">Process only</span></div></section></div>`;
}
function renderSettings(v){
  v.innerHTML=`<div class="grid grid-2"><section class="card"><div class="eyebrow">identity</div><h2>Companion settings</h2><div class="stack"><label class="small muted">Name<input class="input" id="setting-name" value="${esc(state.companion.name)}"></label><label class="small muted">Personality<textarea class="textarea" id="setting-personality">${esc(state.companion.personality)}</textarea></label><button class="btn primary" data-action="save-settings">Save identity</button><div id="settings-result" class="small muted"></div></div></section><section class="card"><div class="eyebrow">trust center</div><h2>What ReBounce can do</h2><div class="permission"><span>Conversation</span><span class="badge">Allowed</span></div><div class="permission"><span>Memory</span><span class="badge">Allowed</span></div><div class="permission"><span>Browser / tools</span><span class="badge off">Not enabled</span></div><div class="permission"><span>Filesystem</span><span class="badge off">Not enabled</span></div><div class="permission"><span>Email</span><span class="badge off">Not enabled</span></div><div class="permission"><span>Payments</span><span class="badge off">Prohibited</span></div><button class="btn" data-action="export">Export my ReBounce data</button></section></div>`;
}
function onboard(){modal(`<div class="eyebrow">first launch</div><h2>Name your companion</h2><p class="muted">This name becomes part of the persistent companion identity.</p><div class="stack"><input class="input" id="onboard-name" placeholder="e.g. Nova"><textarea class="textarea" id="onboard-personality" placeholder="Optional personality: calm, playful, direct…"></textarea><div class="row"><button class="btn ghost" data-action="close-modal">Cancel</button><button class="btn primary" data-action="create-companion">Create</button></div></div>`);setTimeout(()=>$("#onboard-name")?.focus(),0)}
async function sendChat(){
  const input=$("#chat-input"), content=input.value.trim(); if(!content||state.sending)return;
  state.sending=true;renderChat($("#view"));
  try{const d=await api(`/v1/companions/${cid()}/chat`,{method:"POST",body:JSON.stringify({content,conversation_id:state.conversationId})});state.conversationId=d.conversation_id;await load()}
  finally{state.sending=false} renderChat($("#view"));$("#chat-input")?.focus();
}
document.addEventListener("click",async e=>{
  const t=e.target;
  try{
    if(t.dataset.view){state.view=t.dataset.view;await load();shell();return}
    if(t.dataset.conversation){state.conversationId=t.dataset.conversation;await load();render();return}
    if(t.dataset.prompt){$("#chat-input").value=t.dataset.prompt;$("#chat-input").focus();return}
    if(t.dataset.action==="onboard")return onboard();
    if(t.dataset.action==="close-modal")return closeModal();
    if(t.dataset.action==="new-chat"){state.conversationId=null;state.dashboard.messages=[];render();return}
    if(t.dataset.action==="refresh"){await load();render();return}
    if(t.dataset.action==="create-companion"){
      const d=await api("/v1/companions",{method:"POST",body:JSON.stringify({user_id:state.userId,name:$("#onboard-name").value,personality:$("#onboard-personality").value})});
      state.companion=d;safeStorage.set("rebounce_companion_id",d.companion_id);closeModal();await load();shell();return
    }
    if(t.dataset.action==="add-memory"){return modal(`<div class="eyebrow">memory</div><h2>Add a memory</h2><div class="stack"><select class="select" id="mem-type"><option>fact</option><option>preference</option><option>project</option><option>goal</option><option>episodic</option></select><textarea class="textarea" id="mem-content" placeholder="What should ReBounce remember?"></textarea><input class="input" id="mem-importance" type="number" min=".1" max="1" step=".05" value=".75"><div class="row"><button class="btn ghost" data-action="close-modal">Cancel</button><button class="btn primary" data-action="create-memory">Save memory</button></div></div>`)}
    if(t.dataset.action==="create-memory"){await api(`/v1/companions/${cid()}/memories`,{method:"POST",body:JSON.stringify({memory_type:$("#mem-type").value,content:$("#mem-content").value,importance:Number($("#mem-importance").value)})});closeModal();await load();render();return}
    if(t.dataset.editMemory){const m=state.dashboard.memories.find(x=>x.id===t.dataset.editMemory);return modal(`<div class="eyebrow">correction</div><h2>Correct memory</h2><textarea class="textarea" id="edit-memory-content">${esc(m.content)}</textarea><div class="row"><button class="btn ghost" data-action="close-modal">Cancel</button><button class="btn primary" data-save-memory="${m.id}">Save correction</button></div>`)}
    if(t.dataset.saveMemory){await api(`/v1/companions/${cid()}/memories/${t.dataset.saveMemory}`,{method:"PATCH",body:JSON.stringify({content:$("#edit-memory-content").value})});closeModal();await load();render();return}
    if(t.dataset.forgetMemory){if(confirm("Forget this memory?")){await api(`/v1/companions/${cid()}/memories/${t.dataset.forgetMemory}`,{method:"DELETE"});await load();render()}return}
    if(t.dataset.action==="add-goal")return modal(`<div class="eyebrow">goal</div><h2>Add a shared goal</h2><input class="input" id="goal-title" placeholder="What are we working toward?"><div class="row"><button class="btn ghost" data-action="close-modal">Cancel</button><button class="btn primary" data-create-goal>Save goal</button></div>`);
    if(t.dataset.createGoal!==undefined){await api(`/v1/companions/${cid()}/goals`,{method:"POST",body:JSON.stringify({title:$("#goal-title").value})});closeModal();await load();render();return}
    if(t.dataset.goalStatus){await api(`/v1/companions/${cid()}/goals/${t.dataset.goalStatus}`,{method:"PATCH",body:JSON.stringify({status:t.dataset.nextStatus})});await load();render();return}
    if(t.dataset.action==="add-milestone")return modal(`<div class="eyebrow">milestone</div><h2>Add a milestone</h2><div class="stack"><input class="input" id="milestone-title" placeholder="Milestone title"><textarea class="textarea" id="milestone-description" placeholder="Optional note"></textarea><div class="row"><button class="btn ghost" data-action="close-modal">Cancel</button><button class="btn primary" data-create-milestone>Save milestone</button></div></div>`);
    if(t.dataset.createMilestone!==undefined){await api(`/v1/companions/${cid()}/milestones`,{method:"POST",body:JSON.stringify({title:$("#milestone-title").value,description:$("#milestone-description").value})});closeModal();await load();render();return}
    if(t.dataset.action==="add-commitment")return modal(`<div class="eyebrow">commitment</div><h2>Add a commitment</h2><div class="stack"><input class="input" id="commitment-title" placeholder="What should stay on our radar?"><input class="input" id="commitment-due" type="datetime-local"><div class="row"><button class="btn ghost" data-action="close-modal">Cancel</button><button class="btn primary" data-create-commitment>Save commitment</button></div></div>`);
    if(t.dataset.createCommitment!==undefined){await api(`/v1/companions/${cid()}/commitments`,{method:"POST",body:JSON.stringify({title:$("#commitment-title").value,due_at:$("#commitment-due").value||null})});closeModal();await load();render();return}
    if(t.dataset.action==="save-provider"){const kind=$("#provider-kind").value, body={provider:kind,base_url:$("#provider-url").value,model:$("#provider-model").value};if($("#provider-key").value)body.api_key=$("#provider-key").value;state.provider=await api("/v1/config/provider",{method:"POST",body:JSON.stringify(body)});render();return}
    if(t.dataset.action==="test-provider"){const out=$("#provider-result");out.textContent="Testing…";try{const d=await api("/v1/config/provider/test",{method:"POST",body:"{}"});out.textContent=`Connected: ${d.provider} / ${d.model}`;out.style.color="var(--ok)"}catch(err){out.textContent=`Failed: ${err.message}`;out.style.color="var(--danger)"}return}
    if(t.dataset.action==="save-settings"){state.companion=await api(`/v1/companions/${cid()}/settings`,{method:"PATCH",body:JSON.stringify({name:$("#setting-name").value,personality:$("#setting-personality").value})});$("#settings-result").textContent="Identity saved.";shell();return}
    if(t.dataset.action==="export"){const data=await api(`/v1/companions/${cid()}/export`),blob=new Blob([JSON.stringify(data,null,2)],{type:"application/json"}),a=document.createElement("a");a.href=URL.createObjectURL(blob);a.download=`rebounce-${state.companion.name.replace(/[^a-z0-9]+/gi,"-").toLowerCase()}.json`;a.click();URL.revokeObjectURL(a.href);return}
  }catch(err){alert(err.message)}
});
document.addEventListener("submit",async e=>{if(e.target.id==="chat-form"){e.preventDefault();try{await sendChat()}catch(err){state.sending=false;alert(err.message);render()}}});
document.addEventListener("input",e=>{
  if(!state.dashboard)return;
  if(e.target.id==="memory-search"||e.target.id==="memory-type"){
    const q=$("#memory-search").value.toLowerCase(),type=$("#memory-type").value,all=state.dashboard.memories||[];
    $("#memory-list").innerHTML=all.filter(m=>(!q||m.content.toLowerCase().includes(q))&&(!type||m.memory_type===type)).map(memoryCard).join("")||'<div class="empty">No matching memories.</div>';
  }
});
async function boot(){
  try{
    const d=await api(`/v1/companions?user_id=${encodeURIComponent(state.userId)}`);
    if(d.companions?.length){const saved=safeStorage.get("rebounce_companion_id");state.companion=d.companions.find(c=>c.companion_id===saved)||d.companions[0];safeStorage.set("rebounce_companion_id",state.companion.companion_id);await load()}
    shell();
  }catch(err){document.querySelector("#app").innerHTML=`<div class="content"><div class="card"><h2>ReBounce couldn't start</h2><p class="muted">${esc(err.message)}</p></div></div>`}
}
boot();
