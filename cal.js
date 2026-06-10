// ── Calendrier polar-app ──────────────────────────────────────
var CAL_Y=new Date().getFullYear(),CAL_M=new Date().getMonth(),EVS={},EXS={};
var CAL_DS=null,CAL_DE=null,CAL_DRAG=false,CAL_COLOR="#1a1a2e",CAL_EDIT_FP=null,_calVoyId=null;
var CAL_VIEW="month",CAL_WEEK_START=null,CAL_DAY=null;
var MN=["Janvier","Fevrier","Mars","Avril","Mai","Juin","Juillet","Aout","Septembre","Octobre","Novembre","Decembre"];
var DN=["Lun","Mar","Mer","Jeu","Ven","Sam","Dim"];
var SLOT_H=30,HOUR_START=7,HOUR_END=23,SLOTS_TOTAL=(HOUR_END-HOUR_START)*2;
var SLOT_PX=parseInt(localStorage.getItem("cal_slot_px")||"16");
var TYPE_COLORS={autre:"#1a1a2e",course:"#e63946",velo:"#f59e0b",natation:"#3b82f6",renfo:"#7c3aed",repos:"#6b7280",race:"#dc2626",perso:"#2d6a4f"};

function _p(n){return String(n).padStart(2,"0");}
function _ds(y,m,d){return y+"-"+_p(m+1)+"-"+_p(d);}
function _getTs(){return new Date().toISOString().slice(0,10);}
function _weekStart(d){var day=new Date(d);var diff=(day.getDay()+6)%7;day.setDate(day.getDate()-diff);day.setHours(0,0,0,0);return day;}
function _addDays(d,n){var r=new Date(d);r.setDate(r.getDate()+n);return r;}
function _slotToHM(slot){var totalMin=HOUR_START*60+slot*SLOT_H;return _p(Math.floor(totalMin/60))+":"+_p(totalMin%60);}
function _hmToSlot(hm){if(!hm)return -1;var parts=hm.split(":");var h=parseInt(parts[0]),m=parseInt(parts[1]||0);var slot=(h*60+m-HOUR_START*60)/SLOT_H;return Math.max(0,Math.min(SLOTS_TOTAL-1,Math.floor(slot)));}

function calZoom(d){SLOT_PX=Math.max(14,Math.min(40,SLOT_PX+d*4));localStorage.setItem("cal_slot_px",SLOT_PX);drawCal();}

function calSetView(v){
  CAL_VIEW=v;
  ["day","week","month"].forEach(function(n){
    var b=document.getElementById("cal-btn-"+n);
    if(!b)return;
    b.style.background=v===n?"#1565c0":"#f7f5f0";
    b.style.color=v===n?"#fff":"";
    b.style.borderColor=v===n?"#1565c0":"#e8e4dc";
  });
  drawCal();
}

async function loadCal(){
  try{var re=await fetch("/api/calendar/exercises"),de=await re.json();EXS=de;}catch(e){}
  try{
    var r=await fetch("/api/calendar/events"),d=await r.json();EVS={};
    d.forEach(function(e){
      if(!EVS[e.date])EVS[e.date]=[];EVS[e.date].push(e);
      if(e.end_date&&e.end_date!==e.date){
        var c=new Date(e.date);c.setDate(c.getDate()+1);var ed=new Date(e.end_date);
        while(c<=ed){
          var dk=_ds(c.getFullYear(),c.getMonth(),c.getDate());
          if(!EVS[dk])EVS[dk]=[];
          EVS[dk].push(Object.assign({},e,{_cont:true,_isEnd:dk===e.end_date}));
          c.setDate(c.getDate()+1);
        }
      }
    });
  }catch(e){}
  drawCal();
}

function calNav(d){
  if(CAL_VIEW==="week"){if(!CAL_WEEK_START)CAL_WEEK_START=_weekStart(new Date());CAL_WEEK_START=_addDays(CAL_WEEK_START,d*7);}
  else if(CAL_VIEW==="day"){CAL_DAY=_addDays(CAL_DAY||new Date(),d);}
  else{CAL_M+=d;if(CAL_M>11){CAL_M=0;CAL_Y++;}if(CAL_M<0){CAL_M=11;CAL_Y--;}}
  drawCal();
}

