// --- SISTEMA DE NOTIFICAÇÕES (TOAST) ---
function showToast(message, type = "info") {
  const container = document.getElementById("toast-container");
  const toast = document.createElement("div");
  toast.className = `toast ${type}`;
  toast.innerHTML = `<span>${message}</span> <span style="cursor:pointer; margin-left:10px;" onclick="this.parentElement.remove()">&times;</span>`;

  container.appendChild(toast);

  // Remove automaticamente após 4 segundos
  setTimeout(() => {
    toast.style.opacity = "0";
    setTimeout(() => toast.remove(), 300);
  }, 4000);
}

// --- FUNÇÕES GENÉRICAS DE AÇÃO ---
function submitForm(event, url, formElement = null, shouldReload = false) {
  if (event) event.preventDefault();
  const form = formElement || event.target;
  const formData = new FormData(form);

  fetch(url, {
    method: "POST",
    body: formData,
  })
    .then((response) => {
      if (response.redirected) {
        window.location.href = response.url;
        return;
      }
      return response.json().catch(() => ({})); // Tenta ler JSON, se falhar retorna vazio
    })
    .then((data) => {
      // Se a resposta for JSON com mensagem
      if (data && data.message) {
        showToast(data.message, data.status || "success");
        if (shouldReload && data.status === "success") {
          setTimeout(() => window.location.reload(), 1000);
        }
      } else {
        // Fallback se não houver JSON (ex: reload da página)
        // showToast('Ação realizada com sucesso!', 'success');
        // Recarrega para atualizar dados se necessário
        setTimeout(() => window.location.reload(), 500);
      }
    })
    .catch((err) => showToast("Erro ao processar ação: " + err, "error"));
}

function uploadGif(event) {
  event.preventDefault();
  const form = event.target;
  const formData = new FormData(form);
  const fileInput = form.querySelector('input[type="file"]');

  if (fileInput.files.length === 0) return;

  const progressBarContainer = document.getElementById(
    "upload-progress-container",
  );
  const progressBarFill = document.getElementById("upload-progress-fill");
  const progressText = document.getElementById("upload-progress-text");
  const submitBtn = form.querySelector('button[type="submit"]');

  progressBarContainer.style.display = "block";
  progressBarFill.style.width = "0%";
  progressText.innerText = "0%";
  submitBtn.disabled = true;
  submitBtn.style.opacity = "0.5";

  const xhr = new XMLHttpRequest();
  xhr.open("POST", "/upload_gif", true);

  xhr.upload.onprogress = function (e) {
    if (e.lengthComputable) {
      const percentComplete = (e.loaded / e.total) * 100;
      progressBarFill.style.width = percentComplete + "%";
      progressText.innerText = Math.round(percentComplete) + "%";
    }
  };

  xhr.onload = function () {
    submitBtn.disabled = false;
    submitBtn.style.opacity = "1";

    if (xhr.status === 200) {
      try {
        const data = JSON.parse(xhr.responseText);
        showToast(data.message, data.status);
        if (data.status === "success") {
          setTimeout(() => window.location.reload(), 1000);
        }
      } catch (e) {
        showToast("Erro ao processar resposta.", "error");
      }
    } else {
      showToast("Erro no upload: " + xhr.statusText, "error");
    }
    setTimeout(() => {
      progressBarContainer.style.display = "none";
    }, 3000);
  };

  xhr.send(formData);
}

// --- MODAL DE CONFIRMAÇÃO PERSONALIZADA ---
let currentConfirmCallback = null;

