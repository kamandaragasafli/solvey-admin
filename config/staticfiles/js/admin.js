document.addEventListener('DOMContentLoaded', function() {



    // Tab Navigation
    const tabBtns = document.querySelectorAll('.tab-btn');
    const tabPanes = document.querySelectorAll('.tab-pane');

    tabBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const targetTab = this.getAttribute('data-tab');
            
            // Remove active class from all tabs and panes
            tabBtns.forEach(b => b.classList.remove('active'));
            tabPanes.forEach(p => p.classList.remove('active'));
            
            // Add active class to clicked tab and corresponding pane
            this.classList.add('active');
            document.getElementById(targetTab).classList.add('active');
        });
    });

    // File Input Enhancement
    const fileInputs = document.querySelectorAll('.file-input');
    fileInputs.forEach(input => {
        input.addEventListener('change', function() {
            const label = this.nextElementSibling;
            const fileName = this.files[0] ? this.files[0].name : 'Excel faylı seçin';
            
            if (this.files[0]) {
                label.innerHTML = `<i class="bi bi-file-earmark-excel"></i> ${fileName}`;
                label.style.color = 'var(--success-color)';
                label.style.borderColor = 'var(--success-color)';
            }
        });
    });


    // User Management Actions
    const userActionBtns = document.querySelectorAll('.user-actions .btn-icon');
    userActionBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const action = this.classList.contains('edit') ? 'edit' : 
                          this.classList.contains('toggle') ? 'toggle' : 'delete';
            const userCard = this.closest('.user-card');
            const userName = userCard.querySelector('h5').textContent;
            
            switch(action) {
                case 'edit':
                    showEditUserModal(userName);
                    break;
                case 'toggle':
                    toggleUserStatus(this, userName);
                    break;
                case 'delete':
                    deleteUser(userCard, userName);
                    break;
            }
        });
    });

    // Backup Actions
    const backupBtns = document.querySelectorAll('.backup-btn');
    backupBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const action = this.classList.contains('create') ? 'create' :
                          this.classList.contains('schedule') ? 'schedule' : 'restore';
            
            switch(action) {
                case 'create':
                    createBackup();
                    break;
                case 'schedule':
                    showScheduleModal();
                    break;
                case 'restore':
                    showRestoreModal();
                    break;
            }
        });
    });

    // Backup Item Actions
    const backupActionBtns = document.querySelectorAll('.backup-actions .btn-icon');
    backupActionBtns.forEach(btn => {
        btn.addEventListener('click', function() {
            const action = this.classList.contains('download') ? 'download' :
                          this.classList.contains('restore') ? 'restore' :
                          this.classList.contains('retry') ? 'retry' : 'delete';
            const backupItem = this.closest('.backup-item');
            const backupName = backupItem.querySelector('h5').textContent;
            
            switch(action) {
                case 'download':
                    downloadBackup(backupName);
                    break;
                case 'restore':
                    restoreBackup(backupName);
                    break;
                case 'retry':
                    retryBackup(backupName);
                    break;
                case 'delete':
                    deleteBackup(backupItem, backupName);
                    break;
            }
        });
    });

    // Search functionality
    const searchInput = document.querySelector('.search-input');
    searchInput.addEventListener('input', function(e) {
        const searchTerm = e.target.value.toLowerCase();
        console.log('Searching for:', searchTerm);
        // Add search functionality here
    });

    // Notification functionality
    const notificationBtn = document.querySelector('.notification-btn');
    notificationBtn.addEventListener('click', function() {
        showNotificationDropdown();
    });
});

// User Management Functions
function showEditUserModal(userName) {
    showToast(`${userName} istifadəçisinin redaktə pəncərəsi açılır...`, 'info');
    // Here you would open an edit modal
}

function toggleUserStatus(btn, userName) {
    const isActive = btn.classList.contains('inactive');
    
    if (isActive) {
        btn.classList.remove('inactive');
        btn.innerHTML = '<i class="bi bi-toggle-on"></i>';
        btn.style.background = 'rgba(16, 185, 129, 0.1)';
        btn.style.color = 'var(--success-color)';
        showToast(`${userName} istifadəçisi aktivləşdirildi`, 'success');
    } else {
        btn.classList.add('inactive');
        btn.innerHTML = '<i class="bi bi-toggle-off"></i>';
        btn.style.background = 'rgba(107, 114, 128, 0.1)';
        btn.style.color = 'var(--secondary-color)';
        showToast(`${userName} istifadəçisi deaktivləşdirildi`, 'warning');
    }
}

function deleteUser(userCard, userName) {
    if (confirm(`${userName} istifadəçisini silmək istədiyinizə əminsiniz?`)) {
        userCard.style.animation = 'fadeOut 0.3s ease-out';
        setTimeout(() => {
            userCard.remove();
            showToast(`${userName} istifadəçisi silindi`, 'success');
        }, 300);
    }
}


    


function downloadBackup(backupName) {
    showToast(`${backupName} yüklənir...`, 'info');
    // Simulate download
    setTimeout(() => {
        showToast('Backup uğurla yükləndi!', 'success');
    }, 2000);
}

function restoreBackup(backupName) {
    if (confirm(`${backupName} backup-ından bərpa etmək istədiyinizə əminsiniz?`)) {
        showToast('Sistem bərpa edilir...', 'warning');
        setTimeout(() => {
            showToast('Sistem uğurla bərpa edildi!', 'success');
        }, 5000);
    }
}

function retryBackup(backupName) {
    showToast(`${backupName} yenidən yaradılır...`, 'info');
    setTimeout(() => {
        showToast('Backup uğurla yaradıldı!', 'success');
    }, 3000);
}

function deleteBackup(backupItem, backupName) {
    if (confirm(`${backupName} backup-ını silmək istədiyinizə əminsiniz?`)) {
        backupItem.style.animation = 'fadeOut 0.3s ease-out';
        setTimeout(() => {
            backupItem.remove();
            showToast('Backup silindi', 'success');
        }, 300);
    }
}

function showScheduleModal() {
    showToast('Avtomatik backup təyin etmə pəncərəsi açılır...', 'info');
    // Here you would open a schedule modal
}

function showRestoreModal() {
    showToast('Bərpa etmə pəncərəsi açılır...', 'info');
    // Here you would open a restore modal
}