function calGoToday(){var n=new Date();CAL_Y=n.getFullYear();CAL_M=n.getMonth();CAL_WEEK_START=_weekStart(n);CAL_DAY=new Date();drawCal();}

function drawCal(){
  var g=document.getElementById("cal-grid");if(!g)return;
  var ts=_getTs();
  if(CAL_VIEW==="week"){_drawWeekView(g,ts);}
  else if(CAL_VIEW==="day"){_drawDayView(g,ts);}
  else{_drawMonthView(g,ts);}
}

// ── Bloc événement pour la vue mois ──────────────────────────
function _evBlock(e){
  var bg=e.color||"#1a1a2e";
  var ecls="cal-ev";
  if(e._cont&&!e._isEnd)ecls+=" multiday-mid";
  else if(e._cont&&e._isEnd)ecls+=" multiday-end";
  else if(e.end_date&&e.end_date!==e.date)ecls+=" multiday-start";
  var timeStr=(!e.all_day&&e.start_time&&!e._cont)?(e.start_time.slice(0,5)+" "):"";
  var lbl=e._cont?"\u00bb "+e.title:timeStr+e.title;
  var clickAttr=e.read_only?"":" onclick='event.stopPropagation();calOpenEdit(\""+e.fp+"\")'";
  var opacity=e.read_only?" opacity:.65":"";
  return "<span class='"+ecls+"' style='background:"+bg+";"+opacity+"'"+clickAttr+"><span class='cal-ev-title'>"+lbl+"</span></span>";
}

// ── Vue mois ─────────────────────────────────────────────────
function _drawMonthView(g,ts){
  document.getElementById("cal-title").textContent=MN[CAL_M]+" "+CAL_Y;
  var f1=new Date(CAL_Y,CAL_M,1),sd=(f1.getDay()+6)%7;
  var dim=new Date(CAL_Y,CAL_M+1,0).getDate(),pd=new Date(CAL_Y,CAL_M,0).getDate();
  var tot=Math.ceil((sd+dim)/7)*7;
  var html="<div class='cal-grid'>";
  DN.forEach(function(d){html+="<div class='cal-dh'>"+d+"</div>";});
  for(var i=0;i<tot;i++){
    var day,mo,yr,cls="cal-cell",om=false;
    if(i<sd){day=pd-sd+i+1;mo=CAL_M-1;yr=CAL_Y;if(mo<0){mo=11;yr--;}cls+=" other-m";om=true;}
    else if(i>=sd+dim){day=i-sd-dim+1;mo=CAL_M+1;yr=CAL_Y;if(mo>11){mo=0;yr++;}cls+=" other-m";om=true;}
    else{day=i-sd+1;mo=CAL_M;yr=CAL_Y;}
    var dw=i%7;if((dw===5||dw===6)&&!om)cls+=" weekend";
    var ds=_ds(yr,mo,day);if(ds===ts)cls+=" today";
    html+="<div class='"+cls+"' data-d='"+ds+"' onclick='calDayClick(\""+ds+"\")'>";
    html+="<div class='cal-dn'>"+day+"</div>";
    (EVS[ds]||[]).forEach(function(e){html+=_evBlock(e);});
    var exList=EXS[ds]||[];
    if(exList.length>0){
      var seen={};var icons=[];var hasReal=false;
      exList.forEach(function(ex){if(!seen[ex.ico]){seen[ex.ico]=1;icons.push(ex.ico);}if(ex.type==="realise")hasReal=true;});
      var dotHtml=hasReal?"<span style='display:inline-block;width:5px;height:5px;border-radius:50%;background:#2d6a4f;margin-left:2px;flex-shrink:0'></span>":"";
      html+="<div style='position:absolute;bottom:2px;right:2px;display:flex;gap:1px;align-items:center;pointer-events:none'>"+dotHtml+icons.map(function(i){return "<span style='font-size:1.3rem;line-height:1'>"+i+"</span>";}).join("")+"</div>";
    }
    html+="</div>";
  }
  html+="</div>";g.innerHTML=html;
  _attachMonthDrag(g);
}

