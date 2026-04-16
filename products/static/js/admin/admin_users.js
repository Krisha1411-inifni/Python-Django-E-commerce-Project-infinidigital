


// =========================
// TOAST
// =========================
function reset() {
  const form = document.querySelector("#userform");

  // =========================
  // 1. RESET FORM FIELDS
  // =========================
  if (form) form.reset();

  // =========================
  // 2. RESET HIDDEN ID (IMPORTANT)
  // =========================
  const idField = document.getElementById("product_id");
  if (idField) idField.value = "";

  // =========================
  // 3. RESET CATEGORY (radio)
  // =========================
  document.querySelectorAll('input[name="category"]').forEach(r => r.checked = false);

  // =========================
  // 4. RESET IMAGE PREVIEWS
  // =========================
  ["img1", "img2", "img3"].forEach(id => {
    const img = document.getElementById(id);
    if (img) {
      img.src = "";
      img.classList.remove("active");
    }
  });

  // =========================
  // 5. CLEAR LESSONS (CRITICAL)
  // =========================
  const lessonContainer = document.getElementById("lessonContainer");
  if (lessonContainer) lessonContainer.innerHTML = "";

  // =========================
  // 6. HIDE FILE PREVIEW BOXES
  // =========================
  const fileBox = document.getElementById("currentFileBox");
  const videoBox = document.getElementById("currentdemovideoBox");

  if (fileBox) fileBox.style.display = "none";
  if (videoBox) videoBox.style.display = "none";

  // =========================
  // 7. RESET FILE LINKS
  // =========================
  const fileLink = document.getElementById("currentFileLink");
  const videoLink = document.getElementById("currentdemovideoLink");

  if (fileLink) {
    fileLink.href = "#";
    fileLink.textContent = "";
  }

  if (videoLink) {
    videoLink.href = "#";
    videoLink.textContent = "";
  }

  // =========================
  // 8. RESET CKEDITOR
  // =========================
  if (window.CKEDITOR && CKEDITOR.instances.editor) {
    CKEDITOR.instances.editor.setData("");
  }

  // =========================
  // 9. RESTORE REQUIRED (ADD MODE)
  // =========================
  document.querySelector('[name="ProductImage1"]')?.setAttribute("required", true);

  // =========================
  // 10. RESET STEP WIZARD
  // =========================
  step = 0;
  updateWizard();

  console.log("✅ FULL RESET DONE");
}

function showToast(message, type = "success") {
  const toast = document.getElementById("toast");
  if (!toast) return;

  toast.textContent = message;
  toast.className = "toast show " + type;

  setTimeout(() => {
    toast.classList.remove("show");
  }, 3000);
}

// =========================
// CSRF TOKEN
// =========================
function getCSRFToken() {
  return document.cookie
    .split('; ')
    .find(row => row.startsWith('csrftoken'))
    ?.split('=')[1];
}

// =========================
// DELETE PRODUCT
// =========================
document.addEventListener("DOMContentLoaded", () => {
  document.querySelectorAll(".delete-btn").forEach(btn => {
    btn.addEventListener("click", function (e) {
      e.preventDefault();

      const id = this.dataset.id;
      const name = this.dataset.name;

      if (!confirm(`Delete "${name}"?`)) return;

      this.disabled = true; // prevent double click

      fetch("/delete-user/", {
        method: "POST",
        headers: {
          "Content-Type": "application/x-www-form-urlencoded",
          "X-CSRFToken": getCSRFToken()
        },
        body: `id=${encodeURIComponent(id)}`
      })
      .then(res => res.json())
      .then(data => {
        if (data.success) {
          showToast(`${data.name} deleted successfully`, "success");
          this.closest("tr")?.remove();
        } else {
          showToast(data.error || "Delete failed", "error");
          this.disabled = false;
        }
      })
      .catch(() => {
        showToast("Something went wrong", "error");
        this.disabled = false;
      });
    });
  });
});

document.getElementById("userform").addEventListener("submit", function(e) {
    e.preventDefault();

    const form = this;
    const formData = new FormData(form);

    fetch(form.action, {
        method: "POST",
        headers: {
            "X-CSRFToken": getCSRFToken()
        },
        body: formData
    })
    .then(res => {
        console.log("STATUS:", res.status);
        return res.json();
    })
    .then(data => {
        console.log("DATA:", data);

        if (data.success) {
            showToast(data.message, "success");
            closeModal();
            setTimeout(() => location.reload(), 1000);
        } else {
            showToast(data.error || "Error", "error");
        }
    })
    .catch(err => {
        console.error("FETCH ERROR:", err);
        showToast("Server Error", "error");
    });
});
// =========================
// MODAL + STEP WIZARD
// =========================
let steps, dots, modal;

document.addEventListener("DOMContentLoaded", () => {
  modal = document.getElementById("userModal");
  steps = document.querySelectorAll(".step");
  dots = document.querySelectorAll(".dot");

  updateWizard();
});

function updateWizard() {
  if (!steps) return;

  steps.forEach((s, i) => {
    s.classList.toggle("active", i === step);
    dots[i]?.classList.toggle("active", i <= step);
  });

  const progress = steps.length > 1
    ? (step / (steps.length - 1)) * 100
    : 0;

  const bar = document.getElementById("progressBar");
  if (bar) bar.style.width = progress + "%";

  const prevBtn = document.querySelector(".nav-btn.prev");
  const nextBtn = document.querySelector(".nav-btn.next");
  const submitBtn = document.querySelector(".submit-btn");

  if (prevBtn) prevBtn.disabled = step === 0;

  if (step === steps.length - 1) {
    if (nextBtn) nextBtn.style.display = "none";
    if (submitBtn) submitBtn.style.display = "inline-flex";
  } else {
    if (nextBtn) nextBtn.style.display = "flex";
    if (submitBtn) submitBtn.style.display = "none";
  }
}

window.nextStep = function () {
  const currentStep = document.querySelectorAll(".step")[step];
  const inputs = currentStep.querySelectorAll("input, textarea, select");

  for (let input of inputs) {
    if (!input.checkValidity()) {
      input.reportValidity();
      return;
    }
  }

  if (step < steps.length - 1) {
    step++;
    updateWizard();
  }
};

window.prevStep = function () {
  if (step > 0) {
    step--;
    updateWizard();
  }
};

window.openModal = function () {
  const modal = document.getElementById("userModal");

  modal.classList.add("active");

  // RESET FORM
  reset();

  // ✅ ADD REQUIRED BACK (for new product)

  step = 0;
  updateWizard();
};

window.closeModal = function () {
  modal?.classList.remove("active");
};

window.addEventListener("click", function (e) {
  if (e.target === modal) {
    modal.classList.remove("active");
  }
});

// =========================
// EDIT PRODUCT
// =========================
document.addEventListener("DOMContentLoaded", function () {
  document.querySelectorAll(".edit-btn").forEach(btn => {
    btn.addEventListener("click", function () {
      openEditModalFromData(this);
    });
  });
});

function openEditModalFromData(btn) {
  const modal = document.getElementById("userModal");

  // RESET FORM
document.getElementById("userform")?.reset();
  document.getElementById("user_id").value = btn.dataset.id;

  modal?.classList.add("active");

  // BASIC
  document.querySelector('[name="username"]').value = btn.dataset.name || "";
  document.querySelector('[name="email"]').value = btn.dataset.email || "";

  // RESET STEP
  step = 0;
  updateWizard();
}
