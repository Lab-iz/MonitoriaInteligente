function hydrateCharts() {
  document.querySelectorAll("canvas[data-chart]").forEach((canvas) => {
    const rawValues = canvas.dataset.chartValues;
    if (!rawValues) return;

    const values = JSON.parse(rawValues);
    const labels = values.map((item) => item.label);
    const dataset = values.map((item) => item.value);

    new Chart(canvas, {
      type: canvas.dataset.chart || "bar",
      data: {
        labels,
        datasets: [
          {
            label: canvas.dataset.chartLabel || "Valor",
            data: dataset,
            borderRadius: 10,
            backgroundColor: ["#17d7ff", "#ff5c94", "#7c8cff", "#4ef0b2", "#9c7bff", "#ffc857"],
          },
        ],
      },
      options: {
        responsive: true,
        maintainAspectRatio: false,
        scales: {
          y: {
            beginAtZero: true,
            ticks: { color: "rgba(232,241,255,0.72)" },
            grid: { color: "rgba(180,210,255,0.10)" },
          },
          x: {
            ticks: { color: "rgba(232,241,255,0.72)" },
            grid: { display: false },
          },
        },
        plugins: {
          legend: { display: false },
        },
      },
    });
  });
}

function hydrateTopicFilter() {
  const forms = document.querySelectorAll("[data-ticket-form]");
  forms.forEach((form) => {
    const courseSelect = form.querySelector("#course_id");
    const disciplineSelect = form.querySelector("#discipline_id");
    const topicSelect = form.querySelector("#topic_id");
    const classGroupSelect = form.querySelector("#class_group_id");
    if (!courseSelect || !disciplineSelect || !topicSelect) return;

    const syncTopics = () => {
      const selectedDiscipline = disciplineSelect.value;
      let firstVisible = null;
      Array.from(topicSelect.options).forEach((option) => {
        const visible = option.dataset.discipline === selectedDiscipline;
        option.hidden = !visible;
        if (visible && !firstVisible) firstVisible = option.value;
      });
      if (firstVisible) topicSelect.value = firstVisible;
    };

    const syncDisciplines = () => {
      const selectedCourse = courseSelect.value;
      let firstVisible = null;
      Array.from(disciplineSelect.options).forEach((option) => {
        const visible = option.dataset.course === selectedCourse;
        option.hidden = !visible;
        if (visible && !firstVisible) firstVisible = option.value;
      });
      if (firstVisible) disciplineSelect.value = firstVisible;
      syncTopics();
    };

    const syncClassGroups = () => {
      if (!classGroupSelect) return;

      const selectedCourse = courseSelect.value;
      const placeholder = classGroupSelect.options[0];
      let firstVisible = placeholder ? placeholder.value : "";

      Array.from(classGroupSelect.options).forEach((option, index) => {
        if (index === 0) {
          option.hidden = false;
          return;
        }
        const visible = option.dataset.course === selectedCourse;
        option.hidden = !visible;
        if (visible && !firstVisible) firstVisible = option.value;
      });

      if (classGroupSelect.selectedOptions[0]?.hidden) {
        classGroupSelect.value = placeholder ? placeholder.value : firstVisible;
      }
    };

    courseSelect.addEventListener("change", () => {
      syncDisciplines();
      syncClassGroups();
    });
    disciplineSelect.addEventListener("change", syncTopics);

    syncDisciplines();
    syncClassGroups();
  });
}

function hydrateRoleFields() {
  document.querySelectorAll("[data-role-form]").forEach((form) => {
    const roleSelect = form.querySelector("[data-role-select]");
    const roleFields = form.querySelectorAll("[data-role-field]");
    if (!roleSelect || !roleFields.length) return;

    const syncRoleFields = () => {
      const selectedRole = roleSelect.value;
      roleFields.forEach((field) => {
        const visible = field.dataset.roleField.split(" ").includes(selectedRole);
        field.hidden = !visible;
        field.querySelectorAll("input, select, textarea").forEach((input) => {
          input.disabled = !visible;
          if (input.name === "phone") {
            input.required = visible && selectedRole === "monitor";
          }
        });
      });
    };

    roleSelect.addEventListener("change", syncRoleFields);
    syncRoleFields();
  });
}

document.addEventListener("DOMContentLoaded", () => {
  hydrateCharts();
  hydrateTopicFilter();
  hydrateRoleFields();
});
