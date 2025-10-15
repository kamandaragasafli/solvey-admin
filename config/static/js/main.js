// Orders Chart (Line)
// fetch('/monthly-orders-data/')
//   .then(response => response.json())
//   .then(data => {
//     const ctx = document.getElementById('ordersChart').getContext('2d');
//     new Chart(ctx, {
//       type: 'line',
//       data: {
//         labels: data.labels,
//         datasets: [{
//           label: 'Sifarişlər',
//           data: data.data,
//           backgroundColor: 'rgba(91, 112, 243, 0.2)',
//           borderColor: '#5b70f3',
//           borderWidth: 2,
//           tension: 0.3,
//           fill: true
//         }]
//       },
//       options: {
//         responsive: true,
//         plugins: {
//           legend: { position: 'top' }
//         },
//         maintainAspectRatio: false
//       }
//     });
//   })
//   .catch(error => console.error('Sipariş grafiği xətası:', error));

 

//   fetch('/stock-chart-data/')
//     .then(response => response.json())
//     .then(data => {
//       const ctx = document.getElementById('stockChart').getContext('2d');
//       new Chart(ctx, {
//         type: 'bar',
//         data: {
//           labels: data.labels,
//           datasets: [{
//             label: 'Stok Sayı',
//             data: data.data,
//             backgroundColor: '#55e0a3'
//           }]
//         },
//         options: {
//           responsive: true,
//           plugins: {
//             legend: { display: false }
//           },
//           maintainAspectRatio: false
//         }
//       });
//     })
//     .catch(error => console.error('Chart Data Error:', error));
//   fetch('/monthly-sales-data/')
//   .then(response => response.json())
//   .then(data => {
//     const ctx = document.getElementById('monthlySalesChart').getContext('2d');
//     new Chart(ctx, {
//       type: 'bar',
//       data: {
//         labels: data.labels,
//         datasets: [{
//           label: 'Satışlar (AZN)',
//           data: data.data,
//           backgroundColor: '#4850b9'
//         }]
//       },
//       options: {
//         responsive: true,
//         plugins: {
//           legend: { display: false }
//         },
//         maintainAspectRatio: false,
//         scales: {
//           y: {
//             beginAtZero: true,
//             ticks: {
//               callback: function(value) {
//                 return value + ' ₼';  // AZN simgesi
//               }
//             }
//           }
          
//         }
//       }
//     });
//   })
//   .catch(error => console.error('Satış grafiği xətası:', error));




  var tooltipTriggerList = [].slice.call(document.querySelectorAll('[data-bs-toggle="tooltip"]'));
  var tooltipList = tooltipTriggerList.map(function (tooltipTriggerEl) {
    return new bootstrap.Tooltip(tooltipTriggerEl);
  });





// Notification Functions
function showNotificationDropdown() {
    // Remove existing dropdown
    const existingDropdown = document.querySelector('.notification-dropdown');
    if (existingDropdown) {
        existingDropdown.remove();
        return;
    }

    const dropdown = document.createElement('div');
    dropdown.className = 'notification-dropdown';
    dropdown.innerHTML = `
        <div class="notification-header">
            <h4>Bildirişlər</h4>
            <button class="close-btn">&times;</button>
        </div>
        <div class="notification-list">
            <div class="notification-item">
                <i class="fas fa-exclamation-triangle text-warning"></i>
                <div>
                    <p>Az stok xəbərdarlığı</p>
                    <small>15 məhsul az stokda</small>
                </div>
            </div>
            <div class="notification-item">
                <i class="fas fa-user-plus text-success"></i>
                <div>
                    <p>Yeni istifadəçi qeydiyyatı</p>
                    <small>5 dəqiqə əvvəl</small>
                </div>
            </div>
            <div class="notification-item">
                <i class="fas fa-chart-line text-primary"></i>
                <div>
                    <p>Günlük backup tamamlandı</p>
                    <small>10 dəqiqə əvvəl</small>
                </div>
            </div>
        </div>
    `;

    // Position dropdown
    const notificationBtn = document.querySelector('.notification-btn');
    const rect = notificationBtn.getBoundingClientRect();
    dropdown.style.position = 'fixed';
    dropdown.style.top = (rect.bottom + 10) + 'px';
    dropdown.style.right = '20px';
    dropdown.style.zIndex = '1000';

    document.body.appendChild(dropdown);

    // Close functionality
    const closeBtn = dropdown.querySelector('.close-btn');
    closeBtn.addEventListener('click', () => dropdown.remove());

    // Close on outside click
    document.addEventListener('click', function(e) {
        if (!dropdown.contains(e.target) && !notificationBtn.contains(e.target)) {
            dropdown.remove();
        }
    });
}

