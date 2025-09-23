'use strict';

// APIエンドポイントのベースURL（同一オリジンの/api配下）
const API_BASE = '/api';

const fileInput = document.getElementById('fileInput');
const dropzone = document.getElementById('dropzone');
const inputPreview = document.getElementById('inputPreview');
const outputPreview = document.getElementById('outputPreview');
const maskFacesBtn = document.getElementById('maskFacesBtn');
const aiEditBtn = null; // 統合のため未使用
// 結果表示要素は削除

let selectedFile = null;

function setBusy(isBusy) {
  [maskFacesBtn].forEach((btn) => (btn.disabled = isBusy || !selectedFile));
  if (isBusy) {
    maskFacesBtn.textContent = '処理中...';
  } else {
    maskFacesBtn.textContent = '匿名化（花束）';
  }
}

function enableActions() {
  [maskFacesBtn].forEach((btn) => (btn.disabled = !selectedFile));
}

function toBase64(file) {
  // 拡張子・MIME検証（png/jpg/jpegのみ）
  const allowed = ['image/png', 'image/jpeg'];
  if (!allowed.includes(file.type)) {
    throw new Error('対応していない形式です。pngまたはjpg/jpegのみアップロードできます。');
  }
  return new Promise((resolve, reject) => {
    const reader = new FileReader();
    reader.onload = () => resolve(reader.result.split(',')[1]);
    reader.onerror = reject;
    reader.readAsDataURL(file);
  });
}

function showInputPreview(file) {
  const url = URL.createObjectURL(file);
  inputPreview.src = url;
}

async function callApi(path, payload) {
  const res = await fetch(`${API_BASE}${path}`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(payload),
  });
  if (!res.ok) {
    const text = await res.text();
    throw new Error(`API error: ${res.status} ${text}`);
  }
  return await res.json();
}

async function handleMaskFaces() {
  if (!selectedFile) return;
  try {
    setBusy(true);
    const base64 = await toBase64(selectedFile);
    const data = await callApi('/mask-faces', {
      image: base64,
      filename: selectedFile.name || 'uploaded_image',
    });
    // 出力プレビューはData URLを優先
    if (data.data_url) {
      outputPreview.src = data.data_url;
    } else if (data.signed_url) {
      outputPreview.src = data.signed_url;
    }
  } catch (err) {
    alert(err.message);
  } finally {
    setBusy(false);
  }
}


// ドラッグ&ドロップ
dropzone.addEventListener('dragover', (e) => {
  e.preventDefault();
  dropzone.classList.add('dragover');
});
dropzone.addEventListener('dragleave', () => dropzone.classList.remove('dragover'));
dropzone.addEventListener('drop', (e) => {
  e.preventDefault();
  dropzone.classList.remove('dragover');
  const file = e.dataTransfer.files?.[0];
  if (file) {
    selectedFile = file;
    showInputPreview(file);
    enableActions();
  }
});

// ファイル選択
fileInput.addEventListener('change', (e) => {
  const file = e.target.files?.[0];
  if (file) {
    if (!['image/png', 'image/jpeg'].includes(file.type)) {
      alert('pngまたはjpg/jpegのみアップロードできます。');
      fileInput.value = '';
      return;
    }
    selectedFile = file;
    showInputPreview(file);
    enableActions();
  }
});

maskFacesBtn.addEventListener('click', handleMaskFaces);
// 統合のためAI編集ボタンは廃止


