/**
 * Password Toggle Functionality
 * 
 * This script handles toggling password visibility in the login form.
 * It waits for the DOM to be fully loaded, then adds event listeners to the toggle button.
 */
document.addEventListener('DOMContentLoaded', function() {
  const toggleButton = document.getElementById('togglePassword');
  const passwordField = document.getElementById('password');

  if (toggleButton && passwordField) {
    toggleButton.addEventListener('click', function() {
      // Toggle the password field type between 'password' and 'text'
      const type = passwordField.getAttribute('type') === 'password' ? 'text' : 'password';
      passwordField.setAttribute('type', type);
      
      // Toggle the icon between eye and eye-slash
      const icon = toggleButton.querySelector('i');
      if (icon) {
        if (type === 'password') {
          icon.classList.remove('fa-eye-slash');
          icon.classList.add('fa-eye');
        } else {
          icon.classList.remove('fa-eye');
          icon.classList.add('fa-eye-slash');
        }
      }
    });
  }
});