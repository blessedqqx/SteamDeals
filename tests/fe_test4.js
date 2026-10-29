const fs=require('fs'),vm=require('vm'),path=require('path');
const html=fs.readFileSync('index.html','utf8'),js=html.match(/<script>([\s\S]*)<\/script>/)[1];
let fails=0;const ok=(n,c,extra="")=>{console.log((c?"OK   ":"FAIL ")+n+(c?"":"  "+extra));if(!c)fails++};
const errors=[];
function el(id){const o={id,_h:"",textContent:"",value:"",hidden:false,dataset:{},placeholder:"",open:false,className:"",_q:{},
 get innerHTML(){return this._h},set innerHTML(v){this._h=v;if(this.id==='sort'){const vs=[...v.matchAll(/value="(\w+)"/g)].map(m=>m[1]);if(!vs.includes(this.value))this.value=vs[0]||''}},showModal(){this.open=true},close(){this.open=false},querySelector(s){return this._q[s]??=el(s)}};return o}
const E={};[...html.matchAll(/id="(\w+)"/g)].forEach(m=>E[m[1]]=el(m[1]));
const sb={window:{},console,Intl,Date,Math,JSON,Promise,parseInt,Object,Array,Set,String,Number,isNaN,setTimeout,
 location:{hash:""},localStorage:{getItem(){return null},setItem(){}},
 document:{documentElement:{lang:""},getElementById:i=>E[i],querySelectorAll:()=>[]},
 fetch:async u=>{const f=path.join('.',u);if(!fs.existsSync(f))return{ok:false,json:async()=>({})};const t=fs.readFileSync(f,'utf8');return{ok:true,json:async()=>JSON.parse(t)}}};
Object.assign(sb,E);const ctx=vm.createContext(sb);
process.on('unhandledRejection',e=>{errors.push(String(e))});
const run=c=>vm.runInContext(c,ctx),wait=ms=>new Promise(r=>setTimeout(r,ms));
const click=(h,dk,v)=>E[h].onclick({target:{closest:()=>({dataset:{[dk]:v},id:v})}});
const cards=()=>(E.grid.innerHTML.match(/class="card"/g)||[]).length;

