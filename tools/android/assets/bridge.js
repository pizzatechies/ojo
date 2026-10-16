// Runs inside every page the OJO Sentinel app opens (the app injects it after each page load).
// An Android WebView ignores three things a dashboard takes for granted: downloading a file built in the page,
// window.print(), and the Notification API. This hands each of them to the app, through window.OJOAndroid.
(function () {
  "use strict";
  var app = window.OJOAndroid;
  if (!app || window.__ojoBridge) return;
  window.__ojoBridge = true;

  // ---- Downloads: the page makes a Blob, points a hidden <a download> at it and clicks it.
  var blobs = {};
  var create = URL.createObjectURL;
  URL.createObjectURL = function (obj) {
    var url = create.call(URL, obj);
    if (obj instanceof Blob) blobs[url] = obj;
    return url;
  };
  var revoke = URL.revokeObjectURL;
  URL.revokeObjectURL = function (url) {
    setTimeout(function () { delete blobs[url]; }, 30000);
    return revoke.call(URL, url);
  };
  function send(name, blob) {
    var reader = new FileReader();
    reader.onload = function () {
      var text = String(reader.result);
      app.saveFile(name || "download", blob.type || "application/octet-stream", text.slice(text.indexOf(",") + 1));
    };
    reader.readAsDataURL(blob);
  }
  function takeOver(a) {
    if (!a || !a.hasAttribute || !a.hasAttribute("download")) return false;
    var href = String(a.href), name = a.getAttribute("download");
    if (href.indexOf("blob:") === 0 && blobs[href]) { send(name, blobs[href]); return true; }
    if (href.indexOf("data:") === 0) {
      fetch(href).then(function (r) { return r.blob(); }).then(function (b) { send(name, b); });
      return true;
    }
    return false;
  }
  var click = HTMLAnchorElement.prototype.click;
  HTMLAnchorElement.prototype.click = function () {
    if (!takeOver(this)) return click.apply(this, arguments);
  };
  document.addEventListener("click", function (e) {
    var a = e.target && e.target.closest ? e.target.closest("a") : null;
    if (takeOver(a)) e.preventDefault();
  }, true);

  // ---- Printing (the print dialog also offers "Save as PDF").
  window.print = function () { app.print(); };

  // ---- Notifications: the dashboard raises one for every high or critical alert while it is open.
  // (Replaces whatever the WebView offers: it has no working one.)
  var N = function (title, options) {
    app.showNotification(String(title), options && options.body ? String(options.body) : "");
  };
  Object.defineProperty(N, "permission", { get: function () { return app.canNotify() ? "granted" : "default"; } });
  N.requestPermission = function () {
    app.askNotify();
    return new Promise(function (resolve) {
      setTimeout(function () { resolve(N.permission); }, 1500);
    });
  };
  window.Notification = N;
})();
