// Isolated actual-component harness. No application page imports this fixture.
import React from 'react';
import {createRoot} from 'react-dom/client';
import {ThemeProvider} from '../../components/ThemeProvider';
import {AppShell} from '../../components/AppNavigation';
import Asset from '../../app/(workspace)/assets/[...canonicalId]/page';
import Assets from '../../app/(workspace)/assets/page';
import InspectionDetail from '../../components/InspectionDetail';
import fixture from '../../fixtures/asset-evidence.synthetic.json';
import product from '../../fixtures/ux-bundle-b.json';
import type {Inspection} from '../../lib/product-records';
const params=Promise.resolve({canonicalId:[fixture.asset.canonical_id]});
const row={...product.inspections[0],canonical_asset_id:fixture.asset.canonical_id} as Inspection;
const content=location.pathname==='/assets'?<Assets/>:location.pathname==='/pdm'?<InspectionDetail row={row}/>:<Asset params={params}/>;
createRoot(document.getElementById('root')!).render(<ThemeProvider><AppShell engineeringVisible><aside role="note" className="scope-banner engineering-demo"><strong>SYNTHETIC ONLY · SPRINT3 QUALIFICATION</strong><span>Fixture terisolasi; bukan data pembangkit, bukan localhost aktif.</span></aside>{content}</AppShell></ThemeProvider>);