function showConfirmModal(title, message, callback, expectedInput = null) {
  document.getElementById("confirmTitle").innerText = title;
  document.getElementById("confirmMessage").innerText = message;
  currentConfirmCallback = callback;

  const inputContainer = document.getElementById("confirmInputContainer");
  const inputField = document.getElementById("confirmInput");
  const confirmBtn = document.getElementById("confirmBtnAction");

  // Configura modal para input de texto (ex: digitar "SIM") ou apenas botão
  if (expectedInput) {
    inputContainer.style.display = "block";
    inputField.value = "";
    inputField.placeholder = `Digite '${expectedInput}' para confirmar`;
    confirmBtn.disabled = true;
    confirmBtn.style.opacity = "0.5";

    // Validação em tempo real
    inputField.onkeyup = function () {
      if (this.value.toUpperCase() === expectedInput) {
        confirmBtn.disabled = false;
        confirmBtn.style.opacity = "1";
      } else {
        confirmBtn.disabled = true;
        confirmBtn.style.opacity = "0.5";
      }
    };
    setTimeout(() => inputField.focus(), 100);
  } else {
    inputContainer.style.display = "none";
    confirmBtn.disabled = false;
    confirmBtn.style.opacity = "1";
    inputField.onkeyup = null;
  }

  document.getElementById("confirmModal").style.display = "block";
}

function closeConfirmModal() {
  document.getElementById("confirmModal").style.display = "none";
  currentConfirmCallback = null;
}

function executeConfirm() {
  if (currentConfirmCallback) currentConfirmCallback();
  closeConfirmModal();
}

// --- AÇÕES DO SISTEMA ---

function confirmAction(url, message) {
  showConfirmModal("Atenção", message, () => {
    fetch(url)
      .then((response) => {
        if (response.redirected) window.location.href = response.url;
        else showToast("Comando enviado.", "success");
      })
      .catch((err) => showToast("Erro: " + err, "error"));
  });
}

function confirmShutdown(url) {
  showConfirmModal(
    "PERIGO",
    "Isso desligará o Raspberry Pi. Digite SIM para continuar:",
    () => {
      fetch(url)
        .then((response) => {
          if (response.redirected) window.location.href = response.url;
          else showToast("Desligando sistema...", "success");
        })
        .catch((err) => showToast("Erro: " + err, "error"));
    },
    "SIM", // Exige digitar SIM
  );
}

function removeCoin(symbol) {
  showConfirmModal("Remover Moeda", "Deseja remover " + symbol + "?", () => {
    fetch("/remover/" + symbol)
      .then(() => {
        showToast(symbol + " removido.", "success");
        const el = document.querySelector(`.chip[data-symbol="${symbol}"]`);
        if (el) el.remove();
      })
      .catch((err) => showToast("Erro ao remover.", "error"));
  });
}

function deleteGif(filename) {
  showConfirmModal("Excluir GIF", "Excluir " + filename + "?", () => {
    fetch("/delete_gif/" + filename)
      .then(() => {
        showToast("GIF excluído.", "success");
        setTimeout(() => window.location.reload(), 500);
      })
      .catch((err) => showToast("Erro ao excluir.", "error"));
  });
}

function toggleWifiPassword() {
  const input = document.getElementById("wifi-psk");
  const icon = document.getElementById("toggle-psk-btn");
  if (input.type === "password") {
    input.type = "text";
    icon.classList.remove("fa-eye");
    icon.classList.add("fa-eye-slash");
  } else {
    input.type = "password";
    icon.classList.remove("fa-eye-slash");
    icon.classList.add("fa-eye");
  }
}

const modal = document.getElementById("logModal");
const logOutput = document.getElementById("log-output");

function openLogs() {
  modal.style.display = "block";
  fetchLogs();
}

function closeModal() {
  modal.style.display = "none";
}

function fetchLogs() {
  logOutput.textContent = "Carregando logs...";
  fetch("/logs")
    .then((response) => response.text())
    .then((data) => {
      logOutput.textContent = data;
      logOutput.scrollTop = logOutput.scrollHeight; // Rola para o final automaticamente
    })
    .catch((err) => {
      logOutput.textContent = "Erro ao buscar logs: " + err;
    });
}

// Fecha ao clicar fora da modal
window.onclick = function (event) {
  if (event.target == modal) {
    closeModal();
  }
};

// Fecha com a tecla ESC
document.addEventListener("keydown", function (event) {
  if (event.key === "Escape") {
    closeModal();
  }
});

