// Həkim Admin üçün xüsusi JavaScript
document.addEventListener('DOMContentLoaded', function() {
    // Avtomatik axtarış
    const searchInput = document.querySelector('#searchbar');
    if (searchInput) {
        searchInput.placeholder = 'Həkim adı, barkod və ya bölgə axtar...';
    }
    
    // Action buttonları üçün hover effekti
    const actionButtons = document.querySelectorAll('.btn-group a');
    actionButtons.forEach(btn => {
        btn.addEventListener('mouseenter', function() {
            this.style.opacity = '0.8';
            this.style.transform = 'scale(1.05)';
        });
        btn.addEventListener('mouseleave', function() {
            this.style.opacity = '1';
            this.style.transform = 'scale(1)';
        });
    });
    
    // Cədvəl sıralama üçün
    const tableHeaders = document.querySelectorAll('th.sortable');
    tableHeaders.forEach(header => {
        header.style.cursor = 'pointer';
        header.addEventListener('click', function() {
            this.classList.toggle('asc');
        });
    });
});