function calDayClick(ds){
  if(CAL_VIEW==="month"){calOpenCreate(ds,ds);}
}

function _attachMonthDrag(g){
  var _et=null;
  g.querySelectorAll(".cal-cell").forEach(function(el){
    el.addEventListener("mousedown",function(ev){if(ev.button!==0||ev.target!==el&&ev.target.className==="cal-dn")return;CAL_DS=el.dataset.d;CAL_DE=el.dataset.d;CAL_DRAG=true;ev.preventDefault();});
    el.addEventListener("mousemove",function(ev){
      if(!CAL_DRAG)return;CAL_DE=el.dataset.d;_hlDrag();
      var rect=g.getBoundingClientRect();var pct=(ev.clientX-rect.left)/rect.width;
      if(pct<0.05){if(!_et)_et=setTimeout(function(){_et=null;calNav(-1);},800);}
      else if(pct>0.95){if(!_et)_et=setTimeout(function(){_et=null;calNav(1);},800);}
      else{if(_et){clearTimeout(_et);_et=null;}}
    });
    el.addEventListener("mouseup",function(){if(!CAL_DRAG)return;if(_et){clearTimeout(_et);_et=null;}CAL_DE=el.dataset.d;CAL_DRAG=false;_clrDrag();calOpenCreate(CAL_DS,CAL_DE);});
  });
  document.addEventListener("mouseup",function(){if(CAL_DRAG){CAL_DRAG=false;_clrDrag();}});
}

