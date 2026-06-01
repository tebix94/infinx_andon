// static/user_js/Modals.js

// 1. Función para reinicializar eventos de modales al refrescar el DOM
function initModals() {
    const modals = document.querySelectorAll('.close-order-modal-block');
    modals.forEach(function(modal) {
        modal.removeEventListener('show.bs.modal', modalHandler);
        modal.addEventListener('show.bs.modal', modalHandler);
    });
}

// 2. Handler separado para la lógica del modal
function modalHandler() {
    const modal = this;
    const machineId = modal.getAttribute('data-machine-id')?.toString().trim() || "";
    const substationSelect = modal.querySelector('.substation-select');
    
    if (!substationSelect) return;

    substationSelect.querySelectorAll('option').forEach(function(option) {
        if (option.value === "") {
            option.selected = true;
            return;
        }
        const optionMachineId = option.getAttribute('data-substation-machine-id')?.toString().trim() || "";
        
        option.style.display = (machineId === "" || optionMachineId === machineId) ? 'block' : 'none';
        option.disabled = (machineId !== "" && optionMachineId !== machineId);
    });

    resetDeviceSelect(modal);
}

// 3. Funciones auxiliares
function resetDeviceSelect(modal) {
    const deviceSelect = modal.querySelector('.device-select');
    if (deviceSelect) {
        deviceSelect.innerHTML = '<option value="" disabled selected>-- Selecciona una subestación primero --</option>';
        deviceSelect.setAttribute('disabled', 'disabled');
    }
}

function populateDevices(deviceSelect, filteredDevices) {
    deviceSelect.innerHTML = '';
    const defaultOption = document.createElement('option');
    defaultOption.value = "";
    defaultOption.disabled = true;
    defaultOption.selected = true;

    if (filteredDevices.length > 0) {
        defaultOption.textContent = "-- Selecciona un dispositivo --";
        deviceSelect.appendChild(defaultOption);
        deviceSelect.removeAttribute('disabled');
        
        filteredDevices.forEach(device => {
            const option = document.createElement('option');
            option.value = device.id;
            option.textContent = device.name;
            deviceSelect.appendChild(option);
        });
    } else {
        defaultOption.textContent = "-- No hay dispositivos en esta subestación --";
        deviceSelect.appendChild(defaultOption);
        deviceSelect.setAttribute('disabled', 'disabled');
    }
}

// 4. Lógica de actualización asíncrona
async function refreshRequests() {
    // 1. Bloqueo de seguridad
    if (document.body.classList.contains('modal-open')) return;

    try {
        const controller = new AbortController();
        const timeoutId = setTimeout(() => controller.abort(), 8000); // Timeout de 8s

        const response = await fetch(REQUESTS_URL, {
            headers: { 'X-Requested-With': 'XMLHttpRequest' },
            signal: controller.signal
        });
        
        clearTimeout(timeoutId);

        if (!response.ok) throw new Error(`HTTP error! status: ${response.status}`);
        
        const text = await response.text();
        const parser = new DOMParser();
        const doc = parser.parseFromString(text, 'text/html');
        const newContainer = doc.getElementById('requests-container');
        const currentContainer = document.getElementById('requests-container');

        if (newContainer && currentContainer) {
            currentContainer.innerHTML = newContainer.innerHTML;
            initModals(); 
        }
    } catch (error) {
        // Ignoramos errores de aborto, reportamos el resto
        if (error.name !== 'AbortError') {
            console.error('Error al actualizar:', error);
        }
    }
}

// 5. Inicialización
document.addEventListener('DOMContentLoaded', function () {
    if (typeof devicesMap === 'undefined') {
        console.error("Error: devicesMap no está definido.");
        return;
    }

    initModals();

    document.body.addEventListener('change', function (event) {
        if (event.target.classList.contains('substation-select')) {
            const substationSelect = event.target;
            const selectedSubstationId = substationSelect.value.toString();
            const currentForm = substationSelect.closest('form');
            if (!currentForm) return;

            const deviceSelect = currentForm.querySelector('.device-select');
            const filteredDevices = devicesMap.filter(d => d.substationId.toString() === selectedSubstationId);
            populateDevices(deviceSelect, filteredDevices);
        }
    });

    // Refrescar cada 10 segundos
    setInterval(refreshRequests, 5000);
});