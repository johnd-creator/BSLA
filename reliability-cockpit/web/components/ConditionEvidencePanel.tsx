"use client";

import { idText } from "../lib/id-copy";
import ConditionEvidenceView from "./ConditionEvidenceView";
import { useEffect, useState } from "react";
import { reliabilityApi, type AssetConditionEvidence } from "@/lib/api";
import {evidenceError, validateCondition} from '../lib/asset-evidence';
import { ErrorState, LoadingState, SectionCard } from "@/components/ui";

export default function ConditionEvidencePanel({ canonicalId }: { canonicalId: string }) {
  const [data, setData] = useState<AssetConditionEvidence | null>(null);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState<string | null>(null), [retry, setRetry] = useState(0);
  const [observed, setObserved] = useState<string | null>(null);
  useEffect(() => {
    let cancelled = false;
    setData(null); setLoading(true); setError(null); setObserved(null);
    reliabilityApi.conditionEvidence(canonicalId).then((result) => { validateCondition(result, canonicalId); if (!cancelled) {setData(result); setObserved(new Date().toISOString());} })
      .catch((reason) => { if (!cancelled) setError(evidenceError(reason)); })
      .finally(() => { if (!cancelled) setLoading(false); });
    return () => { cancelled = true; };
  }, [canonicalId, retry]);
  return <SectionCard className="condition-evidence-panel">
    <div className="section-heading"><div><p className="eyebrow">{idText("Selected signal evidence")}</p><h2>{idText("Condition Evidence")}</h2></div></div>
    {loading ? <LoadingState /> : error ? <ErrorState message={error} onRetry={() => setRetry(n=>n+1)}/> : data ? <>
      <ConditionEvidenceView data={data} observedAt={observed}/>
    </> : null}
  </SectionCard>;
}
