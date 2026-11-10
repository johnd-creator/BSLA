<?php

namespace App\Http\Controllers;

use App\Services\OperationsDraft;
use App\Services\ReliabilityMart;
use Illuminate\Http\Request;
use Illuminate\Validation\Rule;
use Symfony\Component\HttpKernel\Exception\HttpExceptionInterface;
use Throwable;

class OperationsController extends Controller
{
    public function __invoke(Request $request, ReliabilityMart $mart)
    {
        $screens = OperationsDraft::SCREENS;
        $components = OperationsDraft::components();
        $query = $request->validate([
            'screen' => ['sometimes', 'required', 'string', Rule::in($screens)],
            'component' => ['nullable', 'string', Rule::in(array_keys($components))],
            'offset' => ['sometimes', 'integer', 'min:0', 'max:1000000'],
            'unit' => ['nullable', 'string', 'max:60'],
            'equipment' => ['nullable', 'string', 'max:240'],
        ]);
        $screen = $query['screen'] ?? 'BOIL';
        $draftComponent = $query['component'] ?? null;
        abort_if($draftComponent && $screen !== 'BOIL', 404);
        $componentDetail = $draftComponent ? $components[$draftComponent] : null;
        $offset = (int) ($query['offset'] ?? 0);
        $unit = $query['unit'] ?? null;
        $equipment = $query['equipment'] ?? null;
        abort_if($equipment && (str_contains($equipment, '/') || str_contains($equipment, '\\')), 404);
        try {
            $page = $mart->assets(array_filter(['offset' => $offset, 'unit' => $unit], fn ($v) => $v !== null && $v !== ''));
        } catch (Throwable) {
            $page = null;
        }
        $selected = null;
        $selectionUnavailable = false;
        if ($equipment) {
            try {
                $selected = $mart->detail($equipment);
            } catch (Throwable $error) {
                if ($error instanceof HttpExceptionInterface && $error->getStatusCode() === 404) {
                    throw $error;
                }
                $selectionUnavailable = true;
            }
        }

        return view('operations.index', compact('page', 'selected', 'selectionUnavailable', 'offset', 'unit', 'equipment', 'screens', 'screen', 'components', 'draftComponent', 'componentDetail'));
    }
}
