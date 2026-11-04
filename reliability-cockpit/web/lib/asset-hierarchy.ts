/** Retained Maximo edges are context; they do not confer Registry membership. */
export interface HierarchyNode {
  canonical_id:string; source_asset_number:string|null; description:string|null;
  description_shortened:boolean; parent_asset_ref:string|null; status:string|null;
  asset_type:string|null; unit:string|null; registered:boolean; hierarchy_role:'UNKNOWN';
  source_has_children:boolean|null; source_updated_at:string|null;
}
export interface HierarchyView {
  root_ref:string; node:HierarchyNode; node_relation:'ROOT'|'DESCENDANT'|'ANCESTOR'; path:HierarchyNode[]; ancestors:HierarchyNode[];
  ancestor_state:'NO_RETAINED_PARENT'|'UNRESOLVED_PARENT'|'OUT_OF_SCOPE_PARENT'|'CYCLE'|'DEPTH_LIMIT';
  unresolved_parent_ref:string|null; items:HierarchyNode[]; total:number; offset:number;
  limit:number; has_more:boolean; completeness:'PARTIAL'; source:'RETAINED_MAXIMO_PARENT'; depth_limit:number;
}
