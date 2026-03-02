(function () {
  'use strict';

  const GROUP_SELECTOR = '#options-group';
  const ROW_SELECTOR = 'tr.form-row, tr.dynamic-options';

  function isActiveRow(row) {
    if (!row || row.classList.contains('empty-form')) {
      return false;
    }

    const deleteInput = row.querySelector('input[name$="-DELETE"]');
    return !(deleteInput && deleteInput.checked);
  }

  function getOrderInput(row) {
    return row.querySelector('input[name$="-order"]');
  }

  function getRows(group) {
    return Array.from(group.querySelectorAll(ROW_SELECTOR)).filter((row) => getOrderInput(row));
  }

  function updateOrder(group) {
    const rows = getRows(group).filter(isActiveRow);
    rows.forEach((row, index) => {
      const input = getOrderInput(row);
      if (input) {
        input.value = String(index + 1);
      }
    });
  }

  function clearDropState(group) {
    getRows(group).forEach((row) => {
      row.classList.remove('option-drop-before');
      row.classList.remove('option-drop-after');
      row.classList.remove('option-dragging');
    });
  }

  function addHandle(row) {
    if (row.querySelector('.option-drag-handle')) {
      return;
    }

    const textCell = row.querySelector('td.field-text');
    if (!textCell) {
      return;
    }

    const handle = document.createElement('span');
    handle.className = 'option-drag-handle';
    handle.title = 'Перетащите, чтобы изменить порядок';
    handle.textContent = '\u2630';

    textCell.prepend(handle);
  }

  function attachRowDnD(group, row) {
    if (row.dataset.sortableInit === '1') {
      return;
    }

    row.dataset.sortableInit = '1';
    row.setAttribute('draggable', 'true');
    row.classList.add('option-sortable-row');
    addHandle(row);

    row.addEventListener('dragstart', (event) => {
      if (!isActiveRow(row)) {
        event.preventDefault();
        return;
      }

      row.classList.add('option-dragging');
      event.dataTransfer.effectAllowed = 'move';
      row.dataset.dragging = '1';
    });

    row.addEventListener('dragend', () => {
      row.dataset.dragging = '0';
      clearDropState(group);
      updateOrder(group);
    });

    row.addEventListener('dragover', (event) => {
      const dragging = group.querySelector(`${ROW_SELECTOR}[data-dragging="1"]`);
      if (!dragging || dragging === row || !isActiveRow(row)) {
        return;
      }

      event.preventDefault();
      const rect = row.getBoundingClientRect();
      const isBefore = event.clientY < rect.top + rect.height / 2;
      row.classList.toggle('option-drop-before', isBefore);
      row.classList.toggle('option-drop-after', !isBefore);
    });

    row.addEventListener('dragleave', () => {
      row.classList.remove('option-drop-before');
      row.classList.remove('option-drop-after');
    });

    row.addEventListener('drop', (event) => {
      const dragging = group.querySelector(`${ROW_SELECTOR}[data-dragging="1"]`);
      if (!dragging || dragging === row || !isActiveRow(row)) {
        return;
      }

      event.preventDefault();
      const rect = row.getBoundingClientRect();
      const isBefore = event.clientY < rect.top + rect.height / 2;

      if (isBefore) {
        row.parentNode.insertBefore(dragging, row);
      } else {
        row.parentNode.insertBefore(dragging, row.nextSibling);
      }

      clearDropState(group);
      updateOrder(group);
    });

    const deleteInput = row.querySelector('input[name$="-DELETE"]');
    if (deleteInput) {
      deleteInput.addEventListener('change', () => updateOrder(group));
    }
  }

  function initGroup(group) {
    if (!group) {
      return;
    }

    getRows(group).forEach((row) => attachRowDnD(group, row));
    updateOrder(group);
  }

  function initAll() {
    document.querySelectorAll(GROUP_SELECTOR).forEach((group) => initGroup(group));
  }

  document.addEventListener('DOMContentLoaded', initAll);

  const observer = new MutationObserver(() => initAll());
  observer.observe(document.body, { childList: true, subtree: true });
})();
