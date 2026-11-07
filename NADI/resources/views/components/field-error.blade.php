@props(['name'])
@error($name)
    <p class="field-error" id="error-{{ \Illuminate\Support\Str::slug($name) }}">{{ $message }}</p>
@enderror
