const D = JSON.parse(document.getElementById('payload').textContent);
const $ = s => document.querySelector(s);

/* ── catálogo de indicadores ─────────────────────────────── */
const IND = [
  {k:'idx',     l:'Vulnerabilidad compuesta', u:'z',    s:'div',  lv:['upz'],       mv:null,
   d:'Índice de cuatro componentes con 25% cada uno'},
  {k:'estrato', l:'Estrato promedio',         u:'',     s:'est',  lv:['upz','loc'], mv:'estrato_promedio_oficial',
   d:'Estratificación oficial por manzana, Secretaría Distrital de Planeación'},
  {k:'deficit', l:'Déficit de aseo',          u:'z',    s:'div',  lv:['upz','loc'], mv:'deficit_aseo_relativo',
   d:'z-score invertido de la densidad de cestas y contenedores'},
  {k:'arrojo',  l:'Arrojo clandestino',       u:'/km²', s:'mal',  lv:['upz','loc'], mv:'densidad_puntos_criticos_km2',
   d:'Puntos críticos activos de la UAESP por km²'},
  {k:'emerg',   l:'Emergencias',              u:'/km²', s:'mal',  lv:['upz','loc'], mv:'densidad_incidentes_km2',
   d:'Incidentes atendidos por la UAECOB entre 2016 y 2020, por km²'},
  {k:'cestas',  l:'Cestas públicas',          u:'/km²', s:'bien', lv:['upz','loc'], mv:null,
   d:'Dotación de mobiliario de aseo por km²'},
  {k:'homd',    l:'Homicidios',               u:'/km²', s:'mal',  lv:['loc'],       mv:'densidad_homicidios_km2',
   d:'DAILoc. Los delitos solo se publican por localidad'}
];
const VARLBL = {
  deficit_aseo_relativo:'Déficit de aseo', densidad_puntos_criticos_km2:'Arrojo',
  densidad_incidentes_km2:'Emergencias',  estrato_promedio_oficial:'Estrato',
  densidad_cuadrantes_km2:'Cuadrantes',   densidad_homicidios_km2:'Homicidios',
  estrato_promedio_reportado:'Estrato reportado',
  n_puntos_criticos:'Arrojo',      n_cuadrantes:'Cuadrantes de policía',
  distancia_a_cesta_m:'Distancia a cesta'
};
let lvl = 'upz', ind = 'idx', sel = null, RAMP = [], SURF = [255,255,255];

/* ── color, todo derivado de la rampa de estrato ─────────── */
const hex = h => { h = h.trim().replace('#',''); return [0,2,4].map(i=>parseInt(h.substr(i,2),16)); };
const rgb = c => 'rgb(' + c.map(v=>Math.round(v)).join(',') + ')';
const mix = (a,b,t) => a.map((v,i)=>v+(b[i]-v)*t);
function leerRampa(){
  const cs = getComputedStyle(document.documentElement);
  RAMP = [1,2,3,4,5,6].map(i => hex(cs.getPropertyValue('--e'+i)));
  SURF = hex(cs.getPropertyValue('--surface-2'));
}
const enRampa = t => {                       // recorre los seis pasos
  t = Math.max(0, Math.min(1, t)) * 5;
  const i = Math.min(4, Math.floor(t));
  return mix(RAMP[i], RAMP[i+1], t - i);
};
function paleta(t, esc){
  t = Math.max(0, Math.min(1, t));
  if (esc === 'est')  return rgb(enRampa(t));                       // 1 vino → 6 índigo
  if (esc === 'div'){                                                // divergente: solo los extremos
    const mid = mix(SURF, RAMP[3], .12);
    return t < .5 ? rgb(mix(RAMP[5], mid, t*2)) : rgb(mix(mid, RAMP[0], (t-.5)*2));
  }
  if (esc === 'mal')  return rgb(mix(mix(SURF, RAMP[0], .06), RAMP[0], t));
  if (esc === 'bien') return rgb(mix(mix(SURF, RAMP[5], .06), RAMP[5], t));
  return rgb(enRampa(t));
}
const rampaLeyenda = esc => Array.from({length:7}, (_,i)=>paleta(i/6, esc));

