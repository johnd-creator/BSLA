@props(['assetName', 'thumbnail' => null, 'illustrationLabel' => null])
{{-- Local presentation media stays separate from the read-only source asset DTO.
     Generic illustrations are not evidence of the actual physical asset. No upload or 3D viewer. --}}
<figure class="asset-visual" aria-label="Gambar aset">
    <figcaption class="asset-visual-label">Gambar aset</figcaption>
    <div class="asset-visual-frame">
        @if($thumbnail)
            <img class="asset-visual-image" src="{{ $thumbnail }}" alt="{{ $illustrationLabel ? 'Ilustrasi generik '.$illustrationLabel.', bukan foto aset aktual: ' : 'Gambar ' }}{{ $assetName }}" width="320" height="180" loading="lazy" decoding="async">
        @else
            <div class="asset-visual-empty">
                <svg viewBox="0 0 48 48" fill="none" stroke="currentColor" stroke-width="1.5" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true" focusable="false">
                    <path d="m24 6 15 8.5v18L24 41 9 32.5v-18L24 6Z" />
                    <path d="m9 14.5 15 9 15-9M24 23.5V41M16.5 10.25l15 8.75" />
                </svg>
                <span>Belum ada gambar</span>
            </div>
        @endif
    </div>
    @if($thumbnail && $illustrationLabel)
        <small class="asset-visual-note"><strong>Ilustrasi generik · {{ $illustrationLabel }}</strong><br>Bukan foto aset aktual. Belum diverifikasi engineer.<br>Bentuk dan susunan bukan spesifikasi alat.</small>
    @endif
    <small class="asset-visual-note">3D interaktif belum tersedia. Menunggu cross-check engineer.</small>
</figure>
