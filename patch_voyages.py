#!/usr/bin/env python3
# -*- coding: utf-8 -*-
import sys

src = open("/root/polar/app.py", encoding="utf-8").read()
results = []

# ══ 1. CartoDB + Dark mode ════════════════════════════════════
old_tile = "L.tileLayer('https://{{s}}.tile.openstreetmap.org/{{z}}/{{x}}/{{y}}.png',{{attribution:'\xa9 OpenStreetMap'}}).addTo(map);"
if old_tile in src:
    new_tile = (
        "var _tileLight=L.tileLayer('https://{{s}}.basemaps.cartocdn.com/rastertiles/voyager/{{z}}/{{x}}/{{y}}{{r}}.png',{{attribution:'\xa9 OpenStreetMap \xa9 CARTO',subdomains:'abcd',maxZoom:19}});\n"
        "var _tileDark=L.tileLayer('https://{{s}}.basemaps.cartocdn.com/dark_all/{{z}}/{{x}}/{{y}}{{r}}.png',{{attribution:'\xa9 OpenStreetMap \xa9 CARTO',subdomains:'abcd',maxZoom:19}});\n"
        "var _darkMode=false;\n"
        "function toggleMapDark(){{if(_darkMode){{map.removeLayer(_tileDark);_tileLight.addTo(map);document.getElementById('btn-map-dark').textContent='\U0001f319';}}else{{map.removeLayer(_tileLight);_tileDark.addTo(map);document.getElementById('btn-map-dark').textContent='\u2600\ufe0f';}} _darkMode=!_darkMode;}}\n"
        "_tileLight.addTo(map);"
    )
    src = src.replace(old_tile, new_tile, 1)
    results.append("OK 1a CartoDB")
else:
    results.append("SKIP 1a")

old_mode_btn = '<button id="mode-btn" onclick="toggleMode()">\u2795 Ajouter un point</button>'
if old_mode_btn in src and 'btn-map-dark' not in src:
    new_mode_btn = (
        old_mode_btn +
        '\n<button id="btn-map-dark" onclick="toggleMapDark()" '
        'style="position:absolute;top:10px;right:10px;z-index:1000;background:#fff;'
        'border:2px solid #ccc;border-radius:6px;padding:5px 9px;cursor:pointer;'
        'font-size:1rem;box-shadow:0 2px 6px rgba(0,0,0,.2)">\U0001f319</button>'
    )
    src = src.replace(old_mode_btn, new_mode_btn, 1)
    results.append("OK 1b dark btn")
else:
    results.append("SKIP 1b")

# ══ 2. Flatpickr ══════════════════════════════════════════════
old_fp_ret = "return \"\"\"<script>\nvar _voyAddCtx={}, _voyEtapeVoyId=null, _elType='transport',"
if old_fp_ret in src:
    new_fp_ret = (
        'return """<script src="https://cdn.jsdelivr.net/npm/flatpickr"></script>\n'
        '<script src="https://cdn.jsdelivr.net/npm/flatpickr/dist/l10n/fr.js"></script>\n'
        '<link rel="stylesheet" href="https://cdn.jsdelivr.net/npm/flatpickr/dist/flatpickr.min.css"/>\n'
        "<script>\nvar _voyAddCtx={}, _voyEtapeVoyId=null, _elType='transport',"
    )
    src = src.replace(old_fp_ret, new_fp_ret, 1)
    results.append("OK 2a Flatpickr CDN")
else:
    results.append("SKIP 2a")

old_vdates = (
    '      <div class="voy-form-row"><label>Date de d\xe9but</label>'
    '<input id="vdate_debut" type="date" onchange="if(!document.getElementById(\'vdate_fin\').value)'
    '{document.getElementById(\'vdate_fin\').value=this.value;document.getElementById(\'vdate_fin\').focus();}"/></div>\n'
    '      <div class="voy-form-row"><label>Date de fin</label><input id="vdate_fin" type="date"/></div>'
)
if old_vdates in src:
    new_vdates = (
        '      <div class="voy-form-row"><label>Dates du voyage</label>\n'
        '        <input id="vdate_range" placeholder="Choisir les dates..." readonly '
        'style="cursor:pointer;width:100%;border:1px solid #e8e4dc;border-radius:6px;padding:7px 10px;font-size:.8rem;background:#fafaf8"/>\n'
        '        <input type="hidden" id="vdate_debut"/>\n'
        '        <input type="hidden" id="vdate_fin"/>\n'
        '      </div>'
    )
    src = src.replace(old_vdates, new_vdates, 1)
    results.append("OK 2b dates voyage")
