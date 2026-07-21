/**
 * دار روضة القرآن — خادم كتابة مجاني عبر Google Apps Script.
 * يُلصق داخل الورقة: Extensions ▸ Apps Script، ثم Deploy ▸ Web app.
 * لا يحتاج Google Cloud ولا حساب خدمة ولا بطاقة — مجاني تمامًا.
 *
 * بعد اللصق: غيّر TOKEN إلى كلمة سر من اختيارك، ثم انشره كـ Web app
 * (Execute as: Me  |  Who has access: Anyone). انسخ رابط /exec وضعه
 * مع نفس TOKEN في إعدادات Streamlit (قسم [apps_script]).
 */

var TOKEN = 'change-this-secret-token';  // ⬅️ غيّرها (وضع نفسها في Streamlit secrets)

function doPost(e) {
  try {
    var body = JSON.parse(e.postData.contents);
    if (String(body.token) !== String(TOKEN)) return out({ ok: false, error: 'unauthorized' });
    var ss = SpreadsheetApp.getActiveSpreadsheet();
    switch (body.action) {
      case 'append': return append_(ss, body);
      case 'update': return update_(ss, body);
      case 'delete': return del_(ss, body);
      default:       return out({ ok: false, error: 'unknown action' });
    }
  } catch (err) {
    return out({ ok: false, error: String(err) });
  }
}

function doGet() { return out({ ok: true, msg: 'Dar write service is running' }); }

function out(o) {
  return ContentService.createTextOutput(JSON.stringify(o))
    .setMimeType(ContentService.MimeType.JSON);
}

function getSheet_(ss, name, headers) {
  var sh = ss.getSheetByName(name);
  if (!sh) {
    sh = ss.insertSheet(name);
    if (headers && headers.length) sh.appendRow(headers);
  }
  return sh;
}

function headerRow_(sh) {
  var lastCol = sh.getLastColumn();
  if (lastCol === 0) return [];
  return sh.getRange(1, 1, 1, lastCol).getValues()[0].map(function (x) { return String(x).trim(); });
}

function ensureHeaders_(sh, want) {
  var hdr = headerRow_(sh);
  var missing = (want || []).filter(function (h) { return h && hdr.indexOf(h) < 0; });
  if (missing.length) {
    sh.getRange(1, hdr.length + 1, 1, missing.length).setValues([missing]);
    hdr = hdr.concat(missing);
  }
  return hdr;
}

// أول صف فارغ في عمود الكود (العمود الأول) — يتجاهل صفوف القوالب/الصيغ السفلية
// (مثل صيغة العمر) فتظهر السجلات الجديدة مباشرة أسفل البيانات لا في آخر الورقة.
function firstEmptyKeyRow_(sh) {
  var n = sh.getLastRow();
  if (n < 1) return 2;
  var vals = sh.getRange(1, 1, n, 1).getValues();
  for (var r = 1; r < vals.length; r++) {
    if (String(vals[r][0]).trim() === '') return r + 1;
  }
  return n + 1;
}

function append_(ss, body) {
  var sh = getSheet_(ss, body.sheet, body.headers || []);
  var hdr = ensureHeaders_(sh, body.headers || (body.rows[0] ? Object.keys(body.rows[0]) : []));
  var rows = (body.rows || []).map(function (r) {
    return hdr.map(function (h) { return r[h] !== undefined && r[h] !== null ? r[h] : ''; });
  });
  if (rows.length) {
    var start = firstEmptyKeyRow_(sh);
    sh.getRange(start, 1, rows.length, hdr.length).setValues(rows);
    return out({ ok: true, added: rows.length, atRow: start });
  }
  return out({ ok: true, added: 0 });
}

function update_(ss, body) {
  var sh = getSheet_(ss, body.sheet, []);
  var hdr = headerRow_(sh);
  var ci = hdr.indexOf(body.codeCol);
  if (ci < 0) return out({ ok: false, error: 'codeCol not found' });
  var data = sh.getDataRange().getValues();
  for (var r = 1; r < data.length; r++) {
    if (String(data[r][ci]).trim() === String(body.codeVal).trim()) {
      var upd = body.updates || {};
      Object.keys(upd).forEach(function (k) {
        var j = hdr.indexOf(k);
        if (j >= 0) sh.getRange(r + 1, j + 1).setValue(upd[k]);
      });
      return out({ ok: true, updated: true });
    }
  }
  return out({ ok: true, updated: false });
}

function del_(ss, body) {
  var sh = getSheet_(ss, body.sheet, []);
  var hdr = headerRow_(sh);
  var ci = hdr.indexOf(body.codeCol);
  if (ci < 0) return out({ ok: false, error: 'codeCol not found' });
  var data = sh.getDataRange().getValues();
  for (var r = 1; r < data.length; r++) {
    if (String(data[r][ci]).trim() === String(body.codeVal).trim()) {
      sh.deleteRow(r + 1);
      return out({ ok: true, deleted: true });
    }
  }
  return out({ ok: true, deleted: false });
}
