'use strict';
/**
 * set_compare.cjs — per-set stat comparison (our parser vs slippi-js)
 * Groups replays by match_id, averages stats across games in each set,
 * and prints a side-by-side table for every set found.
 *
 * Run: node scripts/set_compare.cjs
 */
process.env.NODE_ENV = 'production';

const fs   = require('fs');
const path = require('path');
const { SlippiGame } = require('@slippi/slippi-js');

const CONNECT_CODE = 'JOEY#870';
const REPLAY_DIR   = 'C:/Slippi Replays/Recent';

// ── Action-state helpers ───────────────────────────────────────────────────
function isInControl(s) {
  return (s >= 14 && s <= 24) || (s >= 39 && s <= 41) || (s > 44 && s <= 64) || s === 212;
}
function isInStun(s) {
  return (s >= 75 && s <= 91) || s === 38 || s === 185 || s === 193
      || (s >= 223 && s <= 232)
      || (((s >= 266 && s <= 304) || (s >= 327 && s <= 338)) && s !== 293);
}
function countSetBits(x) { let b=x,c=0; while(b){b&=b-1;c++;} return c; }

// ── UBJSON parser ──────────────────────────────────────────────────────────
function parseUbjson(buf, startPos) {
  const data=new Uint8Array(buf), view=new DataView(buf);
  let pos=startPos;
  function readLen() {
    const m=String.fromCharCode(data[pos++]);
    if(m==='i'){const v=view.getInt8(pos);pos+=1;return v;}
    if(m==='U'){return data[pos++];}
    if(m==='I'){const v=view.getInt16(pos,false);pos+=2;return v;}
    if(m==='l'){const v=view.getInt32(pos,false);pos+=4;return v;}
    throw new Error('bad len:'+m);
  }
  function parse() {
    const m=String.fromCharCode(data[pos++]);
    if(m==='{'){const o={};while(String.fromCharCode(data[pos])!=='}'){const kl=readLen(),k=Buffer.from(buf,pos,kl).toString('utf8');pos+=kl;o[k]=parse();}pos++;return o;}
    if(m==='['){const a=[];while(String.fromCharCode(data[pos])!==']')a.push(parse());pos++;return a;}
    if(m==='S'){const l=readLen(),s=Buffer.from(buf,pos,l).toString('utf8');pos+=l;return s;}
    if(m==='i'){const v=view.getInt8(pos);pos+=1;return v;}
    if(m==='U'){return data[pos++];}
    if(m==='I'){const v=view.getInt16(pos,false);pos+=2;return v;}
    if(m==='l'){const v=view.getInt32(pos,false);pos+=4;return v;}
    if(m==='d'){const v=view.getFloat32(pos,false);pos+=4;return v;}
    if(m==='D'){const v=view.getFloat64(pos,false);pos+=8;return v;}
    if(m==='T')return true;if(m==='F')return false;if(m==='Z')return null;
    throw new Error('unknown:'+m);
  }
  return[parse(),pos];
}

