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

document.addEventListener("DOMContentLoaded", function () {
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

  const diskCanvas = document.getElementById("diskChart");
  if (diskCanvas) {
    const free = parseFloat(diskCanvas.getAttribute("data-free"));
    const total = parseFloat(diskCanvas.getAttribute("data-total"));
    const used = (total - free).toFixed(1);

    new Chart(diskCanvas, {
      type: "doughnut",
      data: {
        labels: ["Usado", "Livre"],
        datasets: [
          {
            data: [used, free],
            backgroundColor: ["#ef4444", "#10b981"],
            borderWidth: 0,
            hoverOffset: 4,
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        plugins: {
          legend: {
            position: "bottom",
            labels: { color: "#94a3b8", font: { family: "Inter" } },
          },
        },
      },
    });
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

  let url = `/api/search_tenor?q=${encodeURIComponent(currentTenorQuery)}`;
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
                    <form action="/download_gif" method="POST" style="margin: 0">
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

setTimeout(() => {
  const alerts = document.querySelectorAll(".flash-msg");
  alerts.forEach((alert) => {
    alert.style.transition = "opacity 0.5s ease";
    alert.style.opacity = "0";
    setTimeout(() => alert.remove(), 500);
  });
}, 5000);
