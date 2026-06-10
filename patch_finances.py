src = open("/root/polar/finances_module.py", encoding="utf-8").read()
results = []

# 1. Ajouter 2026 dans AN_MONTHS + démarrer sur mois actuel
old_var = 'var AN_MONTHS={"2024":_AN24_,"2025":_AN25_};\nvar currentPeriod="2025",currentMonth=null,modalCtx=null,currentMonthTab="rd";'
new_var = ('var AN_MONTHS={"2024":_AN24_,"2025":_AN25_,"2026":_AN26_};\n'
           'var now=new Date(),currentYear=now.getFullYear().toString();\n'
           'var currentPeriod=currentYear,currentMonth=null,modalCtx=null,currentMonthTab="rd";\n'
           'var _curMonthYM=now.getFullYear()+"-"+(now.getMonth()+1<10?"0":"")+(now.getMonth()+1);')
if old_var in src:
    src = src.replace(old_var, new_var, 1)
    results.append("OK 1 AN_MONTHS + currentYear")
else:
    results.append("SKIP 1")

# 2. Ajouter 2026 dans les données JS (après an25j)
old_data = 'var AN_MONTHS={"2024":_AN24_,"2025":_AN25_,"2026":_AN26_};'
# Ajouter an26j dans build_finances_page
old_an25 = "    an25j=json.dumps(months_of_year(2025))\n"
new_an25 = "    an25j=json.dumps(months_of_year(2025))\n    an26j=json.dumps(months_of_year(2026))\n"
if old_an25 in src:
    src = src.replace(old_an25, new_an25, 1)
    results.append("OK 2a an26j variable")
else:
    results.append("SKIP 2a")

old_replace = 'JS=JS.replace("_DATA_",dj).replace("_VIE_",vmj).replace("_AN24_",an24j).replace("_AN25_",an25j)'
new_replace = 'JS=JS.replace("_DATA_",dj).replace("_VIE_",vmj).replace("_AN24_",an24j).replace("_AN25_",an25j).replace("_AN26_",an26j)'
if old_replace in src:
    src = src.replace(old_replace, new_replace, 1)
    results.append("OK 2b replace an26j")
else:
    results.append("SKIP 2b")

# 3. Highlight mois actuel dans renderAnnual
old_monthly = "var monthly={};"
new_monthly = "var monthly={};var _TODAY=_curMonthYM;"
if old_monthly in src:
    src = src.replace(old_monthly, new_monthly, 1)
    results.append("OK 3 TODAY var")
else:
    results.append("SKIP 3")

# 4. Highlight dans les th du tableau - chercher month-th
old_th = "h+='<th class=\"month-th\" onclick=\"openMonth(\\''+m+'\\')\">'+(currentPeriod===\"vie\"?fmtM(m):fmtMc(m))+'</th>';"
new_th = "h+='<th class=\"month-th'+(m===_TODAY?' cur-month':'')+'\" onclick=\"openMonth(\\''+m+'\\')\">'+(currentPeriod===\"vie\"?fmtM(m):fmtMc(m))+'</th>';"
if old_th in src:
    src = src.replace(old_th, new_th, 1)
    results.append("OK 4 highlight mois actuel")
else:
    # Chercher pattern
    idx = src.find("month-th")
    results.append("SKIP 4 ctx=" + repr(src[idx:idx+100]))

# 5. CSS mois actuel
old_css_end = ".month-th:hover{background:#dbeafe}"
new_css_end = ".month-th:hover{background:#dbeafe}.cur-month{background:#fef9c3!important;font-weight:900;color:#92400e!important}"
if old_css_end in src:
    src = src.replace(old_css_end, new_css_end, 1)
    results.append("OK 5 CSS cur-month")
else:
    results.append("SKIP 5")

# 6. Modal récurrent - modifier confirmModal pour demander si récurrent
old_confirm = """function confirmModal(){
  var name=document.getElementById("modal-input").value.trim();
  if(!name){alert("Nom requis");return;}
  var p=D[currentPeriod];if(!p[modalCtx])p[modalCtx]={};
  months().forEach(function(m){if(!p[modalCtx][name])p[modalCtx][name]={};p[modalCtx][name][m]=0;});
  closeModal();if(currentMonth)renderMonthTab(currentMonthTab);else renderAnnual();
}"""
new_confirm = """function confirmModal(){
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
}"""
if old_confirm in src:
    src = src.replace(old_confirm, new_confirm, 1)
    results.append("OK 6 modal recurrent")
else:
    results.append("SKIP 6")

