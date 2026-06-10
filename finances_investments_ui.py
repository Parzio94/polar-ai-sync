"""
finances_investments_ui.py
UI pour l onglet Investissements du drill-down mensuel
"""

PEA_TITRES = [
    {"symbol":"EWLD.PA","name":"Amundi MSCI World (D)","type":"etf"},
    {"symbol":"PAEEM.PA","name":"Amundi PEA Emergent","type":"etf"},
    {"symbol":"PANQ.PA","name":"Amundi PEA Nasdaq-100","type":"etf"},
    {"symbol":"ESE.PA","name":"BNP Easy S&P 500","type":"etf"},
    {"symbol":"AIR.PA","name":"Airbus","type":"action"},
    {"symbol":"MC.PA","name":"LVMH","type":"action"},
    {"symbol":"TTE.PA","name":"TotalEnergies","type":"action"},
    {"symbol":"BNP.PA","name":"BNP Paribas","type":"action"},
    {"symbol":"SAF.PA","name":"Safran","type":"action"},
    {"symbol":"SGO.PA","name":"Saint-Gobain","type":"action"},
    {"symbol":"SU.PA","name":"Schneider Electric","type":"action"},
    {"symbol":"SOI.PA","name":"Soitec","type":"action"},
    {"symbol":"HO.PA","name":"Thales","type":"action"},
    {"symbol":"VU.PA","name":"Vusion","type":"action"},
]
CTO_TITRES = [
    {"symbol":"005930.KS","name":"Samsung"},
    {"symbol":"IGLN.L","name":"Or (iShares)"},
    {"symbol":"ISLN.L","name":"Argent (iShares)"},
    {"symbol":"MSFT","name":"Microsoft"},
    {"symbol":"CVX","name":"Chevron"},
    {"symbol":"XOM","name":"ExxonMobil"},
    {"symbol":"NVDA","name":"NVIDIA"},
    {"symbol":"BLK","name":"BlackRock"},
    {"symbol":"MA","name":"Mastercard"},
    {"symbol":"V","name":"Visa"},
    {"symbol":"ORCL","name":"Oracle"},
    {"symbol":"AMD","name":"AMD"},
]
CRYPTO_TITRES = [
    {"id":"bitcoin","symbol":"BTC","name":"Bitcoin"},
    {"id":"ethereum","symbol":"ETH","name":"Ethereum"},
    {"id":"solana","symbol":"SOL","name":"Solana"},
]
LIVRETS = [
    {"id":"livret_a","name":"Livret A LCL","taux_defaut":1.5},
    {"id":"ldds","name":"LDDS LCL","taux_defaut":1.5},
    {"id":"livret_jeune","name":"Livret Jeune LCL","taux_defaut":1.5},
    {"id":"tr_livret","name":"TR Livret","taux_defaut":2.0},
]

