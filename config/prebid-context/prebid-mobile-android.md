# Prebid Mobile Android SDK Technical Context

## Architecture: Android Library with Ad Server Integration

Prebid Mobile Android is a Java/Kotlin SDK that integrates with Android apps to enable header bidding. Like the iOS version, it works alongside Google Ad Manager (GAM) or other ad servers.

### Core Module Structure

```
PrebidMobile/
├── PrebidMobile-core/           # Core SDK module
│   ├── src/main/java/
│   │   ├── org/prebid/mobile/
│   │   │   ├── rendering/     # Ad rendering engine
│   │   │   ├── api/          # Public API
│   │   │   ├── configuration/ # Config management
│   │   │   └── targetingparams/ # Targeting
├── PrebidMobile-gamEventHandlers/ # GAM integration
├── PrebidMobile-admobAdapters/    # AdMob adapters
└── PrebidMobile-maxAdapters/      # AppLovin MAX
```

### SDK Initialization

```java
// Application class or MainActivity
PrebidMobile.setPrebidServerAccountId("YOUR_ACCOUNT_ID");
PrebidMobile.setPrebidServerHost(Host.APPNEXUS); // or RUBICON, CUSTOM

// Custom Prebid Server
Host.CUSTOM.setHostUrl("https://prebid-server.example.com/openrtb2/auction");
PrebidMobile.setPrebidServerHost(Host.CUSTOM);

// Optional configurations
PrebidMobile.setShareGeoLocation(true);
PrebidMobile.setApplicationContext(getApplicationContext());
PrebidMobile.setCustomHeaders(headers);

// GDPR consent
TargetingParams.setSubjectToGDPR(true);
TargetingParams.setGDPRConsentString("BOMyQRvOMyQRvABABBAAABAAAAAAEA");

// Logging
PrebidMobile.setLogLevel(PrebidMobile.LogLevel.DEBUG);
```

### Ad Unit Configuration

```java
// Banner configuration
BannerAdUnit bannerAdUnit = new BannerAdUnit("CONFIG_ID", 320, 50);

// Multiple sizes
bannerAdUnit.addAdditionalSize(300, 250);
bannerAdUnit.addAdditionalSize(728, 90);

// Auto-refresh
bannerAdUnit.setAutoRefreshPeriodMillis(30000);

// Interstitial configuration
InterstitialAdUnit interstitialAdUnit = new InterstitialAdUnit("CONFIG_ID");
interstitialAdUnit.setMinWidthPerc(50);
interstitialAdUnit.setMinHeightPerc(70);

// Video Interstitial
VideoInterstitialAdUnit videoAdUnit = new VideoInterstitialAdUnit("CONFIG_ID");

// Rewarded Video
RewardedVideoAdUnit rewardedAdUnit = new RewardedVideoAdUnit("CONFIG_ID");

// Native configuration
NativeAdUnit nativeAdUnit = new NativeAdUnit("CONFIG_ID");
configureNativeAdUnit(nativeAdUnit);
```

### Native Ad Configuration

```java
private void configureNativeAdUnit(NativeAdUnit adUnit) {
    // Title
    NativeTitleAsset title = new NativeTitleAsset();
    title.setLength(90);
    title.setRequired(true);
    adUnit.addAsset(title);
    
    // Icon
    NativeImageAsset icon = new NativeImageAsset(20, 20, 20, 20);
    icon.setImageType(NativeImageAsset.IMAGE_TYPE.ICON);
    icon.setRequired(true);
    adUnit.addAsset(icon);
    
    // Main Image
    NativeImageAsset image = new NativeImageAsset(200, 200, 200, 200);
    image.setImageType(NativeImageAsset.IMAGE_TYPE.MAIN);
    image.setRequired(true);
    adUnit.addAsset(image);
    
    // Description
    NativeDataAsset description = new NativeDataAsset();
    description.setLen(90);
    description.setDataType(NativeDataAsset.DATA_TYPE.DESC);
    description.setRequired(true);
    adUnit.addAsset(description);
    
    // CTA
    NativeDataAsset cta = new NativeDataAsset();
    cta.setDataType(NativeDataAsset.DATA_TYPE.CTATEXT);
    cta.setRequired(false);
    adUnit.addAsset(cta);
    
    // Event trackers
    NativeEventTracker tracker = new NativeEventTracker();
    tracker.setEvent(NativeEventTracker.EVENT_TYPE.IMPRESSION);
    tracker.setMethods(Arrays.asList(
        NativeEventTracker.EVENT_TRACKING_METHOD.IMAGE,
        NativeEventTracker.EVENT_TRACKING_METHOD.JS
    ));
    adUnit.addEventTracker(tracker);
}
```

