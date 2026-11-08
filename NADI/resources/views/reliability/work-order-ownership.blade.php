@php
    $activeLinks = collect($links)->where('relation_state', '!=', 'removed');
    $thisAsset = $activeLinks->filter(fn($link)=>($link['asset_ref'] ?? null)===$selectedAsset)->count();
    $otherAsset = $activeLinks->filter(fn($link)=>isset($link['asset_ref']) && $link['asset_ref']!==$selectedAsset)->count();
    $unknownAsset = $activeLinks->filter(fn($link)=>!isset($link['asset_ref']))->count();
    $removed = collect($links)->where('relation_state', 'removed')->count();
@endphp
<small>
    {{ $thisAsset }} WO aset ini · {{ $otherAsset }} WO aset lain dalam kejadian · {{ $removed }} hubungan dilepas
    @if($unknownAsset)
        · {{ $unknownAsset }} kepemilikan aset tidak dicatat pada snapshot lama
    @endif
</small>
