import json, sys
from pathlib import Path
sys.path.insert(0, "/root/polar")

FINANCES_DIR = Path("/root/polar/finances")
VIE_START = "2026-01"
VIE_END   = "2027-05"
REVENUS_VIE  = ["Indemnite geo","Indemnite com","Aide logement","Revenus non prevus"]
DEPENSES_VIE = ["Loyer","Telephone","Deezer","Informatique","Courses","Complements","Triathlon","Cadeaux","Loisirs","Medical","Retour France","Voyage"]
REVENUS_AN   = ["Salaire","Navigo rembourse","Versement mensuel","Revenus non prevus"]
DEPENSES_AN  = ["Navigo","Telephone","Manger","Sorties","Ajustement"]
MOIS_FR = ["Jan","Fev","Mar","Avr","Mai","Jun","Jul","Aou","Sep","Oct","Nov","Dec"]

def months_range(s,e):
    r=[];y,m=int(s[:4]),int(s[5:7]);ey,em=int(e[:4]),int(e[5:7])
    while(y,m)<=(ey,em):
        r.append(f"{y}-{m:02d}");m+=1
        if m>12:m=1;y+=1
    return r

def months_of_year(y):return[f"{y}-{m:02d}"for m in range(1,13)]
def default_section(labels,months):return{l:{m:0 for m in months}for l in labels}

def default_data():
    vm=months_range(VIE_START,VIE_END)
    def mk(rv,dp,ms):
        return{"revenus":default_section(rv,ms),"depenses":default_section(dp,ms),
               "debit_differe":{m:{"montant":0,"date_debit":""}for m in ms},
               "epargne_theorique":{m:0 for m in ms}}
    return{"vie":mk(REVENUS_VIE,DEPENSES_VIE,vm),
           "2024":mk(REVENUS_AN,DEPENSES_AN,months_of_year(2024)),
           "2025":mk(REVENUS_AN,DEPENSES_AN,months_of_year(2025)),
           "2026":mk(REVENUS_AN,DEPENSES_AN,months_of_year(2026))}

def load_finances_data():
    p=FINANCES_DIR/"finances_data.json"
    return json.loads(p.read_text(encoding="utf-8"))if p.exists()else default_data()

def save_finances_data(data):
    FINANCES_DIR.mkdir(parents=True,exist_ok=True)
    (FINANCES_DIR/"finances_data.json").write_text(json.dumps(data,ensure_ascii=False,indent=2),encoding="utf-8")

def build_finances_page(data):
    if not data:data=default_data()
    dj=json.dumps(data,ensure_ascii=False)
    vmj=json.dumps(months_range(VIE_START,VIE_END))
    an24j=json.dumps(months_of_year(2024))
    an25j=json.dumps(months_of_year(2025))
    an26j=json.dumps(months_of_year(2026))
    
    try:
        from finances_investments_ui import investments_js,investments_css,investments_modal_html
        inv_js=investments_js();inv_css=investments_css();inv_modal=investments_modal_html()
    except:
        inv_js="";inv_css="";inv_modal=""
    return _build(dj,vmj,an24j,an25j,an26j,inv_js,inv_css,inv_modal)

