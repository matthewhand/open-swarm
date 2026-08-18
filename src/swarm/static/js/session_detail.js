// Session detail graph (loaded via {% static %} from session_detail.html).
(function(){
  var holder = document.getElementById('deleg-data'); var mount = document.getElementById('agent-graph');
  if(!holder || !mount) return;
  var dels = [];
  try { dels = JSON.parse(holder.textContent) || []; }
  catch(e){ mount.innerHTML = '<div class="sd-meta">⚠ Could not render the graph — see the delegation timeline below.</div>'; return; }
  if(!dels.length){ mount.innerHTML = '<div class="sd-meta">No delegations recorded for this session.</div>'; return; }
  var SVGNS = 'http://www.w3.org/2000/svg';
  var color = { completed:'#22c55e', failed:'#ef4444', in_progress:'#3b82f6', queued:'#64748b' };
  var W = Math.max(560, 220 + dels.length*150), H = 300, cx = 130, cy = H/2;
  var svg = document.createElementNS(SVGNS,'svg');
  // Responsive: scale to the container width (viewBox keeps the aspect ratio),
  // but never stretch past the natural width on desktop. On a phone the whole
  // graph shrinks to fit instead of forcing a horizontal scroll.
  svg.setAttribute('viewBox','0 0 '+W+' '+H);
  svg.setAttribute('width','100%');
  svg.setAttribute('preserveAspectRatio','xMidYMid meet');
  svg.style.maxWidth = W+'px'; svg.style.height = 'auto'; svg.style.display = 'block';
  svg.setAttribute('role','img');
  svg.setAttribute('aria-label', dels.length+' sub-agent delegation'+(dels.length===1?'':'s')
    +' routed from the claude -p orchestrator; node colour indicates status');
  function el(n, attrs, text){ var e=document.createElementNS(SVGNS,n); for(var k in attrs) e.setAttribute(k, attrs[k]); if(text!=null){e.textContent=text;} return e; }
  // spoke layout: nodes in a vertical column to the right of the brain
  var n = dels.length, gap = Math.min(90, (H-60)/Math.max(1,n-1) || 0), startY = cy - gap*(n-1)/2;
  dels.forEach(function(d, i){
    var nx = W-170, ny = (n===1? cy : startY + i*gap), c = color[d.status] || '#64748b';
    svg.appendChild(el('path', {d:'M '+(cx+78)+' '+cy+' C '+(W/2)+' '+cy+', '+(W/2)+' '+ny+', '+nx+' '+ny,
      fill:'none', stroke:c, 'stroke-width':2, opacity:.7}));
  });
  // brain node
  svg.appendChild(el('circle',{cx:cx,cy:cy,r:46,fill:'#0f1219',stroke:'#a78bfa','stroke-width':2}));
  svg.appendChild(el('text',{x:cx,y:cy-4,'text-anchor':'middle',fill:'#e9d5ff','font-size':'13','font-weight':'700'},'🧠 claude -p'));
  svg.appendChild(el('text',{x:cx,y:cy+13,'text-anchor':'middle',fill:'#a78bfa','font-size':'10'},'orchestrator'));
  dels.forEach(function(d, i){
    var nx = W-170, ny = (n===1? cy : startY + i*gap), c = color[d.status] || '#64748b';
    var g = el('g',{}); g.appendChild(el('rect',{x:nx,y:ny-22,rx:9,width:150,height:44,fill:'#1b1f29',stroke:c,'stroke-width':2}));
    g.appendChild(el('circle',{cx:nx+14,cy:ny,r:6,fill:c}));
    g.appendChild(el('text',{x:nx+28,y:ny-3,fill:'#e2e8f0','font-size':'12','font-weight':'600'}, d.role||'?'));
    g.appendChild(el('text',{x:nx+28,y:ny+13,fill:'#94a3b8','font-size':'10'}, (d.model_used||'role-default')+' · '+(d.status||'')));
    svg.appendChild(g);
  });
  mount.appendChild(svg);
})();
