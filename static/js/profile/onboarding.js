document.addEventListener('DOMContentLoaded', () => {
  const stepContent = document.querySelector('[data-step-content]');
  if (stepContent) {
    requestAnimationFrame(() => stepContent.classList.add('is-visible'));
  }

  const diagnosisField = document.querySelector('[data-diagnosis-field]');
  const healthStatusInputs = document.querySelectorAll('input[name="health_status"]');
  if (!diagnosisField || healthStatusInputs.length === 0) return;

  const diabetesStatuses = new Set([
    'type_1',
    'type_2',
    'prediabetes',
    'gestational',
  ]);
  const updateDiagnosisVisibility = () => {
    const selected = document.querySelector('input[name="health_status"]:checked');
    diagnosisField.hidden = !selected || !diabetesStatuses.has(selected.value);
  };

  healthStatusInputs.forEach((input) => {
    input.addEventListener('change', updateDiagnosisVisibility);
  });
  updateDiagnosisVisibility();
});