# 7. setPeriod : démarrer sur mois actuel
old_setperiod = """function setPeriod(period){
  currentPeriod=period;currentMonth=null;
  document.querySelectorAll(".period-tab").forEach(function(b){b.classList.toggle("active",b.dataset.period===period);});
  document.getElementById("view-monthly").style.display="none";
  document.getElementById("view-annual").style.display="block";
  document.getElementById("kpis").style.display="flex";
  renderKPIs();renderAnnual();
}"""
new_setperiod = """function setPeriod(period){
  currentPeriod=period;currentMonth=null;
  document.querySelectorAll(".period-tab").forEach(function(b){b.classList.toggle("active",b.dataset.period===period);});
  document.getElementById("view-monthly").style.display="none";
  document.getElementById("view-annual").style.display="block";
  document.getElementById("kpis").style.display="flex";
  renderKPIs();renderAnnual();
  // Aller direct au mois actuel si la période est l'année courante
  if(period===currentYear&&_TODAY&&months().indexOf(_TODAY)>=0){
    setTimeout(function(){openMonth(_TODAY);},80);
  }
}"""
if old_setperiod in src:
    src = src.replace(old_setperiod, new_setperiod, 1)
    results.append("OK 7 setPeriod -> mois actuel")
else:
    results.append("SKIP 7")

# 8. Auto-save à chaque input
old_cell = "p[sec][row][m]=parseFloat(this.value)||0;"
new_cell = "p[sec][row][m]=parseFloat(this.value)||0;saveAll();"
if old_cell in src:
    src = src.replace(old_cell, new_cell, 1)
    results.append("OK 8 auto-save input")
else:
    idx = src.find("parseFloat(this.value)||0")
    results.append("SKIP 8 ctx="+repr(src[max(0,idx-30):idx+50]))

# 9. Ajouter 2026 tab dans HTML
old_tabs = ('"<button class=\'period-tab\' data-period=\'2024\' onclick=\'setPeriod(\\"2024\\")\'>2024</button>"\n'
            '        "<button class=\'period-tab\' data-period=\'2025\' onclick=\'setPeriod(\\"2025\\")\' class=\'period-tab active\'>2025</button>"\n'
            '\n'
            '        "<button class=\'period-tab\' data-period=\'vie\' onclick=\'setPeriod(\\"vie\\")\'>VIE</button>"')
new_tabs = ('"<button class=\'period-tab\' data-period=\'2024\' onclick=\'setPeriod(\\"2024\\")\'>2024</button>"\n'
            '        "<button class=\'period-tab\' data-period=\'2025\' onclick=\'setPeriod(\\"2025\\")\'>2025</button>"\n'
            '        "<button class=\'period-tab\' data-period=\'2026\' onclick=\'setPeriod(\\"2026\\")\'>2026</button>"\n'
            '        "<button class=\'period-tab\' data-period=\'vie\' onclick=\'setPeriod(\\"vie\\")\'>VIE</button>"')
if old_tabs in src:
    src = src.replace(old_tabs, new_tabs, 1)
    results.append("OK 9 tab 2026")
else:
    results.append("SKIP 9")

# 10. Modal avec champ montant + récurrent
old_modal_html = '"<div class=\'modal-overlay\' id=\'modal\' onclick=\'if(event.target===this)closeModal()\'>"'
old_modal_content = ('"<div class=\'modal-overlay\' id=\'modal\' onclick=\'if(event.target===this)closeModal()\'>"'
                     '\n        "<div class=\'modal-box\'><h3 id=\'modal-title\'>Ajouter</h3>"')
new_modal_content = ('"<div class=\'modal-overlay\' id=\'modal\' onclick=\'if(event.target===this)closeModal()\'>"'
                     '\n        "<div class=\'modal-box\'><h3 id=\'modal-title\'>Ajouter</h3>"')
# Chercher le contenu du modal
idx_modal = src.find("<div class='modal-overlay' id='modal'")
if idx_modal > 0:
    idx_input = src.find("modal-input", idx_modal)
    idx_end = src.find("</div>", src.find("modal-actions", idx_modal)) + 6
    old_modal_body = src[idx_modal:idx_end+50]
    print("Modal trouvé, longueur:", len(old_modal_body))
    results.append("OK 10 modal trouvé")
else:
    results.append("SKIP 10 modal non trouvé")

open("/root/polar/finances_module.py", "w", encoding="utf-8").write(src)
for r in results: print(r)
import py_compile; py_compile.compile("/root/polar/finances_module.py", doraise=True)
print("SYNTAXE OK")
