// static/user_js/Modals.js

document.addEventListener('DOMContentLoaded', function () {
    
    // Aseguramos que devicesMap existe
    if (typeof devicesMap === 'undefined') {
        console.error("Error: devicesMap no está definido en el ámbito global.");
        return;
    }

    // 1. Control dinámico de apertura de modales de Bootstrap
    const modals = document.querySelectorAll('.close-order-modal-block');
    modals.forEach(function(modal) {
        modal.addEventListener('show.bs.modal', function () {
            const machineId = modal.getAttribute('data-machine-id')?.toString().trim() || "";
            const substationSelect = modal.querySelector('.substation-select');
            if (!substationSelect) return;

            const options = substationSelect.querySelectorAll('option');
            
            options.forEach(function(option) {
                // Mantener siempre visible la opción por defecto
                if (option.value === "") {
                    option.selected = true;
                    return;
                }

                const optionMachineId = option.getAttribute('data-substation-machine-id')?.toString().trim() || "";

                if (machineId === "" || optionMachineId === machineId) {
                    option.style.display = 'block';
                    option.disabled = false;
                } else {
                    option.style.display = 'none';
                    option.disabled = true;
                }
            });

            // Reseteo preventivo del dropdown de dispositivos
            resetDeviceSelect(modal);
        });
    });

    // 2. Delegación de eventos para poblar dispositivos al cambiar de subestación
    document.body.addEventListener('change', function (event) {
        if (event.target.classList.contains('substation-select')) {
            const substationSelect = event.target;
            const selectedSubstationId = substationSelect.value.toString();
            const currentForm = substationSelect.closest('form');
            
            if (!currentForm) return;

            const deviceSelect = currentForm.querySelector('.device-select');
            if (!deviceSelect) return;

            // Filtrado correcto de dispositivos
            const filteredDevices = devicesMap.filter(d => d.substationId.toString() === selectedSubstationId);
            populateDevices(deviceSelect, filteredDevices);
        }
    });

    // Funciones auxiliares para mantener el código limpio
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
});