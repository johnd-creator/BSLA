<?php

return [
    // Private source-derived catalog is provisioned locally, never committed.
    'catalog' => env('NADI_PDM_CATALOG', storage_path('app/private/pdm-form-catalog.json')),
];
