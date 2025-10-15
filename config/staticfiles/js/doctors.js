


class MedicalDashboard {
    constructor() {
        this.currentPage = 1;
        this.itemsPerPage = 10;
        this.totalItems = 156;
        this.filteredItems = 156;
        this.filters = {
            search: '',
            debtFilter: '',
            regionFilter: ''
        };
        
        this.init();
    }

    init() {
        this.updateStats();
        this.animateOnLoad();
    }

    

  



    bindPaginationEvents() {
        const paginationLinks = document.querySelectorAll('.page-link[data-page]');
        paginationLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                e.preventDefault();
                const page = parseInt(e.target.getAttribute('data-page'));
                this.goToPage(page);
            });
        });
    }

    bindTableEvents() {
        // Doctor name clicks


        // Phone number clicks
        const phoneLinks = document.querySelectorAll('.phone-link');
        phoneLinks.forEach(link => {
            link.addEventListener('click', (e) => {
                this.trackPhoneCall(e.target.textContent.trim());
            });
        });
    }

    applyFilters() {
        this.showLoading();
        
        // Simulate API call delay
        setTimeout(() => {
            this.filterData();
            this.updateTable();
            this.updatePagination();
            this.updateStats();
            this.hideLoading();
            this.showNotification('Filtrlər tətbiq edildi', 'success');
        }, 800);
    }



    updateTable() {
        const tbody = document.getElementById('tableBody');
        tbody.classList.add('fade-out');
        
        setTimeout(() => {
            // Update results count
            document.getElementById('resultsCount').textContent = this.filteredItems;
            tbody.classList.remove('fade-out');
            tbody.classList.add('fade-in');
        }, 300);
    }

    updatePagination() {
        const totalPages = Math.ceil(this.filteredItems / this.itemsPerPage);
        const paginationInfo = document.querySelector('.pagination-info');
        paginationInfo.innerHTML = `Səhifə <strong>${this.currentPage}</strong> / <strong>${totalPages}</strong>`;
        
        // Update pagination buttons (simplified for demo)
        this.generatePaginationButtons(totalPages);
    }

    generatePaginationButtons(totalPages) {
        const pagination = document.querySelector('.pagination');
        let paginationHTML = '';
        
        // Previous button
        const prevDisabled = this.currentPage === 1 ? 'disabled' : '';
        paginationHTML += `
            <li class="page-item ${prevDisabled}">
                <span class="page-link">
                    <i class="fas fa-chevron-left"></i>
                    Əvvəlki
                </span>
            </li>
        `;
        
        // Page numbers
        for (let i = 1; i <= Math.min(totalPages, 5); i++) {
            const active = i === this.currentPage ? 'active' : '';
            paginationHTML += `
                <li class="page-item ${active}">
                    <a class="page-link" href="#" data-page="${i}">${i}</a>
                </li>
            `;
        }
        
        // Next button
        const nextDisabled = this.currentPage === totalPages ? 'disabled' : '';
        paginationHTML += `
            <li class="page-item ${nextDisabled}">
                <a class="page-link" href="#" data-page="${this.currentPage + 1}">
                    Növbəti
                    <i class="fas fa-chevron-right"></i>
                </a>
            </li>
        `;
        
        pagination.innerHTML = paginationHTML;
        this.bindPaginationEvents();
    }

    goToPage(page) {
        this.currentPage = page;
        this.updateTable();
        this.updatePagination();
        this.scrollToTop();
    }

    resetFilters() {
        // Reset form
        document.getElementById('filtersForm').reset();
        
        // Reset internal state
        this.filters = {
            search: '',
            debtFilter: '',
            regionFilter: ''
        };
        
        this.filteredItems = this.totalItems;
        this.currentPage = 1;
        
        this.updateTable();
        this.updatePagination();
        this.updateStats();
        
        this.showNotification('Filtrlər sıfırlandı', 'info');
    }

    updateStats() {
        // Animate counter updates
        this.animateCounter('totalDoctors', this.filteredItems);
        this.animateCounter('activePayments', Math.floor(this.filteredItems * 0.57));
        this.animateCounter('pendingDebts', Math.floor(this.filteredItems * 0.15));
    }

    animateCounter(elementId, targetValue) {
        const element = document.getElementById(elementId);
        const startValue = parseInt(element.textContent) || 0;
        const duration = 1000;
        const startTime = performance.now();
        
        const animate = (currentTime) => {
            const elapsed = currentTime - startTime;
            const progress = Math.min(elapsed / duration, 1);
            
            const currentValue = Math.floor(startValue + (targetValue - startValue) * this.easeOutCubic(progress));
            element.textContent = currentValue;
            
            if (progress < 1) {
                requestAnimationFrame(animate);
            }
        };
        
        requestAnimationFrame(animate);
    }

    easeOutCubic(t) {
        return 1 - Math.pow(1 - t, 3);
    }

    exportToExcel() {
        this.showLoading();
        
        // Simulate export process
        setTimeout(() => {
            this.hideLoading();
            this.showNotification('Excel faylı uğurla yükləndi', 'success');
            
            // Create and trigger download (demo)
            const link = document.createElement('a');
            link.href = '#';
            link.download = `hekim_melumatlari_${new Date().toISOString().split('T')[0]}.xlsx`;
            link.click();
        }, 2000);
    }

    showDeleteConfirmation() {
        const confirmed = confirm('Seçilmiş məlumatları silmək istədiyinizə əminsiniz?');
        if (confirmed) {
            this.showLoading();
            
            setTimeout(() => {
                this.hideLoading();
                this.showNotification('Məlumatlar uğurla silindi', 'warning');
            }, 1500);
        }
    }

    showDoctorDetails(doctorName) {
        this.showNotification(`${doctorName} məlumatları yüklənir...`, 'info');
        
        // Simulate navigation to doctor details
        setTimeout(() => {
            console.log(`Navigating to details for: ${doctorName}`);
        }, 500);
    }

    trackPhoneCall(phoneNumber) {
        console.log(`Phone call initiated to: ${phoneNumber}`);
        this.showNotification(`${phoneNumber} nömrəsinə zəng edilir...`, 'info');
    }

    showLoading() {
        const overlay = document.getElementById('loadingOverlay');
        overlay.classList.add('active');
    }

    hideLoading() {
        const overlay = document.getElementById('loadingOverlay');
        overlay.classList.remove('active');
    }

    showNotification(message, type = 'info') {
        // Create notification element
        const notification = document.createElement('div');
        notification.className = `notification notification-${type}`;
        notification.innerHTML = `
            <div class="notification-content">
                <i class="fas fa-${this.getNotificationIcon(type)}"></i>
                <span>${message}</span>
            </div>
        `;
        
        // Add styles
        notification.style.cssText = `
            position: fixed;
            top: 20px;
            right: 20px;
            background: ${this.getNotificationColor(type)};
            color: white;
            padding: 1rem 1.5rem;
            border-radius: 12px;
            box-shadow: 0 10px 30px rgba(0, 0, 0, 0.2);
            z-index: 1001;
            transform: translateX(400px);
            transition: transform 0.3s ease;
            max-width: 300px;
        `;
        
        notification.querySelector('.notification-content').style.cssText = `
            display: flex;
            align-items: center;
            gap: 0.5rem;
            font-weight: 600;
        `;
        
        document.body.appendChild(notification);
        
        // Animate in
        setTimeout(() => {
            notification.style.transform = 'translateX(0)';
        }, 100);
        
        // Auto remove
        setTimeout(() => {
            notification.style.transform = 'translateX(400px)';
            setTimeout(() => {
                document.body.removeChild(notification);
            }, 300);
        }, 3000);
    }

    getNotificationIcon(type) {
        const icons = {
            success: 'check-circle',
            warning: 'exclamation-triangle',
            error: 'times-circle',
            info: 'info-circle'
        };
        return icons[type] || 'info-circle';
    }

    getNotificationColor(type) {
        const colors = {
            success: 'linear-gradient(135deg, #48bb78 0%, #38a169 100%)',
            warning: 'linear-gradient(135deg, #ed8936 0%, #dd6b20 100%)',
            error: 'linear-gradient(135deg, #f56565 0%, #e53e3e 100%)',
            info: 'linear-gradient(135deg, #4299e1 0%, #3182ce 100%)'
        };
        return colors[type] || colors.info;
    }

    animateOnLoad() {
        // Add entrance animations
        const elements = document.querySelectorAll('.dashboard-header, .filters-card, .table-card');
        elements.forEach((element, index) => {
            element.style.opacity = '0';
            element.style.transform = 'translateY(30px)';
            
            setTimeout(() => {
                element.style.transition = 'all 0.6s ease';
                element.style.opacity = '1';
                element.style.transform = 'translateY(0)';
            }, index * 200);
        });
    }

    scrollToTop() {
        window.scrollTo({
            top: 0,
            behavior: 'smooth'
        });
    }

    debounce(func, wait) {
        let timeout;
        return function executedFunction(...args) {
            const later = () => {
                clearTimeout(timeout);
                func(...args);
            };
            clearTimeout(timeout);
            timeout = setTimeout(later, wait);
        };
    }
}

