var t1="M7 11H9V13H7V11M21 5V19C21 20.11 20.11 21 19 21H5C3.89 21 3 20.1 3 19V5C3 3.9 3.9 3 5 3H6V1H8V3H16V1H18V3H19C20.11 3 21 3.9 21 5M5 7H19V5H5V7M19 19V9H5V19H19M15 13V11H17V13H15M11 13V11H13V13H11M7 15H9V17H7V15M15 17V15H17V17H15M11 17V15H13V17H11Z";var A1="M18,6H8.83L14.83,12L8.83,18H18V20H6V18L12,12L6,6V4H18V6Z";var D=globalThis,E=D.ShadowRoot&&(D.ShadyCSS===void 0||D.ShadyCSS.nativeShadow)&&"adoptedStyleSheets"in Document.prototype&&"replace"in CSSStyleSheet.prototype,G=Symbol(),i1=new WeakMap,k=class{constructor(C,H,V){if(this._$cssResult$=!0,V!==G)throw Error("CSSResult is not constructable. Use `unsafeCSS` or `css` instead.");this.cssText=C,this.t=H}get styleSheet(){let C=this.o,H=this.t;if(E&&C===void 0){let V=H!==void 0&&H.length===1;V&&(C=i1.get(H)),C===void 0&&((this.o=C=new CSSStyleSheet).replaceSync(this.cssText),V&&i1.set(H,C))}return C}toString(){return this.cssText}},_=r=>new k(typeof r=="string"?r:r+"",void 0,G),Z=(r,...C)=>{let H=r.length===1?r[0]:C.reduce((V,L,M)=>V+(e=>{if(e._$cssResult$===!0)return e.cssText;if(typeof e=="number")return e;throw Error("Value passed to 'css' function must be a 'css' function result: "+e+". Use 'unsafeCSS' to pass non-literal values, but take care to ensure page security.")})(L)+r[M+1],r[0]);return new k(H,r,G)},o1=(r,C)=>{if(E)r.adoptedStyleSheets=C.map(H=>H instanceof CSSStyleSheet?H:H.styleSheet);else for(let H of C){let V=document.createElement("style"),L=D.litNonce;L!==void 0&&V.setAttribute("nonce",L),V.textContent=H.cssText,r.appendChild(V)}},Q=E?r=>r:r=>r instanceof CSSStyleSheet?(C=>{let H="";for(let V of C.cssRules)H+=V.cssText;return _(H)})(r):r;var{is:U1,defineProperty:G1,getOwnPropertyDescriptor:Q1,getOwnPropertyNames:z1,getOwnPropertySymbols:K1,getPrototypeOf:q1}=Object,W=globalThis,a1=W.trustedTypes,j1=a1?a1.emptyScript:"",Y1=W.reactiveElementPolyfillSupport,y=(r,C)=>r,z={toAttribute(r,C){switch(C){case Boolean:r=r?j1:null;break;case Object:case Array:r=r==null?r:JSON.stringify(r)}return r},fromAttribute(r,C){let H=r;switch(C){case Boolean:H=r!==null;break;case Number:H=r===null?null:Number(r);break;case Object:case Array:try{H=JSON.parse(r)}catch{H=null}}return H}},p1=(r,C)=>!U1(r,C),d1={attribute:!0,type:String,converter:z,reflect:!1,useDefault:!1,hasChanged:p1};Symbol.metadata??=Symbol("metadata"),W.litPropertyMetadata??=new WeakMap;var x=class extends HTMLElement{static addInitializer(C){this._$Ei(),(this.l??=[]).push(C)}static get observedAttributes(){return this.finalize(),this._$Eh&&[...this._$Eh.keys()]}static createProperty(C,H=d1){if(H.state&&(H.attribute=!1),this._$Ei(),this.prototype.hasOwnProperty(C)&&((H=Object.create(H)).wrapped=!0),this.elementProperties.set(C,H),!H.noAccessor){let V=Symbol(),L=this.getPropertyDescriptor(C,V,H);L!==void 0&&G1(this.prototype,C,L)}}static getPropertyDescriptor(C,H,V){let{get:L,set:M}=Q1(this.prototype,C)??{get(){return this[H]},set(e){this[H]=e}};return{get:L,set(e){let A=L?.call(this);M?.call(this,e),this.requestUpdate(C,A,V)},configurable:!0,enumerable:!0}}static getPropertyOptions(C){return this.elementProperties.get(C)??d1}static _$Ei(){if(this.hasOwnProperty(y("elementProperties")))return;let C=q1(this);C.finalize(),C.l!==void 0&&(this.l=[...C.l]),this.elementProperties=new Map(C.elementProperties)}static finalize(){if(this.hasOwnProperty(y("finalized")))return;if(this.finalized=!0,this._$Ei(),this.hasOwnProperty(y("properties"))){let H=this.properties,V=[...z1(H),...K1(H)];for(let L of V)this.createProperty(L,H[L])}let C=this[Symbol.metadata];if(C!==null){let H=litPropertyMetadata.get(C);if(H!==void 0)for(let[V,L]of H)this.elementProperties.set(V,L)}this._$Eh=new Map;for(let[H,V]of this.elementProperties){let L=this._$Eu(H,V);L!==void 0&&this._$Eh.set(L,H)}this.elementStyles=this.finalizeStyles(this.styles)}static finalizeStyles(C){let H=[];if(Array.isArray(C)){let V=new Set(C.flat(1/0).reverse());for(let L of V)H.unshift(Q(L))}else C!==void 0&&H.push(Q(C));return H}static _$Eu(C,H){let V=H.attribute;return V===!1?void 0:typeof V=="string"?V:typeof C=="string"?C.toLowerCase():void 0}constructor(){super(),this._$Ep=void 0,this.isUpdatePending=!1,this.hasUpdated=!1,this._$Em=null,this._$Ev()}_$Ev(){this._$ES=new Promise(C=>this.enableUpdating=C),this._$AL=new Map,this._$E_(),this.requestUpdate(),this.constructor.l?.forEach(C=>C(this))}addController(C){(this._$EO??=new Set).add(C),this.renderRoot!==void 0&&this.isConnected&&C.hostConnected?.()}removeController(C){this._$EO?.delete(C)}_$E_(){let C=new Map,H=this.constructor.elementProperties;for(let V of H.keys())this.hasOwnProperty(V)&&(C.set(V,this[V]),delete this[V]);C.size>0&&(this._$Ep=C)}createRenderRoot(){let C=this.shadowRoot??this.attachShadow(this.constructor.shadowRootOptions);return o1(C,this.constructor.elementStyles),C}connectedCallback(){this.renderRoot??=this.createRenderRoot(),this.enableUpdating(!0),this._$EO?.forEach(C=>C.hostConnected?.())}enableUpdating(C){}disconnectedCallback(){this._$EO?.forEach(C=>C.hostDisconnected?.())}attributeChangedCallback(C,H,V){this._$AK(C,V)}_$ET(C,H){let V=this.constructor.elementProperties.get(C),L=this.constructor._$Eu(C,V);if(L!==void 0&&V.reflect===!0){let M=(V.converter?.toAttribute!==void 0?V.converter:z).toAttribute(H,V.type);this._$Em=C,M==null?this.removeAttribute(L):this.setAttribute(L,M),this._$Em=null}}_$AK(C,H){let V=this.constructor,L=V._$Eh.get(C);if(L!==void 0&&this._$Em!==L){let M=V.getPropertyOptions(L),e=typeof M.converter=="function"?{fromAttribute:M.converter}:M.converter?.fromAttribute!==void 0?M.converter:z;this._$Em=L;let A=e.fromAttribute(H,M.type);this[L]=A??this._$Ej?.get(L)??A,this._$Em=null}}requestUpdate(C,H,V,L=!1,M){if(C!==void 0){let e=this.constructor;if(L===!1&&(M=this[C]),V??=e.getPropertyOptions(C),!((V.hasChanged??p1)(M,H)||V.useDefault&&V.reflect&&M===this._$Ej?.get(C)&&!this.hasAttribute(e._$Eu(C,V))))return;this.C(C,H,V)}this.isUpdatePending===!1&&(this._$ES=this._$EP())}C(C,H,{useDefault:V,reflect:L,wrapped:M},e){V&&!(this._$Ej??=new Map).has(C)&&(this._$Ej.set(C,e??H??this[C]),M!==!0||e!==void 0)||(this._$AL.has(C)||(this.hasUpdated||V||(H=void 0),this._$AL.set(C,H)),L===!0&&this._$Em!==C&&(this._$Eq??=new Set).add(C))}async _$EP(){this.isUpdatePending=!0;try{await this._$ES}catch(H){Promise.reject(H)}let C=this.scheduleUpdate();return C!=null&&await C,!this.isUpdatePending}scheduleUpdate(){return this.performUpdate()}performUpdate(){if(!this.isUpdatePending)return;if(!this.hasUpdated){if(this.renderRoot??=this.createRenderRoot(),this._$Ep){for(let[L,M]of this._$Ep)this[L]=M;this._$Ep=void 0}let V=this.constructor.elementProperties;if(V.size>0)for(let[L,M]of V){let{wrapped:e}=M,A=this[L];e!==!0||this._$AL.has(L)||A===void 0||this.C(L,void 0,M,A)}}let C=!1,H=this._$AL;try{C=this.shouldUpdate(H),C?(this.willUpdate(H),this._$EO?.forEach(V=>V.hostUpdate?.()),this.update(H)):this._$EM()}catch(V){throw C=!1,this._$EM(),V}C&&this._$AE(H)}willUpdate(C){}_$AE(C){this._$EO?.forEach(H=>H.hostUpdated?.()),this.hasUpdated||(this.hasUpdated=!0,this.firstUpdated(C)),this.updated(C)}_$EM(){this._$AL=new Map,this.isUpdatePending=!1}get updateComplete(){return this.getUpdateComplete()}getUpdateComplete(){return this._$ES}shouldUpdate(C){return!0}update(C){this._$Eq&&=this._$Eq.forEach(H=>this._$ET(H,this[H])),this._$EM()}updated(C){}firstUpdated(C){}};x.elementStyles=[],x.shadowRootOptions={mode:"open"},x[y("elementProperties")]=new Map,x[y("finalized")]=new Map,Y1?.({ReactiveElement:x}),(W.reactiveElementVersions??=[]).push("2.1.2");var C1=globalThis,m1=r=>r,N=C1.trustedTypes,v1=N?N.createPolicy("lit-html",{createHTML:r=>r}):void 0,u1="$lit$",l=`lit$${Math.random().toFixed(9).slice(2)}$`,s1="?"+l,X1=`<${s1}>`,s=document,P=()=>s.createComment(""),w=r=>r===null||typeof r!="object"&&typeof r!="function",H1=Array.isArray,J1=r=>H1(r)||typeof r?.[Symbol.iterator]=="function",K=`[ 	
\f\r]`,B=/<(?:(!--|\/[^a-zA-Z])|(\/?[a-zA-Z][^>\s]*)|(\/?$))/g,x1=/-->/g,n1=/>/g,S=RegExp(`>|${K}(?:([^\\s"'>=/]+)(${K}*=${K}*(?:[^ 	
\f\r"'\`<>=]|("|')|))|$)`,"g"),l1=/'/g,Z1=/"/g,c1=/^(?:script|style|textarea|title)$/i,V1=r=>(C,...H)=>({_$litType$:r,strings:C,values:H}),p=V1(1),s2=V1(2),c2=V1(3),c=Symbol.for("lit-noChange"),d=Symbol.for("lit-nothing"),S1=new WeakMap,u=s.createTreeWalker(s,129);function O1(r,C){if(!H1(r)||!r.hasOwnProperty("raw"))throw Error("invalid template strings array");return v1!==void 0?v1.createHTML(C):C}var C2=(r,C)=>{let H=r.length-1,V=[],L,M=C===2?"<svg>":C===3?"<math>":"",e=B;for(let A=0;A<H;A++){let t=r[A],i,o,a=-1,v=0;for(;v<t.length&&(e.lastIndex=v,o=e.exec(t),o!==null);)v=e.lastIndex,e===B?o[1]==="!--"?e=x1:o[1]!==void 0?e=n1:o[2]!==void 0?(c1.test(o[2])&&(L=RegExp("</"+o[2],"g")),e=S):o[3]!==void 0&&(e=S):e===S?o[0]===">"?(e=L??B,a=-1):o[1]===void 0?a=-2:(a=e.lastIndex-o[2].length,i=o[1],e=o[3]===void 0?S:o[3]==='"'?Z1:l1):e===Z1||e===l1?e=S:e===x1||e===n1?e=B:(e=S,L=void 0);let n=e===S&&r[A+1].startsWith("/>")?" ":"";M+=e===B?t+X1:a>=0?(V.push(i),t.slice(0,a)+u1+t.slice(a)+l+n):t+l+(a===-2?A:n)}return[O1(r,M+(r[H]||"<?>")+(C===2?"</svg>":C===3?"</math>":"")),V]},b=class r{constructor({strings:C,_$litType$:H},V){let L;this.parts=[];let M=0,e=0,A=C.length-1,t=this.parts,[i,o]=C2(C,H);if(this.el=r.createElement(i,V),u.currentNode=this.el.content,H===2||H===3){let a=this.el.content.firstChild;a.replaceWith(...a.childNodes)}for(;(L=u.nextNode())!==null&&t.length<A;){if(L.nodeType===1){if(L.hasAttributes())for(let a of L.getAttributeNames())if(a.endsWith(u1)){let v=o[e++],n=L.getAttribute(a).split(l),R=/([.?@])?(.*)/.exec(v);t.push({type:1,index:M,name:R[2],strings:n,ctor:R[1]==="."?j:R[1]==="?"?Y:R[1]==="@"?X:h}),L.removeAttribute(a)}else a.startsWith(l)&&(t.push({type:6,index:M}),L.removeAttribute(a));if(c1.test(L.tagName)){let a=L.textContent.split(l),v=a.length-1;if(v>0){L.textContent=N?N.emptyScript:"";for(let n=0;n<v;n++)L.append(a[n],P()),u.nextNode(),t.push({type:2,index:++M});L.append(a[v],P())}}}else if(L.nodeType===8)if(L.data===s1)t.push({type:2,index:M});else{let a=-1;for(;(a=L.data.indexOf(l,a+1))!==-1;)t.push({type:7,index:M}),a+=l.length-1}M++}}static createElement(C,H){let V=s.createElement("template");return V.innerHTML=C,V}};function O(r,C,H=r,V){if(C===c)return C;let L=V!==void 0?H._$Co?.[V]:H._$Cl,M=w(C)?void 0:C._$litDirective$;return L?.constructor!==M&&(L?._$AO?.(!1),M===void 0?L=void 0:(L=new M(r),L._$AT(r,H,V)),V!==void 0?(H._$Co??=[])[V]=L:H._$Cl=L),L!==void 0&&(C=O(r,L._$AS(r,C.values),L,V)),C}var q=class{constructor(C,H){this._$AV=[],this._$AN=void 0,this._$AD=C,this._$AM=H}get parentNode(){return this._$AM.parentNode}get _$AU(){return this._$AM._$AU}u(C){let{el:{content:H},parts:V}=this._$AD,L=(C?.creationScope??s).importNode(H,!0);u.currentNode=L;let M=u.nextNode(),e=0,A=0,t=V[0];for(;t!==void 0;){if(e===t.index){let i;t.type===2?i=new T(M,M.nextSibling,this,C):t.type===1?i=new t.ctor(M,t.name,t.strings,this,C):t.type===6&&(i=new J(M,this,C)),this._$AV.push(i),t=V[++A]}e!==t?.index&&(M=u.nextNode(),e++)}return u.currentNode=s,L}p(C){let H=0;for(let V of this._$AV)V!==void 0&&(V.strings!==void 0?(V._$AI(C,V,H),H+=V.strings.length-2):V._$AI(C[H])),H++}},T=class r{get _$AU(){return this._$AM?._$AU??this._$Cv}constructor(C,H,V,L){this.type=2,this._$AH=d,this._$AN=void 0,this._$AA=C,this._$AB=H,this._$AM=V,this.options=L,this._$Cv=L?.isConnected??!0}get parentNode(){let C=this._$AA.parentNode,H=this._$AM;return H!==void 0&&C?.nodeType===11&&(C=H.parentNode),C}get startNode(){return this._$AA}get endNode(){return this._$AB}_$AI(C,H=this){C=O(this,C,H),w(C)?C===d||C==null||C===""?(this._$AH!==d&&this._$AR(),this._$AH=d):C!==this._$AH&&C!==c&&this._(C):C._$litType$!==void 0?this.$(C):C.nodeType!==void 0?this.T(C):J1(C)?this.k(C):this._(C)}O(C){return this._$AA.parentNode.insertBefore(C,this._$AB)}T(C){this._$AH!==C&&(this._$AR(),this._$AH=this.O(C))}_(C){this._$AH!==d&&w(this._$AH)?this._$AA.nextSibling.data=C:this.T(s.createTextNode(C)),this._$AH=C}$(C){let{values:H,_$litType$:V}=C,L=typeof V=="number"?this._$AC(C):(V.el===void 0&&(V.el=b.createElement(O1(V.h,V.h[0]),this.options)),V);if(this._$AH?._$AD===L)this._$AH.p(H);else{let M=new q(L,this),e=M.u(this.options);M.p(H),this.T(e),this._$AH=M}}_$AC(C){let H=S1.get(C.strings);return H===void 0&&S1.set(C.strings,H=new b(C)),H}k(C){H1(this._$AH)||(this._$AH=[],this._$AR());let H=this._$AH,V,L=0;for(let M of C)L===H.length?H.push(V=new r(this.O(P()),this.O(P()),this,this.options)):V=H[L],V._$AI(M),L++;L<H.length&&(this._$AR(V&&V._$AB.nextSibling,L),H.length=L)}_$AR(C=this._$AA.nextSibling,H){for(this._$AP?.(!1,!0,H);C!==this._$AB;){let V=m1(C).nextSibling;m1(C).remove(),C=V}}setConnected(C){this._$AM===void 0&&(this._$Cv=C,this._$AP?.(C))}},h=class{get tagName(){return this.element.tagName}get _$AU(){return this._$AM._$AU}constructor(C,H,V,L,M){this.type=1,this._$AH=d,this._$AN=void 0,this.element=C,this.name=H,this._$AM=L,this.options=M,V.length>2||V[0]!==""||V[1]!==""?(this._$AH=Array(V.length-1).fill(new String),this.strings=V):this._$AH=d}_$AI(C,H=this,V,L){let M=this.strings,e=!1;if(M===void 0)C=O(this,C,H,0),e=!w(C)||C!==this._$AH&&C!==c,e&&(this._$AH=C);else{let A=C,t,i;for(C=M[0],t=0;t<M.length-1;t++)i=O(this,A[V+t],H,t),i===c&&(i=this._$AH[t]),e||=!w(i)||i!==this._$AH[t],i===d?C=d:C!==d&&(C+=(i??"")+M[t+1]),this._$AH[t]=i}e&&!L&&this.j(C)}j(C){C===d?this.element.removeAttribute(this.name):this.element.setAttribute(this.name,C??"")}},j=class extends h{constructor(){super(...arguments),this.type=3}j(C){this.element[this.name]=C===d?void 0:C}},Y=class extends h{constructor(){super(...arguments),this.type=4}j(C){this.element.toggleAttribute(this.name,!!C&&C!==d)}},X=class extends h{constructor(C,H,V,L,M){super(C,H,V,L,M),this.type=5}_$AI(C,H=this){if((C=O(this,C,H,0)??d)===c)return;let V=this._$AH,L=C===d&&V!==d||C.capture!==V.capture||C.once!==V.once||C.passive!==V.passive,M=C!==d&&(V===d||L);L&&this.element.removeEventListener(this.name,this,V),M&&this.element.addEventListener(this.name,this,C),this._$AH=C}handleEvent(C){typeof this._$AH=="function"?this._$AH.call(this.options?.host??this.element,C):this._$AH.handleEvent(C)}},J=class{constructor(C,H,V){this.element=C,this.type=6,this._$AN=void 0,this._$AM=H,this.options=V}get _$AU(){return this._$AM._$AU}_$AI(C){O(this,C)}};var H2=C1.litHtmlPolyfillSupport;H2?.(b,T),(C1.litHtmlVersions??=[]).push("3.3.3");var h1=(r,C,H)=>{let V=H?.renderBefore??C,L=V._$litPart$;if(L===void 0){let M=H?.renderBefore??null;V._$litPart$=L=new T(C.insertBefore(P(),M),M,void 0,H??{})}return L._$AI(r),L};var L1=globalThis,m=class extends x{constructor(){super(...arguments),this.renderOptions={host:this},this._$Do=void 0}createRenderRoot(){let C=super.createRenderRoot();return this.renderOptions.renderBefore??=C.firstChild,C}update(C){let H=this.render();this.hasUpdated||(this.renderOptions.isConnected=this.isConnected),super.update(C),this._$Do=h1(H,this.renderRoot,this.renderOptions)}connectedCallback(){super.connectedCallback(),this._$Do?.setConnected(!0)}disconnectedCallback(){super.disconnectedCallback(),this._$Do?.setConnected(!1)}render(){return c}};m._$litElement$=!0,m.finalized=!0,L1.litElementHydrateSupport?.({LitElement:m});var V2=L1.litElementPolyfillSupport;V2?.({LitElement:m});(L1.litElementVersions??=[]).push("4.2.2");var g1={title:"Balance","category.pv":"PV plant","category.heat_pump":"Heat pump","category.wallbox":"Electric car",show_yearly:"Show yearly figures",show_total:"Show totals",not_set_up:"Set up the Energy Payback integration to see what your PV plant, heat pump, and electric car have saved.",calculating_all:"The past is being computed \u2026",calculating:"Being computed \u2026",saved_invested:"{saved} saved, {invested} invested",saved_only:"{saved} saved",of_investment:"{percent} of {investment}",paid_off:"paid off",since:"since {date}",heat_estimated:"heat partly estimated",instead_heat_pump:"no extra cost entered",instead_wallbox:"no extra cost entered",instead_pv:"no purchase cost entered",in_the_plus_from:"In the plus from about {date}",in_the_plus:"In the plus",yearly_after_twelve:"Yearly figures after twelve months of data.",yearly_from:"Yearly figure from {date}",pays_off_in:"pays off in about {years}",years_one:"1 year",years_other:"{count} years",under_one_year:"less than a year",return_per_year:"paid off, {percent} return per year",instead_of_gas:"instead of gas",instead_of_oil:"instead of oil",instead_of_fuel:"instead of fuel",per_year:"{amount}/year",gas:"Gas {price}/kWh",oil:"Oil {price}/l",fuel:"Fuel {price}/l",prices_link:"Change the prices",progress:"{name}: {percent} of the investment saved",history_title:"Savings",history_title_years:"Savings per year",history_total:"Total",history_no_chart:"The chart is only shown in Home Assistant.",history_failed:"The statistics could not be loaded.",history_empty:"No savings in this period."},L2={title:"Bilanz","category.pv":"PV-Anlage","category.heat_pump":"W\xE4rmepumpe","category.wallbox":"E-Auto",show_yearly:"Jahreswerte zeigen",show_total:"Gesamtwerte zeigen",not_set_up:"Richte die Integration Energy Payback ein, um zu sehen, was PV-Anlage, W\xE4rmepumpe und E-Auto gespart haben.",calculating_all:"Die Vergangenheit wird nachgerechnet \u2026",calculating:"Wird berechnet \u2026",saved_invested:"{saved} gespart, {invested} investiert",saved_only:"{saved} gespart",of_investment:"{percent} von {investment}",paid_off:"amortisiert",since:"seit {date}",heat_estimated:"W\xE4rme teilweise gesch\xE4tzt",instead_heat_pump:"ohne Mehrkosten",instead_wallbox:"ohne Mehrkosten",instead_pv:"ohne Anschaffungskosten",in_the_plus_from:"Im Plus ab etwa {date}",in_the_plus:"Im Plus",yearly_after_twelve:"Jahreswerte gibt es nach zw\xF6lf Monaten Daten.",yearly_from:"Jahreswert ab {date}",pays_off_in:"amortisiert in etwa {years}",years_one:"1 Jahr",years_other:"{count} Jahren",under_one_year:"weniger als einem Jahr",return_per_year:"amortisiert, {percent} Rendite pro Jahr",instead_of_gas:"statt Gas",instead_of_oil:"statt \xD6l",instead_of_fuel:"statt Sprit",per_year:"{amount}/Jahr",gas:"Gas {price}/kWh",oil:"\xD6l {price}/l",fuel:"Sprit {price}/l",prices_link:"Preise \xE4ndern",progress:"{name}: {percent} der Investition gespart",history_title:"Ersparnis",history_title_years:"Ersparnis pro Jahr",history_total:"Summe",history_no_chart:"Das Diagramm erscheint nur in Home Assistant.",history_failed:"Die Statistik konnte nicht geladen werden.",history_empty:"Keine Ersparnis in diesem Zeitraum."},M2={en:g1,de:L2};function I(r){let C=M2[r.split("-")[0]]??g1;return(H,V={})=>C[H].replace(/\{(\w+)\}/g,(L,M)=>V[M]??"")}var r1="energy_payback",M1=["pv","heat_pump","wallbox"];var $=r=>{if(r==null||r==="")return null;let C=Number(r);return Number.isFinite(C)?C:null},f1=r=>typeof r=="string"&&r?new Date(r):null;function F(r){let C=Object.values(r.entities??{}).filter(M=>M.platform===r1),H=(M,e)=>C.find(A=>A.device_id===M&&A.translation_key===e),V=M=>M?$(r.states[M]?.state):null,L=[];for(let M of C){if(M.translation_key!=="saving")continue;let e=r.states[M.entity_id];if(!e||e.state==="unavailable")continue;let A=e.attributes,t=A.category;M1.includes(t)&&L.push({category:t,savingEntity:M.entity_id,calculating:A.calculating===!0,saving:$(e.state),investment:$(A.investment),payback:V(H(M.device_id,"payback")?.entity_id),perYear:V(H(M.device_id,"saving_per_year")?.entity_id),countingSince:f1(A.counting_since),yearlyFrom:f1(A.yearly_from),price:$(A.price),heating:A.heating==="gas"||A.heating==="oil"?A.heating:null,heatEstimated:A.heat_estimated===!0})}return L.sort((M,e)=>M1.indexOf(M.category)-M1.indexOf(e.category))}function k1(r,C=new Date){let H=r.some(o=>o.calculating),V=r.reduce((o,a)=>o+(a.saving??0),0),L=r.reduce((o,a)=>o+(a.investment??0),0),M=!H&&r.length>0,e=M?V-L:null,A=r.every(o=>o.perYear!==null),t=M&&A?r.reduce((o,a)=>o+(a.perYear??0),0):null,i=null;return e!==null&&t!==null&&(e>=0?i=C:t>0&&(i=new Date(C.getTime()+-e/t*12*26298e5))),{saved:V,invested:L,balance:e,perYear:t,inThePlusFrom:i,calculating:H}}function y1(r){let{investment:C,saving:H,perYear:V}=r;return C===null||C<=0||H===null||V===null||V<=0?null:Math.max(0,(C-H)/V)}function B1(r){let{investment:C,saving:H,perYear:V}=r;return C===null||C<=0||H===null||V===null||H<C?null:V/C*100}var U=Z`
  :host {
    --energy-payback-pv-color: var(--energy-solar-color, #ff9800);
    --energy-payback-heat-pump-color: var(--energy-gas-color, #8e021b);
    --energy-payback-wallbox-color: var(--energy-non-fossil-color, #0f9d58);
  }
  ha-card {
    height: 100%;
    overflow: hidden;
  }
  .header {
    display: flex;
    align-items: center;
    gap: 8px;
    padding: 12px 8px 0 16px;
  }
  .title {
    flex: 1;
    min-width: 0;
    margin: 0;
    font-size: var(--ha-card-header-font-size, 24px);
    font-weight: var(--ha-font-weight-normal, 400);
    line-height: 32px;
    letter-spacing: -0.012em;
    color: var(--ha-card-header-color, var(--primary-text-color));
  }
  .chip {
    font-size: 14px;
    font-weight: 500;
    line-height: 20px;
    padding: 4px 8px;
    border-radius: 8px;
    border: 1px solid var(--divider-color);
    white-space: nowrap;
    color: var(--primary-text-color);
  }
  .summary {
    margin: 0;
    padding: 12px 16px 8px;
    color: var(--secondary-text-color);
  }
  .summary:empty {
    display: none;
  }
`;var P1="energy-payback-card-view",r2=()=>{try{return localStorage.getItem(P1)==="yearly"?"yearly":"total"}catch{return"total"}},g=class extends m{constructor(){super(...arguments);this._view=r2()}static getStubConfig(){return{}}static getConfigForm(){return{schema:[]}}setConfig(H){}getCardSize(){return 4}getGridOptions(){return{columns:12,min_columns:6}}get _localize(){return I(this.hass?.locale?.language??this.hass?.language??"en")}get _language(){return this.hass?.locale?.language??"en"}_money(H,V=!1){return new Intl.NumberFormat(this._language,{style:"currency",currency:this.hass?.config.currency??"EUR",maximumFractionDigits:0,minimumFractionDigits:0,signDisplay:V?"exceptZero":"auto"}).format(H)}_price(H){return new Intl.NumberFormat(this._language,{style:"currency",currency:this.hass?.config.currency??"EUR",maximumFractionDigits:4,minimumFractionDigits:2}).format(H)}_percent(H){return new Intl.NumberFormat(this._language,{style:"percent",maximumFractionDigits:0}).format(H/100)}_month(H){return new Intl.DateTimeFormat(this._language,{month:"long",year:"numeric"}).format(H)}_years(H){let V=this._localize;if(H<1)return V("under_one_year");let L=Math.round(H);return L===1?V("years_one"):V("years_other",{count:String(L)})}_toggleView(){this._view=this._view==="total"?"yearly":"total";try{localStorage.setItem(P1,this._view)}catch{}}_openIntegration(){history.pushState(null,"",`/config/integrations/integration/${r1}`),window.dispatchEvent(new CustomEvent("location-changed"))}render(){let H=this._localize;if(!this.hass)return p``;let V=F(this.hass);if(!V.length)return p`<ha-card>
        <div class="header"><h2 class="title">${H("title")}</h2></div>
        <p class="summary">${H("not_set_up")}</p>
      </ha-card>`;let L=k1(V),M=this._view==="yearly";return p`<ha-card>
      <div class="header">
        <h2 class="title">${H("title")}</h2>
        ${this._chip(L,M)}
        <button
          class="toggle"
          type="button"
          aria-label=${H(M?"show_total":"show_yearly")}
          title=${H(M?"show_total":"show_yearly")}
          @click=${this._toggleView}
        >
          <svg viewBox="0 0 24 24" aria-hidden="true">
            <path d=${M?A1:t1}></path>
          </svg>
        </button>
      </div>
      <p class="summary">${this._summary(L,V,M)}</p>
      <ul class="rows">
        ${V.map(e=>this._row(e,M))}
      </ul>
      ${this._footer(V)}
    </ha-card>`}_chip(H,V){let L=this._localize,M=null;return V?H.perYear!==null&&(M=L("per_year",{amount:this._money(H.perYear,!0)})):H.balance!==null?M=this._money(H.balance,!0):H.calculating||(M=this._money(H.saved)),M===null?d:p`<span class="chip">${M}</span>`}_summary(H,V,L){let M=this._localize;return H.calculating?M("calculating_all"):L?H.inThePlusFrom===null?V.some(e=>e.perYear===null)?M("yearly_after_twelve"):"":H.balance!==null&&H.balance>=0?M("in_the_plus"):M("in_the_plus_from",{date:this._month(H.inThePlusFrom)}):H.invested>0?M("saved_invested",{saved:this._money(H.saved),invested:this._money(H.invested)}):M("saved_only",{saved:this._money(H.saved)})}_row(H,V){let L=this._localize,M=L(`category.${H.category}`),e="\u2013";return H.calculating||(V&&H.perYear!==null?e=L("per_year",{amount:this._money(H.perYear)}):!V&&H.saving!==null&&(e=this._money(H.saving))),p`<li class="row ${H.category}">
      <span class="swatch" aria-hidden="true"></span>
      <div class="row-body">
        <div class="line">
          <span>${M}</span>
          <span class="amount ${e==="\u2013"?"waiting":""}">${e}</span>
        </div>
        <div class="sub">
          ${H.calculating?L("calculating"):V?this._yearlyDetail(H):this._totalDetail(H,M)}
        </div>
        ${H.calculating?d:this._since(H)}
      </div>
    </li>`}_since(H){let V=this._localize,L=[];return H.countingSince&&L.push(V("since",{date:this._month(H.countingSince)})),H.heatEstimated&&L.push(V("heat_estimated")),L.length?p`<div class="sub since">${L.join(" \xB7 ")}</div>`:d}_totalDetail(H,V){let L=this._localize;if(H.investment&&H.payback!==null){let M=Math.max(0,H.payback),e=this._percent(H.payback);return p`<div class="meter">
        <div
          class="bar"
          role="progressbar"
          aria-label=${L("progress",{name:V,percent:e})}
          aria-valuemin="0"
          aria-valuemax="100"
          aria-valuenow=${Math.min(100,Math.round(M))}
        >
          <i style="width:${Math.min(100,M)}%"></i>
        </div>
        <span
          >${M>=100?L("paid_off"):L("of_investment",{percent:e,investment:this._money(H.investment)})}</span
        >
      </div>`}return L(`instead_${H.category}`)}_yearlyDetail(H){let V=this._localize;if(H.perYear===null)return H.yearlyFrom?V("yearly_from",{date:this._month(H.yearlyFrom)}):"";let L=B1(H);if(L!==null)return V("return_per_year",{percent:this._percent(L)});let M=y1(H);return M!==null?V("pays_off_in",{years:this._years(M)}):H.category==="heat_pump"?V(H.heating==="oil"?"instead_of_oil":"instead_of_gas"):H.category==="wallbox"?V("instead_of_fuel"):""}_footer(H){let V=this._localize,L=[];for(let M of H){if(M.price===null)continue;let e=this._price(M.price);M.category==="heat_pump"&&L.push(V(M.heating==="oil"?"oil":"gas",{price:e})),M.category==="wallbox"&&L.push(V("fuel",{price:e}))}return L.length?p`<div class="footer">
      <button
        class="prices"
        type="button"
        title=${V("prices_link")}
        aria-label=${`${V("prices_link")}: ${L.join(", ")}`}
        @click=${this._openIntegration}
      >
        ${L.join(" \xB7 ")}
      </button>
    </div>`:d}};g.properties={hass:{attribute:!1},_view:{state:!0}},g.styles=[U,Z`
      .toggle {
        flex: none;
        width: 40px;
        height: 40px;
        border: none;
        border-radius: 50%;
        background: none;
        color: var(--secondary-text-color);
        display: grid;
        place-items: center;
        cursor: pointer;
        padding: 0;
      }
      .toggle:hover {
        background: color-mix(in srgb, var(--primary-text-color) 8%, transparent);
      }
      .toggle:focus-visible,
      .prices:focus-visible {
        outline: 2px solid var(--primary-color);
        outline-offset: 2px;
      }
      .toggle svg {
        width: 24px;
        height: 24px;
        fill: currentColor;
      }
      .rows {
        list-style: none;
        margin: 0;
        padding: 0;
      }
      .row {
        display: flex;
        gap: 16px;
        padding: 12px 16px;
        border-bottom: 1px solid var(--divider-color);
      }
      .row:last-child {
        border-bottom: none;
      }
      .pv {
        --color: var(--energy-payback-pv-color);
      }
      .heat_pump {
        --color: var(--energy-payback-heat-pump-color);
      }
      .wallbox {
        --color: var(--energy-payback-wallbox-color);
      }
      .swatch {
        flex: none;
        width: 32px;
        height: 16px;
        margin-top: 2px;
        border-radius: 4px;
        border: 1px solid var(--color);
        background: color-mix(in srgb, var(--color) 50%, transparent);
      }
      .row-body {
        flex: 1;
        min-width: 0;
      }
      .line {
        display: flex;
        justify-content: space-between;
        gap: 8px;
        color: var(--primary-text-color);
      }
      .amount {
        flex: none;
        font-variant-numeric: tabular-nums;
      }
      .amount.waiting {
        color: var(--secondary-text-color);
      }
      .sub {
        margin-top: 6px;
        font-size: 12px;
        line-height: 16px;
        color: var(--secondary-text-color);
      }
      .sub:empty {
        display: none;
      }
      .sub.since {
        margin-top: 2px;
      }
      .meter {
        display: flex;
        align-items: center;
        gap: 8px;
      }
      .bar {
        flex: 1;
        height: 6px;
        border-radius: 4px;
        background: var(--divider-color);
        overflow: hidden;
      }
      .bar i {
        display: block;
        height: 100%;
        background: var(--color);
      }
      .meter span {
        flex: none;
        white-space: nowrap;
      }
      .footer {
        padding: 4px 8px 8px;
        border-top: 1px solid var(--divider-color);
      }
      .prices {
        font: inherit;
        font-size: 12px;
        line-height: 16px;
        color: var(--secondary-text-color);
        background: none;
        border: none;
        padding: 8px;
        border-radius: 4px;
        cursor: pointer;
        text-decoration: underline dotted;
        text-underline-offset: 3px;
        text-align: start;
      }
      .prices:hover {
        color: var(--primary-text-color);
      }
    `];var w1;function T1(){if(customElements.get("ha-chart-base"))return Promise.resolve(!0);let r=window.loadCardHelpers;return r?(w1??=(async()=>{try{(await r()).createCardElement({type:"statistics-graph",entities:[]})}catch{}let C=new Promise(H=>setTimeout(()=>H(!1),1e4));return Promise.race([customElements.whenDefined("ha-chart-base").then(()=>!0),C])})(),w1):Promise.resolve(!1)}var b1=r=>Math.round(r*255).toString(16).padStart(2,"0");function e2(r,C){let H=r.trim();if(/^#[0-9a-f]{6}$/i.test(H))return H+b1(C);if(/^#[0-9a-f]{3}$/i.test(H))return`#${[...H.slice(1)].map(L=>L+L).join("")}${b1(C)}`;let V=H.match(/^rgba?\(([^)]+)\)/i);if(V){let[L,M,e]=V[1].split(/[ ,/]+/).filter(Boolean);return`rgba(${L}, ${M}, ${e}, ${C})`}return H}var e1=r=>r.replace(/[&<>"']/g,C=>`&#${C.charCodeAt(0)};`),t2=r=>`<span style="display:inline-block;margin-right:4px;border-radius:10px;width:10px;height:10px;background-color:${r}"></span>`;function F1(r){let C=r.series.map((L,M)=>({id:L.id,type:"bar",name:L.name,stack:"savings",cursor:"default",barMaxWidth:50,color:e2(L.color,.5),itemStyle:{borderColor:L.color},data:L.values.map((e,A)=>{let t=r.series.slice(M+1).every(i=>Math.sign(i.values[A]??0)!==Math.sign(e??0));return{value:e,itemStyle:e?t?{borderRadius:e>0?[4,4,0,0]:[0,0,4,4]}:void 0:{borderWidth:0}}})})),H=L=>{let M=Array.isArray(L)?L:[L],e=M.filter(o=>o.value),A=document.createElement("div");if(!M.length)return A;let t=e.map(o=>`${t2(String(o.color??""))}${e1(o.seriesName??"")}: ${r.money(o.value??0)}`),i=e.reduce((o,a)=>o+(a.value??0),0);return A.innerHTML=`<b>${e1(r.labels[M[0].dataIndex]?.tooltip??"")}</b>`+(t.length?`<br>${t.join("<br>")}`:"")+(e.length>1?`<br><b>${e1(r.total)}: ${r.money(i)}</b>`:""),A},V={xAxis:{type:"category",data:r.labels.map(L=>L.axis),axisTick:{show:!1}},yAxis:{type:"value",name:r.unit,nameGap:2,nameTextStyle:{align:"left"},axisLabel:{formatter:r.tick},splitLine:{show:!0}},grid:{top:15,bottom:0,left:1,right:1,containLabel:!0},legend:{show:!0,type:"custom",data:r.series.map(L=>({id:L.id,name:L.name}))},tooltip:{trigger:"axis",axisPointer:{type:"shadow"},formatter:H}};return{data:C,options:V}}var A2=r=>!!r&&typeof r.subscribe=="function";function i2(r){let C=location.pathname.split("/")[1]??"",H=r;for(let V of[`_energy_${C}`,"_energy"])if(A2(H[V]))return H[V]}var o2=()=>new Date().setHours(24,0,0,0)-1;function R1(r,C){let H,V,L=0,M=()=>{let e=i2(r);if(e){H=e.subscribe(A=>C({start:new Date(A.start).getTime(),end:A.end?new Date(A.end).getTime():o2()}));return}L+=1,L===2&&C(null),L<20&&(V=window.setTimeout(M,500))};return M(),()=>{window.clearTimeout(V),H?.()}}function D1({start:r,end:C}){let H=C-r;return H<=2*864e5+36e5?"hour":H<=95*864e5?"day":H<=3*366*864e5?"month":"year"}var E1=r=>r==="year"?"month":r,a2=(r,C)=>{let H=new Date(r);return C==="hour"?H.setMinutes(0,0,0):(H.setHours(0,0,0,0),C==="day"||(H.setDate(1),C==="month")?H.getTime():H.setMonth(0))},d2=(r,C)=>{let H=new Date(r);return C==="hour"?H.setHours(H.getHours()+1):C==="day"?H.setDate(H.getDate()+1):C==="month"?H.setMonth(H.getMonth()+1):H.setFullYear(H.getFullYear()+1),H.getTime()};function _1({start:r,end:C},H){let V=[];for(let L=a2(r,H);L<=C&&V.length<400;L=d2(L,H))V.push(L);return V}function W1(r,C=new Date){let H=r.filter(L=>L!==null).map(L=>L.getFullYear()),V=Math.min(C.getFullYear(),...H);return{start:new Date(V,0,1).getTime(),end:new Date(C.getFullYear()+1,0,1).getTime()-1}}function N1(r,C,H){let V=C.map(()=>null),L=H==="hour"?0:12*36e5;for(let M of r??[]){if(M.change===null||M.change===void 0)continue;let e=(typeof M.start=="number"?M.start:Date.parse(M.start))+L,A=-1;for(let t=0;t<C.length&&C[t]<=e;t+=1)A=t;A<0||(V[A]=(V[A]??0)+M.change)}return V}var p2=300*1e3,I1="250px",m2={pv:["--energy-payback-pv-color","#ff9800"],heat_pump:["--energy-payback-heat-pump-color","#8e021b"],wallbox:["--energy-payback-wallbox-color","#0f9d58"]},f=class extends m{static getStubConfig(){return{}}static getConfigForm(){return{schema:[]}}setConfig(C){}getCardSize(){return 5}getGridOptions(){return{columns:12,min_columns:6}}connectedCallback(){super.connectedCallback(),this._follow()}disconnectedCallback(){super.disconnectedCallback(),this._unfollow?.(),this._unfollow=void 0}get _localize(){return I(this.hass?.locale?.language??this.hass?.language??"en")}get _language(){return this.hass?.locale?.language??"en"}_money(C,H=Math.abs(C)<100){return new Intl.NumberFormat(this._language,{style:"currency",currency:this.hass?.config.currency??"EUR",maximumFractionDigits:H?2:0,minimumFractionDigits:H?2:0}).format(C)}_currencySymbol(){return new Intl.NumberFormat(this._language,{style:"currency",currency:this.hass?.config.currency??"EUR"}).formatToParts(0).find(C=>C.type==="currency")?.value??""}_follow(){this._unfollow||!this.isConnected||!this.hass?.connection||(this._unfollow=R1(this.hass.connection,C=>{this._selected=C}))}_request(C){if(this._selected===void 0||!C.length||C.some(M=>M.calculating))return;let H=this._selected??W1(C.map(M=>M.countingSince)),V=this._selected?D1(H):"year",L=C.map(M=>M.savingEntity);return{key:JSON.stringify([L,H.start,H.end,V]),range:H,period:V,categories:C}}async _load(C){if(!this.hass)return;this._loading=C.key;let H=_1(C.range,C.period),V={},L=!1;try{V=await this.hass.callWS({type:"recorder/statistics_during_period",start_time:new Date(C.range.start).toISOString(),end_time:new Date(C.range.end+1).toISOString(),statistic_ids:C.categories.map(M=>M.savingEntity),period:E1(C.period),types:["change"]})}catch{L=!0}this._loading===C.key&&(this._loading=void 0,this._loaded={key:C.key,at:Date.now(),period:C.period,slots:H,values:C.categories.map(M=>({category:M.category,values:N1(V[M.savingEntity],H,C.period)})),failed:L})}willUpdate(C){if(!this.hass)return;C.has("hass")&&this._follow(),this._hasChart===void 0&&(this._hasChart=!1,T1().then(L=>{this._hasChart=L}));let H=this._request(F(this.hass)),V=!this._loaded||Date.now()-this._loaded.at>p2;H&&H.key!==this._loading&&(H.key!==this._loaded?.key||V&&!this._loading)&&this._load(H),C.has("_loaded")&&(this._chart=this._buildChart())}_color(C){let[H,V]=m2[C];return getComputedStyle(this).getPropertyValue(H).trim()||V}_buildChart(){let C=this._loaded;if(!C||C.failed)return;let H=this._localize;return F1({labels:this._labels(C.slots,C.period),series:C.values.map(({category:V,values:L})=>({id:V,name:H(`category.${V}`),color:this._color(V),values:L})),unit:this._currencySymbol(),total:H("history_total"),money:V=>this._money(V,!0),tick:V=>new Intl.NumberFormat(this._language,{maximumFractionDigits:2}).format(V)})}_labels(C,H){let V=t=>new Intl.DateTimeFormat(this._language,t),L=V({hour:"2-digit",minute:"2-digit"}),M=new Date(C[0]).getFullYear()!==new Date(C[C.length-1]).getFullYear(),e={hour:L,day:V({day:"numeric"}),month:V(M?{month:"short",year:"2-digit"}:{month:"short"}),year:V({year:"numeric"})}[H],A={hour:L,day:V({weekday:"short",day:"numeric",month:"short"}),month:V({month:"long",year:"numeric"}),year:V({year:"numeric"})}[H];return C.map(t=>({axis:e.format(t),tooltip:H==="hour"?`${L.format(t)} \u2013 ${L.format(t+36e5)}`:A.format(t)}))}render(){let C=this._localize;if(!this.hass)return p``;let H=F(this.hass),V=this._selected===null?C("history_title_years"):C("history_title");if(!H.length)return p`<ha-card>
        <div class="header"><h2 class="title">${V}</h2></div>
        <p class="summary">${C("not_set_up")}</p>
      </ha-card>`;let L=H.some(i=>i.calculating),M=L?void 0:this._loaded,e=M?.values.flatMap(i=>i.values)??[],A=e.reduce((i,o)=>i+(o??0),0),t=e.some(i=>i);return p`<ha-card>
      <div class="header">
        <h2 class="title">${V}</h2>
        ${M&&!M.failed&&t?p`<span class="chip">${this._money(A)}</span>`:d}
      </div>
      ${L?p`<p class="summary">${C("calculating_all")}</p>`:this._body(M,t)}
    </ha-card>`}_body(C,H){let V=this._localize;return this._hasChart?C?.failed?p`<p class="summary">${V("history_failed")}</p>`:p`<div class="chart">
      ${this._chart?p`<ha-chart-base
            .hass=${this.hass}
            .data=${this._chart.data}
            .options=${this._chart.options}
            .height=${I1}
          ></ha-chart-base>`:d}
      ${C&&!H?p`<div class="empty">${V("history_empty")}</div>`:d}
    </div>`:p`<p class="summary">${V("history_no_chart")}</p>`}};f.properties={hass:{attribute:!1},_selected:{state:!0},_loaded:{state:!0},_hasChart:{state:!0}},f.styles=[U,Z`
      .chart {
        position: relative;
        min-height: ${_(I1)};
        padding: 8px 16px 16px;
      }
      .empty {
        position: absolute;
        inset: 0;
        display: grid;
        place-items: center;
        padding: 16px;
        text-align: center;
        color: var(--secondary-text-color);
        background: color-mix(
          in srgb,
          var(--card-background-color, #fff) 70%,
          transparent
        );
      }
    `];var v2="https://github.com/ignazhabibi/ha-energy-payback",x2=(r,C)=>{if(!customElements.get(r))try{customElements.define(r,C)}catch{customElements.define(r,class extends C{})}};function $1(r){let C=()=>r.forEach(({tag:e,card:A})=>x2(e,A));C();let H=window.customElements,V=Date.now(),L=window.setInterval(()=>{let e=window.customElements!==H;e&&C(),(e||Date.now()-V>6e4)&&window.clearInterval(L)},100),M=window;M.customCards=M.customCards??[];for(let{tag:e,name:A,description:t}of r)M.customCards.some(i=>i.type===e)||M.customCards.push({type:e,name:A,description:t,preview:!0,documentationURL:v2})}$1([{tag:"energy-payback-card",card:g,name:"Energy Payback",description:"What your PV plant, heat pump, and electric car have saved, and when they pay off."},{tag:"energy-payback-history-card",card:f,name:"Energy Payback history",description:"The savings of your PV plant, heat pump, and electric car per period. Follows the energy date selection."}]);
/*! Bundled license information:

@lit/reactive-element/css-tag.js:
  (**
   * @license
   * Copyright 2019 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

@lit/reactive-element/reactive-element.js:
lit-html/lit-html.js:
lit-element/lit-element.js:
  (**
   * @license
   * Copyright 2017 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)

lit-html/is-server.js:
  (**
   * @license
   * Copyright 2022 Google LLC
   * SPDX-License-Identifier: BSD-3-Clause
   *)
*/
