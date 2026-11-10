@foreach(\App\Services\ReliabilityPeriod::fromReport($report)->query() as $name=>$value)<input type="hidden" name="{{ $name }}" value="{{ $value }}">@endforeach
