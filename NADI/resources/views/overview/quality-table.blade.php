<div class="panel table-scroll overview-quality">
    <table>
        <caption class="sr-only">Status, dasar, dan batas kualitas data</caption>
        <thead><tr><th scope="col">Pemeriksaan</th><th scope="col">Status</th><th scope="col">Dasar & batas penggunaan</th></tr></thead>
        <tbody>
            @foreach($snapshot['quality'] as $item)
                <tr><th scope="row">{{ $item['label'] }}</th><td><span class="overview-state">{{ $item['state'] }}</span></td><td>{{ $item['detail'] }}<small class="overview-source">{{ $item['source'] }}</small></td></tr>
            @endforeach
        </tbody>
    </table>
</div>