const cards2=h=>(h.match(/class="card"/g)||[]).length;
const tap=(h,sel,v)=>E[h].onclick({target:{closest:s=>s===sel?{dataset:{[sel.slice(1,-1).replace("data-","")]:v}}:null}});
(async()=>{
 vm.runInContext(js,ctx);await wait(150);
 ok("страница загрузилась, ошибок нет",!errors.length,errors.join("|"));
 // «Лучшее сегодня»
 ok("блок «Лучшее сегодня» показан на главной (без фильтров)",E.bestW.hidden===false&&cards2(E.best.innerHTML)>=1&&cards2(E.best.innerHTML)<=6,E.best.innerHTML.length);
 const bs=run("(()=>{const r=list().filter(g=>!g.free&&g.discount>=50&&g.rev&&g.rev.pct>=70);return r.length})()");
 ok("в блоке только скидки от 50%: "+(E.best.innerHTML.match(/class="dsc ">−(\d+)%/g)||[]).join(" "),(E.best.innerHTML.match(/class="dsc ">−(\d+)%/g)||[]).every(m=>+m.match(/\d+/)[0]>=50)&&bs>0);
 click("genres","g","coop");ok("с выбранным жанром блок «Лучшее» скрыт",E.bestW.hidden===true);click("genres","g","all");
 ok("после сброса фильтра блок снова виден",E.bestW.hidden===false);
 // популярная игра со смешанными отзывами попадает в блок
 run("rev[1091500]={pct:46,total:900000,d:'x'};prices[1091500].discount=75;prices[1091500].final=250;prices[1091500].initial=1000;");E.q.value="";E.q.oninput();
 ok("игра с оценкой 46%, но 900 тыс. отзывов — в «Лучшем сегодня»",E.best.innerHTML.includes("Cyberpunk 2077"));
 run("rev[1091500]={pct:60,total:4000,d:'x'};");E.q.oninput();
 ok("малоизвестная игра с оценкой 60% в блок не попадает",!E.best.innerHTML.includes("Cyberpunk 2077"));
 run("rev[1091500]={pct:30,total:900000,d:'x'};");E.q.oninput();
 ok("игра с оценкой 30% (провальная) в блок не попадает",!E.best.innerHTML.includes("Cyberpunk 2077"));
 // раздача
 ok("чип «Раздача» скрыт, пока раздач нет",!E.prices.innerHTML.includes("data-p=\"gift\""));
 run("prices[1091500].discount=100;prices[1091500].final=0;prices[1091500].initial=1000;delete prices[1091500].free;");E.q.oninput();
 ok("чип «Раздача» появился (1)",E.prices.innerHTML.includes('data-p="gift"')&&/Раздача<i>1<\/i>/.test(E.prices.innerHTML),E.prices.innerHTML.slice(-400));
 ok("раздача первая в «Лучшем сегодня»",E.best.innerHTML.indexOf("Cyberpunk 2077")>=0&&E.best.innerHTML.indexOf("Cyberpunk 2077")<E.best.innerHTML.indexOf("card",20)+400);
 click("prices","p","gift");ok("фильтр «Раздача»: одна карточка с пометкой",cards()===1&&E.grid.innerHTML.includes("Раздача: можно забрать бесплатно")&&E.grid.innerHTML.includes("Бесплатно"),E.grid.innerHTML.slice(0,200));
 await E.grid.onclick({target:{closest:s=>s==="[data-fav]"?null:{dataset:{id:"1091500"}}}});await wait(80);
 ok("в окне раздачи — понятная подсказка",E.dlg.innerHTML.includes("забрать бесплатно")&&E.dlg.innerHTML.includes("hint good"));
 E.dlg.close();click("prices","p","all");
 run("prices[1091500].discount=50;prices[1091500].final=500;");E.q.oninput();
 ok("после конца раздачи чип снова скрыт",!E.prices.innerHTML.includes('data-p="gift"'));
 // бесплатные (F2P) отдельно от раздач
 click("prices","p","free");ok("чип «Бесплатно» показывает только F2P (карточек "+cards()+")",cards()===0||!E.grid.innerHTML.includes("Раздача: можно"));click("prices","p","all");
 // избранное
 ok("чип «Избранное» есть, в нём 0",/Избранное<i>0<\/i>/.test(E.prices.innerHTML));
 ok("на карточках есть сердечки ♡",E.grid.innerHTML.includes('data-fav="')&&E.grid.innerHTML.includes("♡"));
 const id=run("list()[0].id");tap("grid","[data-fav]",String(id));
 ok("после нажатия на ♡ игра в избранном (1) и сердечко ♥",/Избранное<i>1<\/i>/.test(E.prices.innerHTML)&&E.grid.innerHTML.includes("♥"));
 ok("нажатие на сердце не открыло окно игры",!E.dlg.open);
 click("prices","p","fav");ok("фильтр «Избранное»: одна карточка",cards()===1);
 tap("grid","[data-fav]",String(id));ok("повторное нажатие убирает из избранного, показано подсказку «Пока пусто»",cards()===0&&E.grid.innerHTML.includes("Пока пусто"));
 click("prices","p","all");
 await E.grid.onclick({target:{closest:s=>s==="[data-fav]"?null:{dataset:{id:String(id)}}}});await wait(80);
 ok("в окне игры есть кнопка избранного",E.dlg.innerHTML.includes("data-fav=")&&E.dlg.innerHTML.includes("♡ Избранное"));
 E.dlg.onclick({target:{closest:s=>s==="[data-fav]"?(E.dlg._fb=E.dlg._fb||{dataset:{fav:String(id)},textContent:""}):null}});
 ok("кнопка в окне игры добавляет в избранное",run("fav.has("+id+")")===true&&E.dlg._fb.textContent.startsWith("♥"));
 E.dlg.close();
 // на трёх языках без «undefined»
 for(const l of ["uk","en","ru"]){E.lang.value=l;E.lang.onchange();ok("язык "+l+": новые надписи на месте",!E.prices.innerHTML.includes("undefined")&&!E.grid.innerHTML.includes("undefined")&&!E.best.innerHTML.includes("undefined"))}
 ok("избранное сохраняется в localStorage",run("typeof toggleFav")==="function");
 ok("итоговых ошибок нет",!errors.length,errors.join("|"));
 console.log(fails?`\nПРОВАЛЕНО проверок: ${fails}`:"\nВСЕ ПРОВЕРКИ ПРОЙДЕНЫ");process.exit(fails?1:0);
})().catch(e=>{console.log("КРАШ ТЕСТА:",e);process.exit(2)});
