import ExecutiveOverview from "../../components/ExecutiveOverview";
import ScopedExecutiveOverview from "../../components/ScopedExecutiveOverview";
import {headers} from 'next/headers';
import {localGuardEnabled,verifyLocalSession} from '../../lib/local-session';
import {hasPortfolioRead} from '../../lib/factual-policy';

export default async function HomePage() {
  if(localGuardEnabled()){
    const who=await verifyLocalSession(new Headers(await headers()));
    if(who.state==='authenticated'&&!hasPortfolioRead(who.session))return <ScopedExecutiveOverview />;
  }
  return <ExecutiveOverview />;
}