### GAM Integration

```java
// With Google Ad Manager
private void loadGAMBanner() {
    // Create GAM AdView
    PublisherAdView publisherAdView = new PublisherAdView(this);
    publisherAdView.setAdUnitId("/YOUR_AD_UNIT_ID");
    publisherAdView.setAdSizes(AdSize.BANNER, AdSize.MEDIUM_RECTANGLE);
    
    // Create Prebid banner unit
    BannerAdUnit adUnit = new BannerAdUnit("CONFIG_ID", 320, 50);
    
    // Create GAM request
    PublisherAdRequest.Builder builder = new PublisherAdRequest.Builder();
    PublisherAdRequest request = builder.build();
    
    // Fetch demand
    adUnit.fetchDemand(request, new OnCompleteListener() {
        @Override
        public void onComplete(ResultCode resultCode) {
            // Load GAM ad with Prebid targeting
            publisherAdView.loadAd(request);
        }
    });
}

// With event handlers (preferred)
private void loadWithEventHandlers() {
    GamBannerAdUnit gamAdUnit = new GamBannerAdUnit(
        "/YOUR_AD_UNIT_ID",
        320, 50,
        "CONFIG_ID"
    );
    
    gamAdUnit.setGamView(publisherAdView);
    gamAdUnit.fetchDemand();
}
```

### SDK Rendering (Original API)

```java
// Direct rendering without primary ad server
BannerView bannerView = new BannerView(
    context,
    "CONFIG_ID",
    new AdSize(320, 50)
);

bannerView.setBannerListener(new BannerViewListener() {
    @Override
    public void onAdLoaded(BannerView bannerView) {
        // Ad loaded successfully
    }
    
    @Override
    public void onAdDisplayed(BannerView bannerView) {
        // Ad displayed
    }
    
    @Override
    public void onAdFailed(BannerView bannerView, AdException exception) {
        // Handle error
    }
    
    @Override
    public void onAdClicked(BannerView bannerView) {
        // Handle click
    }
    
    @Override
    public void onAdClosed(BannerView bannerView) {
        // Handle close
    }
});

bannerView.loadAd();
```

### Video Parameters

```java
VideoBaseAdUnit.Parameters parameters = new VideoBaseAdUnit.Parameters();

// Required
parameters.setMimes(Arrays.asList("video/mp4", "video/3gpp"));
parameters.setProtocols(Arrays.asList(
    Protocols.VAST_2_0,
    Protocols.VAST_3_0
));
parameters.setPlaybackMethod(Arrays.asList(
    PlaybackMethod.AutoPlaySoundOff
));

// Size and duration
parameters.setPlacement(Signals.Placement.InStream);
parameters.setMinDuration(5);
parameters.setMaxDuration(30);

// API frameworks
parameters.setApi(Arrays.asList(
    Signals.Api.VPAID_1,
    Signals.Api.VPAID_2,
    Signals.Api.OMID_1
));

videoAdUnit.setParameters(parameters);
```

### Targeting Parameters

