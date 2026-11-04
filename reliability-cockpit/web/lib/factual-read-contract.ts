/** Client-safe DTOs only. Authority and policy files never reach the browser. */
export const FACTUAL_READ_CAPABILITIES=['FACTUAL_DASHBOARD_READ','FACTUAL_ASSET_READ','FACTUAL_MAINTENANCE_READ','FACTUAL_HIERARCHY_READ'] as const;
export type FactualReadCapability=typeof FACTUAL_READ_CAPABILITIES[number];
export interface ScopedFactualOverview {
 wo_evidence?: import("./wo-evidence-types").WoEvidence | null;
 scope:{site_code:'BSR';organization_code:'IP';kind:'FACTUAL_ASSET_ALLOWLIST'|'REGISTERED_BSR_IP'};
 as_of:string;
 summary:{registered_assets:number;maintenance_events:number;assets_with_maintenance:number};
 assets:{canonical_id:string;source_asset_number:string|null;description:string|null;maintenance_events:number;latest_retained_activity:string|null}[];
 restricted_sections:string[];
 operational_kpis:'NOT_ELIGIBLE';
}