// ── Vue semaine ───────────────────────────────────────────────
function _drawWeekView(g,ts){
  if(!CAL_WEEK_START)CAL_WEEK_START=_weekStart(new Date());
  var ws=CAL_WEEK_START;var we=_addDays(ws,6);
  var wsMon=MN[ws.getMonth()];var weMon=MN[we.getMonth()];
  document.getElementById("cal-title").textContent=ws.getDate()+" "+wsMon+(wsMon!==weMon?" - "+we.getDate()+" "+weMon:" - "+we.getDate())+" "+ws.getFullYear();
  var days=[];for(var i=0;i<7;i++)days.push(_addDays(ws,i));
  var s="<div id='wv-wrap' style='display:flex;flex-direction:column;border:1px solid #e8e4dc;border-radius:8px;background:#fff'>";
  // Header
  s+="<div style='display:flex;flex-shrink:0;border-bottom:2px solid #e8e4dc;background:#f7f5f0'>";
  s+="<div style='width:44px;flex-shrink:0'></div>";
  for(var i=0;i<7;i++){
    var dd=days[i];var ds=_ds(dd.getFullYear(),dd.getMonth(),dd.getDate());
    var isToday=(ds===ts);
    s+="<div style='flex:1;text-align:center;padding:5px 2px;font-size:.7rem;font-weight:700;color:"+(isToday?"#e63946":"#4a4a6a")+";border-left:1px solid #e8e4dc'>"+DN[i]+"<br><span style='font-size:1rem;font-weight:900;"+(isToday?"background:#e63946;color:#fff;border-radius:50%;padding:0 5px;":"")+"'>"+dd.getDate()+"</span></div>";
  }
  s+="</div>";
  // All-day strip
  var hasAD=false;
  for(var i=0;i<7;i++){var ds2=_ds(days[i].getFullYear(),days[i].getMonth(),days[i].getDate());(EVS[ds2]||[]).forEach(function(e){if(e.all_day||!e.start_time)hasAD=true;});}
  if(hasAD){
    s+="<div style='display:flex;flex-shrink:0;border-bottom:1px solid #e8e4dc;min-height:26px'>";
    s+="<div style='width:44px;flex-shrink:0;font-size:.58rem;color:#9ca3af;padding:4px 3px 0;text-align:right'>Jour</div>";
    for(var i=0;i<7;i++){
      var ds2=_ds(days[i].getFullYear(),days[i].getMonth(),days[i].getDate());
      s+="<div style='flex:1;border-left:1px solid #e8e4dc;padding:2px'>";
      (EVS[ds2]||[]).forEach(function(e){
        if(!e.all_day&&e.start_time)return;
        var ca=e.read_only?"":" onclick='calOpenEdit(\""+e.fp+"\")'";
        s+="<div style='background:"+(e.color||"#1a1a2e")+";color:#fff;font-size:.62rem;padding:1px 4px;border-radius:3px;margin-bottom:1px;cursor:pointer;white-space:nowrap;overflow:hidden;text-overflow:ellipsis;opacity:"+(e.read_only?.65:1)+"'"+ca+">"+e.title+"</div>";
      });
      s+="</div>";
    }
    s+="</div>";
  }
  // Body
  s+="<div style='display:flex;position:relative'>";
  // Hour labels
  s+="<div style='width:44px;flex-shrink:0'>";
  for(var h=HOUR_START;h<HOUR_END;h++){
    s+="<div style='height:"+(SLOT_PX*2)+"px;box-sizing:border-box;padding-top:2px;text-align:right;padding-right:5px;font-size:.58rem;color:#9ca3af;border-top:1px solid #e8e4dc'>"+(h<10?"0"+h:h)+"h</div>";
  }
  s+="</div>";
  // Day columns
  for(var di=0;di<7;di++){
    var dd=days[di];var ds=_ds(dd.getFullYear(),dd.getMonth(),dd.getDate());
    var isToday=(ds===ts);
    s+="<div class='wv-col' data-d='"+ds+"' style='flex:1;position:relative;border-left:1px solid #e8e4dc;background:"+(isToday?"#fffbfb":"#fff")+";min-width:0'>";
    for(var h=HOUR_START;h<HOUR_END;h++){s+="<div style='height:"+(SLOT_PX*2)+"px;box-sizing:border-box;border-top:1px solid #f0ede8'></div>";}
    // Half-hour lines
    for(var h=HOUR_START;h<HOUR_END;h++){s+="<div style='position:absolute;top:"+(((h-HOUR_START)*2+1)*SLOT_PX)+"px;left:0;right:0;border-top:1px dashed #f5f2ee;pointer-events:none'></div>";}
    // Current time
    if(isToday){var now2=new Date();var nt=(now2.getHours()*60+now2.getMinutes()-HOUR_START*60)/SLOT_H*SLOT_PX;s+="<div style='position:absolute;top:"+nt+"px;left:0;right:0;height:2px;background:#e63946;z-index:3;pointer-events:none'><div style='position:absolute;left:-4px;top:-4px;width:8px;height:8px;border-radius:50%;background:#e63946'></div></div>";}
    // Events
    var dayEvs=(EVS[ds]||[]).filter(function(e){return !e.all_day&&e.start_time&&!e._cont;});
    dayEvs.forEach(function(e){
      var slot=_hmToSlot(e.start_time);if(slot<0)return;
      var endSlot=e.end_time?_hmToSlot(e.end_time):slot+2;
      if(endSlot<=slot)endSlot=slot+2;
      var top=slot*SLOT_PX;var height=Math.max(SLOT_PX,(endSlot-slot)*SLOT_PX)-2;
      var bg=e.color||"#1a1a2e";
      var ca=e.read_only?"":" onclick='calOpenEdit(\""+e.fp+"\")'";
      s+="<div style='position:absolute;top:"+top+"px;left:2px;right:2px;height:"+height+"px;background:"+bg+";color:#fff;border-radius:4px;padding:2px 4px;font-size:.62rem;overflow:hidden;cursor:pointer;z-index:2;box-sizing:border-box;opacity:"+(e.read_only?.65:1)+"'"+ca+">";
      s+="<div style='font-weight:700;line-height:1.2'>"+e.start_time.slice(0,5)+" "+e.title+"</div>";
      if(e.end_time&&height>24)s+="<div style='opacity:.8'>"+e.end_time.slice(0,5)+"</div>";
      s+="</div>";
    });
    s+="</div>";
  }
  s+="</div></div>";
  g.innerHTML=s;
  // Drag to create
  var wvD=null,wvS0=null,wvS1=null,wvDrag=false;
  g.querySelectorAll(".wv-col").forEach(function(col){
    col.addEventListener("mousemove",function(ev){
      var rect=col.getBoundingClientRect();var relY=ev.clientY-rect.top;var slot=Math.floor(relY/SLOT_PX);
      var old=document.getElementById("wv-hover");if(old)old.remove();
      if(!wvDrag){
        var hi=document.createElement("div");hi.id="wv-hover";
        hi.style.cssText="position:absolute;left:1px;right:1px;top:"+(slot*SLOT_PX)+"px;height:"+(SLOT_PX-1)+"px;background:rgba(21,101,192,.12);border-radius:3px;pointer-events:none;z-index:1";
        col.appendChild(hi);
      }
      if(wvDrag&&col.dataset.d===wvD){wvS1=Math.max(wvS0,slot);_wvHighlight(col,wvS0,wvS1);}
    });
    col.addEventListener("mouseleave",function(){var old=document.getElementById("wv-hover");if(old)old.remove();});
    col.addEventListener("mousedown",function(ev){
      if(ev.button!==0||ev.target.closest("[onclick]"))return;
      var rect=col.getBoundingClientRect();wvD=col.dataset.d;wvS0=Math.floor((ev.clientY-rect.top)/SLOT_PX);wvS1=wvS0;wvDrag=true;ev.preventDefault();
    });
    col.addEventListener("mouseup",function(){
      if(!wvDrag)return;wvDrag=false;_wvClearHighlight();
      var t1=_slotToHM(wvS0);var t2=_slotToHM(Math.min(wvS1+1,SLOTS_TOTAL-1));
      calOpenCreate(wvD,wvD);
      setTimeout(function(){document.getElementById("cal-inp-t1").value=t1;document.getElementById("cal-inp-t2").value=t2;},30);
    });
  });
  document.addEventListener("mouseup",function(){if(wvDrag){wvDrag=false;_wvClearHighlight();}});
}

