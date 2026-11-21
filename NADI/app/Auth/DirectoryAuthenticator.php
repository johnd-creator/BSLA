<?php

namespace App\Auth;

use LDAP\Connection;
use LDAP\Result;

class DirectoryAuthenticator
{
    public function authenticate(string $login, #[\SensitiveParameter] string $password, string $requiredGroup): ?DirectoryIdentity
    {
        $host = config('directory.host');
        $base = config('directory.base_dn');
        $bindDn = config('directory.bind_dn');
        $bindPassword = config('directory.bind_password');
        $ca = config('directory.ca_file');
        $attribute = config('directory.login_attribute');

        if (! extension_loaded('ldap')
            || ! is_string($host) || filter_var($host, FILTER_VALIDATE_IP) || ! str_contains($host, '.') || ! filter_var($host, FILTER_VALIDATE_DOMAIN, FILTER_FLAG_HOSTNAME)
            || ! is_string($base) || trim($base) === '' || ! is_string($bindDn) || trim($bindDn) === ''
            || ! is_string($bindPassword) || trim($bindPassword) === ''
            || ! is_string($ca) || ! str_starts_with($ca, '/') || ! is_file($ca) || ! is_readable($ca)
            || ! in_array($attribute, ['sAMAccountName', 'userPrincipalName'], true)
            || trim($requiredGroup) === '' || trim($password) === ''
            || $login === '' || strlen($login) > 254 || preg_match('/[\x00-\x1f\x7f]/', $login)) {
            return null;
        }

        // Set libldap's TLS policy before initializing the LDAPS handle. Any
        // unavailable security option means no authentication, not a downgrade.
        foreach (['LDAP_OPT_X_TLS_CACERTFILE' => $ca,
            'LDAP_OPT_X_TLS_REQUIRE_CERT' => 'LDAP_OPT_X_TLS_DEMAND',
            'LDAP_OPT_X_TLS_REQUIRE_SAN' => 'LDAP_OPT_X_TLS_DEMAND',
            'LDAP_OPT_X_TLS_PROTOCOL_MIN' => 'LDAP_OPT_X_TLS_PROTOCOL_TLS1_2'] as $option => $value) {
            if (! defined($option) || ($option !== 'LDAP_OPT_X_TLS_CACERTFILE' && ! defined($value))
                || ! @ldap_set_option(null, constant($option), $option === 'LDAP_OPT_X_TLS_CACERTFILE' ? $value : constant($value))) {
                return null;
            }
        }
        $ldap = @ldap_connect('ldaps://'.$host.':636');
        if (! $ldap instanceof Connection) {
            return null;
        }

        try {
            if (! @ldap_set_option($ldap, LDAP_OPT_PROTOCOL_VERSION, 3)
                || ! @ldap_set_option($ldap, LDAP_OPT_REFERRALS, false)
                || ! @ldap_set_option($ldap, LDAP_OPT_NETWORK_TIMEOUT, 4)
                || ! @ldap_set_option($ldap, LDAP_OPT_TIMEOUT, 4)
                || ! @ldap_bind($ldap, $bindDn, $bindPassword)) {
                return null;
            }
            $filter = '(&(objectCategory=person)(objectClass=user)('.$attribute.'='.ldap_escape($login, '', LDAP_ESCAPE_FILTER).'))';
            $match = $this->soleEntry($ldap, @ldap_search($ldap, $base, $filter, ['objectGUID'], 0, 2, 4, LDAP_DEREF_NEVER));
            $dn = $match['dn'] ?? null;
            $guid = $match['objectguid'][0] ?? null;
            if (! is_string($dn) || $dn === '' || ($match['objectguid']['count'] ?? 0) !== 1 || ! is_string($guid) || strlen($guid) !== 16) {
                return null;
            }
            $escapedGuid = implode('', array_map(static fn (string $byte) => '\\'.bin2hex($byte), str_split($guid)));
            $membership = '(&'.$filter.'(objectGUID='.$escapedGuid.')(memberOf='.ldap_escape($requiredGroup, '', LDAP_ESCAPE_FILTER).'))';
            if ($this->soleEntry($ldap, @ldap_read($ldap, $dn, $membership, ['objectGUID'], 0, 2, 4, LDAP_DEREF_NEVER)) === null
                || ! @ldap_bind($ldap, $dn, $password)
                || $this->soleEntry($ldap, @ldap_read($ldap, $dn, $membership, ['objectGUID'], 0, 2, 4, LDAP_DEREF_NEVER)) === null) {
                return null;
            }

            return new DirectoryIdentity(bin2hex($guid), $requiredGroup);
        } finally {
            @ldap_unbind($ldap);
        }
    }

    private function soleEntry(Connection $ldap, Result|false $result): ?array
    {
        if ($result === false || ! @ldap_parse_result($ldap, $result, $code, $matched, $message, $referrals)
            || $code !== 0 || $referrals || @ldap_first_reference($ldap, $result) !== false
            || @ldap_count_entries($ldap, $result) !== 1) {
            return null; // Includes partial results, referral, and ambiguous login.
        }
        $entry = @ldap_get_entries($ldap, $result);

        return is_array($entry[0] ?? null) ? $entry[0] : null;
    }
}
