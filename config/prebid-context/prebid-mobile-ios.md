# Prebid Mobile iOS SDK Technical Context

## Architecture: Native iOS SDK with Ad Server Integration

Prebid Mobile iOS is a Swift/Objective-C SDK that integrates with iOS apps to enable header bidding for mobile advertising. It works alongside Google Ad Manager (GAM) or other ad servers.

### Core Components Structure

```
PrebidMobile/
├── PrebidMobile/          # Core SDK
│   ├── Core/              # Core auction logic
│   ├── ConfigurationModule/# Global config
│   ├── Rendering/          # Ad rendering
│   └── Targeting/         # Key-value targeting
├── PrebidMobileGAMEventHandlers/  # GAM integration
├── PrebidMobileAdMobAdapters/     # AdMob adapters
└── PrebidMobileMAXAdapters/       # AppLovin MAX adapters
```

### SDK Initialization Pattern

```swift
// AppDelegate.swift or early in app lifecycle
Prebid.shared.prebidServerAccountId = "YOUR_ACCOUNT_ID"
Prebid.shared.prebidServerHost = PrebidHost.Appnexus // or custom

// Optional configurations
Prebid.shared.shareGeoLocation = true
Prebid.shared.logLevel = .debug
Prebid.shared.pbsDebug = true

// GDPR consent
Prebid.shared.subjectToGDPR = true
Prebid.shared.gdprConsentString = "BOMyQRvOMyQRvABABBAAABAAAAAAEA"

// Custom Prebid Server
let customHost = try PrebidHost.custom("https://prebid-server.example.com")
Prebid.shared.prebidServerHost = customHost
```

### Ad Unit Configuration

```swift
// Banner configuration
let bannerUnit = BannerAdUnit(configId: "CONFIG_ID", size: CGSize(width: 320, height: 50))
bannerUnit.setAutoRefreshMillis(time: 30000)

// Add additional sizes
bannerUnit.addAdditionalSize(sizes: [CGSize(width: 300, height: 250)])

// Interstitial configuration  
let interstitialUnit = InterstitialAdUnit(configId: "CONFIG_ID")
interstitialUnit.setMinSizePerc(width: 50, height: 70)

// Video configuration
let videoUnit = VideoAdUnit(configId: "CONFIG_ID", size: CGSize(width: 300, height: 250))
videoUnit.parameters = VideoParameters()
videoUnit.parameters.mimes = ["video/mp4"]
videoUnit.parameters.protocols = [2, 3]
videoUnit.parameters.playbackMethod = [1]

// Native configuration
let nativeUnit = NativeRequest(configId: "CONFIG_ID", assets: nativeAssets)
let nativeAssets = [
    NativeAssetTitle(length: 90, required: true),
    NativeAssetImage(minimumWidth: 200, minimumHeight: 200, required: true, imageSizes: [.MAIN]),
    NativeAssetData(type: .SPONSORED, required: true),
    NativeAssetData(type: .DESC, required: true)
]
```

### GAM Integration Flow

```swift
// 1. Create GAM ad request
let gamRequest = GAMRequest()

// 2. Fetch demand from Prebid
bannerUnit.fetchDemand(adObject: gamRequest) { [weak self] resultCode in
    
    // 3. Load GAM ad with Prebid targeting
    self?.gamBanner.load(gamRequest)
}

// For video with GAM
let gamRequest = GAMRequest()
videoUnit.fetchDemand(adObject: gamRequest) { [weak self] resultCode in
    GAMInterstitialAd.load(withAdManagerAdUnitID: "/YOUR_GAM_ADUNIT_ID",
                          request: gamRequest) { ad, error in
        // Handle loaded ad
    }
}
```

### Rendering Module (SDK Rendering)

```swift
// Direct SDK rendering without primary ad server
let bannerView = BannerView(frame: CGRect(x: 0, y: 0, width: 320, height: 50),
                            configID: "CONFIG_ID",
                            adSize: CGSize(width: 320, height: 50))

bannerView.delegate = self
bannerView.loadAd()

// Delegate methods
func bannerViewPresentationController() -> UIViewController? {
    return self
}

func bannerView(_ bannerView: BannerView, didReceiveAdWithAdSize adSize: CGSize) {
    // Resize container if needed
}

func bannerView(_ bannerView: BannerView, didFailToReceiveAdWith error: Error) {
    // Handle error
}
```

### Request Enrichment

```swift
// User targeting
let targeting = Targeting.shared
targeting.gender = .male
targeting.yearOfBirth = 1985
targeting.userKeywords = "sports,football"

// Location data
targeting.location = CLLocation(latitude: 37.7749, longitude: -122.4194)
targeting.locationPrecision = 2

// App targeting
targeting.domain = "example.com"
targeting.storeURL = "https://apps.apple.com/app/id123456"
targeting.itunesID = "123456"

// Custom user data
targeting.addUserData(key: "segment", value: "premium")

// Access control lists
targeting.addBidderToAccessControlList("bidderA")
targeting.removeBidderFromAccessControlList("bidderB")

// First-party data
targeting.addContextData(key: "weather", value: "sunny")
targeting.addContextKeyword("summer-sale")

// User identity
Prebid.shared.externalUserIdArray = [
    ExternalUserId(source: "example.com", 
                   identifier: "123456",
                   ext: ["rtiPartner": "TDID"])
]
```

