package com.ojostores.sentinel;

import android.app.Activity;
import android.app.DownloadManager;
import android.app.Notification;
import android.app.NotificationChannel;
import android.app.NotificationManager;
import android.app.PendingIntent;
import android.content.ActivityNotFoundException;
import android.content.ContentValues;
import android.content.Context;
import android.content.Intent;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.print.PrintAttributes;
import android.print.PrintManager;
import android.provider.MediaStore;
import android.util.Base64;
import android.webkit.JavascriptInterface;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceError;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.Toast;

import java.io.ByteArrayOutputStream;
import java.io.File;
import java.io.FileOutputStream;
import java.io.IOException;
import java.io.InputStream;
import java.io.OutputStream;

/**
 * OJO Sentinel for Android: a start screen that opens either the bundled offline demo or the owner's own
 * OJO Sentinel server, both in a full-screen WebView.
 *
 * Version 1.1 adds what a live test on a phone needs:
 *  - the link ojosentinel://connect?server=... (from the live-test server's QR page) fills in the server address;
 *  - report downloads (CSV, JSON) are saved to the phone's Downloads folder;
 *  - the Print button works (including "Save as PDF");
 *  - alerts the dashboard raises while the app is open appear as phone notifications;
 *  - a readable message, instead of a browser error page, when the server cannot be reached.
 */
public class MainActivity extends Activity {
    private static final String START = "file:///android_asset/index.html";
    private static final String ERROR = "file:///android_asset/error.html";
    private static final String CHANNEL = "ojo-alerts";
    private static final String POST_NOTIFICATIONS = "android.permission.POST_NOTIFICATIONS";
    private static final int REQ_STORAGE = 11;
    private static final int REQ_NOTIFY = 12;
    private static final int MAX_FILE_BYTES = 40 * 1024 * 1024;

