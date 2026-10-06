'use strict';
const $ = id => document.getElementById(id);
const token = location.hash.slice(1);
const state = {page:'editor', stats:null, detail:null, dirty:false, offset:0, limit:50, listing:null, batch:null, imported:null, request:0,
  filters:{resource:'all', status:'all', group:'all', q:''}};
const titles = {overview:'ภาพรวม',editor:'ข้อความ'};
const labels = {reviewed:'ตรวจแล้ว',draft:'ฉบับร่าง',untranslated:'ยังไม่แปล'};
const number = value => Number(value).toLocaleString('th-TH');
function node(tag, className, text) { const e=document.createElement(tag); if(className)e.className=className; if(text!==undefined)e.textContent=text; return e; }
function notify(text, error=false) {
  const messages={'Placeholder/tag signature differs from source':'ตัวแปรหรือแท็กไม่ตรงกับต้นฉบับ กรุณาคงตัวแปร เช่น {door} ให้ครบ','Unreal input/image token differs from source':'รหัสปุ่มหรือรูปภาพของ Unreal เปลี่ยนไป กรุณาคงรหัสเดิม','Result must contain every batch ID exactly once':'ไฟล์คำตอบต้องมีรหัสครบตามชุดงาน โดยแต่ละรหัสปรากฏครั้งเดียว'};
  if(error)text=messages[text]||text;
  $('message').textContent=text; $('message').className='message'+(error?' error':''); $('message').hidden=false;
  const dialog=document.querySelector('dialog[open]');
  if(dialog){let p=dialog.querySelector('.dialog-feedback');if(!p){p=node('p');dialog.append(p);}p.className='dialog-feedback '+(error?'dialog-error':'dialog-success');p.setAttribute('role',error?'alert':'status');p.textContent=text;}
}
async function api(path, data) {
  const response=await fetch('/api/'+path,{method:data===undefined?'GET':'POST',headers:{'X-Localizer-Token':token,...(data===undefined?{}:{'Content-Type':'application/json'})},...(data===undefined?{}:{body:JSON.stringify(data)})});
  if(!response.ok){const value=await response.json();throw new Error(value.error||'ไม่สามารถทำรายการได้');}
  return response.headers.get('Content-Type').startsWith('text/csv')?response.blob():response.json();
}
function download(value,name,type='application/json') {const blob=value instanceof Blob?value:new Blob([JSON.stringify(value,null,2)],{type});const url=URL.createObjectURL(blob);const a=node('a');a.href=url;a.download=name;a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);}
let guardPending=false;
async function guarded(){if(!state.dirty)return true;if(guardPending)return false;guardPending=true;const dialog=$('unsavedDialog');dialog.returnValue='';return new Promise(resolve=>{dialog.addEventListener('close',()=>{guardPending=false;resolve(dialog.returnValue==='discard');},{once:true});dialog.showModal();});}
$('discardChanges').onclick=()=>$('unsavedDialog').close('discard');
async function closeDialog(id){if(id==='contextDialog'&&state.dirty){if(!await guarded())return;state.dirty=false;renderEditor();}$(id).close();}
async function openResource(resource){if(!await guarded())return;state.dirty=false;state.filters={resource,status:'all',group:'all',q:''};state.offset=0;$('search').value='';$('statusFilter').value='all';$('resourceFilter').value=resource;selectPage('editor',true);await refreshList(false).catch(e=>notify(e.message,true));}
async function selectPage(page, force=false) {
  if(!force && !await guarded())return false;
  if(state.dirty&&state.detail)renderEditor();
  state.dirty=false;state.page=page;document.body.classList.toggle('editor-view',page==='editor');
  document.querySelectorAll('.page').forEach(p=>p.hidden=p.id!=='page-'+page);
  document.querySelectorAll('[data-page]').forEach(b=>{b.classList.toggle('active',b.dataset.page===page);if(b.dataset.page===page)b.setAttribute('aria-current','page');else b.removeAttribute('aria-current');});
  $('pageTitle').textContent=titles[page];$('breadcrumb').textContent='พื้นที่ทำงาน / '+titles[page];

}
function fillSelect(select,resources,all=false) {const previous=select.value;select.replaceChildren();if(all){const option=node('option',null,'ทุกทรัพยากร');option.value='all';select.append(option);}for(const r of resources){const option=node('option',null,r.name);option.value=r.id;select.append(option);}if([...select.options].some(o=>o.value===previous))select.value=previous;}
async function refreshStats(){
  state.stats=await api('state');const s=state.stats;
  $('projectTitle').textContent=s.title;$('connection').textContent='● ในเครื่อง';
  $('workspaceStatus').textContent=number(s.total)+' รายการ · '+number(s.counts.reviewed||0)+' ตรวจแล้ว · '+s.reviewed_percent+'%';
  $('overviewPercent').textContent=s.reviewed_percent+'%';$('overviewCount').textContent=number(s.counts.reviewed||0)+' จาก '+number(s.total)+' รายการ';$('overviewProgress').value=s.reviewed_percent;
  $('draftCount').textContent=number(s.counts.draft||0);$('untranslatedCount').textContent=number(s.counts.untranslated||0);$('issueCount').textContent=number(s.issues);
  fillSelect($('resourceFilter'),s.resources,true);$('resourceFilter').value=state.filters.resource;
  fillSelect($('aiResource'),s.resources);fillSelect($('exportResource'),s.resources);
  $('resourceSummary').replaceChildren();
  for(const r of s.resources){const row=node('button','resource-row');row.type='button';row.title='เปิดชุดข้อความ '+r.name;row.onclick=()=>openResource(r.id);row.append(node('strong',null,r.name));const progress=node('progress');progress.max=r.total;progress.value=r.reviewed;row.append(progress,node('span',null,number(r.reviewed)+' / '+number(r.total)));$('resourceSummary').append(row);}
}
async function refreshList(keep=true){
  const scrollTop=keep?$('entryList').scrollTop:0;
  const request=++state.request;const params=new URLSearchParams({...state.filters,offset:state.offset,limit:state.limit});
  $('entryList').setAttribute('aria-busy','true');
  try{
    const listing=await api('entries?'+params);if(request!==state.request)return;state.listing=listing;
    $('resultCount').textContent=number(listing.total);const groupSelect=$('groupFilter');groupSelect.replaceChildren();let option=node('option',null,'ทุกหมวด');option.value='all';groupSelect.append(option);
    for(const [key,count]of Object.entries(listing.groups)){option=node('option',null,key+' · '+number(count));option.value=key;groupSelect.append(option);}groupSelect.value=state.filters.group;
    $('entryList').replaceChildren();
    listing.items.forEach((item,index)=>{
      const button=node('button','entry-row');button.type='button';button.dataset.resource=item.resource;button.dataset.id=item.id;button.setAttribute('aria-pressed',String(state.detail?.resource===item.resource&&state.detail?.entry.id===item.id));button.classList.toggle('selected',button.getAttribute('aria-pressed')==='true');
      const meta=node('div','row-meta');meta.append(node('span','row-number',number(state.offset+index+1)));const key=node('span','row-key',item.id);key.title=item.id;meta.append(key,node('span','status '+(item.issue?'issue':item.status),item.issue?'ตรวจรูปแบบ':labels[item.status]));
      button.append(meta,node('div','row-source',item.source),node('div','row-target',item.target||'ยังไม่มีคำแปล'));button.addEventListener('click',()=>openEntry(item.resource,item.id).catch(e=>notify(e.message,true)));$('entryList').append(button);
    });
    $('entryList').scrollTop=scrollTop;
    if(!listing.items.length)$('entryList').append(node('div','no-results',state.stats.total?'ไม่พบข้อความตามเงื่อนไขนี้':'นำเข้าไฟล์ CSV เพื่อเริ่มโปรเจกต์'));
    $('pageRange').textContent=listing.total?number(state.offset+1)+'–'+number(Math.min(state.offset+state.limit,listing.total))+' จาก '+number(listing.total):'0 รายการ';
    $('prevPage').disabled=state.offset===0;$('nextPage').disabled=state.offset+state.limit>=listing.total;
    if(!keep && listing.items.length)await openEntry(listing.items[0].resource,listing.items[0].id,true);
    else if(!keep){state.detail=null;state.dirty=false;$('entryEditor').replaceChildren(node('div','empty-editor','ไม่พบข้อความ ลองเปลี่ยนคำค้นหรือตัวกรอง'));}
  }finally{$('entryList').removeAttribute('aria-busy');}
}
async function openEntry(resource,id,force=false){
  if(!force&&!await guarded())return;
  state.detail=await api('entry?'+new URLSearchParams({resource,id}));state.dirty=false;renderEditor();
  document.querySelectorAll('.entry-row').forEach(b=>{const selected=b.dataset.resource===resource&&b.dataset.id===id;b.classList.toggle('selected',selected);b.setAttribute('aria-pressed',String(selected));if(selected)b.scrollIntoView({block:'nearest'});});
}
function renderEditor(){
  const d=state.detail,e=d.entry;
  $('entryEditor').innerHTML=`<div class="entry-top"><h2>แก้ไขคำแปล</h2><span id="entryStatus" class="status"></span></div><div class="entry-key" id="entryKey"></div><div class="text-label">ต้นฉบับ <span>อ่านอย่างเดียว · <button id="splitSource" class="text-link">แยกบรรทัด</button></span></div><div id="sourceText" class="source-text"></div><div class="text-label">คำแปล <span id="dirtyState">บันทึกแล้ว</span></div><textarea class="target-editor" id="targetText" rows="6" aria-label="แก้ไขคำแปล" spellcheck="false"></textarea><div id="tokens" class="token-strip"></div><div id="entryIssue" class="inline-issue" hidden></div><div class="editor-tools"><button class="button primary" id="saveNext">บันทึกแล้วไปต่อ →</button><button class="button" id="saveTarget">บันทึก</button><button class="button" id="reviewOpen">ตรวจรับ</button><button class="button push" id="nextEntry">รายการถัดไป →</button></div><details class="context-preview"><summary>บริบทของข้อความ</summary><dl id="contextPreview"></dl><button class="text-link" id="editContext">แก้บริบทและหลักฐาน →</button></details><details class="nearby"><summary>ข้อความข้างเคียงในไฟล์</summary><p class="subtle">ลำดับในไฟล์ไม่ยืนยันว่าเป็นลำดับฉาก ใช้ช่วยค้นหลักฐานเท่านั้น</p><div id="nearbyLines"></div></details><details class="nearby" id="historyDetails"><summary>ประวัติการแก้ไข</summary><div id="historyRows"></div></details>`;
  $('entryStatus').className='status '+e.status;$('entryStatus').textContent=labels[e.status];$('entryKey').textContent=e.id;$('sourceText').textContent=e.source;$('targetText').value=e.target||'';
  $('tokens').replaceChildren(...d.markers.map(t=>node('span',null,t)));if(d.issue){$('entryIssue').textContent=d.issue;$('entryIssue').hidden=false;}
  const c=e.context||{};for(const [name,key]of [['ฉาก','scene'],['ผู้พูด','speaker'],['ผู้ฟัง','listener'],['หลักฐาน','references']]){let value=c[key];if(Array.isArray(value))value=value.length+' แหล่ง';$('contextPreview').append(node('dt',null,name),node('dd',null,value||'ยังไม่ระบุ'));}
  d.nearby.forEach(n=>{const p=node('p',null,n.source);if(n.id===e.id)p.style.fontWeight='600';$('nearbyLines').append(p);});
  $('saveTarget').disabled=true;
  $('targetText').addEventListener('input',()=>{state.dirty=true;$('saveTarget').disabled=false;$('dirtyState').textContent='● ยังไม่บันทึก';$('dirtyState').className='dirty-state';});
  $('saveTarget').onclick=()=>saveTarget();$('saveNext').onclick=async()=>{if(await saveTarget())nextEntry().catch(e=>notify(e.message,true));};$('reviewOpen').onclick=()=>{$('reviewer').value=localStorage.getItem('reviewer')||'';$('reviewDialog').showModal();};
  $('editContext').onclick=async()=>{if(!await guarded())return;state.dirty=false;renderEditor();renderContext();$('contextDialog').showModal();};$('nextEntry').onclick=()=>nextEntry().catch(e=>notify(e.message,true));
  let split=false;$('splitSource').onclick=()=>{split=!split;$('splitSource').textContent=split?'ดูข้อความเดิม':'แยกบรรทัด';if(!split){$('sourceText').textContent=e.source;return;}renderSourceLines(e.source);};
  $('historyDetails').addEventListener('toggle',()=>{if($('historyDetails').open)loadHistory();});
}
function renderSourceLines(source){
  const segments=[];let text='',marker='';for(const part of source.split(/(\{\d+(?:\.\d+)?\})/)){if(/^\{\d+(?:\.\d+)?\}$/.test(part)){if(text)segments.push({text,marker});marker=part;text='';}else text+=part;}if(text||marker)segments.push({text,marker});
  $('sourceText').replaceChildren();let index=0;for(const segment of segments){for(const text of segment.text.split(/\r?\n/)){const row=node('div','source-line');row.append(node('span','line-num',String(++index)));const content=node('span');if(segment.marker)content.append(node('span','time-mark',segment.marker));content.append(document.createTextNode(text));row.append(content);$('sourceText').append(row);}}
}
async function saveTarget(approve=false,extra={}){
  if(!state.detail)return;const target=$('targetText').value;const d=state.detail;
  if(!approve&&target===(d.entry.target||'')){state.dirty=false;renderEditor();return true;}
  try{state.detail=await api(approve?'review':'edit',{resource:d.resource,id:d.entry.id,revision:d.revision,target,...extra});state.dirty=false;renderEditor();await refreshStats();await refreshList();notify(approve?'ตรวจรับคำแปลแล้ว':'บันทึกฉบับร่างแล้ว ยังไม่เปลี่ยนไฟล์เกม');return true;}catch(error){notify(error.message,true);return false;}
}
async function nextEntry(){
  if(!await guarded())return;state.dirty=false;const items=state.listing?.items||[];const index=items.findIndex(i=>i.resource===state.detail?.resource&&i.id===state.detail?.entry.id);
  if(index>=0&&index+1<items.length)return openEntry(items[index+1].resource,items[index+1].id,true);
  if(state.offset+state.limit<state.listing.total){state.offset+=state.limit;await refreshList(false);}else notify('ถึงรายการสุดท้ายตามเงื่อนไขนี้แล้ว');
}
function referenceText(refs){return (refs||[]).map(r=>typeof r==='string'?r:r.uri||r.url||'').filter(Boolean).join('\n');}
function renderContext(){
  const container=$('contextForm');container.replaceChildren();if(!state.detail){container.append(node('p',null,'เลือกข้อความจากหน้า “ข้อความ” ก่อนบันทึกบริบท'));return;}
  const e=state.detail.entry,c=e.context||{};
  container.innerHTML=`<form class="context-form" id="contextEdit"><div class="context-selection" id="contextSelection"></div><div class="columns"><label>ผู้พูด<input id="ctxSpeaker" placeholder="ระบุเมื่อมีหลักฐาน"></label><label>ผู้ฟัง<input id="ctxListener" placeholder="บุคคลหรือกลุ่มที่พูดถึง"></label></div><label>ฉาก / หน้าจอ<input id="ctxScene" placeholder="สถานที่ เหตุการณ์ หรือหน้าจอ UI"></label><label>บันทึกบริบท<textarea id="ctxNotes" rows="4" placeholder="เหตุการณ์ก่อนหน้า สิ่งที่อ้างถึง และข้ออนุมานที่ต้องตรวจ"></textarea></label><label>หลักฐานอ้างอิง — หนึ่งแหล่งต่อบรรทัด<textarea id="ctxRefs" rows="3" placeholder="ลิงก์ หรือเส้นทางทรัพยากรในโปรเจกต์"></textarea></label><div class="columns"><label>พร้อมแปลหรือยัง<select id="ctxReady"><option value="pending">ยังขาดบริบท</option><option value="ready">มีหลักฐานเพียงพอ</option><option value="conflicting">หลักฐานขัดแย้ง</option></select></label><label>ความมั่นใจ<select id="ctxConfidence"><option value="low">ต่ำ</option><option value="medium">ปานกลาง</option><option value="high">สูง</option></select></label></div><button class="button primary" type="submit">บันทึกบริบท</button><button class="button" id="backToEditor" type="button">กลับไปข้อความ</button><p class="subtle">การแก้บริบทจะคืนสถานะเป็นฉบับร่าง ให้ตรวจรับอีกครั้งเมื่อพร้อม</p></form>`;
  $('contextSelection').textContent=e.id;$('ctxSpeaker').value=c.speaker||'';$('ctxListener').value=c.listener||'';$('ctxScene').value=c.scene||'';$('ctxNotes').value=c.notes||'';$('ctxRefs').value=referenceText(c.references);
  $('ctxReady').value=c.translation_readiness||'pending';$('ctxConfidence').value=String(c.confidence||'low').startsWith('high')?'high':String(c.confidence||'low').startsWith('medium')?'medium':'low';
  $('contextEdit').addEventListener('input',()=>state.dirty=true);$('backToEditor').textContent='ปิด';$('backToEditor').onclick=()=>closeDialog('contextDialog');
  $('contextEdit').onsubmit=async event=>{event.preventDefault();const context={...c,speaker:$('ctxSpeaker').value,listener:$('ctxListener').value,scene:$('ctxScene').value,notes:$('ctxNotes').value,translation_readiness:$('ctxReady').value,confidence:$('ctxConfidence').value};
    context.references=$('ctxRefs').value.trim()===referenceText(c.references).trim()?(c.references||[]):$('ctxRefs').value.split('\n').map(v=>v.trim()).filter(Boolean).map(uri=>({type:/^https?:\/\//.test(uri)?'web':'local_resource',uri,supports:context.notes}));
    try{state.detail=await api('edit',{resource:state.detail.resource,id:e.id,revision:state.detail.revision,context});state.dirty=false;renderContext();renderEditor();await refreshStats();await refreshList();notify('บันทึกบริบทแล้ว');}catch(error){notify(error.message,true);}
  };
}
async function loadHistory(){
  try{const rows=await api('history?'+new URLSearchParams({resource:state.detail.resource,id:state.detail.entry.id}));const container=$('historyRows');container.replaceChildren();if(!rows.length)container.append(node('p','subtle','ยังไม่มีประวัติการแก้ไขใน GUI'));
    for(const row of rows){const item=node('div','history-row');const text=node('div');text.append(node('span',null,new Date(row.timestamp).toLocaleString('th-TH')),node('p',null,row.target||'ยังไม่มีคำแปล'));const restore=node('button','button','คืนเป็นฉบับร่าง');restore.onclick=async()=>{if(!await guarded())return;try{state.detail=await api('restore',{resource:state.detail.resource,id:state.detail.entry.id,revision:state.detail.revision,checkpoint:row.checkpoint});state.dirty=false;renderEditor();await refreshStats();await refreshList();notify('คืนข้อความก่อนหน้าเป็นฉบับร่างแล้ว');}catch(error){notify(error.message,true);}};item.append(text,restore);container.append(item);}
  }catch(error){notify(error.message,true);}
}
function parseHeader(text){const line=text.replace(/^\uFEFF/,'').split(/\r?\n/)[0];const columns=[];let value='',quoted=false;for(let i=0;i<line.length;i++){const char=line[i];if(char==='"'){if(quoted&&line[i+1]==='"'){value+='"';i++;}else quoted=!quoted;}else if(char===','&&!quoted){columns.push(value);value='';}else value+=char;}columns.push(value);return columns;}
async function loadJsonFile(input){const file=input.files[0];if(!file)throw new Error('เลือกไฟล์ JSON ก่อน');if(file.size>16*1024*1024)throw new Error('ไฟล์ใหญ่เกิน 16 MB');return JSON.parse(await file.text());}
document.querySelectorAll('[data-page]').forEach(b=>b.onclick=()=>selectPage(b.dataset.page));
$('aiOpen').onclick=()=>$('aiDialog').showModal();$('exportOpen').onclick=()=>$('exportDialog').showModal();
let debounce;$('search').oninput=()=>{clearTimeout(debounce);debounce=setTimeout(async()=>{if(!await guarded()){$('search').value=state.filters.q;return;}state.dirty=false;state.filters.q=$('search').value;state.offset=0;refreshList(false).catch(e=>notify(e.message,true));},240);};
for(const [id,key]of [['resourceFilter','resource'],['statusFilter','status'],['groupFilter','group']]){$(id).onchange=async()=>{if(!await guarded()){$(id).value=state.filters[key];return;}state.dirty=false;state.filters[key]=$(id).value;if(key==='resource')state.filters.group='all';state.offset=0;refreshList(false).catch(e=>notify(e.message,true));};}
$('prevPage').onclick=async()=>{if(!await guarded())return;state.dirty=false;state.offset=Math.max(0,state.offset-state.limit);refreshList(false).catch(e=>notify(e.message,true));};
$('nextPage').onclick=async()=>{if(!await guarded())return;state.dirty=false;state.offset+=state.limit;refreshList(false).catch(e=>notify(e.message,true));};
$('continueWork').onclick=async()=>{if(!await guarded())return;state.dirty=false;state.filters.status='draft';$('statusFilter').value='draft';state.offset=0;selectPage('editor');refreshList(false).catch(e=>notify(e.message,true));};
$('importOpen').onclick=()=>$('importDialog').showModal();document.querySelectorAll('[data-close]').forEach(b=>b.onclick=()=>closeDialog(b.dataset.close));
document.querySelectorAll('dialog').forEach(d=>{d.addEventListener('close',()=>d.querySelector('.dialog-feedback')?.remove());d.addEventListener('cancel',event=>{if(d.id==='contextDialog'){event.preventDefault();closeDialog(d.id);}});});
$('importFile').onchange=async()=>{state.imported=null;try{const file=$('importFile').files[0];if(!file)return;if(file.size>16*1024*1024)throw new Error('รองรับไฟล์ข้อความไม่เกิน 16 MB กรุณาส่งออกข้อความจากเอนจินก่อน');const content=await file.text();state.imported={name:file.name,content};const headers=parseHeader(content);for(const id of ['idColumn','sourceColumn']){$(id).replaceChildren(...headers.map(h=>{const option=node('option',null,h);option.value=h;return option;}));}
  $('idColumn').value=headers.find(h=>/^(key|keys|id)$/i.test(h))||headers[0];$('sourceColumn').value=headers.find(h=>/^(source|en|english\(en\))$/i.test(h))||headers[1]||headers[0];$('targetColumn').value=headers.find(h=>/^(target|th|thai\(th\))$/i.test(h))||'target';if(headers.includes('Id')&&headers.some(h=>h.includes('(en)')))$('importEngine').value='unity';else if(headers.includes('keys'))$('importEngine').value='godot';
}catch(error){notify(error.message,true);}};
$('importForm').onsubmit=async event=>{event.preventDefault();if(!await guarded())return;state.dirty=false;if(state.detail)renderEditor();try{if(!state.imported)throw new Error('เลือกไฟล์ CSV ก่อน');await api('import',{...state.imported,engine:$('importEngine').value,id_column:$('idColumn').value,source_column:$('sourceColumn').value,target_column:$('targetColumn').value});$('importDialog').close();await refreshStats();await refreshList(false);notify('นำเข้าข้อความเป็นสำเนาแล้ว คำแปลเดิมมีสถานะฉบับร่าง');}catch(error){notify(error.message,true);}};
$('reviewForm').onsubmit=async event=>{event.preventDefault();const reviewer=$('reviewer').value,notes=$('reviewNotes').value;if(await saveTarget(true,{reviewer,notes})){localStorage.setItem('reviewer',reviewer);$('reviewDialog').close();$('reviewNotes').value='';}};
$('createBatch').onclick=async()=>{try{const resource=$('aiResource').value;if(!resource)throw new Error('นำเข้าทรัพยากรก่อนสร้างชุดงาน');const limit=Number($('batchLimit').value);if(!Number.isInteger(limit)||limit<1||limit>100)throw new Error('ระบุจำนวนรายการเป็นจำนวนเต็ม 1–100');state.batch=await api('batch',{resource,limit});$('researchPrompt').textContent=state.batch.research_prompt;download(state.batch,'ai-research-batch.json');notify('สร้างชุดงานแล้ว ให้ AI ส่งรายงานบริบทก่อนเริ่มแปล');}catch(error){notify(error.message,true);}};
$('copyResearch').onclick=async()=>{try{if(!state.batch)throw new Error('สร้างชุดงานก่อน');await navigator.clipboard.writeText(state.batch.research_prompt);notify('คัดลอกคำสั่งค้นบริบทแล้ว');}catch(error){notify(error.message,true);}};
$('applyResult').onclick=async()=>{if(!await guarded())return;state.dirty=false;if(state.detail)renderEditor();try{const b=$('batchFile').files.length?await loadJsonFile($('batchFile')):state.batch;if(!b)throw new Error('เลือกไฟล์ชุดงานที่ส่งให้ AI');const result=await loadJsonFile($('resultFile'));await api('apply',{batch:b,result});if(state.detail)await openEntry(state.detail.resource,state.detail.entry.id,true);await refreshStats();await refreshList();notify('ตรวจรูปแบบผ่าน รับคำแปลเป็นฉบับร่างแล้ว');}catch(error){notify(error.message,true);}};
$('exportButton').onclick=async()=>{try{const resource=$('exportResource').value;if(!resource)throw new Error('นำเข้าทรัพยากรก่อนส่งออก');const blob=await api('export',{resource});const name=state.stats.resources.find(r=>r.id===resource).name.replace(/\.csv$/i,'');download(blob,name+'.translated.csv');notify('ส่งออกคำแปลตรวจรับแล้ว รายการอื่นใช้ข้อความเดิม');}catch(error){notify(error.message,true);}};
window.addEventListener('beforeunload',event=>{if(state.dirty){event.preventDefault();event.returnValue='';}});
window.addEventListener('keydown',async event=>{if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='k'){event.preventDefault();if(await selectPage('editor')!==false)$('search').focus();}if((event.ctrlKey||event.metaKey)&&event.key.toLowerCase()==='s'){event.preventDefault();if($('contextDialog').open)$('contextEdit').requestSubmit();else if(state.page==='editor'&&state.detail)saveTarget();}});
(async()=>{try{if(!token)throw new Error('เปิด GUI ผ่านคำสั่ง game-localizer-gui เพื่อสร้าง session ในเครื่อง');await refreshStats();await refreshList(false);}catch(error){$('connection').textContent='เปิดไม่สำเร็จ';notify(error.message,true);}})();
