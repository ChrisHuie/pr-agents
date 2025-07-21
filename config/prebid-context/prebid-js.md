# Prebid.js Technical Context

## Core Architecture: Event-Driven Auction System

Prebid.js operates on an event-driven architecture where adapters, core modules, and publishers communicate through a centralized event system.

### Key Events Flow

```
requestBids() called → 'beforeRequestBids' → 'requestBids' → 
adapters execute → 'bidRequested' → 'bidResponse' → 'bidWon'/'bidTimeout' →
'auctionEnd' → 'setTargeting' → 'beforeBidderHttp' → 'bidderDone'
```

**Critical Events:**
- `auctionInit` - Auction starts, auction ID assigned
- `bidRequested` - Adapter asked for bids
- `bidResponse` - Bid received from adapter
- `bidAdjustment` - Bid price modified (price floors, adjustments)
- `bidWon` - Winning bid selected
- `bidTimeout` - Adapter didn't respond in time
- `auctionEnd` - All adapters done or timed out
- `adRenderFailed` - Creative failed to render
- `adRenderSucceeded` - Ad successfully displayed

### Activity Control System

Prebid.js uses an activity control system to manage privacy and permissions:

```javascript
// Activities that can be controlled:
- accessDevice         // Access device info (cookies, local storage)
- syncUser            // Run user syncs
- enrichEids          // Enhance user IDs
- fetchBids           // Allow adapters to fetch bids
- reportAnalytics     // Send analytics
- transmitEids        // Share user IDs with bidders
- transmitGeoLocation // Share location data
- transmitTid         // Share transaction IDs
```

Each activity can be restricted by:
- Component type (bidder, analytics, rtd module)
- Specific component name
- Privacy rules (GDPR, USP, GPP)

### Configuration Structure

Prebid's config system has specific sections that control behavior:

```javascript
pbjs.setConfig({
  // Auction settings
  priceGranularity: "medium",    // Price bucket configuration
  timeoutBuffer: 400,             // Buffer time for responses
  enableSendAllBids: false,       // Send all bids or just winners
  
  // User sync settings
  userSync: {
    syncEnabled: true,
    pixelEnabled: true,
    iframeEnabled: false,
    syncsPerBidder: 5,
    syncDelay: 3000,
    filterSettings: {
      all: {
        bidders: '*',
        filter: 'include'
      }
    }
  },
  
  // Privacy settings
  consentManagement: {
    gdpr: {
      cmpApi: 'iab',
      timeout: 10000,
      defaultGdprScope: true
    },
    usp: {
      cmpApi: 'iab',
      timeout: 100
    }
  },
  
  // Currency settings
  currency: {
    adServerCurrency: 'USD',
    granularityMultiplier: 1
  },
  
  // S2S configuration
  s2sConfig: [{
    accountId: '1',
    bidders: ['appnexus', 'rubicon'],
    defaultVendor: 'appnexuspsp',
    enabled: true
  }],
  
  // Floors module config
  floors: {
    floorMin: 0.10,
    modelVersion: 'v1',
    schema: {
      fields: ['mediaType', 'size', 'domain']
    }
  }
});
```

### Adapter Registration Pattern

Adapters hook into Prebid through specific integration points:

```javascript
// Adapter lifecycle hooks:
registerBidder({
  code: 'example',
  gvlid: 123,  // Global Vendor List ID for GDPR
  
  // Aliases allow multiple names for same adapter
  aliases: [{code: 'exampleAlias', gvlid: 124}],
  
  // Supported features
  supportedMediaTypes: [BANNER, VIDEO, NATIVE],
  
  // Required methods
  isBidRequestValid: function(bid) {},
  buildRequests: function(bids, bidderRequest) {},
  interpretResponse: function(response, request) {},
  
  // Optional methods
  getUserSyncs: function(syncOptions, responses, gdprConsent, uspConsent, gppConsent) {},
  onBidWon: function(bid) {},
  onSetTargeting: function(bid) {},
  onBidderError: function({error, bidderRequest}) {},
  onTimeout: function(timeoutData) {},
  onBidViewable: function(bid) {},
  reportAnalytics: function(eventType, data) {}
});
```

### Bidder Request Structure

The `bidderRequest` object passed to adapters contains:

