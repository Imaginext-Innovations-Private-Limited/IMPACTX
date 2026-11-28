package com.aarogyamesh.app;

import android.Manifest;
import android.app.Activity;
import android.app.ActivityManager;
import android.app.AlertDialog;
import android.content.ActivityNotFoundException;
import android.content.BroadcastReceiver;
import android.content.Context;
import android.content.DialogInterface;
import android.content.Intent;
import android.content.IntentFilter;
import android.content.pm.PackageManager;
import android.graphics.Typeface;
import android.graphics.drawable.GradientDrawable;
import android.net.ConnectivityManager;
import android.net.Network;
import android.net.NetworkCapabilities;
import android.net.NetworkRequest;
import android.net.Uri;
import android.os.BatteryManager;
import android.os.Build;
import android.os.Bundle;
import android.os.VibrationEffect;
import android.os.Vibrator;
import android.os.VibratorManager;
import android.text.InputType;
import android.text.TextUtils;
import android.util.Log;
import android.util.TypedValue;
import android.view.Gravity;
import android.view.KeyEvent;
import android.view.View;
import android.view.ViewGroup;
import android.view.Window;
import android.view.WindowInsetsController;
import android.webkit.ConsoleMessage;
import android.webkit.JavascriptInterface;
import android.webkit.PermissionRequest;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.EditText;
import android.widget.FrameLayout;
import android.widget.HorizontalScrollView;
import android.widget.LinearLayout;
import android.widget.TextView;
import android.widget.Toast;
import android.window.OnBackInvokedCallback;
import android.window.OnBackInvokedDispatcher;

import java.io.IOException;
import java.net.Inet4Address;
import java.net.InetAddress;
import java.net.NetworkInterface;
import java.net.URI;
import java.util.ArrayList;
import java.util.Enumeration;
import java.util.List;
import java.util.Locale;

/**
 * Native Android shell for Aarogya Mesh (com.aarogyamesh.app).
 *
 * Maintains two persistent WebView instances (phoneWebView for /phone/ and watchWebView for /watch/)
 * toggled via VISIBLE/GONE so switching modes never reloads or wipes unsaved forms/recordings.
 * Provides a slim EN / Shuddh Tatsama Hindi / Kannada / Tamil top bar, native Set Hub URL dialog, hardware bridge,
 * microphone capture auto-grant for 127.0.0.1, tel:108 dialing, and OnBackInvokedCallback handling.
 */
public class MainActivity extends Activity {
    private static final String TAG = "AarogyaMainActivity";
    private static final String PREFS_NAME = "aarogya_prefs";
    private static final String PREF_HUB_URL = "hub_url";
    private static final int REQ_RECORD_AUDIO = 1001;
    private static final int REQ_CAMERA = 1002;
    private static final int REQ_QR_SCAN = 1003;

    private static final int COLOR_BG_SLATE = 0xFF0F172A;
    private static final int COLOR_DIVIDER = 0xFF1E293B;
    private static final int COLOR_TEAL_ACTIVE = 0xFF0D9488;
    private static final int COLOR_TAB_INACTIVE = 0xFF1E293B;
    private static final int COLOR_TEXT_DARK = 0xFF020617;
    private static final int COLOR_TEXT_MUTED = 0xFFCBD5E1;
    private static final int COLOR_BADGE_TEXT = 0xFF5EEAD4;

    private LocalAssetServer assetServer;
    private WebView phoneWebView;
    private WebView watchWebView;
    private boolean watchLoaded = false;
    private AarogyaNativeBridge nativeBridge;
    private PermissionRequest pendingWebPermissionRequest;
    private AlertDialog qrScannerDialog;
    private WebView qrScannerWebView;
    private String pendingQrLang;
    private EditText pendingQrTargetInput;

    private TextView tabPhone;
    private TextView tabWatch;
    private TextView langToggle;
    private TextView hubTelemetryPill;

    private String activeMode = "phone";
    private String uiLang = "en";
    private boolean batteryReceiverRegistered = false;
    private boolean networkCallbackRegistered = false;
    private ConnectivityManager.NetworkCallback networkCallback;
    private OnBackInvokedCallback backInvokedCallback;

