document.addEventListener('DOMContentLoaded', () => {
  const modal = document.getElementById('food-entry-modal');
  const openButton = document.querySelector('[data-open-food-modal]');

  if (!(modal instanceof HTMLDialogElement) || !openButton) {
    return;
  }

  const closeButtons = modal.querySelectorAll('[data-close-food-modal]');

  openButton.addEventListener('click', () => {
    modal.showModal();
  });

  closeButtons.forEach((button) => {
    button.addEventListener('click', () => {
      modal.close();
    });
  });

  modal.addEventListener('click', (event) => {
    if (event.target === modal) {
      modal.close();
    }
  });

  modal.addEventListener('cancel', (event) => {
    event.preventDefault();
    modal.close();
  });

  document.addEventListener('keydown', (event) => {
    if (event.key === 'Escape' && modal.open) {
      event.preventDefault();
      modal.close();
    }
  }, true);

  modal.addEventListener('close', () => {
    openButton.focus();
  });

  if (modal.dataset.openOnLoad === 'true') {
    modal.showModal();
  }
});