    private WebView web;
    private String bridgeScript = "";
    private int notificationId = 100;
    // a save that is waiting for the storage permission (Android 6 to 9 only)
    private String pendingName, pendingMime;
    private byte[] pendingData;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        bridgeScript = readAsset("bridge.js");
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setUserAgentString(s.getUserAgentString() + " OJOSentinelAndroid/1.1");
        web.setBackgroundColor(0xFF0B0D10);
        web.addJavascriptInterface(new Bridge(), "OJOAndroid");
        web.setWebChromeClient(new WebChromeClient());  // default alert / confirm / prompt dialogs
        web.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, String url) {
                if (url.startsWith("http://") || url.startsWith("https://") || url.startsWith("file:///android_asset/")) {
                    return false;  // the dashboard, the demo and the start page stay in the app
                }
                try {
                    startActivity(new Intent(Intent.ACTION_VIEW, Uri.parse(url)));  // tel:, mailto:, rtsp: ...
                } catch (ActivityNotFoundException ignored) {
                    // nothing on the phone can open it
                }
                return true;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                view.evaluateJavascript(bridgeScript, null);  // downloads, printing and notifications for this page
            }

            @Override
            public void onReceivedError(WebView view, WebResourceRequest request, WebResourceError error) {
                if (request.isForMainFrame() && !request.getUrl().toString().startsWith("file:///android_asset/")) {
                    view.loadUrl(ERROR + "?url=" + Uri.encode(request.getUrl().toString())
                            + "&why=" + Uri.encode(String.valueOf(error.getDescription())));
                }
            }
        });
        setContentView(web);
        if (state == null || web.restoreState(state) == null) {
            web.loadUrl(startUrlFor(getIntent()));
        }
    }

    /** The start page, with the server address filled in when the app was opened from an ojosentinel://connect link. */
    private static String startUrlFor(Intent intent) {
        Uri link = intent == null ? null : intent.getData();
        if (link != null && "ojosentinel".equals(link.getScheme())) {
            String server = link.getQueryParameter("server");
            if (server != null && (server.startsWith("http://") || server.startsWith("https://"))) {
                return START + "?server=" + Uri.encode(server);
            }
        }
        return START;
    }

    @Override
    protected void onNewIntent(Intent intent) {
        super.onNewIntent(intent);
        setIntent(intent);
        if (intent.getData() != null) {
            web.loadUrl(startUrlFor(intent));  // opened again from a connect link while the app was running
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    public void onBackPressed() {
        String url = web.getUrl();
        if (web.canGoBack()) {
            web.goBack();
        } else if (url == null || !url.startsWith(START)) {
            web.loadUrl(START);
        } else {
            super.onBackPressed();
        }
    }

    @Override
    protected void onPause() {
        super.onPause();
        web.onPause();
    }

    @Override
    protected void onResume() {
        super.onResume();
        web.onResume();
    }

    // ------------------------------------------------------------------ what the page can ask the app to do

    /** Exposed to the page as window.OJOAndroid (see assets/bridge.js, which is the only caller). */
    private final class Bridge {
        @JavascriptInterface
        public String version() {
            return "1.1";
        }

        @JavascriptInterface
        public void saveFile(final String name, final String mime, String base64) {
            final byte[] data;
            try {
                data = Base64.decode(base64, Base64.DEFAULT);
            } catch (IllegalArgumentException bad) {
                toast("That file could not be saved.");
                return;
            }
            if (data.length > MAX_FILE_BYTES) {
                toast("That file is too large to save.");
                return;
            }
            final String safe = cleanName(name);
            final String type = mime == null || mime.isEmpty() ? "application/octet-stream" : mime;
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    store(safe, type, data);
                }
            });
        }

        @JavascriptInterface
        public void print() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    PrintManager pm = (PrintManager) getSystemService(Context.PRINT_SERVICE);
                    String job = "OJO Sentinel report";
                    pm.print(job, web.createPrintDocumentAdapter(job), new PrintAttributes.Builder().build());
                }
            });
        }

        @JavascriptInterface
        public boolean canNotify() {
            return notificationsAllowed();
        }

        @JavascriptInterface
        public void askNotify() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
                        requestPermissions(new String[]{POST_NOTIFICATIONS}, REQ_NOTIFY);
                    }
                }
            });
        }

        @JavascriptInterface
        public void showNotification(String title, String body) {
            notifyOwner(title, body);
        }
    }

    private void toast(final String text) {
        runOnUiThread(new Runnable() {
            @Override
            public void run() {
                Toast.makeText(MainActivity.this, text, Toast.LENGTH_LONG).show();
            }
        });
    }

    private String readAsset(String name) {
        try (InputStream in = getAssets().open(name)) {
            ByteArrayOutputStream out = new ByteArrayOutputStream();
            byte[] buf = new byte[8192];
            for (int n; (n = in.read(buf)) > 0; ) {
                out.write(buf, 0, n);
            }
            return out.toString("UTF-8");
        } catch (IOException e) {
            return "";
        }
    }

    // ------------------------------------------------------------------ files

    private static String cleanName(String name) {
        String n = name == null ? "" : name.replaceAll("[\\\\/:*?\"<>|\\x00-\\x1f]", "_").trim();
        return n.isEmpty() ? "ojo-sentinel-download" : n;
    }

    /** Saves a file into the phone's Downloads folder. */
    private void store(String name, String mime, byte[] data) {
        try {
            if (Build.VERSION.SDK_INT >= 29) {
                ContentValues v = new ContentValues();
                v.put(MediaStore.Downloads.DISPLAY_NAME, name);
                v.put(MediaStore.Downloads.MIME_TYPE, mime);
                v.put(MediaStore.Downloads.IS_PENDING, 1);
                Uri uri = getContentResolver().insert(MediaStore.Downloads.EXTERNAL_CONTENT_URI, v);
                if (uri == null) {
                    throw new IOException("no Downloads folder");
                }
                try (OutputStream out = getContentResolver().openOutputStream(uri)) {
                    out.write(data);
                }
                v.clear();
                v.put(MediaStore.Downloads.IS_PENDING, 0);
                getContentResolver().update(uri, v, null, null);
                toast("Saved to Downloads: " + name);
                return;
            }
            if (checkSelfPermission("android.permission.WRITE_EXTERNAL_STORAGE") != PackageManager.PERMISSION_GRANTED) {
                pendingName = name;
                pendingMime = mime;
                pendingData = data;
                requestPermissions(new String[]{"android.permission.WRITE_EXTERNAL_STORAGE"}, REQ_STORAGE);
                return;
            }
            File dir = Environment.getExternalStoragePublicDirectory(Environment.DIRECTORY_DOWNLOADS);
            dir.mkdirs();
            File file = new File(dir, name);
            for (int i = 1; file.exists(); i++) {
                int dot = name.lastIndexOf('.');
                file = new File(dir, dot > 0 ? name.substring(0, dot) + " (" + i + ")" + name.substring(dot) : name + " (" + i + ")");
            }
            try (OutputStream out = new FileOutputStream(file)) {
                out.write(data);
            }
            DownloadManager dm = (DownloadManager) getSystemService(Context.DOWNLOAD_SERVICE);
            dm.addCompletedDownload(file.getName(), "OJO Sentinel", true, mime, file.getAbsolutePath(), file.length(), true);
            toast("Saved to Downloads: " + file.getName());
        } catch (IOException | RuntimeException e) {
            toast("That file could not be saved.");
        }
    }

    @Override
    public void onRequestPermissionsResult(int code, String[] permissions, int[] results) {
        super.onRequestPermissionsResult(code, permissions, results);
        if (code == REQ_STORAGE && pendingData != null) {
            byte[] data = pendingData;
            pendingData = null;
            if (results.length > 0 && results[0] == PackageManager.PERMISSION_GRANTED) {
                store(pendingName, pendingMime, data);
            } else {
                toast("Allow storage access to save files to Downloads.");
            }
        }
    }

    // ------------------------------------------------------------------ notifications

    private boolean notificationsAllowed() {
        if (Build.VERSION.SDK_INT >= 33 && checkSelfPermission(POST_NOTIFICATIONS) != PackageManager.PERMISSION_GRANTED) {
            return false;
        }
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        return Build.VERSION.SDK_INT < 24 || nm.areNotificationsEnabled();
    }

    /** A phone notification for an alert the dashboard raised; tapping it brings the app back. */
    private void notifyOwner(String title, String body) {
        if (!notificationsAllowed()) {
            return;
        }
        NotificationManager nm = (NotificationManager) getSystemService(Context.NOTIFICATION_SERVICE);
        Notification.Builder b;
        if (Build.VERSION.SDK_INT >= 26) {
            nm.createNotificationChannel(new NotificationChannel(CHANNEL, "OJO Sentinel alerts", NotificationManager.IMPORTANCE_HIGH));
            b = new Notification.Builder(this, CHANNEL);
        } else {
            b = new Notification.Builder(this).setPriority(Notification.PRIORITY_HIGH).setDefaults(Notification.DEFAULT_ALL);
        }
        Intent open = new Intent(this, MainActivity.class).addFlags(Intent.FLAG_ACTIVITY_SINGLE_TOP | Intent.FLAG_ACTIVITY_CLEAR_TOP);
        PendingIntent tap = PendingIntent.getActivity(this, 0, open, PendingIntent.FLAG_UPDATE_CURRENT | PendingIntent.FLAG_IMMUTABLE);
        String text = body == null ? "" : body;
        b.setSmallIcon(R.drawable.ic_stat)
                .setContentTitle(title == null || title.isEmpty() ? "OJO Sentinel" : title)
                .setContentText(text)
                .setStyle(new Notification.BigTextStyle().bigText(text))
                .setContentIntent(tap)
                .setAutoCancel(true);
        nm.notify(notificationId++, b.build());
        if (notificationId > 199) {
            notificationId = 100;
        }
    }
}