/* ── proyección equirrectangular ajustada a la latitud ───── */
let PROJ = null;
function proyectar(){
  let x0=1e9, y0=1e9, x1=-1e9, y1=-1e9;
  Object.values(D.geo).forEach(set => Object.values(set).forEach(polys =>
    polys.forEach(p => p[0].forEach(([x,y]) => {
      if(x<x0)x0=x; if(x>x1)x1=x; if(y<y0)y0=y; if(y>y1)y1=y;
    }))));
  const pad=10, k=Math.cos(4.65*Math.PI/180);
  const sw=(x1-x0)*k, sh=(y1-y0);
  const H=760, s=(H-pad*2)/sh, W=Math.round(sw*s)+pad*2;   // el lienzo toma la forma de la ciudad
  PROJ = ([x,y]) => [pad+(x-x0)*k*s, pad+(y1-y)*s];
  $('#map').setAttribute('viewBox', `0 0 ${W} ${H}`);
}
const trazar = polys => polys.map(p =>
  'M' + p[0].map(c => PROJ(c).map(v=>v.toFixed(1)).join(',')).join('L') + 'Z').join('');

/* ── utilidades ──────────────────────────────────────────── */
const filas = () => lvl==='upz' ? D.upz : D.loc;
const meta  = () => IND.find(i => i.k===ind);
const fmt = (v,dec=1) => (v===null||v===undefined||Number.isNaN(v)) ? '—'
  : v.toLocaleString('es-CO',{minimumFractionDigits:dec, maximumFractionDigits:dec});
const fmtInt = v => (v===null||v===undefined) ? '—' : Math.round(v).toLocaleString('es-CO');
const fmtP = p => p===null||p===undefined ? '' : (p < 0.001 ? 'p<0,001' : 'p ' + fmt(p,3));

/* ── mapa ────────────────────────────────────────────────── */
function pintarMapa(){
  const m = meta(), rows = filas(), g = D.geo[lvl];
  const vals = rows.map(r=>r[ind]).filter(v => v!==null && v!==undefined);
  const lo = Math.min(...vals), hi = Math.max(...vals);
  const ext = Math.max(Math.abs(lo), Math.abs(hi)) || 1;
  const norm = m.s==='div'                         // divergente: el cero queda en el centro
    ? v => .5 + v/(2*ext)
    : v => hi===lo ? .5 : (v-lo)/(hi-lo);

  $('#map').innerHTML = rows.filter(r => g[r.id]).map(r => {
    const v = r[ind];
    const fill = (v===null||v===undefined) ? 'var(--line)'
      : paleta(m.s==='est' ? (v-1)/5 : norm(v), m.s);
    const cls = sel===r.id ? 'on' : (sel ? 'dim' : '');
    return `<path d="${trazar(g[r.id])}" fill="${fill}" data-id="${r.id}" class="${cls}"><title>${r.nom}</title></path>`;
  }).join('');

  $('#lg-title').textContent = m.l + (m.u ? ' · ' + m.u : '');
  $('#lg-bar').innerHTML = rampaLeyenda(m.s).map(c=>`<i style="background:${c}"></i>`).join('');
  const dec = Math.max(Math.abs(lo), Math.abs(hi)) < 10 ? 2 : 0;
  $('#lg-min').textContent = m.s==='est' ? '1' : fmt(lo, dec);
  $('#lg-max').textContent = m.s==='est' ? '6' : fmt(hi, dec);

  const tip = $('#tip'), canvas = $('.canvas');
  $('#map').querySelectorAll('path').forEach(p => {
    p.addEventListener('mouseenter', () => {
      const r = rows.find(x => x.id===p.dataset.id);
      const b = p.getBoundingClientRect(), c = canvas.getBoundingClientRect();
      const v = r[ind];
      tip.innerHTML = `${r.nom}<br><b>${fmt(v, Math.abs(v||0)<10 ? 2 : 1)}</b> ${m.u}`;
      tip.style.left = (b.left - c.left + b.width/2) + 'px';
      tip.style.top  = (b.top  - c.top) + 'px';
      tip.classList.add('show');
    });
    p.addEventListener('mouseleave', () => tip.classList.remove('show'));
    p.addEventListener('click', () => {
      sel = sel===p.dataset.id ? null : p.dataset.id;
      pintarMapa(); pintarPanel(); pintarRanking();
    });
  });
}

