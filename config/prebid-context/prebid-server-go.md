# Prebid Server (Go) Technical Context

## Architecture: HTTP Server with Pluggable Adapters

Prebid Server is a server-side header bidding solution that conducts auctions server-to-server rather than in the browser. The Go version is the primary implementation.

### Core Request Flow

```
/openrtb2/auction → Router → Auction Handler → 
Exchange → Bidder Adapters (parallel) → 
Response Builder → Bid Cache → Response
```

### Adapter Integration Pattern

Unlike Prebid.js where adapters are JavaScript modules, Prebid Server adapters are Go packages that implement specific interfaces:

```go
// adapters/example/example.go
type adapter struct {
    endpoint string
}

// Builder pattern for adapter creation
func Builder(bidderName openrtb_ext.BidderName, config config.Adapter, server config.Server) (adapters.Bidder, error) {
    return &adapter{
        endpoint: config.Endpoint,
    }, nil
}

// Main bid request method
func (a *adapter) MakeRequests(request *openrtb2.BidRequest, reqInfo *adapters.ExtraRequestInfo) ([]*adapters.RequestData, []error) {
    // Split impression objects if needed
    // Build HTTP requests to bidder endpoint
    // Return RequestData objects
}

// Process bidder responses
func (a *adapter) MakeBids(internalRequest *openrtb2.BidRequest, externalRequest *adapters.RequestData, response *adapters.ResponseData) (*adapters.BidderResponse, []error) {
    var bidResponse openrtb2.BidResponse
    if err := json.Unmarshal(response.Body, &bidResponse); err != nil {
        return nil, []error{err}
    }
    
    bidResponse := adapters.NewBidderResponseWithBidsCapacity(len(bidResponse.SeatBid[0].Bid))
    for _, seatBid := range bidResponse.SeatBid {
        for _, bid := range seatBid.Bid {
            bidResponse.Bids = append(bidResponse.Bids, &adapters.TypedBid{
                Bid:     &bid,
                BidType: getMediaType(bid.ImpID, internalRequest.Imp),
            })
        }
    }
    return bidResponse, nil
}
```

### Adapter Registration

Adapters must be registered in multiple places:

```go
// exchange/adapter_builders.go
func newAdapterBuilders() map[openrtb_ext.BidderName]adapters.Builder {
    return map[openrtb_ext.BidderName]adapters.Builder{
        openrtb_ext.BidderExample: example.Builder,
        // ... other adapters
    }
}

// openrtb_ext/bidders.go
const (
    BidderExample BidderName = "example"
)

// static/bidder-params/example.json
{
  "$schema": "http://json-schema.org/draft-04/schema#",
  "title": "Example Adapter Params",
  "description": "Schema for Example adapter params",
  "type": "object",
  "properties": {
    "placementId": {
      "type": "string",
      "description": "Placement ID"
    }
  },
  "required": ["placementId"]
}
```

### Configuration Structure

```yaml
# Server configuration
host: 0.0.0.0
port: 8000
admin_port: 6060

# Adapter-specific settings
adapters:
  example:
    endpoint: "https://bid.example.com/prebid"
    disabled: false
    modifying_vast_xml_allowed: true
    
# Feature flags
auction_timeouts_ms:
  default: 200
  max: 500
  
gdpr:
  enabled: true
  default_value: 1
  timeouts_ms:
    active_vendorlist_fetch: 30000
    
# Stored requests
stored_requests:
  postgres:
    connection:
      dbname: prebid
      host: localhost
      port: 5432
    fetcher:
      query: "SELECT accountId, config FROM stored_requests WHERE id = $1"
    poll_for_updates: true
    
# Metrics and monitoring
metrics:
  influxdb:
    host: localhost:8086
    database: prebid
    
# Currency conversion
currency_converter:
  fetch_url: "https://currency.prebid.org/latest.json"
  fetch_interval_seconds: 3600
```

### OpenRTB 2.x Extensions

Prebid Server extends OpenRTB with custom fields:

```go
// openrtb_ext/request.go
type ExtRequest struct {
    Prebid ExtRequestPrebid `json:"prebid"`
}

type ExtRequestPrebid struct {
    Cache           *ExtRequestPrebidCache      `json:"cache,omitempty"`
    Channel         *ExtRequestPrebidChannel    `json:"channel,omitempty"`
    Debug           bool                        `json:"debug,omitempty"`
    CurrencyConversions *ExtRequestCurrency    `json:"currency,omitempty"`
    Targeting       *ExtRequestTargeting        `json:"targeting,omitempty"`
    SChains         []*ExtRequestPrebidSChain   `json:"schains,omitempty"`
    Bidders         map[string]json.RawMessage  `json:"bidders,omitempty"`
    MultiBid        []*ExtMultiBid             `json:"multibid,omitempty"`
}

// Impression extensions
type ExtImp struct {
    Prebid *ExtImpPrebid                   `json:"prebid,omitempty"`
    Bidder map[string]json.RawMessage      `json:",omitempty"` // Bidder-specific params
}

type ExtImpPrebid struct {
    StoredRequest   *ExtStoredRequest          `json:"storedrequest,omitempty"`
    Options         *Options                   `json:"options,omitempty"`
    Passthrough     json.RawMessage           `json:"passthrough,omitempty"`
    Floors          *ExtImpPrebidFloors       `json:"floors,omitempty"`
}
```

### Stored Request System

Prebid Server can store and retrieve bid request templates:

