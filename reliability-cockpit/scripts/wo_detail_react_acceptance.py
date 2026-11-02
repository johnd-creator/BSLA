"""Actual API serializer -> TS validator -> React, synthetic and networkless."""
from pathlib import Path
from types import SimpleNamespace
import json, os, subprocess
from src.api.reliability import MaintenanceView, _maintenance

rows=[]
for clock in [None,"2026-10-23T07:51:51.123400Z","2026-10-23T14:51:51+07:00","2026-10-23T14:51:51","2026-10-23T14:51:51-00:00","2026-10-23T07:51:51+0700","2026-10-23T07:51:51+00:60","2026-W43-5T07:51:51Z"]:
    fields={k:None for k in MaintenanceView.model_fields if k not in {"classification","source_detail"}}
    fields.update(canonical_id="event:SYNTHETIC-API",contract_version="1.0",id="SYNTHETIC-API",equipment_id="asset:SYNTHETIC-API",site_code="BSR",organization_code="IP",status="CLOSE",event_type=None,duration_hours=0,sources={"maximo":{"wonum":"WO-SYNTHETIC-API","assetnum":"ASSET-SYNTHETIC-API","worktype":"CD","reportdate":clock,"reportedby":"PRIVATE-PERSON"}})
    rows.append(_maintenance(SimpleNamespace(**fields)).model_dump(mode="json"))
root=Path(__file__).resolve().parents[1]/"web"
subprocess.run([os.environ.get("NADI_TEST_NODE","node"),"scripts/wo-detail-check.mjs","--api-receipt"],input=json.dumps(rows),text=True,cwd=root,check=True,timeout=60)
