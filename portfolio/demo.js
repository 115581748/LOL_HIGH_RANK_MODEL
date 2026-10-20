(() => {
  const $ = id => document.getElementById(id);
  const clock = value => `${String(Math.floor(value / 60)).padStart(2,'0')}:${String(Math.floor(value % 60)).padStart(2,'0')}`;
  let data, timer;
  const svgNode = (name, attrs, title) => { const node=document.createElementNS('http://www.w3.org/2000/svg',name); for(const [key,value] of Object.entries(attrs))node.setAttribute(key,value); if(title){const t=document.createElementNS(node.namespaceURI,'title');t.textContent=title;node.append(t)} return node };
  function seek(second){
    $('timeline').value=second;$('clock').textContent=clock(second);
    const frame=data.frames.filter(item=>item.timestamp<=second*1000).at(-1)||data.frames[0];
    $('sample').textContent=`Position sample: ${clock(frame.timestamp/1000)}`;$('map').replaceChildren();
    const pos=data.episode.position;if(pos)$('map').append(svgNode('circle',{cx:pos.x/30,cy:500-pos.y/30,r:28,fill:'none',stroke:'#e9bd59','stroke-width':3},data.episode.objectiveName));
    for(const player of frame.players){if(!Number.isFinite(player.x)||!Number.isFinite(player.y))continue;const info=data.players.find(item=>item.participantId===player.participantId);const x=player.x/30,y=500-player.y/30;$('map').append(svgNode('circle',{cx:x,cy:y,r:player.participantId===data.focusId?11:7,fill:info?.teamId===data.focusTeam?'#67ded7':'#ef7b70',stroke:player.participantId===data.focusId?'white':'#06131a','stroke-width':2},`${info?.champion} · sample ${clock(frame.timestamp/1000)}`));const label=svgNode('text',{x:x+10,y:y-9,fill:'white','font-size':12,stroke:'#06131a','stroke-width':3,'paint-order':'stroke'});label.textContent=info?.champion||player.participantId;$('map').append(label)}
  }
  function factButton(fact){const button=document.createElement('button');button.type='button';button.className='fact';const second=Math.floor((fact.timestamp??fact.sampleTimestamp??data.episode.eventSecond*1000)/1000);button.textContent=`${clock(second)} · ${fact.label}`;const source=document.createElement('small');source.textContent=`Source: ${fact.source||'derived observation'}`;button.append(source);button.addEventListener('click',()=>{stop();seek(second)});return button}
  function stop(){clearInterval(timer);timer=null;$('play').textContent='Play'}
  fetch('demo.json').then(response=>{if(!response.ok)throw Error('Frozen demo data unavailable');return response.json()}).then(payload=>{
    data=payload;const number=value=>Number(value).toLocaleString(undefined,{maximumFractionDigits:1});
    $('sourceRows').textContent=data.sourceRows?Number(data.sourceRows).toLocaleString():'See methodology';
    $('matchContext').textContent=`${data.match.champion} vs ${data.match.opponentChampion} · ${data.match.position} · patch ${data.match.patch} · ${data.match.win?'Win':'Loss'} · objective at ${clock(data.episode.eventSecond)}`;
    const primary=data.episode.hypotheses.find(item=>item.id===data.episode.primaryHypothesisId);$('claim').textContent=primary?.title||'Review the observed objective window';
    const evidence=data.episode.facts.filter(fact=>primary?.evidenceIds?.includes(fact.id));for(const fact of evidence.length?evidence:data.episode.facts.slice(0,3))$('evidence').append(factButton(fact));for(const fact of data.episode.facts)$('allFacts').append(factButton(fact));
    for(const hypothesis of data.episode.hypotheses.filter(item=>item!==primary)){const p=document.createElement('p');p.textContent=hypothesis.title;$('alternatives').append(p)}
    for(const metric of data.metrics||[]){const card=document.createElement('article');card.className='panel';const heading=document.createElement('h3');heading.textContent=metric.label;const values=document.createElement('p');values.textContent=`This match: ${number(metric.value)} / Reference median: ${number(metric.baseline)}`;const delta=document.createElement('p');delta.textContent=`Gap: ${metric.gap>0?'+':''}${number(metric.gap)} · n=${metric.n} · ${metric.lowerIsBetter?'Lower':'Higher'} is better`;const status=document.createElement('small');status.textContent=metric.weak?'Beyond the weak-quartile boundary — review this match.':'Not beyond the weak-quartile boundary.';card.append(heading,values,delta,status);$('benchmarks').append(card)}
    $('timeline').max=Math.floor(data.frames.at(-1).timestamp/1000);$('timeline').addEventListener('input',event=>{stop();seek(Number(event.target.value))});$('play').disabled=false;$('play').addEventListener('click',()=>{if(timer){stop();return}$('play').textContent='Pause';timer=setInterval(()=>{const next=Number($('timeline').value)+2;if(next>Number($('timeline').max)){stop();return}seek(next)},1000)});seek(data.episode.windowStartSecond);
  }).catch(error=>{$('error').textContent=`${error.message}. Serve the project over HTTP and reload.`;$('claim').textContent='Demo unavailable'});
})();
