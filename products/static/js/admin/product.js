


// =========================
// TOAST
// =========================
function reset() {
  const form = document.querySelector("productform");

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

      fetch("/delete-product/", {
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
// =========================
// MODAL + STEP WIZARD
// =========================
let steps, dots, modal;

document.addEventListener("DOMContentLoaded", () => {
  modal = document.getElementById("productModal");
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
  const modal = document.getElementById("productModal");

  modal.classList.add("active");

  // RESET FORM
  reset();

  // ✅ ADD REQUIRED BACK (for new product)
  document.querySelector('[name="ProductImage1"]')?.setAttribute("required", true);

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
// IMAGE PREVIEW
// =========================
function previewImg(input, imgId) {
  const file = input.files[0];
  const preview = document.getElementById(imgId);

  if (file && preview) {
    const reader = new FileReader();
    reader.onload = function (e) {
      preview.src = e.target.result;
      preview.classList.add("active");
    };
    reader.readAsDataURL(file);
  }
}

// =========================
// LESSON SYSTEM
// =========================
function addLesson() {
  const container = document.getElementById("lessonContainer");
  if (!container) return;

  const index = container.children.length;

  const html = `
    <div class="lesson-card">
      <div class="lesson-header">
        <span class="lesson-number">Lesson ${index + 1}</span>
        <span class="lesson-delete" onclick="removeLesson(this)">✕</span>
      </div>

      <input type="text" name="lesson_title_${index}" placeholder="Lesson Title">
      <input type="file" name="lesson_video_${index}">

      <label class="lesson-preview">
        <input type="checkbox" name="lesson_preview_${index}">
        Free Preview
      </label>
    </div>
  `;

  container.insertAdjacentHTML("beforeend", html);
}

function removeLesson(btn) {
  btn.closest(".lesson-card")?.remove();

  document.querySelectorAll(".lesson-card").forEach((card, i) => {
    card.querySelector(".lesson-number").innerText = `Lesson ${i + 1}`;
  });
}

function loadLessons(lessons) {
  const container = document.getElementById("lessonContainer");
  if (!container) return;

  container.innerHTML = "";

  lessons.forEach((lesson, index) => {
    const html = `
      <div class="lesson-card">
        <div class="lesson-header">
          <span class="lesson-number">Lesson ${index + 1}</span>
          <span class="lesson-delete" onclick="removeLesson(this)">✕</span>
        </div>

        <input type="text" name="lesson_title_${index}" value="${lesson.title || ''}">

        ${lesson.video ? `
          <div class="file-preview">
            <a href="${lesson.video}" target="_blank">${lesson.video.split('/').pop()}</a>
          </div>` : ""}

        <input type="file" name="lesson_video_${index}">

        <label class="lesson-preview">
          <input type="checkbox" name="lesson_preview_${index}" ${lesson.preview ? "checked" : ""}>
          Free Preview
        </label>
      </div>
    `;

    container.insertAdjacentHTML("beforeend", html);
  });
}

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

function setImage(id, src) {
  const img = document.getElementById(id);
  if (!img) return;

  if (src) {
    img.src = src;
    img.classList.add("active");
  } else {
    img.src = "";
    img.classList.remove("active");
  }
}

function openEditModalFromData(btn) {
  const modal = document.getElementById("productModal");

  // RESET FORM
document.getElementById("productForm")?.reset();
  document.getElementById("product_id").value = btn.dataset.id;

  // REMOVE REQUIRED FROM IMAGE (fix validation error)
  document.querySelector('[name="ProductImage1"]')?.removeAttribute("required");

  // RESET IMAGES
  ["img1", "img2", "img3"].forEach(id => setImage(id, ""));

  document.getElementById("currentFileBox").style.display = "none";
  document.getElementById("currentdemovideoBox").style.display = "none";

  modal?.classList.add("active");

  // BASIC
  document.querySelector('[name="ProductName"]').value = btn.dataset.name || "";
  document.querySelector('[name="ShortDescription"]').value = btn.dataset.desc || "";
  document.querySelector('[name="productprice"]').value = btn.dataset.price || "";
  document.querySelector('[name="discountprice"]').value = btn.dataset.discount || "";

  // ✅ CATEGORY FIX
  document.querySelectorAll('input[name="category"]').forEach(r => {
    r.checked = (r.value == btn.dataset.category);
  });

  // IMAGES
  setImage("img1", btn.dataset.img1);
  setImage("img2", btn.dataset.img2);
  setImage("img3", btn.dataset.img3);

  // DESCRIPTION
  const descEl = document.getElementById(`desc-${btn.dataset.id}`);
  const longdesc = descEl ? JSON.parse(descEl.textContent) : "";

  if (window.CKEDITOR && CKEDITOR.instances.editor) {
    CKEDITOR.instances.editor.setData(longdesc);
  }

  // TECH
  document.querySelector('[name="ProgrammingLanguage"]').value = btn.dataset.lang || "";
  document.querySelector('[name="Framework"]').value = btn.dataset.framework || "";
  document.querySelector('[name="Database"]').value = btn.dataset.db || "";
  document.querySelector('[name="Platform"]').value = btn.dataset.platform || "";
  document.querySelector('[name="SoftwareRequirements"]').value = btn.dataset.req || "";

  // FILE
  if (btn.dataset.file) {
    currentFileBox.style.display = "block";
    currentFileLink.href = btn.dataset.file;
    currentFileLink.textContent = btn.dataset.file.split('/').pop();
  }

  // VIDEO
  if (btn.dataset.video) {
    currentdemovideoBox.style.display = "block";
    currentdemovideoLink.href = btn.dataset.video;
    currentdemovideoLink.textContent = btn.dataset.video.split('/').pop();
  }

  document.getElementById("demoFolder").value = btn.dataset.demofolder || "";

  // EXTRA
  document.querySelector('[name="Features"]').value = btn.dataset.features || "";
  document.querySelector('[name="FilesIncluded"]').value = btn.dataset.filesincluded || "";

  // LESSONS
  const lessons = JSON.parse(btn.dataset.lessons || "[]");
  loadLessons(lessons);

  // RESET STEP
  step = 0;
  updateWizard();
}

// =========================
// CKEDITOR INIT
// =========================
document.addEventListener("DOMContentLoaded", () => {
  if (typeof CKEDITOR !== "undefined") {
    CKEDITOR.replace('editor', { versionCheck: false });
  }
});