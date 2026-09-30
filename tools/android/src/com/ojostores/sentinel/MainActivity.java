package com.ojostores.sentinel;

import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Intent;
import android.net.Uri;
import android.os.Bundle;
import android.webkit.WebChromeClient;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;

/**
 * OJO Sentinel for Android: a start screen that opens either the bundled offline demo
 * or the owner's own OJO Sentinel server, both in a full-screen WebView.
 */
public class MainActivity extends Activity {
    private static final String START = "file:///android_asset/index.html";
    private WebView web;

    @Override
    protected void onCreate(Bundle state) {
        super.onCreate(state);
        web = new WebView(this);
        WebSettings s = web.getSettings();
        s.setJavaScriptEnabled(true);
        s.setDomStorageEnabled(true);
        s.setDatabaseEnabled(true);
        s.setMediaPlaybackRequiresUserGesture(false);
        s.setUserAgentString(s.getUserAgentString() + " OJOSentinelAndroid/1.0");
        web.setBackgroundColor(0xFF0B0D10);
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
        });
        setContentView(web);
        if (state == null || web.restoreState(state) == null) {
            web.loadUrl(START);
        }
    }

    @Override
    protected void onSaveInstanceState(Bundle out) {
        super.onSaveInstanceState(out);
        web.saveState(out);
    }

    @Override
    public void onBackPressed() {
        if (web.canGoBack()) {
            web.goBack();
        } else if (!START.equals(web.getUrl())) {
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
}
