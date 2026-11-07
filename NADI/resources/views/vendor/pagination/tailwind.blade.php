@if($paginator->hasPages())
    <nav class="compact-pagination" role="navigation" aria-label="Pagination">
        <span class="pagination-summary">Halaman {{ $paginator->currentPage() }} dari {{ $paginator->lastPage() }}</span>
        <div class="pagination-links">
            @if($paginator->onFirstPage())<span aria-disabled="true">← Sebelumnya</span>@else<a class="button secondary small" href="{{ $paginator->previousPageUrl() }}" rel="prev">← Sebelumnya</a>@endif
            @if($paginator->hasMorePages())<a class="button secondary small" href="{{ $paginator->nextPageUrl() }}" rel="next">Berikutnya →</a>@else<span aria-disabled="true">Berikutnya →</span>@endif
        </div>
    </nav>
@endif