```java
// User targeting
TargetingParams.setGender(TargetingParams.GENDER.MALE);
TargetingParams.setYearOfBirth(1985);
TargetingParams.addUserKeyword("sports");
TargetingParams.addUserKeywords(new HashSet<>(Arrays.asList("football", "tennis")));

// Location
Location location = new Location("prebid");
location.setLatitude(37.7749);
location.setLongitude(-122.4194);
location.setAccuracy(100);
TargetingParams.setLocation(location);
TargetingParams.setLocationDecimalDigits(2);

// App targeting
TargetingParams.setDomain("example.com");
TargetingParams.setStoreUrl("https://play.google.com/store/apps/details?id=com.example");
TargetingParams.setBundleName("com.example.app");

// Custom data
TargetingParams.addUserData("segment", new HashSet<>(Arrays.asList("premium", "sports")));
TargetingParams.addContextData("weather", new HashSet<>(Arrays.asList("sunny")));
TargetingParams.addContextKeyword("summer-sale");

// Access control
TargetingParams.addBidderToAccessControlList("bidderA");
TargetingParams.removeBidderFromAccessControlList("bidderB");

// External IDs
ExternalUserId userId = new ExternalUserId("example.com", "123456");
userId.setAtype(1);
userId.setExt(Collections.singletonMap("rtiPartner", "TDID"));
PrebidMobile.setExternalUserIds(Arrays.asList(userId));
```

### Result Codes and Error Handling

```java
public enum ResultCode {
    SUCCESS("Prebid demand fetch successful"),
    NO_BIDS("Prebid server returned no bids"),
    TIMEOUT("Prebid demand fetch timed out"),
    NETWORK_ERROR("Network error"),
    INVALID_ACCOUNT_ID("Invalid account id"),
    INVALID_CONFIG_ID("Invalid config id"),
    INVALID_SIZE("Invalid size"),
    INVALID_CONTEXT("Invalid context"),
    SERVER_ERROR("Prebid server error"),
    PREBID_SERVER_NOT_SET("Prebid server not set");
    
    private final String description;
    
    public String getDescription() {
        return description;
    }
}

// Usage
adUnit.fetchDemand(request, new OnCompleteListener() {
    @Override
    public void onComplete(ResultCode resultCode) {
        switch (resultCode) {
            case SUCCESS:
                // Load with Prebid keywords
                break;
            case NO_BIDS:
                // Load without Prebid
                break;
            case TIMEOUT:
                Log.w(TAG, "Prebid timeout: " + resultCode.getDescription());
                break;
            default:
                Log.e(TAG, "Prebid error: " + resultCode.getDescription());
        }
    }
});
```

### Testing Support

```java
// Enable debug mode
PrebidMobile.setPbsDebug(true);

// Test configuration IDs
public class TestConstants {
    // Prebid test config IDs
    public static final String BANNER_CONFIG_ID = "6ace8c7d-88c0-4623-8117-75bc3f0a2e45";
    public static final String INTERSTITIAL_CONFIG_ID = "625c6125-f19e-4d5b-95c5-55501526b2a4";
    public static final String VIDEO_CONFIG_ID = "28259226-68de-49f8-88d6-b0f4d015f44e";
}

// Mock server for tests
@Test
public void testBannerDemand() {
    // Mock server setup
    MockWebServer server = new MockWebServer();
    server.enqueue(new MockResponse()
        .setBody(TestResponses.validBidResponse())
        .setResponseCode(200));
    
    Host.CUSTOM.setHostUrl(server.url("/openrtb2/auction").toString());
    PrebidMobile.setPrebidServerHost(Host.CUSTOM);
    
    // Test demand fetch
    CountDownLatch latch = new CountDownLatch(1);
    adUnit.fetchDemand(request, resultCode -> {
        assertEquals(ResultCode.SUCCESS, resultCode);
        latch.countDown();
    });
    
    assertTrue(latch.await(5, TimeUnit.SECONDS));
}
```

### Privacy Compliance

```java
// GDPR
TargetingParams.setSubjectToGDPR(true);
TargetingParams.setGDPRConsentString("BOMyQRvOMyQRvABABBAAABAAAAAAEA");
TargetingParams.setPurposeConsents("100111001");

// CCPA
TargetingParams.setSubjectToCCPA(true);
TargetingParams.setUSPrivacyString("1YNN");

// COPPA
TargetingParams.setSubjectToCOPPA(true);

// TCF 2.0 integration
SharedPreferences prefs = PreferenceManager.getDefaultSharedPreferences(context);
int cmpSdkId = prefs.getInt("IABTCF_CmpSdkID", -1);
if (cmpSdkId != -1) {
    TargetingParams.setSubjectToGDPR(true);
    String consent = prefs.getString("IABTCF_TCString", "");
    TargetingParams.setGDPRConsentString(consent);
}
```