// ── Our parser ─────────────────────────────────────────────────────────────
function ourStats(filepath, connectCode) {
  let nodeBuf;
  try{nodeBuf=fs.readFileSync(filepath.replace(/\//g,'\\'));}catch{return null;}
  const buf=nodeBuf.buffer.slice(nodeBuf.byteOffset,nodeBuf.byteOffset+nodeBuf.byteLength);
  const data=new Uint8Array(buf), view=new DataView(buf);

  let matchId='', hasMode=false;
  for(let i=0;i<data.length-4;i++){
    if(data[i]===109&&data[i+1]===111&&data[i+2]===100&&data[i+3]===101&&data[i+4]===46){
      hasMode=true;
      let end=i;while(end<i+60&&end<data.length&&data[end]!==0)end++;
      matchId=Buffer.from(buf,i,end-i).toString('utf8');
      break;
    }
  }
  if(!hasMode) return null;

  const evStart=15, rawLen=view.getInt32(11,false), evEnd=evStart+rawLen;
  if(data[evStart]!==0x35) return null;
  const epSize=data[evStart+1], payloadSizes={};
  for(let i=0;i<Math.floor((epSize-1)/3);i++){const off=evStart+2+i*3;payloadSizes[data[off]]=view.getUint16(off+1,false);}

  let pos=evStart+1+epSize, gameEndMethod=-1;
  const finalStocks={}, frameData={}, lCancelSucc={}, lCancelAtt={};
  const prevActionState={}, maxPreFrame={}, prevButtons={}, inputCounts={};
  const stockDmg={}, prevStocks2={}, prevPcts={}, totalDmg={};

  while(pos<evEnd){
    const cmd=data[pos], size=payloadSizes[cmd];
    if(size===undefined){pos++;continue;}
    const ps=pos+1;
    if(cmd===0x38&&size>=33){
      const port=data[ps+4],isF=data[ps+5];
      if(!isF&&port<=3){
        const fn=view.getInt32(ps,false), state=view.getUint16(ps+7,false);
        const stocks=data[ps+32], percent=view.getFloat32(ps+21,false);
        const lastHitBy=data[ps+31];
        finalStocks[port]=stocks;
        if(!frameData[port])frameData[port]=[];
        frameData[port].push({frame:fn,state,percent,stocks,lastHitBy});
        if(size>=51&&state>=65&&state<=74&&state!==(prevActionState[port]??-1)){
          const lc=data[ps+50];
          if(lc===1){lCancelSucc[port]=(lCancelSucc[port]||0)+1;lCancelAtt[port]=(lCancelAtt[port]||0)+1;}
          else if(lc===2){lCancelAtt[port]=(lCancelAtt[port]||0)+1;}
        }
        prevActionState[port]=state;
        if(prevStocks2[port]!==undefined&&stocks<prevStocks2[port]){
          totalDmg[port]=(totalDmg[port]||0)+(stockDmg[port]||0);
          stockDmg[port]=0;
        } else { stockDmg[port]=percent; }
        prevStocks2[port]=stocks; prevPcts[port]=percent;
      }
    } else if(cmd===0x37&&size>=50){
      const port=data[ps+4],isF=data[ps+5];
      if(!isF&&port<=3){
        const pf=view.getInt32(ps,false);
        if(pf>(maxPreFrame[port]??-Infinity)){
          maxPreFrame[port]=pf;
          const btns=view.getUint16(ps+48,false);
          if(prevButtons[port]!==undefined)inputCounts[port]=(inputCounts[port]||0)+countSetBits((~prevButtons[port]&btns)&0xfff);
          prevButtons[port]=btns;
        }
      }
    } else if(cmd===0x39&&size>=2){gameEndMethod=data[ps];}
    pos+=1+size;
  }
  if(gameEndMethod!==2) return null;

  for(const port of Object.keys(stockDmg).map(Number))
    totalDmg[port]=(totalDmg[port]||0)+(stockDmg[port]||0);

  let meta={};
  try{[meta]=parseUbjson(buf.slice(15+view.getInt32(11,false)+10,buf.byteLength-1),0);}catch{}
  const players={};
  if(meta&&meta.players){
    for(const[portStr,pd]of Object.entries(meta.players)){
      const port=parseInt(portStr,10),chars=pd.characters;
      let charId=null;
      if(chars&&Object.keys(chars).length>0){const best=Object.entries(chars).reduce((a,b)=>b[1]>a[1]?b:a);charId=parseInt(best[0],10);}
      players[port]={connectCode:pd.names?.code??'',charId};
    }
  }

  const cc=connectCode.toUpperCase();
  const ports=Object.keys(players).map(Number);
  const playerPort=ports.find(p=>players[p].connectCode.toUpperCase()===cc);
  if(playerPort===undefined) return null;
  const oppPort=ports.find(p=>p!==playerPort);
  if(oppPort===undefined) return null;
  if((finalStocks[playerPort]??-1)===(finalStocks[oppPort]??-1)) return null;

  for(const port of Object.keys(frameData).map(Number)){
    const seen=new Map();
    for(const snap of frameData[port])seen.set(snap.frame,snap);
    frameData[port]=Array.from(seen.values()).sort((a,b)=>a.frame-b.frame);
  }

  const playerFrames=frameData[playerPort]??[];
  const oppMap=new Map();
  for(const snap of frameData[oppPort]??[])oppMap.set(snap.frame,snap);

  const RESET=45;
  let pConvActive=false,pResetCtr=0,pConvCount=0,pNW=0;
  let oConvActive=false,oResetCtr=0,oNW=0;
  let openingConvCount=0,convHitCount=0,convLastOppPct=-1;
  let prevOppStocks=-1,prevPlayerStocks=-1,prevOppStun=false;
  const attrKillPcts=[];

  for(const snap of playerFrames){
    const opp=oppMap.get(snap.frame);
    if(!opp)continue;
    const oppStun=isInStun(opp.state),oppCtrl=isInControl(opp.state);
    const playerStun=isInStun(snap.state);

    if(prevOppStocks>=0&&opp.stocks<prevOppStocks){
      if(opp.lastHitBy===playerPort)attrKillPcts.push(opp.percent);
      if(pConvActive){
        if(convHitCount>=2)openingConvCount++;
        pConvActive=false;pResetCtr=0;convHitCount=0;convLastOppPct=-1;
      }
    }
    if(prevPlayerStocks>=0&&snap.stocks<prevPlayerStocks&&oConvActive){oConvActive=false;oResetCtr=0;}
    prevOppStocks=opp.stocks;prevPlayerStocks=snap.stocks;

    if(oppStun){
      if(!pConvActive){pConvActive=true;pConvCount++;convHitCount=1;convLastOppPct=opp.percent;if(!oConvActive)pNW++;}
      else if(!prevOppStun){convHitCount++;convLastOppPct=opp.percent;}
      else if(opp.percent>convLastOppPct+0.5){convHitCount++;convLastOppPct=opp.percent;}
      pResetCtr=0;
    } else if(pConvActive){
      if(oppCtrl||pResetCtr>0){pResetCtr++;if(pResetCtr>RESET){if(convHitCount>=2)openingConvCount++;pConvActive=false;pResetCtr=0;convHitCount=0;convLastOppPct=-1;}}
    }
    if(playerStun){if(!oConvActive){oConvActive=true;if(!pConvActive)oNW++;}oResetCtr=0;}
    else if(oConvActive){if(isInControl(snap.state)||oResetCtr>0){oResetCtr++;if(oResetCtr>RESET){oConvActive=false;oResetCtr=0;}}}
    prevOppStun=oppStun;
  }
  if(pConvActive&&convHitCount>=2)openingConvCount++;

  const kills=attrKillPcts.length;
  const nwTotal=pNW+oNW;
  const durationFrames=playerFrames.reduce((mx,s)=>s.frame>mx?s.frame:mx,0);
  const durationMins=durationFrames/3600;
  const ps2=finalStocks[playerPort]??-1, os=finalStocks[oppPort]??-1;
  const result=ps2>os?'win':'loss';

  return {
    matchId,
    oppCode: players[oppPort]?.connectCode ?? '?',
    result,
    opk:  kills>0?pConvCount/kills:null,
    dpo:  pConvCount>0?(totalDmg[oppPort]??0)/pConvCount:null,
    nwr:  nwTotal>0?pNW/nwTotal:null,
    ocr:  pConvCount>0?openingConvCount/pConvCount:null,
    lc:   (lCancelAtt[playerPort]||0)>0?(lCancelSucc[playerPort]||0)/(lCancelAtt[playerPort]||0):null,
    ipm:  durationMins>0?(inputCounts[playerPort]||0)/durationMins:null,
    kill: kills>0?attrKillPcts.reduce((a,b)=>a+b,0)/kills:null,
  };
}

// ── slippi-js stats ────────────────────────────────────────────────────────
function slippiStats(filepath, connectCode) {
  let game;
  try{game=new SlippiGame(filepath.replace(/\//g,'\\'));}catch{return null;}
  const settings=game.getSettings();
  if(!settings)return null;
  const cc=connectCode.toUpperCase();
  const playerIdx=settings.players.findIndex(p=>p&&p.connectCode&&p.connectCode.toUpperCase()===cc);
  if(playerIdx===-1)return null;
  const stats=game.getStats();
  const overall=stats&&stats.overall?stats.overall:[];
  const actions=stats&&stats.actionCounts?stats.actionCounts:[];
  const pO=overall.find(o=>o.playerIndex===playerIdx);
  const pA=actions.find(a=>a.playerIndex===playerIdx);
  if(!pO)return null;
  const lcSucc=pA&&pA.lCancelCount?pA.lCancelCount.success:0;
  const lcFail=pA&&pA.lCancelCount?pA.lCancelCount.fail:0;
  const lcTot=lcSucc+lcFail;
  const convs=stats&&stats.conversions?stats.conversions:[];
  const kills=convs.filter(c=>c.didKill&&c.lastHitBy===playerIdx);
  const kPcts=kills.map(c=>c.endPercent).filter(p=>p!=null&&p>0);
  // Read match_id from settings for grouping
  const matchId=settings.matchInfo?.matchId??'';
  return {
    matchId,
    opk:  pO.openingsPerKill?.ratio??null,
    dpo:  pO.damagePerOpening?.ratio??null,
    nwr:  pO.neutralWinRatio?.ratio??null,
    ocr:  pO.successfulConversions?.ratio??null,
    lc:   lcTot>0?lcSucc/lcTot:null,
    ipm:  pO.digitalInputsPerMinute?.ratio??null,
    kill: kPcts.length>0?kPcts.reduce((a,b)=>a+b,0)/kPcts.length:null,
  };
}

// ── Average a list of per-game stat objects ────────────────────────────────
function avgStats(arr, keys) {
  const out={};
  for(const k of keys){
    const vals=arr.map(g=>g[k]).filter(v=>v!=null&&isFinite(v));
    out[k]=vals.length>0?vals.reduce((a,b)=>a+b,0)/vals.length:null;
  }
  return out;
}

// ── Main ───────────────────────────────────────────────────────────────────
const STATS=['opk','dpo','nwr','ocr','lc','ipm','kill'];
const LABELS={opk:'OPK',dpo:'D/O',nwr:'NWR%',ocr:'OCR%',lc:'L-C%',ipm:'IPM',kill:'Kill%'};
const FMT={
  opk: v=>(v==null?'  —  ':v.toFixed(2).padStart(6)),
  dpo: v=>(v==null?'  —  ':v.toFixed(1).padStart(6)),
  nwr: v=>(v==null?'  —  ':(v*100).toFixed(1).padStart(5)+'%'),
  ocr: v=>(v==null?'  —  ':(v*100).toFixed(1).padStart(5)+'%'),
  lc:  v=>(v==null?'  —  ':(v*100).toFixed(1).padStart(5)+'%'),
  ipm: v=>(v==null?'  —  ':Math.round(v).toString().padStart(5)+' '),
  kill:v=>(v==null?'  —  ':v.toFixed(1).padStart(5)+'%'),
};

const cc=CONNECT_CODE.toUpperCase();
const files=fs.readdirSync(REPLAY_DIR)
  .filter(f=>f.endsWith('.slp'))
  .map(f=>({name:f, fp:path.join(REPLAY_DIR,f), mtime:fs.statSync(path.join(REPLAY_DIR,f)).mtime}))
  .sort((a,b)=>a.mtime-b.mtime);

console.log(`Processing ${files.length} replays...`);

// Group by matchId
const sets=new Map(); // matchId -> {ours:[], theirs:[], oppCode, results:[]}
for(const {fp} of files){
  try{
    const o=ourStats(fp,cc);
    const t=slippiStats(fp,cc);
    if(!o||!t)continue;
    const mid=o.matchId||fp;
    if(!sets.has(mid))sets.set(mid,{ours:[],theirs:[],oppCode:o.oppCode,results:[]});
    const s=sets.get(mid);
    s.ours.push(o); s.theirs.push(t); s.results.push(o.result);
  }catch{}
}

const sorted=[...sets.entries()].sort((a,b)=>{
  // sort by first game's mtime (approximate via matchId lexicographic if no better signal)
  return a[0].localeCompare(b[0]);
});

console.log(`\nFound ${sorted.length} sets\n`);
console.log('='.repeat(100));
console.log('PER-SET COMPARISON  (our parser  /  slippi-js)');
console.log('='.repeat(100));

const hdr=STATS.map(s=>LABELS[s].padEnd(14)).join('  ');
console.log('Set'.padEnd(22)+'Result'.padEnd(8)+hdr);
console.log('-'.repeat(100));

for(const [mid,{ours,theirs,oppCode,results}] of sorted){
  const avgO=avgStats(ours,STATS);
  const avgT=avgStats(theirs,STATS);
  const wins=results.filter(r=>r==='win').length;
  const label=`vs ${oppCode}`.padEnd(20);
  const res=`${wins}-${results.length-wins}`.padEnd(7);
  const cols=STATS.map(s=>{
    const o=FMT[s](avgO[s]), t=FMT[s](avgT[s]);
    return `${o}/${t}`;
  }).join('  ');
  console.log(label+' '+res+' '+cols);
}

console.log('\nFormat: ours / slippi-js  (averaged across games in set)');
