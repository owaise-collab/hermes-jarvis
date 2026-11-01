const token = document.querySelector('meta[name="jarvis-token"]').content;
const $ = id => document.getElementById(id);
let selected = new Set(), resultText = '', audioUrl, recording, busy = false, modelReady = false, transcribing = false, panelStopped = false;
function core(state, caption) {
  const labels = {idle:'STANDING BY',thinking:'PROCESSING',listening:'LISTENING',transcribing:'TRANSCRIBING',speaking:'VOICE OUTPUT',error:'ATTENTION REQUIRED',offline:'MODEL OFFLINE'};
  const captions = {idle:'Ready for your instructions.',thinking:'Processing your request on this machine.',listening:'Microphone active. Click again to stop.',transcribing:'Converting your voice to text locally.',speaking:'Local voice output active.',error:'Check the message above to continue.',offline:'Start the local model server to connect.'};
  document.body.dataset.core = state;
  $('core-state').textContent = labels[state];
  $('core-caption').textContent = caption || captions[state];
  $('core-voice-label').textContent = state === 'listening' ? 'STOP RECORDING' : 'INITIATE VOICE';
  $('core-voice').setAttribute('aria-label', state === 'listening' ? 'Stop voice dictation' : 'Start voice dictation');
}
function restCore() { core(recording ? 'listening' : transcribing ? 'transcribing' : !$('audio').paused ? 'speaking' : busy ? 'thinking' : modelReady ? 'idle' : 'offline'); }
function workflowSelection() {
  document.querySelectorAll('[data-workflow]').forEach(button => {
    const active = button.dataset.workflow === $('workflow').value;
    button.classList.toggle('active', active);
    button.setAttribute('aria-pressed', String(active));
  });
}
function notice(text) { $('notice').textContent = text; }
async function api(path, body, raw = false) {
  const response = await fetch(path, {method: body === undefined ? 'GET' : 'POST', headers: {'X-Jarvis-Token': token, ...(body === undefined ? {} : {'Content-Type': raw ? 'audio/wav' : 'application/json'})}, body: body === undefined ? undefined : raw ? body : JSON.stringify(body)});
  if (!response.ok) { const error = await response.json(); throw Error(error.error || 'Request failed.'); }
  return response;
}
async function json(path, body) { return (await api(path, body)).json(); }
function view(name) { document.querySelectorAll('.view').forEach(el => el.hidden = el.id !== name); document.querySelectorAll('nav button').forEach(el => { const active = el.dataset.view === name; el.classList.toggle('selected', active); el.setAttribute('aria-current', active ? 'page' : 'false'); }); }
function showResult(text, meta = '') { resultText = text; $('result').textContent = text; $('result-meta').textContent = meta; }
function contextCount() { $('context-count').textContent = `${selected.size} notes selected`; }
async function status() {
  if (panelStopped) return;
  try {
    const data = await json('/api/status');
    modelReady = data.model.ready;
    $('health').textContent = modelReady ? '● MODEL LINK ONLINE' : 'MODEL LINK OFFLINE';
    $('health').classList.toggle('error', !data.model.ready);
    $('model-name').textContent = data.model.model; $('endpoint').textContent = data.model.endpoint;
    $('vault-path').textContent = data.vault;
    $('stt-state').textContent = data.speech.stt ? 'Whisper installed · cached model required' : 'Whisper not available in this runtime';
    $('tts-state').textContent = data.speech.tts ? 'Piper · English · installed' : 'Piper voice or runtime missing';
    $('hud-model-state').textContent = modelReady ? 'CONNECTED' : 'OFFLINE';
    $('hud-model-name').textContent = data.model.model;
    $('hud-stt').textContent = data.speech.stt ? 'WHISPER / INSTALLED' : 'NOT INSTALLED';
    $('hud-tts').textContent = data.speech.tts ? 'PIPER / INSTALLED' : 'NOT INSTALLED';
    document.querySelector('.link-indicator').textContent = modelReady ? '●' : '○';
    if (!busy && !recording && !transcribing && $('audio').paused) restCore();
    return data;
  } catch (error) { modelReady = false; $('health').textContent = 'PANEL DISCONNECTED'; $('health').classList.add('error'); core('offline'); notice(error.message); }
}
async function loadNotes() {
  const notes = await json('/api/notes?q=' + encodeURIComponent($('search').value));
  if (!$('search').value.trim()) $('vault-count').textContent = String(notes.length);
  $('notes').replaceChildren();
  if (!notes.length) { $('notes').textContent = 'No matching notes. Capture your first idea here.'; return; }
  for (const note of notes) {
    const row = document.createElement('div'); row.className = 'note';
    const check = document.createElement('input'); check.type = 'checkbox'; check.checked = selected.has(note.path); check.setAttribute('aria-label', 'Use ' + note.title + ' as context');
    check.onchange = () => { if (check.checked && selected.size >= 5) { check.checked = false; notice('Select at most five notes.'); return; } check.checked ? selected.add(note.path) : selected.delete(note.path); contextCount(); };
    const button = document.createElement('button'); button.textContent = note.title;
    const small = document.createElement('small'); small.textContent = note.path; button.append(small);
    button.onclick = async () => { try { const data = await json('/api/note?path=' + encodeURIComponent(note.path)); showResult(data.content, note.path); view('workspace'); } catch (error) { notice(error.message); } };
    row.append(check, button); $('notes').append(row);
  }
}
async function run() {
  if (busy) return;
  const prompt = $('prompt').value.trim(); if (!prompt) return notice('Enter your brief first.');
  busy = true; $('run').disabled = true; $('record').disabled = true; $('core-voice').disabled = true; $('job-status').textContent = 'WORKING'; restCore();
  let failed = false;
  try {
    const job = await json('/api/jobs', {kind: $('workflow').value, prompt, notes: [...selected]});
    notice('Working locally. One model job at a time; the first request may take several minutes.');
    while (true) {
      await new Promise(resolve => setTimeout(resolve, 1800));
      const state = await json('/api/jobs/' + job.id);
      if (state.status === 'completed') { showResult(state.answer, 'DRAFT · saved to ' + state.note); $('job-status').textContent = 'SAVED'; notice('Draft saved locally. Review its accuracy and sources.'); await loadNotes(); break; }
      if (state.status === 'failed') throw Error(state.error);
    }
  } catch (error) { failed = true; $('job-status').textContent = 'FAILED'; notice(error.message); }
  finally { busy = false; $('run').disabled = false; $('record').disabled = false; $('core-voice').disabled = false; failed ? core('error') : restCore(); }
}
function wav(samples, sourceRate) {
  const count = Math.floor(samples.length * 16000 / sourceRate), bytes = new ArrayBuffer(44 + count * 2), out = new DataView(bytes);
  const str = (offset, text) => [...text].forEach((c, i) => out.setUint8(offset + i, c.charCodeAt(0)));
  str(0,'RIFF'); out.setUint32(4,36+count*2,true); str(8,'WAVE'); str(12,'fmt '); out.setUint32(16,16,true); out.setUint16(20,1,true); out.setUint16(22,1,true); out.setUint32(24,16000,true); out.setUint32(28,32000,true); out.setUint16(32,2,true); out.setUint16(34,16,true); str(36,'data'); out.setUint32(40,count*2,true);
  for (let i=0;i<count;i++) { const start=Math.floor(i*sourceRate/16000), end=Math.max(start+1,Math.floor((i+1)*sourceRate/16000)); let value=0; for(let j=start;j<end;j++) value+=samples[j]||0; value=Math.max(-1,Math.min(1,value/(end-start))); out.setInt16(44+i*2,value<0?value*32768:value*32767,true); }
  return new Blob([bytes],{type:'audio/wav'});
}
async function dictate() {
  if (recording) return recording.stop();
  if (busy || transcribing) return;
  $('audio').pause();
  let stream, context;
  try {
    stream = await navigator.mediaDevices.getUserMedia({audio:true}); context = new AudioContext(); await context.resume();
    const source = context.createMediaStreamSource(stream), processor = context.createScriptProcessor(4096,1,1), chunks=[];
    processor.onaudioprocess = event => {
      const samples = new Float32Array(event.inputBuffer.getChannelData(0));
      chunks.push(samples);
      const rms = Math.sqrt(samples.reduce((sum, value) => sum + value * value, 0) / samples.length);
      $('waveform').style.setProperty('--voice-level', String(Math.min(3, 1 + rms * 35)));
    };
    source.connect(processor); processor.connect(context.destination);
    let stopped=false, timer;
    recording = {stop: async () => {
      if(stopped)return; stopped=true; clearTimeout(timer); processor.disconnect(); source.disconnect(); stream.getTracks().forEach(track=>track.stop());
      const rate=context.sampleRate; await context.close(); recording=null; transcribing=true; $('record').textContent='Dictate'; $('record').disabled=true; $('core-voice').disabled=true; core('transcribing'); notice('Transcribing on this PC…');
      try { const data=new Float32Array(chunks.reduce((sum,c)=>sum+c.length,0)); let offset=0; for(const chunk of chunks){data.set(chunk,offset);offset+=chunk.length;} const response=await api('/api/transcribe',wav(data,rate),true); const transcript=await response.json(); $('prompt').value=($('prompt').value+' '+transcript.text).trim(); notice('Transcript added. Review it before creating a draft.'); }
      catch(error){notice(error.message);}finally{transcribing=false;$('record').disabled=false;$('core-voice').disabled=false;$('waveform').style.removeProperty('--voice-level');restCore();}
    }};
    timer=setTimeout(()=>recording?.stop(),59000); $('record').textContent='Stop recording'; core('listening'); notice('Recording · click Stop when finished. Audio is processed locally and is not saved by this panel.');
  } catch(error){stream?.getTracks().forEach(track=>track.stop()); if(context)await context.close(); recording=null; core('error','Microphone unavailable. You can still type a command.'); notice('Microphone unavailable: '+error.message);}
}
document.querySelectorAll('nav button').forEach(button => button.onclick = () => view(button.dataset.view));
document.querySelectorAll('[data-workflow]').forEach(button => button.onclick = () => { $('workflow').value = button.dataset.workflow; workflowSelection(); $('prompt').focus(); });
$('workflow').onchange = workflowSelection;
$('prompt').onkeydown = event => { if ((event.ctrlKey || event.metaKey) && event.key === 'Enter') { event.preventDefault(); run(); } };
$('core-voice').onclick = dictate;
let reduceMotion = window.matchMedia('(prefers-reduced-motion: reduce)').matches;
function motionPreference() { document.body.classList.toggle('reduced-motion',reduceMotion); document.body.classList.toggle('motion-enabled',!reduceMotion); $('motion-toggle').setAttribute('aria-pressed',String(reduceMotion)); $('motion-toggle').textContent=reduceMotion?'ENABLE MOTION':'REDUCE MOTION'; }
$('motion-toggle').onclick = () => { reduceMotion = !reduceMotion; motionPreference(); };
motionPreference();
$('audio').onplaying = () => core('speaking');
$('audio').onpause = restCore;
$('audio').onended = restCore;
$('audio').onerror = () => core('error','Audio playback unavailable. Your text result is saved.');
function updateClock() { $('local-clock').textContent = new Intl.DateTimeFormat(undefined,{hour:'2-digit',minute:'2-digit',second:'2-digit',hour12:false}).format(new Date()); }
updateClock(); setInterval(updateClock,1000);
$('choose-notes').onclick = () => view('vault'); $('use-notes').onclick = () => view('workspace');
$('run').onclick = run; $('record').onclick = dictate; $('clear').onclick = () => { $('prompt').value=''; selected.clear(); contextCount(); loadNotes().catch(error=>notice(error.message)); };
$('open-hermes').onclick = async () => {try {const data=await json('/api/hermes',{});notice(data.message);}catch(error){notice(error.message);}};
$('shutdown').onclick = async () => {if(busy || recording || transcribing)return notice('Finish the current task or recording before stopping the panel.');try {const data=await json('/api/shutdown',{});panelStopped=true;notice(data.message);$('run').disabled=true;$('record').disabled=true;$('core-voice').disabled=true;$('health').textContent='PANEL STOPPED';$('audio').pause();core('offline','Panel stopped. Restart Jarvis to reconnect.');}catch(error){notice(error.message);}};
$('refresh').onclick = () => loadNotes().catch(error=>notice(error.message));
let searchTimer; $('search').oninput = () => {clearTimeout(searchTimer);searchTimer=setTimeout(()=>loadNotes().catch(error=>notice(error.message)),250);};
$('save-note').onclick = async () => {try {const data=await json('/api/notes',{area:$('note-area').value,title:$('note-title').value,content:$('note-content').value}); $('note-title').value='';$('note-content').value='';notice('Saved: '+data.path);await loadNotes();}catch(error){notice(error.message);}};
$('brief').onclick = async () => {try {const data=await json('/api/brief');showResult(data.content,'LOCAL INVENTORY · no model call');view('workspace');}catch(error){notice(error.message);}};
$('copy').onclick = async () => {try {await navigator.clipboard.writeText(resultText);notice('Copied.');}catch(error){notice(error.message);}};
$('print').onclick = () => {if(!resultText)return notice('Create or open a result first.');window.print();};
$('speak').onclick = async () => {if(!resultText)return notice('Create or open a result first.');$('speak').disabled=true;try {const response=await api('/api/speak',{text:resultText.slice(0,3000)});if(audioUrl)URL.revokeObjectURL(audioUrl);audioUrl=URL.createObjectURL(await response.blob());$('audio').src=audioUrl;$('audio').hidden=false;await $('audio').play();}catch(error){notice(error.message);}finally{$('speak').disabled=false;}};
window.addEventListener('beforeunload',()=>{if(recording)recording.stop();});
workflowSelection(); status(); loadNotes().catch(error=>notice(error.message));
setInterval(() => { if (!document.hidden) status(); },20000);
