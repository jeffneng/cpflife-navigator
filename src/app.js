(function(){
  // ---- state ----
  const state = {
    balance: 220400,
    balAge: 55,
    gender: 'male',
    plan: 'standard',
    startAge: 65,
    growRate: 0.0,
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

  function monthlyRateForBalance(bal){
    // piecewise linear interpolation of payout/balance ratio between anchors
    const pts = CPF.payoutAnchors.map(a => ({bal:a.balance, rate:a.monthlyPayout/a.balance}));
    if (bal <= pts[0].bal) return pts[0].rate;
    if (bal >= pts[pts.length-1].bal) return pts[pts.length-1].rate;
    for (let i=0;i<pts.length-1;i++){
      if (bal >= pts[i].bal && bal <= pts[i+1].bal){
        const t = (bal - pts[i].bal) / (pts[i+1].bal - pts[i].bal);
        return pts[i].rate + t*(pts[i+1].rate - pts[i].rate);
      }
    }
    return pts[pts.length-1].rate;
  }

  function lifeExpectancy(gender, override){
    if (override && override > 0) return override;
    return CPF.lifeExpectancy[gender];
  }

  function fmtMoney(n){
    return '$' + Math.round(n).toLocaleString('en-US');
  }

  function compute(){
    // 1. CPF's published anchors already project a 55-year-old's balance forward
    //    to 65 using its own baseline assumptions — so no compounding is applied
    //    by default. The "extra top-ups" slider only adds growth on top of that
    //    baseline, for modeling voluntary contributions beyond what CPF assumed.
    let bal65 = state.balance;
    if (state.balAge === 55 && state.growRate > 0){
      bal65 = state.balance * Math.pow(1 + state.growRate/100, 10);
    }

    // 2. base monthly rate at this balance (male, standard, age 65)
    let rate = monthlyRateForBalance(bal65);
    let monthly = bal65 * rate;

    // 3. gender adjustment
    monthly *= CPF.genderFactor[state.gender];

    // 4. plan adjustment
    monthly *= CPF.planFactor[state.plan];

    // 5. deferral adjustment (balance also keeps earning between 65 and start age,
    //    but CPF's published deferral bonus already folds that in, so apply once)
    const deferYears = state.startAge - 65;
    const deferMultiplier = Math.pow(1 + CPF.deferral.annualBonusRate, deferYears);
    monthly *= deferMultiplier;

    // premium at payout start = balance at 65 grown through any deferral years
    // at CPF's ongoing RA interest rate (not the 55→65 top-up slider)
    const premium = bal65 * Math.pow(1 + CPF.deferral.raInterestWhileDeferred, deferYears);

    const le = lifeExpectancy(state.gender, state.lifeExpOverride);

    return { monthly, premium, le, deferYears };
  }

  function buildSchedule(monthlyStart, premium, startAge, le, plan){
    // returns array of {age, cumPayout, bequest, monthlyThatYear}
    const maxAge = Math.max(le + 8, startAge + 5, 95);
    const rows = [];
    let cum = 0;
    let curMonthly = monthlyStart;
    let breakevenAge = null;
    for (let age = startAge; age <= maxAge; age++){
      if (age > startAge && plan === 'escalating'){
        curMonthly = curMonthly * (1 + CPF.escalatingPlan.annualEscalationRate);
      }
      cum += curMonthly * 12;
      const bequest = Math.max(0, premium - cum);
      if (bequest === 0 && breakevenAge === null){
        breakevenAge = age;
      }
      rows.push({age, cum, bequest, monthly: curMonthly});
    }
    if (breakevenAge === null) breakevenAge = maxAge;
    return { rows, breakevenAge, maxAge };
  }

  function drawChart(rows, startAge, le, breakevenAge, premium){
    const svg = document.getElementById('chart');
    const W = 680, H = 260;
    const padL = 54, padR = 16, padT = 16, padB = 34;
    const plotW = W - padL - padR;
    const plotH = H - padT - padB;

    const maxAge = rows[rows.length-1].age;
    const minAge = rows[0].age;
    const maxVal = Math.max(premium, rows[rows.length-1].cum) * 1.05;

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

    // bequest line (brick)
    let beqPath = rows.map((r,i) => (i===0?'M':'L') + x(r.age).toFixed(1) + ',' + y(r.bequest).toFixed(1)).join(' ');
    svgParts.push(`<path d="${beqPath}" fill="none" stroke="#B4553F" stroke-width="2.2" />`);

    // breakeven marker dot
    const bx = x(breakevenAge), by = y(0);
    svgParts.push(`<circle cx="${bx}" cy="${by}" r="4" fill="#B4553F" />`);

    // axis baseline
    svgParts.push(`<line x1="${padL}" y1="${H-padB}" x2="${W-padR}" y2="${H-padB}" stroke="#2A3F52" stroke-width="1" />`);

    svg.innerHTML = svgParts.join('');
  }

  function render(){
    const { monthly, premium, le, deferYears } = compute();
    const sched = buildSchedule(monthly, premium, state.startAge, le, state.plan);

    document.getElementById('monthlyOut').textContent = fmtMoney(monthly);
    document.getElementById('startAgeEcho').textContent = state.startAge;
    document.getElementById('annualOut').textContent = fmtMoney(monthly*12);

    const lastRow = sched.rows[sched.rows.length-1];
    const leRow = sched.rows.find(r => r.age === le) || lastRow;
    document.getElementById('lifetimeOut').textContent = fmtMoney(leRow.cum);
    document.getElementById('premiumOut').textContent = fmtMoney(premium);
    document.getElementById('breakevenOut').textContent = (sched.breakevenAge >= sched.maxAge && sched.rows[sched.rows.length-1].bequest > 0) ? 'beyond ' + sched.maxAge : ('~' + sched.breakevenAge);

    const planLabel = { standard: 'Standard Plan', basic: 'Basic Plan', escalating: 'Escalating Plan' }[state.plan];
    document.getElementById('sublineNote').innerHTML = planLabel + ' &middot; assumes life expectancy of <b>' + le + '</b>' + (deferYears>0 ? ' &middot; deferred ' + deferYears + ' yr' + (deferYears>1?'s':'') : '');

    drawChart(sched.rows, state.startAge, le, sched.breakevenAge, premium);
  }

  // ---- apply a full state object to the controls, then re-render ----
  function applyState(newState){
    Object.assign(state, newState);

    document.getElementById('balance').value = state.balance;
    document.getElementById('balVal').textContent = fmtMoney(state.balance);

    document.getElementById('startAge').value = state.startAge;
    document.getElementById('startVal').textContent = state.startAge;

    document.getElementById('growRate').value = state.growRate;
    document.getElementById('growVal').textContent = state.growRate.toFixed(1) + '%';

    const lifeExp = document.getElementById('lifeExp');
    lifeExp.value = state.lifeExpOverride > 0 ? state.lifeExpOverride : 0;
    document.getElementById('leVal').textContent = state.lifeExpOverride > 0 ? state.lifeExpOverride : 'Auto';

    document.getElementById('genderVal').textContent = state.gender === 'male' ? 'Male' : 'Female';

    setActiveSeg('balAgeSeg', String(state.balAge));
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
      state.balance = parseInt(balance.value,10);
      document.getElementById('balVal').textContent = fmtMoney(state.balance);
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

    wireSeg('balAgeSeg', 'balAge');
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

    const growRate = document.getElementById('growRate');
    growRate.addEventListener('input', () => {
      state.growRate = parseFloat(growRate.value);
      document.getElementById('growVal').textContent = state.growRate.toFixed(1) + '%';
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