function _wvHighlight(col,s0,s1){
  _wvClearHighlight();
  var el=document.createElement("div");el.id="wv-drag-hi";
  el.style.cssText="position:absolute;left:2px;right:2px;top:"+(s0*SLOT_PX)+"px;height:"+((s1-s0+1)*SLOT_PX)+"px;background:rgba(21,101,192,.25);border:2px solid #1565c0;border-radius:4px;pointer-events:none;z-index:5";
  col.appendChild(el);
}
function _wvClearHighlight(){var el=document.getElementById("wv-drag-hi");if(el)el.remove();}

// ── Vue jour ─────────────────────────────────────────────────
function _drawDayView(g,ts){
  if(!CAL_DAY)CAL_DAY=new Date();
  var ds=_ds(CAL_DAY.getFullYear(),CAL_DAY.getMonth(),CAL_DAY.getDate());
  var dayName=DN[((CAL_DAY.getDay()+6)%7)];
  document.getElementById("cal-title").textContent=dayName+" "+CAL_DAY.getDate()+" "+MN[CAL_DAY.getMonth()]+" "+CAL_DAY.getFullYear();
  var isToday=(ds===ts);
  var s="<div style='display:flex;border:1px solid #e8e4dc;border-radius:8px;background:#fff'>";
  s+="<div style='width:44px;flex-shrink:0'>";
  for(var h=HOUR_START;h<HOUR_END;h++){
    s+="<div style='height:"+(SLOT_PX*2)+"px;box-sizing:border-box;padding-top:2px;text-align:right;padding-right:5px;font-size:.58rem;color:#9ca3af;border-top:1px solid #e8e4dc'>"+(h<10?"0"+h:h)+"h</div>";
  }
  s+="</div>";
  s+="<div class='wv-col' data-d='"+ds+"' style='flex:1;position:relative;border-left:1px solid #e8e4dc;background:"+(isToday?"#fffbfb":"#fff")+"'>";
  for(var h=HOUR_START;h<HOUR_END;h++){s+="<div style='height:"+(SLOT_PX*2)+"px;box-sizing:border-box;border-top:1px solid #f0ede8'></div>";}
  for(var h=HOUR_START;h<HOUR_END;h++){s+="<div style='position:absolute;top:"+(((h-HOUR_START)*2+1)*SLOT_PX)+"px;left:0;right:0;border-top:1px dashed #f5f2ee;pointer-events:none'></div>";}
  if(isToday){var now3=new Date();var nt2=(now3.getHours()*60+now3.getMinutes()-HOUR_START*60)/SLOT_H*SLOT_PX;s+="<div style='position:absolute;top:"+nt2+"px;left:0;right:0;height:2px;background:#e63946;z-index:3;pointer-events:none'><div style='position:absolute;left:-4px;top:-4px;width:8px;height:8px;border-radius:50%;background:#e63946'></div></div>";}
  var dayEvs=(EVS[ds]||[]).filter(function(e){return !e.all_day&&e.start_time;});
  dayEvs.forEach(function(e){
    var slot=_hmToSlot(e.start_time);if(slot<0)return;
    var endSlot=e.end_time?_hmToSlot(e.end_time):slot+2;if(endSlot<=slot)endSlot=slot+2;
    var top=slot*SLOT_PX;var height=Math.max(SLOT_PX,(endSlot-slot)*SLOT_PX)-2;
    var bg=e.color||"#1a1a2e";
    var ca=e.read_only?"":" onclick='calOpenEdit(\""+e.fp+"\")'";
    s+="<div style='position:absolute;top:"+top+"px;left:4px;right:4px;height:"+height+"px;background:"+bg+";color:#fff;border-radius:4px;padding:3px 6px;font-size:.7rem;overflow:hidden;cursor:pointer;z-index:2;box-sizing:border-box'"+ca+">";
    s+="<div style='font-weight:700'>"+e.start_time.slice(0,5)+"–"+(e.end_time?e.end_time.slice(0,5):"?")+" "+e.title+"</div>";
    if(e.notes)s+="<div style='opacity:.8;font-size:.62rem'>"+e.notes+"</div>";
    s+="</div>";
  });
  s+="</div></div>";
  g.innerHTML=s;
  // Drag to create in day view
  var col=g.querySelector(".wv-col");
  if(col){
    var dvS0=null,dvDrag=false;
    col.addEventListener("mousedown",function(ev){if(ev.button!==0||ev.target.closest("[onclick]"))return;var rect=col.getBoundingClientRect();dvS0=Math.floor((ev.clientY-rect.top)/SLOT_PX);dvDrag=true;ev.preventDefault();});
    col.addEventListener("mousemove",function(ev){
      var rect=col.getBoundingClientRect();var slot=Math.floor((ev.clientY-rect.top)/SLOT_PX);
      var old=document.getElementById("wv-hover");if(old)old.remove();
      if(!dvDrag){var hi=document.createElement("div");hi.id="wv-hover";hi.style.cssText="position:absolute;left:1px;right:1px;top:"+(slot*SLOT_PX)+"px;height:"+(SLOT_PX-1)+"px;background:rgba(21,101,192,.12);border-radius:3px;pointer-events:none;z-index:1";col.appendChild(hi);}
    });
    col.addEventListener("mouseleave",function(){var old=document.getElementById("wv-hover");if(old)old.remove();});
    col.addEventListener("mouseup",function(ev){
      if(!dvDrag)return;dvDrag=false;
      var rect=col.getBoundingClientRect();var dvS1=Math.max(dvS0,Math.floor((ev.clientY-rect.top)/SLOT_PX));
      calOpenCreate(ds,ds);
      setTimeout(function(){document.getElementById("cal-inp-t1").value=_slotToHM(dvS0);document.getElementById("cal-inp-t2").value=_slotToHM(Math.min(dvS1+1,SLOTS_TOTAL-1));},30);
    });
    document.addEventListener("mouseup",function(){if(dvDrag)dvDrag=false;});
  }
}