else:
    results.append("SKIP 2b")

old_edates = (
    '      <div class="voy-form-row"><label>Date de d\xe9but</label>'
    '<input id="edate_debut" type="date" onchange="if(!document.getElementById(\'edate_fin\').value)'
    '{document.getElementById(\'edate_fin\').value=this.value;document.getElementById(\'edate_fin\').focus();}"/></div>\n'
    '      <div class="voy-form-row"><label>Date de fin</label><input id="edate_fin" type="date"/></div>'
)
if old_edates in src:
    new_edates = (
        '      <div class="voy-form-row"><label>Dates de l\u2019\xe9tape</label>\n'
        '        <input id="edate_range" placeholder="Choisir les dates..." readonly '
        'style="cursor:pointer;width:100%;border:1px solid #e8e4dc;border-radius:6px;padding:7px 10px;font-size:.8rem;background:#fafaf8"/>\n'
        '        <input type="hidden" id="edate_debut"/>\n'
        '        <input type="hidden" id="edate_fin"/>\n'
        '      </div>'
    )
    src = src.replace(old_edates, new_edates, 1)
    results.append("OK 2c dates etape")
else:
    results.append("SKIP 2c")

old_editvoy = "var _editVoyId=null;"
if old_editvoy in src and '_fpVoy' not in src:
    new_editvoy = (
        "var _editVoyId=null;\n"
        "var _fpVoy=null,_fpEtape=null;\n"
        "document.addEventListener('DOMContentLoaded',function(){\n"
        "  function localDate(d){return d.getFullYear()+'-'+String(d.getMonth()+1).padStart(2,'0')+'-'+String(d.getDate()).padStart(2,'0');}\n"
        "  if(document.getElementById('vdate_range')){\n"
        "    _fpVoy=flatpickr('#vdate_range',{mode:'range',locale:'fr',dateFormat:'Y-m-d',altInput:true,altFormat:'d M Y',\n"
        "      onChange:function(dates){\n"
        "        if(dates[0])document.getElementById('vdate_debut').value=localDate(dates[0]);\n"
        "        if(dates[1])document.getElementById('vdate_fin').value=localDate(dates[1]);\n"
        "      }\n"
        "    });\n"
        "  }\n"
        "  if(document.getElementById('edate_range')){\n"
        "    _fpEtape=flatpickr('#edate_range',{mode:'range',locale:'fr',dateFormat:'Y-m-d',altInput:true,altFormat:'d M Y',\n"
        "      onChange:function(dates){\n"
        "        if(dates[0])document.getElementById('edate_debut').value=localDate(dates[0]);\n"
        "        if(dates[1])document.getElementById('edate_fin').value=localDate(dates[1]);\n"
        "      }\n"
        "    });\n"
        "  }\n"
        "});"
    )
    src = src.replace(old_editvoy, new_editvoy, 1)
    results.append("OK 2d Flatpickr init")
else:
    results.append("SKIP 2d")

# ══ 3. Route /api/voyages/list ════════════════════════════════
if '"/api/voyages/list"' not in src:
    old_cr = '@app.route("/api/voyages/create", methods=["POST"])'
    if old_cr in src:
        new_cr = (
            '@app.route("/api/voyages/list")\n'
            'def api_voyages_list():\n'
            '    return jsonify(load_voyages().get("voyages", []))\n\n'
            + old_cr
        )
        src = src.replace(old_cr, new_cr, 1)
        results.append("OK 3 voyages/list")
    else:
        results.append("SKIP 3")
else:
    results.append("SKIP 3 deja")

# ══ 4. Budget hotel sans doublon checkout ═════════════════════
old_budget = (
    'def _budget_par_cat(voyage):\n'
    '    cats = {"transport":[0,0,0],"hotel":[0,0,0],"activite":[0,0,0],"nourriture":[0,0,0]}\n'
    '    for el in voyage.get("elements",[]):\n'
    '        t = el.get("type","")\n'
    '        if t in cats:\n'
    '            pr = el.get("prix_reel") or el.get("prix_min") or 0\n'
    '            cats[t][2] += pr\n'
    '    return cats'
)
if old_budget in src:
    new_budget = (
        'def _budget_par_cat(voyage):\n'
        '    cats = {"transport":[0,0,0],"hotel":[0,0,0],"activite":[0,0,0],"nourriture":[0,0,0]}\n'
        '    for el in voyage.get("elements",[]):\n'
        '        t = el.get("type","")\n'
        '        if t == "hotel" and el.get("type_evenement","") == "checkout":\n'
        '            continue\n'
        '        if t in cats:\n'
        '            pr = el.get("prix_reel") or el.get("prix_min") or 0\n'
        '            cats[t][2] += pr\n'
        '    return cats'
    )
    src = src.replace(old_budget, new_budget, 1)
    results.append("OK 4 budget")
