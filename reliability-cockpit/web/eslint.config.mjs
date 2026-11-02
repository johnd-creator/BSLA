import tseslint from "typescript-eslint";
import hooks from "eslint-plugin-react-hooks";
import a11y from "eslint-plugin-jsx-a11y";

// NADI presentation coverage, including legacy pages and Indonesian glossary.
export default tseslint.config({
  files: ["scripts/pdm-source-history/**/*.tsx", "components/**/*.tsx", "app/**/*.tsx", "lib/navigation.ts", "lib/integration.ts", "lib/reports.ts", "lib/overview.ts", "lib/glossary.ts", "lib/id-copy.ts", "lib/product-records.ts", "lib/pdm-input.ts", "lib/pdm-date.ts", "lib/pdm-history.ts", "fixtures/PdmTrendDemonstrator.tsx", "lib/pdm-capture.ts", "lib/pdm-capture-catalog.ts", "components/usePdmCommand.ts", "components/useQaRecords.ts", "lib/pdm-workbook.ts", "lib/case-records.ts", "lib/advisory-records.ts", "lib/development-provenance.ts", "middleware.ts", "lib/local-session.ts", "lib/factual-gateway.ts", "lib/factual-policy.ts", "lib/factual-read-contract.ts", "lib/factual-read-policy.ts", "lib/factual-scoped-reader.ts", "lib/factual-error.ts", "app/api/**/*.ts", "lib/api.ts", "lib/asset-hierarchy.ts", "scripts/hierarchy-entry.tsx", "lib/asset-evidence.ts", "lib/reliability-performance.ts", "fixtures/ReliabilityCalculationDemonstrator.tsx", "scripts/reliability-performance/**/*.tsx", "scripts/asset-evidence/**/*.tsx", "lib/case-form.ts", "lib/login-navigation.ts", "lib/development-status-view.ts"],
  extends: [...tseslint.configs.recommended],
  plugins: { "react-hooks": hooks, "jsx-a11y": a11y },
  rules: { ...hooks.configs.recommended.rules, ...a11y.configs.recommended.rules, "jsx-a11y/no-noninteractive-tabindex": ["error", { roles: ["region"] }] },
}, {files: ["lib/wo-date.ts"], extends: [...tseslint.configs.recommended]});
