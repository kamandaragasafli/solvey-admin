









function editDoctor() {
    const modal = document.getElementById('editDoctorModal');
    modal.classList.add('show');
    modal.style.display = 'flex';
    
    // Handle form submission
    const form = document.getElementById('editDoctorForm');
    form.onsubmit = function(e) {
        e.preventDefault();
        
        // Get form data
        const formData = new FormData(form);
        const doctorData = {
            name: document.getElementById('doctorName').value,
            specialty: document.getElementById('doctorSpecialty').value,
            phone: document.getElementById('doctorPhone').value,
            degree: document.getElementById('doctorDegree').value,
            category: document.getElementById('doctorCategory').value,
            region: document.getElementById('doctorRegion').value
        };
        
        // Simulate API call
        showToast('Həkim məlumatları yenilənir...', 'info');
        
        setTimeout(() => {
            // Update the doctor info card
            updateDoctorInfo(doctorData);
            closeModal('editDoctorModal');
            showToast('Həkim məlumatları uğurla yeniləndi!', 'success');
        }, 1500);
    };
}

function deleteDoctor() {
    if (confirm('Bu həkimi silmək istədiyinizə əminsiniz? Bu əməliyyat geri alına bilməz.')) {
        showToast('Həkim silinir...', 'warning');
        
        setTimeout(() => {
            showToast('Həkim uğurla silindi!', 'success');
            // Redirect to doctors list after 2 seconds
            setTimeout(() => {
                window.location.href = '/doctors';
            }, 2000);
        }, 1500);
    }
}

function updateDoctorInfo(data) {
    // Update the doctor name
    document.querySelector('.doctor-name').textContent = data.name;
    
    // Update info items
    const infoItems = document.querySelectorAll('.info-item');
    infoItems.forEach(item => {
        const label = item.querySelector('.info-label').textContent;
        const valueElement = item.querySelector('.info-value');
        
        switch(label) {
            case 'İxtisas:':
                valueElement.textContent = data.specialty;
                break;
            case 'Nömrə:':
                valueElement.textContent = data.phone;
                break;
            case 'Dərəcə:':
                valueElement.textContent = data.degree;
                break;
            case 'Kateqoriya:':
                valueElement.textContent = data.category;
                break;
            case 'Bölgə:':
                valueElement.textContent = data.region;
                break;
        }
    });
}

// Payment Management Functions
function addPayment() {
    showToast('Yeni ödəniş əlavə etmə pəncərəsi açılır...', 'info');
    // Here you would open an add payment modal
}

function deletePayment(paymentId) {
    if (confirm('Bu ödənişi silmək istədiyinizə əminsiniz?')) {
        const row = event.target.closest('tr');
        
        // Add fade out animation
        row.style.transition = 'all 0.3s ease';
        row.style.opacity = '0';
        row.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            row.remove();
            showToast('Ödəniş uğurla silindi!', 'success');
            updatePaymentCount();
        }, 300);
    }
}

// Recipe Management Functions
function addRecipe() {
    showToast('Yeni resept əlavə etmə pəncərəsi açılır...', 'info');
    // Here you would open an add recipe modal
}

function editRecipe(recipeId) {
    showToast(`Resept #${recipeId} redaktə edilir...`, 'info');

    // Here you would open an edit recipe modal
}

function deleteRecipe(recipeId) {
    if (confirm('Bu resepti silmək istədiyinizə əminsiniz?')) {
        const row = event.target.closest('tr');
        
        // Add fade out animation
        row.style.transition = 'all 0.3s ease';
        row.style.opacity = '0';
        row.style.transform = 'translateX(-20px)';
        
        setTimeout(() => {
            row.remove();
            showToast('Resept uğurla silindi!', 'success');
            updateRecipeCount();
        }, 300);
    }
}

// Modal Functions
function closeModal(modalId) {
    const modal = document.getElementById(modalId);
    modal.classList.remove('show');
    
    setTimeout(() => {
        modal.style.display = 'none';
    }, 300);
}

// Close modal when clicking outside
document.addEventListener('click', function(e) {
    if (e.target.classList.contains('modal')) {
        const modalId = e.target.id;
        closeModal(modalId);
    }
});

// Statistics Animation
function animateStatistics() {
    const statValues = document.querySelectorAll('.stat-value');
    
    statValues.forEach(stat => {
        const finalValue = stat.textContent;
        const isMonetary = finalValue.includes('₼');
        const numericValue = parseInt(finalValue.replace(/[^\d]/g, ''));
        
        if (isNaN(numericValue)) return;
        
        let currentValue = 0;
        const increment = Math.ceil(numericValue / 50);
        const duration = 1500;
        const stepTime = duration / (numericValue / increment);
        
        const timer = setInterval(() => {
            currentValue += increment;
            
            if (currentValue >= numericValue) {
                currentValue = numericValue;
                clearInterval(timer);
            }
            
            if (isMonetary) {
                stat.textContent = `${currentValue.toLocaleString()} ₼`;
            } else {
                stat.textContent = currentValue.toString();
            }
        }, stepTime);
    });
}

// Update counters after deletions
function updatePaymentCount() {
    const paymentRows = document.querySelectorAll('.table-card:first-child tbody tr');
    const paymentStat = document.querySelector('.stat-card.payments .stat-value');
    paymentStat.textContent = paymentRows.length.toString();
}