else:
    results.append("SKIP 4")

# ══ 5. Finances dans nav ══════════════════════════════════════
if '"/finances"' not in src:
    old_pages = '("/habitudes","\U0001f4cb","Habitudes")]'
    if old_pages in src:
        src = src.replace(old_pages,
            '("/habitudes","\U0001f4cb","Habitudes"),("/finances","\U0001f4b0","Finances")]', 1)
        results.append("OK 5 Finances nav")
    else:
        results.append("SKIP 5")
else:
    results.append("SKIP 5 deja")

# ══ 6. Finances routes ════════════════════════════════════════
if 'def page_finances' not in src:
    anchor = 'if __name__=="__main__":'
    new_routes = (
        '\nFINANCES_FILE = Path("/root/polar/finances/finances_data.json")\n\n'
        'def _load_finances():\n'
        '    Path("/root/polar/finances").mkdir(parents=True, exist_ok=True)\n'
        '    if FINANCES_FILE.exists():\n'
        '        try: return json.loads(FINANCES_FILE.read_text(encoding="utf-8"))\n'
        '        except: pass\n'
        '    import sys as _s; _s.path.insert(0, str(POLAR))\n'
        '    from finances_module import default_data\n'
        '    return default_data()\n\n'
        '@app.route("/finances")\n'
        'def page_finances():\n'
        '    import sys as _s; _s.path.insert(0, str(POLAR))\n'
        '    from finances_module import build_finances_page\n'
        '    return build_finances_page(_load_finances())\n\n'
        '@app.route("/api/finances/save", methods=["POST"])\n'
        'def api_finances_save():\n'
        '    try:\n'
        '        Path("/root/polar/finances").mkdir(parents=True, exist_ok=True)\n'
        '        atomic_write_json(FINANCES_FILE, request.get_json())\n'
        '        return jsonify({"ok": True})\n'
        '    except Exception as e:\n'
        '        return jsonify({"ok": False, "error": str(e)})\n\n'
    )
    src = src.replace(anchor, new_routes + anchor, 1)
    results.append("OK 6 Finances routes")
else:
    results.append("SKIP 6 deja")