// ── Drag helpers ──────────────────────────────────────────────
function _hlDrag(){
  _clrDrag();var d1=CAL_DS<CAL_DE?CAL_DS:CAL_DE,d2=CAL_DS<CAL_DE?CAL_DE:CAL_DS;
  document.querySelectorAll(".cal-cell").forEach(function(el){if(el.dataset.d>=d1&&el.dataset.d<=d2)el.classList.add("drag-over");});
}
function _clrDrag(){document.querySelectorAll(".drag-over").forEach(function(el){el.classList.remove("drag-over");});}

// ── Modal ─────────────────────────────────────────────────────
function _resetModal(){
  CAL_COLOR="#1a1a2e";CAL_EDIT_FP=null;_calVoyId=null;
  ["cal-inp-title","cal-inp-d1","cal-inp-d2","cal-inp-t1","cal-inp-t2","cal-inp-notes"].forEach(function(id){var el=document.getElementById(id);if(el)el.value="";});
  var rt=document.getElementById("cal-inp-recur");if(rt)rt.value="none";
  var tp=document.getElementById("cal-inp-type");if(tp)tp.value="autre";
  document.querySelectorAll(".cal-color-opt").forEach(function(el){el.classList.toggle("selected",el.dataset.c==="#1a1a2e");});
  document.getElementById("cal-btn-delete").style.display="none";
  var vb=document.getElementById("cal-btn-voyage");if(vb)vb.style.display="none";
  var dab=document.getElementById("cal-btn-delete-all");if(dab)dab.style.display="none";
}