def investments_js():
    """Retourne le JS de l onglet investissements."""
    pea_json = __import__("json").dumps(PEA_TITRES, ensure_ascii=False)
    cto_json = __import__("json").dumps(CTO_TITRES, ensure_ascii=False)
    crypto_json = __import__("json").dumps(CRYPTO_TITRES, ensure_ascii=False)
    livrets_json = __import__("json").dumps(LIVRETS, ensure_ascii=False)

    js = "var PEA_TITRES=" + pea_json + ";"
    js += "var CTO_TITRES=" + cto_json + ";"
    js += "var CRYPTO_TITRES=" + crypto_json + ";"
    js += "var LIVRETS_DEF=" + livrets_json + ";"
    js += r"""
var INV={};
var _quotes={};
var _crypto={};
var _eurusd=1.0;
var _quotesLoaded=false;

async function loadInvestments(){
  await loadQuotes();
  try{
    var r=await fetch("/api/finances/investments");
    var d=await r.json();
    INV=d;
  }catch(e){INV={};}
}

async function loadQuotes(){
  var allSyms=PEA_TITRES.map(function(t){return t.symbol;}).concat(CTO_TITRES.map(function(t){return t.symbol;}));
  try{
    var r=await fetch("/api/finances/quotes?symbols="+allSyms.join(","));
    var d=await r.json();
    // API retourne {symbol: price} directement
    var quotes={};
    var usdSyms=['MSFT','NVDA','BLK','MA','V','ORCL','AMD','CVX','XOM','IGLN.L','ISLN.L'];
    var krwSyms=['005930.KS'];
    if(d['__eurusd'])_eurusd=d['__eurusd'];
    Object.keys(d).forEach(function(sym){
      if(sym==='__eurusd')return;
      if(d[sym]!=null){
        var cur='EUR';
        if(usdSyms.indexOf(sym)>=0)cur='USD';
        else if(krwSyms.indexOf(sym)>=0)cur='KRW';
        quotes[sym]={price:d[sym],currency:cur};
      }
    });
    _quotes=quotes;
  }catch(e){}
  try{
    var r2=await fetch("/api/finances/crypto?ids=bitcoin,ethereum,solana");
    var d2=await r2.json();
    // CoinGecko retourne {bitcoin:{eur:45000},...}
    var prices={};
    Object.keys(d2).forEach(function(id){if(d2[id]&&d2[id].eur)prices[id]={eur:d2[id].eur};});
    _crypto=prices;
  }catch(e){}
  _quotesLoaded=true;
}

async function saveInvestments(){
  try{
    var r=await fetch("/api/finances/investments",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify(INV)});
    var d=await r.json();
    toast(d.ok?"Investi. sauvegard\u00e9s":"Erreur: "+d.error);
  }catch(e){toast("Erreur r\u00e9seau");}
}

function renderInvestments(){
  var h="";

  h+='<div class="inv-actions">';
  h+='';
  h+='<button class="btn btn-gray" onclick="openBuyModal()">+ Achat</button>';
  h+='</div>';
  h+=renderLivrets();
  h+=renderPortfolio("pea","&#127467;&#127479; PEA Boursorama",PEA_TITRES,"EUR");
  h+=renderPortfolio("cto","&#127482;&#127480; CTO Trade Republic",CTO_TITRES,"USD");
  h+=renderCrypto();
  h+=renderSCPI();
  h+=renderAutresProduits();
  return h;
}
function renderAutresProduits(){
  var ap=INV.autres_produits||{};
  var today=new Date().toISOString().slice(0,10);
  var defs=[
    {id:'ccb',name:'CCB Malakoff',ico:'🏢',type:'Épargne salariale'},
    {id:'assurance_vie',name:'Assurance Vie',ico:'🛡️',type:'AV'},
    {id:'per',name:'PER',ico:'🎯',type:'Retraite'},
  ];
  var h='<div class="section"><div class="section-head"><h3>💼 Autres produits</h3></div>';
  h+='<table style="width:100%;border-collapse:collapse">';
  h+='<thead><tr style="background:#f7f5f0">';
  h+='<th style="text-align:left;padding:5px 8px;font-size:.62rem">Produit</th>';
  h+='<th style="padding:5px 8px;font-size:.62rem">Solde</th>';
  h+='<th style="padding:5px 8px;font-size:.62rem">Rdt %</th>';
  h+='<th style="padding:5px 8px;font-size:.62rem">Rev./mois</th>';
  h+='</tr></thead><tbody>';
  var totSolde=0;
  defs.forEach(function(d){
    var pos=ap[d.id]||{solde:0,rendement:2.5};
    var solde=parseFloat(pos.solde)||0;
    var rdt=parseFloat(pos.rendement)||parseFloat(pos.taux_actuel)||0;
    var rev=solde*rdt/100/12;
    totSolde+=solde;
    h+='<tr style="border-bottom:1px solid #f0ede8">';
    h+='<td style="padding:5px 8px"><strong>'+d.ico+' '+d.name+'</strong><br><span style="font-size:.6rem;color:#9ca3af">'+d.type+'</span></td>';
    h+='<td style="text-align:right;padding:5px 4px"><input type="number" step="0.01" class="cell-input wide" value="'+(solde||'')+'" oninput="setAutre(\''+d.id+'\',\'solde\',this.value)" style="width:90px"/>€</td>';
    h+='<td style="text-align:right;padding:5px 4px"><input type="number" step="0.1" class="cell-input" value="'+(rdt||'')+'" oninput="setAutre(\''+d.id+'\',\'rendement\',this.value)" style="width:60px"/>%</td>';
    h+='<td style="text-align:right;padding:5px 8px;font-weight:800;color:#2d6a4f">'+(rev>0?Math.round(rev).toLocaleString('fr-FR')+'€':'—')+'</td>';
    h+='</tr>';
  });
  h+='<tr style="background:#eff6ff;font-weight:800"><td style="padding:5px 8px;font-size:.72rem">Total</td>';
  h+='<td style="text-align:right;padding:5px 8px;color:#1565c0">'+Math.round(totSolde).toLocaleString('fr-FR')+'€</td><td></td><td></td></tr>';
  h+='</tbody></table></div>';
  return h;
}
function setAutre(id,field,val){
  if(!INV.autres_produits)INV.autres_produits={};
  if(!INV.autres_produits[id])INV.autres_produits[id]={solde:0,rendement:2.5};
  INV.autres_produits[id][field]=parseFloat(val)||0;
  clearTimeout(window._invSvt);window._invSvt=setTimeout(saveInvestments,600);
}
function renderSCPI(){
  var scpi=INV.scpi||{};
  var today=new Date().toISOString().slice(0,10);
  // Alerte expiration dans 30 jours
  var in30=new Date();in30.setDate(in30.getDate()+30);var in30s=in30.toISOString().slice(0,10);
  Object.values(INV.scpi||{}).forEach(function(b){
    if(b.date_fin&&b.date_fin>=today&&b.date_fin<=in30s){
      console.warn('Bricks expiration proche:',b.nom,b.date_fin);
    }
  });
  // Filtrer logements actifs (date_fin pas encore passée)
  var logements=Object.values(scpi).filter(function(b){
    return !b.date_fin||b.date_fin>=today;
  });
  var totVal=0,totRev=0;
  var liqBricks=parseFloat((INV.liquidites_bricks||{}).montant)||0;
  var h='<div class="section"><div class="section-head"><h3>🏠 Immobilier / Bricks.fr</h3>';
  h+='<button onclick="addBrick()" style="background:#fff;border:none;border-radius:6px;padding:3px 10px;font-size:.65rem;font-weight:700;cursor:pointer;color:#1a1a2e">+ Ajouter</button>';
  h+='</div>';
  h+='<table style="width:100%;border-collapse:collapse">';
  h+='<thead><tr style="background:#f7f5f0">';
  h+='<th style="text-align:left;padding:5px 8px;font-size:.62rem">Logement</th>';
  h+='<th style="padding:5px 8px;font-size:.62rem">Valeur</th>';
  h+='<th style="padding:5px 8px;font-size:.62rem">Rdt %</th>';
  h+='<th style="padding:5px 8px;font-size:.62rem">Rev./mois</th>';
  h+='<th style="padding:5px 8px;font-size:.62rem">Achat</th>';
  h+='<th style="padding:5px 8px;font-size:.62rem">Fin</th>';
  h+='<th></th>';
  h+='</tr></thead><tbody>';
  logements.forEach(function(b){
    var val=parseFloat(b.valeur)||0;
    var rdt=parseFloat(b.rendement)||5.5;
    var rev=val*rdt/100/12;
    totVal+=val;totRev+=rev;
    var id=b.id||b.nom;
    h+='<tr style="border-bottom:1px solid #f0ede8">';
    var expireSoon=b.date_fin&&b.date_fin>=today&&b.date_fin<=in30s;
    h+='<td style="padding:5px 8px;font-size:.75rem;font-weight:700">'+b.nom+(expireSoon?' <span style="background:#ffc107;color:#1a1a2e;border-radius:4px;padding:1px 5px;font-size:.6rem">⚠️ expire bientôt</span>':'')+'</td>';
    h+='<td style="text-align:right;padding:5px 4px"><input type="number" step="0.01" class="cell-input" style="width:80px" value="'+(val||'')+'" oninput="setBrick(\''+id+'\',\'valeur\',this.value)"/>€</td>';
    h+='<td style="text-align:right;padding:5px 4px"><input type="number" step="0.1" class="cell-input" style="width:55px" value="'+(rdt||'')+'" oninput="setBrick(\''+id+'\',\'rendement\',this.value)"/>%</td>';
    h+='<td style="text-align:right;padding:5px 8px;color:#2d6a4f;font-weight:700">'+(rev>0?Math.round(rev)+'€':'—')+'</td>';
    h+='<td style="text-align:right;padding:5px 8px;font-size:.65rem;color:#9ca3af">'+(b.date_achat||'—')+'</td>';
    h+='<td style="text-align:right;padding:5px 4px"><input type="date" class="cell-input" style="width:110px" value="'+(b.date_fin||'')+'" oninput="setBrick(\''+id+'\',\'date_fin\',this.value)"/></td>';
    h+='<td><button onclick="deleteBrick(\''+id+'\')" style="border:none;background:none;color:#e63946;cursor:pointer">✕</button></td>';
    h+='</tr>';
  });
  if(!logements.length)h+='<tr><td colspan="7" style="text-align:center;padding:12px;color:#9ca3af;font-size:.75rem">Aucun logement actif</td></tr>';
  h+='<tr style="border-bottom:1px solid #f0ede8">';
  h+='<td style="padding:5px 8px;font-size:.75rem;color:#6b7280">💶 Liquidités Bricks</td>';
  h+='<td style="text-align:right;padding:5px 4px"><input type="number" step="0.01" class="cell-input" style="width:80px" value="'+(liqBricks||'')+'" oninput="setLiqBricks(this.value)"/>€</td>';
  h+='<td></td><td></td><td></td><td></td><td></td></tr>';
  h+='<tr style="background:#eff6ff;font-weight:800"><td style="padding:5px 8px">Total</td>';
  h+='<td style="text-align:right;padding:5px 8px;color:#1565c0">'+Math.round(totVal+liqBricks)+'€</td>';
  h+='<td></td><td style="text-align:right;padding:5px 8px;color:#2d6a4f">'+Math.round(totRev)+'€/mois</td>';
  h+='<td></td><td></td><td></td></tr>';
  h+='</tbody></table></div>';
  return h;
}
function addBrick(){
  var nom=prompt("Nom du logement (ex: Bordeaux T2)");
  if(!nom)return;
  var achat=prompt("Date d'achat (YYYY-MM-DD)","2026-01-01");
  var id='brick_'+Date.now();
  if(!INV.scpi)INV.scpi={};
  INV.scpi[id]={id:id,nom:nom,valeur:0,rendement:5.5,date_achat:achat||'',date_fin:''};
  saveInvestments().then(function(){
    if(typeof renderMonthTab==="function")renderMonthTab("inv");
    else{var el=document.getElementById("month-tab-content");if(el)el.innerHTML=renderInvestments();}
  });
}
function setBrick(id,field,val){
  if(!INV.scpi||!INV.scpi[id])return;
  INV.scpi[id][field]=field==='valeur'||field==='rendement'?parseFloat(val)||0:val;
  clearTimeout(window._invSvt);window._invSvt=setTimeout(saveInvestments,600);
}
function deleteBrick(id){
  if(!confirm("Supprimer ce logement ?"))return;
  if(INV.scpi&&INV.scpi[id])delete INV.scpi[id];
  saveInvestments().then(function(){
    if(typeof renderMonthTab==="function")renderMonthTab("inv");
    else{var el=document.getElementById("month-tab-content");if(el)el.innerHTML=renderInvestments();}
  });
}
function setLiqBricks(val){
  if(!INV.liquidites_bricks)INV.liquidites_bricks={};
  INV.liquidites_bricks.montant=parseFloat(val)||0;
  clearTimeout(window._invSvt);window._invSvt=setTimeout(saveInvestments,600);
}
function setSCPI(id,field,val){
  if(!INV.scpi)INV.scpi={};
  if(!INV.scpi[id])INV.scpi[id]={valeur:0,nb_parts:0,rendement:5.5};
  INV.scpi[id][field]=parseFloat(val)||0;
  clearTimeout(window._invSvt);window._invSvt=setTimeout(saveInvestments,600);
}

function renderLivrets(){
  var livrets=(INV.livrets||{});
  var h='<div class="section"><div class="section-head"><h3>&#127970; Livrets</h3></div>';
  h+='<table><thead><tr><th>Livret</th><th>Solde</th><th>Taux %</th><th>Int\u00e9r\u00eats/mois</th><th>Historique</th></tr></thead><tbody>';
  var totSolde=0,totInt=0;
  LIVRETS_DEF.forEach(function(l){
    var pos=livrets[l.id]||{solde:0,taux_actuel:l.taux_defaut};
    var solde=parseFloat(pos.solde)||0;
    var taux=parseFloat(pos.taux_actuel)||l.taux_defaut;
    var inter=solde*taux/100/12;
    totSolde+=solde;totInt+=inter;
    h+='<tr>';
    h+='<td><strong>'+l.name+'</strong></td>';
    h+='<td><input type="number" class="cell-input wide" value="'+(solde||"")+'" oninput="setLivret(\''+l.id+'\',\'solde\',this.value)"/></td>';
    h+='<td><input type="number" step="0.1" class="cell-input" value="'+(taux||"")+'" oninput="setLivret(\''+l.id+'\',\'taux\',this.value)"/> %</td>';
    h+='<td class="green"><strong>'+(inter?Math.round(inter).toLocaleString("fr-FR")+"\u20ac":"\u2014")+'</strong></td>';
    h+='<td><button class="btn-xs" style="background:#e8e4dc" onclick="showTauxHistory(\''+l.id+'\')">&#128203;</button></td>';
    h+='</tr>';
  });
  h+='<tr class="total-row"><td><strong>Total</strong></td>';
  h+='<td class="total-cell"><strong>'+Math.round(totSolde).toLocaleString("fr-FR")+"\u20ac"+'</strong></td>';
  h+='<td></td><td class="green"><strong>'+Math.round(totInt).toLocaleString("fr-FR")+"\u20ac/mois"+'</strong></td><td></td></tr>';
  h+='</tbody></table></div>';
  return h;
}

function showHistory(type,sym){
  var pos=(INV[type]||{})[sym]||{};
  var achats=pos.achats||[];
  var qte=parseFloat(pos.qte)||0;
  var pru=parseFloat(pos.pru)||0;
  var q2=_quotes[sym];var prix=q2?parseFloat(q2.price):null;
  var cur=q2?q2.currency:'EUR';
  if(prix&&cur==='USD'&&_eurusd)prix=prix/_eurusd;
  var pv=prix&&qte?Math.round(qte*prix-qte*pru):null;
  var pvp=pru>0&&pv!=null?(pv/(qte*pru)*100).toFixed(1):null;
  var msg=sym+' — '+qte+' parts @ PRU '+pru+'€\n';
  msg+='Valeur: '+(prix?Math.round(qte*prix)+'€':'N/A')+'\n';
  msg+='PV latente: '+(pv!=null?(pv>=0?'+':'')+pv+'€ ('+pvp+'%)':'N/A')+'\n\n';
  if(achats.length){
    msg+='Historique achats:\n';
    achats.forEach(function(a){
      msg+='  '+a.date+' — '+a.qte+' parts @ '+a.prix+'€ ('+a.montant+'€)\n';
    });
  }else{msg+='Aucun historique d\'achat enregistré';}
  alert(msg);
}
function setLiquidites(val){
  if(!INV.liquidites)INV.liquidites={};
  INV.liquidites.montant=parseFloat(val)||0;
  clearTimeout(window._invSvt);window._invSvt=setTimeout(saveInvestments,600);
}
function setPos(type,symbol,field,val){
  if(!INV[type])INV[type]={};
  if(!INV[type][symbol])INV[type][symbol]={qte:0,pru:0,achats:[],dividende_annuel:0};
  INV[type][symbol][field]=parseFloat(val)||0;
  clearTimeout(window._invSvt);window._invSvt=setTimeout(saveInvestments,600);
}
function setCrypto(id,field,val){
  if(!INV.crypto)INV.crypto={};
  if(!INV.crypto[id])INV.crypto[id]={qte:0,pru:0};
  INV.crypto[id][field]=parseFloat(val)||0;
  clearTimeout(window._invSvt);window._invSvt=setTimeout(saveInvestments,600);
}
function setLivret(id,field,val){
  if(!INV.livrets)INV.livrets={};
  if(!INV.livrets[id])INV.livrets[id]={solde:0,taux_actuel:0,historique_taux:[]};
  if(field==="solde"){INV.livrets[id].solde=parseFloat(val)||0;clearTimeout(window._invSvt);window._invSvt=setTimeout(saveInvestments,600);}
  else if(field==="taux"){
    var old=INV.livrets[id].taux_actuel;
    var nw=parseFloat(val)||0;
    if(old!==nw){
      if(!INV.livrets[id].historique_taux)INV.livrets[id].historique_taux=[];
      var today=new Date().toISOString().slice(0,10);
      INV.livrets[id].historique_taux.push({taux:old,date_fin:today});
      INV.livrets[id].taux_actuel=nw;
    }
  }
}

function showTauxHistory(id){
  var pos=(INV.livrets||{})[id]||{};
  var hist=pos.historique_taux||[];
  var txt=hist.length?hist.map(function(h){return h.taux+"% jusqu au "+h.date_fin;}).join("\n"):"Aucun historique";
  alert("Historique taux:\n"+txt);
}

function renderPortfolio(type,title,titres,currency){
  var portfolio=(INV[type]||{});
  var rows=[];
  titres.forEach(function(t){
    var pos=portfolio[t.symbol]||{qte:0,pru:0,achats:[],dividende_annuel:0};
    var qte=parseFloat(pos.qte)||0,pru=parseFloat(pos.pru)||0;
    var q=_quotes[t.symbol];
    var prix=q?parseFloat(q.price):null;
    var cur=q?q.currency:"EUR";
    var prixEur=prix;
    if(prix&&cur==="USD"&&_eurusd)prixEur=prix/_eurusd;
    if(prix&&cur==="KRW")prixEur=prix/1300;
    var valeur=prixEur!=null&&qte>0?qte*prixEur:null;
    var investi=qte*pru;
    var pv=valeur!=null?valeur-investi:null;
    var pvp=investi>0&&pv!=null?pv/investi*100:null;
    rows.push({t:t,qte:qte,pru:pru,prixEur:prixEur,valeur:valeur,investi:investi,pv:pv,pvp:pvp,pos:pos});
  });
  // Tri par valeur desc
  rows.sort(function(a,b){return (b.valeur||0)-(a.valeur||0);});
  var totVal=0,totInv=0;
  rows.forEach(function(r){if(r.valeur)totVal+=r.valeur;if(r.investi)totInv+=r.investi;});
  var h='<div class="section"><div class="section-head"><h3>'+title+'</h3>';
  if(currency==="USD"&&_eurusd!=null)h+='<span style="font-size:.68rem;color:#9ca3af;margin-left:8px">EUR/USD: '+_eurusd.toFixed(4)+'</span>';
  h+='</div>';
  // Liquidités dans PEA uniquement
  if(type==="pea"){
    var liq=parseFloat((INV.liquidites||{}).montant)||0;
    h+='<div style="display:flex;align-items:center;gap:10px;padding:8px 14px;background:#eff6ff;border-bottom:1px solid #e8e4dc">';
    h+='<span style="font-size:.75rem;font-weight:700;flex:1">💶 Liquidités PEA</span>';
    h+='<input type="number" step="0.01" class="cell-input wide" value="'+(liq||'')+'" oninput="setLiquidites(this.value)" style="width:100px"/>';
    h+='<span style="font-size:.8rem;font-weight:800;color:#1565c0;width:80px;text-align:right">'+Math.round(liq).toLocaleString('fr-FR')+'€</span>';
    h+='</div>';
  }
  h+='<table style="width:100%;border-collapse:collapse">';
  h+='<thead><tr style="background:#f7f5f0"><th style="text-align:left;padding:5px 8px;font-size:.62rem">Titre</th><th style="padding:5px 8px;font-size:.62rem">Prix</th><th style="padding:5px 8px;font-size:.62rem">Qté</th><th style="padding:5px 8px;font-size:.62rem">PRU</th><th style="padding:5px 8px;font-size:.62rem">Valeur</th><th style="padding:5px 8px;font-size:.62rem">+/-</th><th></th></tr></thead><tbody>';
  rows.forEach(function(r){
    var pvCls=r.pv!=null?(r.pv>=0?"cell-pos":"cell-neg"):"";
    h+='<tr style="border-bottom:1px solid #f0ede8">';
    h+='<td style="padding:5px 8px"><strong style="font-size:.75rem">'+r.t.name+'</strong><br><span style="font-size:.6rem;color:#9ca3af">'+r.t.symbol+'</span></td>';
    h+='<td style="text-align:right;padding:5px 8px;font-size:.72rem">'+(r.prixEur!=null?r.prixEur.toLocaleString("fr-FR",{minimumFractionDigits:2,maximumFractionDigits:2})+'€':'—')+'</td>';
    h+='<td style="text-align:right;padding:5px 4px"><input type="number" step="0.001" class="cell-input" style="width:70px" value="'+(r.qte||'')+'" oninput="setPos(\''+type+'\',\''+r.t.symbol+'\',\'qte\',this.value)"/></td>';
    h+='<td style="text-align:right;padding:5px 4px"><input type="number" step="0.01" class="cell-input" style="width:70px" value="'+(r.pru||'')+'" oninput="setPos(\''+type+'\',\''+r.t.symbol+'\',\'pru\',this.value)"/>€</td>';
    h+='<td style="text-align:right;padding:5px 8px;font-weight:800;font-size:.75rem;color:#1565c0">'+(r.valeur!=null?Math.round(r.valeur).toLocaleString("fr-FR")+'€':'—')+'</td>';
    h+='<td style="text-align:right;padding:5px 8px;font-size:.72rem" class="'+pvCls+'">'+(r.pv!=null?(r.pv>=0?'+':'')+Math.round(r.pv).toLocaleString("fr-FR")+'€'+(r.pvp!=null?' ('+(r.pvp>=0?'+':'')+r.pvp.toFixed(1)+'%)':''):'—')+'</td>';
    h+='<td style="text-align:center;padding:5px 4px"><button onclick="showHistory(\''+type+'\',\''+r.t.symbol+'\')" style="border:none;background:none;cursor:pointer;font-size:.8rem" title="Historique">📋</button></td>';
    h+='</tr>';
  });
  var gPv=totVal-totInv,gPvp=totInv>0?gPv/totInv*100:0;
  h+='<tr style="background:#eff6ff;font-weight:800"><td style="padding:5px 8px;font-size:.72rem">Total</td><td></td><td></td><td></td>';
  h+='<td style="text-align:right;padding:5px 8px;font-size:.75rem;color:#1565c0">'+Math.round(totVal).toLocaleString("fr-FR")+'€</td>';
  h+='<td style="text-align:right;padding:5px 8px;font-size:.72rem" class="'+(gPv>=0?"cell-pos":"cell-neg")+'">'+(gPv>=0?'+':'')+Math.round(gPv).toLocaleString("fr-FR")+'€</td></tr>';
  h+='</tbody></table></div>';
  return h;
}

function renderCrypto(){
  var portfolio=(INV.crypto||{});
  var rows=[];
  CRYPTO_TITRES.forEach(function(t){
    var pos=portfolio[t.id]||{qte:0,pru:0};
    var qte=parseFloat(pos.qte)||0,pru=parseFloat(pos.pru)||0;
    var cp=_crypto[t.id];
    var prix=cp?parseFloat(cp.eur):null;
    var chg24=cp?parseFloat(cp.eur_24h_change||0):null;
    var valeur=prix!=null&&qte>0?qte*prix:null;
    var investi=qte*pru;
    var pv=valeur!=null?valeur-investi:null;
    var pvp=investi>0&&pv!=null?pv/investi*100:null;
    rows.push({t:t,qte:qte,pru:pru,prix:prix,chg24:chg24,valeur:valeur,investi:investi,pv:pv,pvp:pvp});
  });
  rows.sort(function(a,b){return (b.valeur||0)-(a.valeur||0);});
  var totVal=0,totInv=0;
  rows.forEach(function(r){if(r.valeur)totVal+=r.valeur;if(r.investi)totInv+=r.investi;});
  var h='<div class="section"><div class="section-head"><h3>₿ Crypto</h3></div>';
  h+='<table style="width:100%;border-collapse:collapse">';
  h+='<thead><tr style="background:#f7f5f0"><th style="text-align:left;padding:5px 8px;font-size:.62rem">Crypto</th><th style="padding:5px 8px;font-size:.62rem">Prix</th><th style="padding:5px 8px;font-size:.62rem">Qté</th><th style="padding:5px 8px;font-size:.62rem">PRU</th><th style="padding:5px 8px;font-size:.62rem">Valeur</th><th style="padding:5px 8px;font-size:.62rem">+/-</th></tr></thead><tbody>';
  rows.forEach(function(r){
    var pvCls=r.pv!=null?(r.pv>=0?"cell-pos":"cell-neg"):"";
    h+='<tr style="border-bottom:1px solid #f0ede8">';
    h+='<td style="padding:5px 8px"><strong style="font-size:.75rem">'+r.t.name+'</strong><br><span style="font-size:.6rem;color:#9ca3af">'+r.t.symbol+(r.chg24!=null&&!isNaN(r.chg24)?' · <span style="color:'+(r.chg24>=0?"#2d6a4f":"#e63946")+'">'+(r.chg24>=0?'+':'')+r.chg24.toFixed(2)+'%</span>':'')+'</span></td>';
    h+='<td style="text-align:right;padding:5px 8px;font-size:.72rem">'+(r.prix!=null?r.prix.toLocaleString("fr-FR",{minimumFractionDigits:2,maximumFractionDigits:2})+'€':'—')+'</td>';
    h+='<td style="text-align:right;padding:5px 4px"><input type="number" step="0.000001" class="cell-input" style="width:80px" value="'+(r.qte||'')+'" oninput="setCrypto(\''+r.t.id+'\',\'qte\',this.value)"/></td>';
    h+='<td style="text-align:right;padding:5px 4px"><input type="number" step="0.01" class="cell-input" style="width:70px" value="'+(r.pru||'')+'" oninput="setCrypto(\''+r.t.id+'\',\'pru\',this.value)"/>€</td>';
    h+='<td style="text-align:right;padding:5px 8px;font-weight:800;font-size:.75rem;color:#1565c0">'+(r.valeur!=null?Math.round(r.valeur).toLocaleString("fr-FR")+'€':'—')+'</td>';
    h+='<td style="text-align:right;padding:5px 8px;font-size:.72rem" class="'+pvCls+'">'+(r.pv!=null?(r.pv>=0?'+':'')+Math.round(r.pv).toLocaleString("fr-FR")+'€'+(r.pvp!=null&&!isNaN(r.pvp)?' ('+(r.pvp>=0?'+':'')+r.pvp.toFixed(2)+'%)':''):'—')+'</td>';
    h+='</tr>';
  });
  var gPv=totVal-totInv,gPvp=totInv>0?gPv/totInv*100:0;
  h+='<tr style="background:#eff6ff;font-weight:800"><td style="padding:5px 8px;font-size:.72rem">Total</td><td></td><td></td><td></td>';
  h+='<td style="text-align:right;padding:5px 8px;font-size:.75rem;color:#1565c0">'+Math.round(totVal).toLocaleString("fr-FR")+'€</td>';
  h+='<td style="text-align:right;padding:5px 8px;font-size:.72rem" class="'+(gPv>=0?"cell-pos":"cell-neg")+'">'+(gPv>=0?'+':'')+Math.round(gPv).toLocaleString("fr-FR")+'€</td></tr>';
  h+='</tbody></table></div>';
  return h;
}

async function refreshQuotes(){
  toast("Chargement cours...");
  await loadQuotes();
  if(currentMonthTab==="inv")renderMonthTab("inv");
  toast("Cours mis \u00e0 jour");
}

// ── Modal achat ───────────────────────────────────────────────
var _buyModal={};
function openBuyModal(){
  _buyModal={};
  document.getElementById("buy-modal").style.display="flex";
  document.getElementById("buy-symbol").value="";
  document.getElementById("buy-montant").value="";
  document.getElementById("buy-date").value=new Date().toISOString().slice(0,10);
  document.getElementById("buy-heure").value="";
  document.getElementById("buy-portfolio").value="pea";
  document.getElementById("buy-result").textContent="";
}
function closeBuyModal(){document.getElementById("buy-modal").style.display="none";}
async function confirmBuy(){
  var sym=document.getElementById("buy-symbol").value.trim().toUpperCase();
  var montant=parseFloat(document.getElementById("buy-montant").value);
  var date=document.getElementById("buy-date").value;
  var heure=document.getElementById("buy-heure").value;
  var portfolio=document.getElementById("buy-portfolio").value;
  if(!sym||!montant){alert("Symbole et montant requis");return;}
  document.getElementById("buy-result").textContent="Enregistrement...";
  try{
    var r=await fetch("/api/finances/buy",{method:"POST",headers:{"Content-Type":"application/json"},
      body:JSON.stringify({portfolio:portfolio,symbol:sym,montant:montant,date:date,heure:heure})});
    var d=await r.json();
    if(d.ok){
      await loadInvestments();
      document.getElementById("buy-result").textContent="Achet\u00e9: "+d.qte.toFixed(4)+" parts @ "+d.cours.toFixed(2)+"\u20ac (PRU: "+d.pru.toFixed(2)+"\u20ac)";
      renderMonthTab("inv");
    }else{document.getElementById("buy-result").textContent="Erreur: "+d.error;}
  }catch(e){document.getElementById("buy-result").textContent="Erreur r\u00e9seau";}
}
"""
    return js