/* ── panel de detalle ────────────────────────────────────── */
function pintarPanel(){
  const rows = filas();
  const orden = [...rows].sort((a,b)=>(b[ind] ?? -1e9)-(a[ind] ?? -1e9));
  const r = rows.find(x => x.id===sel) || orden[0];
  const tope = k => Math.max(...rows.map(x => Math.abs(x[k] ?? 0))) || 1;
  const linea = (k,lab,unit,dec=1) => (r[k]===null||r[k]===undefined) ? '' :
    `<div class="row"><span class="k">${lab}</span>
      <span class="v">${fmt(r[k],dec)}<small>${unit}</small></span>
      <span class="bar"><i style="width:${Math.min(100, Math.abs(r[k])/tope(k)*100).toFixed(0)}%"></i></span></div>`;

  const est = Math.round(r.estrato || 3);
  const chips = Object.entries(r.cluster || {})
    .filter(([,v]) => v && v !== 'No significativo')
    .map(([k,v]) => {
      const alto = /Hotspot/.test(v);
      return `<span class="chip ${alto?'c-crit':'c-ok'}">${VARLBL[k]||k}: ${alto?'concentración alta':'concentración baja'}</span>`;
    }).join('');

  const puesto = [...rows].sort((a,b)=>b.idx-a.idx).findIndex(x => x.id===r.id) + 1;
  $('#panel').innerHTML = `
    <div class="panel-head">
      <span class="eyebrow">${sel ? 'Zona fijada' : 'Valor más alto del indicador'}</span>
      <h3>${r.nom}</h3>
      <div class="sub">${lvl==='upz' ? `UPZ ${r.id} · ${r.loc}` : `Localidad ${r.id}`} · ${fmt(r.area,1)} km²
        &nbsp;<span class="est" style="background:${paleta((est-1)/5,'est')}">${est}</span></div>
      ${chips ? `<div style="margin-top:8px;display:flex;flex-wrap:wrap;gap:5px">${chips}</div>` : ''}
    </div>
    <div class="rows">
      ${linea('estrato','Estrato promedio','',2)}
      ${linea('pct12','Manzanas estrato 1 y 2','%',1)}
      ${linea('cestas','Cestas','/km²',0)}
      ${linea('deficit','Déficit de aseo','z',2)}
      ${linea('arrojo','Arrojo clandestino','/km²',2)}
      ${linea('emerg','Emergencias','/km²',0)}
      ${lvl==='loc' ? linea('homd','Homicidios','/km²',2) : linea('incendios','Incendios','',0)}
      ${lvl==='loc' ? linea('vif','Violencia intrafamiliar','',0) : linea('distbomb','Distancia a bomberos','m',0)}
    </div>
    <div class="panel-foot">${lvl==='upz'
      ? `Índice compuesto <b class="num">${fmt(r.idx,2)}</b>. Puesto ${puesto} de ${rows.length} UPZ.`
      : `Los delitos solo existen por localidad: la fuente DAILoc no baja a UPZ.`}</div>`;
}

