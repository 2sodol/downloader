const form = document.querySelector("#download-form");
const urlInput = document.querySelector("#url");
const message = document.querySelector("#message");
const metadataButton = document.querySelector("#metadata-button");
const metadataPanel = document.querySelector("#metadata");
const jobsPanel = document.querySelector("#jobs");
const healthPanel = document.querySelector("#health");
const refreshButton = document.querySelector("#refresh-button");
const sampleButton = document.querySelector("#sample-button");

let pollTimer = null;
const sampleUrl = "https://www.youtube.com/watch?v=jNQXAC9IVRw";

function escapeHtml(value) {
  const text = String(value ?? "");
  return text.replace(/[&<>"']/g, (char) => ({
    "&": "&amp;",
    "<": "&lt;",
    ">": "&gt;",
    '"': "&quot;",
    "'": "&#39;",
  }[char]));
}

function setMessage(text, isError = false) {
  message.textContent = text;
  message.style.color = isError ? "#b3261e" : "#62676d";
}

async function requestJson(url, options = {}) {
  const response = await fetch(url, {
    headers: { "Content-Type": "application/json" },
    ...options,
  });
  const data = await response.json();
  if (!response.ok) {
    throw new Error(data.detail || "요청을 처리하지 못했습니다.");
  }
  return data;
}

function secondsToText(value) {
  if (!value) return "알 수 없음";
  const minutes = Math.floor(value / 60);
  const seconds = value % 60;
  return `${minutes}분 ${seconds}초`;
}

function renderMetadata(data) {
  const thumbnail = data.thumbnail
    ? `<img src="${escapeHtml(data.thumbnail)}" alt="">`
    : `<div class="thumbnail-placeholder"></div>`;
  metadataPanel.innerHTML = `
    <div class="metadata-content">
      ${thumbnail}
      <div>
        <h2>${escapeHtml(data.title || "제목 없음")}</h2>
        <p class="meta-line">업로더: ${escapeHtml(data.uploader || "알 수 없음")}</p>
        <p class="meta-line">길이: ${secondsToText(data.duration)}</p>
        <p class="meta-line">포맷 수: ${(data.formats || []).length}</p>
        ${data.is_playlist ? `<p class="meta-line">플레이리스트 항목: ${data.entry_count || 0}</p>` : ""}
      </div>
    </div>
  `;
  metadataPanel.classList.remove("hidden");
}

function statusClass(status) {
  if (status === "failed") return "status failed";
  if (status === "queued") return "status queued";
  return "status";
}

function renderJob(job) {
  const title = escapeHtml(job.title || job.source_url);
  const sourceUrl = escapeHtml(job.source_url);
  const errorText = escapeHtml(job.error_message || "");
  const qualityText = job.quality === "best" ? "최고화질" : "호환성 우선 MP4";
  const progress = Math.max(0, Math.min(100, Number(job.progress || 0)));
  const fileLink = job.status === "completed" && job.file_ready
    ? `<a href="/downloads/${job.id}/file">파일 받기</a>`
    : "";
  const error = errorText ? `<p class="message">${errorText}</p>` : "";
  return `
    <article class="job">
      <div class="job-head">
        <div>
          <h3>${title}</h3>
          <p class="meta-line">${sourceUrl}</p>
          <p class="meta-line">품질: ${qualityText}</p>
        </div>
        <span class="${statusClass(job.status)}">${escapeHtml(job.status)}</span>
      </div>
      <div class="progress" aria-label="진행률 ${progress}%"><span style="width: ${progress}%"></span></div>
      <p class="meta-line">${progress.toFixed(1)}%</p>
      ${error}
      ${fileLink}
    </article>
  `;
}

async function loadHealth() {
  try {
    const data = await requestJson("/health");
    healthPanel.textContent = data.ffmpeg_available ? "ffmpeg 사용 가능" : "ffmpeg 필요";
  } catch (error) {
    healthPanel.textContent = "환경 확인 실패";
  }
}

async function loadJobs() {
  const data = await requestJson("/downloads");
  jobsPanel.innerHTML = data.jobs.length
    ? data.jobs.map(renderJob).join("")
    : `<p class="meta-line">현재 서버 세션에 작업이 없습니다.</p>`;

  const hasActiveJob = data.jobs.some((job) => job.status === "queued" || job.status === "running");
  if (hasActiveJob && !pollTimer) {
    pollTimer = window.setInterval(loadJobs, 1500);
  }
  if (!hasActiveJob && pollTimer) {
    window.clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function previewMetadata() {
  metadataButton.disabled = true;
  setMessage("메타데이터를 조회하는 중입니다.");
  try {
    const data = await requestJson("/metadata", {
      method: "POST",
      body: JSON.stringify({ url: urlInput.value }),
    });
    renderMetadata(data);
    setMessage("미리보기를 불러왔습니다.");
  } catch (error) {
    setMessage(error.message, true);
  } finally {
    metadataButton.disabled = false;
  }
}

async function createDownload(event) {
  event.preventDefault();
  const quality = new FormData(form).get("quality") || "compatible";
  form.querySelector('button[type="submit"]').disabled = true;
  setMessage("다운로드 작업을 생성하는 중입니다.");
  try {
    const data = await requestJson("/downloads", {
      method: "POST",
      body: JSON.stringify({ url: urlInput.value, quality }),
    });
    setMessage(data.duplicate ? "이미 실행 중인 작업입니다." : "다운로드 작업을 시작했습니다.");
    await loadJobs();
  } catch (error) {
    setMessage(error.message, true);
  } finally {
    form.querySelector('button[type="submit"]').disabled = false;
  }
}

metadataButton.addEventListener("click", previewMetadata);
refreshButton.addEventListener("click", loadJobs);
sampleButton.addEventListener("click", () => {
  urlInput.value = sampleUrl;
  urlInput.focus();
  setMessage("테스트 URL을 입력했습니다.");
});
form.addEventListener("submit", createDownload);

loadHealth();
loadJobs();
