/**
 * bulk_compare_all.cjs — run with: node scripts/bulk_compare_all.cjs
 *
 * Scans all .slp files, runs both slippi-js and our frame-based parser,
 * and reports accuracy for every slippi-comparable stat:
 *   OPK, D/O, NWR, OCR, L-cancel, IPM, AvgKill%
 */

'use strict';
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
  try { nodeBuf=fs.readFileSync(filepath.replace(/\//g,'\\')); } catch { return null; }
  const buf=nodeBuf.buffer.slice(nodeBuf.byteOffset,nodeBuf.byteOffset+nodeBuf.byteLength);
  const data=new Uint8Array(buf), view=new DataView(buf);

  let hasMode=false;
  for(let i=0;i<data.length-4;i++){
    if(data[i]===109&&data[i+1]===111&&data[i+2]===100&&data[i+3]===101&&data[i+4]===46){hasMode=true;break;}
  }
  if(!hasMode) return null;

  const evStart=15, rawLen=view.getInt32(11,false), evEnd=evStart+rawLen;
  if(data[evStart]!==0x35) return null;
  const epSize=data[evStart+1], payloadSizes={};
  for(let i=0;i<Math.floor((epSize-1)/3);i++){const off=evStart+2+i*3;payloadSizes[data[off]]=view.getUint16(off+1,false);}

  let pos=evStart+1+epSize, gameEndMethod=-1;
  const finalStocks={}, frameData={}, lCancelSucc={}, lCancelAtt={};
  const prevActionState={}, maxPreFrame={}, prevButtons={}, inputCounts={};
  const stockPercents={}, prevStocks={}, prevPercents={}, damageThisStock={}, totalDmg={};

  while(pos<evEnd){
    const cmd=data[pos], size=payloadSizes[cmd];
    if(size===undefined){pos++;continue;}
    const ps=pos+1;
    if(cmd===0x38&&size>=33){
      const port=data[ps+4],isF=data[ps+5];
      if(!isF&&port<=3){
        const fn=view.getInt32(ps,false), state=view.getUint16(ps+7,false);
        const stocks=data[ps+32], percent=view.getFloat32(ps+21,false);
        finalStocks[port]=stocks;
        if(!frameData[port])frameData[port]=[];
        const lastHitBy=data[ps+31];
        frameData[port].push({frame:fn,state,percent,stocks,lastHitBy});
        if(size>=51&&state>=65&&state<=74&&state!==(prevActionState[port]??-1)){
          const lc=data[ps+50];
          if(lc===1){lCancelSucc[port]=(lCancelSucc[port]||0)+1;lCancelAtt[port]=(lCancelAtt[port]||0)+1;}
          else if(lc===2){lCancelAtt[port]=(lCancelAtt[port]||0)+1;}
        }
        prevActionState[port]=state;
        if(prevStocks[port]!==undefined&&stocks<prevStocks[port]){
          if(!stockPercents[port])stockPercents[port]=[];
          stockPercents[port].push(prevPercents[port]??percent);
          totalDmg[port]=(totalDmg[port]||0)+(damageThisStock[port]||0);
          damageThisStock[port]=0;
        } else { damageThisStock[port]=percent; }
        prevStocks[port]=stocks; prevPercents[port]=percent;
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

  for(const port of Object.keys(damageThisStock).map(Number))
    totalDmg[port]=(totalDmg[port]||0)+(damageThisStock[port]||0);

  // Metadata
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

  // Deduplicate frames
  for(const port of Object.keys(frameData).map(Number)){
    const seen=new Map();
    for(const snap of frameData[port])seen.set(snap.frame,snap);
    frameData[port]=Array.from(seen.values()).sort((a,b)=>a.frame-b.frame);
  }

  const playerFrames=frameData[playerPort]??[];
  const oppMap=new Map();
  for(const snap of frameData[oppPort]??[])oppMap.set(snap.frame,snap);

  // Conversion stats
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
    const playerStun=isInStun(snap.state),playerCtrl=isInControl(snap.state);

    if(prevOppStocks>=0&&opp.stocks<prevOppStocks){
      if(opp.lastHitBy===playerPort)attrKillPcts.push(opp.percent);
    }

    if(prevOppStocks>=0&&opp.stocks<prevOppStocks&&pConvActive){
      if(convHitCount>=2)openingConvCount++;
      pConvActive=false;pResetCtr=0;convHitCount=0;convLastOppPct=-1;
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
    else if(oConvActive){if(playerCtrl||oResetCtr>0){oResetCtr++;if(oResetCtr>RESET){oConvActive=false;oResetCtr=0;}}}
    prevOppStun=oppStun;
  }
  if(pConvActive&&convHitCount>=2)openingConvCount++;

  const nwTotal=pNW+oNW;
  const durationFrames=playerFrames.reduce((mx,s)=>s.frame>mx?s.frame:mx,0);
  const durationMins=durationFrames/3600;

  return {
    opk:  attrKillPcts.length>0?pConvCount/attrKillPcts.length:null,
    dpo:  pConvCount>0?(totalDmg[oppPort]??0)/pConvCount:null,
    nwr:  nwTotal>0?pNW/nwTotal:null,
    ocr:  pConvCount>0?openingConvCount/pConvCount:null,
    lc:   (lCancelAtt[playerPort]||0)>0?(lCancelSucc[playerPort]||0)/(lCancelAtt[playerPort]||0):null,
    ipm:  durationMins>0?(inputCounts[playerPort]||0)/durationMins:null,
    kill: attrKillPcts.length>0?attrKillPcts.reduce((a,b)=>a+b,0)/attrKillPcts.length:null,
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
  const ourKills=convs.filter(c=>c.didKill&&c.lastHitBy===playerIdx);
  const kPcts=ourKills.map(c=>c.endPercent).filter(p=>p!=null&&p>0);

  return {
    opk:  pO.openingsPerKill?.ratio??null,
    dpo:  pO.damagePerOpening?.ratio??null,
    nwr:  pO.neutralWinRatio?.ratio??null,
    ocr:  pO.successfulConversions?.ratio??null,
    lc:   lcTot>0?lcSucc/lcTot:null,
    ipm:  pO.digitalInputsPerMinute?.ratio??null,
    kill: kPcts.length>0?kPcts.reduce((a,b)=>a+b,0)/kPcts.length:null,
  };
}

// ── Main ───────────────────────────────────────────────────────────────────

const cc=CONNECT_CODE.toUpperCase();
const files=fs.readdirSync(REPLAY_DIR).filter(f=>f.endsWith('.slp')).map(f=>path.join(REPLAY_DIR,f));
console.log(`Scanning ${files.length} replays...`);

// Per-stat config: label, display unit, display multiplier, exact threshold,
// and three tolerance bands (for "within X" summary rows).
const STAT_CONFIG = {
  opk:  { label:'OPK',   unit:'/kill', mul:1,   exact:0.01, t1:0.1,  t2:0.5,  t3:1.0  },
  dpo:  { label:'D/O',   unit:' dmg',  mul:1,   exact:0.1,  t1:1.0,  t2:2.5,  t3:5.0  },
  nwr:  { label:'NWR',   unit:'pp',    mul:100, exact:0.005,t1:0.01, t2:0.03, t3:0.05 },
  ocr:  { label:'OCR',   unit:'pp',    mul:100, exact:0.005,t1:0.01, t2:0.03, t3:0.05 },
  lc:   { label:'L-Can', unit:'pp',    mul:100, exact:0.005,t1:0.01, t2:0.03, t3:0.05 },
  ipm:  { label:'IPM',   unit:'/min',  mul:1,   exact:0.5,  t1:2.0,  t2:5.0,  t3:10.0 },
  kill: { label:'Kill%', unit:'pp',    mul:1,   exact:0.1,  t1:1.0,  t2:3.0,  t3:5.0  },
};
const STATS=Object.keys(STAT_CONFIG);

// Per-stat accumulators: store {diff, file} for outlier display
const acc={};
for(const s of STATS) acc[s]=[];

let processed=0, skipped=0;

for(const fp of files){
  try{
    const s=slippiStats(fp,cc);
    const o=ourStats(fp,cc);
    if(!s||!o){skipped++;continue;}

    let anyValid=false;
    for(const stat of STATS){
      if(s[stat]!=null&&o[stat]!=null){
        acc[stat].push({diff:o[stat]-s[stat], ours:o[stat], theirs:s[stat], file:path.basename(fp)});
        anyValid=true;
      }
    }
    if(anyValid)processed++;
  }catch{skipped++;}
}

console.log(`\nProcessed: ${processed} games  |  Skipped: ${skipped}\n`);
console.log('='.repeat(80));
console.log('FULL STAT ACCURACY  (our parser vs slippi-js)');
console.log('='.repeat(80));

const avg=arr=>arr.reduce((a,b)=>a+b,0)/arr.length;

console.log(
  'Stat'.padEnd(7),
  'N'.padStart(5),
  'Exact'.padStart(10),
  'Avg|gap|'.padStart(10),
  'Max|gap|'.padStart(10),
  'MaxOver'.padStart(10),
  'MaxUnder'.padStart(10),
);
console.log('-'.repeat(80));

for(const stat of STATS){
  const cfg=STAT_CONFIG[stat];
  const entries=acc[stat];
  if(entries.length===0){console.log(cfg.label.padEnd(7),'  no comparable games');continue;}
  const abs=entries.map(e=>Math.abs(e.diff));
  const exact=abs.filter(v=>v<cfg.exact).length;
  const m=cfg.mul;
  const avgAbs=(avg(abs)*m).toFixed(m>=100?2:2);
  const maxAbs=(Math.max(...abs)*m).toFixed(m>=100?1:2);
  const maxOver=(Math.max(...entries.map(e=>e.diff))*m).toFixed(m>=100?1:2);
  const maxUnder=(Math.min(...entries.map(e=>e.diff))*m).toFixed(m>=100?1:2);
  console.log(
    cfg.label.padEnd(7),
    entries.length.toString().padStart(5),
    `${exact}/${entries.length} (${(exact/entries.length*100).toFixed(0)}%)`.padStart(14),
    (avgAbs+cfg.unit).padStart(10),
    (maxAbs+cfg.unit).padStart(10),
    ((+maxOver>=0?'+':'')+maxOver+cfg.unit).padStart(10),
    (maxUnder+cfg.unit).padStart(10),
  );
}

console.log('\n  Within-tolerance summary (in stat units):');
for(const stat of STATS){
  const cfg=STAT_CONFIG[stat];
  const entries=acc[stat];
  if(entries.length===0)continue;
  const abs=entries.map(e=>Math.abs(e.diff));
  const n=entries.length;
  const w1=abs.filter(v=>v<=cfg.t1).length;
  const w2=abs.filter(v=>v<=cfg.t2).length;
  const w3=abs.filter(v=>v<=cfg.t3).length;
  const m=cfg.mul;
  console.log(`    ${cfg.label.padEnd(7)}  ≤${(cfg.t1*m).toFixed(cfg.t1*m<1?2:1)}${cfg.unit}: ${(w1/n*100).toFixed(0)}%   ≤${(cfg.t2*m).toFixed(cfg.t2*m<1?2:1)}${cfg.unit}: ${(w2/n*100).toFixed(0)}%   ≤${(cfg.t3*m).toFixed(cfg.t3*m<1?2:1)}${cfg.unit}: ${(w3/n*100).toFixed(0)}%`);
}

// Top outliers per stat
console.log('\n  Top 5 outliers per stat (worst absolute gaps):');
for(const stat of STATS){
  const cfg=STAT_CONFIG[stat];
  const entries=acc[stat];
  if(entries.length===0)continue;
  const sorted=[...entries].sort((a,b)=>Math.abs(b.diff)-Math.abs(a.diff)).slice(0,5);
  const anyBig=sorted.some(e=>Math.abs(e.diff)>=cfg.t3);
  if(!anyBig)continue;  // skip if all top-5 are within tightest tolerance
  console.log(`\n    ${cfg.label} (unit: ${cfg.unit.trim()}):`);
  console.log('    '+('File').padEnd(34)+('slippi-js').padStart(10)+('ours').padStart(10)+('diff').padStart(10));
  for(const e of sorted){
    const m=cfg.mul;
    const sign=e.diff>=0?'+':'';
    console.log('    '+e.file.padEnd(34)+(e.theirs*m).toFixed(2).padStart(9)+cfg.unit+(e.ours*m).toFixed(2).padStart(9)+cfg.unit+(sign+(e.diff*m).toFixed(2)).padStart(9)+cfg.unit);
  }
}
