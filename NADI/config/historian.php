<?php

return [
    // Explicit loopback simulation bridge only. Never points at PI/DCS or legacy collectors.
    'url' => env('HISTORIAN_DEMAND_API_BASE'),
    'pages' => [
        'demo-process' => ['title' => 'Proses demonstrasi', 'tags' => ['DEMO.TEMP', 'DEMO.PRESSURE']],
        'demo-temperature' => ['title' => 'Suhu demonstrasi', 'tags' => ['DEMO.TEMP']],
    ],
];