// Initialize dashboard when DOM is loaded
document.addEventListener('DOMContentLoaded', () => {
    const dashboard = new MedicalDashboard();
    
    // Add some additional interactive features
    addTableEnhancements();
    addKeyboardShortcuts();
    addResponsiveEnhancements();
});

function addTableEnhancements() {
    // Add row selection functionality
    const tableRows = document.querySelectorAll('#tableBody tr');
    tableRows.forEach(row => {
        row.addEventListener('click', (e) => {
            if (e.target.tagName !== 'A') {
                row.classList.toggle('selected');
                updateSelectedCount();
            }
        });
    });
}

function updateSelectedCount() {
    const selectedRows = document.querySelectorAll('#tableBody tr.selected');
    if (selectedRows.length > 0) {
        console.log(`${selectedRows.length} rows selected`);
    }
}

function addKeyboardShortcuts() {
    document.addEventListener('keydown', (e) => {
        // Ctrl/Cmd + F for search focus
        if ((e.ctrlKey || e.metaKey) && e.key === 'f') {
            e.preventDefault();
            document.getElementById('searchInput').focus();
        }
        
        // Escape to clear search
        if (e.key === 'Escape') {
            const searchInput = document.getElementById('searchInput');
            if (searchInput === document.activeElement) {
                searchInput.value = '';
                searchInput.dispatchEvent(new Event('input'));
            }
        }
    });
}

function addResponsiveEnhancements() {
    // Add mobile menu toggle if needed
    const handleResize = () => {
        const isMobile = window.innerWidth < 768;
        const table = document.querySelector('.data-table');
        
        if (isMobile) {
            table.classList.add('mobile-optimized');
        } else {
            table.classList.remove('mobile-optimized');
        }
    };
    
    window.addEventListener('resize', handleResize);
    handleResize(); // Initial call
}

// Add CSS for selected rows
const style = document.createElement('style');
style.textContent = `
    #tableBody tr.selected {
        background: linear-gradient(135deg, rgba(102, 126, 234, 0.1) 0%, rgba(118, 75, 162, 0.1) 100%) !important;
        border-left: 4px solid #667eea;
    }
    
    .fade-out {
        opacity: 0;
        transition: opacity 0.3s ease;
    }
    
    .mobile-optimized {
        font-size: 0.75rem;
    }
    
    .mobile-optimized .doctor-info {
        flex-direction: column;
        gap: 0.25rem;
    }
    
    .mobile-optimized .doctor-avatar {
        width: 30px;
        height: 30px;
        font-size: 0.9rem;
    }
`;
document.head.appendChild(style);