/* ── rail: indicadores y autocorrelación ─────────────────── */
function pintarRail(){
  const box = $('#ind-list');
  box.querySelectorAll('.opt').forEach(n => n.remove());
  IND.filter(i => i.lv.includes(lvl)).forEach(i => {
    const b = document.createElement('button');
    b.type = 'button'; b.className = 'opt';
    b.setAttribute('aria-pressed', String(i.k===ind));
    b.title = i.d;
    b.innerHTML = `<span class="dot"></span>${i.l}`;
    b.onclick = () => { ind = i.k; sel = null; pintarRail(); pintarMapa(); pintarPanel(); };
    box.appendChild(b);
  });
  pintarMoran();
}
function pintarMoran(){
  const box = $('#moran');
  box.querySelectorAll('.stat, .cav').forEach(n => n.remove());
  const nivel = lvl==='upz' ? 'UPZ' : 'Localidad';
  const mv = meta().mv;
  const rs = D.moran.filter(m => m.niv===nivel && (!mv || m.var===mv || m.var===meta().mv));
  const lista = (mv ? rs : D.moran.filter(m => m.niv===nivel)).slice(0,4);
  box.insertAdjacentHTML('beforeend', lista.map(m => `
    <div class="stat"><span class="m">${VARLBL[m.var]||m.var}</span>
      <span class="s">I ${fmt(m.I,3)}</span>
      <span class="p ${m.sig?'sig':''}">${fmtP(m.p)}</span></div>`).join('') +
    `<p class="cav">I de Moran. Por encima de cero el fenómeno se agrupa en el espacio en vez de repartirse al azar.</p>`);
}
document.querySelectorAll('.seg button').forEach(b => {
  b.onclick = () => {
    lvl = b.dataset.lvl; sel = null;
    document.querySelectorAll('.seg button').forEach(x => x.setAttribute('aria-pressed', String(x===b)));
    if (!meta().lv.includes(lvl)) ind = 'estrato';
    pintarRail(); pintarMapa(); pintarPanel();
  };
});

/* ── contraste: la misma relación, sola y controlada ─────── */
function pintarContraste(){
  const rs = [
    {l:'Arrojo ↔ homicidios',  s:'medido solo',                          w:.827, txt:'rho 0,83',   p:'p<0,001', a:true},
    {l:'',                     s:'con estrato, déficit y cuadrantes',     w:.007, txt:'coef 0,007', p:'p 0,723', a:false},
    {l:'Arrojo ↔ emergencias', s:'medido solo',                          w:.397, txt:'rho 0,40',   p:'p<0,001', a:true},
    {l:'',                     s:'con estrato y bomberos en el modelo',   w:.009, txt:'coef −0,009',p:'p 0,681', a:false}
  ];
  $('#cmp').innerHTML = rs.map(f => `
    <div class="cmp-row">
      <div class="lbl">${f.l}<small>${f.s}</small></div>
      <div class="track">
        <i class="${f.a?'a':'b'}" style="width:${Math.max(f.w*100, 1.4).toFixed(1)}%"></i>
        <span class="${f.w<.2?'out':''}">${f.txt} · ${f.p}</span>
      </div>
    </div>`).join('') +
    `<p class="cav" style="margin-top:4px">Las dos medidas no comparten escala. Lo comparable no es el largo de la barra sino si el efecto sobrevive al control.</p>`;
}