    private final BroadcastReceiver batteryReceiver = new BroadcastReceiver() {
        @Override
        public void onReceive(Context context, Intent intent) {
            updateTelemetryBadge();
        }
    };

    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);

        assetServer = new LocalAssetServer(getAssets());
        try {
            assetServer.start();
        } catch (IOException e) {
            Log.e(TAG, "Failed to start LocalAssetServer", e);
            Toast.makeText(this, "Failed to start local asset server: " + e.getMessage(), Toast.LENGTH_LONG).show();
            finish();
            return;
        }

        // Enable Chrome DevTools Protocol (CDP) inspection for automated testing & debugging.
        WebView.setWebContentsDebuggingEnabled(true);

        nativeBridge = new AarogyaNativeBridge(this);

        View rootView = buildLayout();
        setContentView(rootView);
        configureSystemBars();
        registerBackNavigation();

        requestMicrophonePermissionIfNeeded();

        // Load ASHA Field App (/phone/) on startup; watchWebView loads lazily on first tab switch.
        phoneWebView.loadUrl(assetServer.getBaseUrl() + "/phone/");
        showMode("phone");
        applyTopBarLocale();
        updateTelemetryBadge();
    }

    private void configureSystemBars() {
        Window window = getWindow();
        if (window == null) {
            return;
        }
        window.setBackgroundDrawableResource(android.R.color.black);
        window.setStatusBarColor(COLOR_BG_SLATE);
        window.setNavigationBarColor(COLOR_BG_SLATE);
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.R) {
            View decor = window.getDecorView();
            if (decor != null) {
                WindowInsetsController controller = window.getInsetsController();
                if (controller != null) {
                    controller.setSystemBarsAppearance(
                            0,
                            WindowInsetsController.APPEARANCE_LIGHT_STATUS_BARS
                                    | WindowInsetsController.APPEARANCE_LIGHT_NAVIGATION_BARS
                    );
                }
            }
        }
    }

    private void registerBackNavigation() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            backInvokedCallback = new OnBackInvokedCallback() {
                @Override
                public void onBackInvoked() {
                    handleBackNavigation();
                }
            };
            getOnBackInvokedDispatcher().registerOnBackInvokedCallback(
                    OnBackInvokedDispatcher.PRIORITY_DEFAULT,
                    backInvokedCallback
            );
        }
    }

    private void handleBackNavigation() {
        WebView active = getActiveWebView();
        if (active != null && active.canGoBack()) {
            active.goBack();
            return;
        }
        if ("watch".equals(activeMode)) {
            showMode("phone");
            return;
        }
        // Minimize cleanly instead of tearing down local server & WebView state.
        moveTaskToBack(true);
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && Build.VERSION.SDK_INT < Build.VERSION_CODES.TIRAMISU) {
            handleBackNavigation();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    private View buildLayout() {
        LinearLayout root = new LinearLayout(this);
        root.setOrientation(LinearLayout.VERTICAL);
        root.setBackgroundColor(COLOR_BG_SLATE);
        root.setFitsSystemWindows(true);
        root.setLayoutParams(new ViewGroup.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        ));

        // Slim native mode switcher bar (ASHA Field <-> Watch / SOS + Lang + Set Hub URL pill)
        // Wrapped in HorizontalScrollView with fillViewport=true so long Indic labels never clip or overlap on narrow screens.
        HorizontalScrollView topBarScroll = new HorizontalScrollView(this);
        topBarScroll.setFillViewport(true);
        topBarScroll.setHorizontalScrollBarEnabled(false);
        topBarScroll.setBackgroundColor(COLOR_BG_SLATE);
        topBarScroll.setLayoutParams(new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        ));

        LinearLayout topBar = new LinearLayout(this);
        topBar.setOrientation(LinearLayout.HORIZONTAL);
        topBar.setGravity(Gravity.CENTER_VERTICAL);
        topBar.setBackgroundColor(COLOR_BG_SLATE);
        topBar.setPadding(dp(8), dp(4), dp(8), dp(4));
        topBar.setLayoutParams(new HorizontalScrollView.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        ));

        tabPhone = createPillButton();
        tabPhone.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                showMode("phone");
            }
        });

        tabWatch = createPillButton();
        tabWatch.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                showMode("watch");
            }
        });

        LinearLayout.LayoutParams phoneLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
        phoneLp.setMarginEnd(dp(5));
        topBar.addView(tabPhone, phoneLp);

        LinearLayout.LayoutParams watchLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
        watchLp.setMarginEnd(dp(5));
        topBar.addView(tabWatch, watchLp);

        View spacer = new View(this);
        LinearLayout.LayoutParams spacerLp = new LinearLayout.LayoutParams(0, 1, 1.0f);
        topBar.addView(spacer, spacerLp);

        langToggle = createPillButton();
        langToggle.setPadding(dp(8), dp(4), dp(8), dp(4));
        langToggle.setBackground(pillDrawable(COLOR_TAB_INACTIVE, 0xFF475569));
        langToggle.setTextColor(0xFFF8FAFC);
        langToggle.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                toggleUiLanguage();
            }
        });
        LinearLayout.LayoutParams langLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
        langLp.setMarginEnd(dp(5));
        topBar.addView(langToggle, langLp);

        hubTelemetryPill = new TextView(this);
        hubTelemetryPill.setTextSize(TypedValue.COMPLEX_UNIT_SP, 10.5f);
        hubTelemetryPill.setTypeface(Typeface.DEFAULT_BOLD);
        hubTelemetryPill.setTextColor(COLOR_BADGE_TEXT);
        hubTelemetryPill.setSingleLine(true);
        hubTelemetryPill.setMaxLines(1);
        hubTelemetryPill.setEllipsize(TextUtils.TruncateAt.END);
        hubTelemetryPill.setGravity(Gravity.CENTER);
        hubTelemetryPill.setPadding(dp(8), dp(4), dp(8), dp(4));
        hubTelemetryPill.setClickable(true);
        hubTelemetryPill.setFocusable(true);
        hubTelemetryPill.setBackground(pillDrawable(0xFF042F2E, COLOR_TEAL_ACTIVE));
        hubTelemetryPill.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                openSetHubUrlDialog();
            }
        });
        topBar.addView(hubTelemetryPill);

        topBarScroll.addView(topBar);
        root.addView(topBarScroll);

        View divider = new View(this);
        divider.setBackgroundColor(COLOR_DIVIDER);
        root.addView(divider, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(1)
        ));

        // Persistent dual-WebView container: VISIBLE/GONE toggling preserves unsaved forms & recordings.
        FrameLayout webContainer = new FrameLayout(this);
        webContainer.setBackgroundColor(COLOR_BG_SLATE);

        phoneWebView = createConfiguredWebView("phone");
        watchWebView = createConfiguredWebView("watch");
        watchWebView.setVisibility(View.GONE);

        FrameLayout.LayoutParams fill = new FrameLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                ViewGroup.LayoutParams.MATCH_PARENT
        );
        webContainer.addView(phoneWebView, fill);
        webContainer.addView(watchWebView, fill);

        root.addView(webContainer, new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                0,
                1.0f
        ));

        return root;
    }

    private TextView createPillButton() {
        TextView btn = new TextView(this);
        btn.setTextSize(TypedValue.COMPLEX_UNIT_SP, 10.5f);
        btn.setTypeface(Typeface.DEFAULT_BOLD);
        btn.setGravity(Gravity.CENTER);
        btn.setSingleLine(true);
        btn.setMaxLines(1);
        btn.setEllipsize(TextUtils.TruncateAt.END);
        btn.setPadding(dp(8), dp(4), dp(8), dp(4));
        btn.setClickable(true);
        btn.setFocusable(true);
        return btn;
    }

    private GradientDrawable pillDrawable(int fillColor, int strokeColor) {
        GradientDrawable d = new GradientDrawable();
        d.setShape(GradientDrawable.RECTANGLE);
        d.setCornerRadius(dp(999));
        d.setColor(fillColor);
        d.setStroke(dp(1), strokeColor);
        return d;
    }

    private static String normalizeLang(String lang) {
        if ("hi".equalsIgnoreCase(lang)) {
            return "hi";
        }
        if ("kn".equalsIgnoreCase(lang)) {
            return "kn";
        }
        if ("ta".equalsIgnoreCase(lang)) {
            return "ta";
        }
        return "en";
    }

    private static String tr(String lang, String en, String hi, String kn, String ta) {
        if ("hi".equals(lang)) {
            return hi;
        }
        if ("kn".equals(lang)) {
            return kn;
        }
        if ("ta".equals(lang)) {
            return ta;
        }
        return en;
    }

    private String tr(String en, String hi, String kn, String ta) {
        return tr(uiLang, en, hi, kn, ta);
    }

    private void applyTopBarLocale() {
        if (tabPhone != null) {
            tabPhone.setText(tr("ASHA Field", "आशा क्षेत्र", "ಆಶಾ ಕ್ಷೇತ್ರ", "ஆஷா களம்"));
            tabPhone.setContentDescription(tr(
                    "Switch to ASHA Field App",
                    "आशा क्षेत्र अनुप्रयोग खोलें",
                    "ಆಶಾ ಕ್ಷೇತ್ರ ಆ್ಯಪ್ ತೆರೆಯಿರಿ",
                    "ஆஷா கள செயலிக்கு மாறவும்"
            ));
        }
        if (tabWatch != null) {
            tabWatch.setText(tr("Watch / SOS", "घटिका / आपात", "ವಾಚ್ / ತುರ್ತು", "கடிகாரம் / அவசரம்"));
            tabWatch.setContentDescription(tr(
                    "Switch to Watch and Family SOS",
                    "घटिका एवं परिवार आपात अनुप्रयोग खोलें",
                    "ವಾಚ್ ಮತ್ತು ಕುಟುಂಬ ತುರ್ತು ಆ್ಯಪ್ ತೆರೆಯಿರಿ",
                    "கடிகாரம் மற்றும் குடும்ப அவசர செயலிக்கு மாறவும்"
            ));
        }
        if (langToggle != null) {
            langToggle.setText(tr("EN", "हिन्दी", "ಕನ್ನಡ", "தமிழ்"));
            langToggle.setContentDescription(tr(
                    "भाषा हिन्दी में बदलें",
                    "ಕನ್ನಡಕ್ಕೆ ಭಾಷೆ ಬದಲಿಸಿ",
                    "மொழியை தமிழுக்கு மாற்றவும்",
                    "Switch language to English"
            ));
        }
        if (hubTelemetryPill != null) {
            hubTelemetryPill.setContentDescription(tr(
                    "Set Hub URL and device status",
                    "स्वास्थ्य केन्द्र का संजाल पता निर्धारित करें",
                    "ಆರೋಗ್ಯ ಕೇಂದ್ರದ ಜಾಲ ವಿಳಾಸ ಹೊಂದಿಸಿ",
                    "சுகாதார நிலைய இணைய முகவரி மற்றும் சாதன நிலை அமைக்கவும்"
            ));
        }
        updateTelemetryBadge();
    }

    private void setUiLanguage(String lang, boolean propagateToWeb) {
        String normalized = normalizeLang(lang);
        boolean changed = !normalized.equals(uiLang);
        uiLang = normalized;
        applyTopBarLocale();
        if (propagateToWeb && changed) {
            String js = "(function(){try{localStorage.setItem('aarogya.lang','" + normalized + "');"
                    + "window.dispatchEvent(new StorageEvent('storage',{key:'aarogya.lang',newValue:'" + normalized + "'}));"
                    + "window.postMessage({type:'aarogya:setLang',lang:'" + normalized + "'},'*');"
                    + "}catch(e){}})();";
            evalOnLoadedWebViews(js);
        }
    }

    private void toggleUiLanguage() {
        String next;
        if ("en".equals(uiLang)) {
            next = "hi";
        } else if ("hi".equals(uiLang)) {
            next = "kn";
        } else if ("kn".equals(uiLang)) {
            next = "ta";
        } else {
            next = "en";
        }
        setUiLanguage(next, true);
    }

    private void syncLocaleFromWebView(WebView view) {
        if (view == null) {
            return;
        }
        view.evaluateJavascript(
                "(function(){try{return localStorage.getItem('aarogya.lang')||'';}catch(e){return '';}})();",
                new ValueCallback<String>() {
                    @Override
                    public void onReceiveValue(String value) {
                        String cleaned = unquoteJsString(value);
                        if ("hi".equals(cleaned) || "kn".equals(cleaned) || "ta".equals(cleaned) || "en".equals(cleaned)) {
                            if (!cleaned.equals(uiLang)) {
                                uiLang = cleaned;
                                applyTopBarLocale();
                            }
                        }
                    }
                }
        );
    }

    private void updateTabStyles(String mode) {
        activeMode = mode;
        boolean isWatch = "watch".equals(mode);
        if (tabPhone != null) {
            tabPhone.setBackground(pillDrawable(
                    isWatch ? COLOR_TAB_INACTIVE : COLOR_TEAL_ACTIVE,
                    isWatch ? 0xFF334155 : 0xFF14B8A6
            ));
            tabPhone.setTextColor(isWatch ? COLOR_TEXT_MUTED : COLOR_TEXT_DARK);
        }
        if (tabWatch != null) {
            tabWatch.setBackground(pillDrawable(
                    isWatch ? COLOR_TEAL_ACTIVE : COLOR_TAB_INACTIVE,
                    isWatch ? 0xFF14B8A6 : 0xFF334155
            ));
            tabWatch.setTextColor(isWatch ? COLOR_TEXT_DARK : COLOR_TEXT_MUTED);
        }
    }

    private void showMode(String mode) {
        if (assetServer == null || phoneWebView == null || watchWebView == null) {
            return;
        }
        String normalized = "watch".equals(mode) ? "watch" : "phone";
        boolean isWatch = "watch".equals(normalized);
        if (isWatch && !watchLoaded) {
            watchLoaded = true;
            watchWebView.loadUrl(assetServer.getBaseUrl() + "/watch/");
        }
        phoneWebView.setVisibility(isWatch ? View.GONE : View.VISIBLE);
        watchWebView.setVisibility(isWatch ? View.VISIBLE : View.GONE);
        updateTabStyles(normalized);
        syncLocaleFromWebView(getActiveWebView());
    }

    private WebView getActiveWebView() {
        return "watch".equals(activeMode) ? watchWebView : phoneWebView;
    }

    private WebView createConfiguredWebView(final String ownerMode) {
        WebView wv = new WebView(this);
        wv.setBackgroundColor(COLOR_BG_SLATE);
        wv.setOverScrollMode(WebView.OVER_SCROLL_NEVER);

        WebSettings settings = wv.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        settings.setAllowContentAccess(true);
        settings.setAllowFileAccess(false);
        settings.setUseWideViewPort(true);
        settings.setLoadWithOverviewMode(true);
        settings.setSupportZoom(false);
        settings.setBuiltInZoomControls(false);
        settings.setDisplayZoomControls(false);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_ALWAYS_ALLOW);

        wv.addJavascriptInterface(nativeBridge, "AarogyaNativeBridge");

        wv.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                Uri uri = request != null ? request.getUrl() : null;
                if (uri == null) {
                    return false;
                }
                String scheme = uri.getScheme() != null ? uri.getScheme().toLowerCase(Locale.US) : "";
                if ("tel".equals(scheme)) {
                    openDialer(uri);
                    return true;
                }
                if ("sms".equals(scheme) || "smsto".equals(scheme) || "mailto".equals(scheme)) {
                    openExternalIntent(new Intent(Intent.ACTION_VIEW, uri));
                    return true;
                }
                String host = uri.getHost() != null ? uri.getHost().toLowerCase(Locale.US) : "";
                if ("127.0.0.1".equals(host) || "localhost".equals(host)) {
                    String path = uri.getPath();
                    if (path != null) {
                        if (path.startsWith("/watch") && !"watch".equals(ownerMode)) {
                            showMode("watch");
                            return true;
                        }
                        if (path.startsWith("/phone") && !"phone".equals(ownerMode)) {
                            showMode("phone");
                            return true;
                        }
                    }
                    return false;
                }
                if ("http".equals(scheme) || "https".equals(scheme)) {
                    openExternalIntent(new Intent(Intent.ACTION_VIEW, uri));
                    return true;
                }
                return false;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                super.onPageFinished(view, url);
                syncLocaleFromWebView(view);
                injectSavedHubUrl(view);
            }
        });

        wv.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                if (request == null) {
                    return;
                }
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        handleWebPermissionRequest(request);
                    }
                });
            }

            @Override
            public void onPermissionRequestCanceled(PermissionRequest request) {
                if (pendingWebPermissionRequest == request) {
                    pendingWebPermissionRequest = null;
                }
            }

            @Override
            public boolean onConsoleMessage(ConsoleMessage consoleMessage) {
                if (consoleMessage != null) {
                    Log.d("AarogyaWebView",
                            "[" + ownerMode + "] " + consoleMessage.messageLevel()
                                    + " [" + consoleMessage.sourceId() + ":"
                                    + consoleMessage.lineNumber() + "] " + consoleMessage.message());
                }
                return super.onConsoleMessage(consoleMessage);
            }
        });

        return wv;
    }

    private void openSetHubUrlDialog() {
        WebView active = getActiveWebView();
        if (active == null) {
            return;
        }
        active.evaluateJavascript(
                "(function(){try{return localStorage.getItem('aarogya.hubUrl')||localStorage.getItem('aarogya.watch.hubUrl')||'';}catch(e){return '';}})();",
                new ValueCallback<String>() {
                    @Override
                    public void onReceiveValue(String value) {
                        String current = unquoteJsString(value);
                        if (current.isEmpty()) {
                            current = getSharedPreferences(PREFS_NAME, MODE_PRIVATE).getString(PREF_HUB_URL, "");
                        }
                        showHubUrlAlertDialog(normalizeHubUrl(current));
                    }
                }
        );
    }

    private void showHubUrlAlertDialog(String currentHubUrl) {
        final String lang = uiLang;
        String netLabel = localizedNetworkLabel(nativeBridge.getNetworkType(), lang);
        int pct = nativeBridge.getBatteryPercent();
        String telemetry = Build.MODEL
                + " · " + (pct >= 0 ? pct + "%" : "--%")
                + " · " + netLabel
                + " · " + nativeBridge.getTotalRamMb() + " MB";
        String currentDisplay = (currentHubUrl == null || currentHubUrl.isEmpty())
                ? tr(lang, "Not set (auto)", "निर्धारित नहीं (स्वतः)", "ನಿಗದಿಪಡಿಸಿಲ್ಲ (ಸ್ವಯಂ)", "அமைக்கப்படவில்லை (தானியங்கி)")
                : currentHubUrl;

        LinearLayout box = new LinearLayout(this);
        box.setOrientation(LinearLayout.VERTICAL);
        box.setPadding(dp(20), dp(10), dp(20), dp(4));

        TextView info = new TextView(this);
        info.setText(telemetry + "\n" + tr(lang, "Current Hub: ", "वर्तमान केन्द्र: ", "ಪ್ರಸ್ತುತ ಕೇಂದ್ರ: ", "தற்போதைய நிலையம்: ") + currentDisplay);
        info.setTextSize(TypedValue.COMPLEX_UNIT_SP, 12f);
        info.setPadding(0, 0, 0, dp(10));
        box.addView(info);

        final EditText input = new EditText(this);
        input.setInputType(InputType.TYPE_CLASS_TEXT | InputType.TYPE_TEXT_VARIATION_URI);
        input.setSingleLine(true);
        input.setHint(LocalAssetServer.DEFAULT_HUB_URL);
        if (currentHubUrl != null && !currentHubUrl.isEmpty()) {
            input.setText(currentHubUrl);
            input.setSelection(currentHubUrl.length());
        }
        box.addView(input);

        TextView scanQrBtn = createPillButton();
        scanQrBtn.setText(tr(lang, "Scan QR Code", "QR कोड स्कैन करें", "QR ಕೋಡ್ ಸ್ಕ್ಯಾನ್ ಮಾಡಿ", "QR குறியீட்டை ஸ்கேன் செய்"));
        scanQrBtn.setTextColor(0xFF5EEAD4);
        scanQrBtn.setBackground(pillDrawable(0xFF042F2E, COLOR_TEAL_ACTIVE));
        scanQrBtn.setPadding(dp(12), dp(8), dp(12), dp(8));
        LinearLayout.LayoutParams scanLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.WRAP_CONTENT,
                ViewGroup.LayoutParams.WRAP_CONTENT
        );
        scanLp.topMargin = dp(8);
        scanQrBtn.setOnClickListener(new View.OnClickListener() {
            @Override
            public void onClick(View v) {
                startQrScanFlow(lang, input);
            }
        });
        box.addView(scanQrBtn, scanLp);

        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle(tr(lang, "Set Hub URL", "स्वास्थ्य केन्द्र का संजाल पता", "ಕೇಂದ್ರದ ಜಾಲ ವಿಳಾಸ ಹೊಂದಿಸಿ", "நிலைய இணைய முகவரி அமைக்கவும்"));
        builder.setView(box);
        builder.setPositiveButton(tr(lang, "Save", "संचित करें", "ಉಳಿಸಿ", "சேமி"), new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface dialog, int which) {
                String raw = input.getText() != null ? input.getText().toString() : "";
                String normalized = normalizeHubUrl(raw);
                if (normalized.isEmpty()) {
                    clearSavedHubUrl(lang);
                    return;
                }
                if (!isValidHttpUrl(normalized)) {
                    Toast.makeText(
                            MainActivity.this,
                            tr(
                                    lang,
                                    "Enter a valid Hub URL (e.g. 192.168.1.14:8000)",
                                    "कृपया मान्य संजाल पता भरें (जैसे 192.168.1.14:8000)",
                                    "ದಯವಿಟ್ಟು ಮಾನ್ಯವಾದ ಕೇಂದ್ರ ವಿಳಾಸ ನಮೂದಿಸಿ (ಉದಾ. 192.168.1.14:8000)",
                                    "சரியான நிலைய முகவரியை உள்ளிடவும் (எ.கா. 192.168.1.14:8000)"
                            ),
                            Toast.LENGTH_SHORT
                    ).show();
                    return;
                }
                applySavedHubUrl(normalized, lang);
            }
        });
        builder.setNeutralButton(tr(lang, "Clear", "हटाएँ", "ತೆರವುಗೊಳಿಸಿ", "அழி"), new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface dialog, int which) {
                clearSavedHubUrl(lang);
            }
        });
        builder.setNegativeButton(tr(lang, "Cancel", "निरस्त करें", "ರದ್ದುಮಾಡಿ", "ரத்து செய்"), null);
        builder.show();
    }

    private void applySavedHubUrl(String url, String lang) {
        String normalized = normalizeHubUrl(url);
        getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
                .edit()
                .putString(PREF_HUB_URL, normalized)
                .apply();
        String escaped = escapeJsSingleQuoted(normalized);
        String js = "(function(){try{"
                + "localStorage.setItem('aarogya.hubUrl','" + escaped + "');"
                + "localStorage.setItem('aarogya.watch.hubUrl','" + escaped + "');"
                + "var el=document.querySelector('input[name=\"hub\"],input[data-hub-url]');"
                + "if(el){el.value='" + escaped + "';el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));}"
                + "window.dispatchEvent(new StorageEvent('storage',{key:'aarogya.hubUrl',newValue:'" + escaped + "'}));"
                + "window.dispatchEvent(new StorageEvent('storage',{key:'aarogya.watch.hubUrl',newValue:'" + escaped + "'}));"
                + "window.dispatchEvent(new Event('aarogya:hub-url-changed'));"
                + "}catch(e){}})();";
        evalOnLoadedWebViews(js);
        Toast.makeText(
                this,
                tr(lang, "Hub URL saved: ", "संजाल पता संचित हुआ: ", "ಕೇಂದ್ರದ ವಿಳಾಸ ಉಳಿಸಲಾಗಿದೆ: ", "நிலைய முகவரி சேமிக்கப்பட்டது: ") + normalized,
                Toast.LENGTH_SHORT
        ).show();
    }

    private void injectSavedHubUrl(WebView view) {
        if (view == null) {
            return;
        }
        String saved = normalizeHubUrl(getSharedPreferences(PREFS_NAME, MODE_PRIVATE).getString(PREF_HUB_URL, ""));
        if (saved.isEmpty()) {
            return;
        }
        String escaped = escapeJsSingleQuoted(saved);
        String js = "(function(){try{"
                + "var cur=localStorage.getItem('aarogya.hubUrl')||localStorage.getItem('aarogya.watch.hubUrl')||'';"
                + "localStorage.setItem('aarogya.hubUrl','" + escaped + "');"
                + "localStorage.setItem('aarogya.watch.hubUrl','" + escaped + "');"
                + "var el=document.querySelector('input[name=\"hub\"],input[data-hub-url]');"
                + "if(el&&el.value!=='" + escaped + "'){el.value='" + escaped + "';el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));}"
                + "if(cur!=='" + escaped + "'){window.dispatchEvent(new Event('aarogya:hub-url-changed'));}"
                + "}catch(e){}})();";
        view.evaluateJavascript(js, null);
    }

    private void clearSavedHubUrl(String lang) {
        getSharedPreferences(PREFS_NAME, MODE_PRIVATE)
                .edit()
                .remove(PREF_HUB_URL)
                .apply();
        String js = "(function(){try{"
                + "localStorage.removeItem('aarogya.hubUrl');"
                + "localStorage.removeItem('aarogya.watch.hubUrl');"
                + "var el=document.querySelector('input[name=\"hub\"],input[data-hub-url]');"
                + "if(el){el.value='';el.dispatchEvent(new Event('input',{bubbles:true}));el.dispatchEvent(new Event('change',{bubbles:true}));}"
                + "window.dispatchEvent(new Event('aarogya:hub-url-changed'));"
                + "}catch(e){}})();";
        evalOnLoadedWebViews(js);
        Toast.makeText(
                this,
                tr(lang, "Hub URL cleared", "संजाल पता हटाया गया", "ಕೇಂದ್ರದ ವಿಳಾಸ ತೆರವುಗೊಳಿಸಲಾಗಿದೆ", "நிலைய முகவரி அழிக்கப்பட்டது"),
                Toast.LENGTH_SHORT
        ).show();
    }

    private void evalOnLoadedWebViews(String js) {
        if (phoneWebView != null) {
            phoneWebView.evaluateJavascript(js, null);
        }
        if (watchWebView != null && watchLoaded) {
            watchWebView.evaluateJavascript(js, null);
        }
    }

    private static String normalizeHubUrl(String raw) {
        if (raw == null) {
            return "";
        }
        String s = raw.trim();
        if (s.isEmpty()) {
            return "";
        }
        if (!s.contains("://")) {
            s = "http://" + s;
        }
        while (s.endsWith("/")) {
            s = s.substring(0, s.length() - 1);
        }
        int schemeEnd = s.indexOf("://");
        if (schemeEnd > 0) {
            s = s.substring(0, schemeEnd).toLowerCase(Locale.US) + s.substring(schemeEnd);
        }
        return s;
    }

    private static boolean isValidHttpUrl(String raw) {
        if (raw == null || raw.isEmpty()) {
            return false;
        }
        try {
            URI uri = new URI(raw);
            String scheme = uri.getScheme();
            String host = uri.getHost();
            int port = uri.getPort();
            return scheme != null
                    && ("http".equalsIgnoreCase(scheme) || "https".equalsIgnoreCase(scheme))
                    && host != null
                    && !host.isEmpty()
                    && (port == -1 || (port >= 1 && port <= 65535));
        } catch (Exception e) {
            return false;
        }
    }

    private static String unquoteJsString(String raw) {
        if (raw == null || "null".equals(raw) || "undefined".equals(raw)) {
            return "";
        }
        String s = raw.trim();
        if (s.length() >= 2 && s.startsWith("\"") && s.endsWith("\"")) {
            s = s.substring(1, s.length() - 1);
            s = s.replace("\\\"", "\"").replace("\\\\", "\\");
        }
        return s;
    }

    private static String escapeJsSingleQuoted(String s) {
        if (s == null) {
            return "";
        }
        return s.replace("\\", "\\\\").replace("'", "\\'").replace("\n", "").replace("\r", "");
    }

    private void startQrScanFlow(String lang, EditText targetInput) {
        pendingQrLang = lang;
        pendingQrTargetInput = targetInput;
        if (checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
            openQrScannerDialog(lang, targetInput);
        } else {
            requestPermissions(new String[]{Manifest.permission.CAMERA}, REQ_CAMERA);
        }
    }

    private void openQrScannerDialog(final String lang, final EditText targetInput) {
        closeQrScannerDialog();
        if (assetServer == null) {
            launchExternalQrIntent(lang);
            return;
        }

        LinearLayout container = new LinearLayout(this);
        container.setOrientation(LinearLayout.VERTICAL);
        container.setPadding(dp(12), dp(8), dp(12), dp(8));
        container.setBackgroundColor(COLOR_BG_SLATE);

        WebView scannerWv = new WebView(this);
        WebSettings settings = scannerWv.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setMediaPlaybackRequiresUserGesture(false);
        scannerWv.setBackgroundColor(0xFF020617);
        scannerWv.setWebChromeClient(new WebChromeClient() {
            @Override
            public void onPermissionRequest(final PermissionRequest request) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        handleWebPermissionRequest(request);
                    }
                });
            }
        });

        scannerWv.addJavascriptInterface(new Object() {
            @JavascriptInterface
            public void onResult(final String raw) {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        handleScannedQrText(raw, lang, targetInput);
                    }
                });
            }

            @JavascriptInterface
            public void fallbackToIntent() {
                runOnUiThread(new Runnable() {
                    @Override
                    public void run() {
                        closeQrScannerDialog();
                        launchExternalQrIntent(lang);
                    }
                });
            }
        }, "QrBridge");

        LinearLayout.LayoutParams wvLp = new LinearLayout.LayoutParams(
                ViewGroup.LayoutParams.MATCH_PARENT,
                dp(290)
        );
        container.addView(scannerWv, wvLp);

        String hintText = tr(
                lang,
                "Point camera at Hub QR code...",
                "स्वास्थ्य केन्द्र के QR कोड पर कैमरा रखें...",
                "ಕೇಂದ್ರದ QR ಕೋಡ್ ಮೇಲೆ ಕ್ಯಾಮೆರಾ ಹಿಡಿಯಿರಿ...",
                "நிலைய QR குறியீட்டின் மீது கேமராவை காட்டவும்..."
        );
        String html = "<!doctype html><html><body style='margin:0;background:#0f172a;color:#f8fafc;font-family:sans-serif;text-align:center;'>"
                + "<video id='v' autoplay playsinline muted style='width:100%;height:240px;object-fit:cover;background:#020617;border-radius:10px;'></video>"
                + "<div id='st' style='padding:8px;font-size:13px;color:#5eead4;'>" + escapeHtml(hintText) + "</div>"
                + "<script>(async function(){"
                + "if(!('BarcodeDetector' in window)||!navigator.mediaDevices||!navigator.mediaDevices.getUserMedia){QrBridge.fallbackToIntent();return;}"
                + "try{"
                + "const stream=await navigator.mediaDevices.getUserMedia({video:{facingMode:{ideal:'environment'}},audio:false});"
                + "const v=document.getElementById('v');v.srcObject=stream;await v.play();"
                + "const det=new BarcodeDetector({formats:['qr_code']});"
                + "const stop=()=>{try{stream.getTracks().forEach(t=>t.stop());}catch(e){}};"
                + "const timer=setInterval(async()=>{"
                + "try{const codes=await det.detect(v);"
                + "if(codes&&codes.length>0&&codes[0].rawValue){clearInterval(timer);stop();QrBridge.onResult(codes[0].rawValue);}"
                + "}catch(e){}"
                + "},220);"
                + "window.addEventListener('pagehide',()=>{clearInterval(timer);stop();});"
                + "}catch(e){QrBridge.fallbackToIntent();}"
                + "})();</script></body></html>";

        scannerWv.loadDataWithBaseURL(assetServer.getBaseUrl() + "/qr-scan", html, "text/html", "UTF-8", null);
        qrScannerWebView = scannerWv;

        AlertDialog.Builder builder = new AlertDialog.Builder(this);
        builder.setTitle(tr(lang, "Scan Hub QR", "QR कोड स्कैन करें", "QR ಸ್ಕ್ಯಾನ್ ಮಾಡಿ", "QR ஸ்கேன் செய்"));
        builder.setView(container);
        builder.setNegativeButton(tr(lang, "Cancel", "निरस्त करें", "ರದ್ದುಮಾಡಿ", "ரத்து செய்"), new DialogInterface.OnClickListener() {
            @Override
            public void onClick(DialogInterface dialog, int which) {
                closeQrScannerDialog();
            }
        });
        builder.setOnCancelListener(new DialogInterface.OnCancelListener() {
            @Override
            public void onCancel(DialogInterface dialog) {
                closeQrScannerDialog();
            }
        });
        qrScannerDialog = builder.create();
        qrScannerDialog.show();
    }

    private void closeQrScannerDialog() {
        if (qrScannerWebView != null) {
            try {
                qrScannerWebView.evaluateJavascript(
                        "(function(){var v=document.getElementById('v');if(v&&v.srcObject){v.srcObject.getTracks().forEach(function(t){t.stop();});}})();",
                        null
                );
            } catch (Exception ignored) {
            }
            qrScannerWebView.removeJavascriptInterface("QrBridge");
            qrScannerWebView.stopLoading();
            qrScannerWebView.destroy();
            qrScannerWebView = null;
        }
        if (qrScannerDialog != null) {
            if (qrScannerDialog.isShowing()) {
                qrScannerDialog.dismiss();
            }
            qrScannerDialog = null;
        }
    }

    private void launchExternalQrIntent(String lang) {
        Intent intent = new Intent("com.google.zxing.client.android.SCAN");
        intent.putExtra("SCAN_MODE", "QR_CODE_MODE");
        try {
            startActivityForResult(intent, REQ_QR_SCAN);
        } catch (ActivityNotFoundException e) {
            Toast.makeText(
                    this,
                    tr(
                            lang,
                            "QR scanner unavailable on this device",
                            "इस उपकरण पर QR स्कैनर उपलब्ध नहीं है",
                            "ಈ ಸಾಧನದಲ್ಲಿ QR ಸ್ಕ್ಯಾನರ್ ಲಭ್ಯವಿಲ್ಲ",
                            "இந்தச் சாதனத்தில் QR ஸ்கேனர் இல்லை"
                    ),
                    Toast.LENGTH_SHORT
            ).show();
        }
    }

    private void handleScannedQrText(String raw, String lang, EditText targetInput) {
        closeQrScannerDialog();
        String normalized = normalizeHubUrl(raw);
        if (!isValidHttpUrl(normalized)) {
            Toast.makeText(
                    this,
                    tr(
                            lang,
                            "Scanned QR is not a valid http:// or https:// URL",
                            "स्कैन किया गया QR मान्य http:// या https:// पता नहीं है",
                            "ಸ್ಕ್ಯಾನ್ ಮಾಡಿದ QR ಮಾನ್ಯವಾದ http:// ಅಥವಾ https:// ವಿಳಾಸವಲ್ಲ",
                            "ஸ்கேன் செய்த QR சரியான http:// அல்லது https:// முகவரி அல்ல"
                    ),
                    Toast.LENGTH_SHORT
            ).show();
            return;
        }
        if (targetInput != null) {
            targetInput.setText(normalized);
            targetInput.setSelection(normalized.length());
        }
        applySavedHubUrl(normalized, lang);
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);
        if (requestCode == REQ_QR_SCAN && resultCode == RESULT_OK && data != null) {
            String result = data.getStringExtra("SCAN_RESULT");
            String lang = pendingQrLang != null ? pendingQrLang : uiLang;
            handleScannedQrText(result, lang, pendingQrTargetInput);
        }
    }

    private static String escapeHtml(String s) {
        if (s == null) {
            return "";
        }
        return s.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;");
    }

    private void handleWebPermissionRequest(PermissionRequest request) {
        Uri origin = request.getOrigin();
        String host = origin != null && origin.getHost() != null ? origin.getHost().toLowerCase(Locale.US) : "";
        boolean isLocalOrigin = "127.0.0.1".equals(host) || "localhost".equals(host);
        if (!isLocalOrigin) {
            Log.w(TAG, "Denied WebView permission request for non-local origin: " + origin);
            request.deny();
            return;
        }

        List<String> requestedResources = new ArrayList<>();
        boolean wantsAudio = false;
        boolean wantsVideo = false;
        String[] resources = request.getResources();
        if (resources != null) {
            for (String res : resources) {
                if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(res)) {
                    requestedResources.add(res);
                    wantsAudio = true;
                } else if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(res)) {
                    requestedResources.add(res);
                    wantsVideo = true;
                }
            }
        }
        if (requestedResources.isEmpty()) {
            request.deny();
            return;
        }

        List<String> missingAndroidPerms = new ArrayList<>();
        if (wantsAudio && checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            missingAndroidPerms.add(Manifest.permission.RECORD_AUDIO);
        }
        if (wantsVideo && checkSelfPermission(Manifest.permission.CAMERA) != PackageManager.PERMISSION_GRANTED) {
            missingAndroidPerms.add(Manifest.permission.CAMERA);
        }

        if (missingAndroidPerms.isEmpty()) {
            request.grant(requestedResources.toArray(new String[0]));
        } else {
            if (pendingWebPermissionRequest != null) {
                pendingWebPermissionRequest.deny();
            }
            pendingWebPermissionRequest = request;
            int reqCode = wantsVideo ? REQ_CAMERA : REQ_RECORD_AUDIO;
            requestPermissions(missingAndroidPerms.toArray(new String[0]), reqCode);
        }
    }

    private void requestMicrophonePermissionIfNeeded() {
        if (checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
            requestPermissions(new String[]{Manifest.permission.RECORD_AUDIO}, REQ_RECORD_AUDIO);
        }
    }

    private void showMicPermissionDeniedToast(String lang) {
        Toast.makeText(
                this,
                tr(
                        lang,
                        "Microphone permission denied — enable Mic in App Settings to record voice",
                        "माइक्रोफ़ोन अनुमति अस्वीकृत — ध्वनि अंकन हेतु ऐप सेटिंग में माइक्रोफ़ोन सक्षम करें",
                        "ಮೈಕ್ರೋಫೋನ್ ಅನುಮತಿ ನಿರಾಕರಿಸಲಾಗಿದೆ — ಧ್ವನಿ ಮುದ್ರಣಕ್ಕಾಗಿ ಆ್ಯಪ್ ಸೆಟ್ಟಿಂಗ್‌ಗಳಲ್ಲಿ ಮೈಕ್ ಸಕ್ರಿಯಗೊಳಿಸಿ",
                        "மைக்ரோஃபோன் அனுமதி மறுக்கப்பட்டது — குரல் பதிவு செய்ய செயலி அமைப்புகளில் மைக்கை இயக்கவும்"
                ),
                Toast.LENGTH_LONG
        ).show();
    }

    private void showCameraPermissionDeniedToast(String lang) {
        Toast.makeText(
                this,
                tr(
                        lang,
                        "Camera permission is required to scan QR codes",
                        "QR कोड स्कैन करने के लिए कैमरा अनुमति आवश्यक है",
                        "QR ಕೋಡ್ ಸ್ಕ್ಯಾನ್ ಮಾಡಲು ಕ್ಯಾಮೆರಾ ಅನುಮತಿ ಅಗತ್ಯವಿದೆ",
                        "QR குறியீட்டை ஸ்கேன் செய்ய கேமரா அனுமதி தேவை"
                ),
                Toast.LENGTH_SHORT
        ).show();
    }

    @Override
    public void onRequestPermissionsResult(int requestCode, String[] permissions, int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if ((requestCode == REQ_RECORD_AUDIO || requestCode == REQ_CAMERA) && pendingWebPermissionRequest != null) {
            PermissionRequest req = pendingWebPermissionRequest;
            pendingWebPermissionRequest = null;
            List<String> grantedResources = new ArrayList<>();
            String[] resources = req.getResources();
            if (resources != null) {
                for (String res : resources) {
                    if (PermissionRequest.RESOURCE_AUDIO_CAPTURE.equals(res)
                            && checkSelfPermission(Manifest.permission.RECORD_AUDIO) == PackageManager.PERMISSION_GRANTED) {
                        grantedResources.add(res);
                    } else if (PermissionRequest.RESOURCE_VIDEO_CAPTURE.equals(res)
                            && checkSelfPermission(Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED) {
                        grantedResources.add(res);
                    }
                }
            }
            if (!grantedResources.isEmpty()) {
                req.grant(grantedResources.toArray(new String[0]));
            } else {
                req.deny();
                if (requestCode == REQ_RECORD_AUDIO) {
                    showMicPermissionDeniedToast(uiLang);
                } else {
                    showCameraPermissionDeniedToast(uiLang);
                }
            }
            return;
        }

        if (requestCode == REQ_RECORD_AUDIO) {
            boolean granted = grantResults != null
                    && grantResults.length > 0
                    && grantResults[0] == PackageManager.PERMISSION_GRANTED;
            if (!granted && checkSelfPermission(Manifest.permission.RECORD_AUDIO) != PackageManager.PERMISSION_GRANTED) {
                showMicPermissionDeniedToast(uiLang);
            }
            return;
        }

        if (requestCode == REQ_CAMERA && pendingQrTargetInput != null) {
            EditText target = pendingQrTargetInput;
            String lang = pendingQrLang != null ? pendingQrLang : uiLang;
            pendingQrTargetInput = null;
            pendingQrLang = null;
            boolean granted = grantResults != null
                    && grantResults.length > 0
                    && grantResults[0] == PackageManager.PERMISSION_GRANTED;
            if (granted) {
                openQrScannerDialog(lang, target);
            } else {
                showCameraPermissionDeniedToast(lang);
            }
        }
    }

    private void openDialer(Uri telUri) {
        Intent intent = new Intent(Intent.ACTION_DIAL, telUri);
        openExternalIntent(intent);
    }

    private void openExternalIntent(Intent intent) {
        try {
            startActivity(intent);
        } catch (ActivityNotFoundException e) {
            Toast.makeText(
                    this,
                    tr(
                            "No app available to handle action",
                            "इस क्रिया हेतु कोई अनुप्रयोग उपलब्ध नहीं",
                            "ಈ ಕ್ರಿಯೆಗೆ ಯಾವುದೇ ಆ್ಯಪ್ ಲಭ್ಯವಿಲ್ಲ",
                            "இந்தச் செயலை மேற்கொள்ள செயலி எதுவும் இல்லை"
                    ),
                    Toast.LENGTH_SHORT
            ).show();
        }
    }

    private static String localizedNetworkLabel(String netType, String lang) {
        if ("OFFLINE".equals(netType)) {
            return tr(lang, "OFFLINE", "संजाल-रहित", "ಆಫ್‌ಲೈನ್", "இணைப்பில்லை");
        }
        if ("HOTSPOT".equals(netType)) {
            return tr(lang, "HOTSPOT", "हॉटस्पॉट", "ಹಾಟ್‌ಸ್ಪಾಟ್", "ஹாட்ஸ்பாட்");
        }
        if ("hi".equals(lang)) {
            return "संजाल";
        }
        if ("kn".equals(lang)) {
            return "ಆನ್‌ಲೈನ್";
        }
        if ("ta".equals(lang)) {
            return "இணைப்பில்";
        }
        if ("CELLULAR".equals(netType)) {
            return "CELL";
        }
        if ("ETHERNET".equals(netType)) {
            return "LAN";
        }
        return netType;
    }

    private void updateTelemetryBadge() {
        if (hubTelemetryPill == null || nativeBridge == null) {
            return;
        }
        int pct = nativeBridge.getBatteryPercent();
        String net = localizedNetworkLabel(nativeBridge.getNetworkType(), uiLang);
        String label = (pct >= 0 ? pct + "%" : "--%") + " · " + net + " ⚙";
        hubTelemetryPill.setText(label);
    }

    private void registerConnectivityCallback() {
        if (networkCallbackRegistered) {
            return;
        }
        try {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm == null) {
                return;
            }
            networkCallback = new ConnectivityManager.NetworkCallback() {
                @Override
                public void onAvailable(Network network) {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            updateTelemetryBadge();
                        }
                    });
                }

                @Override
                public void onLost(Network network) {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            updateTelemetryBadge();
                        }
                    });
                }

                @Override
                public void onCapabilitiesChanged(Network network, NetworkCapabilities caps) {
                    runOnUiThread(new Runnable() {
                        @Override
                        public void run() {
                            updateTelemetryBadge();
                        }
                    });
                }
            };
            cm.registerNetworkCallback(new NetworkRequest.Builder().build(), networkCallback);
            networkCallbackRegistered = true;
        } catch (Exception e) {
            Log.w(TAG, "Connectivity callback registration failed", e);
        }
    }

    private void unregisterConnectivityCallback() {
        if (!networkCallbackRegistered || networkCallback == null) {
            return;
        }
        try {
            ConnectivityManager cm = (ConnectivityManager) getSystemService(Context.CONNECTIVITY_SERVICE);
            if (cm != null) {
                cm.unregisterNetworkCallback(networkCallback);
            }
        } catch (Exception ignored) {
        }
        networkCallbackRegistered = false;
        networkCallback = null;
    }

    @Override
    protected void onResume() {
        super.onResume();
        if (phoneWebView != null) {
            phoneWebView.onResume();
        }
        if (watchWebView != null && watchLoaded) {
            watchWebView.onResume();
        }
        if (!batteryReceiverRegistered) {
            IntentFilter filter = new IntentFilter(Intent.ACTION_BATTERY_CHANGED);
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
                registerReceiver(batteryReceiver, filter, Context.RECEIVER_NOT_EXPORTED);
            } else {
                registerReceiver(batteryReceiver, filter);
            }
            batteryReceiverRegistered = true;
        }
        registerConnectivityCallback();
        syncLocaleFromWebView(getActiveWebView());
        updateTelemetryBadge();
    }

    @Override
    protected void onPause() {
        unregisterConnectivityCallback();
        if (batteryReceiverRegistered) {
            try {
                unregisterReceiver(batteryReceiver);
            } catch (IllegalArgumentException ignored) {
            }
            batteryReceiverRegistered = false;
        }
        if (phoneWebView != null) {
            phoneWebView.onPause();
        }
        if (watchWebView != null && watchLoaded) {
            watchWebView.onPause();
        }
        super.onPause();
    }

    @Override
    protected void onDestroy() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU && backInvokedCallback != null) {
            getOnBackInvokedDispatcher().unregisterOnBackInvokedCallback(backInvokedCallback);
            backInvokedCallback = null;
        }
        if (pendingWebPermissionRequest != null) {
            pendingWebPermissionRequest.deny();
            pendingWebPermissionRequest = null;
        }
        closeQrScannerDialog();
        destroyWebView(phoneWebView);
        phoneWebView = null;
        destroyWebView(watchWebView);
        watchWebView = null;
        if (assetServer != null) {
            assetServer.stop();
            assetServer = null;
        }
        super.onDestroy();
    }

    private static void destroyWebView(WebView wv) {
        if (wv == null) {
            return;
        }
        wv.removeJavascriptInterface("AarogyaNativeBridge");
        wv.stopLoading();
        wv.destroy();
    }

    private int dp(int value) {
        return Math.round(TypedValue.applyDimension(
                TypedValue.COMPLEX_UNIT_DIP,
                value,
                getResources().getDisplayMetrics()
        ));
    }

    private Vibrator resolveVibrator(Context appContext) {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S) {
            VibratorManager vm = (VibratorManager) appContext.getSystemService(Context.VIBRATOR_MANAGER_SERVICE);
            return vm != null ? vm.getDefaultVibrator() : null;
        }
        return resolveLegacyVibrator(appContext);
    }

    @SuppressWarnings("deprecation")
    private static Vibrator resolveLegacyVibrator(Context appContext) {
        return (Vibrator) appContext.getSystemService(Context.VIBRATOR_SERVICE);
    }

    /**
     * Native JavaScript bridge exposed to both WebViews as window.AarogyaNativeBridge.
     */
    public final class AarogyaNativeBridge {
        private final Context appContext;

        AarogyaNativeBridge(Context context) {
            this.appContext = context.getApplicationContext();
        }

        @JavascriptInterface
        public int getBatteryPercent() {
            try {
                BatteryManager bm = (BatteryManager) appContext.getSystemService(Context.BATTERY_SERVICE);
                if (bm != null) {
                    int cap = bm.getIntProperty(BatteryManager.BATTERY_PROPERTY_CAPACITY);
                    if (cap >= 0 && cap <= 100) {
                        return cap;
                    }
                }
                Intent intent = appContext.registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
                if (intent != null) {
                    int level = intent.getIntExtra(BatteryManager.EXTRA_LEVEL, -1);
                    int scale = intent.getIntExtra(BatteryManager.EXTRA_SCALE, -1);
                    if (level >= 0 && scale > 0) {
                        return (int) Math.round((level * 100.0) / scale);
                    }
                }
            } catch (Exception e) {
                Log.w(TAG, "Battery query failed", e);
            }
            return -1;
        }

        @JavascriptInterface
        public boolean isCharging() {
            try {
                Intent intent = appContext.registerReceiver(null, new IntentFilter(Intent.ACTION_BATTERY_CHANGED));
                if (intent != null) {
                    int status = intent.getIntExtra(BatteryManager.EXTRA_STATUS, -1);
                    return status == BatteryManager.BATTERY_STATUS_CHARGING
                            || status == BatteryManager.BATTERY_STATUS_FULL;
                }
            } catch (Exception ignored) {
            }
            return false;
        }

        @JavascriptInterface
        public long getTotalRamMb() {
            try {
                ActivityManager am = (ActivityManager) appContext.getSystemService(Context.ACTIVITY_SERVICE);
                if (am != null) {
                    ActivityManager.MemoryInfo mi = new ActivityManager.MemoryInfo();
                    am.getMemoryInfo(mi);
                    return mi.totalMem / (1024L * 1024L);
                }
            } catch (Exception ignored) {
            }
            return -1L;
        }

        @JavascriptInterface
        public long getAvailableRamMb() {
            try {
                ActivityManager am = (ActivityManager) appContext.getSystemService(Context.ACTIVITY_SERVICE);
                if (am != null) {
                    ActivityManager.MemoryInfo mi = new ActivityManager.MemoryInfo();
                    am.getMemoryInfo(mi);
                    return mi.availMem / (1024L * 1024L);
                }
            } catch (Exception ignored) {
            }
            return -1L;
        }

        @JavascriptInterface
        public int getCpuCores() {
            return Runtime.getRuntime().availableProcessors();
        }

        @JavascriptInterface
        public boolean isOnline() {
            return isNetworkAvailable();
        }

        @JavascriptInterface
        public boolean isNetworkAvailable() {
            return !"OFFLINE".equals(getNetworkType());
        }

        @JavascriptInterface
        public String getNetworkType() {
            try {
                ConnectivityManager cm = (ConnectivityManager) appContext.getSystemService(Context.CONNECTIVITY_SERVICE);
                if (cm != null) {
                    Network active = cm.getActiveNetwork();
                    if (active != null) {
                        String t = transportFromCaps(cm.getNetworkCapabilities(active));
                        if (t != null) {
                            return t;
                        }
                    }
                    Network[] all = cm.getAllNetworks();
                    if (all != null) {
                        for (Network net : all) {
                            String t = transportFromCaps(cm.getNetworkCapabilities(net));
                            if (t != null) {
                                return t;
                            }
                        }
                    }
                }
                String localIfType = detectLocalInterfaceType();
                if (localIfType != null) {
                    return localIfType;
                }
            } catch (Exception e) {
                Log.w(TAG, "Network type query failed", e);
            }
            return "OFFLINE";
        }

        private String transportFromCaps(NetworkCapabilities caps) {
            if (caps == null) {
                return null;
            }
            if (caps.hasTransport(NetworkCapabilities.TRANSPORT_WIFI)) {
                return "WIFI";
            }
            if (caps.hasTransport(NetworkCapabilities.TRANSPORT_ETHERNET)) {
                return "ETHERNET";
            }
            if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.S
                    && caps.hasTransport(NetworkCapabilities.TRANSPORT_USB)) {
                return "ETHERNET";
            }
            if (caps.hasTransport(NetworkCapabilities.TRANSPORT_CELLULAR)) {
                return "CELLULAR";
            }
            if (caps.hasCapability(NetworkCapabilities.NET_CAPABILITY_INTERNET)) {
                return "ONLINE";
            }
            return null;
        }

        private String detectLocalInterfaceType() {
            try {
                Enumeration<NetworkInterface> ifaces = NetworkInterface.getNetworkInterfaces();
                if (ifaces == null) {
                    return null;
                }
                while (ifaces.hasMoreElements()) {
                    NetworkInterface iface = ifaces.nextElement();
                    if (!iface.isUp() || iface.isLoopback()) {
                        continue;
                    }
                    String name = iface.getName() != null ? iface.getName().toLowerCase(Locale.US) : "";
                    boolean hasIpv4 = false;
                    Enumeration<InetAddress> addrs = iface.getInetAddresses();
                    while (addrs.hasMoreElements()) {
                        InetAddress addr = addrs.nextElement();
                        if (addr instanceof Inet4Address && !addr.isLoopbackAddress()) {
                            hasIpv4 = true;
                            break;
                        }
                    }
                    if (!hasIpv4) {
                        continue;
                    }
                    if (name.startsWith("ap") || name.startsWith("swlan") || name.startsWith("softap")) {
                        return "HOTSPOT";
                    }
                    if (name.startsWith("wlan")) {
                        return "WIFI";
                    }
                    if (name.startsWith("rndis") || name.startsWith("usb") || name.startsWith("eth")) {
                        return "ETHERNET";
                    }
                }
            } catch (Exception ignored) {
            }
            return null;
        }

        @JavascriptInterface
        public void vibrateEmergency() {
            try {
                Vibrator vibrator = resolveVibrator(appContext);
                if (vibrator == null || !vibrator.hasVibrator()) {
                    return;
                }
                long[] pattern = new long[]{0, 280, 120, 280, 120, 480};
                vibrator.vibrate(VibrationEffect.createWaveform(pattern, -1));
            } catch (Exception e) {
                Log.w(TAG, "Emergency vibration failed", e);
            }
        }

        @JavascriptInterface
        public void vibratePulse(long durationMs) {
            try {
                long clamped = Math.max(10L, Math.min(durationMs, 2000L));
                Vibrator vibrator = resolveVibrator(appContext);
                if (vibrator == null || !vibrator.hasVibrator()) {
                    return;
                }
                vibrator.vibrate(VibrationEffect.createOneShot(clamped, VibrationEffect.DEFAULT_AMPLITUDE));
            } catch (Exception ignored) {
            }
        }

        @JavascriptInterface
        public void dialEmergency(final String number) {
            final String target = (number == null || number.trim().isEmpty()) ? "108" : number.trim();
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    openDialer(Uri.parse("tel:" + Uri.encode(target)));
                }
            });
        }

        @JavascriptInterface
        public void switchMode(final String mode) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    showMode(mode);
                }
            });
        }

        @JavascriptInterface
        public void setLanguage(final String lang) {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    setUiLanguage(lang, true);
                }
            });
        }

        @JavascriptInterface
        public String getLanguage() {
            return uiLang;
        }

        @JavascriptInterface
        public void openHubSettings() {
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    openSetHubUrlDialog();
                }
            });
        }

        @JavascriptInterface
        public String getDefaultHubUrl() {
            return LocalAssetServer.DEFAULT_HUB_URL;
        }

        @JavascriptInterface
        public String getActiveMode() {
            return activeMode;
        }

        @JavascriptInterface
        public void showToast(final String message) {
            if (message == null || message.isEmpty()) {
                return;
            }
            runOnUiThread(new Runnable() {
                @Override
                public void run() {
                    Toast.makeText(MainActivity.this, message, Toast.LENGTH_SHORT).show();
                }
            });
        }

        @JavascriptInterface
        public String getDeviceInfoJson() {
            int port = assetServer != null ? assetServer.getPort() : -1;
            return "{"
                    + "\"model\":\"" + escapeJson(Build.MODEL) + "\","
                    + "\"manufacturer\":\"" + escapeJson(Build.MANUFACTURER) + "\","
                    + "\"androidVersion\":\"" + escapeJson(Build.VERSION.RELEASE) + "\","
                    + "\"sdkInt\":" + Build.VERSION.SDK_INT + ","
                    + "\"batteryPercent\":" + getBatteryPercent() + ","
                    + "\"charging\":" + isCharging() + ","
                    + "\"totalRamMb\":" + getTotalRamMb() + ","
                    + "\"availableRamMb\":" + getAvailableRamMb() + ","
                    + "\"cpuCores\":" + getCpuCores() + ","
                    + "\"online\":" + isOnline() + ","
                    + "\"networkType\":\"" + escapeJson(getNetworkType()) + "\","
                    + "\"defaultHubUrl\":\"" + escapeJson(LocalAssetServer.DEFAULT_HUB_URL) + "\","
                    + "\"localServerPort\":" + port + ","
                    + "\"activeMode\":\"" + escapeJson(activeMode) + "\","
                    + "\"language\":\"" + escapeJson(uiLang) + "\""
                    + "}";
        }

        private String escapeJson(String s) {
            if (s == null) {
                return "";
            }
            return s.replace("\\", "\\\\").replace("\"", "\\\"");
        }
    }
}
