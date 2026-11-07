<section class="panel annual-wo" aria-labelledby="annual-wo-title">
    <div class="panel-heading"><h2 id="annual-wo-title">Aktivitas WO per tahun</h2><span class="source-pill">Actual start · WIB</span></div>
    @if($annual === null)
        <p class="muted">Ringkasan tahunan belum dapat diverifikasi. Ini bukan hasil nol pemeliharaan; daftar WO tetap dapat dibaca bila tersedia.</p>
    @else
        <div class="annual-wo-overview">
            <p><strong>{{ number_format($annual['counts']['dated_work_order_count'], 0, ',', '.') }}</strong> WO memiliki tahun aktual <span class="muted">dari {{ number_format($annual['counts']['work_order_count'], 0, ',', '.') }} identitas WO di Mart</span></p>
            <p class="muted">Seluruh WO aset ini, bukan hanya halaman atau filter daftar. Klik tahun untuk melihat WO penyusunnya.</p>
        </div>
        <div class="table-scroll"><table class="annual-wo-table"><caption class="sr-only">Perbandingan jumlah WO, jenis pekerjaan, dan status sumber per tahun mulai aktual di Asia/Jakarta</caption><thead><tr><th>Tahun mulai</th><th>Jumlah WO</th><th>Jenis pekerjaan sumber</th><th>Status sumber saat ini</th></tr></thead><tbody>
            @foreach([...$annual['years'], $annual['unknown_year']] as $bucket)
                @php($yearKey = $bucket['year'] === null ? 'unknown' : (string) $bucket['year'])
                <tr @class(['annual-wo-selected' => request('year') === $yearKey])><th scope="row"><a class="text-link" @if(request('year') === $yearKey) aria-current="true" @endif href="{{ route('work-orders.index', ['asset_ref' => $asset['canonical_id'], 'view' => $mode, 'year' => $yearKey]) }}">{{ $bucket['year'] ?? 'Tahun belum diketahui' }}</a></th><td class="annual-wo-count">{{ number_format($bucket['work_orders'], 0, ',', '.') }}</td>
                    @foreach(['work_types', 'statuses'] as $dimension)<td><div class="annual-wo-groups">@forelse($bucket[$dimension] as $group)<span class="badge neutral">{{ $group['value'] ?? 'Unknown' }} <b>{{ number_format($group['count'], 0, ',', '.') }}</b></span>@empty<span class="muted">—</span>@endforelse</div></td>@endforeach
                </tr>
            @endforeach
        </tbody></table></div>
        @if($annual['years'] === [])<p class="muted">Belum ada WO dengan tahun mulai aktual yang dapat dihitung. Tahun yang tidak muncul tidak dianggap nol pemeliharaan.</p>@endif
        @if($annual['counts']['duplicate_work_order_count'] || $annual['counts']['missing_identity_record_count'])<p class="annual-wo-warning">Tidak dimasukkan ke kelompok tahun: {{ $annual['counts']['duplicate_work_order_count'] }} identitas WO berulang ({{ $annual['counts']['duplicate_record_count'] }} record) dan {{ $annual['counts']['missing_identity_record_count'] }} record tanpa identitas WO. Perlu rekonsiliasi, tidak dihitung ganda.</p>@endif
    @endif
    <details class="annual-wo-method"><summary>Definisi tahun dan kaitan dengan reliability</summary><ul>
        <li>Satu identitas WO dihitung sekali pada tahun actual start, kalender Asia/Jakarta (WIB). WO lintas tahun tetap pada tahun mulai, bukan dibagi ke beberapa tahun. Tanggal perubahan record, nomor WO, dan tanggal selesai tidak menggantikan actual start yang kosong.</li>
        <li>Jenis memakai kode worktype sumber, lalu kategori kanonis bila kode sumber kosong. Status adalah status terakhir di Mart, bukan snapshot status akhir tahun. Ini jumlah WO, bukan frekuensi kejadian atau jumlah pekerjaan yang pasti selesai. Tahun yang tidak muncul belum dapat dinyatakan nol.</li>
        <li>Availability tahunan perlu cross-check historian DCS, periode operasi yang sah, dan downtime tervalidasi. Durasi WO tidak menggantikan downtime.</li>
        <li>Score reliability, asset wellness, dan Pareto loss tahunan memerlukan kejadian yang sudah direkonsiliasi serta bukti kehilangan waktu/produksi. Ringkasan WO memberi konteks pemeliharaan, belum menghasilkan skor atau loss.</li>
        <li>Cakupan ini hanya data yang sudah terkumpul di Mart. Kelengkapan sejarah setiap tahun belum dibuktikan.</li>
    </ul></details>
</section>
