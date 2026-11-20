import{esc}from'../utils/format.js';import{STATES}from'../constants.js';
export const badge=s=>`<span class="badge ${esc(s)}">${esc(STATES[s]||s)}</span>`;
export const plaque=e=>`<div class="plaque"><small>${esc(e.code)}</small><b>${esc(e.street)} <strong>${e.number}</strong> 号</b><span>${esc(e.label)}</span></div>`;
export const heading=(n,t,d)=>`<div class="heading"><span>${n}</span><div><small>长桥街道 / 地址核定簿</small><h1>${t}</h1><p>${d}</p></div></div>`;
export const form=(id,title,endpoint,body,method='POST')=>`<form id="${id}" data-endpoint="${endpoint}" data-method="${method}"><h3>${title}</h3>${body}<button>保存办理记录</button></form>`;
export const input=(n,label,value='',type='text')=>`<label>${label}<input name="${n}" value="${esc(value)}" type="${type}" required></label>`;
export const select=(n,label,options)=>`<label>${label}<select name="${n}">${options}</select></label>`;
export const area=(n,label,value='')=>`<label>${label}<textarea name="${n}" required>${esc(value)}</textarea></label>`;
