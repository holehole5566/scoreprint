import re

with open('index.html', 'r', encoding='utf-8') as f:
    content = f.read()

# ============================================================
# 1. Add tab CSS before the print-area CSS
# ============================================================
tab_css = """
/* ===== Tab 分頁 ===== */
.tabs { display: flex; gap: 0; margin-bottom: 0; }
.tab-btn {
  padding: 10px 24px; font-size: 15px; font-weight: bold; cursor: pointer;
  border: 1px solid #ccc; border-bottom: none; border-radius: 6px 6px 0 0;
  background: #e8e8e8; color: #555; transition: background .15s;
}
.tab-btn.active { background: #fff; color: #333; border-bottom: 1px solid #fff; margin-bottom: -1px; z-index: 1; }
.tab-content { display: none; border-top: 1px solid #ccc; padding-top: 16px; }
.tab-content.active { display: block; }

/* ===== Tab3 editor ===== */
#t3-editor table { border-collapse: collapse; width: 100%; }
#t3-editor th, #t3-editor td { border: 1px solid #ccc; padding: 4px 6px; text-align: center; font-size: 13px; }
#t3-editor th { background: #eee; }
#t3-editor input[type="number"] { width: 54px; text-align: center; border: 1px solid #ccc; border-radius: 3px; padding: 2px; }
"""

assert '/* ===== 列印區域 ===== */' in content
content = content.replace(
    '/* ===== 列印區域 ===== */',
    tab_css + '\n/* ===== 列印區域 ===== */'
)

# ============================================================
# 2. Wrap existing controls content in tab structure
# ============================================================

# Find the block between the usage instructions </details> and the closing </div> of controls
# We'll replace the section after the <h1> and usage <details> with tabs

# Locate the end of the </details> block
details_end = '      </ol>\n    </div>\n  </details>'
assert details_end in content, "Cannot find details end"

# Locate the closing of controls div + print-area
controls_close = """  <div style="margin-top:16px">
    <button id="btn-preview" style="display:none">預覽成績單</button>
    <button id="btn-print" style="display:none" onclick="window.print()">列印</button>
  </div>
</div>

<div id="print-area"></div>"""

assert controls_close in content, "Cannot find controls close"

# Build the new section: tabs + tab1 (existing) + tab3 (new)
old_between_start = details_end
old_between_end = controls_close

# Extract the existing content between details_end and controls_close
idx_start = content.index(details_end) + len(details_end)
idx_end = content.index(controls_close)
existing_middle = content[idx_start:idx_end]
# existing_middle contains the file inputs, status, prev-file, rank-editor

new_section = details_end + """

  <div class="tabs">
    <button class="tab-btn active" onclick="switchTab('tab1')">定期一 / 定期二</button>
    <button class="tab-btn" onclick="switchTab('tab3')">定期三</button>
  </div>

  <div id="tab1" class="tab-content active">
""" + existing_middle + """    <div style="margin-top:16px">
      <button id="btn-preview" style="display:none">預覽成績單</button>
      <button id="btn-print" style="display:none" onclick="window.print()">列印</button>
    </div>
  </div>

  <div id="tab3" class="tab-content">
    <details style="margin-bottom:12px; background:#f9f9f9; border:1px solid #ddd; border-radius:6px; padding:12px;">
      <summary style="cursor:pointer; font-weight:bold; font-size:14px;">📖 定期三使用說明</summary>
      <div style="margin-top:10px; font-size:13px; line-height:1.8;">
        <p>定期三的科目較多（含選修），PDF 格式不同，因此<span style="color:#d00; font-weight:bold;">只從 PDF 讀取座號和姓名</span>，其餘成績欄位請手動輸入。</p>
        <p style="margin-top:8px;">步驟：</p>
        <ol style="padding-left:20px;">
          <li>上傳定期三的成績 PDF（僅用來讀取學生名單）</li>
          <li>手動填入各科成績、平均、班名次、校名次、上次名次</li>
          <li>按「預覽成績單」確認排版</li>
          <li>按「列印」印出 A4，自行裁切</li>
        </ol>
      </div>
    </details>

    <label>上傳定期三成績 PDF（僅讀取座號、姓名）：</label>
    <input type="file" id="t3-file-input" accept=".pdf">
    <div id="t3-status" style="margin:8px 0; color:#666; font-size:13px;"></div>
    <div id="t3-editor"></div>
    <div style="margin-top:16px">
      <button id="t3-btn-preview" style="display:none">預覽成績單</button>
      <button id="t3-btn-print" style="display:none" onclick="window.print()">列印</button>
    </div>
  </div>
</div>

<div id="print-area"></div>"""

