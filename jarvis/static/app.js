const token = document.querySelector('meta[name="jarvis-token"]').content;
const $ = id => document.getElementById(id);
let selected = new Set(), resultText = '', audioUrl, recording, busy = false;
function notice(text) { $('notice').textContent = text; }
async function api(path, body, raw = false) {
  const response = await fetch(path, {method: body === undefined ? 'GET' : 'POST', headers: {'X-Jarvis-Token': token, ...(body === undefined ? {} : {'Content-Type': raw ? 'audio/wav' : 'application/json'})}, body: body === undefined ? undefined : raw ? body : JSON.stringify(body)});
  if (!response.ok) { const error = await response.json(); throw Error(error.error || 'Request failed.'); }
  return response;
}
async function json(path, body) { return (await api(path, body)).json(); }
function view(name) { document.querySelectorAll('.view').forEach(el => el.hidden = el.id !== name); document.querySelectorAll('nav button').forEach(el => el.classList.toggle('selected', el.dataset.view === name)); }
function showResult(text, meta = '') { resultText = text; $('result').textContent = text; $('result-meta').textContent = meta; }
function contextCount() { $('context-count').textContent = `${selected.size} notes selected`; }
async function status() {
  try {
    const data = await json('/api/status');
    $('health').textContent = data.model.ready ? '● Local model ready' : 'Local model unavailable';
    $('health').classList.toggle('error', !data.model.ready);
    $('model-name').textContent = data.model.model; $('endpoint').textContent = data.model.endpoint;
    $('vault-path').textContent = data.vault;
    $('stt-state').textContent = data.speech.stt ? 'Whisper installed · cached model required' : 'Whisper not available in this runtime';
    $('tts-state').textContent = data.speech.tts ? 'Piper · English · installed' : 'Piper voice or runtime missing';
    return data;
  } catch (error) { notice(error.message); }
}
async function loadNotes() {
  const notes = await json('/api/notes?q=' + encodeURIComponent($('search').value));
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
  busy = true; $('run').disabled = true; $('job-status').textContent = 'WORKING';
  try {
    const job = await json('/api/jobs', {kind: $('workflow').value, prompt, notes: [...selected]});
    notice('Working locally. One model job at a time; the first request may take several minutes.');
    while (true) {
      await new Promise(resolve => setTimeout(resolve, 1800));
      const state = await json('/api/jobs/' + job.id);
      if (state.status === 'completed') { showResult(state.answer, 'DRAFT · saved to ' + state.note); $('job-status').textContent = 'SAVED'; notice('Draft saved locally. Review its accuracy and sources.'); await loadNotes(); break; }
      if (state.status === 'failed') throw Error(state.error);
    }
  } catch (error) { $('job-status').textContent = 'FAILED'; notice(error.message); }
  finally { busy = false; $('run').disabled = false; }
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
  let stream, context;
  try {
    stream = await navigator.mediaDevices.getUserMedia({audio:true}); context = new AudioContext(); await context.resume();
    const source = context.createMediaStreamSource(stream), processor = context.createScriptProcessor(4096,1,1), chunks=[];
    processor.onaudioprocess = event => chunks.push(new Float32Array(event.inputBuffer.getChannelData(0)));
    source.connect(processor); processor.connect(context.destination);
    let stopped=false, timer;
    recording = {stop: async () => {
      if(stopped)return; stopped=true; clearTimeout(timer); processor.disconnect(); source.disconnect(); stream.getTracks().forEach(track=>track.stop());
      const rate=context.sampleRate; await context.close(); recording=null; $('record').textContent='Dictate'; $('record').disabled=true; notice('Transcribing on this PC…');
      try { const data=new Float32Array(chunks.reduce((sum,c)=>sum+c.length,0)); let offset=0; for(const chunk of chunks){data.set(chunk,offset);offset+=chunk.length;} const response=await api('/api/transcribe',wav(data,rate),true); const transcript=await response.json(); $('prompt').value=($('prompt').value+' '+transcript.text).trim(); notice('Transcript added. Review it before creating a draft.'); }
      catch(error){notice(error.message);}finally{$('record').disabled=false;}
    }};
    timer=setTimeout(()=>recording?.stop(),59000); $('record').textContent='Stop recording'; notice('Recording · click Stop when finished. Audio is processed locally and is not saved by this panel.');
  } catch(error){stream?.getTracks().forEach(track=>track.stop()); if(context)await context.close(); recording=null; notice('Microphone unavailable: '+error.message);}
}
document.querySelectorAll('nav button').forEach(button => button.onclick = () => view(button.dataset.view));
$('choose-notes').onclick = () => view('vault'); $('use-notes').onclick = () => view('workspace');
$('run').onclick = run; $('record').onclick = dictate; $('clear').onclick = () => { $('prompt').value=''; selected.clear(); contextCount(); loadNotes().catch(error=>notice(error.message)); };
$('open-hermes').onclick = async () => {try {const data=await json('/api/hermes',{});notice(data.message);}catch(error){notice(error.message);}};
$('shutdown').onclick = async () => {if(busy)return notice('Wait for the current model job to finish before stopping the panel.');try {const data=await json('/api/shutdown',{});notice(data.message);$('run').disabled=true;$('health').textContent='Panel stopped';}catch(error){notice(error.message);}};
$('refresh').onclick = () => loadNotes().catch(error=>notice(error.message));
let searchTimer; $('search').oninput = () => {clearTimeout(searchTimer);searchTimer=setTimeout(()=>loadNotes().catch(error=>notice(error.message)),250);};
$('save-note').onclick = async () => {try {const data=await json('/api/notes',{area:$('note-area').value,title:$('note-title').value,content:$('note-content').value}); $('note-title').value='';$('note-content').value='';notice('Saved: '+data.path);await loadNotes();}catch(error){notice(error.message);}};
$('brief').onclick = async () => {try {const data=await json('/api/brief');showResult(data.content,'LOCAL INVENTORY · no model call');view('workspace');}catch(error){notice(error.message);}};
$('copy').onclick = async () => {try {await navigator.clipboard.writeText(resultText);notice('Copied.');}catch(error){notice(error.message);}};
$('print').onclick = () => {if(!resultText)return notice('Create or open a result first.');window.print();};
$('speak').onclick = async () => {if(!resultText)return notice('Create or open a result first.');$('speak').disabled=true;try {const response=await api('/api/speak',{text:resultText.slice(0,3000)});if(audioUrl)URL.revokeObjectURL(audioUrl);audioUrl=URL.createObjectURL(await response.blob());$('audio').src=audioUrl;$('audio').hidden=false;await $('audio').play();}catch(error){notice(error.message);}finally{$('speak').disabled=false;}};
window.addEventListener('beforeunload',()=>{if(recording)recording.stop();});
status(); loadNotes().catch(error=>notice(error.message));