### Key Differences from iOS

1. **Language**: Java/Kotlin vs Swift/Objective-C
2. **Ad Server Integration**: PublisherAdView vs GAMBannerView
3. **Callbacks**: OnCompleteListener interface vs closures
4. **Threading**: Android main thread requirements
5. **Permissions**: AndroidManifest.xml requirements

### Build Configuration

```groovy
// build.gradle module configuration
android {
    compileSdkVersion 33
    
    defaultConfig {
        minSdkVersion 19
        targetSdkVersion 33
        
        buildConfigField "String", "PREBID_VERSION", "\"2.1.0\""
        buildConfigField "int", "PREBID_VERSION_CODE", "2100"
    }
    
    buildTypes {
        debug {
            minifyEnabled false
            testCoverageEnabled true
        }
        release {
            minifyEnabled true
            proguardFiles getDefaultProguardFile('proguard-android.txt'), 'proguard-rules.pro'
        }
    }
}

// ProGuard rules for SDK
-keep class org.prebid.mobile.** { *; }
-keep interface org.prebid.mobile.** { *; }
-keepattributes *Annotation*
-keepattributes Signature
-keepattributes Exceptions
```

### Request Building Internals

```java
// How Prebid constructs the OpenRTB request
public class BidManager {
    private void buildOpenRtbRequest(AdUnit adUnit) {
        BidRequest bidRequest = new BidRequest();
        
        // App object
        App app = new App();
        app.bundle = TargetingParams.getBundleName();
        app.storeurl = TargetingParams.getStoreUrl();
        app.publisher = createPublisher();
        app.ext = createAppExt();
        
        // Device object
        Device device = new Device();
        device.ua = getUserAgent();
        device.geo = createGeo();
        device.lmt = AdIdManager.isLimitAdTrackingEnabled() ? 1 : 0;
        device.ifa = AdIdManager.getAdId();
        device.make = Build.MANUFACTURER;
        device.model = Build.MODEL;
        device.os = "android";
        device.osv = String.valueOf(Build.VERSION.SDK_INT);
        device.h = Resources.getSystem().getDisplayMetrics().heightPixels;
        device.w = Resources.getSystem().getDisplayMetrics().widthPixels;
        device.pxratio = Resources.getSystem().getDisplayMetrics().density;
        device.connectiontype = getConnectionType();
        
        // User object
        User user = new User();
        user.yob = TargetingParams.getYearOfBirth();
        user.gender = TargetingParams.getGender();
        user.keywords = TargetingParams.getUserKeywordsString();
        user.ext = createUserExt();
        
        // Impression objects
        List<Imp> imps = createImpressions(adUnit);
        
        // Regulations
        Regs regs = new Regs();
        regs.ext = createRegsExt();
        
        bidRequest.app = app;
        bidRequest.device = device;
        bidRequest.user = user;
        bidRequest.imp = imps;
        bidRequest.regs = regs;
    }
}
```

### Rendering Engine Architecture

```java
// Rendering subsystem for SDK-rendered ads
public class PrebidRenderer {
    private WebView webView;
    private MraidController mraidController;
    private VideoController videoController;
    
    public void renderAd(String html, RenderingListener listener) {
        if (isVideoContent(html)) {
            videoController.renderVideo(html, listener);
        } else if (isMraidContent(html)) {
            mraidController.renderMraid(html, listener);
        } else {
            renderHtmlInWebView(html, listener);
        }
    }
    
    private void renderHtmlInWebView(String html, RenderingListener listener) {
        webView.getSettings().setJavaScriptEnabled(true);
        webView.addJavascriptInterface(new PrebidJsInterface(), "prebid");
        
        String wrappedHtml = wrapHtmlContent(html);
        webView.loadDataWithBaseURL("https://localhost/", wrappedHtml, 
                                   "text/html", "UTF-8", null);
    }
}
```

