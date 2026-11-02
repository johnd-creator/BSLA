// Fully intercepted actual-component test entry; no operational app imports this.
import React from 'react';
import {createRoot} from 'react-dom/client';
import {ThemeProvider} from '../../components/ThemeProvider';
import {AppShell} from '../../components/AppNavigation';
import ReportsCenter from '../../components/ReportsCenter';
import Demonstrator from '../../fixtures/ReliabilityCalculationDemonstrator';
createRoot(document.getElementById('root')!).render(<ThemeProvider><AppShell engineeringVisible><aside role="note" className="scope-banner engineering-demo"><strong>SYNTHETIC ONLY · SPRINT4 QUALIFICATION</strong><span>Fixture terisolasi; bukan data pembangkit atau localhost aktif.</span></aside>{location.pathname==='/__synthetic/reliability'?<Demonstrator/>:<ReportsCenter/>}</AppShell></ThemeProvider>);