# ══ 7. Python : itinerary_by_day + hotel_periods + dedup ══════
old_markers = (
    '    markers_json = _json.dumps(markers, ensure_ascii=False)\n'
    '    routes_json  = _json.dumps(routes,  ensure_ascii=False)\n'
    '    voyage_id_js = voyage_id or ""'
)
new_markers = (
    '    # Itineraire pieton par jour avec injection hotel\n'
    '    from datetime import datetime as _dt, timedelta as _td\n'
    '    import math as _math\n'
    '    MOMENT_ORDER = {"matin":0,"midi":1,"aprem":2,"soir":3,"":4}\n'
    '    DAY_COLORS = ["#e63946","#2d6a4f","#1565c0","#f59e0b","#7c3aed","#006d77","#c62828","#37474f"]\n'
    '    itinerary_by_day = {}\n'
    '    if voyage_id:\n'
    '        _v = next((x for x in load_voyages().get("voyages",[]) if x["id"]==voyage_id), None)\n'
    '        if _v:\n'
    '            hotel_periods = []\n'
    '            for _el in _v.get("elements",[]):\n'
    '                if _el.get("type") != "hotel": continue\n'
    '                _evt = _el.get("type_evenement","")\n'
    '                _c   = _el.get("coords")\n'
    '                if not _c or not _c.get("lat"): continue\n'
    '                if _evt == "checkin":\n'
    '                    hotel_periods.append({"coords":_c,"nom":_el.get("nom",""),"date_in":_el.get("date",""),"date_out":None})\n'
    '                elif _evt == "checkout" and hotel_periods:\n'
    '                    for _hp in reversed(hotel_periods):\n'
    '                        if _hp["date_out"] is None:\n'
    '                            _hp["date_out"] = _el.get("date",""); break\n'
    '            day_raw = {}\n'
    '            for _el in sorted(_v.get("elements",[]), key=lambda e:(e.get("date",""),MOMENT_ORDER.get(e.get("moment",""),4))):\n'
    '                _etype = _el.get("type","")\n'
    '                _date  = _el.get("date","")\n'
    '                if not _date: continue\n'
    '                if _etype == "hotel" and _el.get("type_evenement","") == "checkout": continue\n'
    '                if _date not in day_raw: day_raw[_date] = []\n'
    '                if _etype == "transport":\n'
    '                    _cd = _el.get("coords_depart"); _ca = _el.get("coords")\n'
    '                    if _cd and _ca and _cd.get("lat") and _ca.get("lat"):\n'
    '                        day_raw[_date].append({"lat":_cd["lat"],"lng":_cd["lng"],"nom":_el.get("ville_depart",""),"walk_after":False})\n'
    '                        day_raw[_date].append({"lat":_ca["lat"],"lng":_ca["lng"],"nom":_el.get("ville_arrivee",""),"walk_after":True})\n'
    '                else:\n'
    '                    _c = _el.get("coords")\n'
    '                    if _c and _c.get("lat"):\n'
    '                        _nom = _el.get("nom") or _el.get("nom_etablissement","")\n'
    '                        day_raw[_date].append({"lat":_c["lat"],"lng":_c["lng"],"nom":_nom,"walk_after":True})\n'
    '            for _hp in hotel_periods:\n'
    '                if not _hp["date_in"] or not _hp["date_out"]: continue\n'
    '                try:\n'
    '                    _d_in  = _dt.strptime(_hp["date_in"],  "%Y-%m-%d")\n'
    '                    _d_out = _dt.strptime(_hp["date_out"], "%Y-%m-%d")\n'
    '                    _d = _d_in + _td(days=1)\n'
    '                    while _d <= _d_out:\n'
    '                        _ds = _d.strftime("%Y-%m-%d")\n'
    '                        _hpt = {"lat":_hp["coords"]["lat"],"lng":_hp["coords"]["lng"],"nom":"\U0001f3e8 "+_hp["nom"],"walk_after":True}\n'
    '                        if _ds not in day_raw: day_raw[_ds] = [_hpt]\n'
    '                        else: day_raw[_ds].insert(0, _hpt)\n'
    '                        _d += _td(days=1)\n'
    '                except: pass\n'
    '            def _dist_m(a,b):\n'
    '                R=6371000; la1,lo1,la2,lo2=map(_math.radians,[a["lat"],a["lng"],b["lat"],b["lng"]])\n'
    '                return R*_math.acos(min(1,_math.sin(la1)*_math.sin(la2)+_math.cos(la1)*_math.cos(la2)*_math.cos(lo2-lo1)))\n'
    '            for _di,_date in enumerate(sorted(day_raw.keys())):\n'
    '                _pts = day_raw[_date]\n'
    '                _deduped = []\n'
    '                for _p in _pts:\n'
    '                    if not _deduped or _dist_m(_deduped[-1], _p) >= 50: _deduped.append(_p)\n'
    '                if len(_deduped) >= 2:\n'
    '                    itinerary_by_day[_date] = {"pts":_deduped,"color":DAY_COLORS[_di%len(DAY_COLORS)]}\n'
    '    markers_json = _json.dumps(markers, ensure_ascii=False)\n'
    '    routes_json  = _json.dumps(routes,  ensure_ascii=False)\n'
    '    itinerary_json = _json.dumps(itinerary_by_day, ensure_ascii=False)\n'
    '    voyage_id_js = voyage_id or ""'
)
if old_markers in src:
    src = src.replace(old_markers, new_markers, 1)
    results.append("OK 7 Python itinerary")
else:
    results.append("SKIP 7 markers anchor")

# ══ 8. Passer itinerary_json au JS ═══════════════════════════
old_const = 'const markers={markers_json};\nconst routes={routes_json};'
new_const  = 'const markers={markers_json};\nconst routes={routes_json};\nconst ITINERARY={itinerary_json};'
if old_const in src:
    src = src.replace(old_const, new_const, 1)
    results.append("OK 8 ITINERARY JS")
else:
    results.append("SKIP 8")

