"""
Rebuild index.html: keep clean HTML/CSS/body, replace <script> block with
a fresh, correct version containing the portal-based city dropdown.
"""

with open("index.html", "r", encoding="utf-8") as f:
    content = f.read()

# Extract everything up to (and including) the opening <script> tag
script_open = "<script>"
idx = content.find(script_open)
html_head = content[: idx + len(script_open)]

# Build the fresh JavaScript block
JS = r"""
/* ══════════════════════════════════════════════════════════════════
   CONFIG
══════════════════════════════════════════════════════════════════ */
const API_BASE = 'http://localhost:5000/api/jobs';
const PAGE_SIZE = 15;

const CATEGORIES = [
  { icon:'💻', label:'Frontend Dev',    kw:'frontend developer' },
  { icon:'⚙️', label:'Backend Dev',     kw:'backend developer'  },
  { icon:'🔄', label:'Full Stack',      kw:'full stack developer'},
  { icon:'📊', label:'Data Science',    kw:'data scientist'     },
  { icon:'🤖', label:'ML / AI',         kw:'machine learning'   },
  { icon:'☁️', label:'DevOps / Cloud',  kw:'devops engineer'    },
  { icon:'🎨', label:'UI/UX Design',    kw:'ui ux designer'     },
  { icon:'📱', label:'Mobile Dev',      kw:'mobile developer'   },
  { icon:'🔒', label:'Cybersecurity',   kw:'cybersecurity'      },
  { icon:'📈', label:'Product Manager', kw:'product manager'    },
  { icon:'🧪', label:'QA / Testing',    kw:'qa engineer'        },
  { icon:'🐍', label:'Python',          kw:'python developer'   },
  { icon:'⚛️', label:'React / Next.js', kw:'react developer'    },
  { icon:'☕', label:'Java',            kw:'java developer'     },
  { icon:'💰', label:'Fintech',         kw:'fintech developer'  },
];

/* ══════════════════════════════════════════════════════════════════
   STATE
══════════════════════════════════════════════════════════════════ */
let allJobs   = [];
let filtered  = [];
let activeCat = null;
let page      = 1;

/* ══════════════════════════════════════════════════════════════════
   CITY AUTOCOMPLETE
══════════════════════════════════════════════════════════════════ */

// Full alias map – any spelling → canonical display name
const CITY_ALIASES = {
  'bangalore':'Bengaluru',    'bengaluru':'Bengaluru',
  'bengalore':'Bengaluru',    'bengalooru':'Bengaluru',
  'banglore':'Bengaluru',     'bangaluru':'Bengaluru',
  'bengaloru':'Bengaluru',    'blr':'Bengaluru',
  'bombay':'Mumbai',          'mumbai':'Mumbai',          'mum':'Mumbai',
  'gurgaon':'Gurugram',       'gurugram':'Gurugram',
  'new delhi':'Delhi',        'delhi':'Delhi',            'ncr':'Delhi',
  'calcutta':'Kolkata',       'kolkata':'Kolkata',
  'madras':'Chennai',         'chennai':'Chennai',
  'hyderabad':'Hyderabad',    'hyderbad':'Hyderabad',
  'hydrabad':'Hyderabad',     'hyderabd':'Hyderabad',     'hyd':'Hyderabad',
  'mysore':'Mysuru',          'mysuru':'Mysuru',
  'mysor':'Mysuru',           'mysur':'Mysuru',
  'mysre':'Mysuru',           'msyore':'Mysuru',          'mysoore':'Mysuru',
  'pune':'Pune',              'poona':'Pune',
  'noida':'Noida',
  'cochin':'Kochi',           'kochi':'Kochi',            'ernakulam':'Kochi',
  'trivandrum':'Thiruvananthapuram',
  'thiruvananthapuram':'Thiruvananthapuram',               'tvm':'Thiruvananthapuram',
  'vizag':'Visakhapatnam',    'visakhapatnam':'Visakhapatnam',
  'bhubaneswar':'Bhubaneswar','bbsr':'Bhubaneswar',
  'ahmedabad':'Ahmedabad',    'amdavad':'Ahmedabad',
  'jaipur':'Jaipur',          'lucknow':'Lucknow',
  'chandigarh':'Chandigarh',  'indore':'Indore',
  'coimbatore':'Coimbatore',  'cbe':'Coimbatore',
  'nagpur':'Nagpur',          'bhopal':'Bhopal',
  'surat':'Surat',            'patna':'Patna',
  'vadodara':'Vadodara',      'baroda':'Vadodara',
  'mangaluru':'Mangaluru',    'mangalore':'Mangaluru',
  'remote':'Remote',          'wfh':'Remote',             'work from home':'Remote',
  'india':'India',            'pan india':'India',
};

let _allCities  = [];    // loaded from /api/cities
let _ddHighIdx  = -1;    // keyboard-highlighted index
let _ddVisible  = false;
let _searchTerms = [];   // [{display, match}] – all cities + all aliases
let _ddEl       = null;  // body-portal dropdown element

/* ── Levenshtein distance (pure JS, no library) ── */
function _lev(a, b) {
  const m = a.length, n = b.length;
  if (!m) return n; if (!n) return m;
  let prev = Array.from({length: n+1}, (_,i) => i);
  for (let i = 1; i <= m; i++) {
    const curr = [i];
    for (let j = 1; j <= n; j++)
      curr[j] = a[i-1] === b[j-1] ? prev[j-1]
                : 1 + Math.min(prev[j], curr[j-1], prev[j-1]);
    prev = curr;
  }
  return prev[n];
}
function _sim(a, b) {
  const mx = Math.max(a.length, b.length);
  return mx ? (mx - _lev(a, b)) / mx : 1;
}

/* ── Build search-term index from canonical list + all aliases ── */
function _buildSearchTerms() {
  const seen = new Set();
  _searchTerms = [];
  _allCities.forEach(city => {
    const k = city.toLowerCase();
    if (!seen.has(k)) { seen.add(k); _searchTerms.push({display:city, match:k}); }
  });
  Object.entries(CITY_ALIASES).forEach(([alias, canon]) => {
    if (!seen.has(alias)) { seen.add(alias); _searchTerms.push({display:canon, match:alias}); }
  });
}

/* ── Filter: substring first, fuzzy fallback ── */
function filterCities(q) {
  if (!q || !q.trim()) return _allCities.slice();
  const lq = q.trim().toLowerCase();
  // 1. Substring match (includes aliases)
  const sub = []; const subSeen = new Set();
  _searchTerms.forEach(({display, match}) => {
    if (match.includes(lq) && !subSeen.has(display)) { subSeen.add(display); sub.push(display); }
  });
  if (sub.length) return sub;
  // 2. Fuzzy fallback ≥ 62%
  const fuzzy = []; const fuzzySeen = new Set();
  _searchTerms.forEach(({display, match}) => {
    if (fuzzySeen.has(display)) return;
    const s = Math.max(_sim(lq, match), _sim(lq, match.substring(0, lq.length + 3)));
    if (s >= 0.62) { fuzzySeen.add(display); fuzzy.push({display, s}); }
  });
  fuzzy.sort((a,b) => b.s - a.s);
  return fuzzy.map(x => x.display);
}

/* ── Resolve raw input to canonical name ── */
function resolveCity(raw) {
  if (!raw) return '';
  const lower = raw.trim().toLowerCase();
  if (CITY_ALIASES[lower]) return CITY_ALIASES[lower];
  const found = _allCities.find(c => c.toLowerCase() === lower);
  if (found) return found;
  let best = null, bestS = 0;
  _searchTerms.forEach(({display, match}) => {
    const s = Math.max(_sim(lower, match), _sim(lower, match.substring(0, lower.length + 3)));
    if (s > bestS) { bestS = s; best = display; }
  });
  return (bestS >= 0.72 && best) ? best : raw.trim();
}

/* ── Body-portal dropdown ─────────────────────────────────────────
   The dropdown is appended to <body> with position:fixed so it
   escapes the overflow:hidden on .hero-search.
───────────────────────────────────────────────────────────────── */
function _ensurePortal() {
  if (_ddEl) return;
  _ddEl = document.createElement('div');
  _ddEl.id = 'city-dd';
  Object.assign(_ddEl.style, {
    position:   'fixed',
    background: '#ffffff',
    border:     '1.5px solid #bdeaff',
    borderRadius:'10px',
    boxShadow:  '0 10px 15px rgba(0,0,0,.09),0 4px 6px rgba(0,0,0,.05)',
    maxHeight:  '260px',
    overflowY:  'auto',
    zIndex:     '99999',
    display:    'none',
    minWidth:   '220px',
    fontFamily: 'Inter,system-ui,sans-serif',
    fontSize:   '.88rem',
  });
  document.body.appendChild(_ddEl);
}

function _positionPortal() {
  const inp = document.getElementById('inp-location');
  if (!inp || !_ddEl) return;
  const r = inp.getBoundingClientRect();
  _ddEl.style.top   = (r.bottom + 6) + 'px';
  _ddEl.style.left  = r.left + 'px';
  _ddEl.style.width = Math.max(r.width, 220) + 'px';
}

function renderCityDd(items) {
  _ensurePortal();
  _ddHighIdx = -1;
  if (!items.length) {
    _ddEl.innerHTML = '<div style="padding:10px 16px;color:#64748b;font-style:italic">No matching city</div>';
    return;
  }
  _ddEl.innerHTML = '';
  items.slice(0, 80).forEach((c, i) => {
    const div = document.createElement('div');
    div.textContent = c;
    div.dataset.idx = i;
    Object.assign(div.style, {padding:'8px 16px', cursor:'pointer', color:'#0f172a', whiteSpace:'nowrap', transition:'background .1s'});
    div.addEventListener('mouseover', () => div.style.background = '#d1f0ff');
    div.addEventListener('mouseout',  () => div.style.background = '');
    div.addEventListener('mousedown', e => { e.preventDefault(); pickCity(c); });
    _ddEl.appendChild(div);
  });
}

function openCityDd(items) {
  _ensurePortal();
  renderCityDd(items);
  _positionPortal();
  _ddEl.style.display = 'block';
  _ddVisible = true;
}

function closeCityDd() {
  if (_ddEl) _ddEl.style.display = 'none';
  _ddVisible = false;
  _ddHighIdx = -1;
}

function pickCity(name) {
  document.getElementById('inp-location').value = name;
  document.getElementById('tb-loc').value = name;
  closeCityDd();
}

function cityInput(val)  { openCityDd(filterCities(val)); }
function cityFocus()     { openCityDd(filterCities(document.getElementById('inp-location').value)); }
function cityBlur()      { setTimeout(closeCityDd, 200); }

function cityKd(e) {
  _ensurePortal();
  const items = Array.from(_ddEl.children).filter(el => el.dataset.idx !== undefined);
  if (e.key === 'ArrowDown') {
    e.preventDefault();
    if (items[_ddHighIdx]) items[_ddHighIdx].style.background = '';
    _ddHighIdx = Math.min(_ddHighIdx + 1, items.length - 1);
    if (items[_ddHighIdx]) { items[_ddHighIdx].style.background = '#d1f0ff'; items[_ddHighIdx].scrollIntoView({block:'nearest'}); }
  } else if (e.key === 'ArrowUp') {
    e.preventDefault();
    if (items[_ddHighIdx]) items[_ddHighIdx].style.background = '';
    _ddHighIdx = Math.max(_ddHighIdx - 1, 0);
    if (items[_ddHighIdx]) { items[_ddHighIdx].style.background = '#d1f0ff'; items[_ddHighIdx].scrollIntoView({block:'nearest'}); }
  } else if (e.key === 'Enter') {
    if (_ddVisible && _ddHighIdx >= 0 && items[_ddHighIdx]) pickCity(items[_ddHighIdx].textContent.trim());
    doSearch();
  } else if (e.key === 'Escape') {
    closeCityDd();
  }
}

// Close on outside click
document.addEventListener('mousedown', e => {
  const anchor = document.getElementById('city-dd-anchor');
  if (_ddEl && !_ddEl.contains(e.target) && anchor && !anchor.contains(e.target)) closeCityDd();
});

// Re-position on scroll/resize
window.addEventListener('scroll', () => { if (_ddVisible) _positionPortal(); }, {passive:true});
window.addEventListener('resize', () => { if (_ddVisible) _positionPortal(); }, {passive:true});

// Load cities from backend API, then build search index
async function loadCities() {
  try {
    const res = await fetch('http://localhost:5000/api/cities');
    if (res.ok) _allCities = await res.json();
  } catch (_) {}
  if (!_allCities.length) {
    _allCities = [
      'India','Remote','Bengaluru','Hyderabad','Chennai','Pune','Mumbai',
      'Delhi','Noida','Gurugram','Ahmedabad','Kolkata','Mysuru','Kochi',
      'Thiruvananthapuram','Coimbatore','Indore','Chandigarh','Jaipur',
      'Lucknow','Nagpur','Bhopal','Surat','Visakhapatnam','Bhubaneswar',
      'Patna','Vadodara','Mangaluru','Ranchi','Guwahati','Dehradun',
      'Raipur','Jamshedpur','Amritsar','Ludhiana','Jodhpur','Udaipur',
      'Nashik','Aurangabad','Gwalior','Jabalpur','Vijayawada','Madurai',
    ];
  }
  _buildSearchTerms();
}

/* ══════════════════════════════════════════════════════════════════
   INIT
══════════════════════════════════════════════════════════════════ */
(function init() {
  loadCities();
  const bar = document.getElementById('cat-bar');
  CATEGORIES.forEach(c => {
    const btn = document.createElement('button');
    btn.className = 'cat-pill';
    btn.dataset.kw = c.kw;
    btn.innerHTML = '<span class="cat-pill-icon">' + c.icon + '</span>' + c.label;
    btn.addEventListener('click', () => {
      document.querySelectorAll('.cat-pill').forEach(b => b.classList.remove('active'));
      btn.classList.add('active');
      activeCat = c.kw;
      document.getElementById('inp-keyword').value = c.kw;
      document.getElementById('inp-location').value = 'India';
      document.getElementById('tb-loc').value = 'India';
      doSearch();
    });
    bar.appendChild(btn);
  });
})();

/* ══════════════════════════════════════════════════════════════════
   SEARCH
══════════════════════════════════════════════════════════════════ */
async function doSearch() {
  closeCityDd();

  const heroKw  = document.getElementById('inp-keyword').value.trim();
  const heroLoc = document.getElementById('inp-location').value.trim();
  const tbKw    = document.getElementById('tb-kw').value.trim();
  const tbLoc   = document.getElementById('tb-loc').value.trim();

  const keyword  = heroKw || tbKw;
  const rawLoc   = heroLoc || tbLoc || 'India';
  const location = resolveCity(rawLoc) || 'India';

  if (!keyword) { toast('Please enter a keyword first', '⚠️'); return; }

  document.getElementById('inp-keyword').value  = keyword;
  document.getElementById('inp-location').value = location;
  document.getElementById('tb-kw').value  = keyword;
  document.getElementById('tb-loc').value = location;

  setLoading(true);
  showResults(false);
  document.getElementById('landing-view').style.display = 'none';

  try {
    const url = API_BASE + '?keyword=' + encodeURIComponent(keyword) + '&location=' + encodeURIComponent(location);
    const res = await fetch(url);
    if (!res.ok) { const e = await res.json(); throw new Error(e.error || 'HTTP ' + res.status); }
    const data = await res.json();

    if (Array.isArray(data)) {
      allJobs = data;
    } else {
      allJobs = data.jobs || [];
      if (data.fallback_used && data.fallback_message) {
        const sl = data.searched_location || '';
        if (sl) { document.getElementById('inp-location').value = sl; document.getElementById('tb-loc').value = sl; }
        toast(data.fallback_message, '🌍', 7000);
      }
    }

    updateSidebarCounts();
    page = 1;
    applyFilters();
    showResults(true);
    if (allJobs.length > 0) toast('Found ' + allJobs.length + ' jobs for "' + keyword + '"', '✅');
    else toast('No jobs found for "' + keyword + '" in ' + location, '⚠️', 4000);
  } catch (err) {
    showError(err.message);
    toast('Could not connect — is api.py running?', '❌', 5000);
  } finally {
    setLoading(false);
  }
}

function quickSearch(kw) {
  document.getElementById('inp-keyword').value  = kw;
  document.getElementById('inp-location').value = 'India';
  document.getElementById('tb-loc').value = 'India';
  doSearch();
}

/* ══════════════════════════════════════════════════════════════════
   FILTERS & SORT
══════════════════════════════════════════════════════════════════ */
function applyFilters() {
  const jtChecked  = [...document.querySelectorAll('.jt-filter:checked')].map(e => e.value.toLowerCase());
  const srcChecked = [...document.querySelectorAll('.src-filter:checked')].map(e => e.value);
  const sort       = document.getElementById('sort-sel').value;
  const salaryOnly = document.getElementById('has-salary-chk').checked;

  filtered = allJobs.filter(j => {
    const jt  = (j.job_type || '').toLowerCase();
    const src = j.source || '';
    const jtOk  = !jt || jtChecked.some(t => jt.includes(t));
    const srcOk = srcChecked.includes(src);
    const salOk = !salaryOnly || (j.salary && j.salary.trim() !== '');
    return jtOk && srcOk && salOk;
  });

  const sortFns = {
    'date-desc': (a,b) => ((b.date_posted||'') > (a.date_posted||'') ? 1 : -1),
    'date-asc':  (a,b) => ((a.date_posted||'') > (b.date_posted||'') ? 1 : -1),
    'company':   (a,b) => (a.company||'').localeCompare(b.company||''),
    'title':     (a,b) => (a.title||'').localeCompare(b.title||''),
  };
  filtered.sort(sortFns[sort] || sortFns['date-desc']);

  document.getElementById('feed-count').innerHTML =
    'Showing <strong>' + filtered.length + '</strong> of <strong>' + allJobs.length + '</strong> jobs';
  renderPage();
}

function clearFilters() {
  document.querySelectorAll('.jt-filter, .src-filter').forEach(c => c.checked = true);
  document.getElementById('has-salary-chk').checked = false;
  document.getElementById('sort-sel').value = 'date-desc';
  applyFilters();
}

/* ══════════════════════════════════════════════════════════════════
   SIDEBAR COUNTS
══════════════════════════════════════════════════════════════════ */
function updateSidebarCounts() {
  const typeMap = {}, srcMap = {};
  allJobs.forEach(j => {
    const jt  = (j.job_type || 'other').toLowerCase();
    const src = j.source || 'other';
    typeMap[jt] = (typeMap[jt] || 0) + 1;
    srcMap[src] = (srcMap[src] || 0) + 1;
  });

  [['cnt-remote','remote'],['cnt-fulltime','full-time'],['cnt-contract','contract'],
   ['cnt-parttime','part-time'],['cnt-internship','internship']].forEach(([id,k]) => {
    const el = document.getElementById(id); if (el) el.textContent = typeMap[k] || 0;
  });
  [['cnt-linkedin','LinkedIn'],['cnt-unstop','Unstop'],['cnt-himalayas','Himalayas'],
   ['cnt-jobicy','Jobicy'],['cnt-remotive','Remotive'],['cnt-arbeitnow','Arbeitnow']].forEach(([id,src]) => {
    const el = document.getElementById(id); if (el) el.textContent = srcMap[src] || 0;
  });
  const hasSal = allJobs.some(j => j.salary && j.salary.trim());
  document.getElementById('salary-filter').style.display = hasSal ? 'block' : 'none';
}

/* ══════════════════════════════════════════════════════════════════
   RENDER
══════════════════════════════════════════════════════════════════ */
function renderPage() {
  const list  = document.getElementById('job-list');
  const total = Math.max(1, Math.ceil(filtered.length / PAGE_SIZE));
  page = Math.min(page, total);
  const slice = filtered.slice((page-1)*PAGE_SIZE, page*PAGE_SIZE);

  if (!slice.length) {
    list.innerHTML = '<div class="state-card"><div class="state-icon">🔍</div><div class="state-title">No jobs match these filters</div><div class="state-sub">Try adjusting the filters on the left.</div></div>';
    document.getElementById('pagination').innerHTML = '';
    return;
  }
  list.innerHTML = slice.map(jobCard).join('');
  renderPagination(total);
}

function jobCard(j) {
  const url     = esc(j.url || '#');
  const title   = esc(j.title   || 'Untitled');
  const company = esc(j.company || 'Unknown');
  const loc     = esc(j.location || '');
  const jtype   = j.job_type || '';
  const src     = j.source || '';
  const date    = j.date_posted ? relDate(j.date_posted) : '';
  const desc    = esc((j.description || '').slice(0, 200));
  const salary  = j.salary ? esc(j.salary) : '';
  const tags    = (j.tags||'').split(',').map(t=>t.trim()).filter(Boolean).slice(0,6)
                  .map(t=>'<span class="tag">'+esc(t)+'</span>').join('');
  const avatar  = coAvatar(company);
  const typeCls = typeChipClass(jtype);
  const srcCls  = srcBadgeClass(src);

  return '<a class="job-card" href="' + url + '" target="_blank" rel="noopener">' +
    '<div class="jc-top">' +
      '<div class="co-avatar" style="background:' + avatar.color + '">' + avatar.letter + '</div>' +
      '<div class="jc-meta-block">' +
        '<div class="jc-company">' + company + '</div>' +
        '<div class="jc-title">' + title + '</div>' +
        '<div class="jc-chips">' +
          (loc ? '<span class="chip chip-loc">📍 ' + loc + '</span>' : '') +
          (jtype ? '<span class="chip ' + typeCls + '">' + esc(jtype) + '</span>' : '') +
        '</div>' +
      '</div>' +
      '<div class="jc-right">' +
        '<span class="src-badge ' + srcCls + '">' + esc(src) + '</span>' +
        (date ? '<span class="jc-date">' + date + '</span>' : '') +
      '</div>' +
    '</div>' +
    (desc ? '<div class="jc-desc">' + desc + '</div>' : '') +
    (tags ? '<div class="jc-tags">' + tags + '</div>' : '') +
    '<div class="jc-footer">' +
      '<div class="jc-salary">' + (salary ? '💰 ' + salary : '') + '</div>' +
      '<span class="view-btn">View Job ↗</span>' +
    '</div>' +
  '</a>';
}

/* ══════════════════════════════════════════════════════════════════
   PAGINATION
══════════════════════════════════════════════════════════════════ */
function renderPagination(total) {
  const el = document.getElementById('pagination');
  if (total <= 1) { el.innerHTML = ''; return; }
  let html = '<button class="pg-btn" ' + (page===1?'disabled':'') + ' onclick="goPage(' + (page-1) + ')">‹</button>';
  for (let i = 1; i <= total; i++) {
    if (i===1 || i===total || Math.abs(i-page)<=2)
      html += '<button class="pg-btn ' + (i===page?'active':'') + '" onclick="goPage(' + i + ')">' + i + '</button>';
    else if (Math.abs(i-page)===3)
      html += '<span style="color:var(--text-3);padding:0 4px;align-self:center">…</span>';
  }
  html += '<button class="pg-btn" ' + (page===total?'disabled':'') + ' onclick="goPage(' + (page+1) + ')">›</button>';
  el.innerHTML = html;
}

function goPage(n) {
  page = n;
  renderPage();
  document.getElementById('feed').scrollIntoView({behavior:'smooth', block:'start'});
}

/* ══════════════════════════════════════════════════════════════════
   UI HELPERS
══════════════════════════════════════════════════════════════════ */
function setLoading(on) {
  const btn = document.getElementById('search-btn');
  const sp  = document.getElementById('btn-spin');
  btn.disabled = on;
  sp.style.display = on ? 'inline-block' : 'none';
  if (on) {
    document.getElementById('job-list').innerHTML =
      '<div class="state-card"><div class="spinner"></div>' +
      '<div class="state-title">Fetching from live sources…</div>' +
      '<div class="state-sub">LinkedIn · Unstop · Himalayas · Jobicy · Remotive · Arbeitnow</div></div>';
    showResults(true);
  }
}

function showResults(on) {
  document.getElementById('results-view').style.display = on ? 'block' : 'none';
  document.getElementById('landing-view').style.display = on ? 'none' : 'block';
}

function showError(msg) {
  document.getElementById('job-list').innerHTML =
    '<div class="state-card"><div class="state-icon">⚠️</div>' +
    '<div class="state-title">Connection failed</div>' +
    '<div class="state-sub">Make sure the backend is running:<br><code>python api.py</code><br><br>' + esc(msg) + '</div></div>';
  showResults(true);
}

function toast(msg, icon, ms) {
  icon = icon || 'ℹ️'; ms = ms || 3000;
  const el = document.getElementById('toast');
  document.getElementById('toast-icon').textContent = icon;
  document.getElementById('toast-msg').textContent  = msg;
  el.classList.add('show');
  setTimeout(() => el.classList.remove('show'), ms);
}

/* ══════════════════════════════════════════════════════════════════
   STYLE HELPERS
══════════════════════════════════════════════════════════════════ */
const AVATAR_COLORS = [
  '#6d28d9','#2563eb','#059669','#d97706',
  '#dc2626','#0891b2','#9333ea','#0f766e',
  '#b45309','#1d4ed8','#7c3aed','#065f46',
];
function coAvatar(name) {
  const letter = (name || '?')[0].toUpperCase();
  const color  = AVATAR_COLORS[(name.charCodeAt(0) || 0) % AVATAR_COLORS.length];
  return { letter, color };
}
function typeChipClass(jt) {
  const l = (jt||'').toLowerCase();
  if (l.includes('remote'))   return 'chip-remote';
  if (l.includes('full'))     return 'chip-fulltime';
  if (l.includes('part'))     return 'chip-parttime';
  if (l.includes('contract')) return 'chip-contract';
  return 'chip-default';
}
function srcBadgeClass(src) {
  const m = {LinkedIn:'src-linkedin',Unstop:'src-unstop',Himalayas:'src-himalayas',
             Jobicy:'src-jobicy',Remotive:'src-remotive',Arbeitnow:'src-arbeitnow'};
  return m[src] || 'src-default';
}
function relDate(d) {
  if (!d) return '';
  const diff = Math.floor((Date.now() - new Date(d)) / 86400000);
  if (diff === 0) return 'Today';
  if (diff === 1) return '1d ago';
  if (diff < 7)   return diff + 'd ago';
  if (diff < 30)  return Math.floor(diff/7) + 'w ago';
  return d;
}
function esc(s) {
  return String(s||'').replace(/&/g,'&amp;').replace(/</g,'&lt;')
                      .replace(/>/g,'&gt;').replace(/"/g,'&quot;');
}

/* ══════════════════════════════════════════════════════════════════
   DOWNLOADS
══════════════════════════════════════════════════════════════════ */
function dlCSV() {
  if (!filtered.length) { toast('No data to download','⚠️'); return; }
  const cols = ['title','company','location','job_type','salary','tags','date_posted','source','url'];
  const hdr  = cols.join(',');
  const rows = filtered.map(j => cols.map(c => '"' + (j[c]||'').replace(/"/g,'""') + '"').join(','));
  const blob = new Blob([hdr+'\n'+rows.join('\n')], {type:'text/csv;charset=utf-8;'});
  dl(blob, 'jobs_india_' + iso() + '.csv');
  toast('Downloaded ' + filtered.length + ' jobs as CSV','✅');
}
function dlJSON() {
  if (!filtered.length) { toast('No data to download','⚠️'); return; }
  const blob = new Blob([JSON.stringify(filtered,null,2)], {type:'application/json'});
  dl(blob, 'jobs_india_' + iso() + '.json');
  toast('Downloaded ' + filtered.length + ' jobs as JSON','✅');
}
function dl(blob, name) {
  const url = URL.createObjectURL(blob);
  const a   = Object.assign(document.createElement('a'), {href:url, download:name});
  a.click(); URL.revokeObjectURL(url);
}
function iso() { return new Date().toISOString().slice(0,10); }
"""

HTML_TAIL = """</script>
</body>
</html>
"""

# Write the clean rebuilt file
output = html_head + JS + HTML_TAIL
with open("index.html", "w", encoding="utf-8") as f:
    f.write(output)

print(f"Rebuilt index.html: {len(output.splitlines())} lines, {len(output)} chars")
print("Done!")