function calTypeChanged(){
  var tp=document.getElementById("cal-inp-type");if(!tp)return;
  var col=TYPE_COLORS[tp.value];if(!col)return;
  calSelColor(document.querySelector(".cal-color-opt[data-c='"+col+"']")||document.querySelector(".cal-color-opt"));
  CAL_COLOR=col;
  document.querySelectorAll(".cal-color-opt").forEach(function(el){el.classList.toggle("selected",el.dataset.c===col);});
}

function calSelColor(el){if(!el)return;CAL_COLOR=el.dataset.c;document.querySelectorAll(".cal-color-opt").forEach(function(e){e.classList.remove("selected");});el.classList.add("selected");var fc=document.getElementById("cal-color-free");if(fc)fc.value=CAL_COLOR;}
function calSelFreeColor(inp){CAL_COLOR=inp.value;document.querySelectorAll(".cal-color-opt").forEach(function(e){e.classList.remove("selected");});}

function calAutoFillEnd(){
  var d1=document.getElementById("cal-inp-d1").value;
  var t1=document.getElementById("cal-inp-t1").value;
  var d2=document.getElementById("cal-inp-d2").value;
  var t2=document.getElementById("cal-inp-t2").value;
  if(d1&&!d2)document.getElementById("cal-inp-d2").value=d1;
  if(t1&&!t2){var parts=t1.split(":");var h=(parseInt(parts[0])+1)%24;document.getElementById("cal-inp-t2").value=(h<10?"0"+h:h)+":"+(parts[1]||"00");}
}

function calOpenCreate(d1,d2){
  if(d1>d2){var t=d1;d1=d2;d2=t;}
  _resetModal();
  document.getElementById("cal-modal-title").textContent="Nouvel \u00e9v\u00e9nement";
  document.getElementById("cal-inp-d1").value=d1;
  document.getElementById("cal-inp-d2").value=d2||d1;
  document.getElementById("cal-modal").classList.add("open");
  setTimeout(function(){document.getElementById("cal-inp-title").focus();},50);
}

