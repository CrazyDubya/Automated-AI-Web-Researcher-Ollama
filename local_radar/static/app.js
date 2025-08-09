// Local Radar Dashboard JavaScript
document.addEventListener('DOMContentLoaded', function() {
    const searchInput = document.getElementById('searchInput');
    const tagFilter = document.getElementById('tagFilter');
    const briefsGrid = document.getElementById('briefsGrid');
    const dossiersGrid = document.getElementById('dossiersGrid');
    
    // Search functionality
    if (searchInput) {
        searchInput.addEventListener('input', function() {
            filterContent();
        });
    }
    
    // Tag filter functionality
    if (tagFilter) {
        tagFilter.addEventListener('change', function() {
            filterContent();
        });
    }
    
    function filterContent() {
        const searchTerm = searchInput ? searchInput.value.toLowerCase() : '';
        const selectedTag = tagFilter ? tagFilter.value : '';
        
        // Filter briefs
        if (briefsGrid) {
            const briefCards = briefsGrid.querySelectorAll('.card');
            briefCards.forEach(card => {
                const title = card.querySelector('h3').textContent.toLowerCase();
                const tags = card.dataset.tags || '';
                
                const matchesSearch = title.includes(searchTerm);
                const matchesTag = !selectedTag || tags.includes(selectedTag);
                
                card.style.display = (matchesSearch && matchesTag) ? 'block' : 'none';
            });
        }
        
        // Filter dossiers
        if (dossiersGrid) {
            const dossierCards = dossiersGrid.querySelectorAll('.card');
            dossierCards.forEach(card => {
                const title = card.querySelector('h3').textContent.toLowerCase();
                const tags = card.dataset.tags || '';
                
                const matchesSearch = title.includes(searchTerm);
                const matchesTag = !selectedTag || tags.includes(selectedTag);
                
                card.style.display = (matchesSearch && matchesTag) ? 'block' : 'none';
            });
        }
    }
    
    // Auto-refresh functionality (if enabled)
    const autoRefreshInterval = 300000; // 5 minutes
    if (window.location.pathname.endsWith('index.html')) {
        setInterval(() => {
            window.location.reload();
        }, autoRefreshInterval);
    }
});