<?php

namespace App\Support;

use Illuminate\Support\Facades\File;
use Symfony\Component\HttpKernel\Exception\ServiceUnavailableHttpException;

final class DirectorySettingsDraft
{
    public const FIELDS = ['host', 'base_dn', 'group_dn', 'bind_name'];

    private function directory(): string
    {
        // Deliberately outside both the publicly linked and signed-servable disks.
        return storage_path('app/nadi-drafts');
    }

    public function read(): array
    {
        $dir = $this->directory();
        $path = $dir.'/directory-settings.json';
        if (is_link($dir) || is_link($path) || (is_dir($dir) && (fileperms($dir) & 0077) !== 0)) {
            throw new ServiceUnavailableHttpException(null, 'Penyimpanan draft tidak tersedia.');
        }
        if (! file_exists($path)) {
            return [];
        }
        if (! is_file($path) || (fileperms($path) & 0077) !== 0 || filesize($path) > 16384) {
            throw new ServiceUnavailableHttpException(null, 'Draft tidak dapat dibaca.');
        }
        try {
            $values = json_decode(File::get($path), true, flags: JSON_THROW_ON_ERROR);

            return is_array($values) ? $this->clean($values) : [];
        } catch (\Exception) {
            throw new ServiceUnavailableHttpException(null, 'Draft tidak dapat dibaca.');
        }
    }

    public function save(array $values): void
    {
        $dir = $this->directory();
        $temp = null;
        try {
            if (! is_dir($dir) && ! @mkdir($dir, 0700) && ! is_dir($dir)) {
                throw new \RuntimeException;
            }
            $path = $dir.'/directory-settings.json';
            if (is_link($dir) || is_link($path) || (is_dir($dir) && (fileperms($dir) & 0077) !== 0)) {
                throw new \RuntimeException;
            }
            $content = json_encode($this->clean($values), JSON_UNESCAPED_UNICODE | JSON_THROW_ON_ERROR)."\n";
            $temp = tempnam($dir, '.draft-'); // Created with mode 0600.
            if (! is_string($temp) || dirname($temp) !== $dir || ! chmod($temp, 0600)
                || file_put_contents($temp, $content) !== strlen($content) || ! rename($temp, $path)) {
                throw new \RuntimeException;
            }
            $temp = null;
        } catch (\Exception) {
            throw new ServiceUnavailableHttpException(null, 'Draft tidak dapat disimpan.');
        } finally {
            if (is_string($temp)) {
                @unlink($temp);
            }
        }
    }

    private function clean(array $values): array
    {
        return array_filter(
            array_intersect_key($values, array_flip(self::FIELDS)),
            static fn ($value): bool => is_string($value) && strlen($value) <= 2048,
        );
    }
}