def _build(dj,vmj,an24j,an25j,an26j,inv_js,inv_css,inv_modal):
    CSS="""*{box-sizing:border-box;margin:0;padding:0}body{font-family:Roboto,Arial,sans-serif;background:#f0ede8;color:#1a1a2e;font-size:.8rem}#app{max-width:1600px;margin:0 auto}.app-header{background:#1a1a2e;color:#fff;padding:14px 20px;display:flex;align-items:center;justify-content:space-between}.app-header h1{font-size:1.1rem;font-weight:800}.app-header p{font-size:.7rem;color:#9ca3af;margin-top:2px}.period-tabs{display:flex;gap:4px;padding:10px 20px 0;background:#f0ede8;border-bottom:2px solid #e8e4dc;overflow-x:auto}.period-tab{padding:8px 18px;border:none;background:#e8e4dc;border-radius:8px 8px 0 0;cursor:pointer;font-size:.75rem;font-weight:700;color:#4a4a6a;white-space:nowrap}.period-tab.active{background:#fff;color:#1a1a2e;box-shadow:0 -2px 0 #1565c0 inset}.kpis{display:flex;gap:12px;padding:16px 20px;flex-wrap:wrap}.kpi-card{background:#fff;border-radius:12px;border:1px solid #e8e4dc;padding:14px 18px;flex:1;min-width:140px}.kpi-label{font-size:.6rem;color:#6b7280;font-weight:700;text-transform:uppercase}.kpi-value{font-size:1.2rem;font-weight:900;margin-top:4px}.kpi-sub{font-size:.65rem;color:#6b7280;margin-top:2px}.green{color:#2d6a4f}.red{color:#e63946}.blue{color:#1565c0}.section{background:#fff;border-radius:12px;border:1px solid #e8e4dc;margin:0 20px 16px;overflow:hidden}.section-head{display:flex;align-items:center;justify-content:space-between;padding:10px 16px;background:#1a1a2e;color:#fff}.section-head h3{font-size:.82rem;font-weight:700}.table-wrap{overflow-x:auto}table{width:100%;border-collapse:collapse}th{background:#f7f5f0;padding:6px 8px;font-size:.63rem;font-weight:700;color:#4a4a6a;text-align:right;border-bottom:1px solid #e8e4dc;white-space:nowrap}th:first-child{text-align:left}td{padding:4px 6px;border-bottom:1px solid #f0ede8;text-align:right}td:first-child{text-align:left}tr:hover td{background:#fafaf8}.row-label{font-weight:700;font-size:.75rem;text-align:left}.cell-pos{color:#2d6a4f;font-weight:700}.cell-neg{color:#e63946;font-weight:700}.total-th,.total-cell{background:#eff6ff;font-weight:800;color:#1565c0}.avg-th,.avg-cell{background:#f7f5f0;color:#6b7280;font-style:italic}.total-row td{background:#eff6ff;font-weight:800}.row-rev td{background:#f0fdf4}.row-dep td{background:#fff5f5}.row-ep td{background:#eff6ff;font-weight:800}.month-th{cursor:pointer;color:#1565c0}.month-th:hover{background:#dbeafe}.cur-month{background:#fef9c3!important;font-weight:900;color:#92400e!important}input[type=number].cell-input{width:72px;border:1px solid #e8e4dc;border-radius:4px;padding:2px 4px;text-align:right;font-size:.72rem;background:transparent}input[type=number].cell-input:focus{outline:none;border-color:#1565c0;background:#fff}input[type=number].wide{width:110px}input.row-name{border:1px solid transparent;border-radius:4px;padding:2px 6px;font-size:.72rem;background:transparent;font-weight:600;min-width:120px}input.row-name:focus{outline:none;border-color:#1565c0;background:#fff}input.inline-input{width:90px;border:1px solid #e8e4dc;border-radius:4px;padding:2px 6px;font-size:.72rem;text-align:right}.btn{padding:7px 14px;border:none;border-radius:7px;cursor:pointer;font-size:.73rem;font-weight:700}.btn-save{background:#2d6a4f;color:#fff}.btn-primary{background:#1565c0;color:#fff}.btn-gray{background:#e8e4dc;color:#1a1a2e}.btn-xs{padding:3px 9px;border:none;border-radius:5px;cursor:pointer;font-size:.68rem;font-weight:700}.btn-add{background:#2d6a4f;color:#fff}.btn-del{background:none;border:none;color:#e63946;cursor:pointer;font-size:.8rem;padding:2px 6px}.monthly-header{display:flex;align-items:center;justify-content:space-between;padding:10px 20px;background:#fff;border-bottom:1px solid #e8e4dc;flex-wrap:wrap;gap:8px;margin-bottom:0}.month-tabs{display:flex;gap:4px;padding:8px 20px;background:#f7f5f0;border-bottom:1px solid #e8e4dc}.month-tab{padding:6px 14px;border:none;background:#e8e4dc;border-radius:6px;cursor:pointer;font-size:.73rem;font-weight:700;color:#4a4a6a}.month-tab.active{background:#1a1a2e;color:#fff}.month-nav{display:flex;align-items:center;gap:12px}.month-nav h2{font-size:1rem;font-weight:800;min-width:120px;text-align:center}.summary-block{padding:16px}.summary-row{display:flex;justify-content:space-between;padding:6px 0;border-bottom:1px solid #f0ede8;font-size:.82rem}.summary-row.indent{padding-left:16px;color:#6b7280}.summary-divider{border-top:2px solid #1a1a2e;margin:6px 0}.dd-warning{margin-top:12px;padding:10px 14px;background:#fff3cd;border-radius:8px;border:1px solid #ffc107;font-size:.78rem}.modal-overlay{display:none;position:fixed;inset:0;background:rgba(0,0,0,.5);z-index:100;align-items:center;justify-content:center}.modal-box{background:#fff;border-radius:14px;padding:24px;width:360px;max-width:95vw}.modal-box h3{font-size:.9rem;font-weight:800;margin-bottom:16px}.form-group{margin-bottom:14px}.form-group label{display:block;font-size:.7rem;font-weight:700;color:#4a4a6a;margin-bottom:4px}.form-group input,.form-group select{width:100%;border:1px solid #e8e4dc;border-radius:8px;padding:9px 12px;font-size:.82rem}.modal-actions{display:flex;gap:8px;margin-top:18px}.modal-actions button{flex:1;padding:10px;border:none;border-radius:8px;cursor:pointer;font-weight:700;font-size:.8rem}.toast{position:fixed;bottom:24px;left:50%;transform:translateX(-50%);background:#1a1a2e;color:#fff;padding:10px 22px;border-radius:24px;font-size:.78rem;z-index:999;display:none}"""

    JS = """
var MOIS=["Jan","F\\u00e9v","Mar","Avr","Mai","Jun","Jul","Ao\\u00fb","Sep","Oct","Nov","D\\u00e9c"];
var D=_DATA_;
var VIE_MONTHS=_VIE_;
var AN_MONTHS={"2024":_AN24_,"2025":_AN25_,"2026":_AN26_};
var now=new Date(),currentYear=now.getFullYear().toString();
var currentPeriod=currentYear,currentMonth=null,modalCtx=null,currentMonthTab="rd";
var _curMonthYM=now.getFullYear()+"-"+(now.getMonth()+1<10?"0":"")+(now.getMonth()+1);
var _invLoaded=false;

function fmtM(ym){var p=ym.split("-");return MOIS[parseInt(p[1])-1]+" "+p[0].slice(2);}
function fmtMc(ym){return MOIS[parseInt(ym.split("-")[1])-1];}
function n(v){return parseFloat(v)||0;}
function euros(v,sign){
  if(v===undefined||v===null)return "\\u2014";
  var r=Math.round(Math.abs(v)).toLocaleString("fr-FR")+"\\u20ac";
  if(sign)return (v>=0?"+":"-")+r;
  return (v<0?"-":"")+r;
}
function eurosDec(v,sign){
  if(v===undefined||v===null)return "\\u2014";
  var r=Math.abs(v).toLocaleString("fr-FR",{minimumFractionDigits:2,maximumFractionDigits:2})+"\\u20ac";
  if(sign)return (v>=0?"+":"-")+r;
  return (v<0?"-":"")+r;
}
function pct(v){return isNaN(v)||!isFinite(v)?"":v.toFixed(1)+"%";}
function months(){return currentPeriod==="vie"?VIE_MONTHS:(AN_MONTHS[currentPeriod]||[]);}
function pd(){return D[currentPeriod]||{};}
function sumSec(sec,m){return Object.values((pd()[sec]||{})).reduce(function(a,r){return a+n(r[m]);},0);}

function renderKPIs(){
  var ms=months(),p=pd(),tR=0,tD=0,tDD=0,tE=0;
  ms.forEach(function(m){
    tR+=sumSec("revenus",m);tD+=sumSec("depenses",m);
    tDD+=n(((p.debit_differe||{})[m]||{}).montant);
    tE+=n((p.epargne_theorique||{})[m]);
  });
  var ep=tR-tD,tx=tR>0?ep/tR*100:0;
  var h="";
  h+='<div class="kpi-card"><div class="kpi-label">Revenus</div><div class="kpi-value green">'+euros(tR)+'</div></div>';
  h+='<div class="kpi-card"><div class="kpi-label">D\\u00e9penses</div><div class="kpi-value red">'+euros(tD)+'</div></div>';
  h+='<div class="kpi-card"><div class="kpi-label">\\u00c9pargne nette</div><div class="kpi-value '+(ep>=0?"blue":"red")+'">'+euros(ep)+'</div><div class="kpi-sub">'+pct(tx)+' du revenu</div></div>';
  h+='<div class="kpi-card"><div class="kpi-label">\\u00c9pargne th\\u00e9orique</div><div class="kpi-value blue">'+euros(tE)+'</div></div>';
  document.getElementById("kpis").innerHTML=h;
}

function renderAnnual(){
  var ms=months(),p=pd(),h="";
  var monthly={};var _TODAY=_curMonthYM;
  // Calcul intérêts livrets par mois
  var _livretInterets={};
  ms.forEach(function(m){_livretInterets[m]=0;});
  if(_INV_DATA&&_INV_DATA.livrets){
    Object.values(_INV_DATA.livrets).forEach(function(lv){
      var solde=parseFloat(lv.solde)||0;
      var taux=parseFloat(lv.taux_actuel)||0;
      var intMois=solde*taux/100/12;
      ms.forEach(function(m){_livretInterets[m]+=intMois;});
    });
  }
  ms.forEach(function(m){
    var rv=sumSec("revenus",m),dp=sumSec("depenses",m),dd=n(((p.debit_differe||{})[m]||{}).montant);
    var _sit=(D[currentPeriod].perf_snapshot||{})[m];
    var it;
    if(_sit!=null&&_sit!==undefined){it=n(_sit);}
    else if(m===_curMonthYM&&_INV_DATA&&_INV_DATA.livrets){
      var _itL=0;
      Object.values(_INV_DATA.livrets||{}).forEach(function(lv){_itL+=(parseFloat(lv.solde)||0)*(parseFloat(lv.taux_actuel)||0)/100/12;});
      it=Math.round(_itL);
    }else{it=null;}
    monthly[m]={rv:rv,dp:dp,dd:dd,it:it,ep:rv-dp};
  });
  h+='<div class="section"><div class="section-head"><h3>R\\u00e9capitulatif</h3></div><div class="table-wrap"><table>';
  h+='<thead><tr><th>Cat\\u00e9gorie</th>';
  ms.forEach(function(m){h+='<th class="month-th'+(m===_curMonthYM?" cur-month":"")+'" onclick="openMonth(this.dataset.m)" data-m="'+m+'">'+fmtMc(m)+'</th>';});
  h+='<th class="total-th">Total</th><th class="avg-th">Moy.</th></tr></thead><tbody>';
  var defs=[
    {k:"rv",lbl:"Revenus",cls:"row-rev"},
    {k:"dp",lbl:"D\\u00e9penses",cls:"row-dep"},
    {k:"dd",lbl:"D\u00e9bit diff\u00e9r\u00e9",cls:""},
    {k:"it",lbl:"Int\u00e9r\u00eats",cls:"row-rev"},
    {k:"ep",lbl:"\u00c9pargne nette",cls:"row-ep"},
  ];
  defs.forEach(function(d){
    h+='<tr class="'+d.cls+'"><td class="row-label">'+d.lbl+'</td>';
    var tot=0;
    ms.forEach(function(m){
      var v=monthly[m][d.k];
      if(d.k==="it"){
        h+='<td class="data-cell" style="padding:2px 4px"><input type="number" step="1" class="cell-input perf-inp" data-m="'+m+'" value="'+(v!=null?v:'')+'" placeholder="—" style="width:68px;font-size:.68rem"/></td>';
        if(v!=null)tot+=v;
      } else {
        tot+=v||0;
        var c=d.k==="ep"?(v>=0?"cell-pos":"cell-neg"):"";
        h+='<td class="data-cell '+c+'" data-m="'+m+'" onclick="openMonth(this.dataset.m)">'+euros(v)+'</td>';
      }
    });
    var msPast=ms.filter(function(m){return m<=_curMonthYM;});
    var totPast=0;msPast.forEach(function(m){totPast+=monthly[m][d.k];});
    var avg=msPast.length?totPast/msPast.length:0;
    h+='<td class="total-cell">'+euros(tot)+'</td><td class="avg-cell">'+euros(avg)+'</td></tr>';
  });
  h+='</tbody></table></div></div>';
  document.getElementById("view-annual").innerHTML=h;
  renderPatrimoine(document.getElementById("view-annual"));
}

function renderDetailTable(title,sec,ms,p){
  var data=p[sec]||{},rows=Object.keys(data),isR=(sec==="revenus");
  var h='<div class="section"><div class="section-head"><h3>'+(isR?"Revenus":"D\\u00e9penses")+'</h3>';
  h+='<button class="btn-xs btn-add" onclick="openModal(\\''+sec+'\\')">+ Ajouter</button></div>';
  h+='<div class="table-wrap"><table><thead><tr><th>Libell\\u00e9</th>';
  ms.forEach(function(m){h+='<th>'+fmtMc(m)+'</th>';});
  h+='<th class="total-th">Total</th><th class="avg-th">Moy.</th><th></th></tr></thead><tbody>';
  rows.forEach(function(row){
    var vals=ms.map(function(m){return n((data[row]||{})[m]);});
    var tot=vals.reduce(function(a,b){return a+b;},0);
    var pos=vals.filter(function(v){return v>0;});
    var moy=pos.length?pos.reduce(function(a,b){return a+b;},0)/pos.length:0;
    var esc=encodeURIComponent(row);
    h+='<tr><td><input class="row-name" type="text" value="'+row.replace(/&/g,"&amp;").replace(/"/g,"&quot;")+'" onchange="renameRow(\\''+sec+'\\',decodeURIComponent(\\''+esc+'\\'),this.value)"/></td>';
    ms.forEach(function(m,i){h+='<td><input type="number" class="cell-input" value="'+(vals[i]||"")+'" oninput="setVal(\\''+sec+'\\',decodeURIComponent(\\''+esc+'\\'),\\''+m+'\\',this.value,false)"/></td>';});
    h+='<td class="total-cell">'+euros(tot)+'</td><td class="avg-cell">'+euros(moy)+'</td>';
    h+='<td><button class="btn-del" onclick="deleteRow(\\''+sec+'\\',decodeURIComponent(\\''+esc+'\\'))">&#x2715;</button></td></tr>';
  });
  var gt=0;h+='<tr class="total-row"><td><strong>Total</strong></td>';
  ms.forEach(function(m){var t=rows.reduce(function(a,r){return a+n((data[r]||{})[m]);},0);gt+=t;h+='<td class="total-cell">'+euros(t)+'</td>';});
  h+='<td class="total-cell"><strong>'+euros(gt)+'</strong></td><td class="avg-cell">'+euros(gt/ms.length)+'</td><td></td></tr>';
  h+='</tbody></table></div></div>';
  return h;
}

function openMonth(ym){
  currentMonth=ym;
  document.getElementById("view-annual").style.display="none";
  document.getElementById("kpis").style.display="none";
  renderMonthly();
  document.getElementById("view-monthly").style.display="block";
}

function closeMonth(){
  currentMonth=null;
  document.getElementById("view-monthly").style.display="none";
  document.getElementById("view-annual").style.display="block";
  document.getElementById("kpis").style.display="flex";
}

function renderMonthly(){
  var m=currentMonth,p=pd(),ms=months();
  var idx=ms.indexOf(m),prev=idx>0?ms[idx-1]:null,next=idx<ms.length-1?ms[idx+1]:null;
  var h='<div class="monthly-header">';
  h+='<button class="btn btn-gray" onclick="closeMonth()">\\u2190 Vue annuelle</button>';
  h+='<div class="month-nav">';
  if(prev)h+='<button class="btn btn-gray" onclick="openMonth(\\''+prev+'\\')">\\u2039 '+fmtMc(prev)+'</button>';
  h+='<h2>'+fmtM(m)+'</h2>';
  if(next)h+='<button class="btn btn-gray" onclick="openMonth(\\''+next+'\\')">'+fmtMc(next)+' \\u203a</button>';
  h+='</div><div></div></div>';
  h+='<div class="month-tabs">';
  h+='<button class="month-tab active" id="mtab-rd" onclick="renderMonthTab(\\'rd\\')">Revenus &amp; D\\u00e9penses</button>';
  h+='<button class="month-tab" id="mtab-inv" onclick="renderMonthTab(\\'inv\\')">Investissements</button>';
  h+='</div>';
  h+='<div id="month-tab-content"></div>';
  document.getElementById("view-monthly").innerHTML=h;
  currentMonthTab="rd";
  renderMonthTab("rd");
  if(!_invLoaded){
    if(typeof loadInvestments==="function"){loadInvestments();loadQuotes();_invLoaded=true;}
  }
}

function renderMonthTab(tab){
  currentMonthTab=tab;
  document.querySelectorAll(".month-tab").forEach(function(b){b.classList.toggle("active",b.id==="mtab-"+tab);});
  var m=currentMonth,p=pd();
  if(tab==="rd"){
    var h=renderMonthSec("Revenus","revenus",m,p);
    h+=renderMonthSec("D\\u00e9penses","depenses",m,p);
    h+=renderMonthlySummary(m,p);
    document.getElementById("month-tab-content").innerHTML=h;
  } else if(tab==="inv"){
    if(typeof renderInvestments==="function"){
      var _el=document.getElementById("month-tab-content");
      _el.innerHTML='<div style="padding:20px;text-align:center;color:#9ca3af">Chargement...</div>';
      Promise.all([typeof loadInvestments==="function"?loadInvestments():Promise.resolve(),
                   typeof loadQuotes==="function"?loadQuotes():Promise.resolve()])
      .then(function(){_el.innerHTML=renderInvestments();});
    }
  }
}

function renderMonthlySummary(m,p){
  var rv=sumSec("revenus",m),dp=sumSec("depenses",m);
  var dd=n(((p.debit_differe||{})[m]||{}).montant);
  var ddDate=((p.debit_differe||{})[m]||{}).date_debit||"";
  var ep=rv-dp;
  // Intérêts du mois depuis perf_snapshot
  var it=(D[currentPeriod].perf_snapshot||{})[m];
  // Si mois actuel et pas encore de snapshot -> calculer depuis livrets
  if((it===undefined||it===null)&&m===_curMonthYM&&_INV_DATA&&_INV_DATA.livrets){
    var _itLiv=0;
    Object.values(_INV_DATA.livrets||{}).forEach(function(lv){_itLiv+=(parseFloat(lv.solde)||0)*(parseFloat(lv.taux_actuel)||0)/100/12;});
    it=Math.round(_itLiv);
  }
  var h='<div class="section"><div class="section-head"><h3>R\\u00e9sum\\u00e9</h3></div><div class="summary-block">';
  h+='<div class="summary-row"><span>Revenus</span><span class="green">'+euros(rv)+'</span></div>';
  h+='<div class="summary-row"><span>D\\u00e9penses imm\\u00e9diates</span><span class="red">'+euros(-dp)+'</span></div>';
  h+='<div class="summary-row indent"><span>D\\u00e9bit diff\\u00e9r\\u00e9 CB</span><span class="red"><input type="number" class="inline-input" value="'+(dd||"")+'" oninput="setDD(\\''+m+'\\',\\'montant\\',this.value)"/>\\u20ac</span></div>';
  h+='<div class="summary-divider"></div>';
  h+='<div class="summary-row"><span>Total d\\u00e9penses</span><span class="red">'+euros(-dp)+'</span></div>';
  h+='<div class="summary-row" style="font-weight:700"><span>\\u00c9pargne nette</span><span class="'+(ep>=0?"green":"red")+'">'+euros(ep,true)+'</span></div>';
  if(it!=null){h+='<div class="summary-row"><span>Performance (int\\u00e9r\\u00eats + PV)</span><span class="'+(it>=0?"green":"red")+'">'+euros(it,true)+'</span></div>';}
  // Répartition épargne
  if(ep>0){
    var inv=_INV_DATA||{};
    var livTot=Object.values(inv.livrets||{}).reduce(function(s,l){return s+(parseFloat(l.solde)||0);},0);
    var scpiTot=Object.values(inv.scpi||{}).reduce(function(s,b){return s+(parseFloat(b.valeur)||0);},0)+(parseFloat((inv.liquidites_bricks||{}).montant)||0);
    var ctoTot=Object.values(inv.cto||{}).reduce(function(s,t){return s+(parseFloat(t.qte)||0)*(parseFloat(t.pru)||0);},0);
    var patTot=livTot+scpiTot+ctoTot;
    if(patTot>0){
      h+='<div class="summary-divider"></div>';
      h+='<div class="summary-row"><span style="font-weight:700;font-size:.72rem">R\\u00e9partition \\u00e9pargne</span><span></span></div>';
      // Répartition fixe: CTO 25%, SCPI 15%, Livrets 60%
      var reps=[{lbl:"Livrets",pct:60},{lbl:"SCPI/Bricks",pct:15},{lbl:"CTO",pct:25}];
      reps.forEach(function(r){
        var montant=Math.round(ep*r.pct/100);
        h+='<div class="summary-row indent"><span>'+r.lbl+' ('+r.pct+'%)</span><span style="color:#1565c0;font-weight:700">'+euros(montant)+'</span></div>';
      });
  }
  }
  if(dd>0){h+='<div class="dd-warning">D\\u00e9bit \\u00e0 venir : <strong>'+euros(dd)+'</strong> &mdash; Date : <input type="text" class="inline-input" value="'+ddDate+'" placeholder="JJ/MM" oninput="setDD(\\''+m+'\\',\\'date_debit\\',this.value)"/></div>';}
  h+='</div></div>';
  return h;
}

function renderMonthSec(title,sec,m,p){
  var data=p[sec]||{},rows=Object.keys(data),isR=(sec==="revenus"),tot=0;
  var h='<div class="section"><div class="section-head"><h3>'+title+'</h3>';
  h+='<button class="btn-xs btn-add" onclick="openModal(\\''+sec+'\\')">+ Ajouter</button></div>';
  h+='<table><thead><tr><th>Libell\\u00e9</th><th>Montant</th><th></th></tr></thead><tbody>';
  rows.forEach(function(row){
    var v=n((data[row]||{})[m]);tot+=v;
    var esc=encodeURIComponent(row);
    h+='<tr><td><input class="row-name" type="text" value="'+row.replace(/&/g,"&amp;").replace(/"/g,"&quot;")+'" onchange="renameRow(\\''+sec+'\\',decodeURIComponent(\\''+esc+'\\'),this.value)"/></td>';
    h+='<td><input type="number" class="cell-input wide" value="'+(v||"")+'" oninput="setVal(\\''+sec+'\\',decodeURIComponent(\\''+esc+'\\'),\\''+m+'\\',this.value,false)"/></td>';
    h+='<td><button class="btn-del" onclick="deleteRow(\\''+sec+'\\',decodeURIComponent(\\''+esc+'\\'))">&#x2715;</button></td></tr>';
  });
  h+='<tr class="total-row"><td><strong>Total</strong></td><td class="total-cell"><strong>'+euros(tot)+'</strong></td><td></td></tr>';
  h+='</tbody></table></div>';
  return h;
}

function setVal(sec,row,m,val,propagate){var p=D[currentPeriod];if(!p)return;if(!p[sec])p[sec]={};if(!p[sec][row])p[sec][row]={};var v=parseFloat(val)||0;p[sec][row][m]=v;if(propagate){var ms2=months(),idx2=ms2.indexOf(m);for(var i=idx2+1;i<ms2.length;i++){p[sec][row][ms2[i]]=v;}}renderKPIs();clearTimeout(window._svt);window._svt=setTimeout(saveAll,800);}
function setDD(m,field,val){var p=D[currentPeriod];if(!p.debit_differe)p.debit_differe={};if(!p.debit_differe[m])p.debit_differe[m]={montant:0,date_debit:""};if(field==="montant")p.debit_differe[m].montant=parseFloat(val)||0;else p.debit_differe[m].date_debit=val;renderKPIs();clearTimeout(window._svt);window._svt=setTimeout(saveAll,800);}
function setEpTh(m,val){var p=D[currentPeriod];if(!p.epargne_theorique)p.epargne_theorique={};p.epargne_theorique[m]=parseFloat(val)||0;renderKPIs();clearTimeout(window._svt);window._svt=setTimeout(saveAll,800);}
function calcEpTh(m){var rv=sumSec('revenus',m),dp=sumSec('depenses',m),p=D[currentPeriod];
  var dd=((p.debit_differe||{})[m]||{}).montant||0;
  return rv-dp;}
function renameRow(sec,old,nw){if(!nw||old===nw)return;var p=D[currentPeriod];if(!p||!p[sec]||!p[sec][old])return;p[sec][nw]=p[sec][old];delete p[sec][old];if(currentMonth)renderMonthTab(currentMonthTab);else renderAnnual();}
function deleteRow(sec,row){if(!confirm('Supprimer "'+row+'" ?'))return;var p=D[currentPeriod];if(p&&p[sec])delete p[sec][row];if(currentMonth)renderMonthTab(currentMonthTab);else renderAnnual();}


// ── PATRIMOINE ──────────────────────────────────────────────
var _INV_DATA=null;
async function loadInvData(){
  if(_INV_DATA)return _INV_DATA;
  try{var r=await fetch("/api/finances/investments");_INV_DATA=await r.json();}catch(e){_INV_DATA={};}
  return _INV_DATA;
}
function calcValeur(items,useSolde,useMarket){
  var tot=0;
  Object.values(items||{}).forEach(function(t){
    if(useSolde){tot+=parseFloat(t.solde)||0;}
    else if(useMarket){
      var q=parseFloat(t.qte)||0;
      var pru=parseFloat(t.pru)||0;
      // La clé dans items est le symbol
      var found=false;
      Object.keys(items).forEach(function(sym){
        if(items[sym]===t){
          var q2=_quotes[sym];var prix=q2?parseFloat(q2.price):null;
          var cur=q2?q2.currency:'EUR';
          if(prix&&cur==='USD'&&_eurusd)prix=prix/_eurusd;
          if(prix&&q){tot+=q*prix;found=true;}
        }
      });
      if(!found)tot+=q*pru;
    }
    else{var q=parseFloat(t.qte)||0,p=parseFloat(t.pru)||0;tot+=q*p;}
  });
  return tot;
}
async function renderPatrimoine(container){
  var inv=await loadInvData();
  if(typeof loadQuotes==="function"&&Object.keys(_quotes).length===0)await loadQuotes();
  var cats=[
    {id:"livrets",lbl:"Livrets",ico:"🏦",col:"#1565c0",useSolde:true},
    {id:"pea",lbl:"PEA",ico:"📈",col:"#2d6a4f",useSolde:false,useMarket:true,addLiq:true},
    {id:"cto",lbl:"CTO / Trade Republic",ico:"💹",col:"#7c3aed",useSolde:false,useMarket:true},
    {id:"crypto",lbl:"Crypto",ico:"₿",col:"#f59e0b",useSolde:false,useCrypto:true},
    {id:"scpi",lbl:"Immobilier / Bricks",ico:"🏠",col:"#e63946",useSolde:true,useScpi:true,addLiqBricks:true},
    {id:"autres_produits",lbl:"AV / PER / Épargne",ico:"💼",col:"#1a1a2e",useSolde:true},
  ];
  var total=0;
  var vals=cats.map(function(c){
    var items=inv[c.id]||{};
    var v=0;
    if(c.useScpi){
      // SCPI: liste de logements avec valeur
      var today=new Date().toISOString().slice(0,10);
      Object.values(items).forEach(function(b){
        if(!b.date_fin||b.date_fin>=today)v+=parseFloat(b.valeur)||0;
      });
    } else if(c.useCrypto){
      Object.entries(items).forEach(function(e){
        var id=e[0],pos=e[1];
        var q=parseFloat(pos.qte)||0;
        var cp=_crypto[id];var prix=cp?parseFloat(cp.eur):null;
        if(prix&&q)v+=q*prix;
        else v+=q*(parseFloat(pos.pru)||0);
      });
    } else {
      v=calcValeur(items,c.useSolde,c.useMarket);
      if(c.addLiq)v+=parseFloat((inv.liquidites||{}).montant)||0;
    }
    if(c.addLiqBricks)v+=parseFloat((inv.liquidites_bricks||{}).montant)||0;
    total+=v;return v;
  });
  // KPI
  var h='<div class="section" style="margin-top:8px"><div class="section-head"><h3>💰 Patrimoine estimé</h3><div style="display:flex;align-items:center;gap:10px"><span style="font-size:.75rem;opacity:.7">PRU × quantité</span><button onclick="openMonth(_curMonthYM);setTimeout(renderInvTab,200)" style="background:#fff;border:1px solid rgba(255,255,255,.4);border-radius:6px;padding:3px 10px;font-size:.65rem;font-weight:700;cursor:pointer;color:#1a1a2e">📊 Détail →</button></div></div><div style="padding:14px">';
  h+='<div style="font-size:1.4rem;font-weight:900;color:#1a1a2e;margin-bottom:14px">'+euros(total)+'</div>';
  // Barres
  h+='<div style="display:flex;flex-direction:column;gap:8px">';
  cats.forEach(function(c,i){
    var v=vals[i],pct2=total>0?v/total*100:0;
    h+='<div style="display:flex;align-items:center;gap:10px">';
    h+='<div style="width:90px;font-size:.72rem;font-weight:700;flex-shrink:0">'+c.ico+' '+c.lbl+'</div>';
    h+='<div style="flex:1;background:#f0ede8;border-radius:6px;height:14px;overflow:hidden">';
    h+='<div style="width:'+pct2.toFixed(1)+'%;height:100%;background:'+c.col+';border-radius:6px;transition:width .4s"></div></div>';
    h+='<div style="width:80px;text-align:right;font-size:.72rem;font-weight:700">'+euros(v)+'</div>';
    h+='<div style="width:40px;text-align:right;font-size:.65rem;color:#9ca3af">'+pct2.toFixed(1)+'%</div>';
    h+='</div>';
  });
  h+='</div>';
  // Graphique épargne cumulée
  var ms=months(),p=pd();
  var cumEp=0,cumData=[];
  ms.forEach(function(m){
    var rv=sumSec("revenus",m),dp=sumSec("depenses",m);
    var dd=((p.debit_differe||{})[m]||{}).montant||0;
    if(m<=_curMonthYM){cumEp+=rv-dp-dd;}
    cumData.push({m:m,ep:cumEp,past:m<=_curMonthYM});
  });
  var maxVal=Math.max(total,Math.abs(cumEp),1);
  // Tableau historique remplace graphique
  try{
    var rs2=await fetch('/api/finances/snapshots');var snaps2=await rs2.json();
    if(snaps2.length){
      h+='<div style="margin-top:12px"><div style="font-size:.65rem;font-weight:800;text-transform:uppercase;color:#4a4a6a;margin-bottom:6px">📅 Évolution patrimoine & intérêts</div>';
      h+='<table style="width:100%;border-collapse:collapse;font-size:.7rem">';
      var snapByYm={}; snaps2.forEach(function(s){snapByYm[s.ym]=s;});
      var patData=[];
      months().forEach(function(m){
        if(m>_curMonthYM)return;
        var snap=snapByYm[m]||{};
        var pat=(snap.patrimoine||{}).total||0;
        if(pat>0)patData.push({m:m,v:pat});
      });
      if(patData.length){
        var pMin=Math.min.apply(null,patData.map(function(d){return d.v;}));
        var pMax=Math.max.apply(null,patData.map(function(d){return d.v;}));
        if(pMin===pMax){pMin=pMin*0.98;pMax=pMax*1.02;}
        var gW=320,gH=100,gPL=50,gPR=10,gPT=10,gPB=20;
        var gCW=gW-gPL-gPR,gCH=gH-gPT-gPB;
        function gX(i){return gPL+i/(patData.length-1||1)*gCW;}
        function gY(v){return gPT+gCH-(v-pMin)/(pMax-pMin)*gCH;}
        var path='',dots='';
        patData.forEach(function(d,i){
          var x=gX(i).toFixed(1),y=gY(d.v).toFixed(1);
          path+=(i===0?'M':'L')+x+' '+y;
          dots+='<circle cx="'+x+'" cy="'+y+'" r="3" fill="#1565c0"/>';
          dots+='<text x="'+x+'" y="'+(parseFloat(y)+12)+'" font-size="7" text-anchor="middle" fill="#9ca3af">'+fmtM(d.m)+'</text>';
        });
        // Axe Y labels
        var yLabels='';
        [pMin,pMax].forEach(function(v){
          var y=gY(v).toFixed(1);
          yLabels+='<text x="'+(gPL-4)+'" y="'+(parseFloat(y)+3)+'" font-size="7" text-anchor="end" fill="#9ca3af">'+euros(v)+'</text>';
        });
        h+='<svg viewBox="0 0 '+gW+' '+gH+'" style="width:100%;height:100px;display:block;margin-top:8px">';
        h+='<line x1="'+gPL+'" y1="'+gPT+'" x2="'+gPL+'" y2="'+(gPT+gCH)+'" stroke="#e8e4dc" stroke-width="1"/>';
        h+='<line x1="'+gPL+'" y1="'+(gPT+gCH)+'" x2="'+(gPL+gCW)+'" y2="'+(gPT+gCH)+'" stroke="#e8e4dc" stroke-width="1"/>';
        h+=yLabels;
        h+='<path d="'+path+'" stroke="#1565c0" stroke-width="2" fill="none" stroke-linejoin="round"/>';
        h+=dots;
        h+='</svg>';
        // Dernière valeur
        h+='<div style="text-align:right;font-size:.65rem;color:#1565c0;font-weight:700;margin-top:2px">'+euros(patData[patData.length-1].v)+'</div>';
      }else{
        h+='<div style="text-align:center;color:#9ca3af;padding:20px;font-size:.75rem">Aucune donnée de snapshot disponible</div>';
      }
      h+='</div>';
    }
  }catch(e){console.log('snap err',e);}
  h+='</div></div>';
  container.innerHTML+=h;
}

// Event delegation pour perf-inp
document.addEventListener('input',function(e){
  if(e.target&&e.target.classList.contains('perf-inp')){
    var m=e.target.dataset.m;
    var val=parseFloat(e.target.value)||0;
    setPerfSnapshot(m,val);
  }
});
function setPerfSnapshot(m,val){
  if(!D[currentPeriod].perf_snapshot)D[currentPeriod].perf_snapshot={};
  D[currentPeriod].perf_snapshot[m]=parseFloat(val)||0;
  clearTimeout(window._finSvt);window._finSvt=setTimeout(saveAll,600);
}
async function snapshotPerf(){
  var inv=await loadInvData();
  var m=_curMonthYM;
  // Intérêts livrets
  var intLivrets=0;
  Object.values(inv.livrets||{}).forEach(function(lv){
    intLivrets+=(parseFloat(lv.solde)||0)*(parseFloat(lv.taux_actuel)||0)/100/12;
  });
  // PV latentes PEA+CTO
  var pvPortfolio=0;
  ['pea','cto'].forEach(function(type){
    Object.entries(inv[type]||{}).forEach(function(e){
      var sym=e[0],pos=e[1];
      var q=parseFloat(pos.qte)||0,pru=parseFloat(pos.pru)||0;
      var q2=_quotes[sym];var prix=q2?parseFloat(q2.price):null;
      var cur=q2?q2.currency:'EUR';
      if(prix&&cur==='USD'&&_eurusd)prix=prix/_eurusd;
      if(prix&&q)pvPortfolio+=(prix-pru)*q;
    });
  });
  // PV crypto
  var pvCrypto=0;
  Object.entries(inv.crypto||{}).forEach(function(e){
    var id=e[0],pos=e[1];
    var q=parseFloat(pos.qte)||0,pru=parseFloat(pos.pru)||0;
    var cp=_crypto[id];var prix=cp?parseFloat(cp.eur):null;
    if(prix&&q)pvCrypto+=(prix-pru)*q;
  });
  var total=intLivrets+pvPortfolio+pvCrypto;
  if(!D[currentPeriod].perf_snapshot)D[currentPeriod].perf_snapshot={};
  D[currentPeriod].perf_snapshot[m]=Math.round(total);
  saveAll();
  toast('📸 Snapshot '+m+' : '+euros(total)+' sauvegardé');
  renderAnnual();
}
function renderInvTab(){if(typeof renderMonthTab==="function")renderMonthTab("inv");}
function setPeriod(period){
  currentPeriod=period;currentMonth=null;localStorage.setItem("fin_period",period);
  document.querySelectorAll(".period-tab").forEach(function(b){b.classList.toggle("active",b.dataset.period===period);});
  document.getElementById("view-depenses").style.display="none";
  document.getElementById("view-investissements").style.display="none";
  document.getElementById("view-monthly").style.display="none";
  document.getElementById("view-annual").style.display="none";
  document.getElementById("kpis").style.display="none";
  if(period==="depenses"){
    document.getElementById("view-depenses").style.display="block";
    renderDepenses();
    return;
  }
  if(period==="investissements"){
    currentPeriod="vie";
    var _el=document.getElementById("view-investissements");
    _el.innerHTML='<div style="padding:20px;text-align:center;color:#9ca3af">Chargement...</div>';
    Promise.all([typeof loadInvestments==="function"?loadInvestments():Promise.resolve(),
                 typeof loadQuotes==="function"?loadQuotes():Promise.resolve()])
    .then(function(){
      if(typeof renderInvestments==="function"){_el.innerHTML=renderInvestments();}
    });
    document.getElementById("view-investissements").style.display="block";
    return;
  }
  // period === "vie" (Général) : KPI + tableau annuel détaillé (mois par mois)
  document.getElementById("view-annual").style.display="block";
  document.getElementById("kpis").style.display="flex";
  renderKPIs();renderAnnual();
  if(_curMonthYM&&months().indexOf(_curMonthYM)>=0){
    setTimeout(function(){openMonth(_curMonthYM);},80);
  }
}

var _depensesCache=null;
var _pieChartInstance=null;
function getSalaireVie(){
  return (D.settings&&D.settings.salaire_vie)?n(D.settings.salaire_vie):0;
}
function setSalaireVie(v){
  if(!D.settings)D.settings={};
  D.settings.salaire_vie=n(v);
  saveAll();
  renderDepenses();
}
var _depensesSelectedMonth=null;
function selectDepensesMonth(m){
  _depensesSelectedMonth=m;
  renderDepensesContent();
}
function toggleCatGroup(catId){
  var el=document.getElementById("catgroup-"+catId);
  var arrow=document.getElementById("catarrow-"+catId);
  if(!el)return;
  var hidden=el.style.display==="none";
  el.style.display=hidden?"block":"none";
  if(arrow)arrow.textContent=hidden?"\u25be":"\u25b8";
}
function renderDepenses(){
  var container=document.getElementById("view-depenses");
  container.innerHTML='<div style="padding:16px 20px;color:#6b7280;font-size:.8rem">Chargement des d\u00e9penses\u2026</div>';
  fetch("/api/depenses").then(function(r){return r.json();}).then(function(data){
    _depensesCache=data;
    var months=Object.keys(data).sort().reverse();
    if(!_depensesSelectedMonth||months.indexOf(_depensesSelectedMonth)<0){
      _depensesSelectedMonth=months[0]||_curMonthYM;
    }
    container.innerHTML='<div id="depenses-inner"></div>';
    renderDepensesContent();
  }).catch(function(e){
    container.innerHTML='<div style="padding:16px 20px;color:#e63946;font-size:.8rem">Erreur de chargement : '+e+'</div>';
  });
}
function getDepensesMasquees(){
  return (D.settings&&D.settings.depenses_masquees)?D.settings.depenses_masquees:[];
}
function isOpMasquee(fp){
  return getDepensesMasquees().indexOf(fp)>=0;
}
function toggleOpMasquee(fp){
  if(!D.settings)D.settings={};
  if(!D.settings.depenses_masquees)D.settings.depenses_masquees=[];
  var idx=D.settings.depenses_masquees.indexOf(fp);
  if(idx>=0){D.settings.depenses_masquees.splice(idx,1);}
  else{D.settings.depenses_masquees.push(fp);}
  saveAll();
  renderDepensesContent();
}
function computeAdjusted(d){
  var masquees=getDepensesMasquees();
  var byCat={};
  var total=0;
  (d.operations||[]).forEach(function(op){
    if(masquees.indexOf(op.fingerprint)>=0)return;
    if(op.amount>=0)return;
    var cat=op.category_parent||"Autre";
    byCat[cat]=(byCat[cat]||0)+Math.abs(op.amount);
    total+=Math.abs(op.amount);
  });
  return {par_categorie:byCat,total_depenses:Math.round(total*100)/100};
}
function renderDepensesContent(){
  var inner=document.getElementById("depenses-inner");
  if(!inner||!_depensesCache)return;
  var data=_depensesCache;
  var months=Object.keys(data).sort().reverse();
  var curMonth=_depensesSelectedMonth||months[0];
  var dRaw=data[curMonth]||{total_depenses:0,par_categorie:{},operations:[]};
  var adj=computeAdjusted(dRaw);
  // d.operations garde TOUTES les opérations (y compris masquées) pour l'affichage.
  // d.par_categorie / d.total_depenses reflètent uniquement les lignes NON masquées (le calcul).
  var d={operations:dRaw.operations||[],total_mouvements_internes:dRaw.total_mouvements_internes,
         total_depenses:adj.total_depenses,par_categorie:adj.par_categorie};
  var salaire=getSalaireVie();
  var dca=salaire-d.total_depenses;

  var h="";
  h+='<div class="monthly-header"><div style="display:flex;align-items:center;gap:10px">';
  h+='<label style="font-size:.7rem;font-weight:700;color:#4a4a6a">Mois</label>';
  h+='<select id="depenses-month-select" onchange="selectDepensesMonth(this.value)" style="border:1px solid #e8e4dc;border-radius:8px;padding:7px 10px;font-size:.78rem;font-weight:700">';
  months.forEach(function(m){
    h+='<option value="'+m+'"'+(m===curMonth?" selected":"")+'>'+fmtM(m)+'</option>';
  });
  h+='</select></div>';
  h+='<div style="display:flex;align-items:center;gap:8px"><label style="font-size:.7rem;font-weight:700;color:#4a4a6a">Salaire VIE mensuel (net)</label>';
  h+='<input type="number" id="salaire-vie-input" class="inline-input" style="width:110px" value="'+salaire+'" onchange="setSalaireVie(this.value)"/></div>';
  h+='</div>';

  h+='<div class="kpis" style="display:flex">';
  h+='<div class="kpi-card"><div class="kpi-label">Salaire VIE</div><div class="kpi-value blue">'+eurosDec(salaire)+'</div></div>';
  h+='<div class="kpi-card"><div class="kpi-label">D\u00e9penses '+fmtM(curMonth)+'</div><div class="kpi-value red">'+eurosDec(d.total_depenses)+'</div></div>';
  h+='<div class="kpi-card"><div class="kpi-label">DCA estim\u00e9 disponible</div><div class="kpi-value '+(dca>=0?"green":"red")+'">'+eurosDec(dca)+'</div><div class="kpi-sub">'+eurosDec(salaire)+' salaire \u2212 '+eurosDec(d.total_depenses)+' d\u00e9penses</div></div>';
  h+='</div>';

  h+='<div class="section"><div class="section-head"><h3>R\u00e9partition '+fmtM(curMonth)+'</h3></div>';
  h+='<div style="padding:16px"><div style="position:relative;height:260px"><canvas id="depensesPie"></canvas></div>';
  h+='<div id="depensesLegend" style="display:flex;flex-wrap:wrap;gap:10px;font-size:.7rem;color:#6b7280;margin-top:12px;justify-content:center"></div></div></div>';

  var opsByCat={};
  (d.operations||[]).forEach(function(op){
    if(op.amount>=0)return;
    var cat=op.category_parent||"Autre";
    if(!opsByCat[cat])opsByCat[cat]=[];
    opsByCat[cat].push(op);
  });
  var catsSorted=Object.keys(opsByCat);

  h+='<div class="section"><div class="section-head"><h3>D\u00e9tail des op\u00e9rations '+fmtM(curMonth)+'</h3></div><div style="padding:8px 0">';
  catsSorted.forEach(function(cat,idx){
    var ops=(opsByCat[cat]||[]).slice().sort(function(a,b){return a.date<b.date?1:-1;});
    var catTotal=d.par_categorie[cat]||0;
    var catTotalBrut=ops.reduce(function(s,op){return s+Math.abs(op.amount);},0);
    var catId="c"+idx;
    h+='<div style="border-bottom:1px solid #f0ede8">';
    h+='<div onclick="toggleCatGroup(&quot;'+catId+'&quot;)" style="display:flex;align-items:center;justify-content:space-between;padding:10px 16px;cursor:pointer;background:#fafaf8">';
    h+='<div style="display:flex;align-items:center;gap:8px"><span id="catarrow-'+catId+'" style="font-size:.7rem;color:#6b7280">\u25be</span><span style="font-weight:700;font-size:.78rem">'+cat+'</span><span style="font-size:.68rem;color:#6b7280">('+ops.length+')</span></div>';
    h+='<span style="font-weight:800;color:#e63946;font-size:.8rem">'+eurosDec(catTotalBrut)+'</span>';
    h+='</div>';
    h+='<div id="catgroup-'+catId+'" style="display:block">';
    ops.forEach(function(op){
      var isNeg=op.amount<0;
      var checked=isOpMasquee(op.fingerprint)?"":" checked";
      var displayLabel=op.suggested_label||op.label;
      h+='<div style="display:flex;align-items:center;justify-content:space-between;padding:7px 16px 7px 16px;border-top:1px solid #f7f5f0">';
      h+='<div style="display:flex;align-items:center;gap:8px;min-width:0;flex:1">';
      h+='<input type="checkbox"'+checked+' onchange="toggleOpMasquee(&quot;'+op.fingerprint+'&quot;)" style="flex-shrink:0"/>';
      h+='<div style="min-width:0"><div style="font-size:.75rem;font-weight:600;overflow:hidden;text-overflow:ellipsis;white-space:nowrap">'+displayLabel+'</div>';
      h+='<div style="font-size:.65rem;color:#9ca3af">'+op.date+' \u00b7 '+(op.account_label||"")+'</div></div></div>';
      h+='<div style="font-size:.78rem;font-weight:700;white-space:nowrap;margin-left:10px" class="'+(isNeg?"cell-neg":"cell-pos")+'">'+eurosDec(op.amount,true)+'</div>';
      h+='</div>';
    });
    h+='</div></div>';
  });
  if(d.total_mouvements_internes){
    h+='<div style="padding:10px 16px;background:#f7f5f0;font-size:.7rem;color:#9ca3af;text-align:center">Mouvements internes (virements/d\u00e9bits diff\u00e9r\u00e9s, hors calcul) : '+eurosDec(d.total_mouvements_internes)+'</div>';
  }
  h+='</div></div>';

  inner.innerHTML=h;

  var cats=Object.keys(d.par_categorie||{});
  var vals=cats.map(function(c){return d.par_categorie[c];});
  var palette=["#2a78d6","#eb6834","#1baf7a","#eda100","#e87ba4","#008300","#6250d6","#e34948"];
  var colors=cats.map(function(_,i){return palette[i%palette.length];});
  var total=vals.reduce(function(a,b){return a+b;},0);

  if(_pieChartInstance){_pieChartInstance.destroy();}
  var ctx=document.getElementById("depensesPie");
  if(ctx&&cats.length){
    _pieChartInstance=new Chart(ctx,{
      type:"doughnut",
      data:{labels:cats,datasets:[{data:vals,backgroundColor:colors,borderColor:"#fff",borderWidth:2}]},
      options:{responsive:true,maintainAspectRatio:false,plugins:{legend:{display:false}}}
    });
    var legendHtml="";
    cats.forEach(function(c,i){
      var pct=total>0?Math.round(vals[i]/total*100):0;
      legendHtml+='<span style="display:flex;align-items:center;gap:4px"><span style="width:10px;height:10px;border-radius:2px;background:'+colors[i]+'"></span>'+c+" "+pct+"%</span>";
    });
    document.getElementById("depensesLegend").innerHTML=legendHtml;
  }else if(document.getElementById("depensesLegend")){
    document.getElementById("depensesLegend").innerHTML='<span>Aucune donn\u00e9e pour ce mois</span>';
  }
}

function openModal(sec){modalCtx=sec;document.getElementById("modal-title").textContent=(sec==="revenus"?"Ajouter un revenu":"Ajouter une d\\u00e9pense");document.getElementById("modal-input").value="";document.getElementById("modal").style.display="flex";setTimeout(function(){document.getElementById("modal-input").focus();},50);}
function closeModal(){document.getElementById("modal").style.display="none";}
function confirmModal(){
  var name=document.getElementById("modal-input").value.trim();
  if(!name){alert("Nom requis");return;}
  var recur=document.getElementById("modal-recur").checked;
  var p=D[currentPeriod];if(!p[modalCtx])p[modalCtx]={};
  var val=parseFloat(document.getElementById("modal-amount").value)||0;
  months().forEach(function(m){
    if(!p[modalCtx][name])p[modalCtx][name]={};
    p[modalCtx][name][m]=recur?val:0;
  });
  closeModal();
  saveAll();
  if(currentMonth)renderMonthTab(currentMonthTab);else renderAnnual();
}

async function saveAll(){
  try{var r=await fetch("/api/finances/save",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(D)});var d=await r.json();toast(d.ok?"Sauvegard\\u00e9 \\u2713":"Erreur: "+(d.error||"?"));}catch(e){toast("Erreur r\\u00e9seau");}
}
function toast(msg){var t=document.getElementById("toast");t.textContent=msg;t.style.display="block";setTimeout(function(){t.style.display="none";},2500);}
document.addEventListener("keydown",function(e){if(e.key==="Escape")closeModal();if(e.key==="Enter"&&document.getElementById("modal").style.display==="flex")confirmModal();});
// Auto-snapshot mois précédent si pas encore fait
async function autoSnapshot(){
  var inv=await loadInvData();
  // Calculer le mois précédent
  var now=new Date();
  var prevMonth=new Date(now.getFullYear(),now.getMonth()-1,1);
  var pm=prevMonth.getFullYear()+'-'+(prevMonth.getMonth()+1<10?'0':'')+(prevMonth.getMonth()+1);
  var year=prevMonth.getFullYear().toString();
  if(!D[year])return;
  if(!D[year].perf_snapshot)D[year].perf_snapshot={};
  if(D[year].perf_snapshot[pm]!==undefined)return; // déjà fait
  // Intérêts livrets
  var intLivrets=0;
  Object.values(inv.livrets||{}).forEach(function(lv){
    intLivrets+=(parseFloat(lv.solde)||0)*(parseFloat(lv.taux_actuel)||0)/100/12;
  });
  // PV latentes PEA+CTO
  var pvPortfolio=0;
  ['pea','cto'].forEach(function(type){
    Object.entries(inv[type]||{}).forEach(function(e){
      var sym=e[0],pos=e[1];
      var q=parseFloat(pos.qte)||0,pru=parseFloat(pos.pru)||0;
      var q2=_quotes[sym];var prix=q2?parseFloat(q2.price):null;
      var cur=q2?q2.currency:'EUR';
      if(prix&&cur==='USD'&&_eurusd)prix=prix/_eurusd;
      if(prix&&q)pvPortfolio+=(prix-pru)*q;
    });
  });
  // PV crypto
  var pvCrypto=0;
  Object.entries(inv.crypto||{}).forEach(function(e){
    var id=e[0],pos=e[1];
    var q=parseFloat(pos.qte)||0,pru=parseFloat(pos.pru)||0;
    var cp=_crypto[id];var prix=cp?parseFloat(cp.eur):null;
    if(prix&&q)pvCrypto+=(prix-pru)*q;
  });
  D[year].perf_snapshot[pm]=Math.round(intLivrets+pvPortfolio+pvCrypto);
  saveAll();
}
Promise.all([loadInvData(),typeof loadQuotes==="function"?loadQuotes():Promise.resolve()]).then(autoSnapshot);
// Pré-remplir Performance depuis daily_pv
fetch('/data/pv_current.json').then(function(r){return r.json();})
.then(function(pv){
  if(!pv||!pv.pv_mois)return;
  var ym=_curMonthYM;
  var year=ym.slice(0,4);
  if(!D[year])return;
  if(!D[year].perf_snapshot)D[year].perf_snapshot={};
  // Seulement si pas encore saisi manuellement
  if(D[year].perf_snapshot[ym]===undefined||D[year].perf_snapshot[ym]===0){
    D[year].perf_snapshot[ym]=Math.round(pv.pv_mois.total||0);
    if(document.getElementById('view-annual').children.length)renderAnnual();
  }
}).catch(function(){});
var _savedPeriod=localStorage.getItem("fin_period");
if(_savedPeriod==="2024"||_savedPeriod==="2025"){_savedPeriod="vie";}
setPeriod(_savedPeriod||"vie");
"""
    JS=JS.replace("_DATA_",dj).replace("_VIE_",vmj).replace("_AN24_",an24j).replace("_AN25_",an25j).replace("_AN26_",an26j)
    return ("<!DOCTYPE html><html lang='fr'><head><meta charset='UTF-8'>"
        "<meta name='viewport' content='width=device-width,initial-scale=1.0'>"
        "<title>Finances</title><style>"+CSS+"</style>"
        "<script src='https://cdnjs.cloudflare.com/ajax/libs/Chart.js/4.4.1/chart.umd.js'></script>"
        "<style>"+inv_css+"</style>"
        "</head><body>"
        "<div id='app'>"
        "<header class='app-header'><div><h1>&#128176; Finances</h1><p>Revenus &middot; D&eacute;penses &middot; Investissements</p></div>"
        "</header>"
        "<div class='period-tabs'>"
        "<button class='period-tab' data-period='vie' onclick='setPeriod(\"vie\")'>G\u00e9n\u00e9ral</button>"
        "<button class='period-tab' data-period='depenses' onclick='setPeriod(\"depenses\")'>D\u00e9penses</button>"
        "<button class='period-tab' data-period='investissements' onclick='setPeriod(\"investissements\")'>Investissements</button>"
        "</div>"
        "<div class='kpis' id='kpis' style='display:flex'></div>"
        "<div id='view-annual'></div>"
        "<div id='view-monthly' style='display:none'></div>"
        "<div id='view-depenses' style='display:none'></div>"
        "<div id='view-investissements' style='display:none'></div>"
        "</div>"
        "<div class='modal-overlay' id='modal' onclick='if(event.target===this)closeModal()'>"
        "<div class='modal-box'><h3 id='modal-title'>Ajouter</h3>"
        "<div class='form-group'><label>Nom</label><input id='modal-input' class='form-group input' placeholder='Nom de la ligne'/></div>"
        "<div class='form-group'><label>Montant mensuel (optionnel)</label><input id='modal-amount' type='number' min='0' step='0.01' placeholder='0'/></div>"
        "<div class='form-group' style='display:flex;align-items:center;gap:8px'><input id='modal-recur' type='checkbox'/><label for='modal-recur' style='margin:0;cursor:pointer'>Montant récurrent (même valeur tous les mois)</label></div>"
        "<div class='modal-actions'><button class='btn btn-gray' onclick='closeModal()'>Annuler</button>"
        "<button class='btn btn-primary' onclick='confirmModal()'>Ajouter</button></div>"
        "</div></div>"
        +inv_modal+
        "<div class='toast' id='toast'></div>"
        "<script>"+JS+inv_js+"</script>"
        "</body></html>")
