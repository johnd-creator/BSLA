<?php

namespace App\Auth;

final readonly class DirectoryIdentity
{
    public function __construct(
        public string $stableId,
        public string $authorizedGroup,
    ) {}
}
