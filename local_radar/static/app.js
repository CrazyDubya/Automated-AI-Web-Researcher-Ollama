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
    
    // Auto-refresh functionality (user-configurable)
    if (window.location.pathname.endsWith('index.html')) {
        // Create auto-refresh controls if not present
        let controlsContainer = document.getElementById('autoRefreshControls');
        if (!controlsContainer) {
            controlsContainer = document.createElement('div');
            controlsContainer.id = 'autoRefreshControls';
            controlsContainer.style.margin = '1em 0';
            controlsContainer.innerHTML = `
                <label>
                    <input type="checkbox" id="autoRefreshCheckbox">
                    Enable auto-refresh
                </label>
                <label style="margin-left:1em;">
                    Interval:
                    <select id="autoRefreshIntervalSelect">
                        <option value="60000">1 min</option>
                        <option value="180000">3 min</option>
                        <option value="300000">5 min</option>
                        <option value="600000">10 min</option>
                    </select>
                </label>
            `;
            // Insert at top of body or main content
            document.body.insertBefore(controlsContainer, document.body.firstChild);
        }

        const autoRefreshCheckbox = document.getElementById('autoRefreshCheckbox');
        const autoRefreshIntervalSelect = document.getElementById('autoRefreshIntervalSelect');

        // Load settings from localStorage
        const savedEnabled = localStorage.getItem('autoRefreshEnabled') === 'true';
        const savedInterval = localStorage.getItem('autoRefreshInterval') || '300000';
        autoRefreshCheckbox.checked = savedEnabled;
        autoRefreshIntervalSelect.value = savedInterval;

        let autoRefreshTimer = null;
        function setupAutoRefresh() {
            if (autoRefreshTimer) {
                clearInterval(autoRefreshTimer);
                autoRefreshTimer = null;
            }
            if (autoRefreshCheckbox.checked) {
                autoRefreshTimer = setInterval(() => {
                    window.location.reload();
                }, parseInt(autoRefreshIntervalSelect.value, 10));
            }
        }

        // Set up event listeners
        autoRefreshCheckbox.addEventListener('change', function() {
            localStorage.setItem('autoRefreshEnabled', autoRefreshCheckbox.checked);
            setupAutoRefresh();
        });
        autoRefreshIntervalSelect.addEventListener('change', function() {
            localStorage.setItem('autoRefreshInterval', autoRefreshIntervalSelect.value);
            setupAutoRefresh();
        });

        // Initial setup
        setupAutoRefresh();
    }
});