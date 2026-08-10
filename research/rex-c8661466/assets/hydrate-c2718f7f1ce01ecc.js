(function(){
'use strict';
var here=document.currentScript;
function mount(id,type,parts){
  var node=document.createElement('script');
  node.id=id;node.type=type;node.textContent=(parts||[]).join('');
  here.parentNode.insertBefore(node,here);
}
mount('expedition-static-blob-data','application/octet-stream',window.__SNEFERU_RESEARCH_BLOB_PARTS__);
mount('expedition-static-data','application/json',window.__SNEFERU_RESEARCH_DATA_PARTS__);
try{delete window.__SNEFERU_RESEARCH_BLOB_PARTS__;delete window.__SNEFERU_RESEARCH_DATA_PARTS__;}catch(_){}
})();