# ══ 9. JS OSRM + bouton recalcul (auto-escape pour f-string) ═
_osrm_raw = (
    "// OSRM itineraires pietons\n"
    "var _routeLayers={};\n"
    "var _osrmCache={};\n"
    "function _hashPts(pts){return pts.map(function(p){return p.lat.toFixed(5)+','+p.lng.toFixed(5);}).join('|');}\n"
    "function _loadCache(){try{var c=localStorage.getItem('osrm_cache');return c?JSON.parse(c):{};}catch(e){return{};}}\n"
    "function _saveCache(cache){try{localStorage.setItem('osrm_cache',JSON.stringify(cache));}catch(e){}}\n"
    "_osrmCache=_loadCache();\n"
    "async function fetchOSRMRoute(pts){\n"
    "  var h=_hashPts(pts);\n"
    "  if(_osrmCache[h])return _osrmCache[h];\n"
    "  var coords=pts.map(function(p){return p.lng+','+p.lat;}).join(';');\n"
    "  try{\n"
    "    var r=await fetch('https://router.project-osrm.org/route/v1/foot/'+coords+'?overview=full&geometries=geojson');\n"
    "    var d=await r.json();\n"
    "    if(d.routes&&d.routes[0]){\n"
    "      var geo=d.routes[0].geometry.coordinates;\n"
    "      _osrmCache[h]=geo;_saveCache(_osrmCache);return geo;\n"
    "    }\n"
    "  }catch(e){}\n"
    "  return null;\n"
    "}\n"
    "async function drawItineraries(forceRecalc){\n"
    "  Object.keys(_routeLayers).forEach(function(k){_routeLayers[k].forEach(function(l){map.removeLayer(l);});});\n"
    "  _routeLayers={};\n"
    "  if(!ITINERARY||!Object.keys(ITINERARY).length)return;\n"
    "  if(forceRecalc){_osrmCache={};_saveCache(_osrmCache);}\n"
    "  for(var date in ITINERARY){\n"
    "    var day=ITINERARY[date];\n"
    "    _routeLayers[date]=[];\n"
    "    var capturedDate=date;\n"
    "    var geo=await fetchOSRMRoute(day.pts);\n"
    "    if(geo){\n"
    "      var latlngs=geo.map(function(c){return[c[1],c[0]];});\n"
    "      var line=L.polyline(latlngs,{color:day.color,weight:4,opacity:0.8,dashArray:'8,4'});\n"
    "      line.addTo(map);_routeLayers[capturedDate].push(line);\n"
    "    }else{\n"
    "      var latlngs=day.pts.map(function(p){return[p.lat,p.lng];});\n"
    "      var line=L.polyline(latlngs,{color:day.color,weight:3,opacity:0.5,dashArray:'4,4'});\n"
    "      line.addTo(map);_routeLayers[capturedDate].push(line);\n"
    "    }\n"
    "    day.pts.forEach(function(p,i){\n"
    "      var bk=day.color;\n"
    "      var num=L.marker([p.lat,p.lng],{icon:L.divIcon({\n"
    "        html:'<div style=\"position:relative;width:24px;height:24px\"><span style=\"position:absolute;top:-4px;right:-4px;background:'+bk+';color:#fff;border-radius:50%;width:12px;height:12px;display:flex;align-items:center;justify-content:center;font-size:8px;font-weight:800;border:1px solid #fff;line-height:1\">'+(i+1)+'</span></div>',\n"
    "        className:'',iconSize:[24,24],iconAnchor:[12,12]\n"
    "      })}).bindTooltip((i+1)+'. '+(p.nom||''),{permanent:false});\n"
    "      num.addTo(map);_routeLayers[capturedDate].push(num);\n"
    "    });\n"
    "  }\n"
    "}\n"
    "drawItineraries(false);\n"
    "var _rcBtn=document.createElement('button');\n"
    "_rcBtn.id='btn-recalc';_rcBtn.textContent='\U0001f504 Recalculer';\n"
    "_rcBtn.style.cssText='position:absolute;top:50px;right:10px;z-index:1000;background:#fff;border:2px solid #ccc;border-radius:6px;padding:5px 9px;cursor:pointer;font-size:.8rem;box-shadow:0 2px 6px rgba(0,0,0,.2)';\n"
    "_rcBtn.onclick=function(){drawItineraries(true);};\n"
    "document.body.appendChild(_rcBtn);\n"
)
# Echapper tous les { et } pour la f-string de app.py
_osrm_escaped = _osrm_raw.replace("{", "{{").replace("}", "}}")

old_after_tile = "_tileLight.addTo(map);\nconst statutLbl"
new_after_tile = "_tileLight.addTo(map);\n" + _osrm_escaped + "const statutLbl"
if old_after_tile in src:
    src = src.replace(old_after_tile, new_after_tile, 1)
    results.append("OK 9 OSRM JS + recalcul")
else:
    idx = src.find("_tileLight.addTo(map);")
    results.append("SKIP 9 ctx=" + repr(src[idx:idx+50]) if idx>=0 else "SKIP 9 not found")

open("/root/polar/app.py", "w", encoding="utf-8").write(src)
for r in results:
    print(r)

import py_compile
try:
    py_compile.compile("/root/polar/app.py", doraise=True)
    print("SYNTAXE OK")
except Exception as e:
    print("ERREUR:", e)
