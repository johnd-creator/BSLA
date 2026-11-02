// Test-only component entry. No application route imports this file.
import React from 'react';
import {createRoot} from 'react-dom/client';
import AssetHierarchy from '../components/AssetHierarchy';
createRoot(document.getElementById('root')!).render(<main style={{padding:24,maxWidth:1200,margin:'auto'}}><h1>Hierarki aset · SYNTHETIC ONLY</h1><AssetHierarchy canonicalId="asset:MAXIMO:MXASSET:BSR:IP:SYNTHETIC-ROOT"/></main>);
