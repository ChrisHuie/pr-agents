"""
Realistic PR test scenarios based on actual Prebid organization patterns.

Each scenario represents common PR types found across Prebid repositories,
providing comprehensive test coverage for different development patterns.
"""


from .mock_github import (
    MockBranch,
    MockComment,
    MockFile,
    MockLabel,
    MockMilestone,
    MockPullRequest,
    MockRepository,
    MockReview,
    MockUser,
)


class PrebidPRScenarios:
    """Test scenarios based on real Prebid organization PR patterns."""

    @staticmethod
    def prebid_js_adapter_pr() -> MockPullRequest:
        """
        Scenario: New bid adapter for Prebid.js
        Based on: "Zeta SSP Adapter: add GPP support" type PRs
        """
        author = MockUser("adapter-developer")
        repo = MockRepository(
            name="Prebid.js",
            full_name="prebid/Prebid.js",
            owner=MockUser("prebid"),
            description="A free and open source library for publishers to quickly implement header bidding.",
            language="JavaScript",
            languages={"JavaScript": 95000, "HTML": 3000, "CSS": 2000},
            topics=["javascript", "header-bidding", "advertising", "prebid"],
        )

        files = [
            MockFile(
                "modules/zetaSspBidAdapter.js",
                status="modified",
                additions=45,
                deletions=8,
                patch="""@@ -120,8 +120,15 @@
 function buildRequests(validBidRequests, bidderRequest) {
   const requests = [];
   
+  // Add GPP support
+  const gppConsent = bidderRequest.gppConsent;
+  if (gppConsent && gppConsent.gppString) {
+    payload.gpp = gppConsent.gppString;
+    payload.gpp_sid = gppConsent.applicableSections;
+  }
+
   validBidRequests.forEach(bid => {
     const payload = {
       placementId: bid.params.placementId,
       sizes: bid.sizes""",
            ),
            MockFile(
                "test/spec/modules/zetaSspBidAdapter_spec.js",
                status="modified",
                additions=25,
                deletions=0,
                patch="""@@ -80,6 +80,31 @@
     });
   });
   
+  describe('GPP consent', function () {
+    it('should include GPP data when available', function () {
+      const gppConsentData = {
+        gppString: 'DBACNYA~CPXxRfAPXx...',
+        applicableSections: [7]
+      };
+      
+      const bidderRequest = {
+        gppConsent: gppConsentData
+      };
+      
+      const requests = spec.buildRequests(bidRequests, bidderRequest);
+      const payload = JSON.parse(requests[0].data);
+      
+      expect(payload.gpp).to.equal(gppConsentData.gppString);
+      expect(payload.gpp_sid).to.deep.equal(gppConsentData.applicableSections);
+    });
+  });""",
            ),
        ]

        reviews = [
            MockReview(
                MockUser("prebid-reviewer"),
                "APPROVED",
                "LGTM! GPP implementation looks correct.",
            ),
            MockReview(
                MockUser("core-maintainer"),
                "CHANGES_REQUESTED",
                "Please add unit tests for edge cases.",
            ),
        ]

        base_branch = MockBranch("main", "abc123def456", repo)
        head_branch = MockBranch("feature/zeta-gpp-support", "def456ghi789", repo)

        return MockPullRequest(
            number=123,
            title="Zeta SSP Adapter: add GPP support",
            body="""## Summary
Adds Global Privacy Platform (GPP) support to the Zeta SSP bid adapter.

## Changes
- Added GPP string and applicable sections to bid requests
- Updated unit tests to cover GPP scenarios
- Follows existing adapter patterns for consent handling

## Testing
- [x] Unit tests pass
- [x] Manual testing with GPP-enabled requests
- [ ] Integration testing pending

## Related
- Relates to Prebid.js GPP initiative
- Follows pattern established in other adapters""",
            user=author,
            labels=[
                MockLabel("adapter", "0366d6"),
                MockLabel("feature", "28a745"),
                MockLabel("needs unit tests", "d73a4a"),
            ],
            files=files,
            reviews=reviews,
            base=base_branch,
            head=head_branch,
            merge_commit_sha="ghi789abc123",
        )

    @staticmethod
    def prebid_server_go_infrastructure() -> MockPullRequest:
        """
        Scenario: Infrastructure change in Go-based Prebid Server
        Based on: "Limiting impressions in auction requests" type PRs
        """
        author = MockUser("backend-engineer")
        repo = MockRepository(
            name="prebid-server",
            full_name="prebid/prebid-server",
            owner=MockUser("prebid"),
            description="Server for prebid.js header bidding. ",
            language="Go",
            languages={"Go": 850000, "JavaScript": 15000, "Dockerfile": 2000},
            topics=["go", "header-bidding", "server", "openrtb"],
        )

        files = [
            MockFile(
                "auction/auction.go",
                status="modified",
                additions=35,
                deletions=12,
                patch="""@@ -45,12 +45,25 @@
 
 type AuctionRequest struct {
 	BidRequest *openrtb2.BidRequest
+	MaxImps    int
 	Account    *config.Account
 }
 
+// ValidateImpressions checks if impression count exceeds limits
+func (r *AuctionRequest) ValidateImpressions() error {
+	if r.MaxImps > 0 && len(r.BidRequest.Imp) > r.MaxImps {
+		return fmt.Errorf("request exceeds maximum impressions limit: %d > %d", 
+			len(r.BidRequest.Imp), r.MaxImps)
+	}
+	return nil
+}
+
 func (e *exchange) HoldAuction(ctx context.Context, r AuctionRequest) (*openrtb2.BidResponse, error) {
+	if err := r.ValidateImpressions(); err != nil {
+		return nil, err
+	}
+	
 	debugInfo := &DebugInfo{
 		Request: r.BidRequest,
 	}""",
            ),
            MockFile(
                "config/config.go",
                status="modified",
                additions=8,
                deletions=0,
                patch="""@@ -120,6 +120,14 @@
 type Server struct {
 	ExternalURL string     `mapstructure:"external_url"`
 	GvlID       int        `mapstructure:"gvl_id"`
+	MaxImps     MaxImpsConfig `mapstructure:"max_imps"`
+}
+
+type MaxImpsConfig struct {
+	Total   int `mapstructure:"total"`
+	PerUser int `mapstructure:"per_user"`
+	Value   int `mapstructure:"value"`
+	Enabled bool `mapstructure:"enabled"`
 }""",
            ),
            MockFile(
                "auction/auction_test.go",
                status="modified",
                additions=42,
                deletions=0,
                patch="""@@ -200,6 +200,48 @@
 	}
 }
 
+func TestAuctionRequest_ValidateImpressions(t *testing.T) {
+	tests := []struct {
+		name     string
+		maxImps  int
+		impCount int
+		wantErr  bool
+	}{
+		{
+			name:     "within limit",
+			maxImps:  10,
+			impCount: 5,
+			wantErr:  false,
+		},
+		{
+			name:     "exceeds limit", 
+			maxImps:  5,
+			impCount: 10,
+			wantErr:  true,
+		},
+		{
+			name:     "no limit set",
+			maxImps:  0,
+			impCount: 100,
+			wantErr:  false,
+		},
+	}
+	
+	for _, tt := range tests {
+		t.Run(tt.name, func(t *testing.T) {
+			req := &AuctionRequest{
+				BidRequest: &openrtb2.BidRequest{
+					Imp: make([]openrtb2.Imp, tt.impCount),
+				},
+				MaxImps: tt.maxImps,
+			}
+			
+			err := req.ValidateImpressions()
+			if (err != nil) != tt.wantErr {
+				t.Errorf("ValidateImpressions() error = %v, wantErr %v", err, tt.wantErr)
+			}
+		})
+	}
+}""",
            ),
        ]

        base_branch = MockBranch("main", "def456ghi789", repo)
        head_branch = MockBranch("feature/impression-limits", "ghi789jkl012", repo)

        return MockPullRequest(
            number=456,
            title="Add configurable impression limits for auction requests",
            body="""## Summary
Implements configurable limits on the number of impressions per auction request to prevent resource exhaustion and ensure fair usage.

## Changes
- Added MaxImps configuration to AuctionRequest 
- Implemented ValidateImpressions() method with limit checking
- Added comprehensive unit tests
- Updated configuration structure to support impression limits

## Configuration
```yaml
server:
  max_imps:
    total: 30
    per_user: 10
    enabled: true
```

## Performance Impact
- Minimal overhead: O(1) validation check
- Early rejection of oversized requests
- Configurable limits per deployment needs

## Testing
- [x] Unit tests for all limit scenarios
- [x] Integration tests with various request sizes  
- [x] Performance benchmarks show negligible impact

## Related Issues
Addresses DoS prevention requirements and resource management.""",
            user=author,
            labels=[
                MockLabel("enhancement", "28a745"),
                MockLabel("performance", "0e8a16"),
                MockLabel("security", "d73a4a"),
            ],
            milestone=MockMilestone("v2.1.0"),
            files=files,
            reviews=[
                MockReview(
                    MockUser("security-reviewer"),
                    "APPROVED",
                    "Good security enhancement",
                ),
                MockReview(
                    MockUser("performance-team"), "APPROVED", "Benchmarks look good"
                ),
            ],
            base=base_branch,
            head=head_branch,
            merge_commit_sha="jkl012mno345",
        )

    @staticmethod
    def prebid_mobile_ios_feature() -> MockPullRequest:
        """
        Scenario: iOS mobile feature implementation
        Based on: "Enable landscape support and autorotation" type PRs
        """
        author = MockUser("ios-developer")
        repo = MockRepository(
            name="prebid-mobile-ios",
            full_name="prebid/prebid-mobile-ios",
            owner=MockUser("prebid"),
            description="Prebid Mobile SDK for iOS applications",
            language="Swift",
            languages={"Swift": 120000, "Objective-C": 15000, "Ruby": 2000},
            topics=["ios", "swift", "mobile-sdk", "advertising"],
        )

        files = [
            MockFile(
                "PrebidMobile/AdUnits/AdView.swift",
                status="modified",
                additions=28,
                deletions=5,
                patch="""@@ -15,5 +15,32 @@
 class AdView: UIView {
     
     override func viewDidLoad() {
         super.viewDidLoad()
+        setupOrientationSupport()
+    }
+    
+    private func setupOrientationSupport() {
+        NotificationCenter.default.addObserver(
+            self,
+            selector: #selector(orientationChanged),
+            name: UIDevice.orientationDidChangeNotification,
+            object: nil
+        )
+    }
+    
+    @objc private func orientationChanged() {
+        DispatchQueue.main.async { [weak self] in
+            self?.handleOrientationChange()
+        }
+    }
+    
+    private func handleOrientationChange() {
+        let orientation = UIDevice.current.orientation
+        
+        if orientation.isLandscape {
+            enableLandscapeMode()
+        } else if orientation.isPortrait {
+            enablePortraitMode()
+        }
     }""",
            ),
            MockFile(
                "PrebidMobile/Configuration/PrebidMobileConfig.swift",
                status="modified",
                additions=12,
                deletions=2,
                patch="""@@ -25,2 +25,14 @@
 public class PrebidMobileConfig {
     public static let shared = PrebidMobileConfig()
+    
+    /// Enable automatic orientation handling for ad views
+    public var autorotationEnabled: Bool = true
+    
+    /// Supported interface orientations for ads
+    public var supportedOrientations: UIInterfaceOrientationMask = .all
+    
+    private init() {
+        // Default configuration
+    }
 }""",
            ),
            MockFile(
                "PrebidMobileTests/AdViewTests.swift",
                status="added",
                additions=35,
                deletions=0,
                patch="""@@ -0,0 +1,35 @@
+import XCTest
+@testable import PrebidMobile
+
+class AdViewOrientationTests: XCTestCase {
+    
+    var adView: AdView!
+    
+    override func setUp() {
+        super.setUp()
+        adView = AdView()
+    }
+    
+    func testOrientationChangeHandling() {
+        // Test landscape orientation
+        simulateOrientationChange(to: .landscapeLeft)
+        XCTAssertTrue(adView.isLandscapeMode)
+        
+        // Test portrait orientation  
+        simulateOrientationChange(to: .portrait)
+        XCTAssertFalse(adView.isLandscapeMode)
+    }
+    
+    func testAutorotationConfiguration() {
+        PrebidMobileConfig.shared.autorotationEnabled = false
+        let newAdView = AdView()
+        
+        simulateOrientationChange(to: .landscapeLeft)
+        // Should not respond to orientation changes when disabled
+        XCTAssertFalse(newAdView.isLandscapeMode)
+    }
+    
+    private func simulateOrientationChange(to orientation: UIDeviceOrientation) {
+        // Test helper method
+    }
+}""",
            ),
        ]

        base_branch = MockBranch("main", "ghi789jkl012", repo)
        head_branch = MockBranch("feature/ios-landscape-support", "jkl012mno345", repo)

        return MockPullRequest(
            number=789,
            title="Enable landscape support and autorotation for device orientation",
            body="""## Summary
Adds support for landscape orientation and automatic rotation handling in iOS ad views.

## Changes
- Implemented orientation change detection in AdView
- Added configuration options for autorotation
- Created comprehensive unit tests
- Supports all device orientations with graceful handling

## Features
- Automatic orientation detection and handling
- Configurable autorotation (can be disabled)
- Smooth transitions between orientations
- Memory-safe notification handling

## Testing
- [x] Unit tests for orientation changes
- [x] Manual testing on various iOS devices  
- [x] Portrait/landscape transition testing
- [x] Memory leak testing with orientation changes

## Configuration
```swift
// Enable/disable autorotation globally
PrebidMobileConfig.shared.autorotationEnabled = true

// Set supported orientations
PrebidMobileConfig.shared.supportedOrientations = .landscape
```

## Compatibility
- iOS 12.0+
- iPhone and iPad support
- All orientation modes supported""",
            user=author,
            labels=[
                MockLabel("enhancement", "28a745"),
                MockLabel("mobile", "1d76db"),
                MockLabel("ios", "0366d6"),
            ],
            files=files,
            reviews=[
                MockReview(
                    MockUser("ios-reviewer"), "APPROVED", "Great implementation!"
                ),
                MockReview(
                    MockUser("ux-reviewer"),
                    "CHANGES_REQUESTED",
                    "Please test on iPad Pro",
                ),
            ],
            review_comments=[
                MockComment(
                    MockUser("ios-reviewer"),
                    "Consider using weak references to prevent retain cycles",
                    path="PrebidMobile/AdUnits/AdView.swift",
                    position=25,
                )
            ],
            base=base_branch,
            head=head_branch,
            merge_commit_sha="mno345pqr678",
        )

    @staticmethod
    def documentation_update() -> MockPullRequest:
        """
        Scenario: Documentation update for new bid adapter
        Based on prebid.github.io patterns
        """
        author = MockUser("docs-contributor")
        repo = MockRepository(
            name="prebid.github.io",
            full_name="prebid/prebid.github.io",
            owner=MockUser("prebid"),
            description="Website and documentation for Prebid.org",
            language="HTML",
            languages={"HTML": 45000, "JavaScript": 25000, "CSS": 15000, "Ruby": 5000},
            topics=["documentation", "jekyll", "website", "prebid"],
        )

        files = [
            MockFile(
                "dev-docs/bidders/mediago.md",
                status="added",
                additions=89,
                deletions=0,
                patch="""@@ -0,0 +1,89 @@
+---
+layout: bidder
+title: MediaGo
+description: Prebid MediaGo Bidder Adapter
+pbjs: true
+pbs: true
+pbs_app_supported: true
+biddercode: mediago
+media_types: video, banner
+gpp_sids: tcfeu, tcfca, usnat, usstate_all, usp
+usp_supported: true
+coppa_supported: true
+schain_supported: true
+dchain_supported: false
+safeframes_ok: true
+floors_supported: true
+fpd_supported: true
+pbjs_version_notes: not in 8.0
+---
+
+### Bid params
+
+{: .table .table-bordered .table-striped }
+| Name          | Scope    | Description           | Example    | Type     |
+|---------------|----------|-----------------------|------------|----------|
+| `token`       | required | MediaGo token ID      | `'abc123'` | `string` |
+| `placementId` | required | Placement ID          | `'12345'`  | `string` |
+| `region`      | optional | Geographic region     | `'us'`     | `string` |
+
+### Configuration
+
+MediaGo requires setup of the following configuration:
+
+```javascript
+pbjs.bidderSettings = {
+  mediago: {
+    storageAllowed: true
+  }
+};
+```
+
+### Examples
+
+#### Banner
+```javascript
+var adUnits = [{
+  code: 'banner-div',
+  mediaTypes: {
+    banner: {
+      sizes: [[300, 250], [728, 90]]
+    }
+  },
+  bids: [{
+    bidder: 'mediago',
+    params: {
+      token: 'your-token-here',
+      placementId: '12345'
+    }
+  }]
+}];
+```
+
+#### Video
+```javascript
+var adUnits = [{
+  code: 'video-div',
+  mediaTypes: {
+    video: {
+      context: 'instream',
+      playerSize: [640, 480],
+      mimes: ['video/mp4'],
+      protocols: [2, 3, 5, 6]
+    }
+  },
+  bids: [{
+    bidder: 'mediago',
+    params: {
+      token: 'your-token-here', 
+      placementId: '67890'
+    }
+  }]
+}];
+```""",
            ),
            MockFile(
                "assets/js/prebid-analytics.js",
                status="modified",
                additions=3,
                deletions=1,
                patch="""@@ -120,1 +120,4 @@
 const supportedBidders = [
   'appnexus', 'rubicon', 'openx',
+  'mediago',
 ];""",
            ),
        ]

        base_branch = MockBranch("main", "jkl012mno345", repo)
        head_branch = MockBranch("feature/mediago-docs", "mno345pqr678", repo)

        return MockPullRequest(
            number=101,
            title="Add MediaGo bid adapter documentation",
            body="""## Summary
Adding documentation for the new MediaGo bid adapter.

## Changes
- Created complete bidder documentation page
- Added configuration examples for banner and video
- Included parameter reference table
- Updated supported bidders list

## Documentation Includes
- Bid parameters and types
- Configuration requirements  
- Banner and video examples
- GPP and privacy compliance notes

## Review Checklist
- [x] All parameters documented
- [x] Examples tested and validated
- [x] Follows existing documentation format
- [ ] Technical review pending

Pending PBS Release: v2.1.0""",
            user=author,
            labels=[
                MockLabel("documentation", "0366d6"),
                MockLabel("Pending PBS Release", "fbca04"),
                MockLabel("adapter", "d73a4a"),
            ],
            files=files,
            base=base_branch,
            head=head_branch,
            merge_commit_sha="pqr678stu901",
        )

    @staticmethod
    def universal_creative_security() -> MockPullRequest:
        """
        Scenario: Security update in Universal Creative
        Based on dependency and security patterns
        """
        author = MockUser("security-team")
        repo = MockRepository(
            name="prebid-universal-creative",
            full_name="prebid/prebid-universal-creative",
            owner=MockUser("prebid"),
            description="Universal creative for use with Prebid.js and Prebid Mobile",
            language="JavaScript",
            languages={"JavaScript": 35000, "HTML": 8000, "CSS": 3000},
            topics=["creative", "mobile", "prebid", "advertising"],
        )

        files = [
            MockFile(
                "package.json",
                status="modified",
                additions=5,
                deletions=5,
                patch="""@@ -25,10 +25,10 @@
   "devDependencies": {
     "webpack": "^5.88.0",
-    "tar-fs": "^2.1.1",
+    "tar-fs": "^3.0.4",
     "eslint": "^8.45.0",
-    "terser-webpack-plugin": "^5.3.7",
+    "terser-webpack-plugin": "^5.3.9",
-    "postcss": "^8.4.14"
+    "postcss": "^8.4.31"
   }""",
            ),
            MockFile(
                "src/renderingManager.js",
                status="modified",
                additions=12,
                deletions=3,
                patch="""@@ -45,3 +45,15 @@
   renderAd(creative, container) {
     if (!creative || !container) {
       throw new Error('Invalid creative or container');
+    }
+    
+    // Sanitize creative content to prevent XSS
+    const sanitizedCreative = this.sanitizeContent(creative);
+    
+    if (!sanitizedCreative) {
+      console.warn('Creative content blocked due to security policy');
+      return false;
     }
     
+    container.innerHTML = sanitizedCreative;
+    return true;
   }""",
            ),
            MockFile(
                "src/utils/security.js",
                status="added",
                additions=45,
                deletions=0,
                patch="""@@ -0,0 +1,45 @@
+/**
+ * Security utilities for creative rendering
+ */
+
+const ALLOWED_TAGS = ['div', 'span', 'img', 'a', 'script'];
+const BLOCKED_PROTOCOLS = ['javascript:', 'data:', 'vbscript:'];
+
+/**
+ * Sanitize HTML content to prevent XSS attacks
+ * @param {string} content - HTML content to sanitize
+ * @returns {string} - Sanitized content
+ */
+export function sanitizeHTML(content) {
+  if (typeof content !== 'string') {
+    return '';
+  }
+  
+  // Remove potentially dangerous protocols
+  let sanitized = content;
+  BLOCKED_PROTOCOLS.forEach(protocol => {
+    const regex = new RegExp(protocol, 'gi');
+    sanitized = sanitized.replace(regex, '');
+  });
+  
+  // Additional XSS prevention
+  sanitized = sanitized.replace(/<script[^>]*>.*?<\\/script>/gi, '');
+  sanitized = sanitized.replace(/on\\w+\\s*=\\s*["'][^"']*["']/gi, '');
+  
+  return sanitized;
+}
+
+/**
+ * Validate creative content against security policies
+ * @param {Object} creative - Creative object to validate
+ * @returns {boolean} - Whether creative passes security validation
+ */
+export function validateCreative(creative) {
+  if (!creative || typeof creative !== 'object') {
+    return false;
+  }
+  
+  // Add specific validation logic here
+  return true;
+}""",
            ),
        ]

        base_branch = MockBranch("main", "mno345pqr678", repo)
        head_branch = MockBranch("security/xss-protection", "pqr678stu901", repo)

        return MockPullRequest(
            number=55,
            title="Security: Update dependencies and add XSS protection",
            body="""## Summary
Security update addressing dependency vulnerabilities and adding XSS protection for creative rendering.

## Security Fixes
- Updated tar-fs to v3.0.4 (CVE-2023-XXXX)
- Updated terser-webpack-plugin to v5.3.9 
- Updated postcss to v8.4.31 (security patches)

## XSS Protection
- Added content sanitization for creative rendering
- Implemented security utilities module
- Added validation for dangerous protocols and scripts
- Enhanced creative content filtering

## Changes
- Updated package.json with secure dependency versions
- Added sanitizeHTML() function with XSS prevention
- Enhanced renderingManager with security checks
- Created comprehensive security utilities module

## Testing
- [x] Dependency vulnerability scan passes
- [x] XSS protection tests added and passing
- [x] Creative rendering functionality preserved
- [x] No breaking changes to public API

## Security Impact
- Prevents script injection attacks
- Blocks dangerous protocol usage
- Maintains creative functionality while improving security

## Dependency Audit
```
npm audit fix --force
0 vulnerabilities found
```""",
            user=author,
            labels=[
                MockLabel("security", "d73a4a"),
                MockLabel("dependencies", "0366d6"),
                MockLabel("critical", "b60205"),
            ],
            files=files,
            reviews=[
                MockReview(
                    MockUser("security-lead"),
                    "APPROVED",
                    "Excellent security improvements",
                ),
                MockReview(
                    MockUser("tech-lead"), "APPROVED", "LGTM - no breaking changes"
                ),
            ],
            base=base_branch,
            head=head_branch,
            merge_commit_sha="stu901vwx234",
        )

    @staticmethod
    def get_all_scenarios() -> list[MockPullRequest]:
        """Get all predefined PR scenarios for comprehensive testing."""
        return [
            PrebidPRScenarios.prebid_js_adapter_pr(),
            PrebidPRScenarios.prebid_server_go_infrastructure(),
            PrebidPRScenarios.prebid_mobile_ios_feature(),
            PrebidPRScenarios.documentation_update(),
            PrebidPRScenarios.universal_creative_security(),
        ]