### Server Configuration

```swift
// Prebid Server configuration stored in SDK
public class PrebidHost {
    static let Appnexus = try! PrebidHost.custom("https://prebid.openx.net/openrtb2/auction")
    static let Rubicon = try! PrebidHost.custom("https://prebid-server.rubiconproject.com/openrtb2/auction")
    
    // Custom Prebid Server
    static func custom(_ url: String) throws -> PrebidHost {
        // Validates URL format
    }
}

// Request configuration
Prebid.shared.timeoutMillis = 2000 // Default: 2000ms
Prebid.shared.cacheExpireMillis = 300000 // 5 minutes
```

### Native Ads Structure

```swift
// Native ad configuration
let nativeEventTracker = NativeEventTracker(
    event: .Impression,
    methods: [.Image, .js]
)

let nativeUnit = NativeRequest(
    configId: "CONFIG_ID",
    assets: [
        NativeAssetTitle(length: 90, required: true),
        NativeAssetImage(
            minimumWidth: 200,
            minimumHeight: 200,
            required: true,
            imageSizes: [.MAIN]
        ),
        NativeAssetData(type: .SPONSORED, required: true),
        NativeAssetData(type: .DESC, required: true),
        NativeAssetData(type: .CTATEXT, required: false)
    ]
)

nativeUnit.context = .Social
nativeUnit.placementType = .FeedContent
nativeUnit.contextSubType = .Social
nativeUnit.eventtrackers = [nativeEventTracker]
```

### Error Handling and Result Codes

```swift
public enum ResultCode: Int {
    case prebidDemandFetchSuccess = 0
    case prebidDemandNoBids = 1
    case prebidDemandTimedOut = 2
    case prebidDemandFetchFailed = 3
    case prebidServerNotSpecified = 4
    case prebidInvalidAccountId = 5
    case prebidInvalidConfigId = 6
    case prebidInvalidSize = 7
    case prebidNetworkError = 8
    case prebidServerError = 9
    case prebidWrongArguments = 10
}

// Usage in fetch callback
unit.fetchDemand(adObject: request) { resultCode in
    switch resultCode {
    case .prebidDemandFetchSuccess:
        // Load ad with prebid keywords
    case .prebidDemandNoBids:
        // Load without prebid keywords
    case .prebidDemandTimedOut:
        // Handle timeout
    default:
        // Handle other errors
    }
}
```

### Testing Support

```swift
// Enable test mode
Prebid.shared.pbsDebug = true

// Use test config IDs
let testBannerUnit = BannerAdUnit(
    configId: "6ace8c7d-88c0-4623-8117-75bc3f0a2e45", // Prebid test ID
    size: CGSize(width: 300, height: 250)
)

// Mock locations for testing
if ProcessInfo.processInfo.environment["PREBID_TEST"] != nil {
    Prebid.shared.location = CLLocation(
        latitude: 37.7749,
        longitude: -122.4194
    )
}
```

### Privacy and Compliance

```swift
// GDPR
Prebid.shared.subjectToGDPR = true
Prebid.shared.gdprConsentString = "BOMyQRvOMyQRvABABBAAABAAAAAAEA"
Prebid.shared.purposeConsents = "100111001"

// CCPA
Prebid.shared.subjectToCCPA = true
Prebid.shared.uspConsent = "1YNN"

// COPPA
Prebid.shared.subjectToCOPPA = true

// Custom TCF integration
if let cmpSdk = UserDefaults.standard.object(forKey: "IABTCF_CmpSdkID") as? Int {
    Prebid.shared.subjectToGDPR = true
    if let consentString = UserDefaults.standard.string(forKey: "IABTCF_TCString") {
        Prebid.shared.gdprConsentString = consentString
    }
}
```

### Logging and Debugging

```swift
// Log levels
public enum LogLevel: String {
    case debug = "DEBUG"
    case verbose = "VERBOSE"  
    case info = "INFO"
    case warn = "WARN"
    case error = "ERROR"
    case severe = "SEVERE"
}

// Enable detailed logging
Prebid.shared.logLevel = .debug

// Custom logger
class CustomLogger: NSObject, PrebidLoggerDelegate {
    func logMessage(_ message: String, level: LogLevel) {
        // Send to your logging system
        print("[\(level.rawValue)] \(message)")
    }
}

Prebid.shared.customLogger = CustomLogger()
```

### Module Dependencies

The SDK uses these key dependencies:
- `PrebidMobile`: Core SDK (required)
- `PrebidMobileGAMEventHandlers`: For Google Ad Manager integration
- `PrebidMobileAdMobAdapters`: For AdMob mediation
- `PrebidMobileMAXAdapters`: For AppLovin MAX mediation

Integration via:
- **CocoaPods**: `pod 'PrebidMobile'`
- **Carthage**: `github "prebid/prebid-mobile-ios"`
- **SPM**: `https://github.com/prebid/prebid-mobile-ios`