```javascript
{
  bidderCode: "example",
  auctionId: "abc123",
  bidderRequestId: "xyz789",
  bids: [{
    bidder: "example",
    params: { /* bidder specific */ },
    mediaTypes: {
      banner: { sizes: [[300,250], [728,90]] },
      video: { 
        context: 'instream',
        playerSize: [[640, 480]],
        mimes: ['video/mp4'],
        protocols: [2, 3]
      }
    },
    adUnitCode: "div-gpt-ad-123",
    transactionId: "tx123",
    bidId: "bid123",
    bidderRequestId: "xyz789",
    auctionId: "abc123",
    src: "client",
    bidRequestsCount: 1,
    bidderRequestsCount: 1,
    bidderWinsCount: 0,
    ortb2: { /* OpenRTB 2.x data */ },
    ortb2Imp: { /* Impression-level OpenRTB data */ }
  }],
  auctionStart: 1234567890,
  timeout: 3000,
  refererInfo: {
    page: "https://example.com",
    domain: "example.com",
    ref: "https://google.com",
    isAmp: false,
    numIframes: 0,
    reachedTop: true
  },
  gdprConsent: {
    consentString: "CO9Zx...",
    gdprApplies: true,
    vendorData: { /* TCF 2.0 vendor data */ },
    apiVersion: 2
  },
  uspConsent: "1YNN",
  ortb2: { /* Global OpenRTB 2.x data */ },
  fledgeEnabled: true  // For Privacy Sandbox
}
```

### Module Types and Their Hooks

**Bid Adapters:**
- Hook into: Auction system
- Key files: `modules/*BidAdapter.js`
- Must implement: `isBidRequestValid`, `buildRequests`, `interpretResponse`

**Analytics Adapters:**
- Hook into: Event system
- Key files: `modules/*AnalyticsAdapter.js`
- Listen to: All prebid events
- Track: Auctions, bids, wins, timeouts, renders

**User ID Modules:**
- Hook into: User identity system
- Key files: `modules/*IdSystem.js`
- Provide: `decode()`, `getId()`, `extendId()`
- Output: User ID in standard format

**RTD (Real-Time Data) Modules:**
- Hook into: Request enrichment pipeline
- Key files: `modules/*RtdProvider.js`
- Methods: `init()`, `getBidRequestData()`, `getTargetingData()`
- Timing: Run before bid requests

**Video Modules:**
- Hook into: Video rendering pipeline
- Handle: VAST parsing, player integration
- Support: Instream, outstream, adpod

### Price Granularity System

Prebid uses price buckets to create targeting keys:

```javascript
// Standard granularities:
'low': {buckets: [{max: 5, increment: 0.50}]},
'medium': {buckets: [{max: 20, increment: 0.10}]},
'high': {buckets: [{max: 20, increment: 0.01}]},
'auto': {buckets: [
  {max: 5, increment: 0.05},
  {max: 10, increment: 0.10},
  {max: 20, increment: 0.50}
]},
'dense': {buckets: [
  {max: 3, increment: 0.01},
  {max: 8, increment: 0.05},
  {max: 20, increment: 0.50}
]}

// Creates targeting keys like:
// hb_pb: "2.50" (price bucket)
// hb_bidder: "example" (bidder name)
// hb_adid: "abc123" (ad ID)
```

### Auction Mechanics

1. **Auction Init**: Each auction gets unique ID
2. **Bid Collection**: Adapters called in parallel
3. **Bid Adjustment**: CPM adjustments, bid caching
4. **Winner Selection**: Highest CPM after adjustments
5. **Targeting Set**: Key-values sent to ad server
6. **Render**: Creative displayed via renderAd()

### OpenRTB Integration

Prebid.js uses OpenRTB 2.x objects throughout:

```javascript
// First-party data in ortb2
pbjs.setConfig({
  ortb2: {
    site: {
      name: "Example",
      domain: "example.com",
      cat: ["IAB2"],
      content: {
        language: "en"
      }
    },
    user: {
      yob: 1985,
      gender: "m"
    }
  }
});

// Impression-level data
adUnits[0].ortb2Imp = {
  ext: {
    data: {
      pbadslot: '/123/homepage'
    }
  }
};
```

### Storage Manager

Prebid abstracts storage access for privacy compliance:

```javascript
// Modules must use storage manager, not direct access
import {getStorageManager} from '../src/storageManager.js';

const storage = getStorageManager({gvlid: 123, moduleName: 'exampleBidAdapter'});

// Methods available based on permissions:
storage.getCookie('name');
storage.setCookie('name', 'value', expiry);
storage.getDataFromLocalStorage('key');
storage.setDataInLocalStorage('key', 'value');
```

### Build System and Bundle Structure

- Uses Webpack to create bundles
- Modules included via gulp build flags
- Core is always included, modules are optional
- Bundle size critical for performance

```bash
gulp build --modules=rubiconBidAdapter,appnexusBidAdapter
```

Creates `build/dist/prebid.js` with only specified modules.