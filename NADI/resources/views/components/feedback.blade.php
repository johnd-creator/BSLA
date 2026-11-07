@if(session('status'))<div class="notice success" role="status">{{ session('status') }}</div>@endif
@if($errors->any())
    <div class="notice error validation-summary" role="alert" id="validation-errors" tabindex="-1" data-error-summary>
        <strong>Periksa kembali isian Anda.</strong>
        <p>{{ $errors->count() }} isian perlu diperiksa. Pilih pesan untuk menuju ke isian terkait. Perbaiki isian terkait, lalu simpan kembali.</p>
        <ul>@foreach($errors->messages() as $field => $messages)
            @foreach($messages as $message)<li><a href="#error-{{ \Illuminate\Support\Str::slug($field) }}" data-error-field="{{ $field }}">{{ $message }}</a></li>@endforeach
        @endforeach</ul>
    </div>
@endif
