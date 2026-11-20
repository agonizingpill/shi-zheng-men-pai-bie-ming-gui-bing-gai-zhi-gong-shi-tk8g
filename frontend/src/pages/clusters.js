import{heading,badge}from'../components/registry.js';
import{esc}from'../utils/format.js';
import{STATES,LINEAGE,ROLES}from'../constants.js';
import{user,api}from'../utils/api.js';
let query='',result=null,lookupError='';
const padNo=n=>'C'+String(n).padStart(3,'0');
function aliasText(d,id){return d.aliases.find(a=>a.id===id)?.text||('别名#'+id)}
function runState(d,runId){return d.runs.find(r=>r.id===runId)?.state||'-'}
export function render(d){
 const isSup=user.role==='supervisor';
 const publishedRunIds=new Set(d.batches.map(b=>b.run_id));
 const readyRuns=d.runs.filter(r=>r.state==='ready'&&!publishedRunIds.has(r.id));
 const activeBatch=d.batches.find(b=>b.state==='active');
 const membersByCluster={};
 for(const m of d.cluster_members){(membersByCluster[m.cluster_id]??=[]).push(m.alias_id)}
 const clusterRows=d.clusters.map(c=>({...c,members:membersByCluster[c.id]||[]}));
 const batchBlock=b=>{
  const cs=clusterRows.filter(c=>c.batch_id===b.id).sort((a,z)=>a.cluster_no-z.cluster_no);
  return `<article class="batch"><h3>批次 #${b.id} <small>匹配任务 ${b.run_id}（${esc(runState(d,b.run_id))}）· 发布于 ${esc(b.published)}</small> ${badge(b.state)}</h3><table><thead><tr><th>簇号</th><th>本批成员（别名）</th><th>成员数</th></tr></thead><tbody>${cs.map(c=>`<tr><td><a href="#clusters?no=${c.cluster_no}"><b>${padNo(c.cluster_no)}</b></a></td><td>${c.members.map(a=>esc(aliasText(d,a))).join('、')||'<span class="muted">无成员</span>'}</td><td>${c.members.length}</td></tr>`).join('')}</tbody></table></article>`;
 };
 const lineageBlock=()=>{
  if(!query)return '<p class="muted">输入簇号（如 1 或 C001）查询该号在各批次的成员与拆合去向。</p>';
  if(lookupError)return `<p class="error">${esc(lookupError)}</p>`;
  if(!result)return '<p class="muted">查询中…</p>';
  const peer=no=>no==null?'<span class="muted">—</span>':padNo(no);
  return `<h2>簇号 ${padNo(result.cluster_no)} 的跨批核验</h2><div class="split"><section><h3>各批成员</h3>${result.batches.map(b=>`<article class="batch"><b>${padNo(b.cluster_no)}</b> <small>批次 #${b.batch_id} / 任务 ${b.run_id}</small> ${badge(b.state)}<p>${b.members.map(a=>esc(aliasText(d,a))).join('、')}</p></article>`).join('')}</section><section><h3>去向与来源</h3><table><thead><tr><th>批次</th><th>关系</th><th>方向</th><th>对端簇号</th><th>共享别名</th></tr></thead><tbody>${result.lineage.map(x=>`<tr><td>#${x.batch_id}</td><td>${esc(LINEAGE[x.relation]||x.relation)}</td><td>${x.direction==='outgoing'?'去向':'来源'}</td><td>${peer(x.peer_cluster_no)}</td><td>${x.shared}</td></tr>`).join('')}</tbody></table></section></div>`;
 };
 return heading('07','旧号找得到原组，拆合都有去向。','每次重算按共享别名做最大权配对，一个旧号只续给一簇；发布时以当时在用批次接续，重试不重复占号。')
 +`<div class="split"><section><h2>簇号核验</h2><form id="cluster-lookup"><label>按簇号查询<input name="no" value="${esc(query)}" placeholder="1 或 C001" required></label><button>查各批成员与去向</button></form>${lineageBlock()}</section><aside><h2>发布匹配批次为簇号</h2>${isSup?'':'<p class="muted">当前为只读角色，仅核定员可发布。</p>'}${readyRuns.length?readyRuns.map(r=>`<article class="batch"><b>匹配任务 #${r.id}</b> ${badge(r.state)}<p class="muted">簇数 ${r.result?.clusters?new Set(r.result.clusters.map(x=>x.label)).size:0}</p>${isSup?`<form data-endpoint="/batches" data-method="POST"><input type="hidden" name="run_id" value="${r.id}"><button>发布该批次并接续旧号</button></form>`:'<p class="muted">仅核定员可发布</p>'}</article>`).join(''):'<p class="muted">没有待发布的已计算批次，先到「归并候选」页计算。</p>'}${activeBatch?`<p class="muted">当前在用：批次 #${activeBatch.id}（任务 ${activeBatch.run_id}）</p>`:''}</aside></div><h2>历史批次</h2>${[...d.batches].sort((a,b)=>b.id-a.id).map(batchBlock).join('')||'<p class="muted">尚未发布任何簇号批次。</p>'}`;
}
export function hydrate(){
 const m=location.hash.match(/[?&]no=([^&]+)/);if(!m)return;
 const raw=decodeURIComponent(m[1]).trim().replace(/^[cC]0*/,'');
 const no=Number(raw);
 if(Number.isInteger(no)&&no>0&&String(no)!==query){query=String(no);doLookup(no)}
}
async function doLookup(no){
 lookupError='';result=null;
 try{result=await api('/clusters/'+no)}catch(e){lookupError=e.message}
 const ev=new Event('cluster-lookup-done');window.dispatchEvent(ev);
}
document.addEventListener('submit',async e=>{
 const f=e.target;
 if(f.id!=='cluster-lookup')return;
 e.preventDefault();
 const raw=String(new FormData(f).get('no')||'').trim().replace(/^[cC]0*/,'');
 const no=Number(raw);
 if(!Number.isInteger(no)||no<1){lookupError='请输入正整数簇号';result=null;query=raw;window.dispatchEvent(new Event('cluster-lookup-done'));return}
 query=raw;doLookup(no);
});
window.addEventListener('cluster-lookup-done',()=>{
 const app=window.__rerender;if(app)app();
});