/* ── tablero de hipótesis ────────────────────────────────── */
const NIVEL = {
  CONFIRMADA:                                 {c:'v-ok',   chip:'c-ok',   t:'Confirmada'},
  PARCIALMENTE_RESPALDADA:                    {c:'v-part', chip:'c-warn', t:'Parcial'},
  NO_RESPALDADA:                              {c:'v-no',   chip:'c-crit', t:'No respaldada'},
  PARCIALMENTE_RESPALDADA_POR_VULNERABILIDAD: {c:'v-part', chip:'c-warn', t:'Solo vía estrato'}
};
function pintarHipotesis(){
  const grupos = {};
  D.hip.forEach(h => (grupos[h.id] = grupos[h.id] || []).push(h));
  $('#hyps').innerHTML = Object.entries(grupos).map(([id, rs]) => {
    const n = NIVEL[rs[0].niv] || NIVEL.NO_RESPALDADA;
    const corto = m => m
      .replace('Binomial Negativa multivariable','NegBin')
      .replace('Spearman bivariado','Spearman')
      .replace('Moran Bivariado','Moran biv.')
      .replace('Mann-Whitney U','Mann-Whitney')
      .replace(', controla',', ctrl ')
      .replace('sub-periodo','periodo');
    const vistos = new Set();
    const st = rs.filter(r => {
      const k = r.met + '|' + r.stat;
      if (vistos.has(k)) return false; vistos.add(k); return true;
    }).slice(0,4);
    const iguales = new Set(st.map(r=>r.met)).size === 1 && st.length > 1;
    const items = st.map(r => `
      <div class="stat">
        <span class="m" title="${r.met}">${iguales ? (VARLBL[r.x]||r.x) : corto(r.met)}</span>
        <span class="s">${r.stat===null?'—':fmt(r.stat,3)}</span>
        <span class="p ${r.p!==null && r.p<0.05 ? 'sig':''}">${fmtP(r.p)}</span>
      </div>`).join('');
    return `<article class="hyp ${n.c}">
      <div class="hyp-top">
        <span class="hyp-id">${id==='H_CONJUNTA' ? 'Conjunta' : id}</span>
        <span class="chip ${n.chip}">${n.t}</span>
      </div>
      <h3>${rs[0].nom.replace(/->/g,'→')}</h3>
      <div class="stats">${items}</div>
    </article>`;
  }).join('');
}

/* ── series ──────────────────────────────────────────────── */
const SERIES = [
  {k:'emergencies',               l:'Emergencias atendidas',   e:'UAECOB',            c:'El corte de 2020 llega hasta agosto, no es un año completo.'},
  {k:'fires',                     l:'Incendios',               e:'UAECOB',            c:'Misma ventana y mismo corte parcial en 2020.'},
  {k:'rescues',                   l:'Rescates',                e:'UAECOB',            c:'Sube de forma sostenida hasta el corte de 2020.'},
  {k:'environmental_emergencies', l:'Emergencias ambientales', e:'UAECOB',            c:'2016 aparece en cero: la categoría no se registraba todavía.'},
  {k:'homicides',                 l:'Homicidios',              e:'DAILoc',            c:'Nueve años completos de datos. 2026 va en curso.'},
  {k:'domestic_violence',         l:'Violencia intrafamiliar', e:'DAILoc',            c:'2026 va parcial y ya supera a cualquier año anterior completo.'},
  {k:'residuos_total_t',          l:'Residuos recogidos',      e:'UAESP · toneladas', c:'2026 solo tiene 5 de los 12 archivos mensuales.'}
];
function pintarSeries(){
  $('#series').innerHTML = SERIES.filter(s => D.trends[s.k]).map(s => {
    const d = D.trends[s.k], W=280, H=68, pad=5;
    const ys = d.map(p => p[1]), lo = Math.min(...ys, 0), hi = Math.max(...ys);
    const px = i => pad + i*(W-pad*2)/Math.max(1, d.length-1);
    const py = v => H-pad - (v-lo)/((hi-lo)||1)*(H-pad*2-9);
    const pts = d.map((p,i) => [px(i), py(p[1])]);
    const linea = pts.map((p,i) => (i?'L':'M') + p[0].toFixed(1) + ',' + p[1].toFixed(1)).join('');
    const area  = linea + `L${px(d.length-1).toFixed(1)},${H-pad}L${pad},${H-pad}Z`;
    const fin = pts[pts.length-1], id = 'g-' + s.k;
    return `<div class="serie">
      <div class="serie-top"><h3>${s.l}</h3><span class="rng">${s.e}</span></div>
      <svg viewBox="0 0 ${W} ${H+14}" role="img" aria-label="${s.l}, de ${d[0][0]} a ${d[d.length-1][0]}">
        <defs><linearGradient id="${id}" x1="0" x2="0" y1="0" y2="1">
          <stop offset="0%" stop-color="var(--accent)" stop-opacity=".28"/>
          <stop offset="100%" stop-color="var(--accent)" stop-opacity="0"/>
        </linearGradient></defs>
        <line x1="${pad}" x2="${W-pad}" y1="${H-pad}" y2="${H-pad}" stroke="var(--line)" stroke-width="1"/>
        <path d="${area}" fill="url(#${id})"/>
        <path d="${linea}" fill="none" stroke="var(--accent)" stroke-width="1.8" stroke-linejoin="round" stroke-linecap="round"/>
        <circle cx="${fin[0].toFixed(1)}" cy="${fin[1].toFixed(1)}" r="3.2" fill="var(--accent)" stroke="var(--surface)" stroke-width="1.7"/>
        <text x="${pad}" y="${H+11}" font-size="9.5" fill="var(--ink-3)" style="font-family:var(--mono)">${d[0][0]}</text>
        <text x="${W-pad}" y="${H+11}" text-anchor="end" font-size="9.5" fill="var(--ink-3)" style="font-family:var(--mono)">${d[d.length-1][0]}</text>
        <text x="${W-pad}" y="11" text-anchor="end" font-size="11.5" font-weight="600" fill="var(--ink)" style="font-family:var(--mono)">${fmtInt(d[d.length-1][1])}</text>
      </svg>
      <p class="cav">${s.c}</p>
    </div>`;
  }).join('');
}

