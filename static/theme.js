// Theme toggle — dark/light mode
(function(){
  var t = localStorage.getItem('theme') || 'dark';
  document.documentElement.setAttribute('data-theme', t);
})();

function setTheme(mode) {
  document.documentElement.setAttribute('data-theme', mode);
  localStorage.setItem('theme', mode);
  document.querySelectorAll('.mt-tbtn').forEach(function(b){
    b.classList.toggle('theme-btn-active', b.dataset.theme === mode);
  });
}
