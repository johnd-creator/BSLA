<?php

return [
    'enabled' => env('NADI_DIRECTORY_ENABLED', false),
    'realm' => env('NADI_DIRECTORY_REALM'),
    'required_group' => env('NADI_DIRECTORY_REQUIRED_GROUP'),
    'host' => env('NADI_DIRECTORY_HOST'),
    'base_dn' => env('NADI_DIRECTORY_BASE_DN'),
    'login_attribute' => env('NADI_DIRECTORY_LOGIN_ATTRIBUTE', 'sAMAccountName'),
    'bind_dn' => env('NADI_DIRECTORY_BIND_DN'),
    'bind_password' => env('NADI_DIRECTORY_BIND_PASSWORD'),
    'ca_file' => env('NADI_DIRECTORY_CA_FILE'),
];