// Toast Notification Function
function showToast(message, type = 'info') {
    const toast = document.createElement('div');
    toast.className = `toast toast-${type}`;

    
    const icons = {
        success: 'bi-check-circle',
        error: 'bi-x-circle',
        warning: 'bi-exclamation-triangle',
        info: 'bi-info-circle'
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
    toast.style.boxShadow = 'var(--shadow-lg)';
    toast.style.zIndex = '1001';
    toast.style.transform = 'translateX(100%)';
    toast.style.transition = 'transform 0.3s ease';
    toast.style.display = 'flex';
    toast.style.alignItems = 'center';
    toast.style.gap = '0.5rem';
    toast.style.color = 'white';
    toast.style.fontWeight = '500';
    toast.style.minWidth = '300px';
    
    // Set background color based on type
    const colors = {
        success: 'var(--success-color)',
        error: 'var(--danger-color)',
        warning: 'var(--warning-color)',
        info: 'var(--primary-color)'
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
            toast.remove();
        }, 300);
    }, 4000);
}

// Additional CSS for animations and notifications
const additionalStyles = `
.notification-dropdown {
    background: var(--bg-card);
    border: 1px solid var(--border-color);
    border-radius: 0.5rem;
    box-shadow: var(--shadow-lg);
    width: 300px;
    max-height: 400px;
    overflow-y: auto;
    animation: slideDown 0.3s ease;
}

.notification-header {
    padding: 1rem;
    border-bottom: 1px solid var(--border-color);
    display: flex;
    justify-content: space-between;
    align-items: center;
}

.notification-header h4 {
    margin: 0;
    font-size: 1rem;
    font-weight: 600;
    color: var(--text-primary);
}

.close-btn {
    background: none;
    border: none;
    font-size: 1.5rem;
    cursor: pointer;
    color: var(--text-secondary);
    padding: 0;
    width: 24px;
    height: 24px;
    display: flex;
    align-items: center;
    justify-content: center;
}

.close-btn:hover {
    color: var(--text-primary);
}

.notification-list {
    padding: 0.5rem;
}

.notification-item {
    display: flex;
    align-items: center;
    gap: 0.75rem;
    padding: 0.75rem;
    border-radius: 0.375rem;
    transition: background-color 0.2s ease;
    cursor: pointer;
}

.notification-item:hover {
    background-color: var(--bg-secondary);
}

.notification-item i {
    font-size: 1.25rem;
}

.notification-item p {
    margin: 0;
    font-weight: 500;
    font-size: 0.875rem;
    color: var(--text-primary);
}

.notification-item small {
    color: var(--text-secondary);
    font-size: 0.75rem;
}

.text-warning { color: var(--warning-color) !important; }
.text-success { color: var(--success-color) !important; }
.text-primary { color: var(--primary-color) !important; }

@keyframes slideDown {
    from {
        opacity: 0;
        transform: translateY(-10px);
    }
    to {
        opacity: 1;
        transform: translateY(0);
    }
}

@keyframes fadeOut {
    from {
        opacity: 1;
        transform: translateY(0);
    }
    to {
        opacity: 0;
        transform: translateY(-20px);
    }
}
`;

// Add the additional styles to the document
const styleSheet = document.createElement('style');
styleSheet.textContent = additionalStyles;
document.head.appendChild(styleSheet);



