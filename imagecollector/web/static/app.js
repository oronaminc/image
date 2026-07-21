// 상세 페이지 인터랙션: 즐겨찾기 토글 / 삭제 / 저작자 표기 복사
(function () {
  const favBtn = document.getElementById("fav-btn");
  const delBtn = document.getElementById("del-btn");
  const id = window.__IMG_ID__;

  async function post(url, body) {
    const opts = { method: "POST" };
    if (body) {
      const fd = new FormData();
      Object.entries(body).forEach(([k, v]) => fd.append(k, v));
      opts.body = fd;
    }
    const res = await fetch(url, opts);
    return res.json();
  }

  if (favBtn) {
    favBtn.addEventListener("click", async () => {
      const next = favBtn.dataset.fav === "1" ? 0 : 1;
      const data = await post(`/api/image/${id}/favorite`, { value: next });
      if (data.ok) {
        favBtn.dataset.fav = next;
        favBtn.classList.toggle("active", !!next);
        favBtn.textContent = next ? "⭐ 즐겨찾기됨" : "☆ 즐겨찾기";
      }
    });
  }

  if (delBtn) {
    delBtn.addEventListener("click", async () => {
      if (!confirm("이 이미지를 라이브러리와 디스크에서 삭제할까요?")) return;
      const data = await post(`/api/image/${id}/delete`);
      if (data.ok) window.location.href = "/";
    });
  }
})();

function copyAttr() {
  const ta = document.getElementById("attr-text");
  if (!ta) return;
  ta.select();
  navigator.clipboard.writeText(ta.value).then(() => {
    const btn = event.target;
    const old = btn.textContent;
    btn.textContent = "✅ 복사됨";
    setTimeout(() => (btn.textContent = old), 1500);
  });
}