```json
// Stored request example
{
  "id": "test-imp-id",
  "banner": {
    "format": [{"w": 300, "h": 250}]
  },
  "ext": {
    "prebid": {
      "bidder": {
        "example": {
          "placementId": "12345"
        }
      }
    }
  }
}

// Request using stored request
{
  "imp": [{
    "ext": {
      "prebid": {
        "storedrequest": {
          "id": "test-imp-id"
        }
      }
    }
  }]
}
```

### Auction Endpoint Variants

1. **`/openrtb2/auction`** - Standard OpenRTB 2.x auction
2. **`/openrtb2/video`** - Video-specific endpoint with VAST caching
3. **`/openrtb2/amp`** - Accelerated Mobile Pages support
4. **`/auction`** - Legacy endpoint (deprecated)

### Middleware and Hooks

```go
// endpoints/openrtb2/auction.go
func (deps *endpointDeps) Auction(w http.ResponseWriter, r *http.Request, _ httprouter.Params) {
    // Metric recording
    deps.metricsEngine.RecordRequest(labels)
    
    // Request validation
    if err := validateRequest(request); err != nil {
        deps.metricsEngine.RecordRequestPrivacy(metrics.PrivacyLabels{})
        return
    }
    
    // Privacy enforcement
    if err := deps.privacyEnforcement.Apply(request); err != nil {
        return
    }
    
    // Run auction
    response, err := deps.ex.HoldAuction(ctx, auctionRequest, nil)
    
    // Response caching
    if request.Ext.Prebid.Cache != nil {
        deps.cache.CacheBids(ctx, response)
    }
}
```

### Metrics System

Prebid Server has extensive metrics:

```go
// metrics/config/metrics.go
type Metrics interface {
    RecordRequest(labels Labels)
    RecordImps(labels ImpLabels)
    RecordRequestTime(labels Labels, length time.Duration)
    RecordAdapterRequest(labels AdapterLabels)
    RecordAdapterConnections(labels AdapterLabels, connWasReused bool, connWait time.Duration)
    RecordAdapterBidReceived(labels AdapterLabels, bidType openrtb_ext.BidType, hasAdm bool)
    RecordAdapterPrice(labels AdapterLabels, cpm float64)
    RecordAdapterTime(labels AdapterLabels, length time.Duration)
    RecordCookieSync(status CookieSyncStatus)
    RecordStoredDataFetchTime(labels StoredDataLabels, length time.Duration)
    RecordStoredDataError(labels StoredDataLabels)
    RecordPrebidCacheRequestTime(success bool, length time.Duration)
}
```

### Privacy Modules

GDPR, CCPA, and GPP enforcement:

```go
// privacy/enforcement.go
type Enforcement struct {
    GDPR    gdpr.Permissions
    CCPA    ccpa.Policy
    GPP     gpp.Policy
    COPPA   coppa.Policy
    LMT     lmt.Policy
}

// Applied at multiple levels:
// 1. Global request level
// 2. Per-bidder level
// 3. User sync level
// 4. Analytics level
```

### Bidder Info System

Each adapter has metadata:

```yaml
# static/bidder-info/example.yaml
endpoint: "https://bid.example.com/pbs"
maintainer:
  email: "support@example.com"
gvlVendorID: 123
capabilities:
  app:
    mediaTypes:
      - banner
      - video
      - native
  site:
    mediaTypes:
      - banner
      - video
userSync:
  iframe:
    url: "https://sync.example.com/iframe?gdpr={{.GDPR}}&consent={{.GDPRConsent}}"
    userMacro: "$UID"
  redirect:
    url: "https://sync.example.com/pixel?gdpr={{.GDPR}}&consent={{.GDPRConsent}}"
    userMacro: "$UID"
```

### Testing Structure

```go
// adapters/example/exampletest/supplemental/valid-bid.json
{
  "mockBidRequest": {
    "imp": [{
      "id": "test-imp",
      "banner": {"w": 300, "h": 250},
      "ext": {
        "bidder": {
          "placementId": "123"
        }
      }
    }]
  },
  "httpCalls": [{
    "expectedRequest": {
      "uri": "https://bid.example.com/prebid",
      "body": {
        "imp": [{
          "id": "test-imp",
          "banner": {"w": 300, "h": 250},
          "ext": {"placementId": "123"}
        }]
      }
    },
    "mockResponse": {
      "status": 200,
      "body": {
        "seatbid": [{
          "bid": [{
            "id": "bid-1",
            "impid": "test-imp",
            "price": 1.50,
            "adm": "<creative/>",
            "crid": "creative-1"
          }]
        }]
      }
    }
  }],
  "expectedBidResponses": [{
    "currency": "USD",
    "bids": [{
      "bid": {
        "id": "bid-1",
        "impid": "test-imp",
        "price": 1.50,
        "adm": "<creative/>",
        "crid": "creative-1"
      },
      "type": "banner"
    }]
  }]
}
```

### Module System

Prebid Server supports pluggable modules:

```go
// modules/builder.go
type Module interface {
    HandleEntrypointHook(ctx context.Context, req *http.Request) error
    HandleRawAuctionHook(ctx context.Context, req *openrtb2.BidRequest) error
    HandleProcessedAuctionHook(ctx context.Context, req *openrtb2.BidRequest) error
    HandleBidderRequestHook(ctx context.Context, req *adapters.RequestData) error
    HandleRawBidderResponseHook(ctx context.Context, resp *adapters.ResponseData) error
    HandleAllProcessedBidsHook(ctx context.Context, bids []openrtb2.Bid) error
    HandleAuctionResponseHook(ctx context.Context, resp *openrtb2.BidResponse) error
}
```