content = content[:content.index(details_end)] + new_section + content[content.index(controls_close) + len(controls_close):]

# ============================================================
# 3. Add tab switching JS + tab3 logic before closing </script>
# ============================================================

tab3_js = """

// ===== Tab switching =====
window.switchTab = function(id) {
  document.querySelectorAll('.tab-btn').forEach((b, i) => b.classList.toggle('active', (i === 0 ? 'tab1' : 'tab3') === id));
  document.querySelectorAll('.tab-content').forEach(c => c.classList.toggle('active', c.id === id));
};

// ===== Tab3: 定期三 =====
let t3Students = [];
const T3_SUBJECTS = ['國文','英語','數學','歷史','地理','公民','自然'];

document.getElementById('t3-file-input').addEventListener('change', handleT3File);
document.getElementById('t3-btn-preview').addEventListener('click', generateT3Preview);

async function handleT3File(e) {
  const file = e.target.files[0];
  if (!file) return;
  const status = document.getElementById('t3-status');
  status.textContent = '解析 PDF 中（僅讀取座號姓名）...';

  try {
    const arrayBuffer = await file.arrayBuffer();
    const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;
    let allItems = [];
    for (let i = 1; i <= pdf.numPages; i++) {
      const page = await pdf.getPage(i);
      const tc = await page.getTextContent();
      allItems = allItems.concat(tc.items);
    }

    // Parse only seat + name
    const rows = [];
    const Y_THRESHOLD = 3;
    allItems.forEach(item => {
      const y = Math.round(item.transform[5]);
      const x = item.transform[4];
      const text = item.str.trim();
      if (!text) return;
      let found = rows.find(r => Math.abs(r.y - y) < Y_THRESHOLD);
      if (!found) { found = { y, cells: [] }; rows.push(found); }
      found.cells.push({ x, text });
    });
    rows.sort((a, b) => b.y - a.y);
    rows.forEach(r => r.cells.sort((a, b) => a.x - b.x));

    t3Students = [];
    for (const row of rows) {
      let seat = '', name = '';
      for (const c of row.cells) {
        if (c.x >= 30 && c.x < 55) seat += c.text;
        else if (c.x >= 55 && c.x < 110) name += c.text;
      }
      if (/^\\d{2}$/.test(seat)) {
        t3Students.push({ seat, name, scores: Array(7).fill(''), avg: '', classRank: '', yearRank: '', prevRank: '' });
      }
    }
    t3Students.sort((a, b) => parseInt(a.seat) - parseInt(b.seat));
    status.textContent = `解析完成，共 ${t3Students.length} 位學生（僅座號姓名）`;
    renderT3Editor();
    document.getElementById('t3-btn-preview').style.display = 'inline-block';
    document.getElementById('t3-btn-print').style.display = 'inline-block';
  } catch (err) {
    status.textContent = '解析失敗：' + err.message;
    console.error(err);
  }
}

function renderT3Editor() {
  const hdr = '<tr><th>座號</th><th>姓名</th>' +
    T3_SUBJECTS.map(s => '<th>' + s + '</th>').join('') +
    '<th>平均</th><th>班名次</th><th>校名次</th><th>上次名次</th></tr>';
  let body = '';
  t3Students.forEach((s, i) => {
    body += '<tr><td>' + s.seat + '</td><td>' + s.name + '</td>';
    for (let j = 0; j < 7; j++) {
      body += '<td><input type="number" data-i="' + i + '" data-f="s' + j + '" value="' + s.scores[j] + '" oninput="window.t3Update(this)"></td>';
    }
    body += '<td><input type="number" data-i="' + i + '" data-f="avg" value="' + s.avg + '" oninput="window.t3Update(this)"></td>';
    body += '<td><input type="number" data-i="' + i + '" data-f="cr" value="' + s.classRank + '" oninput="window.t3Update(this)"></td>';
    body += '<td><input type="number" data-i="' + i + '" data-f="yr" value="' + s.yearRank + '" oninput="window.t3Update(this)"></td>';
    body += '<td><input type="number" data-i="' + i + '" data-f="pr" value="' + s.prevRank + '" oninput="window.t3Update(this)"></td>';
    body += '</tr>';
  });
  document.getElementById('t3-editor').innerHTML = '<table>' + hdr + body + '</table>';
}

window.t3Update = function(el) {
  const i = parseInt(el.dataset.i), f = el.dataset.f, v = el.value;
  if (f.startsWith('s')) t3Students[i].scores[parseInt(f[1])] = v;
  else if (f === 'avg') t3Students[i].avg = v;
  else if (f === 'cr') t3Students[i].classRank = v;
  else if (f === 'yr') t3Students[i].yearRank = v;
  else if (f === 'pr') t3Students[i].prevRank = v;
};

function generateT3Preview() {
  const printArea = document.getElementById('print-area');
  printArea.classList.add('preview');
  let html = '';
  for (let p = 0; p < t3Students.length; p += CARDS_PER_PAGE) {
    html += '<div class="page">';
    t3Students.slice(p, p + CARDS_PER_PAGE).forEach(s => {
      let progressText = '';
      if (s.prevRank && s.yearRank) {
        const diff = parseInt(s.prevRank) - parseInt(s.yearRank);
        if (diff > 0) progressText = '<span class="progress-pos">+' + diff + '</span>';
        else if (diff < 0) progressText = '<span class="progress-neg">' + diff + '</span>';
        else progressText = '+0';
      }
      html += '<div class="card"><table><tr><th>姓名</th>' +
        T3_SUBJECTS.map(n => '<th>' + n + '</th>').join('') +
        '<th>平均</th><th>班名次</th><th>校名次</th><th>上次名次</th><th>家長簽章</th></tr><tr>' +
        '<td>' + s.name + '</td>' +
        s.scores.map(v => '<td>' + (v || '') + '</td>').join('') +
        '<td>' + (s.avg || '') + '</td><td>' + (s.classRank || '') + '</td><td>' + (s.yearRank || '') + '</td>' +
        '<td>' + (s.prevRank ? s.prevRank + '(' + progressText + ')' : '') + '</td>' +
        '<td class="sign-cell"></td></tr></table></div>';
    });
    html += '</div>';
  }
  printArea.innerHTML = html;
  printArea.scrollIntoView({ behavior: 'smooth' });
}
"""

assert '</script>' in content
content = content.replace('</script>', tab3_js + '</script>')

# ============================================================
# 4. Update the warning text in the usage instructions
# ============================================================
content = content.replace(
    '本工具僅適用於<span style="color:#d00; font-weight:bold;">定期評量一、定期評量二</span>（定期三有其他科目，格式不同）',
    '本分頁適用於<span style="color:#d00; font-weight:bold;">定期評量一、定期評量二</span>（定期三請切換至「定期三」分頁）'
)

with open('index.html', 'w', encoding='utf-8') as f:
    f.write(content)

print("Done! Tab mechanism + Tab3 added successfully.")
