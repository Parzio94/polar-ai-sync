var _cat=null,_q="";
function filterCat(c){
  _cat=c;
  document.querySelectorAll("[id^=cat-]").forEach(function(b){b.style.background="#e8e4dc";b.style.color="#4a4a6a";});
  var aid=c===null?"cat-all":"cat-"+c.slice(0,5).replace(/ /g,"_");
  var ab=document.getElementById(aid);
  if(ab){ab.style.background="#1a1a2e";ab.style.color="#fff";}
  renderDocs();
}
var _sort='date';
function filterSearch(q){_q=q.toLowerCase();renderDocs();}
function setSort(s){_sort=s;renderDocs();}
function renderDocs(){
  var f=FILES.filter(function(x){return(!_cat||x.cat===_cat)&&(!_q||x.name.toLowerCase().indexOf(_q)>=0);});
  f.sort(function(a,b){
    if(_sort==='name')return a.name.localeCompare(b.name);
    if(_sort==='size')return b.size-a.size;
    return 0; // date: déjà trié par mtime côté serveur
  });
  var byCat={};
  f.forEach(function(x){if(!byCat[x.cat])byCat[x.cat]=[];byCat[x.cat].push(x);});
  var h="";
  Object.keys(byCat).sort().forEach(function(cat){
    h+='<div style="margin-bottom:14px">';
    h+='<div style="font-size:.65rem;font-weight:800;letter-spacing:.1em;text-transform:uppercase;color:#4a4a6a;margin-bottom:6px">'+cat+'</div>';
    byCat[cat].forEach(function(doc){
      var ext=doc.name.split('.').pop().toLowerCase();
      var ico=ext==='pdf'?'📄':['jpg','jpeg','png','gif'].indexOf(ext)>=0?'🖼️':'📎';
      var sz=doc.size>1048576?(doc.size/1048576).toFixed(1)+'Mo':(doc.size/1024).toFixed(0)+'Ko';
      h+='<div style="display:flex;align-items:center;gap:10px;padding:8px 10px;background:#fff;border:1px solid #e8e4dc;border-radius:8px;margin-bottom:5px">';
      h+='<span style="font-size:1.2rem">'+ico+'</span>';
      h+='<div style="flex:1;min-width:0"><div style="font-size:.78rem;font-weight:700;white-space:nowrap;overflow:hidden;text-overflow:ellipsis">'+doc.name+'</div>';
      h+='<div style="font-size:.6rem;color:#9ca3af">'+doc.cat+' · '+sz+'</div></div>';
      h+='<a href="/documents/download?path='+encodeURIComponent(doc.path)+'" style="color:#1565c0;font-size:.7rem;font-weight:700;text-decoration:none;padding:4px 8px;border:1px solid #1565c0;border-radius:5px">⬇</a>';
      h+='<button onclick="deleteDoc(\''+doc.path+'\')" style="border:none;background:none;color:#e63946;cursor:pointer;font-size:1rem;padding:4px">✕</button>';
      h+='</div>';
    });
    h+='</div>';
  });
  if(!f.length)h='<div style="text-align:center;color:#9ca3af;padding:40px 0;font-size:.8rem">Aucun document trouvé</div>';
  document.getElementById("docs-list").innerHTML=h;
}
function previewPDF(path){
  var modal=document.createElement('div');
  modal.style.cssText='position:fixed;inset:0;background:rgba(0,0,0,.8);z-index:999;display:flex;flex-direction:column;align-items:center;justify-content:center';
  modal.innerHTML='<div style="width:90vw;height:85vh;background:#fff;border-radius:12px;overflow:hidden;display:flex;flex-direction:column">';
  modal.innerHTML+='<div style="display:flex;justify-content:space-between;align-items:center;padding:10px 16px;background:#1a1a2e;color:#fff">';
  modal.innerHTML+='<span style="font-size:.8rem;font-weight:700">'+path.split('/').pop()+'</span>';
  modal.innerHTML+='<button onclick="this.closest(\'div[style*=fixed]\').remove()" style="border:none;background:none;color:#fff;font-size:1.2rem;cursor:pointer">✕</button></div>';
  modal.innerHTML+='<iframe src="/documents/download?path='+encodeURIComponent(path)+'" style="flex:1;border:none"></iframe></div>';
  document.body.appendChild(modal);
}
async function uploadFiles(files){
  var cat=prompt("Choisir une catégorie:\n"+CATS.join("\n"),"Fiches de paie");
  if(!cat)return;
  for(var i=0;i<files.length;i++){
    var fd=new FormData();
    fd.append("file",files[i]);
    fd.append("cat",cat);
    await fetch("/documents/upload",{method:"POST",body:fd});
  }
  location.reload();
}
async function renameDoc(path, oldName){
  var newName=prompt('Nouveau nom:',oldName);
  if(!newName||newName===oldName)return;
  var r=await fetch('/documents/rename',{method:'POST',
    headers:{'Content-Type':'application/json'},
    body:JSON.stringify({path:path,new_name:newName})});
  if(r.ok)location.reload();
  else alert('Erreur renommage');
}
async function deleteDoc(path){
  if(!confirm("Supprimer ce fichier ?"))return;
  await fetch("/documents/delete",{method:"POST",headers:{"Content-Type":"application/json"},body:JSON.stringify({path:path})});
  location.reload();
}
filterCat(null);
