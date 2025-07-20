# Prebid.js Repository Context

## Repository Overview

Prebid.js is an open-source header bidding library that enables publishers to conduct real-time auctions in the browser before making ad server requests. It's the client-side implementation of the Prebid protocol and integrates with 150+ demand partners.

### Core Purpose
- **Real-time bidding**: Conducts auctions in the browser to maximize ad revenue
- **Multi-format support**: Handles display (banner), video, native, and audio ads
- **Privacy-first**: Built-in consent management for GDPR, CCPA, USP, GPP
- **Performance optimized**: Lazy loading, request batching, and efficient auction management

## Repository Structure

### `/src` - Core Library
The heart of Prebid.js containing the auction engine and core functionality:

- **`/src/adapters/`**: Base classes for all adapter types
  - `bidderFactory.js`: Factory for creating bid adapters, handles adapter lifecycle
  - `adapterManager.js`: Manages all adapters (bidders, analytics, user ID)
  
- **`/src/auction*.js`**: Auction management system
  - `auctionManager.js`: Orchestrates bid auctions, timing, and bid responses
  - `auction.js`: Individual auction instance handling
  - `auctionIndex.js`: Tracks all auctions and their states

- **`/src/mediaTypes.js`**: Defines BANNER, VIDEO, NATIVE, AUDIO constants and validation

- **`/src/prebid.js`**: Main entry point exposing the global `pbjs` object

### `/modules` - Plugin Architecture
Contains all pluggable components. Files follow strict naming conventions:

#### Bid Adapters (`*BidAdapter.js`)
Connect to Supply-Side Platforms (SSPs) and Demand-Side Platforms (DSPs) to fetch bids:
- **Purpose**: Each adapter integrates with a specific ad exchange or SSP
- **Example**: `rubiconBidAdapter.js` connects to Rubicon Project's exchange
- **Key methods**:
  - `isBidRequestValid()`: Validates required parameters (placement IDs, account IDs)
  - `buildRequests()`: Constructs HTTP requests to the bidding endpoint
  - `interpretResponse()`: Parses bid responses into Prebid's standard format
  - `getUserSyncs()`: Returns pixel/iframe URLs for cookie syncing

#### Analytics Adapters (`*AnalyticsAdapter.js`)
Track auction events and performance metrics:
- **Purpose**: Send auction data to analytics platforms for reporting
- **Example**: `googleAnalyticsAdapter.js` sends events to Google Analytics
- **Events tracked**: Auction init, bid requested, bid response, bid won, auction end
- **Common uses**: Revenue tracking, bid performance, timeout analysis

#### RTD Modules (`*RtdProvider.js`)
Real-Time Data providers that enrich bid requests with additional targeting data:
- **Purpose**: Add contextual, behavioral, or first-party data before auction
- **Example**: `permutiveRtdProvider.js` adds audience segments from Permutive
- **Timing**: Runs before bid requests are sent
- **Data types**: User segments, contextual categories, weather, stock prices

#### User ID Modules (`*IdSystem.js`)
Identity solutions for cross-site user recognition without third-party cookies:
- **Purpose**: Generate or retrieve stable user identifiers
- **Example**: `id5IdSystem.js` provides ID5's universal ID
- **Storage**: Can use first-party cookies or local storage
- **Privacy**: Respects consent and provides opt-out mechanisms

#### Video Modules (`*VideoProvider.js`)
Integrate with video players and provide video-specific functionality:
- **Purpose**: Handle video ad playback, VAST/VPAID support
- **Example**: `jwplayerVideoProvider.js` integrates with JW Player
- **Features**: Outstream rendering, video event tracking, player controls

### `/metadata/modules/` (v10.0+)
JSON metadata files that describe module configurations:
```json
{
  "componentType": "bidder",  // or "analytics", "rtd", "userId", "video"
  "title": "Example Bidder",
  "description": "Connects to Example SSP",
  "maintainer": "example@company.com",
  "gvlId": 123  // IAB Global Vendor List ID
}
```

### `/libraries` - Shared Code
Reusable utilities and helpers:
- **`/chunk/`**: Code splitting for dynamic module loading
- **`/ortbConverter/`**: OpenRTB 2.x/3.x conversion utilities
- **`/creativeRenderer/`**: Renders ad creatives safely
- **`/appnexusUtils/`**: Shared utilities for AppNexus family adapters
- **`/teadsUtils/`**: Shared code for Teads adapters
- **`/vidazooUtils/`**: Common functionality for Vidazoo products

### `/test` - Comprehensive Testing
- **`/spec/modules/`**: Unit tests for each module
- **`/spec/unit/`**: Core functionality tests
- **`/fixtures/`**: Mock server responses and test data
- **Testing approach**: Heavy use of Sinon for mocking, Chai for assertions

## Module Types Explained

### Bid Adapters - The Revenue Generators
These are the most common modules. Each represents an integration with an ad exchange:
- **What they do**: Connect to ad servers, submit bid requests, parse responses
- **Real example**: `openxBidAdapter.js` connects to OpenX exchange
- **Key features**:
  - Multi-format support (banner, video, native)
  - Consent handling (GDPR, CCPA)
  - Price floor support
  - Deal ID handling
  - User sync for match rates

### RTD Modules - The Data Enrichers  
Add valuable data to improve targeting and increase bid prices:
- **What they do**: Fetch and attach real-time data before auctions
- **Real example**: `1plusXRtdProvider.js` adds demographic and interest data
- **Data examples**:
  - Weather conditions for weather-sensitive ads
  - Stock prices for financial advertisers
  - Content categories for contextual targeting
  - User segments for behavioral targeting

