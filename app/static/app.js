"use strict";
const $ = id => document.getElementById(id);
const fmt = n => new Intl.NumberFormat("vi-VN").format(n) + " ₫";
const today = new Intl.DateTimeFormat("sv-SE",{timeZone:"Asia/Ho_Chi_Minh"}).format(new Date());
let queryText="";
let registering=false, filter="all", page=1, report, editing, requestId, generation=0, timer;
$("month").value=today.slice(0,7);

function element(tag, text, className) {
  const e=document.createElement(tag);
  if(text!==undefined) e.textContent=text;
  if(className) e.className=className;
  return e;
}
function notice(message) {
  const dialog=document.querySelector("dialog[open]");
  if(dialog) {
    let box=dialog.querySelector(".error");
    if(!box) {box=element("p","","error");box.setAttribute("role","alert");dialog.querySelector("form").append(box);}
    box.textContent=message;
  } else {
    $("notice").hidden=false; $("notice").textContent=message;
    clearTimeout(timer);timer=setTimeout(()=>$("notice").hidden=true,6000);
  }
}
function authScreen(){
  generation++; report=null; queryText=""; $("query").value="";
  document.querySelectorAll("dialog[open]").forEach(d=>d.close());
  $("home").hidden=true; $("auth").hidden=false; document.querySelector(".account").hidden=true;
}
async function api(path,method="GET",data) {
  const opts={method};
  if(data!==undefined){opts.headers={"Content-Type":"application/json","X-Ledger-Request":"1"};opts.body=JSON.stringify(data);}
  const res=await fetch("/api/"+path,opts);
  const json=await res.json();
  if(!res.ok){if(res.status===401 && !["login","register"].includes(path))authScreen();throw Error(json.error||"Không thể thực hiện yêu cầu.");}
  return json;
}
function action(fn){return async e=>{e?.preventDefault();try{await fn(e);}catch(err){notice(err.message);}};}
function submit(form,fn){
  form.onsubmit=action(async()=>{const b=form.querySelector(".primary");if(b.disabled)return;b.disabled=true;
    try{await fn();}finally{b.disabled=false;}});
}
$("switchAuth").onclick=()=>{
  registering=!registering;
  $("authTitle").textContent=$("authSubmit").textContent=registering?"Tạo tài khoản":"Đăng nhập";
  $("authHint").hidden=!registering; $("password").minLength=registering?12:1;
  $("password").autocomplete=registering?"new-password":"current-password";
  $("switchAuth").textContent=registering?"Đã có tài khoản? Đăng nhập":"Chưa có tài khoản? Đăng ký";
};
submit($("authform"),async()=>{
  await api(registering?"register":"login","POST",{username:$("username").value,password:$("password").value});
  $("password").value=""; await openHome();
});
async function openHome(){
  const me=await api("me");
  $("who").textContent=me.username; $("auth").hidden=true; $("home").hidden=false;
  document.querySelector(".account").hidden=false; await refresh();
}
$("logout").onclick=action(async()=>{await api("logout","POST",{});authScreen();});
async function refresh(){
  const g=++generation, month=$("month").value;
  const query=new URLSearchParams({month,kind:filter,page,q:queryText});
  const data=await api("report?"+query);
  if(g!==generation)return;
  report=data;page=data.page;
  $("period").textContent="Tháng "+month.slice(5)+" năm "+month.slice(0,4);
  $("export").href="/api/export?"+query;
  $("net").textContent=fmt(data.closing);
  $("flow").textContent="Đầu tháng "+fmt(data.opening)+" · Thu trừ chi "+fmt(data.totals.in-data.totals.out);
  $("income").textContent=fmt(data.totals.in);$("expense").textContent=fmt(data.totals.out);
  $("rows").replaceChildren();
  for(const r of data.rows){
    const row=element("button",undefined,"row"), info=element("span",undefined,"details"),isIn=r.kind==="in";
    info.append(element("b",r.note||r.category),element("small",r.day.split("-").reverse().join("/")+" · "+r.category));
    row.append(element("span",isIn?"↙":"↗","badge "+(isIn?"income":"expense")),info,element("strong",(isIn?"+":"−")+fmt(r.amount)));
    row.title="Xem và chỉnh sửa";row.onclick=()=>edit(r);$("rows").append(row);
  }
  if(!data.rows.length)$("rows").append(element("p","Chưa có giao dịch cho bộ lọc này.","empty"));
  const pages=Math.max(1,Math.ceil(data.count/20));$("page").textContent=data.count+" giao dịch · Trang "+page+"/"+pages;
  $("prev").disabled=page<=1;$("next").disabled=page>=pages;
  $("budgetText").textContent=data.budget?fmt(data.totals.out)+" / "+fmt(data.budget):"Chưa đặt ngân sách";
  $("budgetBar").hidden=!data.budget;$("budgetBar").value=data.budget?Math.min(100,data.totals.out/data.budget*100):0;
  const left=data.budget-data.totals.out;
  $("available").textContent=data.budget?(left>=0?"Còn lại ":"Vượt ngân sách ")+fmt(Math.abs(left)):"Đặt hạn mức để theo dõi chi tiêu.";
  $("breakdown").replaceChildren();
  for(const r of data.breakdown){
    const line=element("div",undefined,"split");line.append(element("span",r.category),element("b",fmt(r.total)));
    const bar=element("progress");bar.max=data.totals.out;bar.value=r.total;bar.setAttribute("aria-label",r.category);
    $("breakdown").append(line,bar);
  }
  if(!data.breakdown.length)$("breakdown").append(element("p","Chưa có khoản chi trong tháng.","empty"));
}
$("searchForm").onsubmit=action(async()=>{queryText=$("query").value.trim();page=1;await refresh();});
$("query").oninput=action(async()=>{if(queryText&&!$("query").value){queryText="";page=1;await refresh();}});
$("month").onchange=action(async()=>{if(!$("month").value)$("month").value=today.slice(0,7);page=1;await refresh();});
document.querySelectorAll("[data-kind]").forEach(b=>b.onclick=action(async()=>{
  filter=b.dataset.kind;page=1;
  document.querySelectorAll("[data-kind]").forEach(x=>x.setAttribute("aria-pressed",String(x===b))); await refresh();
}));
$("prev").onclick=action(async()=>{page--;await refresh();});$("next").onclick=action(async()=>{page++;await refresh();});
function categories(){ $("category").replaceChildren(...report.groups[$("kind").value].map(v=>new Option(v,v))); }
function show(id){$(id).querySelector(".error")?.remove();$(id).showModal();}
function edit(r){
  if(!report)return;
  editing=r;requestId=crypto.randomUUID();$("kind").value=r?.kind||"out";categories();
  if(r)$("category").value=r.category;
  $("day").value=r?.day||($("month").value===today.slice(0,7)?today:$("month").value+"-01");
  $("note").value=r?.note||"";$("amount").value=r?.amount||"";$("remove").hidden=!r;
  $("entryTitle").textContent=r?"Chỉnh sửa giao dịch":"Thêm giao dịch";show("editor");$("amount").focus();
}
$("kind").onchange=categories;$("add").onclick=()=>edit(null);
document.querySelectorAll("[data-close]").forEach(b=>b.onclick=()=>b.closest("dialog").close());
submit($("entryform"),async()=>{
  const data={kind:$("kind").value,category:$("category").value,day:$("day").value,amount:Number($("amount").value),note:$("note").value,request_id:requestId,version:editing?.version};
  await api(editing?"entries/"+editing.id:"entries",editing?"PUT":"POST",data);
  $("editor").close();$("month").value=data.day.slice(0,7);page=1;
  if(filter!=="all" && filter!==data.kind){filter="all";document.querySelectorAll("[data-kind]").forEach(b=>b.setAttribute("aria-pressed",String(b.dataset.kind===filter)));}
  await refresh();notice("Đã lưu giao dịch.");
});
$("remove").onclick=action(async()=>{
  if(!editing||!confirm("Xóa giao dịch này khỏi sổ?"))return;
  await api("entries/"+editing.id,"DELETE",{version:editing.version});$("editor").close();await refresh();notice("Đã xóa giao dịch.");
});
$("setBudget").onclick=()=>{if(report){$("limit").value=report.budget||"";show("budgetDialog");}};
submit($("budgetForm"),async()=>{await api("budget","POST",{month:$("month").value,amount:Number($("limit").value)});$("budgetDialog").close();await refresh();notice("Đã lưu ngân sách.");});
async function initialize(){
  const {demo}=await api("mode");
  if(demo){
    $("demoInfo").hidden=false;
    $("demoLabel").hidden=false;
    $("username").value="demo";
    $("password").value="SoMocDemo123!";
    $("switchAuth").hidden=true;
  }
  await openHome();
}
initialize().catch(err=>{if($("auth").hidden)notice(err.message);});
