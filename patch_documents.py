import json, os
src = open("/root/polar/app.py", encoding="utf-8").read()

# 1. Ajouter lien dans nav
old_nav = '"Finances":"/finances"'
new_nav = '"Finances":"/finances","Documents":"/documents"'
if old_nav in src:
    src = src.replace(old_nav, new_nav, 1)
    print("OK nav documents")

# 2. Ajouter icône documents dans nav
old_ico = '"finances":"💰"'
new_ico = '"finances":"💰","documents":"📁"'
if old_ico in src:
    src = src.replace(old_ico, new_ico, 1)
    print("OK icone documents")

# 3. Ajouter routes documents
documents_routes = '''
@app.route("/documents")
def page_documents():
    import os as _os
    docs_dir = POLAR / "documents"
    docs_dir.mkdir(exist_ok=True)
    cats = ["Fiches de paie","Contrats","Impots","Banque","Sante","Autre"]
    files = []
    for f in sorted(docs_dir.rglob("*"), key=lambda x: x.stat().st_mtime, reverse=True):
        if f.is_file():
            rel = f.relative_to(docs_dir)
            parts = rel.parts
            cat = parts[0] if len(parts) > 1 else "Autre"
            files.append({"name": f.name, "cat": cat, "path": str(rel), "size": f.stat().st_size, "mtime": f.stat().st_mtime})
    cats_json = json.dumps(cats, ensure_ascii=False)
    files_json = json.dumps(files, ensure_ascii=False)
    html = (
        \'\'\'<!DOCTYPE html><html lang="fr"><head><meta charset="UTF-8">\'\'\'
        \'\'\'<meta name="viewport" content="width=device-width,initial-scale=1">\'\'\'
        \'\'\'<title>Documents</title>\'\'\' + CSS +
        \'\'\'</head><body>\'\'\'
        \'\'\'<div style="position:sticky;top:0;z-index:99;background:#1a1a2e;color:#fff;padding:11px 15px;display:flex;align-items:center;justify-content:space-between">\'\'\'
        \'\'\'<div style="font-size:1rem;font-weight:700">📁 Documents</div>\'\'\'
        \'\'\'<label style="background:#52b788;color:#fff;border:none;border-radius:7px;padding:6px 14px;font-size:.75rem;font-weight:700;cursor:pointer">\'\'\'
        \'\'\'+ Ajouter<input type="file" multiple style="display:none" onchange="uploadFiles(this.files)"/></label></div>\'\'\'
        \'\'\'<div style="display:flex;gap:6px;padding:10px 12px;overflow-x:auto;border-bottom:1px solid #e8e4dc;background:#fff">\'\'\'
        \'\'\'<button class="btn-xs btn-add" onclick="filterCat(null)" id="cat-all" style="background:#1a1a2e;color:#fff">Tous</button>\'\'\'
    )
    for c in cats:
        html += f\'\'\'<button class="btn-xs btn-gray" onclick="filterCat(\\\'{c}\\\')" id="cat-{c[:5]}">{c}</button>\'\'\'
    html += (
        \'\'\'</div>\'\'\'
        \'\'\'<div style="padding:10px 12px"><input type="text" placeholder="🔍 Rechercher..." oninput="filterSearch(this.value)"\'\'\'
        \'\'\' style="width:100%;border:1px solid #e8e4dc;border-radius:8px;padding:8px 12px;font-size:.8rem"/></div>\'\'\'
        \'\'\'<div id="docs-list" style="padding:0 12px 80px"></div>\'\'\'
        \'\'\'<script>\'\'\'
        f\'\'\'var CATS={cats_json};var FILES={files_json};var _cat=null,_q="";\'\'\'
        \'\'\'function filterCat(c){_cat=c;document.querySelectorAll("[id^=cat-]").forEach(b=>b.style.background="");\'\'\'
        \'\'\'if(c===null)document.getElementById("cat-all").style.background="#1a1a2e";\'\'\'
        \'\'\'renderDocs();}\'\'\'
        \'\'\'function filterSearch(q){_q=q.toLowerCase();renderDocs();}\'\'\'
        \'\'\'function renderDocs(){\'\'\'
        \'\'\'  var f=FILES.filter(x=>(!_cat||x.cat===_cat)&&(!_q||x.name.toLowerCase().includes(_q)));\'\'\'
        \'\'\'  var byCat={};f.forEach(x=>{if(!byCat[x.cat])byCat[x.cat]=[];byCat[x.cat].push(x);});\'\'\'
        \'\'\'  var h="";\'\'\'
        \'\'\'  Object.keys(byCat).sort().forEach(cat=>{\'\'\'
        \'\'\'    h+=\'<div style="margin-bottom:14px">\';\'\'\'
        \'\'\'    h+=\'<div style="font-size:.65rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:#4a4a6a;margin-bottom:6px">\'+cat+\'</div>\';\'\'\'
        \'\'\'    byCat[cat].forEach(f=>{\'\'\'
        \'\'\'      var ico=f.name.endsWith(".pdf")?"📄":f.name.match(/\\.(jpg|jpeg|png)$/i)?"🖼️":"📎";\'\'\'
        \'\'\'      var sz=f.size>1024*1024?(f.size/1024/1024).toFixed(1)+"Mo":(f.size/1024).toFixed(0)+"Ko";\'\'\'
        \'\'\'      h+=\'<div style="display:flex;align-items:center;gap:10px;padding:8px 10px;background:#fff;border:1px solid #e8e4dc;border-radius:8px;margin-bottom:5px">\';\'\'\'
        \'\'\'      h+=\'<span style="font-size:1.2rem">\'+ico+\'</span>\';\'\'\'
        \'\'\'      h+=\'<div style="flex:1;min-width:0"><div style="font-size:.78rem;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">\'+f.name+\'</div>\';\'\'\'
        \'\'\'      h+=\'<div style="font-size:.6rem;color:#9ca3af">\'+f.cat+\' · \'+sz+\'</div></div>\';\'\'\'
        \'\'\'      h+=\'<a href="/documents/download?path=\'+encodeURIComponent(f.path)+\'" style="color:#1565c0;font-size:.7rem;font-weight:700;text-decoration:none">⬇</a>\';\'\'\'
        \'\'\'      h+=\'<button onclick="deleteDoc(\\\'\'+f.path+\'\\\')" style="border:none;background:none;color:#e63946;cursor:pointer;font-size:.8rem">✕</button>\';\'\'\'
        \'\'\'      h+=\'</div>\';\'\'\'
        \'\'\'    });\'\'\'
        \'\'\'    h+=\'</div>\';\'\'\'
        \'\'\'  });\'\'\'
        \'\'\'  if(!f.length)h=\'<div style="text-align:center;color:#9ca3af;padding:40px 0;font-size:.8rem">Aucun document trouvé</div>\';\'\'\'
        \'\'\'  document.getElementById("docs-list").innerHTML=h;}\'\'\'
        \'\'\'async function uploadFiles(files){\'\'\'
        \'\'\'  var cat=prompt("Catégorie ?\\n"+CATS.join("\\n"),"Fiches de paie");\'\'\'
        \'\'\'  if(!cat)return;\'\'\'
        \'\'\'  for(var f of files){\'\'\'
        \'\'\'    var fd=new FormData();fd.append("file",f);fd.append("cat",cat);\'\'\'
        \'\'\'    await fetch("/documents/upload",{method:"POST",body:fd});\'\'\'
        \'\'\'  }\'\'\'
        \'\'\'  location.reload();}\'\'\'
        \'\'\'async function deleteDoc(path){\'\'\'
        \'\'\'  if(!confirm("Supprimer "+path+"?"))return;\'\'\'
        \'\'\'  await fetch("/documents/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path:path})});\'\'\'
        \'\'\'  location.reload();}\'\'\'
        \'\'\'renderDocs();</script>\'\'\'
    )
    html += nav("/documents") + \'<div style="height:60px"></div></body></html>\'
    return html

@app.route("/documents/upload", methods=["POST"])
def documents_upload():
    import werkzeug
    f = request.files.get("file")
    cat = request.form.get("cat", "Autre")
    if not f: return jsonify({"ok": False})
    docs_dir = POLAR / "documents" / cat
    docs_dir.mkdir(parents=True, exist_ok=True)
    safe = werkzeug.utils.secure_filename(f.filename)
    f.save(str(docs_dir / safe))
    return jsonify({"ok": True})

@app.route("/documents/download")
def documents_download():
    from flask import send_file
    path = request.args.get("path","")
    full = POLAR / "documents" / path
    if not full.exists(): return "Not found", 404
    return send_file(str(full), as_attachment=True)

@app.route("/documents/delete", methods=["POST"])
def documents_delete():
    path = (request.get_json() or {}).get("path","")
    full = POLAR / "documents" / path
    try:
        if full.exists(): full.unlink()
        return jsonify({"ok": True})
    except Exception as e:
        return jsonify({"ok": False, "error": str(e)})
'''

# Injecter avant la dernière route
anchor = '@app.route("/api/finances/investments"'
if anchor in src:
    src = src.replace(anchor, documents_routes + '\n' + anchor, 1)
    print("OK routes documents")

# Créer dossier documents
import pathlib
pathlib.Path("/root/polar/documents").mkdir(exist_ok=True)
for cat in ["Fiches de paie","Contrats","Impots","Banque","Sante","Autre"]:
    pathlib.Path(f"/root/polar/documents/{cat}").mkdir(exist_ok=True)
print("OK dossiers créés")

open("/root/polar/app.py","w",encoding="utf-8").write(src)
import py_compile
try:
    py_compile.compile("/root/polar/app.py",doraise=True)
    print("SYNTAXE OK")
except Exception as e:
    print("ERREUR:", e)
