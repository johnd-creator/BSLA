import AuthenticatedWorkspace from '../../components/AuthenticatedWorkspace';
import {ThemeProvider} from "../../components/ThemeProvider";
// Browser-only test entry: actual candidate components, no listening server.
import React from 'react';
import {createRoot} from 'react-dom/client';
import {AppShell} from '../../components/AppNavigation';
import Executive from '../../components/ExecutiveOverview';
import Login from '../../components/LoginPage';
import Glossary from '../../components/Glossary';
import Cases from '../../components/CaseWorkspace';
import Advisory from '../../components/AdvisoryWorkspace';
import Recommendations from '../../components/RecommendationWorkspace';
import Pdm from '../../components/PdmCenter';
import EngineeringQa from '../../components/EngineeringQa';
import EngineeringWorkflow from '../../components/EngineeringWorkflow';
import Phase2 from '../../components/Phase2Workspace';
import Engineering from '../../components/EngineeringWorkspace';
import Assets from '../../app/(workspace)/assets/page';
import Asset from '../../app/(workspace)/assets/[...canonicalId]/page';
import Health from '../../app/(workspace)/asset-health/page';
import Maintenance from '../../app/(workspace)/maintenance/page';
import Investigation from '../../app/(workspace)/maintenance/investigation/page';
import Fmea from '../../app/(workspace)/fmea/page';
import Rcfa from '../../app/(workspace)/rcfa/page';
import Overhaul from '../../app/(workspace)/overhauls/page';
import Trust from '../../app/(workspace)/data-quality/page';
import WorkOrders from '../../app/(workspace)/work-orders/page';
import Equipment from '../../app/(workspace)/equipment/[id]/page';
import fixture from '../../fixtures/ux-bundle-b.json';
import PdmTrendDemonstrator from '../../fixtures/PdmTrendDemonstrator';
const path=location.pathname;
const pages:Record<string,React.ReactNode>={
 '/':<Executive/>, '/login':<Login expired={new URLSearchParams(location.search).get('expired')==='1'} returnTo={new URLSearchParams(location.search).get('returnTo')??undefined}/>, '/panduan/istilah':<Glossary/>,
 '/engineering/cases':<Cases enabled/>, '/engineering/advisories':<Advisory enabled/>,
 '/engineering/inbox':<Advisory enabled inbox/>, '/engineering/local':<EngineeringQa localAuthentication/>,
 '/engineering':<Engineering/>, '/engineering/lab':<Phase2/>, '/engineering/workflow':<EngineeringWorkflow/>,
 '/recommendations':<Recommendations qaEnabled/>, '/action-board':<Recommendations qaEnabled board/>,
 '/pdm':<Pdm qaEnabled/>, '/assets':<Assets/>, '/asset-health':<Health/>, '/maintenance':<Maintenance/>,
 '/__synthetic/pdm-trend':<PdmTrendDemonstrator/>,
 '/maintenance/investigation':<Investigation/>, '/fmea':<Fmea/>, '/rcfa':<Rcfa/>, '/overhauls':<Overhaul/>,
 '/data-quality':<Trust/>, '/work-orders':<WorkOrders/>, '/equipment/DEMO':<Equipment params={Promise.resolve({id:'DEMO'})}/>, '/engineering/qa':<EngineeringQa/>,
};
const assetParams=Promise.resolve({canonicalId:[decodeURIComponent(path.split('/').at(-1)??'')]});
const content=path.startsWith('/assets/')?<Asset params={assetParams}/>:pages[path];
const shell=<AppShell engineeringVisible liveDevelopment><aside role="note" className="scope-banner engineering-demo"><strong>DEMO — QA SINTETIS · UJI KOMPONEN KANDIDAT</strong><span>Fixture browser terisolasi; bukan data pembangkit atau runtime yang diterapkan.</span></aside>{content}</AppShell>;
createRoot(document.getElementById('root')!).render(<ThemeProvider>{path==='/login'
 ? <main id="main-content" className="authentication-layout">{content}</main>
 : path==='/engineering/local'?<AuthenticatedWorkspace identity={{subject:'demo-author',roles:['AUTHOR'],asset_ids:[fixture.asset.canonical_id]}}>{shell}</AuthenticatedWorkspace>:shell}
</ThemeProvider>);