### MRAID Support

```java
// MRAID (Mobile Rich Media Ad Interface Definitions) implementation
public class MraidController {
    private static final String[] MRAID_COMMANDS = {
        "close", "expand", "resize", "storePicture", 
        "createCalendarEvent", "playVideo", "open"
    };
    
    public void processMraidCommand(String command, Map<String, String> params) {
        switch (command) {
            case "expand":
                handleExpand(params.get("url"), params.get("width"), params.get("height"));
                break;
            case "resize":
                handleResize(params);
                break;
            case "close":
                handleClose();
                break;
            case "open":
                handleOpen(params.get("url"));
                break;
            // ... other commands
        }
    }
    
    private void injectMraidJs(WebView webView) {
        String mraidJs = AssetManager.getMraidJs();
        webView.evaluateJavascript(mraidJs, null);
        
        // Set MRAID state
        webView.evaluateJavascript("mraid.setState('default');", null);
        
        // Set MRAID properties
        JSONObject properties = new JSONObject();
        properties.put("width", adWidth);
        properties.put("height", adHeight);
        properties.put("useCustomClose", false);
        webView.evaluateJavascript(
            String.format("mraid.setExpandProperties(%s);", properties), null);
    }
}
```

### Cache Management

```java
// Prebid Cache integration
public class PrebidCache {
    private static final String CACHE_ENDPOINT = "/cache";
    
    public void cacheAd(String adm, CacheListener listener) {
        CacheRequest request = new CacheRequest();
        request.puts = Arrays.asList(new CacheObject(adm));
        
        String body = JsonUtil.toJson(request);
        
        PrebidServerConnection.post(
            CACHE_ENDPOINT,
            body,
            new ResponseHandler() {
                @Override
                public void onResponse(String response) {
                    CacheResponse cacheResponse = JsonUtil.fromJson(response, CacheResponse.class);
                    String uuid = cacheResponse.responses.get(0).uuid;
                    listener.onCached(uuid);
                }
            }
        );
    }
    
    public String getCacheUrl(String uuid) {
        return String.format("%s/cache?uuid=%s", 
                           PrebidMobile.getPrebidServerHost().getHostUrl(), 
                           uuid);
    }
}
```

### Event Tracking System

```java
// Analytics and event tracking
public class AnalyticsManager {
    private final List<AnalyticsAdapter> adapters = new ArrayList<>();
    
    public void trackEvent(PrebidEvent event) {
        for (AnalyticsAdapter adapter : adapters) {
            adapter.track(event);
        }
    }
    
    public void trackBidRequest(BidRequest request) {
        PrebidEvent event = new PrebidEvent.Builder()
            .setEventType(EventType.BID_REQUESTED)
            .setTimestamp(System.currentTimeMillis())
            .setAdUnitCode(request.getAdUnitCode())
            .setConfigId(request.getConfigId())
            .build();
            
        trackEvent(event);
    }
    
    public void trackBidResponse(BidResponse response) {
        PrebidEvent event = new PrebidEvent.Builder()
            .setEventType(EventType.BID_RESPONSE)
            .setTimestamp(System.currentTimeMillis())
            .setBidder(response.getBidder())
            .setCpm(response.getCpm())
            .setServerLatency(response.getLatency())
            .build();
            
        trackEvent(event);
    }
}
```

### Thread Management

```java
// Background task handling
public class BackgroundTaskRunner {
    private final ExecutorService executorService = 
        Executors.newFixedThreadPool(Runtime.getRuntime().availableProcessors());
    
    private final Handler mainHandler = new Handler(Looper.getMainLooper());
    
    public void runOnBackgroundThread(Runnable task) {
        executorService.execute(task);
    }
    
    public void runOnMainThread(Runnable task) {
        if (Looper.myLooper() == Looper.getMainLooper()) {
            task.run();
        } else {
            mainHandler.post(task);
        }
    }
    
    // Demand fetch must handle threading properly
    public void fetchDemand(AdUnit adUnit, OnCompleteListener listener) {
        runOnBackgroundThread(() -> {
            ResultCode result = performDemandFetch(adUnit);
            
            runOnMainThread(() -> {
                listener.onComplete(result);
            });
        });
    }
}
```

