// Actual components in an intercepted SYNTHETIC browser; never an application route.
import React from 'react';
import {createRoot} from 'react-dom/client';
import {ThemeProvider} from '../components/ThemeProvider';
import AuthenticatedWorkspace from '../components/AuthenticatedWorkspace';
import EngineeringDraftProviders from '../components/EngineeringDraftProviders';
import {AppShell} from '../components/AppNavigation';
import LoginPage from '../components/LoginPage';
import ScopedExecutiveOverview from '../components/ScopedExecutiveOverview';
import Assets from '../app/(workspace)/assets/page';
import Asset from '../app/(workspace)/assets/[...canonicalId]/page';
import PdmCenter from '../components/PdmCenter';
const identity={subject:'local:synthetic-engineer',username:'synthetic_engineer',roles:['AUTHOR'],asset_ids:['asset:DEMO-001']};
const p=location.pathname;
const content=p==='/'?<ScopedExecutiveOverview/>:p==='/assets'?<Assets/>:p==='/pdm'?<PdmCenter qaEnabled/>:<Asset params={Promise.resolve({canonicalId:[decodeURIComponent(p.split('/').at(-1)??'')]})}/>;
createRoot(document.getElementById('root')!).render(<ThemeProvider>{p==='/login'?<main className="authentication-layout"><LoginPage returnTo="/"/></main>:<AuthenticatedWorkspace identity={identity}><EngineeringDraftProviders><AppShell engineeringVisible liveDevelopment><aside className="scope-banner engineering-demo" role="note"><strong>SYNTHETIC ONLY · ENGINEER READ QUALIFICATION</strong><span>Fixture terisolasi; bukan bukti pembangkit atau localhost aktif.</span></aside>{content}</AppShell></EngineeringDraftProviders></AuthenticatedWorkspace>}</ThemeProvider>);