function openTab(evt, tabName) {
  localStorage.setItem("activeTab", tabName);

  var i, tabcontent, tablinks;
  tabcontent = document.getElementsByClassName("tab-content");
  for (i = 0; i < tabcontent.length; i++) {
    tabcontent[i].style.display = "none";
    tabcontent[i].classList.remove("active");
  }
  tablinks = document.getElementsByClassName("tab-btn");
  for (i = 0; i < tablinks.length; i++) {
    tablinks[i].className = tablinks[i].className.replace(" active", "");
  }
  document.getElementById(tabName).style.display = "flex";
  document.getElementById(tabName).classList.add("active");
  evt.currentTarget.className += " active";
}

const coinList = document.getElementById("coin-list");
if (coinList) {
  if (typeof Sortable === "undefined") {
    console.error(
      "ERRO: SortableJS não carregou. Verifique se o Raspberry Pi tem acesso à internet para baixar a biblioteca.",
    );
  } else {
    new Sortable(coinList, {
      animation: 150,
      ghostClass: "sortable-ghost",
      onEnd: function () {
        const newOrder = Array.from(coinList.children).map((chip) =>
          chip.getAttribute("data-symbol"),
        );

        fetch("/reordenar_moedas", {
          method: "POST",
          headers: {
            "Content-Type": "application/json",
          },
          body: JSON.stringify({ moedas: newOrder }),
        })
          .then((response) => response.json())
          .catch((error) => console.error("Erro ao salvar ordem:", error));
      },
    });
  }
}

function savePlaylist(event) {
  event.preventDefault();
  const list = document.getElementById("playlist-list");
  const items = list.querySelectorAll(".playlist-item");
  const pages = [];

  items.forEach((item) => {
    const id = item.getAttribute("data-id");
    const enabled = item.querySelector('input[type="checkbox"]').checked;
    const tempo = item.querySelector('input[type="number"]').value;
    pages.push({ id: id, enabled: enabled, tempo: tempo });
  });

  fetch("/salvar_playlist", {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ pages: pages }),
  })
    .then((r) => r.json())
    .then((data) => showToast(data.message, data.status))
    .catch((e) => showToast("Erro: " + e, "error"));
}

function getCurrentLocation() {
  if (!navigator.geolocation) {
    showToast("Geolocalização não suportada.", "error");
    return;
  }

  const btn = document.getElementById("btn-location");
  const icon = btn.querySelector("i");
  const originalClass = icon.className;

  icon.className = "fa-solid fa-spinner fa-spin";
  btn.disabled = true;

  navigator.geolocation.getCurrentPosition(
    (position) => {
      const lat = position.coords.latitude;
      const lon = position.coords.longitude;

      // Usa Nominatim (OpenStreetMap) para obter a cidade a partir das coordenadas
      fetch(
        `https://nominatim.openstreetmap.org/reverse?format=json&lat=${lat}&lon=${lon}`,
      )
        .then((r) => r.json())
        .then((data) => {
          const addr = data.address;
          const city =
            addr.city ||
            addr.town ||
            addr.village ||
            addr.municipality ||
            addr.county;
          if (city) {
            document.querySelector('input[name="cidade"]').value = city;
            showToast(`Localização: ${city}`, "success");
          } else showToast("Cidade não encontrada.", "warning");
        })
        .catch(() => showToast("Erro ao buscar endereço.", "error"))
        .finally(() => {
          icon.className = originalClass;
          btn.disabled = false;
        });
    },
    (err) => {
      // Fallback: Tenta obter localização via IP (útil para HTTP onde GPS é bloqueado)
      fetch("http://ip-api.com/json")
        .then((r) => r.json())
        .then((data) => {
          if (data && data.city) {
            document.querySelector('input[name="cidade"]').value = data.city;
            showToast(`Localização (IP): ${data.city}`, "warning");
          } else showToast("Erro GPS: " + err.message, "error");
        })
        .catch(() => showToast("Erro GPS: " + err.message, "error"))
        .finally(() => {
          icon.className = originalClass;
          btn.disabled = false;
        });
    },
  );
}