### Storage and Persistence

```java
// SharedPreferences wrapper for Prebid data
public class PrebidStorage {
    private static final String PREFS_NAME = "org.prebid.mobile";
    private final SharedPreferences prefs;
    
    // Keys
    private static final String KEY_GDPR_CONSENT = "gdpr_consent";
    private static final String KEY_CCPA_CONSENT = "ccpa_consent";
    private static final String KEY_CACHED_BIDDERS = "cached_bidders";
    private static final String KEY_EXTERNAL_USER_IDS = "external_user_ids";
    
    public void saveGdprConsent(String consent) {
        prefs.edit()
            .putString(KEY_GDPR_CONSENT, consent)
            .putLong(KEY_GDPR_CONSENT + "_timestamp", System.currentTimeMillis())
            .apply();
    }
    
    public String getGdprConsent() {
        // Check if consent is still valid (24 hours)
        long timestamp = prefs.getLong(KEY_GDPR_CONSENT + "_timestamp", 0);
        if (System.currentTimeMillis() - timestamp > 24 * 60 * 60 * 1000) {
            return null;
        }
        return prefs.getString(KEY_GDPR_CONSENT, null);
    }
    
    public void saveExternalUserIds(List<ExternalUserId> userIds) {
        String json = JsonUtil.toJson(userIds);
        prefs.edit().putString(KEY_EXTERNAL_USER_IDS, json).apply();
    }
}
```

### Network Layer

```java
// HTTP connection handling
public class PrebidServerConnection {
    private static final int TIMEOUT_MILLIS = 2000;
    private static OkHttpClient client;
    
    static {
        client = new OkHttpClient.Builder()
            .connectTimeout(TIMEOUT_MILLIS, TimeUnit.MILLISECONDS)
            .readTimeout(TIMEOUT_MILLIS, TimeUnit.MILLISECONDS)
            .addInterceptor(new UserAgentInterceptor())
            .addInterceptor(new LoggingInterceptor())
            .build();
    }
    
    public static void post(String path, String body, ResponseHandler handler) {
        String url = PrebidMobile.getPrebidServerHost().getHostUrl() + path;
        
        RequestBody requestBody = RequestBody.create(
            MediaType.parse("application/json"), body);
            
        Request request = new Request.Builder()
            .url(url)
            .post(requestBody)
            .addHeader("Content-Type", "application/json")
            .addHeader("X-Prebid-SDK-Version", BuildConfig.PREBID_VERSION)
            .build();
            
        client.newCall(request).enqueue(new Callback() {
            @Override
            public void onResponse(Call call, Response response) {
                if (response.isSuccessful()) {
                    handler.onResponse(response.body().string());
                } else {
                    handler.onError(new ServerException(response.code()));
                }
            }
            
            @Override
            public void onFailure(Call call, IOException e) {
                handler.onError(e);
            }
        });
    }
}
```

### Common PR Patterns for Android

**File Structure for New Features:**
```
PrebidMobile-core/
├── src/main/
│   ├── java/org/prebid/mobile/
│   │   ├── api/              # Public API changes
│   │   ├── rendering/        # Rendering engine updates
│   │   ├── configuration/    # Config changes
│   │   └── newfeature/       # New feature package
│   └── res/
│       ├── values/
│       │   └── strings.xml   # New strings
│       └── raw/
│           └── mraid.js      # MRAID updates
└── src/test/
    └── java/org/prebid/mobile/
        └── newfeature/       # Unit tests

PrebidMobile-gamEventHandlers/
└── src/main/              # GAM-specific changes
```

**Key Review Points:**
1. **Thread Safety**: All public APIs must be thread-safe
2. **Memory Leaks**: Proper cleanup of WebViews, handlers
3. **API Level**: Maintain minSdkVersion compatibility
4. **ProGuard**: Update rules for new public classes
5. **Permissions**: Document any new permissions needed