### ID Modules - The Identity Bridge
Critical for maintaining targeting capabilities in a cookieless world:
- **What they do**: Generate or retrieve user identifiers
- **Real example**: `unifiedIdSystem.js` creates deterministic IDs from email
- **Technologies**:
  - Deterministic IDs (hashed email)
  - Probabilistic IDs (device fingerprinting)
  - Publisher-provided IDs
  - Cohort-based IDs (Topics API)

### Analytics Adapters - The Insight Providers
Essential for optimizing revenue and performance:
- **What they do**: Collect and send auction data for analysis
- **Real example**: `prebidmanagerAnalyticsAdapter.js` provides full auction logs
- **Metrics tracked**:
  - Bid rates by adapter
  - Win rates and prices
  - Timeout frequency
  - Page load impact

## Common Patterns in PRs

### New Bid Adapter PRs
Typically include:
1. `modules/exampleBidAdapter.js` - The adapter implementation
2. `modules/exampleBidAdapter.md` - Documentation
3. `test/spec/modules/exampleBidAdapter_spec.js` - Unit tests
4. Integration test page updates
5. Often 500-1000 lines of code

### Adapter Updates
Common changes:
- Adding new media type support (e.g., adding video to banner-only adapter)
- Implementing new consent frameworks (GPP, USP)
- Adding new bid parameters
- Performance optimizations
- Bug fixes for edge cases

### Core Updates
Less frequent but higher impact:
- Auction algorithm improvements
- New API methods
- Performance optimizations
- Security enhancements
- Breaking changes (major versions)

## Key Technical Concepts

### Auction Flow
1. Publisher calls `pbjs.requestBids()`
2. Prebid validates ad units and builds bid requests
3. Adapters' `buildRequests()` methods are called in parallel
4. HTTP requests sent to all bidders simultaneously  
5. Responses parsed by `interpretResponse()`
6. Auction determines winners
7. Winners passed to ad server via key-value targeting

### Adapter Lifecycle
1. **Registration**: `registerBidder(spec)` adds adapter to system
2. **Validation**: `isBidRequestValid()` checks parameters
3. **Request Building**: `buildRequests()` creates server requests
4. **Response Handling**: `interpretResponse()` normalizes bids
5. **Events**: `onBidWon()`, `onTimeout()` for tracking

### Data Flow
- **Inbound**: Page → Ad Units → Bid Requests → Adapters
- **Outbound**: Server Responses → Bid Objects → Auction → Ad Server
- **Enrichment**: First-party data, RTD modules, user IDs all modify requests

## Performance Considerations

### Request Optimization
- Adapters batch multiple ad slots into single requests
- Parallel requests to all bidders (not sequential)
- Timeout management (typically 1000-3000ms)
- Request size limits (some adapters compress)

### Response Handling
- Streaming response parsing where possible
- Bid caching to avoid redundant auctions
- Lazy loading of non-critical adapters
- Memory management for large responses

## Testing Philosophy

### Required Test Coverage
- Every adapter must have >80% code coverage
- Tests must cover:
  - Valid/invalid parameter scenarios
  - All media types supported
  - Consent handling
  - Timeout behavior
  - Error scenarios

### Test Patterns
```javascript
describe('exampleBidAdapter', function() {
  describe('isBidRequestValid', function() {
    it('should return true with required params', function() {
      const bid = { params: { placementId: '123' } };
      expect(spec.isBidRequestValid(bid)).to.equal(true);
    });
  });
});
```

## Configuration Examples

### Publisher Configuration
```javascript
pbjs.setConfig({
  debug: true,
  timeout: 1000,
  priceGranularity: 'high',
  userSync: {
    syncEnabled: true,
    pixels: [{ type: 'image', url: '//pixel.com' }]
  }
});
```

### Ad Unit Structure
```javascript
{
  code: 'div-1',
  mediaTypes: {
    banner: { sizes: [[300, 250], [728, 90]] },
    video: { 
      playerSize: [640, 480],
      context: 'instream',
      mimes: ['video/mp4']
    }
  },
  bids: [
    { bidder: 'rubicon', params: { accountId: 1001, siteId: 2002 } },
    { bidder: 'appnexus', params: { placementId: 12345 } }
  ]
}
```

## Security & Privacy

### Consent Management
- Built-in modules for GDPR (TCF 2.0), CCPA/USP, GPP
- Consent passed to all adapters automatically
- Adapters must respect consent signals
- User sync gated by consent

### Security Measures
- All adapters run in sandboxed context
- No direct DOM manipulation allowed
- HTTPS required for all endpoints
- Content Security Policy support
- SafeFrame creative rendering

## Common Integration Points

### With Google Ad Manager (DFP)
- Key-value targeting: `hb_pb`, `hb_adid`, `hb_size`
- Price bucket rounding for line items
- Creative templates for rendering

### With Amazon TAM/APS
- Can run alongside Prebid
- Requires timing coordination
- Shared targeting keys possible

### With Other Header Bidders
- Compatible with Amazon UAM
- Can coexist with Index Exchange wrapper
- Supports hybrid client/server setups

## Development Workflow

### Adding a New Module
1. Create module file following naming convention
2. Implement required interface methods
3. Add comprehensive unit tests
4. Create markdown documentation
5. Test with live ad units
6. Submit PR with all components

### Testing Locally
```bash
gulp serve  # Starts local server
gulp test   # Runs unit tests
gulp build  # Creates production bundle
```

### PR Requirements
- All tests passing
- >80% code coverage
- Documentation included
- No linting errors
- Follows module rules
- Includes test pages

This context file provides AI assistants with deep understanding of Prebid.js structure, purpose, and patterns to better analyze PRs and provide meaningful insights.