package ar.heberfrau.truco;

import android.app.Activity;
import android.os.Bundle;
import android.graphics.Color;
import android.media.MediaPlayer;
import android.content.res.AssetFileDescriptor;
import android.webkit.WebChromeClient;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.webkit.JavascriptInterface;
import android.view.View;
import android.view.WindowManager;
import android.widget.Toast;

public class MainActivity extends Activity {
    private WebView webView;
    private MediaPlayer player;
    private boolean musicEnabled = true;

    @Override public void onCreate(Bundle state) {
        super.onCreate(state);
        getWindow().setStatusBarColor(Color.rgb(14,24,34));
        getWindow().addFlags(WindowManager.LayoutParams.FLAG_KEEP_SCREEN_ON);
        getWindow().setNavigationBarColor(Color.rgb(14,24,34));
        musicEnabled = getPreferences(MODE_PRIVATE).getBoolean("music_enabled", true);
        webView = new WebView(this);
        webView.setBackgroundColor(Color.rgb(14,24,34));
        webView.setKeepScreenOn(true);
        webView.getSettings().setJavaScriptEnabled(true);
        webView.getSettings().setDomStorageEnabled(true);
        webView.getSettings().setAllowFileAccess(true);
        webView.setWebChromeClient(new WebChromeClient());
        webView.setWebViewClient(new WebViewClient());
        webView.addJavascriptInterface(new NativeBridge(), "TrucoNative");
        webView.setOverScrollMode(View.OVER_SCROLL_NEVER);
        setContentView(webView);
        webView.loadUrl("file:///android_asset/index.html");
        if (musicEnabled) startMusic();
    }

    private void startMusic() {
        if (player != null) { if (!player.isPlaying()) player.start(); return; }
        try {
            AssetFileDescriptor afd = getAssets().openFd("musica_fondo.ogg");
            MediaPlayer mp = new MediaPlayer();
            mp.setDataSource(afd.getFileDescriptor(), afd.getStartOffset(), afd.getLength());
            afd.close();
            mp.setLooping(true);
            mp.setVolume(0.24f, 0.24f);
            mp.prepare();
            mp.start();
            player = mp;
        } catch (Exception ex) {
            android.util.Log.w("TrucoHeber", "No se pudo reproducir la música", ex);
        }
    }

    private void stopMusic() {
        if (player != null && player.isPlaying()) player.pause();
    }

    private class NativeBridge {
        @JavascriptInterface public boolean isMusicEnabled() { return musicEnabled; }
        @JavascriptInterface public void setMusicEnabled(final boolean enabled) {
            runOnUiThread(() -> {
                musicEnabled = enabled;
                getPreferences(MODE_PRIVATE).edit().putBoolean("music_enabled", enabled).apply();
                if (enabled) startMusic(); else stopMusic();
            });
        }
    }

    @Override protected void onPause() {
        super.onPause();
        stopMusic();
        if (webView != null) webView.onPause();
    }
    @Override protected void onResume() {
        super.onResume();
        if (webView != null) webView.onResume();
        if (musicEnabled) startMusic();
    }
    @Override protected void onDestroy() {
        if (player != null) { player.release(); player = null; }
        if (webView != null) { webView.destroy(); webView = null; }
        super.onDestroy();
    }
    @Override public void onBackPressed() {
        if (webView != null) webView.evaluateJavascript("toggleMenu(false)", null);
        else super.onBackPressed();
    }
}