document.addEventListener("DOMContentLoaded", function () {
  // Atualiza status do sistema (CPU/RAM) a cada 5s
  // (Movido para o topo para garantir execução mesmo se houver erro no Chart.js)
  setInterval(() => {
    fetch("/api/status")
      .then((r) => r.json())
      .then((data) => {
        const cpu = document.getElementById("sys-cpu");
        const ram = document.getElementById("sys-ram");
        const load = document.getElementById("sys-load");
        const uptime = document.getElementById("sys-uptime");
        const wifi = document.getElementById("sys-wifi");
        const ip = document.getElementById("sys-ip");

        if (cpu) cpu.textContent = data.cpu_temp;
        if (ram) ram.textContent = data.ram_usage;
        if (load) load.textContent = data.cpu_load;
        if (uptime) uptime.textContent = data.uptime;
        if (wifi) wifi.textContent = data.wifi_ssid;
        if (ip) ip.textContent = data.ip;
      })
      .catch(() => {});
  }, 5000);

  const activeTab = localStorage.getItem("activeTab");
  if (activeTab) {
    const tabLinks = document.getElementsByClassName("tab-btn");
    for (let i = 0; i < tabLinks.length; i++) {
      if (tabLinks[i].getAttribute("onclick").includes(activeTab)) {
        tabLinks[i].click();
        break;
      }
    }
  }

  const pingEl = document.getElementById("net-ping");
  const dlEl = document.getElementById("net-download");

  if (pingEl && dlEl) {
    fetch("/measure_speed")
      .then((response) => response.json())
      .then((data) => {
        pingEl.textContent = data.ping;
        dlEl.textContent = data.download;
      })
      .catch((err) => {
        pingEl.textContent = "Err";
        dlEl.textContent = "Err";
      });
  }

  const playlistList = document.getElementById("playlist-list");
  if (playlistList && typeof Sortable !== "undefined") {
    new Sortable(playlistList, {
      animation: 150,
      ghostClass: "sortable-ghost",
      handle: ".handle", // Arrastar pelo ícone
    });
  }
});

let currentTenorPos = "";
let currentTenorQuery = "";

function handleEnter(e) {
  if (e.key === "Enter") searchTenor();
}

function searchTenor() {
  const query = document.getElementById("tenor-query").value;

  if (!query) return;

  currentTenorQuery = query;
  currentTenorPos = "";

  const list = document.getElementById("library-list");
  list.innerHTML = ""; // Limpa lista

  fetchTenorData();
}

function loadMoreTenor() {
  fetchTenorData();
}

function fetchTenorData() {
  const list = document.getElementById("library-list");
  const loading = document.getElementById("tenor-loading");
  const loadMoreBtn = document.getElementById("load-more-container");

  loading.style.display = "block";
  loadMoreBtn.style.display = "none";

  let url = `/search_gif?q=${encodeURIComponent(currentTenorQuery)}`;
  if (currentTenorPos) {
    url += `&pos=${currentTenorPos}`;
  }

  fetch(url)
    .then((response) => response.json())
    .then((data) => {
      if (data.results.length === 0 && !currentTenorPos) {
        list.innerHTML =
          '<div style="grid-column: 1/-1; text-align:center; padding:10px; color:#aaa;">Nenhum resultado encontrado.</div>';
      }

      currentTenorPos = data.next;

      data.results.forEach((item) => {
        const html = `
                <div class="gif-card">
                    <img src="${item.url}" loading="lazy" />
                    <div class="gif-card-actions">
                    <form onsubmit="submitForm(event, '/download_gif', null, true)" style="margin: 0">
                        <input type="hidden" name="url" value="${item.url}" />
                        <input type="hidden" name="name" value="${item.name.replace(/[^a-zA-Z0-9]/g, "_")}" />
                        <button type="submit" class="btn btn-primary" style="padding: 4px 8px; font-size: 0.8rem; width: auto; height: auto;"><i class="fa-solid fa-download"></i></button>
                    </form>
                    </div>
                </div>`;
        list.innerHTML += html;
      });
      loading.style.display = "none";

      if (currentTenorPos) {
        loadMoreBtn.style.display = "block";
      }
    });
}
