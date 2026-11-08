<?php

return [
    'cems_live' => ['url' => env('CEMS_LIVE_API_BASE')],
    'maximo_collector' => ['url' => env('MAXIMO_COLLECTOR_API_BASE', 'http://127.0.0.1:8002')],
    'asset_mapping' => ['file' => env('NADI_ASSET_MAPPING', storage_path('app/private/asset-mapping.json'))],
    'reliability_mart' => [
        'url' => env('RELIABILITY_MART_API_BASE'),
    ],

    /*
    |--------------------------------------------------------------------------
    | Third Party Services
    |--------------------------------------------------------------------------
    |
    | This file is for storing the credentials for third party services such
    | as Resend, Postmark, AWS, and more. This file provides the de facto
    | location for this type of information, allowing packages to have
    | a conventional file to locate the various service credentials.
    |
    */

    'postmark' => [
        'key' => env('POSTMARK_API_KEY'),
    ],

    'resend' => [
        'key' => env('RESEND_API_KEY'),
    ],

    'ses' => [
        'key' => env('AWS_ACCESS_KEY_ID'),
        'secret' => env('AWS_SECRET_ACCESS_KEY'),
        'region' => env('AWS_DEFAULT_REGION', 'us-east-1'),
    ],

    'slack' => [
        'notifications' => [
            'bot_user_oauth_token' => env('SLACK_BOT_USER_OAUTH_TOKEN'),
            'channel' => env('SLACK_BOT_USER_DEFAULT_CHANNEL'),
        ],
    ],

];
