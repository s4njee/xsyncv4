import { enter, leave, motionAllowed } from './vendor/holocss/runtime/index.js';
import { transitionView } from './vendor/holocss/view-transitions/index.js';

const $ = selector => document.querySelector(selector);
const root = document.documentElement;
let recordings;
let sessionName = 'transfer';
let frameIndex = 0;
let playing = false;
let playbackTimer;
let toastTimer;
const descriptions = {
  scanning:'This scanning line was emitted during the real checksum run. File discovery and checksum comparison can alternate as xsync walks the source tree.',
  transferring:'A real local transfer: 130 sample files, two workers, and a 1M bandwidth limit. File rows, bars, speeds, ETA, and totals are exactly as xsync printed them.',
  verifying:'Actual output from a separate --checksum run against matching files. The spinner and check count come directly from xsync; the final result reports the files checked.',
  complete:'The original completion line from the successful copy. All 130 destination files were compared with their sources using SHA-256 after this capture.',
  interrupted:'This transfer was interrupted with SIGINT. The recording preserves xsync’s actual diagnostics and exit code 20. -P enables retention of contiguous partial data.',
  error:'A real attempt to copy a missing source. xsync reports the missing path, summarizes the error, and returns exit code 23.'
};
const labels = {scanning:'Scanning',transferring:'Transferring',verifying:'Verifying',complete:'Complete',interrupted:'Interrupted',error:'Missing source'};
function timecode(ms){return `${String(Math.floor(ms/60000)).padStart(2,'0')}:${String(Math.floor(ms/1000)%60).padStart(2,'0')}.${String(ms%1000).padStart(3,'0')}`;}
function detectedState(text){
  if(sessionName==='error')return 'error';
  if(/code 20/.test(text))return 'interrupted';
  if(text.includes('✓'))return 'complete';
  if(text.includes('verifying'))return 'verifying';
  if(text.includes('scanning'))return 'scanning';
  return 'transferring';
}
function renderFrame(index){
  const session=recordings[sessionName];
  frameIndex=Math.max(0,Math.min(index,session.frames.length-1));
  const frame=session.frames[frameIndex],state=detectedState(frame.text);
  // No displayed line is reconstructed: only cursor control sequences were stripped at capture.
  $('#terminal-output').textContent=frame.text;
  $('#demo-command').textContent=session.command;
  $('#recording-time').textContent=timecode(frame.at_ms);
  $('#recording-duration').textContent=timecode(session.frames.at(-1).at_ms);
  $('#recording-frame').max=session.frames.length-1;
  $('#recording-frame').value=frameIndex;
  $('#recording-frame').setAttribute('aria-valuetext',`Frame ${frameIndex+1} of ${session.frames.length}, ${timecode(frame.at_ms)}`);
  $('#recording-position').textContent=`FRAME ${String(frameIndex+1).padStart(3,'0')} / ${session.frames.length} · CAPTURED OUTPUT`;
  $('#recording-exit').textContent=`Recording exit code: ${session.exit_code}`;
  $('#state-badge').textContent=labels[state];
  $('#state-description').textContent=sessionName==='verification'&&state==='complete'?'The original result of the checksum comparison: 15 files checked and already up to date. This run did not copy any file contents.':descriptions[state];
  $('.terminal').className=`terminal recorded-terminal is-${state}`;
  $('#download-transcript').href=session.transcript;
  $('#download-raw').href=session.raw;
  document.querySelectorAll('[data-state]').forEach(button=>button.setAttribute('aria-pressed',String(button.dataset.state===state)));
}
function stopPlayback(){
  clearTimeout(playbackTimer);playing=false;
  $('#play-demo').setAttribute('aria-pressed','false');
  $('#play-demo').innerHTML='<span aria-hidden="true">▷</span> Play recording';
}
function selectState(state){
  if(!recordings)return;
  stopPlayback();
  const names={scanning:'verification',transferring:'transfer',verifying:'verification',complete:'transfer',interrupted:'interrupted',error:'error'};
  sessionName=names[state];
  const frames=recordings[sessionName].frames;
  let index=frames.length-1;
  if(state==='scanning')index=frames.findIndex(frame=>frame.text.includes('scanning'));
  if(state==='verifying'){
    const matches=frames.map((frame,index)=>frame.text.includes('verifying')?index:-1).filter(index=>index>=0);
    index=matches.at(-1)??0;
  }
  if(state==='transferring'){
    const match=frames.findIndex(frame=>/(?:^|\n) [^\n]* 6[0-9]%\s+/.test(frame.text));
    index=match>=0?match:Math.floor(frames.length*.6);
  }
  const update=()=>{renderFrame(index);$('#status-announcement').textContent=`${labels[state]}. ${descriptions[state]}`;};
  if(motionAllowed(root))transitionView(update,{root});else update();
}
document.querySelectorAll('[data-state]').forEach(button=>button.addEventListener('click',()=>selectState(button.dataset.state)));
document.querySelectorAll('[data-example]').forEach(button=>button.addEventListener('click',()=>{
  selectState(button.dataset.example);
  $('#demo').scrollIntoView({behavior:motionAllowed(root)?'smooth':'instant'});
  $(`[data-state="${button.dataset.example}"]`).focus({preventScroll:true});
}));
$('#play-demo').addEventListener('click',()=>{
  if(!recordings)return;
  if(playing){stopPlayback();return;}
  playing=true;
  $('#play-demo').setAttribute('aria-pressed','true');
  $('#play-demo').innerHTML='<span aria-hidden="true">Ⅱ</span> Pause recording';
  renderFrame(0);
  const next=()=>{
    const frames=recordings[sessionName].frames;
    if(frameIndex>=frames.length-1){stopPlayback();$('#status-announcement').textContent='Recording finished.';return;}
    playbackTimer=setTimeout(()=>{renderFrame(frameIndex+1);next();},Math.max(16,frames[frameIndex+1].at_ms-frames[frameIndex].at_ms));
  };
  next();
});
$('#recording-frame').addEventListener('input',event=>{if(!recordings)return;stopPlayback();renderFrame(Number(event.target.value));});
document.addEventListener('visibilitychange',()=>{if(document.hidden)stopPlayback();});
$('#json-toggle').addEventListener('click',()=>{
  const open=$('#json-panel').hidden;
  $('#json-panel').hidden=!open;
  $('#json-toggle').setAttribute('aria-expanded',String(open));
  $('#json-toggle').innerHTML=open?'Hide captured JSON <span aria-hidden="true">↙</span>':'View captured JSON <span aria-hidden="true">↗</span>';
});
async function notify(message){
  clearTimeout(toastTimer);const toast=$('#toast');toast.textContent=message;toast.inert=false;
  await enter(toast);toastTimer=setTimeout(async()=>{toast.inert=true;await leave(toast);},2200);
}
document.querySelectorAll('[data-copy]').forEach(button=>button.addEventListener('click',async()=>{
  const target=document.getElementById(button.dataset.copy);
  try{await navigator.clipboard.writeText(target.textContent);await notify('Copied to clipboard.');}
  catch{const range=document.createRange();range.selectNodeContents(target);const selection=window.getSelection();selection.removeAllRanges();selection.addRange(range);await notify('Select and copy the highlighted text.');}
}));
document.querySelectorAll('[data-platform]').forEach(button=>button.addEventListener('click',()=>{
  document.querySelectorAll('[data-platform]').forEach(option=>option.setAttribute('aria-pressed',String(option===button)));
  $('#install-command').textContent=(button.dataset.platform==='mac'?'brew install cmake ninja zstd xxhash icu4c':'sudo apt install build-essential cmake ninja-build libzstd-dev libxxhash-dev libicu-dev')+'\ncmake -S . -B build -G Ninja\ncmake --build build\nbuild/xsync -aP src/ dst/';
  $('#install-label').textContent=button.dataset.platform==='mac'?'BUILD FROM THE XSYNC SOURCE DIRECTORY':'DEBIAN / UBUNTU — FROM THE SOURCE DIRECTORY';
}));
if('IntersectionObserver' in window&&motionAllowed(root)){
  const observer=new IntersectionObserver(entries=>entries.forEach(entry=>{if(entry.isIntersecting){entry.target.inert=false;enter(entry.target);observer.unobserve(entry.target);}}),{threshold:.15});
  document.querySelectorAll('.reveal').forEach((element,index)=>{
    if(element.getBoundingClientRect().top>window.innerHeight){element.dataset.hcssState='closed';element.inert=true;element.style.setProperty('--hcss-delay',`${index*70}ms`);observer.observe(element);}
  });
}
try{
  const response=await fetch('./recordings/sessions.json');
  if(!response.ok)throw new Error('Recording unavailable');
  recordings=await response.json();
  $('#recording-source').textContent=`Captured from xsync ${recordings.binary_version.match(/version ([\d.]+)/)?.[1]||''} · protocol 4 · local filesystem. Playback does not access your files.`;
  const events=recordings.json.events;
  const event=events.find(event=>event.type==='progress'&&event.bytes>0)||events[0];
  const jsonResponse=await fetch('./recordings/progress.ndjson');
  if(!jsonResponse.ok)throw new Error('JSON recording unavailable');
  const lines=(await jsonResponse.text()).split('\n').filter(Boolean);
  $('#json-output').textContent=lines[events.indexOf(event)];
  $('#json-command').textContent=recordings.json.command;
  $('#play-demo').disabled=false;
  sessionName='transfer';
  const initial=recordings.transfer.frames.findIndex(frame=>/(?:^|\n) [^\n]* 6[0-9]%\s+/.test(frame.text));
  renderFrame(initial>=0?initial:Math.floor(recordings.transfer.frames.length*.6));
}catch(error){
  $('#terminal-output').textContent='The captured session could not be loaded. Download the original transcript below to view the xsync output.';
  $('#state-badge').textContent='Recording unavailable';
  $('#status-announcement').textContent='Recording unavailable. The transcript download remains available.';
}