function calOpenEdit(fp){
  var ev=null;
  Object.values(EVS).forEach(function(arr){arr.forEach(function(e){if(e.fp===fp)ev=e;});});
  if(!ev)return;
  _resetModal();CAL_EDIT_FP=fp;
  document.getElementById("cal-modal-title").textContent="Modifier l\u2019\u00e9v\u00e9nement";
  document.getElementById("cal-inp-title").value=ev.title;
  document.getElementById("cal-inp-d1").value=ev.date;
  document.getElementById("cal-inp-d2").value=ev.end_date&&ev.end_date!==ev.date?ev.end_date:ev.date;
  document.getElementById("cal-inp-t1").value=ev.start_time||"";
  document.getElementById("cal-inp-t2").value=ev.end_time||"";
  var nt=document.getElementById("cal-inp-notes");if(nt)nt.value=ev.notes||"";
  var tp=document.getElementById("cal-inp-type");if(tp&&ev.type)tp.value=ev.type;
  CAL_COLOR=ev.color||"#1a1a2e";
  document.querySelectorAll(".cal-color-opt").forEach(function(el){el.classList.toggle("selected",el.dataset.c===CAL_COLOR);});
  document.getElementById("cal-btn-delete").style.display="inline-block";
  if(ev.recur_id){var dab=document.getElementById("cal-btn-delete-all");if(dab)dab.style.display="inline-block";}
  var vb=document.getElementById("cal-btn-voyage");
  if(vb&&ev.type==="voyage"&&ev.voyage_id){vb.style.display="inline-block";_calVoyId=ev.voyage_id;}else if(vb)vb.style.display="none";
  document.getElementById("cal-modal").classList.add("open");
  setTimeout(function(){document.getElementById("cal-inp-title").focus();},50);
}

function calOpenVoyage(){if(_calVoyId)window.location.href="/voyages?id="+_calVoyId;}
function calModalClose(){document.getElementById("cal-modal").classList.remove("open");}

async function calModalSave(){
  var t=document.getElementById("cal-inp-title").value.trim();if(!t){alert("Titre requis");return;}
  var d1=document.getElementById("cal-inp-d1").value;
  var d2=document.getElementById("cal-inp-d2").value||d1;
  var t1=document.getElementById("cal-inp-t1").value;
  var t2=document.getElementById("cal-inp-t2").value;
  var tp=document.getElementById("cal-inp-type");var type=tp?tp.value:"autre";
  var rn=document.getElementById("cal-inp-recur");var recur=rn?rn.value:"none";
  var nt=document.getElementById("cal-inp-notes");var notes=nt?nt.value:"";
  var payload={title:t,date:d1,end_date:d2,start_time:t1,end_time:t2,color:CAL_COLOR,type:type,recur:recur,notes:notes};
  if(CAL_EDIT_FP){
    payload.fp=CAL_EDIT_FP;
    await fetch("/api/calendar/update",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
  }else{
    await fetch("/api/calendar/create",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(payload)});
  }
  calModalClose();loadCal();
}

async function calModalDelete(){
  if(!CAL_EDIT_FP)return;
  if(!confirm("Supprimer cet \u00e9v\u00e9nement ?"))return;
  await fetch("/api/calendar/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({fp:CAL_EDIT_FP})});
  calModalClose();loadCal();
}

async function calModalDeleteAll(){
  if(!CAL_EDIT_FP)return;
  if(!confirm("Supprimer toutes les occurrences de cette r\u00e9currence ?"))return;
  await fetch("/api/calendar/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({fp:CAL_EDIT_FP,delete_all_recur:true})});
  calModalClose();loadCal();
}

// ── Raccourcis clavier ────────────────────────────────────────
document.addEventListener("keydown",function(ev){
  if(ev.target.tagName==="INPUT"||ev.target.tagName==="TEXTAREA"||ev.target.tagName==="SELECT")return;
  if(ev.key==="ArrowLeft")calNav(-1);
  else if(ev.key==="ArrowRight")calNav(1);
  else if(ev.key==="Escape")calModalClose();
  else if(ev.key==="t"||ev.key==="T")calGoToday();
  else if(ev.key==="d"||ev.key==="D")calSetView("day");
  else if(ev.key==="w"||ev.key==="W")calSetView("week");
  else if(ev.key==="m"||ev.key==="M")calSetView("month");
});

calSetView("month");loadCal();
