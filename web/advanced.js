(() => {
  const nav = ["Vision", "Agent", "Devices", "Avatar", "Together", "Physical"];
  let active = null;
  const B = () => window.ReBounceBridge;
  const esc = value => B().esc(value);
  const api = B().api;
  const cid = B().cid;

  function stat(label, value) {
    return '<div class="card"><div class="metric">' + esc(value) + '</div><div class="metric-label">' + esc(label) + '</div></div>';
  }

  function setTitle(view) {
    const t = document.querySelector(".topbar-title");
    if (t) t.textContent = view;
  }

  function injectNav() {
    const list = document.querySelector(".nav");
    if (!list) return;
    nav.forEach(name => {
      if (!list.querySelector('[data-advanced-view="' + name + '"]')) {
        const button = document.createElement("button");
        button.type = "button";
        button.dataset.advancedView = name;
        button.textContent = name;
        list.appendChild(button);
      }
    });
  }

  async function reload() {
    await B().load();
    renderActive();
  }

  function renderActive() {
    if (!active) return;
    injectNav();
    const v = document.querySelector("#view");
    if (!v) return;
    setTitle(active);
    ({
      Vision: renderVision,
      Agent: renderAgent,
      Devices: renderDevices,
      Avatar: renderAvatar,
      Together: renderTogether,
      Physical: renderPhysical
    }[active] || renderVision)(v);
    document.querySelectorAll(".nav button").forEach(b => b.classList.toggle("active", b.dataset.advancedView === active));
    document.querySelectorAll(".nav button[data-view]").forEach(b => b.classList.remove("active"));
  }

  function permissionButton(resource, level) {
    return '<button class="btn" data-advanced-permission="' + esc(resource) + '" data-max-level="' + level + '">Enable ' + esc(resource) + '</button>';
  }

  function renderVision(v) {
    const d = B().dashboard?.vision || {};
    const session = d.session || {};
    const context = d.context || {};
    const screenAllowed = !!d.privacy?.screen_permission?.allowed;
    v.innerHTML =
      '<div class="grid grid-3">' +
        stat("Screen access", screenAllowed ? "Enabled" : "Off") +
        stat("Session", d.active_session ? "Active" : "Stopped") +
        stat("Context", "Ephemeral") +
      '</div>' +
      '<div class="grid grid-2" style="margin-top:18px">' +
        '<section class="card"><div class="eyebrow">stage 10 · vision / screen</div><h2>See only what you intentionally show</h2>' +
        '<p class="muted">Sessions expire, raw captures are never retained, and visual context is short-lived.</p>' +
        '<div class="row wrap">' +
          (screenAllowed ? "" : permissionButton("screen", 1)) +
          '<button class="btn primary" data-action="vision-start">Start screen session</button>' +
          '<button class="btn" data-action="vision-end">End session</button>' +
        '</div>' +
        '<div class="stack" style="margin-top:14px"><input class="input" id="vision-window" placeholder="Window / app title">' +
        '<input class="input" id="vision-app" placeholder="Application"><input class="input" id="vision-url" placeholder="URL optional">' +
        '<textarea class="textarea" id="vision-observation" placeholder="What the visual adapter sees"></textarea>' +
        '<input class="input" id="vision-shot" type="file" accept="image/*"><button class="btn" data-action="vision-observe">Share this visual context</button></div></section>' +
        '<section class="card"><div class="eyebrow">privacy boundary</div><h2>' + esc(d.active_session ? "Active session" : "No active session") + '</h2>' +
        '<div class="permission"><span>Purpose</span><span>' + esc(session.purpose || "—") + '</span></div>' +
        '<div class="permission"><span>Expires</span><span>' + esc(session.expires_at || "—") + '</span></div>' +
        '<div class="permission"><span>Raw capture retained</span><span class="badge off">No</span></div>' +
        '<div class="section-head" style="margin-top:16px"><h2>Latest context</h2></div>' +
        '<p class="muted">' + esc(context.observation || "Nothing shared yet.") + '</p>' +
        '<div class="small muted">' + esc(context.window_title || "") + ' ' + esc(context.app_name || "") + '</div></section>' +
      '</div>';
  }

  function renderAgent(v) {
    const a = B().dashboard?.agent || {};
    const plans = a.plans || [];
    const jobs = a.jobs || [];
    const deps = a.delegations || [];
    v.innerHTML =
      '<div class="grid grid-3">' + stat("Plans", plans.length) + stat("Queued jobs", jobs.filter(x => x.status === "queued").length) + stat("Checkpoints", (a.checkpoints || []).length) + '</div>' +
      '<div class="grid grid-2" style="margin-top:18px"><section class="card"><div class="eyebrow">stage 11 · long-running agent</div>' +
      '<h2>Durable work that can resume</h2><p class="muted">Plans require approval by default. Jobs checkpoint and recover instead of disappearing.</p>' +
      '<div class="stack"><input class="input" id="agent-title" placeholder="Plan title"><textarea class="textarea" id="agent-goal" placeholder="Approved goal"></textarea>' +
      '<label class="row"><input id="agent-approval" type="checkbox" checked> Require plan approval</label><button class="btn primary" data-action="agent-create">Create plan</button>' +
      '<select class="select" id="agent-plan">' + (plans.map(x => '<option value="' + esc(x.id) + '">' + esc(x.title) + ' · ' + esc(x.status) + '</option>').join("") || '<option value="">Create a plan first</option>') + '</select>' +
      '<input class="input" id="agent-step-title" placeholder="Job title"><textarea class="textarea" id="agent-step" placeholder="Step the agent should pursue"></textarea>' +
      '<button class="btn" data-action="agent-add-job">Add checkpointed job</button><div class="row">' +
      '<button class="btn" data-action="agent-approve">Approve selected plan</button><button class="btn primary" data-action="agent-run">Run next step</button><button class="btn" data-action="agent-recover">Recover stale work</button></div></div></section>' +
      '<section class="card"><div class="eyebrow">specialists + checkpoints</div><h2>One identity, bounded workers</h2><div class="list">' +
      (jobs.slice(0, 8).map(x => '<div class="goal"><strong>' + esc(x.title) + '</strong><div class="small muted">' + esc(x.status) + ' · attempts ' + esc(x.attempts) + '</div><p class="muted small">' + esc(x.step) + '</p></div>').join("") || '<div class="empty">No durable jobs yet.</div>') +
      '</div><div class="section-head" style="margin-top:14px"><h2>Delegations</h2><button class="btn" data-action="agent-delegate" ' + (jobs.length ? "" : "disabled") + '>Propose specialist</button></div>' +
      '<div class="small muted">' + (deps.slice(0, 4).map(x => esc(x.specialist) + ' · ' + esc(x.status)).join(" · ") || "No specialist delegation proposed.") + '</div></section></div>';
  }

  function renderDevices(v) {
    const d = B().dashboard?.devices || {};
    const devs = d.devices || [];
    const offline = d.offline_queue || [];
    const events = d.recent_sync || [];
    v.innerHTML =
      '<div class="grid grid-3">' + stat("Devices", devs.length) + stat("Offline queue", offline.length) + stat("Sync events", events.length) + '</div>' +
      '<div class="grid grid-2" style="margin-top:18px"><section class="card"><div class="eyebrow">stage 12 · multi-device</div><h2>Same companion everywhere</h2>' +
      '<p class="muted">Register web, phone, laptop or future clients. Ordered sync cursors support handoff and offline queues.</p>' +
      '<div class="stack"><input class="input" id="device-name" placeholder="Device name"><select class="select" id="device-kind"><option>desktop</option><option>phone</option><option>laptop</option><option>web</option><option>wearable</option></select>' +
      '<input class="input" id="device-platform" placeholder="Platform"><input class="input" id="device-capabilities" placeholder="chat,voice,vision"><button class="btn primary" data-action="device-register">Register device</button>' +
      '<select class="select" id="device-select">' + (devs.map(x => '<option value="' + esc(x.id) + '">' + esc(x.name) + ' · ' + esc(x.status) + '</option>').join("") || '<option value="">Register a device first</option>') + '</select>' +
      '<div class="row"><button class="btn" data-action="device-heartbeat">Heartbeat</button><button class="btn" data-action="device-sync">Push sync event</button><button class="btn" data-action="device-pull">Pull updates</button><button class="btn" data-action="device-handoff">Create handoff</button></div></div></section>' +
      '<section class="card"><div class="eyebrow">continuity</div><h2>Recent sync</h2><div class="list">' +
      (events.slice(0, 10).map(x => '<div class="goal"><strong>#' + esc(x.sequence) + ' · ' + esc(x.event_type) + '</strong><div class="small muted">' + esc(x.created_at) + '</div></div>').join("") || '<div class="empty">No sync events yet.</div>') +
      '</div><div class="section-head" style="margin-top:16px"><h2>Offline work</h2></div><div class="small muted">' +
      (offline.slice(0, 6).map(x => esc(x.operation) + ' · ' + esc(x.status)).join(" · ") || "Nothing waiting offline.") + '</div></section></div>';
  }

  function renderAvatar(v) {
    const e = B().dashboard?.embodiment || {};
    const p = e.profile || {};
    const room = e.room || {};
    v.innerHTML =
      '<div class="grid grid-2"><section class="card"><div class="eyebrow">stage 13 · advanced embodiment</div><h2>Give ' + esc(B().state.companion.name) + ' a body</h2>' +
      '<p class="muted">Asset adapters stay separate from identity. Start with the CSS orb, then point to Live2D, VRM or another renderer.</p>' +
      '<div class="stack"><input class="input" id="avatar-profile" value="' + esc(p.profile_name || "ReBounce avatar") + '" placeholder="Profile name">' +
      '<select class="select" id="avatar-kind"><option ' + (p.asset_kind === "css-orb" ? "selected" : "") + '>css-orb</option><option ' + (p.asset_kind === "live2d" ? "selected" : "") + '>live2d</option><option ' + (p.asset_kind === "vrm" ? "selected" : "") + '>vrm</option></select>' +
      '<input class="input" id="avatar-ref" value="' + esc(p.asset_ref || "") + '" placeholder="Asset URL or local ref"><input class="input" id="avatar-expressions" value="' + esc(p.expression_set || "calm,joy,focus,curious") + '">' +
      '<select class="select" id="avatar-animation"><option>subtle</option><option>expressive</option><option>ambient</option></select><button class="btn primary" data-action="avatar-save">Save embodiment</button></div></section>' +
      '<section class="card"><div class="eyebrow">persistent room</div><h2>Companion room</h2><div class="stack"><input class="input" id="room-name" value="' + esc(room.name || "Companion Room") + '">' +
      '<select class="select" id="room-theme"><option ' + (room.theme === "midnight" ? "selected" : "") + '>midnight</option><option>glass</option><option>sunrise</option><option>forest</option></select>' +
      '<button class="btn" data-action="room-save">Save room</button><input class="input" id="room-object-name" placeholder="Persistent object name"><button class="btn" data-action="room-object">Add room object</button></div>' +
      '<div class="status-line">' + esc(p.profile_name || "No avatar configured") + ' · ' + esc(p.animation_style || "subtle") + '</div></section></div>';
  }

  function renderTogether(v) {
    const t = B().dashboard?.together || {};
    const acts = t.activities || [];
    v.innerHTML =
      '<div class="grid grid-3">' + stat("Activities", acts.length) + stat("Active", acts.filter(x => x.status === "active").length) + stat("Events", (t.events || []).length) + '</div>' +
      '<div class="grid grid-2" style="margin-top:18px"><section class="card"><div class="eyebrow">stage 14 · shared activities</div><h2>Do things together</h2>' +
      '<p class="muted">Shared state supports watch, listen, game, study and creative sessions.</p><div class="stack"><select class="select" id="together-type"><option>watch</option><option>listen</option><option>game</option><option>study</option><option>creative</option></select>' +
      '<input class="input" id="together-title" placeholder="Activity title"><button class="btn primary" data-action="together-create">Start activity</button>' +
      '<select class="select" id="together-activity">' + (acts.map(x => '<option value="' + esc(x.id) + '">' + esc(x.title) + ' · ' + esc(x.status) + '</option>').join("") || '<option value="">Start an activity first</option>') + '</select>' +
      '<div class="row"><button class="btn" data-action="together-pause">Pause</button><button class="btn" data-action="together-complete">Complete</button><button class="btn" data-action="together-event">Add event</button></div></div></section>' +
      '<section class="card"><div class="eyebrow">shared timeline</div><h2>Recent activity</h2><div class="list">' +
      (acts.slice(0, 10).map(x => '<div class="goal"><strong>' + esc(x.activity_type) + ' · ' + esc(x.title) + '</strong><div class="small muted">' + esc(x.status) + ' · ' + esc(x.started_at || "") + '</div></div>').join("") || '<div class="empty">No shared activities yet.</div>') +
      '</div></section></div>';
  }

  function renderPhysical(v) {
    const p = B().dashboard?.physical || {};
    const devs = p.devices || [];
    const cmds = p.commands || [];
    v.innerHTML =
      '<div class="grid grid-3">' + stat("Devices", devs.length) + stat("Commands", cmds.length) + stat("Enabled", devs.filter(x => x.enabled).length) + '</div>' +
      '<div class="grid grid-2" style="margin-top:18px"><section class="card"><div class="eyebrow">stage 15 · wearable / ar / physical</div><h2>Extend ReBounce safely</h2>' +
      '<p class="muted">The simulator is included for testing. Real wearables, home devices and robotics stay disabled until explicitly permitted.</p>' +
      '<div class="stack"><input class="input" id="physical-name" placeholder="Device name"><select class="select" id="physical-kind"><option>haptic</option><option>light</option><option>speaker</option><option>smart_home</option><option>wearable</option><option>robot</option></select>' +
      '<input class="input" id="physical-location" placeholder="Location"><button class="btn" data-action="physical-register">Register simulator</button>' +
      '<select class="select" id="physical-device">' + (devs.map(x => '<option value="' + esc(x.id) + '">' + esc(x.name) + ' · ' + (x.enabled ? "enabled" : "disabled") + '</option>').join("") || '<option value="">Register a device first</option>') + '</select>' +
      '<div class="row"><button class="btn" data-advanced-permission="physical_devices" data-max-level="3">Enable physical controls</button><button class="btn" data-advanced-permission="smart_home" data-max-level="3">Enable smart-home</button><button class="btn" data-action="physical-enable">Enable selected</button></div>' +
      '<input class="input" id="physical-command" placeholder="Command, for example pulse"><button class="btn primary" data-action="physical-command">Queue command</button></div></section>' +
      '<section class="card"><div class="eyebrow">safety boundary</div><h2>Command log</h2><div class="list">' +
      (cmds.slice(0, 10).map(x => '<div class="goal"><strong>' + esc(x.command) + '</strong><div class="small muted">' + esc(x.status) + ' · L' + esc(x.requested_level) + '</div>' +
      (x.status === "pending_approval" ? '<div class="row"><button class="btn primary" data-physical-resolve="' + esc(x.id) + '" data-approved="true">Approve</button><button class="btn danger" data-physical-resolve="' + esc(x.id) + '" data-approved="false">Reject</button></div>' : '') + '</div>').join("") || '<div class="empty">No physical commands yet.</div>') +
      '</div><p class="small muted">Approval-required commands are stored durably and resolved separately from model authority.</p></section></div>';
  }

  async function dispatch(action, target) {
    const id = cid();
    if (!id) return;
    if (target.advancedPermission) {
      await api("/v1/companions/" + id + "/permissions/" + target.advancedPermission, {method:"PATCH", body:JSON.stringify({allowed:true,max_level:Number(target.maxLevel||1)})});
      return reload();
    }
    if (action === "vision-start") await api("/v1/companions/" + id + "/vision",{method:"POST",body:JSON.stringify({action:"start",minutes:15})});
    else if (action === "vision-end") await api("/v1/companions/" + id + "/vision",{method:"POST",body:JSON.stringify({action:"end"})});
    else if (action === "vision-observe") {
      let shot = null; const file = document.querySelector("#vision-shot")?.files?.[0];
      if (file) shot = await new Promise(resolve => {const fr = new FileReader();fr.onload=()=>resolve(String(fr.result||"").split(",")[1]||"");fr.readAsDataURL(file);});
      await api("/v1/companions/" + id + "/vision",{method:"POST",body:JSON.stringify({action:"observe",session_id:B().dashboard?.vision?.session?.id||"",window_title:document.querySelector("#vision-window")?.value||"",app_name:document.querySelector("#vision-app")?.value||"",url:document.querySelector("#vision-url")?.value||"",observation:document.querySelector("#vision-observation")?.value||"",screenshot_b64:shot})});
    } else if (action === "agent-create") await api("/v1/companions/" + id + "/agent",{method:"POST",body:JSON.stringify({action:"create_plan",title:document.querySelector("#agent-title").value,goal:document.querySelector("#agent-goal").value,approval_required:document.querySelector("#agent-approval").checked})});
    else if (action === "agent-add-job") await api("/v1/companions/" + id + "/agent",{method:"POST",body:JSON.stringify({action:"add_job",plan_id:document.querySelector("#agent-plan").value,title:document.querySelector("#agent-step-title").value,step:document.querySelector("#agent-step").value})});
    else if (action === "agent-approve") await api("/v1/companions/" + id + "/agent",{method:"POST",body:JSON.stringify({action:"approve_plan",plan_id:document.querySelector("#agent-plan").value,approved:true})});
    else if (action === "agent-run") await api("/v1/companions/" + id + "/agent",{method:"POST",body:JSON.stringify({action:"run",plan_id:document.querySelector("#agent-plan").value})});
    else if (action === "agent-recover") await api("/v1/companions/" + id + "/agent",{method:"POST",body:JSON.stringify({action:"recover"})});
    else if (action === "agent-delegate") {
      const job = B().dashboard?.agent?.jobs?.[0]; if (!job) return;
      await api("/v1/companions/" + id + "/agent",{method:"POST",body:JSON.stringify({action:"delegate",job_id:job.id,specialist:"researcher",scope:"bounded research assistance"})});
    } else if (action === "device-register") await api("/v1/companions/" + id + "/devices",{method:"POST",body:JSON.stringify({action:"register",name:document.querySelector("#device-name").value,kind:document.querySelector("#device-kind").value,platform:document.querySelector("#device-platform").value||"web",capabilities:document.querySelector("#device-capabilities").value.split(",").map(x=>x.trim()).filter(Boolean)})});
    else if (action === "device-heartbeat") await api("/v1/companions/" + id + "/devices",{method:"POST",body:JSON.stringify({action:"heartbeat",device_id:document.querySelector("#device-select").value})});
    else if (action === "device-sync") await api("/v1/companions/" + id + "/devices",{method:"POST",body:JSON.stringify({action:"sync",device_id:document.querySelector("#device-select").value,event_type:"state.changed",payload:{view:active}})});
    else if (action === "device-pull") {const out=await api("/v1/companions/" + id + "/devices",{method:"POST",body:JSON.stringify({action:"pull",cursor:0})});alert("Received " + (out.events?.length||0) + " sync events");return;}
    else if (action === "device-handoff") {const out=await api("/v1/companions/" + id + "/devices",{method:"POST",body:JSON.stringify({action:"handoff",source_device:document.querySelector("#device-select").value,ttl_minutes:10})});alert("Handoff created: " + out.token.slice(0,8) + "…");return;}
    else if (action === "avatar-save") await api("/v1/companions/" + id + "/embodiment",{method:"POST",body:JSON.stringify({action:"configure",profile_name:document.querySelector("#avatar-profile").value,asset_kind:document.querySelector("#avatar-kind").value,asset_ref:document.querySelector("#avatar-ref").value,expression_set:document.querySelector("#avatar-expressions").value,animation_style:document.querySelector("#avatar-animation").value})});
    else if (action === "room-save") await api("/v1/companions/" + id + "/embodiment",{method:"POST",body:JSON.stringify({action:"room",name:document.querySelector("#room-name").value,theme:document.querySelector("#room-theme").value})});
    else if (action === "room-object") await api("/v1/companions/" + id + "/embodiment",{method:"POST",body:JSON.stringify({action:"object",name:document.querySelector("#room-object-name").value,kind:"memory-artifact",state:{created_from:"dashboard"}})});
    else if (action === "together-create") await api("/v1/companions/" + id + "/together",{method:"POST",body:JSON.stringify({action:"create",activity_type:document.querySelector("#together-type").value,title:document.querySelector("#together-title").value})});
    else if (action === "together-pause") await api("/v1/companions/" + id + "/together",{method:"POST",body:JSON.stringify({action:"update",activity_id:document.querySelector("#together-activity").value,status:"paused",state:{paused_at:new Date().toISOString()}})});
    else if (action === "together-complete") await api("/v1/companions/" + id + "/together",{method:"POST",body:JSON.stringify({action:"update",activity_id:document.querySelector("#together-activity").value,status:"completed",state:{completed_at:new Date().toISOString()}})});
    else if (action === "together-event") await api("/v1/companions/" + id + "/together",{method:"POST",body:JSON.stringify({action:"event",activity_id:document.querySelector("#together-activity").value,actor:"user",event_type:"interaction",payload:{view:"Together"}})});
    else if (action === "physical-register") await api("/v1/companions/" + id + "/physical",{method:"POST",body:JSON.stringify({action:"register",name:document.querySelector("#physical-name").value,kind:document.querySelector("#physical-kind").value,transport:"simulator",location:document.querySelector("#physical-location").value})});
    else if (action === "physical-enable") await api("/v1/companions/" + id + "/physical",{method:"POST",body:JSON.stringify({action:"enable",device_id:document.querySelector("#physical-device").value,enabled:true})});
    else if (action === "physical-command") await api("/v1/companions/" + id + "/physical",{method:"POST",body:JSON.stringify({action:"command",device_id:document.querySelector("#physical-device").value,command:document.querySelector("#physical-command").value,payload:{source:"dashboard"},requested_level:3,approved:false})});
    else if (target.physicalResolve) await api("/v1/companions/" + id + "/physical",{method:"POST",body:JSON.stringify({action:"resolve",command_id:target.physicalResolve,approved:target.approved==="true"})});
    else return;
    await reload();
  }

  document.addEventListener("click", async event => {
    const t = event.target.closest("button");
    if (!t) return;
    if (t.dataset.advancedView) {
      event.preventDefault();
      event.stopPropagation();
      active = t.dataset.advancedView;
      renderActive();
      return;
    }
    if (t.dataset.advancedPermission || t.dataset.physicalResolve || t.dataset.action?.startsWith("vision-") || t.dataset.action?.startsWith("agent-") || t.dataset.action?.startsWith("device-") || t.dataset.action?.startsWith("avatar-") || t.dataset.action?.startsWith("room-") || t.dataset.action?.startsWith("together-") || t.dataset.action?.startsWith("physical-")) {
      try {
        event.preventDefault();
        await dispatch(t.dataset.action || "", {
          advancedPermission:t.dataset.advancedPermission,
          maxLevel:t.dataset.maxLevel,
          physicalResolve:t.dataset.physicalResolve,
          approved:t.dataset.approved
        });
      } catch (err) {
        alert(err.message);
      }
    }
  });

  const observer = new MutationObserver(() => injectNav());
  observer.observe(document.body, {subtree:true, childList:true});
  setTimeout(injectNav, 0);
  document.addEventListener("click", event => { if (event.target.closest("button[data-view]")) active = null; });
})();