def investments_css():
    return """
.inv-actions{display:flex;gap:8px;padding:10px 20px;flex-wrap:wrap;align-items:center;margin-bottom:4px}
.cards-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(220px,1fr));gap:12px;padding:14px}
.inv-card{border:1px solid #e8e4dc;border-radius:12px;padding:14px;background:#fff;transition:box-shadow .15s}
.inv-card:hover{box-shadow:0 4px 12px rgba(0,0,0,.08)}
.card-header{display:flex;justify-content:space-between;align-items:center;margin-bottom:8px}
.card-name{font-weight:800;font-size:.78rem}
.card-symbol{font-size:.65rem;color:#6b7280;background:#f0ede8;padding:2px 6px;border-radius:8px}
.card-price{font-size:1rem;font-weight:900;margin-bottom:10px;color:#1a1a2e}
.card-details{border-top:1px solid #f0ede8;padding-top:8px}
.card-row{display:flex;justify-content:space-between;align-items:center;padding:3px 0;font-size:.72rem}
.card-row span:first-child{color:#6b7280}
.card-input{width:80px;border:1px solid #e8e4dc;border-radius:4px;padding:2px 5px;text-align:right;font-size:.72rem}
.card-input:focus{outline:none;border-color:#1565c0}
.pnl-block{margin-top:10px;padding:8px 12px;border-radius:8px;font-weight:800;font-size:.82rem;text-align:center}
.pnl-pos{background:#f0fdf4;color:#2d6a4f}
.pnl-neg{background:#fff5f5;color:#e63946}
.pnl-zero{background:#f7f5f0;color:#6b7280}
.portfolio-total{display:flex;gap:20px;padding:10px 16px;border-top:1px solid #f0ede8;background:#fafaf8;font-size:.78rem;flex-wrap:wrap}
"""

