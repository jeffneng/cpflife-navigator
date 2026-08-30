(function(){
  // ---- state ----
  const state = {
    balance: 220400,
    gender: 'male',
    plan: 'standard',
    startAge: 65,
    lifeExpOverride: 0
  };

  // CPF anchor tables & assumptions, loaded from /data (via the server) so the
  // yearly-updated figures never need a code change here.
  let CPF = null;

  async function loadAssumptions(){
    const res = await fetch('/api/anchors');
    if (!res.ok) throw new Error('Failed to load CPF assumptions');
    CPF = await res.json();
  }

  // Piecewise-linear interpolation of payout/balance ratio between anchors,
  // parametrized by which payout field to read (age-65 or age-70 figures) —
  // interpolating the ratio rather than the raw payout keeps the curve shaped
  // like CPF's (payouts aren't linear in balance).
  function interpolatedPayout(bal, field){
    const pts = CPF.payoutAnchors.map(a => ({bal:a.balance, rate:a[field]/a.balance}));
    let rate;
    if (bal <= pts[0].bal) rate = pts[0].rate;
    else if (bal >= pts[pts.length-1].bal) rate = pts[pts.length-1].rate;
    else {
      rate = pts[pts.length-1].rate;
      for (let i=0;i<pts.length-1;i++){
        if (bal >= pts[i].bal && bal <= pts[i+1].bal){
          const t = (bal - pts[i].bal) / (pts[i+1].bal - pts[i].bal);
          rate = pts[i].rate + t*(pts[i+1].rate - pts[i].rate);
          break;
        }
      }
    }
    return bal * rate;
  }

  function lifeExpectancy(gender, override){
    if (override && override > 0) return override;
    return CPF.lifeExpectancy[gender];
  }

  function fmtMoney(n){
    return '$' + Math.round(n).toLocaleString('en-US');
  }

  function compute(){
    const bal = state.balance;

    // 1. base monthly payout at this balance (male, standard), at age 65 and
    //    age 70 — both interpolated directly from CPF's published anchors.
    const payout65 = interpolatedPayout(bal, 'monthlyPayout');
    const payout70 = interpolatedPayout(bal, 'monthlyPayoutAt70');

    // 2. deferral adjustment: rather than one flat bonus rate for every balance,
    //    derive the compound annual rate implied by *this balance's own*
    //    age-65 -> age-70 anchor ratio, so payouts at 65 and 70 land exactly on
    //    CPF's published figures and years in between are interpolated sensibly.
    const deferYears = state.startAge - 65;
    const impliedAnnualRate = Math.pow(payout70 / payout65, 1/5) - 1;
    let monthly = payout65 * Math.pow(1 + impliedAnnualRate, deferYears);

    // 3. gender adjustment
    monthly *= CPF.genderFactor[state.gender];

    // 4. plan adjustment
    monthly *= CPF.planFactor[state.plan];

    // premium at payout start = RA balance grown through any deferral years
    // at CPF's ongoing RA interest rate
    const premium = bal * Math.pow(1 + CPF.deferral.raInterestWhileDeferred, deferYears);

    const le = lifeExpectancy(state.gender, state.lifeExpOverride);

    return { monthly, premium, le, deferYears };
  }

  function buildSchedule(monthlyStart, startAge, le, plan){
    // returns array of {age, cum, monthly}
    const maxAge = Math.max(le + 8, startAge + 5, 95);
    const rows = [];
    let cum = 0;
    let curMonthly = monthlyStart;
    for (let age = startAge; age <= maxAge; age++){
      if (age > startAge && plan === 'escalating'){
        curMonthly = curMonthly * (1 + CPF.escalatingPlan.annualEscalationRate);
      }
      cum += curMonthly * 12;
      rows.push({age, cum, monthly: curMonthly});
    }
    return { rows, maxAge };
  }

  function drawChart(rows, le){
    const svg = document.getElementById('chart');
    const W = 680, H = 260;
    const padL = 54, padR = 16, padT = 16, padB = 34;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    const maxAge = rows[rows.length-1].age;
    const minAge = rows[0].age;
    const maxVal = rows[rows.length-1].cum * 1.05;

    function x(age){ return padL + (age - minAge) / (maxAge - minAge) * plotW; }
    function y(val){ return padT + plotH - (val / maxVal) * plotH; }

    let svgParts = [];

    // gridlines (horizontal)
    const gridSteps = 4;
    for (let i=0;i<=gridSteps;i++){
      const val = maxVal * i / gridSteps;
      const yy = y(val);
      svgParts.push(`<line x1="${padL}" y1="${yy}" x2="${W-padR}" y2="${yy}" stroke="#2A3F52" stroke-width="1" />`);
      svgParts.push(`<text x="${padL-8}" y="${yy+4}" text-anchor="end" font-family="IBM Plex Mono, monospace" font-size="9.5" fill="#8FA0AE">${(val/1000).toFixed(0)}K</text>`);
    }

    // x axis labels every ~5 years
    for (let age = minAge; age <= maxAge; age += 5){
      const xx = x(age);
      svgParts.push(`<text x="${xx}" y="${H-10}" text-anchor="middle" font-family="IBM Plex Mono, monospace" font-size="9.5" fill="#8FA0AE">${age}</text>`);
    }

    // life expectancy vertical dashed line
    const leX = x(le);
    svgParts.push(`<line x1="${leX}" y1="${padT}" x2="${leX}" y2="${H-padB}" stroke="#C7A24A" stroke-width="1.3" stroke-dasharray="4,4" />`);
    svgParts.push(`<text x="${leX}" y="${padT+10}" text-anchor="middle" font-family="IBM Plex Mono, monospace" font-size="9.5" fill="#C7A24A">age ${le}</text>`);

    // cumulative payout line (teal)
    let cumPath = rows.map((r,i) => (i===0?'M':'L') + x(r.age).toFixed(1) + ',' + y(r.cum).toFixed(1)).join(' ');
    svgParts.push(`<path d="${cumPath}" fill="none" stroke="#4F9C90" stroke-width="2.2" />`);

    // axis baseline
    svgParts.push(`<line x1="${padL}" y1="${H-padB}" x2="${W-padR}" y2="${H-padB}" stroke="#2A3F52" stroke-width="1" />`);

    svg.innerHTML = svgParts.join('');
  }

  function renderPayoutByAge(rows, startAge){
    document.querySelectorAll('#payoutByAge .v').forEach(el => {
      const age = parseInt(el.dataset.age, 10);
      if (age < startAge){
        el.textContent = 'starts at ' + startAge;
      } else {
        const row = rows.find(r => r.age === age);
        el.textContent = row ? fmtMoney(row.monthly) + '/mo' : '—';
      }
    });
  }

  function render(){
    const { monthly, premium, le, deferYears } = compute();
    const sched = buildSchedule(monthly, state.startAge, le, state.plan);

    document.getElementById('monthlyOut').textContent = fmtMoney(monthly);
    document.getElementById('startAgeEcho').textContent = state.startAge;
    document.getElementById('annualOut').textContent = fmtMoney(monthly*12);

    const lastRow = sched.rows[sched.rows.length-1];
    const leRow = sched.rows.find(r => r.age === le) || lastRow;
    document.getElementById('lifetimeOut').textContent = fmtMoney(leRow.cum);
    document.getElementById('premiumOut').textContent = fmtMoney(premium);

    const planLabel = { standard: 'Standard Plan', basic: 'Basic Plan', escalating: 'Escalating Plan' }[state.plan];
    document.getElementById('sublineNote').innerHTML = planLabel + ' &middot; assumes life expectancy of <b>' + le + '</b>' + (deferYears>0 ? ' &middot; deferred ' + deferYears + ' yr' + (deferYears>1?'s':'') : '');

    renderPayoutByAge(sched.rows, state.startAge);
    drawChart(sched.rows, le);
  }

  // ---- apply a full state object to the controls, then re-render ----
  function applyState(newState){
    Object.assign(state, newState);

    document.getElementById('balance').value = state.balance;

    document.getElementById('startAge').value = state.startAge;
    document.getElementById('startVal').textContent = state.startAge;

    const lifeExp = document.getElementById('lifeExp');
    lifeExp.value = state.lifeExpOverride > 0 ? state.lifeExpOverride : 0;
    document.getElementById('leVal').textContent = state.lifeExpOverride > 0 ? state.lifeExpOverride : 'Auto';

    document.getElementById('genderVal').textContent = state.gender === 'male' ? 'Male' : 'Female';

    setActiveSeg('genderSeg', state.gender);
    setActiveSeg('planSeg', state.plan);

    render();
  }

  function setActiveSeg(id, value){
    const seg = document.getElementById(id);
    seg.querySelectorAll('button').forEach(b => {
      b.classList.toggle('active', b.dataset.v === value);
    });
  }

  // ---- wire up controls ----
  function wireControls(){
    const balance = document.getElementById('balance');
    balance.addEventListener('input', () => {
      const v = parseFloat(balance.value);
      state.balance = isNaN(v) ? 0 : v;
      render();
    });

    function wireSeg(id, key, onChange){
      const seg = document.getElementById(id);
      seg.querySelectorAll('button').forEach(btn => {
        btn.addEventListener('click', () => {
          seg.querySelectorAll('button').forEach(b=>b.classList.remove('active'));
          btn.classList.add('active');
          state[key] = isNaN(btn.dataset.v) ? btn.dataset.v : parseInt(btn.dataset.v,10);
          if (onChange) onChange();
          render();
        });
      });
    }

    wireSeg('genderSeg', 'gender', () => {
      document.getElementById('genderVal').textContent = state.gender === 'male' ? 'Male' : 'Female';
    });
    wireSeg('planSeg', 'plan');

    const startAge = document.getElementById('startAge');
    startAge.addEventListener('input', () => {
      state.startAge = parseInt(startAge.value,10);
      document.getElementById('startVal').textContent = state.startAge;
      render();
    });

    const lifeExp = document.getElementById('lifeExp');
    lifeExp.addEventListener('input', () => {
      const v = parseInt(lifeExp.value,10);
      state.lifeExpOverride = v;
      document.getElementById('leVal').textContent = v <= 78 ? 'Auto' : v;
      if (v <= 78) state.lifeExpOverride = 0;
      render();
    });
  }

  // ---- saved scenarios (persisted server-side in SQLite) ----
  function scenarioStatus(msg, kind){
    const el = document.getElementById('scenarioStatus');
    el.textContent = msg || '';
    el.className = 'scenario-status' + (kind ? ' ' + kind : '');
  }

  async function refreshScenarioList(){
    const listEl = document.getElementById('scenarioList');
    let scenarios;
    try {
      const res = await fetch('/api/scenarios');
      if (!res.ok) throw new Error('request failed');
      scenarios = await res.json();
    } catch (err) {
      listEl.innerHTML = '<p class="scenario-empty">Could not load saved scenarios.</p>';
      return;
    }

    if (!scenarios.length){
      listEl.innerHTML = '<p class="scenario-empty">No saved scenarios yet.</p>';
      return;
    }

    listEl.innerHTML = '';
    scenarios.forEach(s => {
      const row = document.createElement('div');
      row.className = 'scenario-row';
      row.innerHTML =
        '<span class="name">' + escapeHtml(s.name) + '</span>' +
        '<span class="actions">' +
          '<button data-action="load" data-id="' + s.id + '">Load</button>' +
          '<button data-action="delete" data-id="' + s.id + '" class="danger">Delete</button>' +
        '</span>';
      listEl.appendChild(row);
    });
  }

  function escapeHtml(str){
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
  }

  async function saveScenario(){
    const nameInput = document.getElementById('scenarioName');
    const name = nameInput.value.trim();
    if (!name){
      scenarioStatus('Give the scenario a name first.', 'err');
      return;
    }
    try {
      const res = await fetch('/api/scenarios', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ name, inputs: state })
      });
      if (!res.ok){
        const body = await res.json().catch(() => ({}));
        throw new Error(body.error || 'Save failed');
      }
      scenarioStatus('Saved "' + name + '".', 'ok');
      nameInput.value = '';
      await refreshScenarioList();
    } catch (err) {
      scenarioStatus(err.message, 'err');
    }
  }

  async function loadScenario(id){
    try {
      const res = await fetch('/api/scenarios/' + id);
      if (!res.ok) throw new Error('Could not load scenario');
      const scenario = await res.json();
      applyState(scenario.inputs);
      scenarioStatus('Loaded "' + scenario.name + '".', 'ok');
    } catch (err) {
      scenarioStatus(err.message, 'err');
    }
  }

  async function deleteScenario(id){
    try {
      const res = await fetch('/api/scenarios/' + id, { method: 'DELETE' });
      if (!res.ok && res.status !== 204) throw new Error('Could not delete scenario');
      scenarioStatus('Scenario deleted.', 'ok');
      await refreshScenarioList();
    } catch (err) {
      scenarioStatus(err.message, 'err');
    }
  }

  function wireScenarioControls(){
    document.getElementById('saveScenarioBtn').addEventListener('click', saveScenario);
    document.getElementById('scenarioName').addEventListener('keydown', (e) => {
      if (e.key === 'Enter') saveScenario();
    });
    document.getElementById('scenarioList').addEventListener('click', (e) => {
      const btn = e.target.closest('button[data-action]');
      if (!btn) return;
      const id = btn.dataset.id;
      if (btn.dataset.action === 'load') loadScenario(id);
      if (btn.dataset.action === 'delete') deleteScenario(id);
    });
  }

  // ---- boot ----
  (async function init(){
    try {
      await loadAssumptions();
    } catch (err) {
      document.body.innerHTML = '<p style="color:#B4553F;padding:40px;font-family:monospace;">Failed to load CPF assumptions from /api/anchors — is the server running? (' + err.message + ')</p>';
      return;
    }
    wireControls();
    wireScenarioControls();
    render();
    refreshScenarioList();
  })();
})();
