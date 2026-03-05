const projectStatusTable = document.querySelector("#project-status");
if (projectStatusTable && window.simpleDatatables && simpleDatatables.DataTable) {
  new simpleDatatables.DataTable(projectStatusTable, {
    perpage: 10,
    // tabIndex: 1,
    search: true,
    sort: true,
    // footer: true,
  });
}

// filter option
const listItems1 = document.querySelectorAll(".light-box");

listItems1.forEach(function (item) {
  const envelope_1 = item.querySelector(".filter-icon");
  const envelope_2 = item.querySelector(".filter-close");

  item.addEventListener("click", function () {
    if (envelope_1) {
      envelope_1.classList.toggle("show");
      if (envelope_2) {
        envelope_2.classList.toggle("hide");
      }
    }
    if (envelope_2) {
      if (envelope_1) {
        envelope_1.classList.toggle("hide");
      }
      envelope_2.classList.toggle("show");
    }
  });
});
