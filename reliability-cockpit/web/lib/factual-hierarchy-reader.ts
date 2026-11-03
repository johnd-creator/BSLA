/** Server-side allowlisted DTO and exact retained-path proof before body release. */
import type {HierarchyNode,HierarchyView} from './asset-hierarchy';
import {canonicalBsrAsset} from './factual-read-policy';
import {preciseInstant} from './pdm-history';
const fail=():never=>{throw new Error('SCOPED_HIERARCHY_INVALID');};
function object(v:unknown):Record<string,unknown>{return v!==null&&typeof v==='object'&&!Array.isArray(v)?v as Record<string,unknown>:fail();}
function nullableText(v:unknown,max=200):v is string|null{return v===null||typeof v==='string'&&v.length<=max;}
function node(v:unknown):HierarchyNode{
 const n=object(v);
 if(typeof n.canonical_id!=='string'||!canonicalBsrAsset(n.canonical_id)||!nullableText(n.source_asset_number)||n.source_asset_number!==null&&n.source_asset_number!==n.canonical_id.split(':').at(-1)||!nullableText(n.description,1000)||typeof n.description_shortened!=='boolean'||!nullableText(n.parent_asset_ref)||n.parent_asset_ref!==null&&!canonicalBsrAsset(n.parent_asset_ref)||!nullableText(n.status)||!nullableText(n.asset_type)||!nullableText(n.unit)||typeof n.registered!=='boolean'||n.hierarchy_role!=='UNKNOWN'||n.source_has_children!==null&&typeof n.source_has_children!=='boolean'||!nullableText(n.source_updated_at)||typeof n.source_updated_at==='string'&&!(preciseInstant(n.source_updated_at)||/^\d{4}-\d{2}-\d{2}T\d{2}:\d{2}:\d{2}(?:\.\d+)?$/.test(n.source_updated_at)&&preciseInstant(n.source_updated_at+'Z')))return fail();
 return Object.fromEntries(['canonical_id','source_asset_number','description','description_shortened','parent_asset_ref','status','asset_type','unit','registered','hierarchy_role','source_has_children','source_updated_at'].map(k=>[k,n[k]])) as unknown as HierarchyNode;
}
function nodes(v:unknown,max:number):HierarchyNode[]{
 if(!Array.isArray(v)||v.length>max)return fail();
 const result=v.map(node);if(new Set(result.map(n=>n.canonical_id)).size!==result.length)return fail();return result;
}
const same=(a:HierarchyNode,b:HierarchyNode)=>JSON.stringify(a)===JSON.stringify(b);
export function scopedHierarchyPage(value:unknown,root:string,requested:string,offset:number,limit:number):HierarchyView{
 const v=object(value),selected=node(v.node),path=nodes(v.path,33),ancestors=nodes(v.ancestors,32),items=nodes(v.items,50);
 if(v.root_ref!==root||selected.canonical_id!==requested||!path.length||v.offset!==offset||v.limit!==limit||!Number.isSafeInteger(v.total)||(v.total as number)<0||items.length!==Math.min(limit,Math.max(0,(v.total as number)-offset))||v.has_more!==(offset+items.length<(v.total as number))||v.completeness!=='PARTIAL'||v.source!=='RETAINED_MAXIMO_PARENT'||v.depth_limit!==32||!['NO_RETAINED_PARENT','UNRESOLVED_PARENT','OUT_OF_SCOPE_PARENT','CYCLE','DEPTH_LIMIT'].includes(v.ancestor_state as string)||!nullableText(v.unresolved_parent_ref)||v.unresolved_parent_ref!==null&&!canonicalBsrAsset(v.unresolved_parent_ref))return fail();
 const relation=v.node_relation;
 if(!['ROOT','DESCENDANT','ANCESTOR'].includes(relation as string))return fail();
 for(let i=1;i<path.length;i++)if(path[i].parent_asset_ref!==path[i-1].canonical_id)return fail();
 for(let i=1;i<ancestors.length;i++)if(ancestors[i].parent_asset_ref!==ancestors[i-1].canonical_id)return fail();
 const anchor=relation==='ANCESTOR'?path.at(-1)!:path[0];
 if(anchor.canonical_id!==root||!anchor.registered||ancestors.some(n=>n.canonical_id===root)||ancestors.length&&anchor.parent_asset_ref!==ancestors.at(-1)!.canonical_id)return fail();
 if(relation==='ANCESTOR'){
  const i=ancestors.findIndex(n=>same(n,selected)),expected=ancestors.slice(i).concat(anchor);
  if(i<0||path.length!==expected.length||path.some((n,k)=>!same(n,expected[k]))||v.total!==1||!same(path[0],selected)||items.some(n=>!same(n,path[1])))return fail();
 }else if(!same(path.at(-1)!,selected)||path[0].canonical_id!==root||(relation==='ROOT')!==(selected.canonical_id===root)||items.some(n=>n.parent_asset_ref!==selected.canonical_id))return fail();
 return {root_ref:root,node:selected,node_relation:relation as HierarchyView['node_relation'],path,ancestors,ancestor_state:v.ancestor_state as HierarchyView['ancestor_state'],unresolved_parent_ref:v.unresolved_parent_ref as string|null,items,total:v.total as number,offset,limit,has_more:v.has_more as boolean,completeness:'PARTIAL',source:'RETAINED_MAXIMO_PARENT',depth_limit:32};
}