function updateRecipeCount() {
    const recipeRows = document.querySelectorAll('.table-card:last-child tbody tr');
    const recipeStat = document.querySelector('.stat-card.recipes .stat-value');
    recipeStat.textContent = recipeRows.length.toString();
}

// Table hover effects
function addTableHoverEffects() {
    const tableRows = document.querySelectorAll('.data-table tbody tr');
    
    tableRows.forEach(row => {
        row.addEventListener('mouseenter', function() {
            this.style.transform = 'translateX(4px)';
        });
        
        row.addEventListener('mouseleave', function() {
            this.style.transform = 'translateX(0)';
        });
    });
}

// Toast Notification Function
function showToast(message, type = 'info') {
    // Remove existing toast
    const existingToast = document.querySelector('.toast');
    if (existingToast) {
        existingToast.remove();
    }
    
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    
    const icons = {
        success: 'bi-check-circle-fill',
        error: 'bi-x-circle-fill',
        warning: 'bi-exclamation-triangle-fill',
        info: 'bi-info-circle-fill'
    };
    
    toast.innerHTML = `
        <i class="bi ${icons[type]}"></i>
        <span>${message}</span>
    `;
    
    // Style the toast
    toast.style.position = 'fixed';
    toast.style.bottom = '20px';
    toast.style.right = '20px';
    toast.style.padding = '1rem 1.5rem';
    toast.style.borderRadius = '0.5rem';
    toast.style.boxShadow = 'var(--shadow-xl)';
    toast.style.zIndex = '1001';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'transform 0.3s ease';
    toast.style.display = 'flex';
    toast.style.alignItems = 'center';
    toast.style.gap = '0.5rem';
    toast.style.color = 'white';
    toast.style.fontWeight = '500';
    toast.style.minWidth = '300px';
    toast.style.fontSize = '0.875rem';
    
    // Set background color based on type
    const colors = {
        success: '#10b981',
        error: '#ef4444',
        warning: '#f59e0b',
        info: '#3b82f6'
    };
    toast.style.background = colors[type];
    
    document.body.appendChild(toast);
    
    // Animate in
    setTimeout(() => {
        toast.style.transform = 'translateX(0)';
    }, 100);
    
    // Remove after 4 seconds
    setTimeout(() => {
        toast.style.transform = 'translateX(100%)';
        setTimeout(() => {
            if (toast.parentNode) {
                toast.remove();
            }
        }, 300);
    }, 4000);
}

// Keyboard shortcuts
document.addEventListener('keydown', function(e) {
    // ESC to close modals
    if (e.key === 'Escape') {
        const openModal = document.querySelector('.modal.show');
        if (openModal) {
            closeModal(openModal.id);
        }
    }
    
    // Ctrl+E to edit doctor
    if (e.ctrlKey && e.key === 'e') {
        e.preventDefault();
        editDoctor();
    }
    
    // Ctrl+B to go back
    if (e.ctrlKey && e.key === 'b') {
        e.preventDefault();
        goBack();
    }
});

// Add loading states to buttons
document.addEventListener('click', function(e) {
    if (e.target.matches('.action-btn, .add-btn, .btn')) {
        const button = e.target;
        const originalContent = button.innerHTML;
        
        // Add loading state
        button.style.opacity = '0.7';
        button.style.pointerEvents = 'none';
        
        // Reset after a short delay (for demo purposes)
        setTimeout(() => {
            button.style.opacity = '1';
            button.style.pointerEvents = 'auto';
        }, 500);
    }
});

// Initialize tooltips for action buttons
function initializeTooltips() {
    const actionButtons = document.querySelectorAll('.action-icon');
    
    actionButtons.forEach(button => {
        button.addEventListener('mouseenter', function() {
            const tooltip = document.createElement('div');
            tooltip.className = 'tooltip';
            
            let tooltipText = '';
            if (this.classList.contains('edit')) {
                tooltipText = 'Redaktə et';
            } else if (this.classList.contains('delete')) {
                tooltipText = 'Sil';
            }
            
            tooltip.textContent = tooltipText;
            tooltip.style.position = 'absolute';
            tooltip.style.background = 'rgba(0, 0, 0, 0.8)';
            tooltip.style.color = 'white';
            tooltip.style.padding = '0.25rem 0.5rem';
            tooltip.style.borderRadius = '0.25rem';
            tooltip.style.fontSize = '0.75rem';
            tooltip.style.zIndex = '1000';
            tooltip.style.pointerEvents = 'none';
            tooltip.style.whiteSpace = 'nowrap';
            
            document.body.appendChild(tooltip);
            
            const rect = this.getBoundingClientRect();
            tooltip.style.left = (rect.left + rect.width / 2 - tooltip.offsetWidth / 2) + 'px';
            tooltip.style.top = (rect.top - tooltip.offsetHeight - 5) + 'px';
            
            this.tooltip = tooltip;
        });
        
        button.addEventListener('mouseleave', function() {
            if (this.tooltip) {
                this.tooltip.remove();
                this.tooltip = null;
            }
        });
    });
}

// Initialize tooltips when page loads
document.addEventListener('DOMContentLoaded', initializeTooltips);