def investments_modal_html():
    return """
<div class="modal-overlay" id="buy-modal" onclick="if(event.target===this)closeBuyModal()">
  <div class="modal-box" style="width:400px">
    <h3>Enregistrer un achat</h3>
    <div class="form-group">
      <label>Portefeuille</label>
      <select id="buy-portfolio" style="width:100%;border:1px solid #e8e4dc;border-radius:8px;padding:8px">
        <option value="pea">PEA Boursorama</option>
        <option value="cto">CTO Trade Republic</option>
        <option value="crypto">Crypto</option>
      </select>
    </div>
    <div class="form-group">
      <label>Symbole (ex: AIR.PA, NVDA, bitcoin)</label>
      <input type="text" id="buy-symbol" placeholder="AIR.PA" style="text-transform:uppercase"/>
    </div>
    <div class="form-group">
      <label>Montant investi (€)</label>
      <input type="number" id="buy-montant" placeholder="500"/>
    </div>
    <div style="display:flex;gap:8px">
      <div class="form-group" style="flex:1">
        <label>Date</label>
        <input type="date" id="buy-date"/>
      </div>
      <div class="form-group" style="flex:1">
        <label>Heure (optionnel)</label>
        <input type="time" id="buy-heure"/>
      </div>
    </div>
    <div id="buy-result" style="font-size:.75rem;color:#2d6a4f;min-height:20px;margin-top:4px"></div>
    <div class="modal-actions">
      <button class="btn btn-gray" onclick="closeBuyModal()">Annuler</button>
      <button class="btn btn-primary" onclick="confirmBuy()">Enregistrer</button>
    </div>
  </div>
</div>
"""
