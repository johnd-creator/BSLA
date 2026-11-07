<section class="asset-summary" aria-labelledby="asset-summary-title">
    <div class="asset-summary-heading">
        <h2 id="asset-summary-title">Ringkasan Asset</h2>
        <span class="muted">BSR / IP · Hierarki CS01</span>
    </div>
    <dl class="asset-summary-grid">
        @foreach(['total' => 'Total Asset', 'equipment' => 'Equipment', 'component' => 'Component', 'part' => 'Part'] as $key => $label)
            <div @class(['panel', 'asset-summary-card', 'asset-summary-total' => $key === 'total'])>
                <dt>{{ $label }}</dt>
                <dd><span class="asset-summary-value">{{ $summary !== null ? number_format($summary[$key], 0, ',', '.') : '—' }}</span><small>{{ $summary === null ? 'Belum tersedia' : ($key === 'total' ? 'Tersimpan di Mart' : 'Acuan Excel engineer') }}</small></dd>
            </div>
        @endforeach
    </dl>
    @if($summary === null)
        <p class="asset-summary-note">Ringkasan belum tersedia atau responsnya belum dapat diverifikasi. Angka tidak dihitung dari halaman daftar.</p>
    @else
        <p class="asset-summary-note">Total mencakup Equipment, Component, Part, <strong>{{ number_format($summary['system'], 0, ',', '.') }} System</strong>, dan <strong>{{ number_format($summary['unknown'], 0, ',', '.') }} belum dikategorikan</strong>. Kategori mengacu pada Excel engineer melalui ID sumber yang cocok tepat, bukan tipe aset Maximo atau kedalaman hierarki.</p>
        <p class="asset-summary-note">Seluruh inventaris dalam cakupan ini, tidak mengikuti filter atau halaman daftar.
            @if($summary['complete'])
                Pemindaian lengkap terakhir: <time datetime="{{ $summary['last_completed_at'] }}">{{ $summary['last_completed_at'] }}</time>. Bukan jaminan kesegaran saat ini.
            @else
                <strong>Cakupan belum lengkap.</strong> Jumlah ini belum membuktikan seluruh aset sumber telah tersedia di Mart.
                @if($summary['pending_projection'] > 0)
                    {{ number_format($summary['pending_projection'], 0, ',', '.') }} aset masih menunggu proyeksi ke Mart.
                @endif
            @endif
        </p>
    @endif
</section>
