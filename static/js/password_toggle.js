// Password Toggle Functionality
document.addEventListener('DOMContentLoaded', function() {
  const togglePassword = document.getElementById('togglePassword');
  const passwordInput = document.getElementById('password');
  
  if (togglePassword && passwordInput) {
    togglePassword.addEventListener('click', function() {
      const type = passwordInput.getAttribute('type') === 'password' ? 'text' : 'password';
      passwordInput.setAttribute('type', type);
      
      const icon = this.querySelector('i');
      if (icon) {
        icon.classList.toggle('fa-eye');
        icon.classList.toggle('fa-eye-slash');
      }
    });
  }
});