/* ── ranking ─────────────────────────────────────────────── */
function pintarRanking(){
  const top = [...D.upz].sort((a,b)=>b.idx-a.idx).slice(0,12);
  const mx = top[0].idx, mn = Math.min(...D.upz.map(u=>u.idx));
  $('#rank').innerHTML = top.map((u,i) => {
    const est = Math.round(u.estrato || 3);
    return `<tr data-id="${u.id}" class="${sel===u.id?'on':''}">
      <td class="rank">${i+1}</td>
      <td class="name">${u.nom}<small>${u.loc}</small></td>
      <td class="r"><span class="mini"><i style="width:${((u.idx-mn)/(mx-mn)*100).toFixed(0)}%"></i></span><span class="num">${fmt(u.idx,2)}</span></td>
      <td class="r"><span class="est" style="background:${paleta((est-1)/5,'est')}">${est}</span></td>
      <td class="r num">${fmt(u.deficit,2)}</td>
      <td class="r num">${fmt(u.arrojo,2)}</td>
    </tr>`;
  }).join('');
  $('#rank').querySelectorAll('tr').forEach(tr => tr.onclick = () => {
    lvl = 'upz'; sel = tr.dataset.id;
    document.querySelectorAll('.seg button').forEach(x => x.setAttribute('aria-pressed', String(x.dataset.lvl==='upz')));
    if (!meta().lv.includes('upz')) ind = 'idx';
    pintarRail(); pintarMapa(); pintarPanel(); pintarRanking();
  });
}

/* ── contadores ──────────────────────────────────────────── */
function pintarContadores(){
  $('#k-emerg').textContent  = fmtInt(D.upz.reduce((a,u)=>a+(u.nemerg||0), 0));
  $('#k-arrojo').textContent = fmtInt(D.loc.reduce((a,l)=>a+(l.narrojo||0), 0));
}

/* ── arranque y reacción al tema ─────────────────────────── */
function repintarColor(){ leerRampa(); pintarMapa(); pintarPanel(); pintarRanking(); }
leerRampa(); proyectar();
pintarRail(); pintarMapa(); pintarPanel();
pintarContraste(); pintarHipotesis(); pintarSeries(); pintarRanking(); pintarContadores();
matchMedia('(prefers-color-scheme:dark)').addEventListener('change', repintarColor);
new MutationObserver(repintarColor).observe(document.documentElement, {attributes:true, attributeFilter:['data-theme']});
