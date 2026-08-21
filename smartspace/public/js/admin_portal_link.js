function redirectToAdminPortal(e) {
    e.preventDefault();
    e.stopPropagation();
    alert('Button clicked! Redirecting to admin portal...');
    window.location.href = '/admin-portal/analytics';
    return false;
}

$(document).on('click', '#admin-portal-link-btn', redirectToAdminPortal);

document.addEventListener('click', function(e) {
    var btn = e.target.closest('#admin-portal-link-btn');
    if (btn) {
        redirectToAdminPortal(e);
    }
}, true);
